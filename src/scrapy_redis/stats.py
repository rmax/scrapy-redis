from scrapy.statscollectors import StatsCollector
from .connection import from_settings as redis_from_settings
from .defaults import STATS_KEY, SCHEDULER_PERSIST
from datetime import datetime


class RedisStatsCollector(StatsCollector):
    """
    Stats Collector based on Redis
    """

    def __init__(self, crawler, spider=None):
        super().__init__(crawler)
        self.server = redis_from_settings(crawler.settings)
        self.spider = spider
        self.spider_name = spider.name if spider else crawler.spidercls.name
        self.stats_key = crawler.settings.get('STATS_KEY', STATS_KEY)
        self.persist = crawler.settings.get(
            'SCHEDULER_PERSIST', SCHEDULER_PERSIST)

    def _get_key(self, spider=None):
        """Return the hash name of stats"""
        if spider:
            self.stats_key % {'spider': spider.name}
        if self.spider:
            return self.stats_key % {'spider': self.spider.name}
        return self.stats_key % {'spider': self.spider_name or 'scrapy'}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    @classmethod
    def from_spider(cls, spider):
        return cls(spider.crawler)

    def get_value(self, key, default=None, spider=None):
        """Return the value of hash stats"""
        if self.server.hexists(self._get_key(spider), key):
            return int(self.server.hget(self._get_key(spider), key))
        else:
            return default

    def get_stats(self, spider=None):
        """Return the all of the values of hash stats"""
        return self.server.hgetall(self._get_key(spider))

    def set_value(self, key, value, spider=None):
        """Set the value according to hash key of stats"""
        if isinstance(value, datetime):
            value = value.timestamp()
        self.server.hset(self._get_key(spider), key, value)

    def set_stats(self, stats, spider=None):
        """Set all the hash stats"""
        self.server.hmset(self._get_key(spider), stats)

    def inc_value(self, key, count=1, start=0, spider=None):
        """Set increment of value according to key"""
        if not self.server.hexists(self._get_key(spider), key):
            self.set_value(key, start)
        self.server.hincrby(self._get_key(spider), key, count)

    def max_value(self, key, value, spider=None):
        """Set max value between current and new value"""
        self.set_value(key, max(self.get_value(key, value), value))

    def min_value(self, key, value, spider=None):
        """Set min value between current and new value"""
        self.set_value(key, min(self.get_value(key, value), value))

    def clear_stats(self, spider=None):
        """Clarn all the hash stats"""
        self.server.delete(self._get_key(spider))

    def open_spider(self, spider):
        """Set spider to self"""
        if spider:
            self.spider = spider

    def close_spider(self, spider, reason):
        """Clear spider and clear stats"""
        self.spider = None
        if not self.persist:
            self.clear_stats(spider)
