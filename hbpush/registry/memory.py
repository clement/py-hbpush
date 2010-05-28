from hbpush.registry import BaseRegistry

class MemoryRegistry(BaseRegistry):
    def __init__(self, *args, **kwargs):
        super(MemoryRegistry, self).__init__(*args, **kwargs)
        self.channels = {}

    def get_channel(self, name):
        return setdefault(self.channels, name, self.channel_cls())
