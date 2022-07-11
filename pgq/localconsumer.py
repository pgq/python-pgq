"""Consumer that stores last applied position in local file.

For cases where the consumer cannot use single database for remote tracking.

To be subclassed, then override .process_local_batch() or .process_local_event()
methods.
"""

from typing import Optional

import errno
import os
import sys
import optparse

import skytools
from skytools.basetypes import Connection

from pgq.event import Event
from pgq.baseconsumer import BaseConsumer, EventList

__all__ = ['LocalConsumer']


class LocalConsumer(BaseConsumer):
    """Consumer that applies batches sequentially in second database.

    Requirements:
     - Whole batch in one TX.
     - Must not use retry queue.

    Features:
     - Can detect if several batches are already applied to dest db.
     - If some ticks are lost, allows to seek back on queue.
       Whether it succeeds, depends on pgq configuration.

    Config options::

        ## Parameters for LocalConsumer ##

        # file location where last applied tick is tracked
        local_tracking_file = ~/state/%(job_name)s.tick
    """

    def reload(self) -> None:
        super().reload()

        self.local_tracking_file = self.cf.getfile('local_tracking_file')
        if not os.path.exists(os.path.dirname(self.local_tracking_file)):
            raise skytools.UsageError("path does not exist: %s" % self.local_tracking_file)

    def init_optparse(self, parser: Optional[optparse.OptionParser] = None) -> optparse.OptionParser:
        p = super().init_optparse(parser)
        p.add_option("--rewind", action="store_true",
                     help="change queue position according to local tick")
        p.add_option("--reset", action="store_true",
                     help="reset local tick based on queue position")
        return p

    def startup(self) -> None:
        if self.options.rewind:
            self.rewind()
            sys.exit(0)
        if self.options.reset:
            self.dst_reset()
            sys.exit(0)
        super().startup()

        self.check_queue()

    def check_queue(self) -> None:
        queue_tick = -1
        local_tick = self.load_local_tick()

        db = self.get_database(self.db_name)
        curs = db.cursor()
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        curs.execute(q, [self.queue_name, self.consumer_name])
        rows = curs.fetchall()
        if len(rows) == 1:
            queue_tick = rows[0]['last_tick']
        db.commit()

        if queue_tick < 0:
            if local_tick >= 0:
                self.log.info("Registering consumer at tick %d", local_tick)
                q = "select * from pgq.register_consumer_at(%s, %s, %s)"
                curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
            else:
                self.log.info("Registering consumer at queue top")
                q = "select * from pgq.register_consumer(%s, %s)"
                curs.execute(q, [self.queue_name, self.consumer_name])
        elif local_tick < 0:
            self.log.info("Local tick missing, storing queue tick %d", queue_tick)
            self.save_local_tick(queue_tick)
        elif local_tick > queue_tick:
            self.log.warning("Tracking out of sync: queue=%d local=%d.  Repositioning on queue.  [Database failure?]",
                             queue_tick, local_tick)
            q = "select * from pgq.register_consumer_at(%s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
        elif local_tick < queue_tick:
            self.log.warning("Tracking out of sync: queue=%d local=%d.  Rewinding queue.  [Lost file data?]",
                             queue_tick, local_tick)
            q = "select * from pgq.register_consumer_at(%s, %s, %s)"
            curs.execute(q, [self.queue_name, self.consumer_name, local_tick])
        else:
            self.log.info("Ticks match: Queue=%d Local=%d", queue_tick, local_tick)

    def work(self) -> int:
        if self.work_state < 0:
            self.check_queue()
        return super().work()

    def process_batch(self, db: Connection, batch_id: int, event_list: EventList) -> None:
        """Process all events in batch.
        """

        # check if done
        if self.is_batch_done():
            return

        # actual work
        self.process_local_batch(db, batch_id, event_list)

        # finish work
        self.set_batch_done()

    def process_local_batch(self, db: Connection, batch_id: int, event_list: EventList) -> None:
        """Overridable method to process whole batch."""
        for ev in event_list:
            self.process_local_event(db, batch_id, ev)

    def process_local_event(self, db: Connection, batch_id: int, ev: Event) -> None:
        """Overridable method to process one event at a time."""
        raise Exception('process_local_event not implemented')

    def is_batch_done(self) -> bool:
        """Helper function to keep track of last successful batch in external database.
        """

        local_tick = self.load_local_tick()
        assert self.batch_info

        cur_tick = self.batch_info['tick_id']
        prev_tick = self.batch_info['prev_tick_id']

        if local_tick < 0:
            # seems this consumer has not run yet?
            return False

        if prev_tick == local_tick:
            # on track
            return False

        if cur_tick == local_tick:
            # current batch is already applied, skip it
            return True

        # anything else means problems
        raise Exception('Lost position: batch %d..%d, dst has %d' % (
                        prev_tick, cur_tick, local_tick))

    def set_batch_done(self) -> None:
        """Helper function to set last successful batch in external database.
        """
        if self.batch_info:
            tick_id = self.batch_info['tick_id']
            self.save_local_tick(tick_id)

    def register_consumer(self) -> int:
        new = super().register_consumer()
        if new:  # fixme
            self.dst_reset()
        return new

    def unregister_consumer(self) -> None:
        """If unregistering, also clean completed tick table on dest."""

        super().unregister_consumer()
        self.dst_reset()

    def rewind(self) -> None:
        dst_tick = self.load_local_tick()
        if dst_tick >= 0:
            src_db = self.get_database(self.db_name)
            src_curs = src_db.cursor()

            self.log.info("Rewinding queue to local tick %d", dst_tick)
            q = "select pgq.register_consumer_at(%s, %s, %s)"
            src_curs.execute(q, [self.queue_name, self.consumer_name, dst_tick])

            src_db.commit()
        else:
            self.log.error('Cannot rewind, no tick found in local file')

    def dst_reset(self) -> None:
        self.log.info("Removing local tracking file")
        try:
            os.remove(self.local_tracking_file)
        except BaseException:
            pass

    def load_local_tick(self) -> int:
        """Reads stored tick or -1."""
        try:
            with open(self.local_tracking_file, "r", encoding="utf8") as f:
                buf = f.read()
            data = buf.strip()
            if data:
                tick_id = int(data)
            else:
                tick_id = -1
            return tick_id
        except IOError as ex:
            if ex.errno == errno.ENOENT:
                return -1
            raise

    def save_local_tick(self, tick_id: int) -> None:
        """Store tick in local file."""
        data = str(tick_id)
        skytools.write_atomic(self.local_tracking_file, data)

