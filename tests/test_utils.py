from scrapy_redis.utils import bytes_to_str


def test_bytes_to_str():
    assert bytes_to_str(b'foo') == 'foo'
    # This char is the same in bytes or latin1.
    assert bytes_to_str(b'\xc1', 'latin1') == '\xc1'
