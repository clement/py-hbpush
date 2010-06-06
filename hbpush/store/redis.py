from hbpush.store import Store
from hbpush.message import Message
from hbpush.utils.redis import AutoClient as Client

from email.utils import formatdate, parsedate_tz, mktime_tz
from functools import partial


class RedisStore(Store):
    PRECISION = 5

    def __init__(self):
        self.client = Client()
        self.client.connect()

    def _get_message(self, callback, errback, data):
        if len(data) == 0:
            errback(Message.DoesNotExist())
        else:
            try:
                callback(self.parse_message(data[0]))
            except:
                errback(Message.Invalid())
        

    def get(self, channel_id, last_modified, etag, callback, errback):
        score = self.make_score(Message(last_modified, etag))
        # If an etag is set, we have to make the range request exclusive
        if etag >= 0:
            score = '('+score

        self.client.zrangebyscore(channel_id, score, '+inf', 0, 1,
            callbacks=partial(self._on_result, partial(self._get_message, callback, errback), errback))

    def get_last(self, channel_id, callback, errback):
        self.client.zrevrange(channel_id, 0, 0, False, partial(self._on_result, partial(self._get_message, callback, errback), errback))
        
    def post(self, channel_id, message, callback, errback):
        (score, data) = self.make_message(message)
        self.client.zadd(channel_id, score, data, partial(self._on_result, lambda x: callback(message), errback))

    def flush(self, channel_id, callback, errback):
        self.client.delete(channel_id, partial(self._on_result, lambda x: callback(True), errback))


    def make_score(self, message):
        return '{{0:d}}.{{1:0{0}d}}'.format(self.PRECISION).format(message.last_modified, message.etag > 0 and message.etag or 0)

    def make_message(self, message):
        return (self.make_score(message),
            ('Last-Modified: %s\r\n' % formatdate(message.last_modified, localtime=False, usegmt=True))+
            ('Content-Type: %s\r\n' % message.content_type)+
            ('Etag: %d\r\n\r\n' % message.etag)+
            message.body
        )

    def parse_message(self, payload):
        headers, body = payload.split('\r\n'*2, 1)
        headers = dict(map(lambda h: h.split(': ', 1), headers.split('\r\n')))
        return Message(mktime_tz(parsedate_tz(headers['Last-Modified'])), int(headers['Etag']), headers['Content-Type'], body)

    def _on_result(self, callback, errback, result):
        (error, data) = result
        if error:
            errback(error)
        else:
            callback(data)
