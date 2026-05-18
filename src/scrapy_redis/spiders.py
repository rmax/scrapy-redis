import json
import time
from collections.abc import Iterable

from scrapy import FormRequest, signals
from scrapy import version_info as scrapy_version
from scrapy.exceptions import DontCloseSpider
from scrapy.spiders import CrawlSpider, Spider

from scrapy_redis.utils import TextColor

from . import connection, defaults
from .utils import bytes_to_str, is_dict


class RedisMixin:
    """Mixin class to implement reading urls from a redis queue."""

    redis_key = None
    redis_batch_size = None
    redis_encoding = None
    redis_key_check_interval = None

    # Redis client placeholder.
    server = None

    # Idle start time
    spider_idle_start_time = int(time.time())
    max_idle_time = None
    _redis_keys = None
    _last_priority_scan = 0

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
            # We allow optional crawler argument to keep backwards
            # compatibility.
            # XXX: Raise a deprecation warning.
            crawler = getattr(self, "crawler", None)

        if crawler is None:
            raise ValueError("crawler is required")

        settings = crawler.settings

        if self.redis_key is None:
            self.redis_key = settings.get(
                "REDIS_START_URLS_KEY",
                defaults.START_URLS_KEY,
            )

        self.redis_key, self._redis_keys = self._normalize_redis_key(self.redis_key)

        if self.redis_batch_size is None:
            self.redis_batch_size = settings.getint(
                "CONCURRENT_REQUESTS", defaults.REDIS_CONCURRENT_REQUESTS
            )

        try:
            self.redis_batch_size = int(self.redis_batch_size)
        except (TypeError, ValueError):
            raise ValueError("redis_batch_size must be an integer")

        if self.redis_encoding is None:
            self.redis_encoding = settings.get(
                "REDIS_ENCODING", defaults.REDIS_ENCODING
            )

        self.server = connection.from_settings(crawler.settings)

        if settings.getbool("REDIS_START_URLS_AS_SET", defaults.START_URLS_AS_SET):
            self.fetch_data = self.server.spop
            self.count_size = self.server.scard
        elif settings.getbool("REDIS_START_URLS_AS_ZSET", defaults.START_URLS_AS_ZSET):
            self.fetch_data = self.pop_priority_queue
            self.count_size = self.server.zcard
        else:
            self.fetch_data = self.pop_list_queue
            self.count_size = self.server.llen

        if self.redis_key_check_interval is None:
            self.redis_key_check_interval = settings.get(
                "REDIS_KEY_CHECK_INTERVAL", defaults.REDIS_KEY_CHECK_INTERVAL
            )

        if self.redis_key_check_interval in (None, 0, "0"):
            self.redis_key_check_interval = 0
        else:
            try:
                self.redis_key_check_interval = int(self.redis_key_check_interval)
            except (TypeError, ValueError):
                raise ValueError("redis_key_check_interval must be an integer or None")

        self._last_priority_scan = 0

        if self._redis_keys:
            self.logger.info(
                "Reading start URLs from redis keys '%(redis_keys)s' "
                "(batch size: %(redis_batch_size)s, encoding: %(redis_encoding)s)",
                {
                    "redis_keys": self._redis_keys,
                    "redis_batch_size": self.redis_batch_size,
                    "redis_encoding": self.redis_encoding,
                },
            )
        else:
            self.logger.info(
                "Reading start URLs from redis key '%(redis_key)s' "
                "(batch size: %(redis_batch_size)s, encoding: %(redis_encoding)s)",
                self.__dict__,
            )

        if self.max_idle_time is None:
            self.max_idle_time = settings.get(
                "MAX_IDLE_TIME_BEFORE_CLOSE", defaults.MAX_IDLE_TIME
            )

        try:
            self.max_idle_time = int(self.max_idle_time)
        except (TypeError, ValueError):
            raise ValueError("max_idle_time must be an integer")

        # The idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    def _normalize_redis_key(self, redis_key):
        if isinstance(redis_key, str):
            redis_key = redis_key % {"name": self.name}
            if not redis_key.strip():
                raise ValueError("redis_key must not be empty")
            return redis_key, None

        if isinstance(redis_key, list):
            redis_keys = []
            seen = set()
            for key in redis_key:
                formatted_key = key % {"name": self.name}
                stripped_key = formatted_key.strip()
                if not stripped_key:
                    raise ValueError("redis_key must not be empty")
                if stripped_key not in seen:
                    seen.add(stripped_key)
                    redis_keys.append(stripped_key)

            if not redis_keys:
                raise ValueError("redis_key list is empty after normalization")

            return redis_keys[0], redis_keys

        return redis_key, None

    def _is_multi_key_mode(self):
        return bool(self._redis_keys)

    def _any_key_has_items(self):
        if not self._is_multi_key_mode():
            return self.count_size(self.redis_key) > 0
        return sum(self.count_size(key) for key in self._redis_keys) > 0

    def _select_priority_key(self):
        """Return the first non-empty key from _redis_keys in priority order."""
        if not self._redis_keys:
            return self.redis_key
        for key in self._redis_keys:
            if self.count_size(key) > 0:
                return key
        return None

    def _maybe_switch_to_higher_priority_key(self):
        if not self._redis_keys:
            return

        selected_key = self._select_priority_key()
        if selected_key is None:
            return

        try:
            current_index = self._redis_keys.index(self.redis_key)
        except ValueError:
            current_index = len(self._redis_keys)

        selected_index = self._redis_keys.index(selected_key)
        if selected_index < current_index:
            self.redis_key = selected_key

    def _maybe_check_priority_scan(self):
        if not self._redis_keys:
            return

        if self.count_size(self.redis_key) == 0:
            selected_key = self._select_priority_key()
            if selected_key is not None:
                self.redis_key = selected_key

        if not self.redis_key_check_interval:
            return

        current_time = time.time()
        if current_time - self._last_priority_scan >= self.redis_key_check_interval:
            self._maybe_switch_to_higher_priority_key()
            self._last_priority_scan = current_time

    def pop_list_queue(self, redis_key, batch_size):
        with self.server.pipeline() as pipe:
            pipe.lrange(redis_key, 0, batch_size - 1)
            pipe.ltrim(redis_key, batch_size, -1)
            datas, _ = pipe.execute()
        return datas

    def pop_priority_queue(self, redis_key, batch_size):
        with self.server.pipeline() as pipe:
            pipe.zrevrange(redis_key, 0, batch_size - 1)
            pipe.zremrangebyrank(redis_key, -batch_size, -1)
            datas, _ = pipe.execute()
        return datas

    def next_requests(self):
        """Returns a request to be scheduled or none."""
        # XXX: Do we need to use a timeout here?
        self._maybe_check_priority_scan()
        found = 0
        datas = self.fetch_data(self.redis_key, self.redis_batch_size)
        for data in datas:
            reqs = self.make_request_from_data(data)
            if isinstance(reqs, Iterable):
                for req in reqs:
                    yield req
                    # XXX: should be here?
                    found += 1
                    self.logger.info(f"start req url:{req.url}")
            elif reqs:
                yield reqs
                found += 1
            else:
                self.logger.debug(f"Request not made from data: {data}")

        if found:
            self.logger.debug(f"Read {found} requests from '{self.redis_key}'")

    def make_request_from_data(self, data):
        """Returns a `Request` instance for data coming from Redis.

        Overriding this function to support the `json` requested `data` that contains
        `url` ,`meta` and other optional parameters. `meta` is a nested json which contains sub-data.

        Along with:
        After accessing the data, sending the FormRequest with `url`, `meta` and addition `formdata`, `method`

        For example:

        .. code:: json

            {
                "url": "https://example.com",
                "meta": {
                    "job-id":"123xsd",
                    "start-date":"dd/mm/yy",
                },
                "url_cookie_key":"fertxsas",
                "method":"POST",
            }

        If `url` is empty, return `[]`. So you should verify the `url` in the data.
        If `method` is empty, the request object will set method to 'GET', optional.
        If `meta` is empty, the request object will set `meta` to an empty dictionary, optional.

        This json supported data can be accessed from 'scrapy.spider' through response.
        'request.url', 'request.meta', 'request.cookies', 'request.method'

        Parameters
        ----------
        data : bytes
            Message from redis.

        """
        formatted_data = bytes_to_str(data, self.redis_encoding)

        if is_dict(formatted_data):
            parameter = json.loads(formatted_data)
        else:
            self.logger.warning(
                f"{TextColor.WARNING}WARNING: String request is deprecated, please use JSON data format. "
                f"Detail information, please check https://github.com/rmax/scrapy-redis#features{TextColor.ENDC}"
            )
            return FormRequest(formatted_data, dont_filter=True)

        if parameter.get("url", None) is None:
            self.logger.warning(
                f"{TextColor.WARNING}The data from Redis has no url key in push data{TextColor.ENDC}"
            )
            return []

        url = parameter.pop("url")
        method = parameter.pop("method").upper() if "method" in parameter else "GET"
        metadata = parameter.pop("meta") if "meta" in parameter else {}

        return FormRequest(
            url, dont_filter=True, method=method, formdata=parameter, meta=metadata
        )

    def schedule_next_requests(self):
        """Schedules a request if available"""
        # TODO: While there is capacity, schedule a batch of redis requests.
        self._maybe_check_priority_scan()
        for req in self.next_requests():
            # see https://github.com/scrapy/scrapy/issues/5994
            if scrapy_version >= (2, 6):
                self.crawler.engine.crawl(req)
            else:
                self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """
        Schedules a request if available, otherwise waits.
        or close spider when waiting seconds > MAX_IDLE_TIME_BEFORE_CLOSE.
        MAX_IDLE_TIME_BEFORE_CLOSE will not affect SCHEDULER_IDLE_BEFORE_CLOSE.
        """
        self._maybe_check_priority_scan()

        if self.server is not None and self._any_key_has_items():
            self.spider_idle_start_time = int(time.time())

        self.schedule_next_requests()

        idle_time = int(time.time()) - self.spider_idle_start_time
        if self.max_idle_time != 0 and idle_time >= self.max_idle_time:
            return
        raise DontCloseSpider


