#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import redis


def main():
    r = redis.Redis()
    while True:
        # process queue as FIFO, change `blpop` to `brpop` to process as LIFO
        source, data = r.blpop(["dmoz:items"])
        item = json.loads(data)
        try:
            print u"Processing: %(name)s <%(link)s>" % item
        except KeyError:
            print u"Error procesing: %r" % item


if __name__ == '__main__':
    main()
