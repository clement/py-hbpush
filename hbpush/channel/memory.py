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
            def _cb(message):
                channel = self.channel_cls(id, self.store)
                channel.last_message = message
                self.channels[id] = channel
                callback(channel)
            def _eb(error):
                if error.__class__ == Message.DoesNotExist:
                    error = Channel.DoesNotExist()
                errback(error)
            self.store.get_last(id, _cb, _eb)


    def create(self, id, callback, errback, overwrite=False):
        def _create():
            channel = self.channel_cls(id, self.store)
            self.channels[id] = channel
            callback(channel)

        def _cb(channel):
            if not overwrite:
                errback(Channel.Duplicate())
            else:
                _create()

        def _eb(error):
            # A good thing, we actually need an error
            if error.__class__ == Channel.DoesNotExist:
                _create()
            else:
                errback(error)

        self.get(id, _cb, _eb)


    def get_or_create(self, id, callback, errback):
        def _eb(error):
            if error.__class__ == Channel.DoesNotExist:
                self.create(id, callback, errback)
            else:
                errback(error)

        self.get(id, callback, _eb)


    def delete(self, id, callback, errback):
        def _delete(channel):
            self.channels.pop(id)
            channel.delete(callback, errback)
        self.get(id, _delete, errback)


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
        self.store.post(self.id, message, callback=_process_message, errback=errback)

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
            self.store.get(self.id, last_modified, etag, callback=callback, errback=errback)
        else:
            errback(Channel.NotModified())

    def delete(self, callback, errback):
        for id, (cb, eb) in self.subscribers.items():
            try:
                eb(Channel.Gone())
            except:
                logging.error("Error disconnecting subscribers after channel deletion", exc_info=True)
        # Just for the record
        self.subscribers = {}

        # Delete all messages from the store
        self.store.flush(self.id, callback, errback)
