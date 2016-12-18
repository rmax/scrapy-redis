import contextlib
import mock
import pytest

from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.settings import Settings

from scrapy_redis.spiders import (
    RedisCrawlSpider,
    RedisSpider,
)


@contextlib.contextmanager
def flushall(server):
    try:
        yield
    finally:
        server.flushall()


class MySpider(RedisSpider):
    name = 'myspider'


class MyCrawlSpider(RedisCrawlSpider):
    name = 'myspider'


def get_crawler(**kwargs):
    return mock.Mock(settings=Settings(), **kwargs)


class TestRedisMixin_setup_redis(object):

    def setup(self):
        self.myspider = MySpider()

    def test_crawler_required(self):
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "crawler" in str(excinfo.value)

    def test_requires_redis_key(self):
        self.myspider.crawler = get_crawler()
        self.myspider.redis_key = ''
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "redis_key" in str(excinfo.value)

    def test_invalid_batch_size(self):
        self.myspider.redis_batch_size = 'x'
        self.myspider.crawler = get_crawler()
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "redis_batch_size" in str(excinfo.value)

    @mock.patch('scrapy_redis.spiders.connection')
    def test_via_from_crawler(self, connection):
        server = connection.from_settings.return_value = mock.Mock()
        crawler = get_crawler()
        myspider = MySpider.from_crawler(crawler)
        assert myspider.server is server
        connection.from_settings.assert_called_with(crawler.settings)
        crawler.signals.connect.assert_called_with(myspider.spider_idle, signal=signals.spider_idle)
        # Second call does nothing.
        server = myspider.server
        crawler.signals.connect.reset_mock()
        myspider.setup_redis()
        assert myspider.server is server
        assert crawler.signals.connect.call_count == 0


@pytest.mark.parametrize('spider_cls', [
    MySpider,
    MyCrawlSpider,
])
def test_from_crawler_with_spider_arguments(spider_cls):
    crawler = get_crawler()
    spider = spider_cls.from_crawler(
        crawler, 'foo',
        redis_key='key:%(name)s',
        redis_batch_size='2000',
    )
    assert spider.name == 'foo'
    assert spider.redis_key == 'key:foo'
    assert spider.redis_batch_size == 2000


class MockRequest(mock.Mock):
    def __init__(self, url, **kwargs):
        super(MockRequest, self).__init__()
        self.url = url

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, self.url)


@pytest.mark.parametrize('spider_cls', [
    MySpider,
    MyCrawlSpider,
])
@pytest.mark.parametrize('start_urls_as_set', [False, True])
@mock.patch('scrapy.spiders.Request', MockRequest)
def test_consume_urls_from_redis(start_urls_as_set, spider_cls):
    batch_size = 5
    redis_key = 'start:urls'
    crawler = get_crawler()
    crawler.settings.setdict({
        'REDIS_START_URLS_KEY': redis_key,
        'REDIS_START_URLS_AS_SET': start_urls_as_set,
        'CONCURRENT_REQUESTS': batch_size,
    })
    spider = spider_cls.from_crawler(crawler)
    with flushall(spider.server):
        urls = [
            'http://example.com/%d' % i for i in range(batch_size * 2)
        ]
        reqs = []
        server_put = spider.server.sadd if start_urls_as_set else spider.server.rpush
        for url in urls:
            server_put(redis_key, url)
            reqs.append(MockRequest(url))

        # First call is to start requests.
        start_requests = list(spider.start_requests())
        if start_urls_as_set:
            assert len(start_requests) == batch_size
            assert set(start_requests).issubset(reqs)
        else:
            assert start_requests == reqs[:batch_size]

        # Second call is to spider idle method.
        with pytest.raises(DontCloseSpider):
            spider.spider_idle()
        # Process remaining requests in the queue.
        with pytest.raises(DontCloseSpider):
            spider.spider_idle()

        # Last batch was passed to crawl.
        assert crawler.engine.crawl.call_count == batch_size
        if start_urls_as_set:
            crawler.engine.crawl.assert_has_calls([
                mock.call(req, spider=spider) for req in reqs if req not in start_requests
            ], any_order=True)
        else:
            crawler.engine.crawl.assert_has_calls([
                mock.call(req, spider=spider) for req in reqs[batch_size:]
            ])
