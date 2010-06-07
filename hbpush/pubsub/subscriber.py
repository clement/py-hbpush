from tornado.web import asynchronous, HTTPError
from hbpush.pubsub import PubSubHandler
from hbpush.channel import Channel

from email.utils import formatdate, parsedate_tz, mktime_tz
from functools import partial

class Subscriber(PubSubHandler):
    @asynchronous
    def get(self, channel_id):
        try:
            etag = int(self.request.headers.get('If-None-Match', -1))
            last_modified = int('If-Modified-Since' in self.request.headers and mktime_tz(parsedate_tz(self.request.headers['If-Modified-Since'])) or 0)
        except:
            raise HTTPError(400)

        self.registry.get(channel_id,
            callback=self.async_callback(partial(self._process_channel, last_modified, etag)),
            errback=self.errback)

    def _process_message(self, message):
        self.set_header('Etag', message.etag)
        self.set_header('Last-Modified', formatdate(message.last_modified, localtime=False, usegmt=True))
        self.add_vary_header()
        self.set_header('Content-Type', message.content_type)
        self.write(message.body)
        self.finish()
        
    def _process_channel(self, last_modified, etag, channel):
        channel.get(last_modified, etag,
            callback=self.async_callback(self._process_message),
            errback=self.errback)


class LongPollingSubscriber(Subscriber):
    def unsubscribe(self):
        if hasattr(self, 'channel'):
            self.channel.unsubscribe(id(self))
    on_connection_close = unsubscribe

    def finish(self):
        self.unsubscribe()
        super(LongPollingSubscriber, self).finish()

    def _process_channel(self, last_modified, etag, channel):
        @self.async_callback
        def _wait_for_message(error):
            if error.__class__ == Channel.NotModified:
                self.channel.wait_for(last_modified, etag, id(self), callback=self.async_callback(self._process_message), errback=self.errback)
            else:
                self.errback(error)
        
        self.channel = channel
        self.channel.get(last_modified, etag,
            callback=self.async_callback(self._process_message),
            errback=_wait_for_message)
