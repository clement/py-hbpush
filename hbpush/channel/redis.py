import logging
from hbpush.channel import Channel, ChannelRegistry
from hbpush.message import Message


class RedisChannelRegistry(ChannelRegistry):
    def __init__(self, *args, **kwargs):
        super(RedisChannelRegistry, self).__init__(*args, **kwargs)
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


    def create(self, id, callback, errback, overwrite=False, last_message=None):
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
