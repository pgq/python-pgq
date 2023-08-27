"""PgQ producer helpers for Python.
"""

from typing import Sequence, Optional, Any, Mapping, Union

import skytools

from skytools.basetypes import Cursor

__all__ = ['bulk_insert_events', 'insert_event']

_fldmap = {
    'id': 'ev_id',
    'time': 'ev_time',
    'type': 'ev_type',
    'data': 'ev_data',
    'extra1': 'ev_extra1',
    'extra2': 'ev_extra2',
    'extra3': 'ev_extra3',
    'extra4': 'ev_extra4',

    'ev_id': 'ev_id',
    'ev_time': 'ev_time',
    'ev_type': 'ev_type',
    'ev_data': 'ev_data',
    'ev_extra1': 'ev_extra1',
    'ev_extra2': 'ev_extra2',
    'ev_extra3': 'ev_extra3',
    'ev_extra4': 'ev_extra4',
}


def bulk_insert_events(curs: Cursor,
                       rows: Union[Sequence[Sequence[Any]], Sequence[Mapping[str, Any]]],
                       fields: Sequence[str],
                       queue_name: str) -> None:
    q = "select pgq.current_event_table(%s)"
    curs.execute(q, [queue_name])
    tbl = curs.fetchone()[0]
    db_fields = [_fldmap[name] for name in fields]
    skytools.magic_insert(curs, tbl, rows, db_fields)


def insert_event(curs: Cursor,
                 queue: str,
                 ev_type: Optional[str],
                 ev_data: Optional[str],
                 extra1: Optional[str] = None,
                 extra2: Optional[str] = None,
                 extra3: Optional[str] = None,
                 extra4: Optional[str] = None) -> int:
    q = "select pgq.insert_event(%s, %s, %s, %s, %s, %s, %s)"
    curs.execute(q, [queue, ev_type, ev_data,
                     extra1, extra2, extra3, extra4])
    return curs.fetchone()[0]

