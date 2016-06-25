#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""A script to process items from a redis queue."""
from __future__ import print_function, unicode_literals

import argparse
import json
import logging
import pprint
import sys
import time

from scrapy_redis import get_redis


logger = logging.getLogger('process_items')


def process_items(r, keys, timeout, limit=0, log_every=1000, wait=.1):
    """Process items from a redis queue.

    Parameters
    ----------
    r : Redis
        Redis connection instance.
    keys : list
        List of keys to read the items from.
    timeout: int
        Read timeout.

    """
    limit = limit or float('inf')
    processed = 0
    while processed < limit:
        # Change ``blpop`` to ``brpop`` to process as LIFO.
        ret = r.blpop(keys, timeout)
        # If data is found before the timeout then we consider we are done.
        if ret is None:
            time.sleep(wait)
            continue

        source, data = ret
        try:
            item = json.loads(data)
        except Exception:
            logger.exception("Failed to load item:\n%r", pprint.pformat(data))
            continue

        try:
            name = item.get('name') or item.get('title')
            url = item.get('url') or item.get('link')
            logger.debug("[%s] Processing item: %s <%s>", source, name, url)
        except KeyError:
            logger.exception("[%s] Failed to process item:\n%r",
                             source, pprint.pformat(item))
            continue

        processed += 1
        if processed % log_every == 0:
            logger.info("Processed %s items", processed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key', help="Redis key where items are stored")
    parser.add_argument('--host')
    parser.add_argument('--port')
    parser.add_argument('--timeout', type=int, default=5)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--progress-every', type=int, default=100)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    params = {}
    if args.host:
        params['host'] = args.host
    if args.port:
        params['port'] = args.port

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    r = get_redis(**params)
    host = r.connection_pool.get_connection('info').host
    logger.info("Waiting for items in '%s' (server: %s)", args.key, host)
    kwargs = {
        'keys': [args.key],
        'timeout': args.timeout,
        'limit': args.limit,
        'log_every': args.progress_every,
    }
    try:
        process_items(r, **kwargs)
        retcode = 0  # ok
    except KeyboardInterrupt:
        retcode = 0  # ok
    except Exception:
        logger.exception("Unhandled exception")
        retcode = 2

    return retcode


if __name__ == '__main__':
    sys.exit(main())
