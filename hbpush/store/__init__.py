class Store(object):
    def get(self, last_modified, etag, callback):
        raise NotImplementedError("")

    def post(self, message, callback):
        raise NotImplementedError("")
