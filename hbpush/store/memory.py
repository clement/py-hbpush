from hbpush.store import Store
from hbpush.message import Message

from bisect import bisect


class MemoryStore(Store):
    def __init__(self, *args, **kwargs):
        super(MemoryStore, self).__init__(*args, **kwargs)
        self.messages = []

    def get(self, last_modified, etag, callback, errback):
        msg = Message(last_modified, etag)
        try:
            callback(self.messages[bisect(self.messages, msg)])
        except IndexError:
            errback(Message.DoesNotExist)

    def post(self, message, callback, errback):
        self.messages.append(message)
        callback(message)
