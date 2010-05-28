class Message(object):
    def __init__(self, last_modified=0, etag=0, content_type='', body=''):
        self.last_modified = last_modified
        self.etag = etag
        self.content_type = content_type
        self.body = body

    def __cmp__(self, other):
        return cmp((self.last_modified, self.etag), (other.last_modified, other.etag))
