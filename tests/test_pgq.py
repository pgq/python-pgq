
import os
import secrets

import pytest
import skytools
import datetime

import pgq


TEST_Q_NAME = os.environ.get("TEST_Q_NAME")


@pytest.fixture(scope="session")
def dbconn():
    db = skytools.connect_database("")
    db.set_isolation_level(0)
    return db


@pytest.mark.skipif(not TEST_Q_NAME, reason="no db setup")
def test_insert_event(dbconn):
    with dbconn.cursor() as curs:
        ev_id = pgq.insert_event(curs, TEST_Q_NAME, "mytype", "payload")
    assert ev_id > 0

    with dbconn.cursor() as curs:
        curs.execute("select * from pgq.event_template where ev_id = %s", (ev_id,))
        rows = curs.fetchall()

    assert len(rows) == 1
    assert rows[0]["ev_id"] == ev_id
    assert rows[0]["ev_type"] == "mytype"


@pytest.mark.skipif(not TEST_Q_NAME, reason="no db setup")
def test_bulk_insert_events(dbconn):
    fields = ['ev_type', 'ev_data', 'ev_time']
    my_type = secrets.token_urlsafe(12)
    ev_time = datetime.datetime.now()
    rows1 = [
        {'ev_type': my_type, 'ev_data': 'data1', 'ev_time': ev_time},
        {'ev_type': my_type, 'ev_data': 'data2', 'ev_time': ev_time},
        {'ev_type': my_type, 'ev_data': 'data3', 'ev_time': ev_time},
    ]
    with dbconn.cursor() as curs:
        pgq.bulk_insert_events(curs, rows1, fields, TEST_Q_NAME)

    with dbconn.cursor() as curs:
        curs.execute("select * from pgq.event_template where ev_type = %s", (my_type,))
        rows2 = curs.fetchall()

    assert len(rows1) == len(rows2)

