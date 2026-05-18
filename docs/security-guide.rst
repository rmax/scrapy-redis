.. _security-guide:

Security Guide
==============

This document outlines security considerations for the scrapy-redis project
and its usage in production environments.

Bandit Scanning
---------------

Bandit runs in CI via ``tox -e security``, scanning ``src/`` and ``tests/``
with the configuration in ``.bandit.yml``:

.. code-block:: bash

    bandit -r -c .bandit.yml src/ tests/

To run locally:

.. code-block:: bash

    pip install bandit
    bandit -r -c .bandit.yml src/ tests/

Dependency Security
-------------------

- **Dependabot**: Enabled on GitHub for automated vulnerability alerts
- **Python packages**: All dependencies are pinned in ``requirements.txt``
  and ``requirements-tests.txt``
- **Minimal runtime deps**: Only ``scrapy`` and ``redis`` are required

Redis Connection Security
-------------------------

Connections are configured via ``REDIS_URL`` or individual settings
(``REDIS_HOST``, ``REDIS_PORT``, ``REDIS_PASSWORD``, etc.) through
the ``scrapy_redis.connection`` module.

**TLS/SSL**: Supported via ``REDIS_URL`` with ``rediss://`` scheme:

.. code-block:: python

    REDIS_URL = "rediss://user:password@host:6379/0"

**Authentication**: Redis passwords are set via ``REDIS_PARAMS``:

.. code-block:: python

    REDIS_PARAMS = {
        "password": os.environ.get("REDIS_PASSWORD"),
    }

Never hardcode Redis credentials in source code. Use environment variables
or Scrapy settings loaded from secure configuration.

Input Validation
----------------

All data read from Redis queues should be validated:

1. **Start URLs** — validated by ``make_request_from_data()`` in
   ``RedisMixin`` (checks for ``url`` key, handles both JSON and plain
   string formats)
2. **Scheduled requests** — validated by ``Scheduler.enqueue_request()``
   (duplicate filtering via request fingerprint)
3. **Queue data** — serialized/deserialized via configurable serializer
   (default: JSON)

Request Fingerprinting
----------------------

The ``RFPDupeFilter`` class uses Scrapy's request fingerprinting to
prevent duplicate processing. This hashes the request method, URL, body,
and headers into a deterministic fingerprint stored in a Redis set.

This prevents:

- Duplicate URL crawling from retry logic
- Multiple spider instances processing the same URL
- Accidental re-submission of identical requests

Known Concerns
--------------

**Pickle serialization**: The ``SCHEDULER_SERIALIZER`` setting defaults to
JSON. ``pickle`` is supported as an alternative serializer but should be
used with caution — never unpickle data from untrusted sources.
When possible, avoid ``pickle`` and use the default JSON serializer.

**Redis queue persistence**: The ``SCHEDULER_PERSIST`` setting controls
whether the Redis queue survives spider restarts. When ``True``, ensure
your Redis instance has appropriate persistence (RDB/AOF) configured.

**Redis exposure**: In production, Redis should not be exposed to the
public internet. Use VPCs, firewalls, or SSH tunnels. Consider Redis
TLS and password authentication.

**Data isolation**: Multi-tenant deployments should use separate Redis
databases or separate keyspaces per tenant to prevent data leakage.

Configuration Security
----------------------

- Scrapy settings are Python code — use ``os.environ.get()`` for secrets
- ``REDIS_URL`` in environment variables overrides individual settings
- Avoid committing ``scrapy.cfg`` or settings files with production secrets
- Use ``.env`` files for local development (already in ``.gitignore``)

CI Security
-----------

- Dependabot monitors for vulnerable dependencies monthly
- Bandit runs security linting on every PR
- Pre-commit checks for debug statements (``pdb.set_trace()``,
  ``breakpoint()``, ``import pdb``)
- No secrets stored in CI configuration
