import marshal
from scrapy.utils.reqser import request_to_dict, request_from_dict


class SpiderQueue(object):
    """Per-spider queue abstraction on top of redis using sorted set"""

    def __init__(self, server, spider, key):
        """Initialize per-spider redis queue

        Parameters:
            server -- redis connection
            spider -- spider instance
            key -- key for this queue (e.g. "%(spider)s:queue")

        """
        self.server = server
        self.spider = spider
        self.key = key % {'spider': spider.name}

    def __len__(self):
        return self.server.zcard(self.key)

    def push(self, request):
        data = marshal.dumps(request_to_dict(request, self.spider))
        pairs = {data: -request.priority}
        self.server.zadd(self.key, **pairs)

    def pop(self):
        # use atomic range/remove using multi/exec
        pipe = self.server.pipeline()
        pipe.multi()
        pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
        results, count = pipe.execute()
        if results:
            return request_from_dict(marshal.loads(results[0]), self.spider)

    def clear(self):
        self.server.delete(self.key)

