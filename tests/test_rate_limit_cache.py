"""Per-venue token-bucket rate limiting and opt-in TTL response cache."""

from __future__ import annotations

import time

import pytest

from crypto_composite.connectors import base
from crypto_composite.connectors.base import (
    TokenBucket,
    clear_response_cache,
    reset_rate_limiters,
)
from crypto_composite.connectors.binance import BinanceConnector


@pytest.fixture(autouse=True)
def _isolate_shared_state():
    reset_rate_limiters()
    clear_response_cache()
    yield
    reset_rate_limiters()
    clear_response_cache()


def test_token_bucket_burst_then_debt():
    bucket = TokenBucket(rate_per_sec=2.0, burst=3.0)
    assert bucket.acquire() == 0.0
    assert bucket.acquire() == 0.0
    assert bucket.acquire() == 0.0
    # Burst spent: the fourth caller owes one token at 2/s => ~0.5s.
    wait = bucket.acquire()
    assert 0.4 < wait <= 0.51
    # Debt accumulates for the next caller.
    assert bucket.acquire() > wait


def test_token_bucket_refills_over_time(monkeypatch):
    bucket = TokenBucket(rate_per_sec=10.0, burst=1.0)
    assert bucket.acquire() == 0.0
    assert bucket.acquire() > 0.0
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now + 10.0)
    assert bucket.acquire() == 0.0


def test_token_bucket_zero_rate_never_blocks():
    bucket = TokenBucket(rate_per_sec=0.0, burst=1.0)
    assert all(bucket.acquire() == 0.0 for _ in range(20))


class _CountingSession:
    def __init__(self, payload):
        self.calls = 0
        self._payload = payload

    def get(self, url, params=None, timeout=None):
        self.calls += 1

        class _Resp:
            def raise_for_status(self_inner):
                return None

            def json(self_inner):
                return self._payload

        return _Resp()


def _connector(cache_ttl_s=None, payload=None):
    connector = BinanceConnector(cache_ttl_s=cache_ttl_s)
    connector._session = _CountingSession(payload if payload is not None else {"ok": True})
    return connector


def test_cache_disabled_by_default(monkeypatch):
    monkeypatch.delenv(base.CACHE_TTL_ENV_VAR, raising=False)
    connector = _connector()
    connector._get("https://x.test/a", {"s": "1"})
    connector._get("https://x.test/a", {"s": "1"})
    assert connector._session.calls == 2


def test_cache_hit_within_ttl_and_key_sensitivity():
    connector = _connector(cache_ttl_s=60.0)
    connector._get("https://x.test/a", {"s": "1"})
    connector._get("https://x.test/a", {"s": "1"})
    assert connector._session.calls == 1
    connector._get("https://x.test/a", {"s": "2"})
    assert connector._session.calls == 2
    connector._get("https://x.test/b", {"s": "1"})
    assert connector._session.calls == 3


def test_cache_expires_after_ttl(monkeypatch):
    connector = _connector(cache_ttl_s=30.0)
    connector._get("https://x.test/a")
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now + 31.0)
    connector._get("https://x.test/a")
    assert connector._session.calls == 2


def test_cache_env_var_enables(monkeypatch):
    monkeypatch.setenv(base.CACHE_TTL_ENV_VAR, "45")
    connector = _connector()
    connector._get("https://x.test/a")
    connector._get("https://x.test/a")
    assert connector._session.calls == 1


def test_rate_limit_sleeps_after_burst(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

    connector = _connector()
    connector.rate_limit_per_sec = 2.0
    connector.rate_limit_burst = 1.0
    connector._get("https://x.test/a", {"n": "1"})
    connector._get("https://x.test/a", {"n": "2"})
    assert len(sleeps) == 1
    assert 0.4 < sleeps[0] <= 0.51


def test_rate_limit_env_zero_disables(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    monkeypatch.setenv(base.RATE_LIMIT_ENV_VAR, "0")

    connector = _connector()
    connector.rate_limit_burst = 1.0
    for n in range(5):
        connector._get("https://x.test/a", {"n": str(n)})
    assert sleeps == []


def test_buckets_are_shared_per_venue(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

    first = _connector()
    second = _connector()
    for connector in (first, second):
        connector.rate_limit_per_sec = 2.0
        connector.rate_limit_burst = 1.0
    first._get("https://x.test/a", {"n": "1"})
    # Same venue, different instance: shares the budget and must wait.
    second._get("https://x.test/a", {"n": "2"})
    assert len(sleeps) == 1
