import redis

# For standalone use.
DUPEFILTER_KEY = "dupefilter:%(timestamp)s"

PIPELINE_KEY = "%(spider)s:items"

STATS_KEY = "%(spider)s:stats"

REDIS_CLS = redis.StrictRedis
REDIS_ENCODING = "utf-8"
# Sane connection defaults.
REDIS_PARAMS = {
    "socket_timeout": 30,
    "socket_connect_timeout": 30,
    "retry_on_timeout": True,
    "encoding": REDIS_ENCODING,
}
REDIS_CONCURRENT_REQUESTS = 16

SCHEDULER_QUEUE_KEY = "%(spider)s:requests"
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.PriorityQueue"
SCHEDULER_DUPEFILTER_KEY = "%(spider)s:dupefilter"
SCHEDULER_DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = False
START_URLS_KEY = "%(name)s:start_urls"
START_URLS_AS_SET = False
START_URLS_AS_ZSET = False
REDIS_KEY_CHECK_INTERVAL = None
MAX_IDLE_TIME = 0
REDIS_IDLE_BACKOFF_ENABLED = False
REDIS_IDLE_BACKOFF_MIN = 1.0
REDIS_IDLE_BACKOFF_MAX = 30.0
REDIS_IDLE_BACKOFF_FACTOR = 2.0
