from datetime import datetime, timezone
from unittest import mock

from scrapy.settings import Settings

from scrapy_redis.stats import RedisStatsCollector


class FakeRedisHash:
    """In-memory redis hash. hget returns bytes, matching redis-py."""

    def __init__(self):
        self._hashes = {}

    def hexists(self, name, key):
        return key in self._hashes.get(name, {})

    def hget(self, name, key):
        value = self._hashes.get(name, {}).get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")

    def hset(self, name, key, value):
        self._hashes.setdefault(name, {})[key] = value
        return 1

    def hincrby(self, name, key, amount=1):
        mapping = self._hashes.setdefault(name, {})
        current = int(mapping.get(key, 0))
        mapping[key] = current + int(amount)
        return mapping[key]


def _make_collector():
    crawler = mock.Mock()
    crawler.settings = Settings()
    crawler.spidercls.name = "myspider"
    server = FakeRedisHash()
    with mock.patch("scrapy_redis.stats.redis_from_settings", return_value=server):
        return RedisStatsCollector(crawler)


class TestRedisStatsCollector:
    def setup_method(self):
        self.stats = _make_collector()

    def test_datetime_roundtrip_returns_datetime(self):
        start = datetime.now(tz=timezone.utc)
        self.stats.set_value("start_time", start)
        got = self.stats.get_value("start_time")
        assert isinstance(got, datetime)

    def test_finish_minus_start_has_seconds(self):
        start = datetime.now(tz=timezone.utc)
        finish = datetime.now(tz=timezone.utc)
        self.stats.set_value("start_time", start)
        self.stats.set_value("finish_time", finish)
        delta = self.stats.get_value("finish_time") - self.stats.get_value(
            "start_time"
        )
        assert hasattr(delta, "seconds")
        assert isinstance(delta.seconds, int)

    def test_inc_value_counter_stays_int(self):
        self.stats.inc_value("item_scraped_count")
        self.stats.inc_value("item_scraped_count")
        got = self.stats.get_value("item_scraped_count")
        assert got == 2
        assert type(got) is int
