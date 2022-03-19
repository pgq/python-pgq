"""PgQ consumer framework for Python.
"""

from typing import Optional, Dict, Tuple, Iterator
from skytools.basetypes import Cursor, DictRow

from pgq.baseconsumer import BaseBatchWalker, BaseConsumer, EventList
from pgq.event import Event

__all__ = ['Consumer']


# Event status codes
EV_UNTAGGED = -1
EV_RETRY = 0
EV_DONE = 1


class RetriableEvent(Event):
    """Event which can be retried

    Consumer is supposed to tag them after processing.
    """
    __slots__ = ('_status', )

    _status: int

    def __init__(self, queue_name: str, row: DictRow) -> None:
        super().__init__(queue_name, row)
        self._status = EV_DONE

    def tag_done(self) -> None:
        self._status = EV_DONE

    def get_status(self) -> int:
        return self._status

    def tag_retry(self, retry_time: int = 60) -> None:
        self._status = EV_RETRY
        self.retry_time = retry_time


class RetriableWalkerEvent(RetriableEvent):
    """Redirects status flags to RetriableBatchWalker.

    That way event data can be gc'd immediately and
    tag_done() events don't need to be remembered.
    """
    __slots__ = ('_walker', )

    _walker: "RetriableBatchWalker"

    def __init__(self, walker: "RetriableBatchWalker", queue_name: str, row: DictRow) -> None:
        super().__init__(queue_name, row)
        self._walker = walker

    def tag_done(self) -> None:
        self._walker.tag_event_done(self)

    def get_status(self) -> int:
        return self._walker.get_status(self)

    def tag_retry(self, retry_time: int = 60) -> None:
        self._walker.tag_event_retry(self, retry_time)


class RetriableBatchWalker(BaseBatchWalker):
    """BatchWalker that returns RetriableEvents
    """

    status_map: Dict[int, Tuple[int,int]]

    def __init__(self, curs: Cursor, batch_id: int, queue_name: str, fetch_size: int = 300, consumer_filter: Optional[str] = None) -> None:
        super().__init__(curs, batch_id, queue_name, fetch_size, consumer_filter)
        self.status_map = {}

    def _make_event(self, queue_name: str, row: DictRow) -> RetriableWalkerEvent:
        return RetriableWalkerEvent(self, queue_name, row)

    def tag_event_done(self, event: Event) -> None:
        if event.id in self.status_map:
            del self.status_map[event.id]

    def tag_event_retry(self, event: Event, retry_time: int) -> None:
        self.status_map[event.id] = (EV_RETRY, retry_time)

    def get_status(self, event: Event) -> int:
        return self.status_map.get(event.id, (EV_DONE, 0))[0]

    def iter_status(self) -> Iterator[Tuple[int, Tuple[int, int]]]:
        for res in self.status_map.items():
            yield res


class Consumer(BaseConsumer):
    """Normal consumer base class.
    Can retry events
    """

    _batch_walker_class = RetriableBatchWalker

    def _make_event(self, queue_name: str, row: DictRow) -> RetriableEvent:
        return RetriableEvent(queue_name, row)

    def _flush_retry(self, curs: Cursor, batch_id: int, ev_list: EventList) -> None:
        """Tag retry events."""

        retry = 0
        if self.pgq_lazy_fetch and isinstance(ev_list, RetriableBatchWalker):
            for ev_id, stat in ev_list.iter_status():
                if stat[0] == EV_RETRY:
                    self._tag_retry(curs, batch_id, ev_id, stat[1])
                    retry += 1
                elif stat[0] != EV_DONE:
                    raise Exception("Untagged event: id=%d" % ev_id)
        else:
            for ev in ev_list:
                if ev._status == EV_RETRY:
                    self._tag_retry(curs, batch_id, ev.id, ev.retry_time)
                    retry += 1
                elif ev._status != EV_DONE:
                    raise Exception("Untagged event: (id=%d, type=%s, data=%s, ex1=%s" % (
                                    ev.id, ev.type, ev.data, ev.extra1))

        # report weird events
        if retry:
            self.stat_increase('retry-events', retry)

    def _finish_batch(self, curs: Cursor, batch_id: int, ev_list: EventList) -> None:
        """Tag events and notify that the batch is done."""

        self._flush_retry(curs, batch_id, ev_list)

        super()._finish_batch(curs, batch_id, ev_list)

    def _tag_retry(self, cx: Cursor, batch_id: int, ev_id: int, retry_time: int) -> None:
        """Tag event for retry. (internal)"""
        cx.execute("select pgq.event_retry(%s, %s, %s)",
                   [batch_id, ev_id, retry_time])

