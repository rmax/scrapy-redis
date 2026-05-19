import contextlib
import os
from unittest import mock

import pytest
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.settings import Settings

from scrapy_redis.spiders import RedisCrawlSpider, RedisSpider

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


class FakePipeline:
    def __init__(self, server):
        self.server = server
        self.operations = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def lrange(self, key, start, end):
        self.operations.append(lambda: self.server.lrange(key, start, end))
        return self

    def ltrim(self, key, start, end):
        self.operations.append(lambda: self.server.ltrim(key, start, end))
        return self

    def zrevrange(self, key, start, end):
        self.operations.append(lambda: self.server.zrevrange(key, start, end))
        return self

    def zremrangebyrank(self, key, start, end):
        self.operations.append(lambda: self.server.zremrangebyrank(key, start, end))
        return self

    def execute(self):
        return [operation() for operation in self.operations]


class FakeRedisServer:
    def __init__(self):
        self._lists = {}
        self._sets = {}
        self._zsets = {}

    def flushall(self):
        self._lists.clear()
        self._sets.clear()
        self._zsets.clear()

    def pipeline(self):
        return FakePipeline(self)

    def rpush(self, key, value):
        self._lists.setdefault(key, []).append(value)

    def lrange(self, key, start, end):
        values = list(self._lists.get(key, []))
        if end == -1:
            end = len(values) - 1
        return values[start : end + 1]

    def ltrim(self, key, start, end):
        values = list(self._lists.get(key, []))
        if end == -1:
            trimmed = values[start:]
        else:
            trimmed = values[start : end + 1]
        self._lists[key] = trimmed
        return True

    def llen(self, key):
        return len(self._lists.get(key, []))

    def sadd(self, key, value):
        self._sets.setdefault(key, set()).add(value)

    def spop(self, key, count=1):
        values = self._sets.get(key, set())
        popped = []
        for value in sorted(values)[:count]:
            popped.append(value)
            values.remove(value)
        return popped

    def scard(self, key):
        return len(self._sets.get(key, set()))

    def zadd(self, key, mapping):
        zset = self._zsets.setdefault(key, {})
        zset.update(mapping)

    def zrevrange(self, key, start, end):
        values = self._sorted_zset(key, reverse=True)
        if end == -1:
            end = len(values) - 1
        return [member for member, _score in values[start : end + 1]]

    def zremrangebyrank(self, key, start, end):
        values = self._sorted_zset(key, reverse=False)
        if not values:
            return 0

        total = len(values)
        if start < 0:
            start += total
        if end < 0:
            end += total
        start = max(start, 0)
        end = min(end, total - 1)
        if start > end:
            return 0

        removed = 0
        for member, _score in values[start : end + 1]:
            if member in self._zsets.get(key, {}):
                del self._zsets[key][member]
                removed += 1
        return removed

    def zcard(self, key):
        return len(self._zsets.get(key, {}))

    def _sorted_zset(self, key, reverse):
        return sorted(
            self._zsets.get(key, {}).items(),
            key=lambda item: (item[1], item[0]),
            reverse=reverse,
        )


@contextlib.contextmanager
def flushall(server):
    try:
        yield
    finally:
        server.flushall()


class MySpider(RedisSpider):
    name = "myspider"


class MyCrawlSpider(RedisCrawlSpider):
    name = "myspider"


def get_crawler(**kwargs):
    return mock.Mock(
        settings=Settings(
            {
                "REDIS_HOST": REDIS_HOST,
                "REDIS_PORT": REDIS_PORT,
            }
        ),
        **kwargs,
    )


@contextlib.contextmanager
def patched_redis(server):
    with mock.patch(
        "scrapy_redis.spiders.connection.from_settings", return_value=server
    ):
        yield


