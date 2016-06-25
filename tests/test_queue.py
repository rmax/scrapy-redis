import mock

from scrapy import Spider
from scrapy.http import Request

from scrapy_redis.queue import Base


class TestBaseQueue(object):

    def setup(self):
        self.server = mock.Mock()
        self.spider = Spider(name='foo')
        self.spider.parse_method = lambda x: x
        self.key = 'key'
        self.q = Base(self.server, self.spider, self.key)

    def test_encode_decode_requests(self):
        req = Request('http://example.com',
                      callback=self.spider.parse,
                      meta={'foo': 'bar'})
        out = self.q._decode_request(self.q._encode_request(req))
        assert req.url == out.url
        assert req.meta == out.meta
        assert req.callback == out.callback
