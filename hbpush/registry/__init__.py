class BaseRegistry(object):
    def __init__(self, channel_cls):
        self.channel_cls = channel_cls

    def get_channel(self, name):
        raise NotImplementedError("")
