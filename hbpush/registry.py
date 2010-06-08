from hbpush.message import Message
from hbpush.channel import Channel


class Registry(object):
    def __init__(self, store):
        self.store = store
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
                    channel = Channel(id, self.store)
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
                    channel = Channel(id, self.store)
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

