from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.spiders import Spider, CrawlSpider

from . import connection


class RedisMixin(object):
    """Mixin class to implement reading urls from a redis queue."""
    redis_key = None  # If empty, uses default '<spider>:start_urls'.
    # Fetch this amount of start urls when idle.
    redis_batch_size = 100
    # Redis client instance.
    server = None

    def start_requests(self):
        """Returns a batch of start requests from redis."""
        return self.next_requests()

    def setup_redis(self, crawler=None):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.
        """
        if self.server is not None:
            return

        if crawler is None:
            # We allow optional crawler argument to keep backwrads
            # compatibility.
            # XXX: Raise a deprecation warning.
            assert self.crawler, "crawler not set"
            crawler = self.crawler

        if not self.redis_key:
            self.redis_key = '%s:start_urls' % self.name
        self.log("Reading URLs from redis key '%s'" % self.redis_key)

        self.redis_batch_size = self.settings.getint(
            'REDIS_START_URLS_BATCH_SIZE',
            self.redis_batch_size,
        )

        self.server = connection.from_settings(crawler.settings)
        # The idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    def next_requests(self):
        """Returns a request to be scheduled or none."""
        use_set = self.settings.getbool('REDIS_START_URLS_AS_SET')
        fetch_one = self.server.spop if use_set else self.server.lpop
        # XXX: Do we need to use a timeout here?
        found = 0
        while found < self.redis_batch_size:
            data = fetch_one(self.redis_key)
            if not data:
                # Queue empty.
                break
            yield self.make_request_from_data(data)
            found += 1

        if found:
            self.logger.debug("Read %s requests from '%s'", found, self.redis_key)

    def make_request_from_data(self, data):
        # By default, data is an URL.
        if '://' in data:
            return self.make_requests_from_url(data)
        else:
            self.logger.error("Unexpected URL from '%s': %r", self.redis_key, data)

    def schedule_next_requests(self):
        """Schedules a request if available"""
        for req in self.next_requests():
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        # XXX: Handle a sentinel to close the spider.
        self.schedule_next_requests()
        raise DontCloseSpider


class RedisSpider(RedisMixin, Spider):
    """Spider that reads urls from redis queue when idle."""

    @classmethod
    def from_crawler(self, crawler):
        obj = super(RedisSpider, self).from_crawler(crawler)
        obj.setup_redis(crawler)
        return obj


class RedisCrawlSpider(RedisMixin, CrawlSpider):
    """Spider that reads urls from redis queue when idle."""

    @classmethod
    def from_crawler(self, crawler):
        obj = super(RedisCrawlSpider, self).from_crawler(crawler)
        obj.setup_redis(crawler)
        return obj
