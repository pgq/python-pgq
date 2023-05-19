"""Cascaded consumer.

Does not maintain node, but is able to pause, resume and switch provider.
"""

from typing import Optional, Any, Sequence

import sys
import time
import optparse

from skytools.basetypes import Cursor, Connection, DictRow
from pgq.baseconsumer import BaseConsumer, EventList, BatchInfo
from pgq.event import Event

PDB = '_provider_db'

__all__ = ['CascadedConsumer']


class CascadedConsumer(BaseConsumer):
    """CascadedConsumer base class.

    Loads provider from target node, accepts pause/resume commands.
    """

    _consumer_state: Optional[DictRow]
    target_db: str
    provider_connstr: Optional[str]

    def __init__(self, service_name: str, db_name: str, args: Sequence[str]) -> None:
        """Initialize new consumer.

        @param service_name: service_name for DBScript
        @param db_name: target database name for get_database()
        @param args: cmdline args for DBScript
        """

        super().__init__(service_name, PDB, args)

        self.log.debug("__init__")

        self.target_db = db_name
        self.provider_connstr = None
        self._consumer_state = None

    def init_optparse(self, parser: Optional[optparse.OptionParser] = None) -> optparse.OptionParser:
        p = super().init_optparse(parser)
        p.add_option("--provider", help="provider location for --register")
        p.add_option("--rewind", action="store_true",
                     help="change queue position according to destination")
        p.add_option("--reset", action="store_true",
                     help="reset queue position on destination side")
        return p

    def startup(self) -> None:
        if self.options.rewind:
            self.rewind()
            sys.exit(0)
        if self.options.reset:
            self.dst_reset()
            sys.exit(0)
        return super().startup()

    def register_consumer(self, provider_loc: Optional[str] = None) -> int:
        """Register consumer on source node first, then target node."""

        if not provider_loc:
            provider_loc = self.options.provider
        if not provider_loc:
            self.log.error('Please give provider location with --provider=')
            sys.exit(1)

        dst_db = self.get_database(self.target_db)
        #dst_curs = dst_db.cursor()
        src_db = self.get_database(PDB, connstr=provider_loc, profile='remote')
        src_curs = src_db.cursor()

        # check target info
        q = "select * from pgq_node.get_node_info(%s)"
        res = self.exec_cmd(src_db, q, [self.queue_name])
        pnode = res[0]['node_name']
        if not pnode:
            raise Exception('parent node not initialized?')

        # source queue
        super().register_consumer()

        # fetch pos
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        src_curs.execute(q, [self.queue_name, self.consumer_name])
        last_tick = src_curs.fetchone()['last_tick']
        if not last_tick:
            raise Exception('registration failed?')
        src_db.commit()

        # target node
        q = "select * from pgq_node.register_consumer(%s, %s, %s, %s)"
        self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name, pnode, last_tick])

        return 1

    def get_consumer_state(self) -> DictRow:
        dst_db = self.get_database(self.target_db)
        q = "select * from pgq_node.get_consumer_state(%s, %s)"
        rows = self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])
        state = rows[0]
        self.log.debug("CascadedConsumer.get_consumer_state: state=%r", state)
        return state

    def get_provider_db(self, state: DictRow) -> Connection:
        provider_loc = state['provider_location']
        return self.get_database(PDB, connstr=provider_loc, profile='remote')

    def unregister_consumer(self) -> None:
        dst_db = self.get_database(self.target_db)
        state = self.get_consumer_state()
        self.get_provider_db(state)

        # unregister on provider
        super().unregister_consumer()

        # unregister on subscriber
        q = "select * from pgq_node.unregister_consumer(%s, %s)"
        self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])

    def rewind(self) -> None:
        self.log.info("Rewinding queue")
        dst_db = self.get_database(self.target_db)

        state = self.get_consumer_state()
        src_db = self.get_provider_db(state)
        src_curs = src_db.cursor()

        dst_tick = state['completed_tick']
        if dst_tick:
            q = "select pgq.register_consumer_at(%s, %s, %s)"
            src_curs.execute(q, [self.queue_name, self.consumer_name, dst_tick])
        else:
            self.log.warning('No tick found on dst side')

        dst_db.commit()
        src_db.commit()

    def dst_reset(self) -> None:
        self.log.info("Resetting queue tracking on dst side")

        dst_db = self.get_database(self.target_db)
        dst_curs = dst_db.cursor()

        state = self.get_consumer_state()

        src_db = self.get_provider_db(state)
        src_curs = src_db.cursor()

        # fetch last tick from source
        q = "select last_tick from pgq.get_consumer_info(%s, %s)"
        src_curs.execute(q, [self.queue_name, self.consumer_name])
        row = src_curs.fetchone()
        src_db.commit()

        # on root node we dont have consumer info
        if not row:
            self.log.info("No info about consumer, cannot reset")
            return

        # set on destination
        last_tick = row['last_tick']
        q = "select * from pgq_node.set_consumer_completed(%s, %s, %s)"
        dst_curs.execute(q, [self.queue_name, self.consumer_name, last_tick])
        dst_db.commit()

    def process_batch(self, db: Connection, batch_id: int, event_list: EventList) -> None:
        state = self._consumer_state

        dst_db = self.get_database(self.target_db)

        assert self.batch_info
        assert state
        if self.is_batch_done(state, self.batch_info, dst_db):
            return

        tick_id = self.batch_info['tick_id']
        self.process_remote_batch(db, tick_id, event_list, dst_db)

        # this also commits
        self.finish_remote_batch(db, dst_db, tick_id)

    def process_root_node(self, dst_db: Connection) -> None:
        """This is called on root node, where no processing should happen.
        """
        # extra sleep
        time.sleep(10 * self.loop_delay)

        self.log.info('{standby: 1}')

    def work(self) -> int:
        """Refresh state before calling Consumer.work()."""

        dst_db = self.get_database(self.target_db)
        self._consumer_state = self.refresh_state(dst_db)

        if self._consumer_state['node_type'] == 'root':
            self.process_root_node(dst_db)
            return 0

        if not self.provider_connstr:
            raise Exception('provider_connstr not set')
        self.get_provider_db(self._consumer_state)

        return super().work()

    def refresh_state(self, dst_db: Connection, full_logic: bool = True) -> DictRow:
        """Fetch consumer state from target node.

        This also sleeps if pause is set and updates
        "uptodate" flag to notify that data is refreshed.
        """

        while True:
            q = "select * from pgq_node.get_consumer_state(%s, %s)"
            rows = self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])
            state = rows[0]
            self.log.debug("CascadedConsumer.refresh_state: state=%r", state)

            # tag refreshed
            if not state['uptodate'] and full_logic:
                q = "select * from pgq_node.set_consumer_uptodate(%s, %s, true)"
                self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])

            if state['cur_error'] and self.work_state != -1:
                q = "select * from pgq_node.set_consumer_error(%s, %s, NULL)"
                self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name])

            if not state['paused'] or not full_logic:
                break
            time.sleep(self.loop_delay)

        # update connection
        loc = state['provider_location']
        if self.provider_connstr != loc:
            self.close_database(PDB)
            self.provider_connstr = loc
            # re-initialize provider connection
            self.get_provider_db(state)

        return state

    def is_batch_done(self, state: DictRow, batch_info: BatchInfo, dst_db: Connection) -> bool:
        cur_tick = batch_info['tick_id']
        prev_tick = batch_info['prev_tick_id']
        dst_tick = state['completed_tick']

        if not dst_tick:
            raise Exception('dst_tick NULL?')

        if prev_tick == dst_tick:
            # on track
            return False

        if cur_tick == dst_tick:
            # current batch is already applied, skip it
            return True

        # anything else means problems
        raise Exception('Lost position: batch %s..%s, dst has %s' % (
                        prev_tick, cur_tick, dst_tick))

    def process_remote_batch(self, src_db: Connection, tick_id: int, event_list: EventList, dst_db: Connection) -> None:
        """Per-batch callback.

        By default just calls process_remote_event() in loop."""
        src_curs = src_db.cursor()
        dst_curs = dst_db.cursor()
        for ev in event_list:
            self.process_remote_event(src_curs, dst_curs, ev)

    def process_remote_event(self, src_curs: Cursor, dst_curs: Cursor, ev: Event) -> None:
        """Per-event callback.

        By default ignores cascading events and gives error on others.
        Can be called from user handler to finish unprocessed events.
        """
        if ev.ev_type[:4] == "pgq.":
            # ignore cascading events
            pass
        else:
            raise Exception('Unhandled event type in queue: %s' % ev.ev_type)

    def finish_remote_batch(self, src_db: Connection, dst_db: Connection, tick_id: int) -> None:
        """Called after event processing.  This should finish
        work on remote db and commit there.
        """
        self.log.debug("CascadedConsumer.finish_remote_batch: tick_id=%r", tick_id)

        # this also commits
        q = "select * from pgq_node.set_consumer_completed(%s, %s, %s)"
        self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name, tick_id])

    def exception_hook(self, det: Any, emsg: str) -> None:
        try:
            dst_db = self.get_database(self.target_db)
            q = "select * from pgq_node.set_consumer_error(%s, %s, %s)"
            self.exec_cmd(dst_db, q, [self.queue_name, self.consumer_name, emsg])
        except BaseException:
            self.log.warning("Failure to call pgq_node.set_consumer_error()")
        self.reset()
        super().exception_hook(det, emsg)

