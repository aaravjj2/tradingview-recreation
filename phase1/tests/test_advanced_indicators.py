"""
Unit tests for Advanced Indicators
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from decimal import Decimal
from services.charting.advanced_indicators import AdvancedIndicators
from services.models import Bar


@pytest.fixture
def sample_bars():
    """Create sample bars with trending pattern"""
    bars = []
    for i in range(200):
        # Create uptrend
        base_price = 100.0 + i * 0.5
        ts_start = int(datetime(2024, 1, 1, 9, 30 + i, tzinfo=timezone.utc).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=i,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=base_price,
            high=base_price + 1.0,
            low=base_price - 1.0,
            close=base_price + 0.5,
            volume=1000 + i * 5,
        )
        bars.append(bar)
    return bars


@pytest.fixture
def indicators():
    return AdvancedIndicators()


class TestAdvancedIndicators:
    def test_anchored_vwap(self, indicators, sample_bars):
        """Test anchored VWAP calculation"""
        anchor_date = sample_bars[0].timestamp
        result = indicators.calculate_anchored_vwap(sample_bars, anchor_date)
        
        assert result is not None
        assert "vwap" in result
        assert "upper_band_1sd" in result
        assert "lower_band_1sd" in result
        assert "upper_band_2sd" in result
        assert "lower_band_2sd" in result
        assert "anchor_date" in result
        
        # VWAP should be within price range
        prices = [float(b.close) for b in sample_bars]
        min_price = min(prices)
        max_price = max(prices)
        
        assert min_price <= result["vwap"] <= max_price
        
        # Upper bands should be above VWAP
        assert result["upper_band_1sd"] > result["vwap"]
        assert result["upper_band_2sd"] > result["upper_band_1sd"]
        
        # Lower bands should be below VWAP
        assert result["lower_band_1sd"] < result["vwap"]
        assert result["lower_band_2sd"] < result["lower_band_1sd"]

    def test_atr_bands(self, indicators, sample_bars):
        """Test ATR bands calculation"""
        result = indicators.calculate_atr_bands(
            sample_bars, period=14, multiplier=2.0
        )
        
        assert result is not None
        assert "middle" in result
        assert "upper" in result
        assert "lower" in result
        assert "atr" in result
        
        # Middle should be recent close price
        recent_close = float(sample_bars[-1].close)
        assert abs(result["middle"] - recent_close) < 1.0
        
        # Upper should be above middle, lower should be below
        assert result["upper"] > result["middle"]
        assert result["lower"] < result["middle"]
        
        # ATR should be positive
        assert result["atr"] > 0

    def test_atr_bands_different_parameters(self, indicators, sample_bars):
        """Test ATR bands with different parameters"""
        # Short period, small multiplier
        result1 = indicators.calculate_atr_bands(
            sample_bars, period=7, multiplier=1.0
        )
        
        # Long period, large multiplier
        result2 = indicators.calculate_atr_bands(
            sample_bars, period=28, multiplier=3.0
        )
        
        # Larger multiplier should create wider bands
        width1 = result1["upper"] - result1["lower"]
        width2 = result2["upper"] - result2["lower"]
        
        assert width2 > width1

    def test_ema_regime(self, indicators, sample_bars):
        """Test EMA regime calculation"""
        result = indicators.calculate_ema_regime(sample_bars)
        
        assert result is not None
        assert "ema_20" in result
        assert "ema_50" in result
        assert "ema_200" in result
        assert "slope_20" in result
        assert "slope_50" in result
        assert "slope_200" in result
        assert "regime" in result
        assert "crossovers" in result
        
        # EMAs should be in reasonable range
        prices = [float(b.close) for b in sample_bars]
        min_price = min(prices)
        max_price = max(prices)
        
        assert min_price <= result["ema_20"] <= max_price
        assert min_price <= result["ema_50"] <= max_price
        assert min_price <= result["ema_200"] <= max_price
        
        # For uptrend data, slope should be positive
        assert result["slope_20"] > 0
        assert result["slope_50"] > 0
        
        # Regime should be a valid string
        assert result["regime"] in ["bullish", "bearish", "neutral"]

    def test_ema_regime_uptrend(self, indicators, sample_bars):
        """Test EMA regime detection in uptrend"""
        result = indicators.calculate_ema_regime(sample_bars)
        
        # With uptrending data, should detect bullish regime
        assert result["regime"] in ["bullish", "neutral"]
        
        # Shorter EMA should be above longer EMA in uptrend
        # (not always true at every point, but generally for strong uptrend)
        if result["regime"] == "bullish":
            assert result["ema_20"] >= result["ema_50"]

    def test_ema_crossovers(self, indicators, sample_bars):
        """Test crossover detection"""
        result = indicators.calculate_ema_regime(sample_bars)
        
        # Crossovers should be a list
        assert isinstance(result["crossovers"], list)
        
        # Each crossover should have required fields
        for crossover in result["crossovers"]:
            assert "type" in crossover
            assert "timestamp" in crossover
            assert crossover["type"] in ["golden_cross", "death_cross"]

    def test_insufficient_data(self, indicators):
        """Test handling of insufficient data"""
        # Create very few bars
        short_bars = []
        for i in range(5):
            ts_start = int(datetime(2024, 1, 1, 9, 30 + i, tzinfo=timezone.utc).timestamp() * 1000)
            bar = Bar(
                symbol="AAPL",
                timeframe="1min",
                bar_index=i,
                ts_start_ms=ts_start,
                ts_end_ms=ts_start + 60000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )
            short_bars.append(bar)
        
        # Should handle gracefully or return None
        result = indicators.calculate_ema_regime(short_bars)
        # Either returns None or returns partial data
        assert result is None or "ema_20" in result

    def test_anchored_vwap_future_anchor(self, indicators, sample_bars):
        """Test anchored VWAP with future anchor date"""
        future_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = indicators.calculate_anchored_vwap(sample_bars, future_date)
        
        # Should handle gracefully (either None or use first bar)
        assert result is None or "vwap" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
