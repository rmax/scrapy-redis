import mock

from scrapy.settings import Settings

from scrapy_redis import defaults
from scrapy_redis.connection import (
    from_settings,
    get_redis,
    get_redis_from_settings,
)


class TestGetRedis(object):

    def test_default_instance(self):
        server = get_redis()
        assert isinstance(server, defaults.REDIS_CLS)

    def test_custom_class(self):
        client_cls = mock.Mock()
        server = get_redis(param='foo', redis_cls=client_cls)
        assert server is client_cls.return_value
        client_cls.assert_called_with(param='foo')

    def test_from_url(self):
        client_cls = mock.Mock()
        url = 'redis://localhost'
        server = get_redis(redis_cls=client_cls, url=url, param='foo')
        assert server is client_cls.from_url.return_value
        client_cls.from_url.assert_called_with(url, param='foo')


class TestFromSettings(object):

    def setup(self):
        self.redis_cls = mock.Mock()
        self.expected_params = {
            'timeout': 0,
            'flag': False,
        }
        self.settings = Settings({
            'REDIS_PARAMS': dict(self.expected_params, redis_cls=self.redis_cls),
        })

    def test_redis_cls_default(self):
        server = from_settings(Settings())
        assert isinstance(server, defaults.REDIS_CLS)

    def test_redis_cls_custom_path(self):
        self.settings['REDIS_PARAMS']['redis_cls'] = 'mock.Mock'
        server = from_settings(self.settings)
        assert isinstance(server, mock.Mock)

    def test_default_params(self):
        server = from_settings(self.settings)
        assert server is self.redis_cls.return_value
        self.redis_cls.assert_called_with(**dict(defaults.REDIS_PARAMS, **self.expected_params))

    def test_override_default_params(self):
        for key, val in defaults.REDIS_PARAMS.items():
            self.expected_params[key] = self.settings['REDIS_PARAMS'][key] = object()

        server = from_settings(self.settings)
        assert server is self.redis_cls.return_value
        self.redis_cls.assert_called_with(**self.expected_params)


def test_get_server_from_settings_alias():
    assert from_settings is get_redis_from_settings
