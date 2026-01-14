from typing import Callable, Iterable, List, Optional, Tuple
import threading
import time
import numpy as np
from redis import WatchError, Redis
import atexit
from scrapy.http import Request
from scrapy.utils.request import request_from_dict
from scrapy.spiders import Spider

from . import picklecompat
# from .defaults import timeit


class Base(object):
    """Per-spider base queue class"""

    def __init__(
        self,
        server: Redis,
        spider: Spider,
        request_fingerprint: Callable,
        requests_key = '%(spider)s:requests',
        queue_key = '%(spider)s:queue',
        length_key = '%(spider)s:queue_length',
        dropped_key = '%(spider)s:dropped',
        ignored_key = '%(spider)s:ignored',
        completed_key = '%(spider)s:completed',
        flush_buffer_size=100,
        flush_interval=2,
    ):
        """
            Initialize per-spider redis queue.
        """
        self.server = server
        self.spider = spider
        self.requests_key = requests_key % {"spider": spider.name}
        self.queue_key = queue_key % {"spider": spider.name}
        self.length_key = length_key % {"spider": spider.name}
        self.dropped_key = dropped_key % {"spider": spider.name}
        self.ignored_key = ignored_key % {"spider": spider.name}
        self.completed_key = completed_key % {"spider": spider.name}
        self.serializer = picklecompat
        self.request_fingerprint = request_fingerprint

        self.flush_buffer_size = flush_buffer_size
        self.flush_interval = flush_interval

        self.push_buffer = []
        self.push_buffer_lock = threading.Lock()
        
        self.completed_buffer = []
        self.completed_buffer_lock = threading.Lock()

        self.flush_running = True
        self.flush_thread = threading.Thread(
            target=self.flush_buffers_periodically, daemon=True
        )
        self.flush_thread.start()

        atexit.register(self.shutdown)

    def _encode_request(self, request: Request):
        """Encode a request object"""

        obj = request.to_dict(spider=self.spider)
        return self.serializer.dumps(obj)

    def _decode_request(self, encoded_request):
        """Decode an request previously encoded"""
        obj = self.serializer.loads(encoded_request)
        return request_from_dict(obj, spider=self.spider)

    def __len__(self):
        """Return the length of the queue"""
        count = self.server.get(self.length_key)
        return int(count) if count else 0

    def push(self, request):
        """Push a request"""
        raise NotImplementedError

    def complete(self, crawl_id: str, data: str) -> bool:
        """Store the completed request data in a buffer for later processing."""
        raise NotImplementedError("complete method must be implemented in subclass")

    def pop(self, queue_key, timeout=0):
        """Pop a request"""
        raise NotImplementedError

    def put_request_data(self, request):
        """Put request data into the queue"""
        raise NotImplementedError("put_request_data method must be implemented in subclass")

    def flush_buffers(self):
        raise NotImplementedError

    def flush_buffers_periodically(self):
        while self.flush_running:
            time.sleep(self.flush_interval)
            self.flush_buffers()

    def clear(self, crawl_id):
        """Clear queue/stack"""
        if crawl_id is None:
            return False

        self.server.delete(self.dequeue_key(crawl_id))
        return True

    def ack(self, crawl_id, fp):
        raise NotImplementedError("ack method must be implemented in subclass")

    def nack(self, crawl_id, fp, request=None, priority=0.0):
        raise NotImplementedError("nack method must be implemented in subclass")

    def drop(self, crawl_id: str, fp: str) -> bool:
        """
        Permanently discard *fp* after repeated nack failures.
        Returns True  if the request was still in processing and was dropped.
        Returns False if someone else had already handled it.
        """
        raise NotImplementedError("drop method must be implemented in subclass")

    def enqueue_key(self, request):
        """Return a key to identify the queue"""

        crawl_id = request.meta.get("crawl_id", None)
        return f"{self.queue_key}:pending:{crawl_id}"

    def dequeue_key(self, crawl_id):
        """Return a key to identify the queue"""
        return f"{self.queue_key}:pending:{crawl_id}"

    def shutdown(self):
        """Handle the shutdown process."""
        self.flush_running = False
        self.flush_thread.join()
        self.flush_buffers()

    # @timeit
    def pending_queues_lengths(self):
        lua_script = """
            local lengths = {}
            for i, key in ipairs(KEYS) do
                lengths[#lengths+1] = redis.call('ZCARD', key)
            end
            return lengths
            """

        # Use scan_iter to get the keys safely without blocking the server
        keys = [key for key in self.server.scan_iter(f"{self.queue_key}:pending:*")]

        # You may want to process these in batches if there are a lot of keys
        batch_size = 1000  # Number of keys to process in each batch
        queues_lengths = {}

        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i : i + batch_size]
            lengths = self.server.eval(lua_script, len(batch_keys), *batch_keys)
            queues_lengths.update(dict(zip(batch_keys, lengths)))

        # At this point, queue_lengths contains all your queues and their sizes

        queues_lengths = {k.decode("utf-8"): v for k, v in queues_lengths.items()}

        crawl_id_lengths = {}
        for k, v in queues_lengths.items():
            crawl_id = k.split(":")[-1]  # Extract crawl_id from the key
            if crawl_id not in crawl_id_lengths:
                crawl_id_lengths[crawl_id] = 0
            crawl_id_lengths[crawl_id] += v

        return crawl_id_lengths


    def reconcile_queue_length(self):
        lua_script = f"""
            local total_count = 0
            local keys = redis.call('KEYS', '{self.queue_key}:*')
            for _, key in ipairs(keys) do
                total_count = total_count + redis.call('ZCARD', key)
            end
            redis.call('SET', '{self.length_key}', total_count)
            return total_count
        """

        total_count = self.server.eval(lua_script, 0)
        return total_count
    
    def overdue_requests(
        self,
        crawl_ids: Optional[Iterable[str]] = None,
        min_age_seconds: int = 600,      # 10 min default
        max_items: int = 1000,           # 0 ⇒ no limit
    ) -> List[Tuple[str, str, Request]]:
        
        raise NotImplementedError(
            "overdue_processing method must be implemented in subclass"
        )


