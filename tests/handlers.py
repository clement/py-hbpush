# -coding: utf8
from tests.mocks import *
from tests.base import seq, par

ct_textplain = 'Content-Type: text/plain'
ct_json = 'Content-Type: application/json'
hello_world = 'hello world!'


class BaseHandlerTestCase(object):
    """base class for hbpush tests. Subclasses should create a concrete message store
       to test on"""

    ## Shortcuts for creating requests
    def publisher(self, *args, **kwargs):
        """create a MockRequest with a MockPublisher as default handler, and with
           the current test case registry"""

        default_kwargs = {'handler': MockPublisher, 'registry': self.registry}
        default_kwargs.update(kwargs)
        return MockRequest(*args, **default_kwargs)

    def subscriber(self, *args, **kwargs):
        """create a MockRequest with a MockSubscriber as default handler, and with
           the current test case registry"""

        default_kwargs = {'handler': MockSubscriber, 'registry': self.registry}
        default_kwargs.update(kwargs)
        return MockRequest(*args, **default_kwargs)

    def long_subscriber(self, *args, **kwargs):
        """create a MockRequest with a MockLongPollingSubscriber as default handler, and with
           the current test case registry"""

        default_kwargs = {'handler': MockLongPollingSubscriber, 'registry': self.registry}
        default_kwargs.update(kwargs)
        return MockRequest(*args, **default_kwargs)

    ## Common test methods
    def test_delete_basic(self):
        """Test basic deletion functionnality"""

        channel_id = 'delete_basic'
        self.execute(
            # Delete a non-existing channel
            self.publisher('DELETE', channel_id, cb=self.expect(404)),
            # Create a channel, then delete it
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            self.publisher('DELETE', channel_id, cb=self.expect(200)),
        )

    def test_delete_gone(self):
        """Test that long polling subscribers get a 410 Gone response when the channel they were waiting
           on is deleted"""

        channel_id = 'delete_gone'
        self.execute(
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            par(
                self.long_subscriber('GET', channel_id, cb=self.expect(410)),
                self.publisher('DELETE', channel_id, cb=self.expect(200)),
            ),
        )

    def test_create(self):
        """Test that we can create a channel, and double PUT on it won't complain"""

        channel_id = 'create'
        self.execute(
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            self.publisher('PUT', channel_id, cb=self.expect(200)),
        )

    def test_create_on_post(self):
        """Test that a publisher location can't create a channel with a POST when create_on_post option
           is set to False"""

        channel_id = 'create_on_post'
        self.execute(
            self.publisher('POST', channel_id, headers=(ct_textplain,), create_on_post=False, cb=self.expect(404)),
            self.publisher('PUT', channel_id, create_on_post=False, cb=self.expect(200)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), create_on_post=False, cb=self.expect(202)),
            # Now delete the channel, and create it with a POST
            self.publisher('DELETE', channel_id, cb=self.expect(200)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), cb=self.expect(202)),
        )

    def test_post_subscribers(self):
        """Test thath publishers receive the right HTTP status code when posting a message,
           201 when there was subscribers to whom the message has been sent to,
           202 otherwise"""

        channel_id = 'post_subscribers'
        self.execute(
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            par(
                self.long_subscriber('GET', channel_id, cb=self.expect(200)),
                self.long_subscriber('GET', channel_id, cb=self.expect(200)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), cb=self.expect(201)),
            ),
            self.publisher('POST', channel_id, headers=(ct_textplain,), cb=self.expect(202)),
        )

    def test_content_type(self):
        """Test that we get back the correct content-type when retrieving a posted message"""

        channel_id = 'content_type_%d'
        self.execute(
            self.publisher('POST', channel_id % 1, headers=(ct_textplain,), cb=self.expect(202)),
            self.subscriber('GET', channel_id % 1, cb=self.expect(200, (ct_textplain,))),
            self.publisher('POST', channel_id % 2, headers=(ct_json,), cb=self.expect(202)),
            self.subscriber('GET', channel_id % 2, cb=self.expect(200, (ct_json,))),
        )

    def test_subscriber_basic(self):
        """Test for a single message use-cases, not found if the channel has not been created,
           not modified if no message found, posted content otherwise"""

        channel_id = 'subscriber_basic'
        self.execute(
            self.subscriber('GET', channel_id, cb=self.expect(404)),
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            self.subscriber('GET', channel_id, cb=self.expect(304)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            self.subscriber('GET', channel_id, cb=self.expect(200, headers=(ct_textplain,), body=hello_world)),
        )

    def test_malformed_request(self):
        """Test that subscribers will get a 400 error if they send invalid request headers"""
        channel_id = 'malformed_request'
        self.execute(
            self.subscriber('GET', channel_id, headers=('If-None-Match: abcd',), cb=self.expect(400)),
            self.subscriber('GET', channel_id, headers=('If-Modified-Since: abcd',), cb=self.expect(400)),
            self.long_subscriber('GET', channel_id, headers=('If-None-Match: abcd',), cb=self.expect(400)),
            self.long_subscriber('GET', channel_id, headers=('If-Modified-Since: abcd',), cb=self.expect(400)),
        )

    def test_binary_string_id(self):
        """Test that binary-string are accepted for channel ids, and that we can do all the chain of
           PUT/POST/GET/DELETE without problem"""

        channel_id = 'abc é\nfg\thi\0po'
        self.execute(
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            self.subscriber('GET', channel_id, cb=self.expect(200, headers=(ct_textplain,), body=hello_world)),
            self.long_subscriber('GET', channel_id, cb=self.expect(200, headers=(ct_textplain,), body=hello_world)),
            self.publisher('DELETE', channel_id, cb=self.expect(200)),
        )


    def test_subscriber_chain(self):
        """Test that we are able to retrieve a set of messages in order, using etag and last
           modified dates"""

        channel_id = 'subscriber_chain'
        request_headers = []
        def _pass_headers(status, headers, body):
            request_headers.append('If-Modified-Since: %s' % headers['Last-Modified'])
            request_headers.append('If-None-Match: %s' % headers['Etag'])

        self.execute(
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world+'1', cb=self.expect(202)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world+'2', cb=self.expect(202)),
            self.subscriber('GET', channel_id, cb=(self.expect(200, headers=(ct_textplain,), body=hello_world), _pass_headers)),
            self.subscriber('GET', channel_id, headers=request_headers, cb=(self.expect(200, headers=(ct_textplain,), body=hello_world+'1'), _pass_headers)),
            self.subscriber('GET', channel_id, headers=request_headers, cb=(self.expect(200, headers=(ct_textplain,), body=hello_world+'2'), _pass_headers)),
        )

    def test_long_subscriber(self):
        """Test that a long polling subscriber will get a message as soon as it is available"""
        
        channel_id = 'long_subscriber'
        request_headers = []
        def _pass_headers(status, headers, body):
            request_headers.append('If-Modified-Since: %s' % headers['Last-Modified'])
            request_headers.append('If-None-Match: %s' % headers['Etag'])

        self.execute(
            self.publisher('PUT', channel_id, cb=self.expect(200)),
            par(
                self.long_subscriber('GET', channel_id, cb=self.expect(200, (ct_textplain,), hello_world)),
                self.long_subscriber('GET', channel_id, cb=(self.expect(200, (ct_textplain,), hello_world), _pass_headers)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(201)),
            ),
            par(
                self.long_subscriber('GET', channel_id, headers=request_headers, cb=self.expect(200, (ct_textplain,), hello_world+'1')),
                self.long_subscriber('GET', channel_id, headers=request_headers, cb=(self.expect(200, (ct_textplain,), hello_world+'1'), _pass_headers)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world+'1', cb=self.expect(201)),
            ),
        )

