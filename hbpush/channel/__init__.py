from hbpush.message import Message
import time


class ChannelRegistry(object):
    def __init__(self, channel_cls, store):
        self.channel_cls = channel_cls
        self.store = store

    def get(self, id, callback, errback):
        raise NotImplementedError("")
        
    def create(self, id, callback, errback, overwrite=False):
        raise NotImplementedError("")

    def get_or_create(self, id, callback, errback):
        raise NotImplementedError("")
        
    def delete(self, id, callback, errback):
        raise NotImplementedError("")
        

class Channel(object):
    def __init__(self, store):
        self.store = store

    def post(self, message, callback):
        raise NotImplementedError("")

    def get(self, last_modified, etag, callback):
        raise NotImplementedError("")

    def get_last_message(self):
        raise NotImplementedError("")
        
    def subscribe(self, id_subscriber, callback):
        raise NotImplementedError("")

    def unsubscribe(self, id_subscriber):
        raise NotImplementedError("")

    def make_message(self, content_type, body):
        last_message = self.get_last_message()

        last_modified = int(time.time())
        if last_modified == last_message.last_modified:
            etag = last_message.etag+1
        else:
            etag = 0

        return Message(last_modified, etag, content_type, body)


    class DoesNotExist(Exception):
        pass

    class Duplicate(Exception):
        pass

    class Gone(Exception):
        pass
