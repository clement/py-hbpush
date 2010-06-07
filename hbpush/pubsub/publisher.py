from tornado.web import asynchronous
from hbpush.pubsub import PubSubHandler
from hbpush.channel import Channel

class Publisher(PubSubHandler):
    def __init__(self, *args, **kwargs):
        self.create_on_post = kwargs.pop('create_on_post', True)
        super(Publisher, self).__init__(*args, **kwargs)

    @asynchronous
    def post(self, channel_id):
        # Write a summary of the post to the publisher
        @self.async_callback
        def _write_response(message):
            self.write('Written: (%d) (%d) %s' % (message.last_modified, message.etag, message.body))
            self.finish()

        # the channel is ok, write a message to it
        @self.async_callback
        def _post_message(channel):
            channel.post(self.request.headers['Content-Type'], self.request.body, callback=_write_response, errback=self.errback)

        if self.create_on_post:
            func = self.registry.get_or_create
        else:
            func = self.registry.get

        func(channel_id, callback=_post_message, errback=self.errback)


    @asynchronous
    def put(self, channel_id):
        @self.async_callback
        def _channel_error(error):
            if error.__class__ != Channel.Duplicate:
                raise error
            self.simple_finish()

        self.registry.create(channel_id, callback=self.simple_finish, errback=_channel_error)


    @asynchronous
    def get(self, channel_id):
        @self.async_callback
        def _print_info(channel):
            self.write("Channel %s with last message %s" % (channel.id, channel.last_message))
            self.finish()

        self.registry.get(channel_id, callback=_print_info, errback=self.errback)

    
    @asynchronous
    def delete(self, channel_id):
        self.registry.delete(channel_id, callback=self.simple_finish, errback=self.errback)
