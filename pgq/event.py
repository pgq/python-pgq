"""PgQ event container.
"""

from typing import Any, Optional, Iterable, Tuple

from skytools.basetypes import DictRow

__all__ = ['Event']

_fldmap = {
    'ev_id': 'ev_id',
    'ev_txid': 'ev_txid',
    'ev_time': 'ev_time',
    'ev_type': 'ev_type',
    'ev_data': 'ev_data',
    'ev_extra1': 'ev_extra1',
    'ev_extra2': 'ev_extra2',
    'ev_extra3': 'ev_extra3',
    'ev_extra4': 'ev_extra4',
    'ev_retry': 'ev_retry',

    'id': 'ev_id',
    'txid': 'ev_txid',
    'time': 'ev_time',
    'type': 'ev_type',
    'data': 'ev_data',
    'extra1': 'ev_extra1',
    'extra2': 'ev_extra2',
    'extra3': 'ev_extra3',
    'extra4': 'ev_extra4',
    'retry': 'ev_retry',
}


class Event(object):
    """Event data for consumers.

    Will be removed from the queue by default.
    """
    __slots__ = ('_event_row', 'retry_time', 'queue_name')

    _event_row: DictRow
    retry_time: int
    queue_name: str

    def __init__(self, queue_name: str, row: DictRow) -> None:
        self._event_row = row
        self.retry_time = 60
        self.queue_name = queue_name

    def __getattr__(self, key: str) -> Any:
        return self._event_row[_fldmap[key]]

    # would be better in RetriableEvent only since we don't care but
    # unfortunately it needs to be defined here due to compatibility concerns
    def tag_done(self) -> None:
        pass

    # be also dict-like
    def __getitem__(self, k: str) -> Any:
        return self._event_row.__getitem__(k)

    def __contains__(self, k: str) -> bool:
        return self._event_row.__contains__(k)

    def get(self, k: str, d: Optional[Any] = None) -> Any:
        return self._event_row.get(k, d)

    def has_key(self, k: str) -> bool:
        return k in self._event_row

    def keys(self) -> Iterable[str]:
        return self._event_row.keys()

    def values(self) -> Iterable[Any]:
        return self._event_row.values()

    def items(self) -> Iterable[Tuple[str, Any]]:
        return self._event_row.items()

    def __str__(self) -> str:
        return "<id=%d type=%s data=%s e1=%s e2=%s e3=%s e4=%s>" % (
            self.id, self.type, self.data, self.extra1, self.extra2, self.extra3, self.extra4)

