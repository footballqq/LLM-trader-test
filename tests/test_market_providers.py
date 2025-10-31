"""Tests for market data providers."""
from __future__ import annotations

import pandas as pd
import pytest

from market.crypto_binance import CryptoBinanceMarketDataProvider
from market.interfaces import MarketDataProvider


def test_crypto_binance_provider_initialization():
    """Test crypto binance provider initialization."""
    provider = CryptoBinanceMarketDataProvider()
    assert isinstance(provider, MarketDataProvider)


def test_crypto_binance_load_ohlcv_empty(monkeypatch):
    """Test loading OHLCV when API returns empty."""
    from unittest.mock import Mock
    provider = CryptoBinanceMarketDataProvider()
    
    # Mock client to return empty list
    mock_client = Mock()
    mock_client.get_klines.return_value = []
    monkeypatch.setattr(provider, "client", mock_client)
    
    df = provider.load_ohlcv("BTCUSDT", "1m")
    assert isinstance(df, pd.DataFrame)
    assert "datetime" in df.columns
    assert len(df) == 0


@pytest.mark.skip(reason="Requires actual Binance API or more mocking setup")
def test_crypto_binance_load_ohlcv_real():
    """Test loading real OHLCV data (requires API key or mocked client)."""
    provider = CryptoBinanceMarketDataProvider()
    df = provider.load_ohlcv("BTCUSDT", "1m", limit=10)
    assert isinstance(df, pd.DataFrame)
    if len(df) > 0:
        assert "datetime" in df.columns
        assert "open" in df.columns
        assert "close" in df.columns

