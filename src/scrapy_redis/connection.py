import threading
import weakref

import redis
from scrapy.utils.misc import load_object

from . import defaults

# Shortcut maps 'setting name' -> 'parmater name'.
SETTINGS_PARAMS_MAP = {
    "REDIS_URL": "url",
    "REDIS_HOST": "host",
    "REDIS_PORT": "port",
    "REDIS_DB": "db",
    "REDIS_ENCODING": "encoding",
}

SETTINGS_PARAMS_MAP["REDIS_DECODE_RESPONSES"] = "decode_responses"

_POOLS_REGISTRY: dict = {}
_POOLS_LOCK = threading.Lock()


def _canonicalize(value):
    """Return a hashable, type-aware representation of ``value``."""
    value_type = type(value)
    if value is None:
        return ("none", None)
    if value_type in (bool, int, float, complex, str, bytes):
        return (value_type.__name__, value)
    if isinstance(value, dict):
        items = [(_canonicalize(key), _canonicalize(item)) for key, item in value.items()]
        return ("dict", tuple(sorted(items, key=repr)))
    if isinstance(value, list):
        return ("list", tuple(_canonicalize(item) for item in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_canonicalize(item) for item in value))
    if isinstance(value, set):
        return ("set", frozenset(_canonicalize(item) for item in value))
    if isinstance(value, frozenset):
        return ("frozenset", frozenset(_canonicalize(item) for item in value))
    try:
        hash(value)
    except TypeError:
        return ("obj-id", value_type.__name__, id(value))
    return ("obj", value_type.__name__, value)


def _make_pool_key(url, params):
    """Build a collision-safe key for a URL and pool parameters."""
    return _canonicalize(url), _canonicalize(params)


def _get_params_from_settings(settings):
    params = defaults.REDIS_PARAMS.copy()
    params.update(settings.getdict("REDIS_PARAMS"))
    # XXX: Deprecate REDIS_* settings.
    for source, dest in SETTINGS_PARAMS_MAP.items():
        val = settings.get(source)
        if val:
            params[dest] = val
    return params


def _apply_max_connections(settings, params):
    max_connections = settings.get(
        "REDIS_MAX_CONNECTIONS", defaults.REDIS_MAX_CONNECTIONS
    )
    if max_connections is None:
        return

    try:
        max_connections = int(max_connections)
    except (OverflowError, TypeError, ValueError):
        raise ValueError(
            "REDIS_MAX_CONNECTIONS must be a positive integer"
        ) from None
    if max_connections < 1:
        raise ValueError("REDIS_MAX_CONNECTIONS must be a positive integer")
    params["max_connections"] = max_connections


def _register_pools(settings):
    settings_id = id(settings)
    entry = _POOLS_REGISTRY.get(settings_id)
    if entry is not None and entry[0]() is settings:
        return entry[1]

    def cleanup(settings_ref):
        with _POOLS_LOCK:
            current_entry = _POOLS_REGISTRY.get(settings_id)
            if current_entry is not None and current_entry[0] is settings_ref:
                del _POOLS_REGISTRY[settings_id]

    settings_ref = weakref.ref(settings, cleanup)
    pools = {}
    _POOLS_REGISTRY[settings_id] = (settings_ref, pools)
    return pools


def get_connection_pool_from_settings(settings):
    """Return a Redis connection pool shared by one Settings object.

    One pool set is kept per crawler's Settings object, and registry entries
    are removed automatically when that Settings object is garbage-collected.
    ``REDIS_MAX_CONNECTIONS`` limits the shared pool; when it is exhausted,
    redis-py raises ``ConnectionError("Too many connections")``. Waiting
    semantics require supplying an explicit ``BlockingConnectionPool`` via
    ``REDIS_PARAMS["connection_pool"]``.
    """
    params = _get_params_from_settings(settings)
    if "connection_pool" in params:
        return params["connection_pool"]

    url = params.pop("url", None)
    params.pop("redis_cls", None)
    _apply_max_connections(settings, params)

    if not url:
        params.setdefault("host", "localhost")
        params.setdefault("port", 6379)

    pool_key = _make_pool_key(url, params)
    with _POOLS_LOCK:
        pools = _register_pools(settings)
        if pool_key not in pools:
            if url:
                pools[pool_key] = redis.ConnectionPool.from_url(url, **params)
            else:
                pools[pool_key] = redis.ConnectionPool(**params)
        return pools[pool_key]


def get_redis_from_settings(settings):
    """Returns a redis client instance from given Scrapy settings object.

    Shared pools apply to the default Redis client with plain connection
    parameters. Every other configuration keeps the previous per-component
    behavior. ``defaults.REDIS_PARAMS`` provides the default parameters, which
    can be overridden using the ``REDIS_PARAMS`` setting.

    Parameters
    ----------
    settings : Settings
        A scrapy settings object. See the supported settings below.

    Returns
    -------
    server
        Redis client instance.

    Other Parameters
    ----------------
    REDIS_URL : str, optional
        Server connection URL.
    REDIS_HOST : str, optional
        Server host.
    REDIS_PORT : str, optional
        Server port.
    REDIS_DB : int, optional
        Server database
    REDIS_ENCODING : str, optional
        Data encoding.
    REDIS_PARAMS : dict, optional
        Additional client parameters.
    REDIS_MAX_CONNECTIONS : int, optional
        Maximum connections in the shared pool. At exhaustion, redis-py raises
        ``ConnectionError("Too many connections")``; waiting semantics require
        an explicit ``BlockingConnectionPool`` via ``REDIS_PARAMS["connection_pool"]``.

    Python 3 Only
    ----------------
    REDIS_DECODE_RESPONSES : bool, optional
        Sets the `decode_responses` kwarg in Redis cls ctor

    """
    params = _get_params_from_settings(settings)

    # Allow ``redis_cls`` to be a path to a class.
    redis_cls = params.get("redis_cls", defaults.REDIS_CLS)
    if isinstance(redis_cls, str):
        redis_cls = load_object(redis_cls)
        params["redis_cls"] = redis_cls

    if "connection_pool" in params:
        params.pop("redis_cls", None)
        params.pop("url", None)
        return redis_cls(**params)

    shareable = redis_cls is redis.Redis and not {
        "ssl",
        "unix_socket_path",
        "single_connection_client",
    }.intersection(params)
    if not shareable:
        return get_redis(**params)

    pool = get_connection_pool_from_settings(settings)
    return redis_cls(connection_pool=pool)


# Backwards compatible alias.
from_settings = get_redis_from_settings


def get_redis(**kwargs):
    """Returns a redis client instance.

    Parameters
    ----------
    redis_cls : class, optional
        Defaults to ``redis.StrictRedis``.
    url : str, optional
        If given, ``redis_cls.from_url`` is used to instantiate the class.
    **kwargs
        Extra parameters to be passed to the ``redis_cls`` class.

    Returns
    -------
    server
        Redis client instance.

    """
    redis_cls = kwargs.pop("redis_cls", defaults.REDIS_CLS)
    url = kwargs.pop("url", None)
    if url:
        return redis_cls.from_url(url, **kwargs)
    else:
        return redis_cls(**kwargs)
