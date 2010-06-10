from tests.handlers import *
from tests.base import TornadoTestCase
from hbpush.store.memory import MemoryStore
from hbpush.registry import Registry


class MemoryHandlerTestCase(BaseHandlerTestCase, TornadoTestCase):
    """TestCase using a MemoryStore for message storage and retrieval"""

    def setUp(self):
        super(MemoryHandlerTestCase, self).setUp()
        self.store = MemoryStore()
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

        self.assertEquals(len(self.store.messages[channel_id]), 3)

        self.execute(
            self.publisher('DELETE', channel_id, cb=self.expect(200)),
        )

        self.assert_(channel_id not in self.store.messages)

