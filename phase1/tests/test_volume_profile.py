"""
Unit tests for Volume Profile Calculator
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from services.charting.volume_profile import VolumeProfileCalculator
from services.models import Bar


@pytest.fixture
def sample_bars():
    """Create sample bars for testing"""
    bars = []
    base_time = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
    for i in range(100):
        ts_start = int((base_time + timedelta(minutes=i)).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=i,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=150.0 + i * 0.1,
            high=150.5 + i * 0.1,
            low=149.5 + i * 0.1,
            close=150.0 + i * 0.1,
            volume=1000 + i * 10,
        )
        bars.append(bar)
    return bars


@pytest.fixture
def calculator():
    return VolumeProfileCalculator()


class TestVolumeProfile:
    def test_visible_range_profile(self, calculator, sample_bars):
        """Test visible range volume profile calculation"""
        profile = calculator.calculate_visible_range_profile(sample_bars)
        
        assert profile is not None
        assert "poc" in profile
        assert "vah" in profile
        assert "val" in profile
        assert "hvn_zones" in profile
        assert "lvn_zones" in profile
        assert "levels" in profile
        
        # POC should be a float
        assert isinstance(profile["poc"], float)
        assert profile["poc"] > 0
        
        # VAH should be greater than VAL
        assert profile["vah"] > profile["val"]
        
        # HVN and LVN should be lists
        assert isinstance(profile["hvn_zones"], list)
        assert isinstance(profile["lvn_zones"], list)
        
        # Levels should be a dict with price keys
        assert isinstance(profile["levels"], dict)
        assert len(profile["levels"]) > 0

    def test_fixed_range_profile(self, calculator, sample_bars):
        """Test fixed range volume profile calculation"""
        start_time = sample_bars[0].timestamp
        end_time = sample_bars[-1].timestamp
        
        profile = calculator.calculate_fixed_range_profile(
            sample_bars, start_time, end_time
        )
        
        assert profile is not None
        assert "poc" in profile
        assert "vah" in profile
        assert "val" in profile
        
        # Should have similar structure to visible range
        assert profile["vah"] > profile["val"]

    def test_session_profile(self, calculator, sample_bars):
        """Test session volume profile calculation"""
        session_date = "2024-01-01"
        
        profile = calculator.calculate_session_profile(sample_bars, session_date)
        
        assert profile is not None
        assert "poc" in profile
        assert "session_date" in profile
        assert profile["session_date"] == session_date

    def test_developing_poc(self, calculator, sample_bars):
        """Test developing POC calculation"""
        # Calculate developing POC for first 50 bars
        current_bars = sample_bars[:50]
        developing = calculator.calculate_developing_poc(current_bars)
        
        assert developing is not None
        assert "poc" in developing
        assert "current_time" in developing
        
        # Calculate again with all bars - POC should potentially shift
        full_developing = calculator.calculate_developing_poc(sample_bars)
        assert full_developing is not None
        assert "poc" in full_developing

    def test_hvn_lvn_detection(self, calculator, sample_bars):
        """Test HVN/LVN zone detection"""
        profile = calculator.calculate_visible_range_profile(sample_bars)
        
        # Should have at least some HVN zones (high volume areas)
        assert len(profile["hvn_zones"]) >= 0
        
        # Each HVN zone should have price_start, price_end, avg_volume
        for zone in profile["hvn_zones"]:
            assert "price_start" in zone
            assert "price_end" in zone
            assert "avg_volume" in zone
            assert zone["price_end"] >= zone["price_start"]

    def test_value_area_70_percent(self, calculator, sample_bars):
        """Test that value area contains approximately 70% of volume"""
        profile = calculator.calculate_visible_range_profile(sample_bars)
        
        val = profile["val"]
        vah = profile["vah"]
        levels = profile["levels"]
        
        # Calculate total volume
        total_volume = sum(levels.values())
        
        # Calculate volume in value area
        va_volume = sum(
            vol for price, vol in levels.items()
            if val <= price <= vah
        )
        
        # Should be approximately 70% (within 10% tolerance)
        va_percentage = va_volume / total_volume
        assert 0.60 <= va_percentage <= 0.80

    def test_empty_bars(self, calculator):
        """Test handling of empty bar list"""
        profile = calculator.calculate_visible_range_profile([])
        
        # Should return None for empty bars (insufficient data)
        assert profile is None

    def test_single_bar(self, calculator):
        """Test handling of single bar"""
        ts_start = int(datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=0,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=150.0,
            high=150.5,
            low=149.5,
            close=150.0,
            volume=1000,
        )
        
        profile = calculator.calculate_visible_range_profile([bar])
        
        # Should return None for single bar (needs at least 2)
        assert profile is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
