from hbpush.message import Message
from email.utils import parsedate_tz, mktime_tz
import struct

def make_score(last_modified, etag):
    etag = max(etag, 0)
    assert (etag >> 30) == 0
    # We return repr here not to suffer the precision rounding of str
    return repr(struct.unpack('d', struct.pack('Q', (last_modified << 30) + etag))[0])

def parse_redis_message(payload):
    try:
        headers, body = payload.split('\r\n'*2, 1)
        headers = dict(map(lambda h: h.split(': ', 1), headers.split('\r\n')))
        return Message(mktime_tz(parsedate_tz(headers['Last-Modified'])), int(headers['Etag']), headers['Content-Type'], body)
    except:
        raise Message.Invalid()
