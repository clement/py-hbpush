from tornado.web import RequestHandler, Application, asynchronous
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from hbpush.channel import Channel

from email.utils import formatdate, parsedate_tz, mktime_tz



class PubSubHandler(RequestHandler):
    def add_vary_header(self):
        self.set_header('Vary', 'If-Modified-Since, If-None-Match')

class Publisher(PubSubHandler):
    @asynchronous
    def post(self, channel_id):
        try:
            channel = channel_cls.get_by_id(channel_id)
        except Channel.DoesNotExist:
            channel = channel_cls.create(channel_id)

        channel.post(self.request.headers['Content-Type'], self.request.body, self.async_callback(self._finalize_post))

    def _finalize_post(self, message):
        self.write('Written: (%d) (%d) %s' % (message.last_modified, message.etag, message.body))
        self.finish()

class Subscriber(PubSubHandler):
    @asynchronous
    def get(self, channel_id):
        channel = channel_cls.get_by_id(channel_id)
        etag = int(self.request.headers.get('If-None-Match', 0))
        last_modified = int('If-Modified-Since' in self.request.headers and mktime_tz(parsedate_tz(self.request.headers['If-Modified-Since'])) or 0)
        # :TODO: if failure, send a bad request
        channel.get(last_modified, etag, self._finalize_get)

    def _finalize_get(self, message):
        self.set_header('Etag', message.etag)
        self.set_header('Last-Modified', formatdate(message.last_modified, localtime=False, usegmt=True))
        self.add_vary_header()
        self.set_header('Content-Type', message.content_type)
        self.write(message.body)
        self.finish()


from hbpush.channel.memory import MemoryChannel
from hbpush.store.memory import MemoryStore
channel_cls = MemoryChannel
channel_cls.store = MemoryStore()

application = Application([(r"/pub/(.+)", Publisher), (r"/sub/(.+)", Subscriber),])
http_server = HTTPServer(application)
http_server.listen(9090)
IOLoop.instance().start()
