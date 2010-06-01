import logging
from hbpush.channel import Channel, ChannelRegistry
from hbpush.message import Message


class MemoryChannelRegistry(ChannelRegistry):
    def __init__(self, *args, **kwargs):
        super(MemoryChannelRegistry, self).__init__(*args, **kwargs)
        self.channels = {}

    def get(self, id, callback, errback):
        try:
            callback(self.channels[id])
        except KeyError:
            errback(Channel.DoesNotExist())

    def create(self, id, callback, errback, overwrite=False):
        if not overwrite and id in self.channels:
            errback(Channel.Duplicate())
        else:
            channel = self.channel_cls(self.store)
            self.channels[id] = channel
            callback(channel)

    def get_or_create(self, id, callback, errback):
        if id not in self.channels:
            self.channels[id] = self.channel_cls(self.store)
        callback(self.channels[id])

    def delete(self, id, callback, errback):
        try:
            channel = self.channels.pop(id)
            callback(channel.delete())
        except KeyError:
            errback(Channel.DoesNotExist())

class MemoryChannel(Channel):
    def __init__(self, *args, **kwargs):
        super(MemoryChannel, self).__init__(*args, **kwargs)
        self.subscribers = {}
        # Empty message, we just want to keep etag and lastmodified data
        self.last_message = Message(0, -1)


    def get_last_message(self):
        return self.last_message

    def send_to_subscribers(self, message):
        subs = self.subscribers.copy()
        self.subscribers = {}
        for (id_subscriber, (cb, eb)) in subs.items():
            try:
                cb(message)
            except:
                logging.error("Error sending message to subscriber", exc_info=True)

    def post(self, content_type, body, callback, errback):
        def _process_message(message):
            # We work on a copy to deal with reentering subscribers
            self.send_to_subscribers(message)
            self.last_message = Message(message.last_modified, message.etag)
            # Give back control to the handler with the result of the store
            callback(message)
            
        message = self.make_message(content_type, body)
        self.store.post(message, callback=_process_message, errback=errback)

    def wait_for(self, last_modified, etag, id_subscriber, callback, errback):
        request_msg = Message(last_modified, etag)

        def _cb(message):
            if request_msg >= message:
                self.subscribe(id_subscriber, _cb, errback)
            else:
                callback(message)

        self.subscribe(id_subscriber, _cb, errback)

    def subscribe(self, id_subscriber, callback, errback):
        self.subscribers[id_subscriber] = (callback, errback)

    def unsubscribe(self, id_subscriber):
        self.subscribers.pop(id_subscriber, None)

    def get(self, last_modified, etag, callback, errback):
        request_msg = Message(last_modified, etag)

        if request_msg < self.last_message:
            self.store.get(last_modified, etag, callback=callback, errback=errback)
        else:
            errback(Channel.NotModified())

    def delete(self):
        for id, (cb, eb) in self.subscribers.items():
            try:
                eb(Channel.Gone())
            except:
                logging.error("Error disconnecting subscribers after channel deletion", exc_info=True)
        # Just for the record
        self.subscribers = {}
