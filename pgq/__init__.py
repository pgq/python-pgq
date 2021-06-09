"""PgQ framework for Python."""

from pgq.cascade.admin import CascadeAdmin
from pgq.cascade.consumer import CascadedConsumer
from pgq.cascade.nodeinfo import MemberInfo, NodeInfo, QueueInfo
from pgq.cascade.worker import CascadedWorker
from pgq.consumer import Consumer
from pgq.coopconsumer import CoopConsumer
from pgq.event import Event
from pgq.localconsumer import LocalConsumer
from pgq.producer import bulk_insert_events, insert_event
from pgq.remoteconsumer import RemoteConsumer, SerialConsumer
from pgq.status import PGQStatus

__all__ = [
    'Event', 'Consumer', 'CoopConsumer', 'LocalConsumer',
    'bulk_insert_events', 'insert_event',
    'RemoteConsumer', 'SerialConsumer', 'PGQStatus',
    'CascadeAdmin', 'CascadedConsumer', 'CascadedWorker',
    'MemberInfo', 'NodeInfo', 'QueueInfo'
]

__version__ = '3.5.1'

