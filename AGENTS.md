# scrapy-redis — Agent Guide

This file documents everything an AI agent (or new contributor) needs to work effectively on this project. It covers conventions, architecture, workflows, and best practices.

## Quick Start

```bash
git clone https://github.com/rmax/scrapy-redis.git
cd scrapy-redis
pip install -e .
pip install -r docs/requirements.txt    # Sphinx, etc.
pip install pre-commit && pre-commit install
pip install -r requirements-tests.txt   # pytest, tox, etc.
```

### Run Tests

```bash
# Unit tests (no Redis needed for FakeRedisServer tests)
python -m pytest tests/test_spiders.py -v

# Full test suite with tox (requires Docker for Redis service)
tox -e pytest

# All environments
tox
```

### Pre-commit

```bash
pre-commit run --all-files
```

## Architecture

### Key Modules (`src/scrapy_redis/`)

| File | Responsibility |
|------|---------------|
| `spiders.py` | `RedisMixin`, `RedisSpider`, `RedisCrawlSpider` — reads start URLs from Redis queues |
| `scheduler.py` | `Scheduler` — enqueues/dequeues crawled requests via Redis |
| `dupefilter.py` | `RFPDupeFilter` — request fingerprint deduplication via Redis |
| `queue.py` | Queue classes (LifoQueue, FifoQueue, PriorityQueue) for Redis-backed request queues |
| `pipelines.py` | `RedisPipeline` — pushes scraped items to Redis |
| `connection.py` | Redis connection management from Scrapy settings |
| `defaults.py` | Default settings values |

### RedisMixin / RedisSpider

The central class is `RedisMixin`. It's used by `RedisSpider(RedisMixin, Spider)` and `RedisCrawlSpider(RedisMixin, CrawlSpider)`.

Key flow:
1. `setup_redis(crawler)` — initializes Redis connection, queue type (SET/ZSET/LIST), polling
2. `start_requests()` → `next_requests()` → `fetch_data(redis_key, batch_size)` — fetches URLs
3. `spider_idle()` → `schedule_next_requests()` — re-fetches when idle
4. `spider_idle_start_time` + `max_idle_time` control when the spider closes

### Multi-Key Mode

Since PR #311, `redis_key` accepts `str` (unchanged) or `list[str]` (priority-ordered, index 0 = highest). Multi-key behavior:
- Selects first non-empty queue by priority order
- Drains current queue for throughput
- Optional `redis_key_check_interval` (seconds, default None) for periodic preemption
- Checks are elapsed wall-clock time at method entry — no threads or Twisted reactors
- All keys share the same globally configured queue type (SET/ZSET/LIST)
- Keys are templated (`% {"name": self.name}`), deduplicated preserving order, validated

Internal helpers: `_normalize_redis_key()`, `_select_priority_key()`, `_maybe_switch_to_higher_priority_key()`, `_maybe_check_priority_scan()`, `_any_key_has_items()`.

### Class Hierarchy

```
RedisMixin
├── RedisSpider (RedisMixin + Spider)       — general-purpose crawler
└── RedisCrawlSpider (RedisMixin + CrawlSpider) — rule-based crawler

Scheduler — request scheduling via Redis queues
RFPDupeFilter — duplicate detection via Redis sets
RedisPipeline — item persistence to Redis
```

## Coding Conventions

See [docs/coding-standards.rst](docs/coding-standards.rst) for the full guide. Key points:

- **Style**: PEP 8, 120 char line limit (enforced by flake8)
- **Docstrings**: NumPy/Google style (napoleon-compatible Sphinx autodoc)
- **Type hints**: Use for all public API methods. Python 3.7+ compatible typing.
- **Naming**: `snake_case` for methods/variables, `PascalCase` for classes, `UPPER_CASE` for settings/constants
- **Private methods**: Prefix with `_` (Python convention)
- **Formatting**: f-strings preferred for logging (but respect existing `%`-style logger patterns)
- **Testing**: `FakeRedisServer` for unit tests (no real Redis), mocks for Scrapy internals. Real Redis in tox integration tests.
- **Backward compatibility**: Critical for this project (Scrapy plugin ecosystem). Don't break existing behavior. Prefer `isinstance()` type guards over mode flags.

### Python Design Principles

- Favor composition over inheritance (RedisMixin is an exception as a standard mixin)
- `isinstance()` for polymorphic parameters (e.g., `redis_key` being `str | list[str]`)
- Type hints on all public API methods
- Simple boolean checks over complex branching
- Context managers for resource management
- Specific exception handling, not bare `except:`
- List comprehensions over `map()`/`filter()`
- `is` for `None` checks, not `==`
- Avoid threads — Scrapy is Twisted-based, threads introduce race conditions

## Testing

### Test Structure (`tests/`)

| File | What it tests |
|------|--------------|
| `test_spiders.py` | RedisMixin, RedisSpider, RedisCrawlSpider |
| `test_queue.py` | Queue implementations |
| `test_dupefilter.py` | RFPDupeFilter |
| `test_scheduler.py` | Scheduler |
| `test_connection.py` | Redis connection |
| `test_utils.py` | Utility functions |
| `test_package_import.py` | Package import sanity check |

### FakeRedisServer Pattern

