import connection

from scrapy.utils.misc import load_object
from scrapy_redis.dupefilter import RFPDupeFilter


# default values
SCHEDULER_PERSIST = False
QUEUE_KEY = '%(spider)s:requests'
QUEUE_CLASS = 'scrapy_redis.queue.SpiderPriorityQueue'
DUPEFILTER_KEY = '%(spider)s:dupefilter'
IDLE_BEFORE_CLOSE = 0


class Scheduler(object):
    """Redis-based scheduler"""

    def __init__(self, server, persist, queue_key, queue_cls, dupefilter_key, idle_before_close):
        """Initialize scheduler.

        Parameters
        ----------
        server : Redis instance
        persist : bool
        queue_key : str
        queue_cls : queue class
        dupefilter_key : str
        idle_before_close : int
        """
        self.server = server
        self.persist = persist
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.dupefilter_key = dupefilter_key
        self.idle_before_close = idle_before_close
        self.stats = None

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
        queue_key = settings.get('SCHEDULER_QUEUE_KEY', QUEUE_KEY)
        queue_cls = load_object(settings.get('SCHEDULER_QUEUE_CLASS', QUEUE_CLASS))
        dupefilter_key = settings.get('DUPEFILTER_KEY', DUPEFILTER_KEY)
        idle_before_close = settings.get('SCHEDULER_IDLE_BEFORE_CLOSE', IDLE_BEFORE_CLOSE)
        server = connection.from_settings(settings)
        return cls(server, persist, queue_key, queue_cls, dupefilter_key, idle_before_close)

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls.from_settings(crawler.settings)
        # FIXME: for now, stats are only supported from this constructor
        instance.stats = crawler.stats
        return instance

    def open(self, spider):
        self.spider = spider
        self.queue = self.queue_cls(self.server, spider, self.queue_key)
        self.df = RFPDupeFilter(self.server, self.dupefilter_key % {'spider': spider.name})
        if self.idle_before_close < 0:
            self.idle_before_close = 0
        # notice if there are requests already in the queue to resume the crawl
        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.df.clear()
            self.queue.clear()

    def enqueue_request(self, request):
        if not request.dont_filter and self.df.request_seen(request):
            return
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        self.queue.push(request)

    def next_request(self):
        block_pop_timeout = self.idle_before_close
        request = self.queue.pop(block_pop_timeout)
        if request and self.stats:
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0
