import mock

from scrapy import Spider
from scrapy.http import Request

from scrapy_redis.queue import Base


class TestBaseQueue(object):

    queue_cls = Base

    def setup(self):
        self.server = mock.Mock()
        self.spider = Spider(name='foo')
        self.spider.parse_method = lambda x: x
        self.key = 'key'
        self.q = self.queue_cls(self.server, self.spider, self.key)

    def test_encode_decode_requests(self, q=None):
        if q is None:
            q = self.q
        req = Request('http://example.com',
                      callback=self.spider.parse,
                      meta={'foo': 'bar'})
        out = q._decode_request(q._encode_request(req))
        assert req.url == out.url
        assert req.meta == out.meta
        assert req.callback == out.callback

    def test_custom_serializer(self):
        serializer = mock.Mock()
        serializer.dumps = mock.Mock(side_effect=lambda x: x)
        serializer.loads = mock.Mock(side_effect=lambda x: x)
        q = Base(self.server, self.spider, self.key, serializer=serializer)
        self.test_encode_decode_requests(q)
        assert serializer.dumps.call_count == 1
        assert serializer.loads.call_count == 1
