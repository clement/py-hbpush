import logging
from hbpush.channel import Channel
from hbpush.message import Message

from brukva.adisp import async, process


class MemoryChannel(Channel):
    channels = {}

    def __init__(self, *args, **kwargs):
        super(MemoryChannel, self).__init__(*args, **kwargs)
        self.subscribers = {}
        # Empty message, we just want to keep etag and lastmodified data
        self.last_message = Message(0, 0)

    @classmethod
    def get_by_id(cls, id):
        try:
            return cls.channels[id]
        except KeyError:
            raise Channel.DoesNotExist

    @classmethod
    def create(cls, id, overwrite=False):
        if not overwrite and id in cls.channels:
            raise Channel.Duplicate
        cls.channels[id] = cls()
        return cls.get_by_id(id)

    def get_last_message(self):
        return self.last_message

    @async
    @process
    def post(self, content_type, body, callback):
        message = self.make_message(content_type, body)
        message = yield self.store.post(message)

        if message is not None: # No error when storing
            # We work on a copy to deal with reentering subscribers
            subs = self.subscribers.copy()
            self.subscribers = {}
            for id_subscriber in subs:
                try:
                    subs[id_subscriber](message)
                except:
                    logging.error("Error sending message to subscriber", exc_info=True)
            self.last_message = Message(message.last_modified, message.etag)

        # Give back control to the handler with the result of the store
        callback(message)

    def subscribe(self, id_subscriber, callback):
        self.subscribers[id_subscriber] = callback

    def unsubscribe(self, id_subscriber):
        del self.subscribers[id_subscriber]


    @async
    @process
    def get(self, id_subscriber, last_modified, etag, callback):
        request_msg = Message(last_modified, etag)

        if request_msg < self.last_message:
            message = yield self.store.get(last_modified, etag)
            callback(message)
        else:
            def _cb(message):
                if request_msg >= message:
                    # We still have to wait
                    self.subscribe(id_subscriber, _cb)
                else:
                    callback(message)
            self.subscribe(id_subscriber, _cb)
