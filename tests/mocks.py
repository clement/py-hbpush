from hbpush.pubsub.publisher import Publisher
from hbpush.pubsub.subscriber import Subscriber, LongPollingSubscriber
from tornado.httpserver import HTTPHeaders, HTTPRequest
from tornado.web import HTTPError
from tornado.ioloop import IOLoop

def decorate_method(method):
    def _new_method(self, channel_id, expect, next):
        self.expect = expect
        self.next = next
        try:
            getattr(super(MockHandler, self), method)(channel_id)
        except Exception, e:
            self._handle_request_exception(e)
    return _new_method

class MockHandler(object):
    def __init__(self, *args, **kwargs):
        super(MockHandler, self).__init__(*args, **kwargs)
        self._write_buf = ''

    delete = decorate_method('delete')
    get = decorate_method('get')
    post = decorate_method('post')
    put = decorate_method('put')

    def write(self, data):
        assert not self._finished
        self._write_buf += data

    def flush(self, *args, **kwargs):
        pass

    def _log(self, *args, **kwargs):
        pass

    def finish(self, *args, **kwargs):
        super(MockHandler, self).finish(*args, **kwargs)

        # Here we test expectations
        for callback in self.expect:
            callback(self._status_code, self._headers, self._write_buf)
        self.next()

    def _handle_request_exception(self, e):
        if isinstance(e, HTTPError):
            super(MockHandler, self)._handle_request_exception(e)
        else:
            raise e


class MockPublisher(MockHandler, Publisher):
    pass

class MockSubscriber(MockHandler, Subscriber):
    pass

class MockLongPollingSubscriber(MockHandler, LongPollingSubscriber):
    pass


class MockApplication(object):
    ui_modules = {}
    ui_methods = {}
    _wsgi = False

class MockRequest(object):
    def request_time(self):
        import time
        return time.time()

    def supports_http_1_1(self):
        return True

    uri = ''
    remote_ip = '127.0.0.1'

    def __init__(self, method='GET', channel=None, headers=None, body='', cb=(), handler=None, **kwargs):
        self.method = method
        self.channel = channel
        self.callbacks = hasattr(cb, '__iter__') and tuple(cb) or (cb,)
        self.handler = handler
        self.body = body
        self.kwargs = kwargs
        self.headers_in = headers

    def __call__(self, next):
        self.headers = HTTPHeaders()
        if self.headers_in:
            for name, val in [h.split(': ') for h in self.headers_in]:
                self.headers[name] = val

        app = MockApplication()
        getattr(self.handler(app, self, **self.kwargs), self.method.lower())(self.channel, self.callbacks, next)

    def finish(self, *args, **kwargs):
        pass


class MockIOLoop(IOLoop):
    def handle_callback_exception(self, callback):
        import sys
        (type, value, traceback) = sys.exc_info()
        raise type, value, traceback
