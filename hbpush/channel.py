from hbpush.message import Message
import logging
import time


class Channel(object):

    class DoesNotExist(Exception):
        pass
    class Duplicate(Exception):
        pass
    class Gone(Exception):
        pass
    class NotModified(Exception):
        pass

    def __init__(self, id, store):
        self.store = store
        self.id = id
        self.sentinel = None
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
            cb(message)
            nb += 1
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
            eb(Channel.Gone())
        # Just for the record
        self.subscribers = {}

        # Delete all messages from the store
        self.store.flush(self.id, callback, errback)

    def make_message(self, content_type, body):
        if not self.sentinel:
            self.sentinel = self.get_last_message()

        last_modified = int(time.time())
        if last_modified == self.sentinel.last_modified:
            etag = self.sentinel.etag+1
        else:
            etag = 0

        self.sentinel = Message(last_modified, etag, content_type, body)
        return self.sentinel


