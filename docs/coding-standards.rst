.. _coding-standards:

Python Coding Standards
=======================

This document defines the Python coding conventions for scrapy-redis.
These apply to all code in ``src/``, ``tests/``, and related scripts.

Style Guide
-----------

- **Line length**: Maximum 120 characters (enforced by flake8)
- **Indentation**: 4 spaces, no tabs
- **Quotes**: Double quotes (``"``) for strings, single quotes (``'``) for docstrings
- **Imports**: One import per line, standard library first, then third-party, then local
- **Spacing**: Two blank lines around class definitions, one around method definitions
- **Naming**: ``snake_case`` for functions/methods/variables, ``PascalCase`` for classes,
  ``UPPER_CASE`` for constants and settings

Linting & Formatting
--------------------

Linting is done by flake8 with these exceptions (configured in ``.flake8``):

- ``D`` — docstring enforcement is opt-in, not CI-enforced
- ``E203`` — whitespace before ``:`` (conflicts with black)
- ``W503`` — line break before binary operator (conflicts with PEP 8 recommended style)
- ``P102`` — deprecated pylint checks
- ``P103`` — deprecated pylint checks

Full flake8 command (from ``tox.ini``):

.. code-block:: bash

    flake8 --ignore=W503,E265,E731 docs src tests

Excluded directories: ``.git``, ``__pycache__``, ``.venv``, ``build``, ``dist``,
``docs``, ``tests``, ``example-project``.

Type Hints
----------

All public API methods should have type hints:

.. code-block:: python

    def next_requests(self) -> Iterator[FormRequest]:
        ...

    def _normalize_redis_key(
        self, redis_key: str | list[str]
    ) -> tuple[str, list[str] | None]:
        ...

Use ``str | list[str]`` (Python 3.10+ union syntax) or ``Union[str, List[str]]``
for Python 3.7 compatibility. The project targets Python 3.7+.

Docstrings
----------

Use NumPy/Google style for compatibility with ``sphinx.ext.napoleon``:

.. code-block:: python

    def setup_redis(self, crawler=None):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.

        Parameters
        ----------
        crawler : Crawler, optional
            The Scrapy crawler instance. If None, attempts to get it from
            the spider's ``crawler`` attribute.

        Raises
        ------
        ValueError
            If crawler is None or redis_key is empty.
        """
        ...

Best Practices
--------------

**Polymorphic parameters**: Use ``isinstance()`` for type-dispatch:

.. code-block:: python

    def _normalize_redis_key(self, redis_key):
        if isinstance(redis_key, str):
            ...
        elif isinstance(redis_key, list):
            ...
        return redis_key, None

**Backward compatibility**: Never change existing behavior without opt-in.
Prefer ``isinstance`` guards over mode flags or breaking changes.

**Private methods**: Prefix internal helpers with ``_``.
Make helpers single-purpose and testable.

**Logging**: Use structured logging (``%``-style format strings with dicts):

.. code-block:: python

    self.logger.info(
        "Reading start URLs from redis key '%(redis_key)s' "
        "(batch size: %(redis_batch_size)s)",
        self.__dict__,
    )

**None checks**: Always use ``is``:

.. code-block:: python

    if value is None:      # correct
    if value is not None:  # correct
    if not value:          # wrong — treats empty list, 0, False as None

**Exception handling**: Be specific:

.. code-block:: python

    # Good
    try:
        self.redis_batch_size = int(self.redis_batch_size)
    except (TypeError, ValueError):
        raise ValueError("redis_batch_size must be an integer")

    # Bad
    try:
        ...
    except:
        ...

**Context managers**: Use for resource management:

.. code-block:: python

    with self.server.pipeline() as pipe:
        pipe.lrange(redis_key, 0, batch_size - 1)
        pipe.ltrim(redis_key, batch_size, -1)
        datas, _ = pipe.execute()

**Comprehensions over map/filter**:

.. code-block:: python

    # Good
    urls = [f"http://example.com/{i}" for i in range(5)]
    non_empty = [k for k in keys if k.strip()]

    # Avoid
    urls = list(map(lambda i: f"http://example.com/{i}", range(5)))
