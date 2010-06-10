from hbpush.store import Store
from hbpush.message import Message
from hbpush.utils.redis import AutoClient as Client
from hbpush.utils.message import make_score, parse_redis_message

from email.utils import formatdate
from functools import partial
import struct


class RedisStore(Store):
    def __init__(self, **kwargs):
        self.key_prefix = kwargs.pop('key_prefix', '')
        self.client = Client(**kwargs)
        self.client.connect()

    def _get_message(self, callback, errback, data):
        if len(data) == 0:
            errback(Message.DoesNotExist())
        else:
            try:
                callback(parse_redis_message(data[0]))
            except Message.Invalid, e:
                errback(e)
        

    def get(self, channel_id, last_modified, etag, callback, errback):
        score = make_score(last_modified, etag)
        # If an etag is set, we have to make the range request exclusive
        if etag >= 0:
            score = '('+score

        self.client.zrangebyscore(self.make_key(channel_id), score, '+inf', 0, 1,
            callbacks=partial(self._on_result, partial(self._get_message, callback, errback), errback))

    def get_last(self, channel_id, callback, errback):
        self.client.zrevrange(self.make_key(channel_id), 0, 0, False, partial(self._on_result, partial(self._get_message, callback, errback), errback))
        
    def post(self, channel_id, message, callback, errback):
        (score, data) = self.make_message(message)
        self.client.zadd(self.make_key(channel_id), score, data, partial(self._on_result, lambda x: callback(message), errback))

    def flush(self, channel_id, callback, errback):
        self.client.delete(self.make_key(channel_id), partial(self._on_result, lambda x: callback(True), errback))

    def flushall(self, callback, errback):
        self.client.flushdb(partial(self._on_result, lambda x: callback(True), errback))


    def make_key(self, channel_id):
        return ''.join((self.key_prefix, channel_id))

    def make_message(self, message):
        return (make_score(message.last_modified, message.etag),
            ('Last-Modified: %s\r\n' % formatdate(message.last_modified, localtime=False, usegmt=True))+
            ('Content-Type: %s\r\n' % message.content_type)+
            ('Etag: %d\r\n\r\n' % message.etag)+
            message.body
        )

    def _on_result(self, callback, errback, result):
        (error, data) = result
        if error:
            errback(error)
        else:
            callback(data)
