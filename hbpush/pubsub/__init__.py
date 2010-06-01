from tornado.web import RequestHandler, HTTPError
from hbpush.channel import Channel


class PubSubHandler(RequestHandler):
    exception_mapping = {
        Channel.DoesNotExist: 404,
        Channel.Duplicate: 409,
        Channel.Gone: 410,
    }

    def __init__(self, *args, **kwargs):
        self.registry = kwargs.pop('registry', None)
        super(PubSubHandler, self).__init__(*args, **kwargs)

    def add_vary_header(self):
        self.set_header('Vary', 'If-Modified-Since, If-None-Match')

    def _handle_request_exception(self, e):
        if e.__class__ in self.exception_mapping:
            e = HTTPError(self.exception_mapping[e.__class__], str(e))

        super(PubSubHandler, self)._handle_request_exception(e)

    errback = _handle_request_exception


    def simple_finish(self, *args, **kwargs):
        # ignore everything, and just finish the request
        self.finish()

