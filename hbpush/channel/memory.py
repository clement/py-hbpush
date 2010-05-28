import logging
from hbpush.channel import Channel
from hbpush.message import Message

class MemoryChannel(Channel):
    channels = {}

    def __init__(self, *args, **kwargs):
        super(MemoryChannel, self).__init__(*args, **kwargs)
        self.subscribers = []
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

    def post(self, content_type, body, callback):
        message = self.make_message(content_type, body)
        def _notify(message):
            if message is not None: # No error when storing
                # We work on a copy to deal with reentering subscribers
                subs = self.subscribers[:]
                self.subscribers = []
                for cb in subs:
                    try:
                        cb(message)
                    except:
                        logging.error("Error sending message to subscriber", exc_info=True)
                self.last_message = Message(message.last_modified, message.etag)
            # Give back control to the handler with the result of the store
            callback(message)
        self.store.post(message, _notify)

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def get(self, last_modified, etag, callback):
        request_msg = Message(last_modified, etag)

        if request_msg < self.last_message:
            self.store.get(last_modified, etag, callback)
        else:
            def _cb(message):
                if request_msg >= message:
                    # We still have to wait
                    self.subscribe(_cb)
                else:
                    callback(message)
            self.subscribe(_cb)
