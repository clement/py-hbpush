from tornado.web import RequestHandler, Application, asynchronous
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from brukva.adisp import process

from hbpush.channel import Channel

from email.utils import formatdate, parsedate_tz, mktime_tz



class PubSubHandler(RequestHandler):
    def add_vary_header(self):
        self.set_header('Vary', 'If-Modified-Since, If-None-Match')

class Publisher(PubSubHandler):
    @asynchronous
    @process
    def post(self, channel_id):
        try:
            channel = channel_cls.get_by_id(channel_id)
        except Channel.DoesNotExist:
            channel = channel_cls.create(channel_id)

        message = yield channel.post(self.request.headers['Content-Type'], self.request.body)
        self.write('Written: (%d) (%d) %s' % (message.last_modified, message.etag, message.body))
        self.finish()

class Subscriber(PubSubHandler):
    @asynchronous
    @process
    def get(self, channel_id):
        channel = channel_cls.get_by_id(channel_id)
        etag = int(self.request.headers.get('If-None-Match', -1))
        last_modified = int('If-Modified-Since' in self.request.headers and mktime_tz(parsedate_tz(self.request.headers['If-Modified-Since'])) or 0)
        # :TODO: if failure, send a bad request
        self.channel = channel
        message = yield channel.get(id(self), last_modified, etag)
        self.channel = None

        self.set_header('Etag', message.etag)
        self.set_header('Last-Modified', formatdate(message.last_modified, localtime=False, usegmt=True))
        self.add_vary_header()
        self.set_header('Content-Type', message.content_type)
        self.write(message.body)
        self.finish()

    def on_connection_close(self):
        if self.channel:
            self.channel.unsubscribe(id(self))


from hbpush.channel.memory import MemoryChannel
from hbpush.store.memory import MemoryStore
channel_cls = MemoryChannel
channel_cls.store = MemoryStore()

application = Application([(r"/pub/(.+)", Publisher), (r"/sub/(.+)", Subscriber),])
http_server = HTTPServer(application)
http_server.listen(9090)
IOLoop.instance().start()
