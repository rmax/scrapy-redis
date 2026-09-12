import gc
from unittest import mock
import weakref

import pytest
import redis
from scrapy.settings import Settings

from scrapy_redis import connection, defaults
from scrapy_redis.connection import from_settings, get_redis, get_redis_from_settings
from scrapy_redis.dupefilter import RFPDupeFilter
from scrapy_redis.pipelines import RedisPipeline
from scrapy_redis.queue import FifoQueue
from scrapy_redis.scheduler import Scheduler
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.stats import RedisStatsCollector


class TestGetRedis:

    def test_default_instance(self):
        server = get_redis()
        assert isinstance(server, defaults.REDIS_CLS)

    def test_custom_class(self):
        client_cls = mock.Mock()
        server = get_redis(param="foo", redis_cls=client_cls)
        assert server is client_cls.return_value
        client_cls.assert_called_with(param="foo")

    def test_from_url(self):
        client_cls = mock.Mock()
        url = "redis://localhost"
        server = get_redis(redis_cls=client_cls, url=url, param="foo")
        assert server is client_cls.from_url.return_value
        client_cls.from_url.assert_called_with(url, param="foo")


class TestFromSettings:

    def setup(self):
        self.expected_params = {
            "timeout": 0,
            "flag": False,
        }
        self.settings = Settings(
            {
                "REDIS_PARAMS": dict(self.expected_params),
            }
        )

    def test_redis_cls_default(self):
        server = from_settings(Settings())
        assert isinstance(server, defaults.REDIS_CLS)

    def test_redis_cls_custom_path(self):
        self.settings["REDIS_PARAMS"]["redis_cls"] = "unittest.mock.Mock"
        server = from_settings(self.settings)
        assert isinstance(server, mock.Mock)

    def test_default_params(self):
        server = from_settings(self.settings)
        connection_kwargs = server.connection_pool.connection_kwargs
        for key, value in dict(defaults.REDIS_PARAMS, **self.expected_params).items():
            assert connection_kwargs[key] is value or connection_kwargs[key] == value

    def test_override_default_params(self):
        for key, _ in defaults.REDIS_PARAMS.items():
            self.expected_params[key] = self.settings["REDIS_PARAMS"][key] = object()

        server = from_settings(self.settings)
        connection_kwargs = server.connection_pool.connection_kwargs
        for key, value in self.expected_params.items():
            assert connection_kwargs[key] is value


def test_get_server_from_settings_alias():
    assert from_settings is get_redis_from_settings


def test_same_settings_share_a_pool():
    settings = Settings()

    first = connection.get_connection_pool_from_settings(settings)
    second = connection.get_connection_pool_from_settings(settings)

    assert first is second


def test_different_settings_do_not_share_a_pool():
    first_settings = Settings()
    second_settings = Settings()

    first = connection.get_connection_pool_from_settings(first_settings)
    second = connection.get_connection_pool_from_settings(second_settings)

    assert first is not second


def test_different_hosts_do_not_share_a_pool():
    first = connection.get_connection_pool_from_settings(Settings({"REDIS_HOST": "one"}))
    second = connection.get_connection_pool_from_settings(Settings({"REDIS_HOST": "two"}))

    assert first is not second


def test_pool_registry_is_removed_when_settings_are_collected():
    settings = Settings()
    settings_id = id(settings)
    settings_ref = weakref.ref(settings)
    connection.get_connection_pool_from_settings(settings)

    del settings
    gc.collect()

    assert settings_ref() is None
    with connection._POOLS_LOCK:
        assert settings_id not in connection._POOLS_REGISTRY


def test_pool_key_is_type_aware_and_nested():
    key = connection._make_pool_key

    assert key(None, {"value": True}) != key(None, {"value": 1})
    assert key(None, {"value": 1}) != key(None, {"value": 1.0})
    assert key(None, {"value": "1"}) != key(None, {"value": 1})
    assert key(None, {"value": [1]}) != key(None, {"value": (1,)})
    assert key(None, {"value": {1}}) != key(None, {"value": {1, 2}})
    assert key(None, {"value": {1}}) != key(None, {"value": frozenset({1})})
    assert key(None, {"nested": {"value": 1}}) != key(
        None, {"nested": {"value": True}}
    )
    assert key(None, {"nested": {"left": 1, "right": [2, 3]}}) == key(
        None, {"nested": {"right": [2, 3], "left": 1}}
    )


class ComponentSpider(RedisSpider):
    name = "component-spider"


