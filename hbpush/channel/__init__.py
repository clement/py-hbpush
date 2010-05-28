from hbpush.message import Message
import time

class Channel(object):
    store = None

    @classmethod
    def get_by_id(cls, id):
        raise NotImplementedError("")
        
    @classmethod
    def create(cls, id, overwrite=False):
        raise NotImplementedError("")

    def post(self, message, callback):
        raise NotImplementedError("")

    def get(self, last_modified, etag, callback):
        raise NotImplementedError("")

    def get_last_message(self):
        raise NotImplementedError("")
        
    def subscribe(self, callback):
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


