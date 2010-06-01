class Store(object):
    def get(self, channel_id, last_modified, etag, callback, errback):
        raise NotImplementedError("")

    def post(self, channel_id, message, callback, errback):
        raise NotImplementedError("")

    def flush(self, channel_id, callback, errback):
        raise NotImplementedError("")
