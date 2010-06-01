from tornado.web import asynchronous
from hbpush.pubsub import PubSubHandler

class Publisher(PubSubHandler):
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

        self.registry.get_or_create(channel_id, callback=_post_message, errback=self.errback)


    @asynchronous
    def put(self, channel_id):
        @self.async_callback
        def _channel_error(error):
            if error.__class__ != Channel.Duplicate:
                raise error

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
