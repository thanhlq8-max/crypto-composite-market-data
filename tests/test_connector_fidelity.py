"""Connector fidelity: faithful payload fields and venue-legal request params."""

from __future__ import annotations

import pytest

from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.kraken import KrakenConnector
from crypto_composite.connectors.okx import OKXConnector


def test_kraken_quote_volume_uses_payload_vwap(monkeypatch) -> None:
    connector = KrakenConnector()
    # vwap 104 deviates from close 105: quote volume must follow vwap.
    payload = {"error": [], "result": {"XBTUSDT": [
        [1700000000, "100", "110", "90", "105", "104", "2", 12],
    ], "last": 1700000000}}
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    bars = connector.fetch_ohlcv("XBTUSDT", "spot_usdt", "15m", 1)

    assert bars[0].volume_quote == pytest.approx(104.0 * 2.0)


def test_kraken_quote_volume_falls_back_to_close_without_vwap(monkeypatch) -> None:
    connector = KrakenConnector()
    payload = {"error": [], "result": {"XBTUSDT": [
        [1700000000, "100", "110", "90", "105", "0", "2", 12],
    ], "last": 1700000000}}
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    bars = connector.fetch_ohlcv("XBTUSDT", "spot_usdt", "15m", 1)

    assert bars[0].volume_quote == pytest.approx(105.0 * 2.0)


def test_binance_open_interest_uses_exchange_time(monkeypatch) -> None:
    connector = BinanceConnector()
    monkeypatch.setattr(
        connector,
        "_get",
        lambda url, params=None: {"symbol": "BTCUSDT", "openInterest": "100.5", "time": 1700000123456},
    )

    snap = connector.fetch_open_interest("BTCUSDT", "perp_usdt")

    assert snap.timestamp_ms == 1700000123456


def _sent_params(monkeypatch, connector, payload):
    sent: dict = {}

    def fake_get(url: str, params: dict | None = None):
        sent.update(params or {})
        return payload

    monkeypatch.setattr(connector, "_get", fake_get)
    return sent


def test_binance_fapi_depth_snaps_up_to_legal_limit(monkeypatch) -> None:
    connector = BinanceConnector()
    sent = _sent_params(monkeypatch, connector, {"bids": [["100", "1"]], "asks": [["101", "1"]]})

    connector.fetch_orderbook("BTCUSDT", "perp_usdt", 300)
    assert sent["limit"] == 500  # next legal value above 300

    connector.fetch_orderbook("BTCUSDT", "perp_usdt", 3000)
    assert sent["limit"] == 1000  # capped at the maximum


def test_binance_kline_limit_clamped(monkeypatch) -> None:
    connector = BinanceConnector()
    sent = _sent_params(monkeypatch, connector, [])

    connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 5000)
    assert sent["limit"] == 1000


def test_bybit_spot_orderbook_clamped_to_200(monkeypatch) -> None:
    connector = BybitConnector()
    sent = _sent_params(
        monkeypatch, connector, {"retCode": 0, "result": {"b": [["100", "1"]], "a": [["101", "1"]], "ts": 1}}
    )

    connector.fetch_orderbook("BTCUSDT", "spot_usdt", 400)
    assert sent["limit"] == 200

    connector.fetch_orderbook("BTCUSDT", "perp_usdt", 400)
    assert sent["limit"] == 400  # linear allows up to 500


def test_okx_candles_limit_clamped_to_300(monkeypatch) -> None:
    connector = OKXConnector()
    sent = _sent_params(monkeypatch, connector, {"code": "0", "data": []})

    connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 900)
    assert sent["limit"] == 300