class RedisSpider(RedisMixin, Spider):
    """Spider that reads urls from redis queue when idle.

    Attributes
    ----------
    redis_key : str (default: REDIS_START_URLS_KEY)
        Redis key where to fetch start URLs from..
    redis_batch_size : int (default: CONCURRENT_REQUESTS)
        Number of messages to fetch from redis on each attempt.
    redis_encoding : str (default: REDIS_ENCODING)
        Encoding to use when decoding messages from redis queue.

    Redis Settings
    --------------
    REDIS_START_URLS_KEY : str (default: "<spider.name>:start_urls")
        Default Redis key where to fetch start URLs from..
    REDIS_START_URLS_BATCH_SIZE : int (deprecated by CONCURRENT_REQUESTS)
        Default number of messages to fetch from redis on each attempt.
    REDIS_START_URLS_AS_SET : bool (default: False)
        Use SET operations to retrieve messages from the redis queue. If False,
        the messages are retrieve using the LPOP command.
    REDIS_ENCODING : str (default: "utf-8")
        Default encoding to use when decoding messages from redis queue.

    """

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        obj = super().from_crawler(crawler, *args, **kwargs)
        obj.setup_redis(crawler)
        return obj


class RedisCrawlSpider(RedisMixin, CrawlSpider):
    """Spider that reads urls from redis queue when idle.

    Attributes
    ----------
    redis_key : str (default: REDIS_START_URLS_KEY)
        Redis key where to fetch start URLs from..
    redis_batch_size : int (default: CONCURRENT_REQUESTS)
        Number of messages to fetch from redis on each attempt.
    redis_encoding : str (default: REDIS_ENCODING)
        Encoding to use when decoding messages from redis queue.

    Crawl Spider Settings
    ---------------------
    REDIS_START_URLS_KEY : str (default: "<spider.name>:start_urls")
        Default Redis key where to fetch start URLs from..
    REDIS_START_URLS_BATCH_SIZE : int (deprecated by CONCURRENT_REQUESTS)
        Default number of messages to fetch from redis on each attempt.
    REDIS_START_URLS_AS_SET : bool (default: True)
        Use SET operations to retrieve messages from the redis queue.
    REDIS_ENCODING : str (default: "utf-8")
        Default encoding to use when decoding messages from redis queue.

    """

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        obj = super().from_crawler(crawler, *args, **kwargs)
        obj.setup_redis(crawler)
        return obj
