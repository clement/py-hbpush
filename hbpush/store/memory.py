from hbpush.store import Store
from hbpush.message import Message

from bisect import bisect


class MemoryStore(Store):
    def __init__(self, *args, **kwargs):
        super(MemoryStore, self).__init__(*args, **kwargs)
        self.messages = {}

    def get(self, channel_id, last_modified, etag, callback, errback):
        channel_messages = self.messages.setdefault(channel_id, [])

        msg = Message(last_modified, etag)
        try:
            callback(channel_messages[bisect(channel_messages, msg)])
        except IndexError:
            errback(Message.DoesNotExist)

    def post(self, channel_id, message, callback, errback):
        self.messages.setdefault(channel_id, []).append(message)
        callback(message)