class TestRedisMixinSetupRedis:

    def setup(self):
        self.myspider = MySpider()

    def test_crawler_required(self):
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "crawler" in str(excinfo.value)

    def test_requires_redis_key(self):
        self.myspider.crawler = get_crawler()
        self.myspider.redis_key = ""
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "redis_key" in str(excinfo.value)

    def test_invalid_batch_size(self):
        self.myspider.redis_batch_size = "x"
        self.myspider.crawler = get_crawler()
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "redis_batch_size" in str(excinfo.value)

    def test_invalid_idle_time(self):
        self.myspider.max_idle_time = "x"
        self.myspider.crawler = get_crawler()
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "max_idle_time" in str(excinfo.value)

    def test_empty_list_raises(self):
        self.myspider.crawler = get_crawler()
        self.myspider.redis_key = []
        with pytest.raises(ValueError) as excinfo:
            self.myspider.setup_redis()
        assert "empty after normalization" in str(excinfo.value)

    @mock.patch("scrapy_redis.spiders.connection")
    def test_via_from_crawler(self, connection):
        server = connection.from_settings.return_value = mock.Mock()
        crawler = get_crawler()
        myspider = MySpider.from_crawler(crawler)
        assert myspider.server is server
        connection.from_settings.assert_called_with(crawler.settings)
        crawler.signals.connect.assert_called_with(
            myspider.spider_idle, signal=signals.spider_idle
        )
        server = myspider.server
        crawler.signals.connect.reset_mock()
        myspider.setup_redis()
        assert myspider.server is server
        assert crawler.signals.connect.call_count == 0


@pytest.mark.parametrize(
    "spider_cls",
    [
        MySpider,
        MyCrawlSpider,
    ],
)
def test_from_crawler_with_spider_arguments(spider_cls):
    crawler = get_crawler()
    with patched_redis(FakeRedisServer()):
        spider = spider_cls.from_crawler(
            crawler,
            "foo",
            redis_key="key:%(name)s",
            redis_batch_size="2000",
            max_idle_time="100",
        )
    assert spider.name == "foo"
    assert spider.redis_key == "key:foo"
    assert spider.redis_batch_size == 2000
    assert spider.max_idle_time == 100


class MockRequest(mock.Mock):
    def __init__(self, url, **kwargs):
        super().__init__()
        self.url = url

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.url})>"


@pytest.mark.parametrize(
    "spider_cls",
    [
        MySpider,
        MyCrawlSpider,
    ],
)
@pytest.mark.parametrize("start_urls_as_zset", [False, True])
@pytest.mark.parametrize("start_urls_as_set", [False, True])
@mock.patch("scrapy.spiders.Request", MockRequest)
def test_consume_urls_from_redis(start_urls_as_zset, start_urls_as_set, spider_cls):
    batch_size = 5
    redis_key = "start:urls"
    server = FakeRedisServer()
    crawler = get_crawler()
    crawler.settings.setdict(
        {
            "REDIS_HOST": REDIS_HOST,
            "REDIS_PORT": REDIS_PORT,
            "REDIS_START_URLS_KEY": redis_key,
            "REDIS_START_URLS_AS_ZSET": start_urls_as_zset,
            "REDIS_START_URLS_AS_SET": start_urls_as_set,
            "CONCURRENT_REQUESTS": batch_size,
        }
    )
    with patched_redis(server):
        spider = spider_cls.from_crawler(crawler)
    with flushall(server):
        urls = [f"http://example.com/{i}" for i in range(batch_size * 2)]
        reqs = []
        if start_urls_as_set:
            server_put = server.sadd
        elif start_urls_as_zset:

            def server_put(key, value):
                server.zadd(key, {value: 0})

        else:
            server_put = server.rpush
        for url in urls:
            server_put(redis_key, url)
            reqs.append(MockRequest(url))

        start_requests = list(spider.start_requests())
        if start_urls_as_zset or start_urls_as_set:
            assert len(start_requests) == batch_size
            assert {r.url for r in start_requests}.issubset(r.url for r in reqs)
        else:
            assert start_requests == reqs[:batch_size]

        with pytest.raises(DontCloseSpider):
            spider.spider_idle()
        with pytest.raises(DontCloseSpider):
            spider.spider_idle()

        assert crawler.engine.crawl.call_count == batch_size

        if start_urls_as_zset or start_urls_as_set:
            crawler.engine.crawl.assert_has_calls(
                [mock.call(req) for req in reqs if req not in start_requests],
                any_order=True,
            )
        else:
            crawler.engine.crawl.assert_has_calls(
                [mock.call(req) for req in reqs[batch_size:]]
            )