def test_components_share_one_pool_for_one_settings_object():
    settings = Settings({"DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter"})
    crawler = mock.Mock(settings=settings, signals=mock.Mock(), spidercls=ComponentSpider)

    with mock.patch.object(redis.Redis, "ping", return_value=True):
        scheduler = Scheduler.from_settings(settings)
    spider = ComponentSpider.from_crawler(crawler)
    dupefilter = RFPDupeFilter.from_spider(spider)
    pipeline = RedisPipeline.from_settings(settings)
    stats = RedisStatsCollector(crawler, spider=spider)
    queue = FifoQueue(scheduler.server, spider, "component-queue")

    clients = [scheduler.server, dupefilter.server, pipeline.server, spider.server, stats.server]
    pools = [client.connection_pool for client in clients]

    assert all(pool is pools[0] for pool in pools)
    assert queue.server is scheduler.server
    with connection._POOLS_LOCK:
        assert len(connection._POOLS_REGISTRY[id(settings)][1]) == 1


@pytest.mark.parametrize(
    "client_only_params",
    [
        {"single_connection_client": True},
        {"ssl": True, "ssl_cert_reqs": "none"},
        {"unix_socket_path": "/tmp/x.sock"},
    ],
)
def test_client_only_params_use_the_legacy_path(client_only_params):
    settings = Settings({"REDIS_PARAMS": client_only_params})

    with mock.patch("scrapy_redis.connection.get_redis", return_value=mock.sentinel.client) as get_redis_mock:
        client = from_settings(settings)

    assert client is mock.sentinel.client
    get_redis_mock.assert_called_once_with(
        **dict(defaults.REDIS_PARAMS, **client_only_params)
    )
    with connection._POOLS_LOCK:
        assert id(settings) not in connection._POOLS_REGISTRY


def test_custom_client_class_uses_the_legacy_path():
    client_cls = mock.Mock()
    settings = Settings({"REDIS_PARAMS": {"redis_cls": client_cls}})

    client = from_settings(settings)

    assert client is client_cls.return_value
    client_cls.assert_called_once_with(**defaults.REDIS_PARAMS)
    with connection._POOLS_LOCK:
        assert id(settings) not in connection._POOLS_REGISTRY


def test_custom_client_url_uses_the_legacy_from_url_path():
    client_cls = mock.Mock()
    settings = Settings(
        {
            "REDIS_URL": "redis://localhost:6380/3",
            "REDIS_PARAMS": {"redis_cls": client_cls},
        }
    )

    from_settings(settings)

    client_cls.from_url.assert_called_once_with(
        "redis://localhost:6380/3", **defaults.REDIS_PARAMS
    )


def test_max_connections_is_applied_to_the_shared_pool():
    settings = Settings({"REDIS_MAX_CONNECTIONS": "7"})

    pool = connection.get_connection_pool_from_settings(settings)

    assert pool.max_connections == 7


def test_max_connections_setting_takes_precedence():
    settings = Settings(
        {
            "REDIS_MAX_CONNECTIONS": 5,
            "REDIS_PARAMS": {"max_connections": 11},
        }
    )

    pool = connection.get_connection_pool_from_settings(settings)

    assert pool.max_connections == 5


@pytest.mark.parametrize("max_connections", [0, -1, "abc"])
def test_invalid_max_connections_raises(max_connections):
    settings = Settings({"REDIS_MAX_CONNECTIONS": max_connections})

    with pytest.raises(
        ValueError, match="REDIS_MAX_CONNECTIONS must be a positive integer"
    ):
        from_settings(settings)


def test_max_connections_absent_uses_redis_unlimited_sentinel():
    settings = Settings()
    pool = connection.get_connection_pool_from_settings(settings)

    # redis-py 4.x/5.x use 2**31 as the default unlimited sentinel.
    assert pool.max_connections == redis.ConnectionPool().max_connections


def test_connection_pool_escape_hatch_is_passthrough():
    pool = redis.ConnectionPool(max_connections=3)
    settings = Settings({"REDIS_PARAMS": {"connection_pool": pool}})

    client = from_settings(settings)

    assert client.connection_pool is pool
    assert connection.get_connection_pool_from_settings(settings) is pool
    with connection._POOLS_LOCK:
        assert id(settings) not in connection._POOLS_REGISTRY


def test_connection_pool_escape_hatch_keeps_url_out_of_client_kwargs():
    pool = redis.ConnectionPool(max_connections=3)
    settings = Settings(
        {
            "REDIS_URL": "redis://localhost:6380/3",
            "REDIS_PARAMS": {"connection_pool": pool},
        }
    )

    client = from_settings(settings)

    assert client.connection_pool is pool
