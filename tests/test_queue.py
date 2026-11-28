from unittest import mock

import pytest
from scrapy import Spider
from scrapy.http import Request

from scrapy_redis.queue import Base, FifoQueue


class TestBaseQueue:

    queue_cls = Base

    def setup(self):
        self.server = mock.Mock()
        self.spider = Spider(name="foo")
        self.spider.parse_method = lambda x: x
        self.key = "key"
        self.q = self.queue_cls(self.server, self.spider, self.key)

    def test_encode_decode_requests(self, q=None):
        if q is None:
            q = self.q
        req = Request(
            "http://example.com", callback=self.spider.parse, meta={"foo": "bar"}
        )
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


def module_level_callback(response):
    pass


class TestUnserializableRequests:

    def setup_method(self):
        self.server = mock.Mock()
        self.spider = Spider(name="foo")
        self.q = FifoQueue(self.server, self.spider, "key")

    def test_callback_not_spider_method(self):
        req = Request("http://example.com", callback=module_level_callback)
        with pytest.raises(ValueError):
            self.q.push(req)
        self.server.lpush.assert_not_called()

    def test_unpicklable_meta(self):
        req = Request("http://example.com", meta={"fn": lambda x: x})
        with pytest.raises(ValueError):
            self.q.push(req)
        self.server.lpush.assert_not_called()

    def test_serializer_type_error_is_normalized(self):
        serializer = mock.Mock()
        serializer.dumps = mock.Mock(side_effect=TypeError("nope"))
        q = FifoQueue(self.server, self.spider, "key", serializer=serializer)
        with pytest.raises(ValueError):
            q.push(Request("http://example.com"))
        self.server.lpush.assert_not_called()

    def test_undeserializable_request_class(self):
        class LocalRequest(Request):
            pass

        with pytest.raises(ValueError):
            self.q.push(LocalRequest("http://example.com"))
        self.server.lpush.assert_not_called()

    def test_normal_request_is_pushed(self):
        self.q.push(Request("http://example.com"))
        assert self.server.lpush.call_count == 1