class TestRedisMixinMultiKey:

    def setup(self):
        self.server = FakeRedisServer()
        self.crawler = get_crawler()
        self.crawler.settings.setdict(
            {
                "CONCURRENT_REQUESTS": 2,
                "MAX_IDLE_TIME_BEFORE_CLOSE": 5,
            }
        )

    def make_spider(self, **kwargs):
        with patched_redis(self.server):
            return MySpider.from_crawler(self.crawler, **kwargs)

    def test_multi_key_list_accepted(self):
        spider = self.make_spider(redis_key=["high:urls", "low:urls"])
        assert spider._redis_keys == ["high:urls", "low:urls"]
        assert spider.redis_key == "high:urls"

    def test_duplicates_removed(self):
        spider = self.make_spider(redis_key=["k", "k"])
        assert spider._redis_keys == ["k"]
        assert spider.redis_key == "k"

    def test_templating_per_key(self):
        spider = self.make_spider(redis_key=["%(name)s:high", "%(name)s:low"])
        assert spider._redis_keys == ["myspider:high", "myspider:low"]
        assert spider.redis_key == "myspider:high"

    def test_consumes_from_highest_priority_non_empty_queue(self):
        spider = self.make_spider(redis_key=["high:urls", "low:urls"])
        self.server.rpush("high:urls", "http://example.com/high")
        self.server.rpush("low:urls", "http://example.com/low")

        requests = list(spider.next_requests())

        assert [request.url for request in requests] == ["http://example.com/high"]
        assert spider.redis_key == "high:urls"
        assert self.server.llen("low:urls") == 1

    def test_drains_current_queue_before_switching(self):
        spider = self.make_spider(redis_key=["high:urls", "low:urls"])
        self.server.rpush("low:urls", "http://example.com/low-1")
        self.server.rpush("low:urls", "http://example.com/low-2")

        first_batch = list(spider.next_requests())
        assert [request.url for request in first_batch] == [
            "http://example.com/low-1",
            "http://example.com/low-2",
        ]
        assert spider.redis_key == "low:urls"

        self.server.rpush("high:urls", "http://example.com/high")
        self.server.rpush("low:urls", "http://example.com/low-3")

        second_batch = list(spider.next_requests())
        assert [request.url for request in second_batch] == ["http://example.com/low-3"]
        assert spider.redis_key == "low:urls"

        third_batch = list(spider.next_requests())
        assert [request.url for request in third_batch] == ["http://example.com/high"]
        assert spider.redis_key == "high:urls"

    def test_spider_idle_checks_all_keys(self):
        spider = self.make_spider(redis_key=["high:urls", "low:urls"], max_idle_time=1)
        self.server.rpush("low:urls", "http://example.com/low")

        with mock.patch("scrapy_redis.spiders.time.time", return_value=100):
            spider.spider_idle_start_time = 0
            with pytest.raises(DontCloseSpider):
                spider.spider_idle()

        assert spider.spider_idle_start_time == 100
        crawler_calls = spider.crawler.engine.crawl.call_args_list
        assert [call.args[0].url for call in crawler_calls] == ["http://example.com/low"]

    def test_all_keys_empty_idle_timeout(self):
        spider = self.make_spider(redis_key=["high:urls", "low:urls"], max_idle_time=1)
        spider.spider_idle_start_time = 0

        with mock.patch("scrapy_redis.spiders.time.time", return_value=1):
            assert spider.spider_idle() is None

    def test_backward_compatible_string_redis_key(self):
        spider = self.make_spider(redis_key="queue:%(name)s")
        assert spider.redis_key == "queue:myspider"
        assert spider._redis_keys is None

    def test_redis_key_check_interval_preempts(self):
        spider = self.make_spider(
            redis_key=["high:urls", "low:urls"],
            redis_batch_size=1,
            redis_key_check_interval=5,
        )
        self.server.rpush("low:urls", "http://example.com/low-1")
        self.server.rpush("low:urls", "http://example.com/low-2")

        with mock.patch("scrapy_redis.spiders.time.time", return_value=1):
            first_batch = list(spider.next_requests())

        assert [request.url for request in first_batch] == ["http://example.com/low-1"]
        assert spider.redis_key == "low:urls"

        self.server.rpush("high:urls", "http://example.com/high-1")

        with mock.patch("scrapy_redis.spiders.time.time", return_value=3):
            second_batch = list(spider.next_requests())

        assert [request.url for request in second_batch] == ["http://example.com/low-2"]
        assert spider.redis_key == "low:urls"

        with mock.patch("scrapy_redis.spiders.time.time", return_value=6):
            third_batch = list(spider.next_requests())

        assert [request.url for request in third_batch] == ["http://example.com/high-1"]
        assert spider.redis_key == "high:urls"