class PriorityQueue(Base):
    """Per-spider priority queue that keeps payload, pending and processing
    in separate Redis keys.
    """

    # ------------------------------------------------------------------ #
    # helpers                                                             #
    # ------------------------------------------------------------------ #
    def _data_key(self, crawl_id):
        # one payload store per spider (share between crawl-ids)
        return f"{self.requests_key}:{crawl_id}"

    def _pending_key(self, crawl_id):
        return f"{self.queue_key}:pending:{crawl_id}"

    def _processing_key(self, crawl_id):
        return f"{self.queue_key}:processing:{crawl_id}"
    
    def _dropped_key(self, crawl_id):
        return f"{self.dropped_key}:{crawl_id}"

    def _ignored_key(self, crawl_id):
        return f"{self.ignored_key}:{crawl_id}"
    
    def _completed_key(self, crawl_id):
        return f"{self.completed_key}:{crawl_id}"

    def push(self, request):
        """Put *request* in the pending queue."""
        fp = self.request_fingerprint(request)
        data = self._encode_request(request)
        score = -request.priority
        crawl_id = request.meta.get("crawl_id")

        with self.push_buffer_lock:
            # buffer: (pending_key, fp, score, data)
            self.push_buffer.append((crawl_id, fp, score, data))

    def complete(self, crawl_id: str, data: str) -> bool:
        """ Store the completed request data in a buffer for later processing."""
        with self.completed_buffer_lock:
            self.completed_buffer.append((crawl_id, data))

    def flush_buffers(self):
        self.flush_push_buffer()
        self.flush_completed_buffer()

    def flush_completed_buffer(self):
        with self.completed_buffer_lock:
            if not self.completed_buffer:
                return
            
        key_to_blob = {}
        
        for crawl_id, data in self.completed_buffer:
            key = self._completed_key(crawl_id)
            if key not in key_to_blob:
                key_to_blob[key] = bytearray()
            key_to_blob[key] += data

        with self.server.pipeline() as pipe:
            for key, blob in key_to_blob.items():
                pipe.append(key, memoryview(blob))
            pipe.execute()

        self.completed_buffer.clear()
        

    def flush_push_buffer(self):
        """
        Push the in-memory buffer to Redis and increment `length_key`
        **only for requests whose fingerprint has not been seen before**.

        ▸ Uses plain HSET (overwrites payload ↔ retry-middleware friendly).  
        ▸ Counts how many HSET replies are `1` → *new* requests.  
        ▸ Adds that count to `length_key` with a single, atomic INCRBY.
        """
        with self.push_buffer_lock:
            if not self.push_buffer:
                return                      # nothing to flush

            # ── 1. Write everything in one pipeline ───────────────────────
            with self.server.pipeline() as pipe:
                for crawl_id, fp, score, data in self.push_buffer:
                    data_key       = self._data_key(crawl_id)
                    pending_key    = self._pending_key(crawl_id)
                    processing_key = self._processing_key(crawl_id)

                    pipe.hset(data_key, fp, data)        # reply: 1 ⇒ new, 0 ⇒ existed
                    pipe.zadd(pending_key, {fp: score})  # enqueue
                    pipe.zrem(processing_key, fp)        # ensure not in processing

                results = pipe.execute()                 # list of replies

            # ── 2. Count *new* insertions (every 3rd reply is from HSET) ───
            new_count = sum(
                1 for i in range(0, len(results), 3) if results[i] == 1
            )

            # ── 3. Update global queue length if needed ────────────────────
            if new_count:
                # INCRBY is itself atomic; no WATCH needed.
                self.server.incrby(self.length_key, new_count)

            # ── 4. Clear local buffer ──────────────────────────────────────
            self.push_buffer.clear()

    # ------------------------------------------------------------------ #
    # atomic take → processing                                            #
    # ------------------------------------------------------------------ #
    _TAKE_PAYLOAD_LUA = """
    -- KEYS[1] = pending    ZSET
    -- KEYS[2] = processing ZSET
    -- KEYS[3] = data       HASH
    -- ARGV[1] = now (unix time, becomes score in KEYS[2])

    local popped = redis.call('ZPOPMIN', KEYS[1], 1)
    if not popped[1] then
        return nil                    -- queue empty
    end

    local fp    = popped[1]
    local prio  = popped[2]

    -- move → processing
    redis.call('ZADD', KEYS[2], ARGV[1], fp)

    -- get pickled payload
    local data  = redis.call('HGET', KEYS[3], fp)

    return {fp, prio, data}           -- array reply
    """

    def __post_init_take_script(self):
        if not hasattr(self, "_take_payload_script"):
            self._take_payload_script = self.server.register_script(self._TAKE_PAYLOAD_LUA)

    def pop(self, crawl_id, timeout=0):
        """Atomically move → processing *and* get the pickled request.

        Returns None when the queue is empty or payload missing.
        """
        self.__post_init_take_script()

        keys = [
            self._pending_key(crawl_id),
            self._processing_key(crawl_id),
            self._data_key(crawl_id),
        ]
        res = self._take_payload_script(keys=keys, args=[time.time()])

        if not res:
            return None  # nothing to pop

        fp, _prio, raw = res
        if raw:
            return self._decode_request(raw)
        # payload unexpectedly missing → clean up
        self.server.zrem(keys[1], fp)  # remove from processing again
        return None

    # ------------------------------------------------------------------ #
    # acknowledge / retry helpers                                         #
    # ------------------------------------------------------------------ #
    def ack(self, crawl_id, fp):
        """Mark the fingerprint as successfully processed."""
        dk = self._data_key(crawl_id)
        qk = self._pending_key(crawl_id)
        pk = self._processing_key(crawl_id)
        with self.server.pipeline() as pipe:
            pipe.zrem(pk, fp)
            pipe.zrem(qk, fp)  # remove from pending queue as well to avoid potential duplicates 
            pipe.hdel(dk, fp)
            pipe.decr(self.length_key)
            pipe.execute()

    def nack(self, crawl_id, fp, request=None, priority=None) -> bool:
        """
        Move *fp* from “processing” back to “pending”, but only if it is
        *still* present in the processing set at commit-time.  The whole
        operation is executed atomically: if another client removes or
        re-queues the same fp meanwhile, we back off and quit without side
        effects.
        """
        pk = self._processing_key(crawl_id)   # processing ZSET
        qk = self._pending_key(crawl_id)      # pending    ZSET
        dk = self._data_key(crawl_id)         # payloads   HASH

        while True:
            try:
                with self.server.pipeline() as pipe:
                    # 1. Watch the processing key for external changes
                    pipe.watch(pk)

                    # 2. Is the fp still in the processing set?
                    if pipe.zscore(pk, fp) is None:
                        pipe.unwatch()         # someone else already handled it
                        return False            # → no retry needed

                    # 3. Build the transaction
                    pipe.multi()
                    pipe.zrem(pk, fp)          # remove from processing

                    if request is not None:
                        pipe.hset(dk, fp, self._encode_request(request))
                        if priority is None:
                            priority = request.priority

                    if priority is None:
                        priority = 0.0

                    # Scrapy: higher priority ⇒ lower ZSET score
                    pipe.zadd(qk, {fp: -priority})

                    # 4. Execute atomically
                    pipe.execute()
                    return True                    # success ─ exit loop

            except WatchError:
                # The watched key changed between WATCH and EXEC.
                # Retry once more; loop keeps attempts cheap and finite.
                continue

    def drop(self, crawl_id: str, fp: str) -> bool:
        """
        Permanently discard *fp* after repeated nack failures.

        • Stores the full pickled request under `:<spider>:queue:dropped:<crawl-id>`
        so it can be inspected or replayed later.
        • Returns True  if the request was still in processing and was dropped.
        Returns False if someone else had already handled it.
        """
        pk  = self._processing_key(crawl_id)   # processing ZSET
        dk  = self._data_key(crawl_id)         # payloads   HASH
        drk = self._dropped_key(crawl_id)      # dropped    HASH

        while True:
            try:
                with self.server.pipeline() as pipe:
                    # ── 1. Watch keys we rely on ───────────────────────────
                    pipe.watch(pk, dk)

                    # Is it still in processing?
                    if pipe.zscore(pk, fp) is None:
                        pipe.unwatch()
                        return False                # already handled elsewhere

                    # Fetch the payload before entering MULTI
                    raw = pipe.hget(dk, fp)          # may be None

                    # ── 2. Atomic removal & archival ──────────────────────
                    pipe.multi()
                    pipe.zrem(pk, fp)                # drop from processing
                    pipe.hdel(dk, fp)                # remove payload
                    pipe.decr(self.length_key)       # global queue length −1
                    if raw is not None:
                        pipe.hset(drk, fp, raw)      # archive full request
                    pipe.execute()
                    break                            # success
            except WatchError:
                # Someone changed pk or dk ⇒ retry once more
                continue

        return True

    def overdue_requests(
        self,
        crawl_ids: Optional[Iterable[str]] = None,
        min_age_seconds: int = 600,      # 10 min default
        max_items: int = 1000,           # 0 ⇒ no limit
    ) -> List[Tuple[str, str, Request]]:
        """
        Return (crawl_id, fp, request) tuples for requests that have sat in the
        *processing* ZSET longer than *min_age_seconds*.

        Args
        ----
        crawl_ids       Iterable of crawl-ids to inspect.
                        •  None  ⇒ scan every crawl-id under this spider.
                        •  str   ⇒ treated as a single-element list.
        min_age_seconds How old a processing entry must be before it is
                        considered “overdue”.  Default = 600 s (10 min).
        max_items       Soft cap on number of tuples returned (0 ⇒ unlimited).
        """
        # Normalise crawl_ids → iterable (or None)
        if isinstance(crawl_ids, str):
            crawl_ids = [crawl_ids]

        now    = time.time()
        cutoff = now - min_age_seconds
        out: List[Tuple[str, str, Request]] = []

        # Helper yields (crawl_id, processing_key)
        def _iter_proc_keys():
            if crawl_ids is not None:
                for crawl_id in crawl_ids:
                    yield crawl_id, self._processing_key(crawl_id)
            else:
                pattern = f"{self.queue_key}:processing:*"
                for key in self.server.scan_iter(pattern):
                    crawl_id = key.decode().rsplit(":", 1)[-1]
                    yield crawl_id, key


        for crawl_id, processing_key in _iter_proc_keys():
            # All fingerprints whose score (timestamp) ≤ cutoff
            fps = self.server.zrangebyscore(processing_key, '-inf', cutoff)
            if not fps:
                continue

            if max_items and len(out) + len(fps) > max_items:
                fps = fps[: max_items - len(out)]

            data_key = self._data_key(crawl_id)
            payloads = self.server.hmget(data_key, *fps)

            for fp, raw in zip(fps, payloads):
                if not raw:
                    continue  # missing payload – skip
                request = self._decode_request(raw)
                fp_str = fp.decode() if isinstance(fp, bytes) else fp
                out.append((crawl_id, fp_str, request))

            if max_items and len(out) >= max_items:
                break  # safety cap reached

        return out
    
    def completed_requests(self, crawl_id: str, chunk_words: int = 1_000_000,) -> np.ndarray:
        """
        Return a single `np.ndarray` of dtype uint64 containing every packed word
        stored under `completed:<crawl_id>`.

        Each word layout:
            bits  0-47  – fingerprint
            bits 48-50  – status
            bits 51-63  – unused
        """
        key = self._completed_key(crawl_id)
        word_size  = 8
        chunk_bytes = chunk_words * word_size

        parts: list[np.ndarray] = []
        start, end = 0, chunk_bytes - 1

        while True:
            raw = self.server.getrange(key, start, end)   # inclusive offsets
            if not raw:
                break
            parts.append(np.frombuffer(raw, dtype="<u8"))  # little-endian uint64
            start += len(raw)
            end   += chunk_bytes

        return np.concatenate(parts).astype(np.uint64, copy=False) if parts else np.empty(0, np.uint64)

    def dropped_requests(self, crawl_id: str) -> list[Request]:
        """
        Return a list of requests that were dropped after repeated nack failures.
        """
        key = self._dropped_key(crawl_id)
        raw_requests = self.server.hvals(key)
        return [self._decode_request(raw) for raw in raw_requests if raw]

    def ignored_requests(self, crawl_id: str) -> list[Request]:
        """
        Return a list of requests that were ignored due to content not allowed, other reasons.
        """
        key = self._ignored_key(crawl_id)
        raw_requests = self.server.lrange(key, 0, -1)
        return [self._decode_request(raw) for raw in raw_requests if raw]

    def push_ignored_request(self, request, reason=None, limit=10):
        """
        Push an ignored request to the queue (limited count).
        """
        crawl_id = request.meta.get("crawl_id")
        if not crawl_id:
            return

        key = self._ignored_key(crawl_id)
        
        # Check limit
        if self.server.llen(key) >= limit:
            return
            
        # Add reason to meta if provided
        if reason:
            request.meta['ignored_reason'] = reason
            
        data = self._encode_request(request)
        self.server.rpush(key, data)

SpiderPriorityQueue = PriorityQueue
