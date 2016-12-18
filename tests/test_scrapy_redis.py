import os

import mock
import redis

from scrapy import Request, Spider
from scrapy.settings import Settings
from scrapy.utils.test import get_crawler
from unittest import TestCase

from scrapy_redis import connection
from scrapy_redis.dupefilter import RFPDupeFilter
from scrapy_redis.queue import FifoQueue, LifoQueue, PriorityQueue
from scrapy_redis.scheduler import Scheduler


# allow test settings from environment
REDIS_HOST = os.environ.get('REDIST_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))


def get_spider(*args, **kwargs):
    crawler = get_crawler(spidercls=kwargs.pop('spidercls', None),
                          settings_dict=kwargs.pop('settings_dict', None))
    return crawler._create_spider(*args, **kwargs)


class RedisTestMixin(object):

    @property
    def server(self):
        if not hasattr(self, '_redis'):
            self._redis = redis.Redis(REDIS_HOST, REDIS_PORT)
        return self._redis

    def clear_keys(self, prefix):
        keys = self.server.keys(prefix + '*')
        if keys:
            self.server.delete(*keys)


class DupeFilterTest(RedisTestMixin, TestCase):

    def setUp(self):
        self.key = 'scrapy_redis:tests:dupefilter:'
        self.df = RFPDupeFilter(self.server, self.key)

    def tearDown(self):
        self.clear_keys(self.key)

    def test_dupe_filter(self):
        req = Request('http://example.com')

        self.assertFalse(self.df.request_seen(req))
        self.assertTrue(self.df.request_seen(req))

        self.df.close('nothing')


class QueueTestMixin(RedisTestMixin):

    queue_cls = None

    def setUp(self):
        self.spider = get_spider(name='myspider')
        self.key = 'scrapy_redis:tests:%s:queue' % self.spider.name
        self.q = self.queue_cls(self.server, Spider('myspider'), self.key)

    def tearDown(self):
        self.clear_keys(self.key)

    def test_clear(self):
        self.assertEqual(len(self.q), 0)

        for i in range(10):
            # XXX: can't use same url for all requests as SpiderPriorityQueue
            # uses redis' set implemention and we will end with only one
            # request in the set and thus failing the test. It should be noted
            # that when using SpiderPriorityQueue it acts as a request
            # duplication filter whenever the serielized requests are the same.
            # This might be unwanted on repetitive requests to the same page
            # even with dont_filter=True flag.
            req = Request('http://example.com/?page=%s' % i)
            self.q.push(req)
        self.assertEqual(len(self.q), 10)

        self.q.clear()
        self.assertEqual(len(self.q), 0)


class FifoQueueTest(QueueTestMixin, TestCase):

    queue_cls = FifoQueue

    def test_queue(self):
        req1 = Request('http://example.com/page1')
        req2 = Request('http://example.com/page2')

        self.q.push(req1)
        self.q.push(req2)

        out1 = self.q.pop()
        out2 = self.q.pop(timeout=1)

        self.assertEqual(out1.url, req1.url)
        self.assertEqual(out2.url, req2.url)


class PriorityQueueTest(QueueTestMixin, TestCase):

    queue_cls = PriorityQueue

    def test_queue(self):
        req1 = Request('http://example.com/page1', priority=100)
        req2 = Request('http://example.com/page2', priority=50)
        req3 = Request('http://example.com/page2', priority=200)

        self.q.push(req1)
        self.q.push(req2)
        self.q.push(req3)

        out1 = self.q.pop()
        out2 = self.q.pop(timeout=0)
        out3 = self.q.pop(timeout=1)

        self.assertEqual(out1.url, req3.url)
        self.assertEqual(out2.url, req1.url)
        self.assertEqual(out3.url, req2.url)


class LifoQueueTest(QueueTestMixin, TestCase):

    queue_cls = LifoQueue

    def test_queue(self):
        req1 = Request('http://example.com/page1')
        req2 = Request('http://example.com/page2')

        self.q.push(req1)
        self.q.push(req2)

        out1 = self.q.pop()
        out2 = self.q.pop(timeout=1)

        self.assertEqual(out1.url, req2.url)
        self.assertEqual(out2.url, req1.url)


class SchedulerTest(RedisTestMixin, TestCase):

    def setUp(self):
        self.key_prefix = 'scrapy_redis:tests:'
        self.queue_key = self.key_prefix + '%(spider)s:requests'
        self.dupefilter_key = self.key_prefix + '%(spider)s:dupefilter'
        self.spider = get_spider(name='myspider', settings_dict={
            'REDIS_HOST': REDIS_HOST,
            'REDIS_PORT': REDIS_PORT,
            'SCHEDULER_QUEUE_KEY': self.queue_key,
            'SCHEDULER_DUPEFILTER_KEY': self.dupefilter_key,
            'SCHEDULER_FLUSH_ON_START': False,
            'SCHEDULER_PERSIST': False,
            'SCHEDULER_SERIALIZER': 'pickle',
            'DUPEFILTER_CLASS': 'scrapy_redis.dupefilter.RFPDupeFilter',
        })
        self.scheduler = Scheduler.from_crawler(self.spider.crawler)

    def tearDown(self):
        self.clear_keys(self.key_prefix)

    def test_scheduler(self):
        # default no persist
        self.assertFalse(self.scheduler.persist)

        self.scheduler.open(self.spider)
        self.assertEqual(len(self.scheduler), 0)

        req = Request('http://example.com')
        self.scheduler.enqueue_request(req)
        self.assertTrue(self.scheduler.has_pending_requests())
        self.assertEqual(len(self.scheduler), 1)

        # dupefilter in action
        self.scheduler.enqueue_request(req)
        self.assertEqual(len(self.scheduler), 1)

        out = self.scheduler.next_request()
        self.assertEqual(out.url, req.url)

        self.assertFalse(self.scheduler.has_pending_requests())
        self.assertEqual(len(self.scheduler), 0)

        self.scheduler.close('finish')

    def test_scheduler_persistent(self):
        # TODO: Improve this test to avoid the need to check for log messages.
        self.spider.log = mock.Mock(spec=self.spider.log)

        self.scheduler.persist = True
        self.scheduler.open(self.spider)

        self.assertEqual(self.spider.log.call_count, 0)

        self.scheduler.enqueue_request(Request('http://example.com/page1'))
        self.scheduler.enqueue_request(Request('http://example.com/page2'))

        self.assertTrue(self.scheduler.has_pending_requests())
        self.scheduler.close('finish')

        self.scheduler.open(self.spider)
        self.spider.log.assert_has_calls([
            mock.call("Resuming crawl (2 requests scheduled)"),
        ])
        self.assertEqual(len(self.scheduler), 2)

        self.scheduler.persist = False
        self.scheduler.close('finish')

        self.assertEqual(len(self.scheduler), 0)


class ConnectionTest(TestCase):

    # We can get a connection from just REDIS_URL.
    def test_redis_url(self):
        settings = Settings({
            'REDIS_URL': 'redis://foo:bar@localhost:9001/42',
        })

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)
        self.assertEqual(connect_args['password'], 'bar')
        self.assertEqual(connect_args['db'], 42)

    # We can get a connection from REDIS_HOST/REDIS_PORT.
    def test_redis_host_port(self):
        settings = Settings({
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 9001,
        })

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)

    # REDIS_URL takes precedence over REDIS_HOST/REDIS_PORT.
    def test_redis_url_precedence(self):
        settings = Settings(dict(
            REDIS_HOST='baz',
            REDIS_PORT=1337,
            REDIS_URL='redis://foo:bar@localhost:9001/42'
        ))

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)
        self.assertEqual(connect_args['password'], 'bar')
        self.assertEqual(connect_args['db'], 42)

    # We fallback to REDIS_HOST/REDIS_PORT if REDIS_URL is None.
    def test_redis_host_port_fallback(self):
        settings = Settings(dict(
            REDIS_HOST='baz',
            REDIS_PORT=1337,
            REDIS_URL=None
        ))

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'baz')
        self.assertEqual(connect_args['port'], 1337)

    # We use default values for REDIS_HOST/REDIS_PORT.
    def test_redis_default(self):
        settings = Settings()

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 6379)
