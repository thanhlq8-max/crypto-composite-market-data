"""OKX SWAP payloads report contracts, not base currency; envelopes carry errors.

Live-verified 2026-07-12 on BTC-USDT-SWAP (ctVal 0.01 BTC): candle vol /
volCcy ratio exactly 100, book sz in contracts, oi/oiCcy ratio 100, and a bad
instId returns HTTP 200 with code=51001.
"""

from __future__ import annotations

import pytest

from crypto_composite.connectors import okx as okx_module
from crypto_composite.connectors.base import ConnectorDataError
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.okx import OKXConnector

SWAP = "BTC-USDT-SWAP"
CT_VAL = 0.01


@pytest.fixture(autouse=True)
def _clear_ct_val_cache():
    okx_module._CT_VAL_CACHE.clear()
    yield
    okx_module._CT_VAL_CACHE.clear()


def _instruments_payload():
    return {"code": "0", "data": [{"instId": SWAP, "ctVal": str(CT_VAL), "ctValCcy": "BTC"}]}


def _okx(monkeypatch, routes):
    connector = OKXConnector()

    def fake_get(url: str, params: dict | None = None):
        for token, payload in routes.items():
            if token in url:
                return payload
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)
    return connector


def test_okx_perp_candle_volume_uses_base_currency_column(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "instruments": _instruments_payload(),
        "candles": {"code": "0", "data": [
            ["1000", "64000", "64100", "63900", "64000", "34821.27", "348.2127", "22293261.17"],
        ]},
    })

    bars = connector.fetch_ohlcv(SWAP, "perp_usdt", "15m", 1)

    assert bars[0].volume_base == pytest.approx(348.2127)   # volCcy, not contracts
    assert bars[0].volume_quote == pytest.approx(22293261.17)


def test_okx_perp_candle_missing_volccy_falls_back_to_ct_val(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "instruments": _instruments_payload(),
        "candles": {"code": "0", "data": [["1000", "64000", "64100", "63900", "64000", "100"]]},
    })

    bars = connector.fetch_ohlcv(SWAP, "perp_usdt", "15m", 1)

    assert bars[0].volume_base == pytest.approx(100 * CT_VAL)


def test_okx_spot_candle_volume_unchanged(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "candles": {"code": "0", "data": [
            ["1000", "64000", "64100", "63900", "64018", "11.797", "755663.06", "755663.06"],
        ]},
    })

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 1)

    assert bars[0].volume_base == pytest.approx(11.797)     # spot vol IS base


def test_okx_perp_trades_and_book_scale_by_ct_val(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "instruments": _instruments_payload(),
        "trades": {"code": "0", "data": [
            {"ts": "1010", "px": "64000", "sz": "190.79", "side": "buy", "tradeId": "a"},
        ]},
        "books": {"code": "0", "data": [
            {"ts": "1020", "bids": [["63990", "190.79"]], "asks": [["64010", "50"]]},
        ]},
    })

    trades = connector.fetch_recent_trades(SWAP, "perp_usdt", 1)
    book = connector.fetch_orderbook(SWAP, "perp_usdt", 10)

    assert trades[0].size_base == pytest.approx(1.9079)
    assert book.bids[0] == (63990.0, pytest.approx(1.9079))
    assert book.asks[0] == (64010.0, pytest.approx(0.5))


def test_okx_open_interest_prefers_base_currency_field(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "open-interest": {"code": "0", "data": [
            {"ts": "1030", "oi": "3116838.57", "oiCcy": "31168.3857"},
        ]},
    })

    snap = connector.fetch_open_interest(SWAP, "perp_usdt")

    assert snap.open_interest_base == pytest.approx(31168.3857)


def test_okx_ct_val_fetched_once_per_symbol(monkeypatch) -> None:
    calls = {"instruments": 0}
    connector = OKXConnector()

    def fake_get(url: str, params: dict | None = None):
        if "instruments" in url:
            calls["instruments"] += 1
            return _instruments_payload()
        if "trades" in url:
            return {"code": "0", "data": [
                {"ts": "1010", "px": "64000", "sz": "1", "side": "buy", "tradeId": "a"},
            ]}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)
    connector.fetch_recent_trades(SWAP, "perp_usdt", 1)
    connector.fetch_recent_trades(SWAP, "perp_usdt", 1)

    assert calls["instruments"] == 1


def test_okx_business_error_raises_instead_of_empty(monkeypatch) -> None:
    connector = _okx(monkeypatch, {
        "books": {"code": "51001", "msg": "Instrument ID does not exist.", "data": None},
    })

    with pytest.raises(ConnectorDataError, match="OKX_API_ERROR.*51001"):
        connector.fetch_orderbook("NOT-REAL", "spot_usdt", 10)


def test_bybit_business_error_raises_instead_of_empty(monkeypatch) -> None:
    connector = BybitConnector()
    monkeypatch.setattr(
        connector,
        "_get",
        lambda url, params=None: {"retCode": 10001, "retMsg": "params error", "result": {}},
    )

    with pytest.raises(ConnectorDataError, match="BYBIT_API_ERROR.*10001"):
        connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 1)
