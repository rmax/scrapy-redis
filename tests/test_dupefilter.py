from unittest import mock

from scrapy.http import Request
from scrapy.settings import Settings

from scrapy_redis.dupefilter import RFPDupeFilter


def get_redis_mock():
    server = mock.Mock()

    def sadd(key, fp, added=0, db={}):  # noqa: mutable db
        fingerprints = db.setdefault(key, set())
        if fp not in fingerprints:
            fingerprints.add(fp)
            added += 1
        return added

    server.sadd = sadd

    return server


class TestRFPDupeFilter:

    def setup(self):
        self.server = get_redis_mock()
        self.key = "dupefilter:1"
        self.df = RFPDupeFilter(self.server, self.key)

    def test_request_seen(self):
        req = Request("http://example.com")

        def same_request():
            assert not self.df.request_seen(req)
            assert self.df.request_seen(req)

        def diff_method():
            diff_method = Request("http://example.com", method="POST")
            assert self.df.request_seen(req)
            assert not self.df.request_seen(diff_method)

        def diff_url():
            diff_url = Request("http://example2.com")
            assert self.df.request_seen(req)
            assert not self.df.request_seen(diff_url)

        same_request()
        diff_method()
        diff_url()

    def test_overridable_request_fingerprinter(self):
        req = Request("http://example.com")
        self.df.request_fingerprint = mock.Mock(wraps=self.df.request_fingerprint)
        assert not self.df.request_seen(req)
        self.df.request_fingerprint.assert_called_with(req)

    def test_clear_deletes(self):
        self.df.clear()
        self.server.delete.assert_called_with(self.key)

    def test_close_calls_clear(self):
        self.df.clear = mock.Mock(wraps=self.df.clear)
        self.df.close()
        self.df.close(reason="foo")
        assert self.df.clear.call_count == 2


def test_log_dupes():
    def _test(df, dupes, logcount):
        df.logger.debug = mock.Mock(wraps=df.logger.debug)
        for _ in range(dupes):
            req = Request("http://example")
            df.log(req, spider=mock.Mock())
        assert df.logger.debug.call_count == logcount

    server = get_redis_mock()

    df_quiet = RFPDupeFilter(server, "foo")  # debug=False
    _test(df_quiet, 5, 1)

    df_debug = RFPDupeFilter(server, "foo", debug=True)
    _test(df_debug, 5, 5)


@mock.patch("scrapy_redis.dupefilter.get_redis_from_settings")
class TestFromMethods:

    def setup(self):
        self.settings = Settings(
            {
                "DUPEFILTER_DEBUG": True,
            }
        )

    def test_from_settings(self, get_redis_from_settings):
        df = RFPDupeFilter.from_settings(self.settings)
        self.assert_dupefilter(df, get_redis_from_settings)

    def test_from_crawler(self, get_redis_from_settings):
        crawler = mock.Mock(settings=self.settings)
        df = RFPDupeFilter.from_crawler(crawler)
        self.assert_dupefilter(df, get_redis_from_settings)

    def assert_dupefilter(self, df, get_redis_from_settings):
        assert df.server is get_redis_from_settings.return_value
        assert df.key.startswith("dupefilter:")
        assert df.debug  # true
