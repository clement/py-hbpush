from tornado.web import RequestHandler, Application, asynchronous, HTTPError
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from hbpush.pubsub.publisher import Publisher
from hbpush.pubsub.subscriber import Subscriber, LongPollingSubscriber

from hbpush.channel.memory import MemoryChannel, MemoryChannelRegistry
from hbpush.store.redis import RedisStore
from hbpush.store.memory import MemoryStore

registry = MemoryChannelRegistry(MemoryChannel, RedisStore())

application = Application([(r"/pub/(.+)", Publisher, {'registry':registry}), (r"/sub/(.+)", LongPollingSubscriber, {'registry':registry}),])
http_server = HTTPServer(application)
http_server.listen(9090)
IOLoop.instance().start()
