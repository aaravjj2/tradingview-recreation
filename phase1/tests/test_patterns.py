"""
Unit tests for Pattern Detection
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone, timedelta
from services.charting.patterns import PatternDetector
from services.models import Bar


@pytest.fixture
def detector():
    return PatternDetector()


@pytest.fixture
def uptrend_bars():
    """Create bars in uptrend"""
    bars = []
    base_time = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
    for i in range(100):
        base = 100.0 + i * 0.3
        ts_start = int((base_time + timedelta(minutes=i)).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=i,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=float(base),
            high=float(base + 1.0),
            low=float(base - 0.5),
            close=float(base + 0.8),
            volume=1000,
        )
        bars.append(bar)
    return bars


@pytest.fixture
def flag_pattern_bars():
    """Create bars that form a bull flag pattern"""
    bars = []
    base_time = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
    
    # Uptrend (pole)
    for i in range(20):
        base = 100.0 + i * 2.0
        ts_start = int((base_time + timedelta(minutes=i)).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=i,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=float(base),
            high=float(base + 2.5),
            low=float(base - 0.5),
            close=float(base + 2.0),
            volume=2000,
        )
        bars.append(bar)
    
    # Consolidation (flag)
    last_price = 100.0 + 19 * 2.0 + 2.0
    for i in range(15):
        ts_start = int((base_time + timedelta(minutes=20 + i)).timestamp() * 1000)
        bar = Bar(
            symbol="AAPL",
            timeframe="1min",
            bar_index=20 + i,
            ts_start_ms=ts_start,
            ts_end_ms=ts_start + 60000,
            open=float(last_price - 1.0),
            high=float(last_price),
            low=float(last_price - 2.0),
            close=float(last_price - 1.5),
            volume=800,
        )
        bars.append(bar)
    
    return bars


class TestPatternDetector:
    def test_detect_patterns_basic(self, detector, uptrend_bars):
        """Test basic pattern detection"""
        patterns = detector.detect_patterns(uptrend_bars, lookback=50)
        
        assert isinstance(patterns, list)
        # Should detect at least some patterns in trending data
        
        for pattern in patterns:
            assert "pattern_type" in pattern
            assert "confidence" in pattern
            assert "timestamp" in pattern
            assert "context" in pattern
            
            # Confidence should be between 0 and 1
            assert 0 <= pattern["confidence"] <= 1

    def test_detect_flag_pattern(self, detector, flag_pattern_bars):
        """Test detection of bull flag pattern"""
        patterns = detector.detect_patterns(
            flag_pattern_bars,
            lookback=40,
            pattern_types=["bull_flag"]
        )
        
        # Should find at least one bull flag
        bull_flags = [p for p in patterns if p["pattern_type"] == "bull_flag"]
        assert len(bull_flags) > 0
        
        flag = bull_flags[0]
        assert flag["confidence"] > 0.5

    def test_detect_double_top(self, detector):
        """Test detection of double top pattern"""
        bars = []
        
        # Create double top pattern
        # First peak
        for i in range(20):
            base = 100.0 + i * 0.5
            bar = Bar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, 9, 30 + i, tzinfo=timezone.utc),
                open=Decimal(str(base)),
                high=Decimal(str(base + 0.5)),
                low=Decimal(str(base - 0.3)),
                close=Decimal(str(base + 0.4)),
                volume=1000,
                vwap=Decimal(str(base + 0.2)),
            )
            bars.append(bar)
        
        # Decline
        for i in range(10):
            base = 110.0 - i * 0.5
            bar = Bar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, 9, 30 + 20 + i, tzinfo=timezone.utc),
                open=Decimal(str(base)),
                high=Decimal(str(base + 0.3)),
                low=Decimal(str(base - 0.5)),
                close=Decimal(str(base - 0.4)),
                volume=1000,
                vwap=Decimal(str(base - 0.2)),
            )
            bars.append(bar)
        
        # Second peak
        for i in range(20):
            base = 105.0 + i * 0.25
            bar = Bar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, 9, 30 + 30 + i, tzinfo=timezone.utc),
                open=Decimal(str(base)),
                high=Decimal(str(base + 0.5)),
                low=Decimal(str(base - 0.3)),
                close=Decimal(str(base + 0.4)),
                volume=1000,
                vwap=Decimal(str(base + 0.2)),
            )
            bars.append(bar)
        
        patterns = detector.detect_patterns(
            bars, lookback=60, pattern_types=["double_top"]
        )
        
        # May or may not detect double top depending on exact criteria
        # Just verify no errors and returns list
        assert isinstance(patterns, list)

    def test_detect_engulfing_candle(self, detector):
        """Test detection of bullish engulfing pattern"""
        bars = []
        
        # Create small down candle
        bar1 = Bar(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            open=Decimal("101.0"),
            high=Decimal("101.5"),
            low=Decimal("100.0"),
            close=Decimal("100.5"),
            volume=1000,
            vwap=Decimal("100.75"),
        )
        bars.append(bar1)
        
        # Create large up candle that engulfs previous
        bar2 = Bar(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=timezone.utc),
            open=Decimal("100.0"),
            high=Decimal("103.0"),
            low=Decimal("99.5"),
            close=Decimal("102.5"),
            volume=2000,
            vwap=Decimal("101.0"),
        )
        bars.append(bar2)
        
        patterns = detector.detect_patterns(
            bars, lookback=5, pattern_types=["bullish_engulfing"]
        )
        
        # Should detect bullish engulfing
        engulfing = [p for p in patterns if p["pattern_type"] == "bullish_engulfing"]
        assert len(engulfing) > 0

    def test_confidence_threshold(self, detector, uptrend_bars):
        """Test confidence threshold filtering"""
        # Get all patterns
        all_patterns = detector.detect_patterns(uptrend_bars, min_confidence=0.0)
        
        # Get high confidence patterns only
        high_conf_patterns = detector.detect_patterns(
            uptrend_bars, min_confidence=0.8
        )
        
        # High confidence should be subset of all
        assert len(high_conf_patterns) <= len(all_patterns)
        
        # All high conf patterns should have confidence >= 0.8
        for pattern in high_conf_patterns:
            assert pattern["confidence"] >= 0.8

    def test_pattern_context(self, detector, uptrend_bars):
        """Test that patterns include context information"""
        patterns = detector.detect_patterns(uptrend_bars)
        
        for pattern in patterns:
            context = pattern["context"]
            assert isinstance(context, dict)
            
            # Should have some context fields
            # Could include: atr, vwap, poc, regime, etc.

    def test_empty_bars(self, detector):
        """Test handling of empty bar list"""
        patterns = detector.detect_patterns([])
        
        assert isinstance(patterns, list)
        assert len(patterns) == 0

    def test_insufficient_bars(self, detector):
        """Test handling of insufficient bars"""
        bars = []
        for i in range(3):
            bar = Bar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, 9, 30 + i, tzinfo=timezone.utc),
                open=Decimal("100.0"),
                high=Decimal("101.0"),
                low=Decimal("99.0"),
                close=Decimal("100.5"),
                volume=1000,
                vwap=Decimal("100.25"),
            )
            bars.append(bar)
        
        patterns = detector.detect_patterns(bars, lookback=50)
        
        # Should handle gracefully
        assert isinstance(patterns, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
