from tornado.web import asynchronous, HTTPError
from hbpush.pubsub import PubSubHandler

from email.utils import formatdate, parsedate_tz, mktime_tz

class Subscriber(PubSubHandler):
    @asynchronous
    def get(self, channel_id):
        try:
            etag = int(self.request.headers.get('If-None-Match', -1))
            last_modified = int('If-Modified-Since' in self.request.headers and mktime_tz(parsedate_tz(self.request.headers['If-Modified-Since'])) or 0)
        except:
            raise HTTPError(400)

        @self.async_callback
        def _process_message(message):
            self.set_header('Etag', message.etag)
            self.set_header('Last-Modified', formatdate(message.last_modified, localtime=False, usegmt=True))
            self.add_vary_header()
            self.set_header('Content-Type', message.content_type)
            self.write(message.body)
            self.finish()
        
        @self.async_callback
        def _process_channel(channel):
            self.channel = channel
            self.channel.get(id(self), last_modified, etag, callback=_process_message, errback=self.errback)

        self.registry.get(channel_id, callback=_process_channel, errback=self.errback)


    def on_connection_close(self):
        if hasattr(self, 'channel'):
            self.channel.unsubscribe(id(self))