New tests use `FakeRedisServer` — an in-memory mock that implements `pipeline()`, `rpush()`, `lrange()`, `ltrim()`, `llen()`, `sadd()`, `spop()`, `scard()`, `zadd()`, `zrevrange()`, `zremrangebyrank()`, `zcard()`, and `flushall()`. This avoids needing a real Redis server for unit tests.

```python
def make_spider(self, **kwargs):
    with patched_redis(self.server):
        return MySpider.from_crawler(self.crawler, **kwargs)
```

Use `patched_redis(server)` context manager to inject `FakeRedisServer` as the connection.

### Tox Matrix

Tests run across Python 3.8-3.12, Scrapy 2.6-2.11, Redis 4.2-5.0. The CI only tests Python 3.12 by default. The full matrix runs on demand.

## Documentation

- **Format**: RST (reStructuredText) for Sphinx
- **Build**: `cd docs && make html` or `tox -e docs`
- **CI**: Runs with `-W --keep-going -D language=en` (warnings as errors)
- **Extensions**: `sphinx.ext.autodoc`, `sphinx.ext.napoleon`, `sphinx.ext.viewcode`
- **API docs auto-generated**: `sphinx-apidoc -o docs/ src/scrapy_redis`

### Docstring Requirements

Docstrings should follow NumPy/Google style for napoleon compatibility:

```python
def my_method(self, param1, param2):
    """Short description.

    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int, optional
        Description of param2.

    Returns
    -------
    bool
        Description of return value.
    """
```

## Pre-commit

Configured in `.pre-commit-config.yaml`:

| Hook | Purpose |
|------|---------|
| `trailing-whitespace` | Removes trailing whitespace |
| `end-of-file-fixer` | Ensures files end with newline |
| `check-yaml` | Validates YAML files |
| `check-added-large-files` | Prevents committing large files |
| `check-merge-conflict` | Detects merge conflict markers |
| `debug-statements` | Catches `pdb.set_trace()` / `breakpoint()` |
| `check-json` | Validates JSON files |
| `flake8` | Linting (120 char, flake8-docstrings) |

To update: edit `.pre-commit-config.yaml` and run `pre-commit autoupdate`.

## CI/CD (GitHub Actions)

| Workflow | File | What it does |
|----------|------|-------------|
| **test** | `.github/workflows/tests.yml` | pytest with tox + real Redis (Docker) |
| **check** | `.github/workflows/checks.yml` | flake8, bandit security scan, pre-commit |
| **docs** | `.github/workflows/docs.yml` | Sphinx build with `-W` (warnings→errors) |
| **build** | `.github/workflows/builds.yml` | Cross-platform build test (ubuntu/macos/windows) |

### Debugging CI Failures

```bash
# Get failed run ID
gh run list --branch feat/my-branch --limit 5

# View failed logs
gh run view <RUN_ID> --log-failed
```

### PR Checks Status

```bash
gh pr checks 311
gh pr checks 311 --watch   # poll until done
```

## Security

See [docs/security-guide.rst](docs/security-guide.rst) for the full guide.

- **Bandit**: Runs in CI via `tox -e security`. Configured in `.bandit.yml`.
- **No hardcoded credentials**: Redis connections use settings/env vars, never hardcoded values.
- **Input validation**: All data from Redis queues is validated before processing.
- **Request fingerprinting**: DupeFilter uses hashed fingerprints, not raw URLs.
- **Dependency scanning**: Dependabot monitors for vulnerable dependencies.

## PR Workflow

### Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Maintenance, tooling, CI |
| `docs/` | Documentation |
| `refactor/` | Code restructuring |
| `test/` | Test improvements |

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add optional multi-key priority support for RedisSpider

- redis_key can now be str (unchanged) or list[str]
- Priority-ordered consumption (index 0 = highest)

Closes #310
Co-authored-by: Name <email>
```

### Creating a PR

```bash
git checkout -b feat/my-feature
# ... make changes ...
git add -A && git commit -m "feat: description"
git push -u origin HEAD
gh pr create \
  --title "feat: description" \
  --body "Implements #N\n\n## Changes\n- ...\n\nCloses #N" \
  --base master
```

### Co-Author Credit

Add `Co-authored-by: Name <email>` in commit messages or PR body using GitHub's noreply email format: `<user-id>+<username>@users.noreply.github.com`.

### Merging

Always squash merge into master from a feature branch:
```bash
gh pr merge --squash --delete-branch
```

## Dependency Management

| File | Purpose |
|------|---------|
| `requirements.txt` | Runtime deps (scrapy, redis) |
| `requirements-tests.txt` | Test deps (pytest, tox, mock, coverage) |
| `docs/requirements.txt` | Docs deps (Sphinx, bumpversion, twine) |

## Release Process

1. `bumpversion release` (or `patch`/`minor`/`major`)
2. Update `HISTORY.rst`
3. Commit and tag: `git tag -a $(cat VERSION)`
4. Push: `git push --follow-tags`
5. CI deploys to PyPI automatically

## Related Documentation

- [docs/coding-standards.rst](docs/coding-standards.rst) — Full Python coding standards
- [docs/security-guide.rst](docs/security-guide.rst) — Security best practices
- [docs/contributing.rst](docs/contributing.rst) — Contributor guide
