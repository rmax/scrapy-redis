import importlib
import logging
from collections import deque

from scrapy.utils.misc import load_object

from . import connection, defaults

logger = logging.getLogger(__name__)


# TODO: add SCRAPY_JOB support.
class Scheduler:
    """Redis-based scheduler

    Settings
    --------
    SCHEDULER_PERSIST : bool (default: False)
        Whether to persist or clear redis queue.
    SCHEDULER_FLUSH_ON_START : bool (default: False)
        Whether to flush redis queue on start.
    SCHEDULER_IDLE_BEFORE_CLOSE : int (default: 0)
        How many seconds to wait before closing if no message is received.
    SCHEDULER_QUEUE_KEY : str
        Scheduler redis key.
    SCHEDULER_QUEUE_CLASS : str
        Scheduler queue class.
    SCHEDULER_DUPEFILTER_KEY : str
        Scheduler dupefilter redis key.
    SCHEDULER_DUPEFILTER_CLASS : str
        Scheduler dupefilter class.
    SCHEDULER_SERIALIZER : str
        Scheduler serializer.

    Requests that can't be serialized (e.g. their callback is not a spider
    method) are kept in a local in-memory queue instead of Redis. They are
    only processed by the worker that created them and are never persisted.

    """

    def __init__(
        self,
        server,
        persist=False,
        flush_on_start=False,
        queue_key=defaults.SCHEDULER_QUEUE_KEY,
        queue_cls=defaults.SCHEDULER_QUEUE_CLASS,
        dupefilter=None,
        dupefilter_key=defaults.SCHEDULER_DUPEFILTER_KEY,
        dupefilter_cls=defaults.SCHEDULER_DUPEFILTER_CLASS,
        idle_before_close=0,
        serializer=None,
    ):
        """Initialize scheduler.

        Parameters
        ----------
        server : Redis
            The redis server instance.
        persist : bool
            Whether to flush requests when closing. Default is False.
        flush_on_start : bool
            Whether to flush requests on start. Default is False.
        queue_key : str
            Requests queue key.
        queue_cls : str
            Importable path to the queue class.
        dupefilter: Dupefilter
            Custom dupefilter instance.
        dupefilter_key : str
            Duplicates filter key.
        dupefilter_cls : str
            Importable path to the dupefilter class.
        idle_before_close : int
            Timeout before giving up.

        """
        if idle_before_close < 0:
            raise TypeError("idle_before_close cannot be negative")

        self.server = server
        self.persist = persist
        self.flush_on_start = flush_on_start
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.df = dupefilter
        self.dupefilter_cls = dupefilter_cls
        self.dupefilter_key = dupefilter_key
        self.idle_before_close = idle_before_close
        self.serializer = serializer
        self.stats = None
        self.local_queue = deque()
        self._logunser = True

    def __len__(self):
        return len(self.local_queue) + len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        kwargs = {
            "persist": settings.getbool("SCHEDULER_PERSIST"),
            "flush_on_start": settings.getbool("SCHEDULER_FLUSH_ON_START"),
            "idle_before_close": settings.getint("SCHEDULER_IDLE_BEFORE_CLOSE"),
        }

        # If these values are missing, it means we want to use the defaults.
        optional = {
            # TODO: Use custom prefixes for this settings to note that are
            # specific to scrapy-redis.
            "queue_key": "SCHEDULER_QUEUE_KEY",
            "queue_cls": "SCHEDULER_QUEUE_CLASS",
            "dupefilter_key": "SCHEDULER_DUPEFILTER_KEY",
            # We use the default setting name to keep compatibility.
            "dupefilter_cls": "DUPEFILTER_CLASS",
            "serializer": "SCHEDULER_SERIALIZER",
        }
        for name, setting_name in optional.items():
            val = settings.get(setting_name)
            if val:
                kwargs[name] = val

        dupefilter_cls = load_object(kwargs["dupefilter_cls"])
        if not hasattr(dupefilter_cls, "from_spider"):
            kwargs["dupefilter"] = dupefilter_cls.from_settings(settings)

        # Support serializer as a path to a module.
        if isinstance(kwargs.get("serializer"), str):
            kwargs["serializer"] = importlib.import_module(kwargs["serializer"])

        server = connection.from_settings(settings)
        # Ensure the connection is working.
        server.ping()

        return cls(server=server, **kwargs)

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls.from_settings(crawler.settings)
        # FIXME: for now, stats are only supported from this constructor
        instance.stats = crawler.stats
        return instance

    def open(self, spider):
        self.spider = spider

        try:
            self.queue = load_object(self.queue_cls)(
                server=self.server,
                spider=spider,
                key=self.queue_key % {"spider": spider.name},
                serializer=self.serializer,
            )
        except TypeError as e:
            raise ValueError(
                f"Failed to instantiate queue class '{self.queue_cls}': {e}"
            )

        if not self.df:
            self.df = load_object(self.dupefilter_cls).from_spider(spider)

        if self.flush_on_start:
            self.flush()
        # notice if there are requests already in the queue to resume the crawl
        if len(self.queue):
            spider.log(f"Resuming crawl ({len(self.queue)} requests scheduled)")

    def close(self, reason):
        if not self.persist:
            self.flush()

    def flush(self):
        self.df.clear()
        self.queue.clear()
        self.local_queue.clear()

    def enqueue_request(self, request):
        if not request.dont_filter and self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False
        try:
            self.queue.push(request)
        except ValueError as e:
            self._push_local(request, e)
            return True
        if self.stats:
            self.stats.inc_value("scheduler/enqueued/redis")
        return True

    def _push_local(self, request, reason):
        if self._logunser:
            logger.warning(
                "Unable to serialize request: %(request)s - reason: %(reason)s"
                " - keeping it in the local memory queue, no more"
                " unserializable requests will be logged (stats being"
                " collected)",
                {"request": request, "reason": reason},
                exc_info=True,
                extra={"spider": self.spider},
            )
            self._logunser = False
        self.local_queue.append(request)
        if self.stats:
            self.stats.inc_value("scheduler/unserializable")
            self.stats.inc_value("scheduler/enqueued/memory")

    def next_request(self):
        if self.local_queue:
            request = self.local_queue.popleft()
            if self.stats:
                self.stats.inc_value("scheduler/dequeued/memory")
            return request
        block_pop_timeout = self.idle_before_close
        request = self.queue.pop(block_pop_timeout)
        if request and self.stats:
            self.stats.inc_value("scheduler/dequeued/redis")
        return request

    def has_pending_requests(self):
        return len(self) > 0
