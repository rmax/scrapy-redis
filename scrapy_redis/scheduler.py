import redis
from scrapy_redis.queue import SpiderQueue
from scrapy_redis.dupefilter import RFPDupeFilter


# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
SCHEDULER_PERSIST = False
QUEUE_KEY = '%(spider)s:requests'
DUPEFILTER_KEY = '%(spider)s:dupefilter'


class Scheduler(object):
    """Redis-based scheduler"""

    def __init__(self, server, persist, queue_key):
        self.server = server
        self.persist = persist
        self.queue_key = queue_key

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        host = settings.get('REDIS_HOST', REDIS_HOST)
        port = settings.get('REDIS_PORT', REDIS_PORT)
        persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
        queue_key = settings.get('SCHEDULER_QUEUE_KEY', QUEUE_KEY)
        server = redis.Redis(host, port)
        return cls(server, persist, queue_key)

    def open(self, spider):
        self.spider = spider
        self.queue = SpiderQueue(self.server, spider, self.queue_key)
        self.df = RFPDupeFilter(self.server, DUPEFILTER_KEY % {'spider': spider.name})
        # notice if there are requests already in the queue
        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.df.clear()
            self.queue.clear()

    def enqueue_request(self, request):
        if not request.dont_filter and self.df.request_seen(request):
            return
        self.queue.push(request)

    def next_request(self):
        return self.queue.pop()

    def has_pending_requests(self):
        return len(self) > 0

