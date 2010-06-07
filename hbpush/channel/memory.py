import logging
from hbpush.channel import Channel, ChannelRegistry
from hbpush.message import Message


class MemoryChannelRegistry(ChannelRegistry):
    def __init__(self, *args, **kwargs):
        super(MemoryChannelRegistry, self).__init__(*args, **kwargs)
        self.channels = {}
        self.get_request = {}

    def get(self, id, callback, errback):
        try:
            callback(self.channels[id])
        except KeyError:
            # Try to get the channel from the store to populate
            # the cache.
            # We might not be the first ones to do that
            reqs = self.get_request.get(id, ())
            if len(reqs):
                self.get_request[id].append((callback, errback))
            else:
                def _cache_channel(message):
                    channel = self.channel_cls(id, self.store)
                    channel.last_message = message
                    self.channels[id] = channel
                    for (cb, _) in self.get_request[id]:
                        cb(channel)
                    del self.get_request[id]
                def _no_message(error):
                    if error.__class__ == Message.DoesNotExist:
                        error = Channel.DoesNotExist()
                    for (_, eb) in self.get_request[id]:
                        eb(error)
                    del self.get_request[id]

                self.get_request[id] = [(callback, errback),]
                self.store.get_last(id, _cache_channel, _no_message)


    def create(self, id, callback, errback):
        def _no_channel(error):
            if error.__class__ == Channel.DoesNotExist:
                # someone might have populated the cache in between
                if id in self.channels:
                    errback(Channel.Duplicate())
                else:
                    channel = self.channel_cls(id, self.store)
                    self.channels[id] = channel
                    callback(channel)
            else:
                errback(error)

        def _got_channel(channel):
            errback(Channel.Duplicate())

        self.get(id, _got_channel, _no_channel)


    def get_or_create(self, id, callback, errback):
        def _duplicate(error):
            if error.__class__ == Channel.Duplicate:
                callback(self.channels[id])
            else:
                errback(error)
        self.create(id, callback, _duplicate)


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
        # We work on a copy to deal with reentering subscribers
        subs = self.subscribers.copy()
        self.subscribers = {}
        nb = 0
        for (id_subscriber, (cb, eb)) in subs.items():
            try:
                cb(message)
                nb += 1
            except:
                logging.error("Error sending message to subscriber", exc_info=True)
        return nb

    def post(self, content_type, body, callback, errback):
        def _process_message(message):
            nb_subscribers = self.send_to_subscribers(message)
            # This piece assumes we will always get to that callback in the order
            # we posted messages
            assert self.last_message < message
            self.last_message = Message(message.last_modified, message.etag)
            # Give back control to the handler with the result of the store
            callback((message, nb_subscribers))
            
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
