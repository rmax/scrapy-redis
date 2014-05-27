import connection

from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.spider import Spider


class RedisMixin(object):
    """Mixin class to implement reading urls from a redis queue."""
    redis_key = None  # use default '<spider>:start_urls'

    def setup_redis(self):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.
        """
        if not self.redis_key:
            self.redis_key = '%s:start_urls' % self.name

        self.server = connection.from_settings(self.crawler.settings)
        # idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        self.crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        self.log("Reading URLs from redis list '%s'" % self.redis_key)

    def next_request(self):
        """Returns a request to be scheduled or none."""
        url = self.server.lpop(self.redis_key)
        if url:
            return self.make_requests_from_url(url)

    def schedule_next_request(self):
        """Schedules a request if available"""
        req = self.next_request()
        if req:
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        self.schedule_next_request()
        raise DontCloseSpider

    def item_scraped(self, *args, **kwargs):
        """Avoids waiting for the spider to  idle before scheduling the next request"""
        self.schedule_next_request()


class RedisSpider(RedisMixin, Spider):
    """Spider that reads urls from redis queue when idle."""

    def set_crawler(self, crawler):
        super(RedisSpider, self).set_crawler(crawler)
        self.setup_redis()
