from tests.handlers import *
from tests.base import TornadoTestCase
from hbpush.store.redis import RedisStore
from hbpush.registry import Registry


class RedisHandlerTestCase(BaseHandlerTestCase, TornadoTestCase):
    """TestCase using a RedisStore for message storage and retrieval"""

    def setUp(self):
        super(RedisHandlerTestCase, self).setUp()

        # Clean the store
        self.store = RedisStore(io_loop=self.io_loop)
        self.store.flushall(lambda _: self.io_loop.stop(), lambda e: None)
        self.io_loop.start()

        # Create a brand new registry!
        self.registry = Registry(self.store)

    def test_store_filling(self):
        """Test that the store is correctly filled by successive POST to a channel,
           and correctly deleted with a DELETE request"""

        channel_id = 'store_filling'
        self.execute(
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
        )

        self.store.client.zcard(channel_id, (lambda (_,x): self.assertEquals(x, 3), self.finish))
        self.start()

        self.execute(
            self.publisher('DELETE', channel_id, cb=self.expect(200)),
        )

        self.store.client.zcard(channel_id, (lambda (_,x): self.assertEquals(x, 0), self.finish))
        self.start()


    def test_race_store_create(self):
        """Test for a race condition that used to happen when multiple requests
           where creating the channel at the same time"""

        channel_id = 'race_store_create'
        self.execute(
            par(
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
                self.publisher('POST', channel_id, headers=(ct_textplain,), body=hello_world, cb=self.expect(202)),
            )
        )

        self.store.client.zcard(channel_id, (lambda (_,x): self.assertEquals(x, 9), self.finish))
        self.start()
