from scrapy_redis.utils import bytes_to_str


def test_bytes_to_str():
    assert bytes_to_str(b'\xc3\x81') == u'\xc1'
    assert bytes_to_str(b'\xc3\x81') == u'\xc1'
    assert bytes_to_str(b'\xc1', 'latin1') == u'\xc1'
