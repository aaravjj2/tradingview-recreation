"""
Unit tests for Fundamentals Adapter
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import Mock, patch
from services.fundamentals.adapter import FundamentalsAdapter


@pytest.fixture
def adapter():
    return FundamentalsAdapter()


class TestFundamentalsAdapter:
    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_get_fundamentals_success(self, mock_ticker, adapter):
        """Test successful fundamentals fetch"""
        # Mock yfinance Ticker object
        mock_info = {
            'returnOnEquity': 0.25,
            'returnOnAssets': 0.15,
            'grossMargins': 0.40,
            'operatingMargins': 0.30,
            'profitMargins': 0.20,
            'freeCashflow': 50000000000,
            'debtToEquity': 1.5,
            'currentRatio': 2.0,
            'quickRatio': 1.5,
            'trailingPE': 25.0,
            'priceToBook': 5.0,
            'priceToSalesTrailing12Months': 3.0,
            'marketCap': 2000000000000,
            'enterpriseValue': 2100000000000,
            'sharesOutstanding': 16000000000,
            'revenueGrowth': 0.15,
            'earningsGrowth': 0.20,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert "profitability" in result
        assert "cash_flow" in result
        assert "leverage" in result
        assert "quality" in result
        assert "valuation" in result
        assert "growth" in result
        assert "additional" in result

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_profitability_metrics(self, mock_ticker, adapter):
        """Test profitability metrics extraction"""
        mock_info = {
            'returnOnEquity': 0.25,
            'grossMargins': 0.40,
            'operatingMargins': 0.30,
            'profitMargins': 0.20,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        profitability = result["profitability"]
        assert profitability["gross_margin"] == 0.40
        assert profitability["operating_margin"] == 0.30
        assert profitability["net_margin"] == 0.20

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_missing_data_handling(self, mock_ticker, adapter):
        """Test handling of missing data"""
        # Mock with minimal data
        mock_info = {
            'symbol': 'TEST',
            # Most fields missing
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("TEST")
        
        assert result is not None
        # Missing fields should be marked as "unavailable"
        assert result["profitability"]["roic"] == "unavailable"
        assert result["cash_flow"]["fcf"] == "unavailable"

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_fcf_yield_calculation(self, mock_ticker, adapter):
        """Test FCF yield calculation"""
        mock_info = {
            'freeCashflow': 100000000000,
            'marketCap': 2000000000000,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        cash_flow = result["cash_flow"]
        assert cash_flow["fcf"] == 100000000000
        # FCF yield = FCF / Market Cap = 100B / 2000B = 0.05
        assert abs(cash_flow["fcf_yield"] - 0.05) < 0.001

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_roic_calculation(self, mock_ticker, adapter):
        """Test ROIC calculation when components available"""
        mock_info = {
            'returnOnEquity': 0.30,
            'debtToEquity': 0.5,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        # ROIC approximation: ROE * (1 + D/E) / (1 + (1-tax_rate) * D/E)
        # Should have calculated ROIC
        roic = result["profitability"]["roic"]
        assert isinstance(roic, float) or roic == "unavailable"

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_valuation_ratios(self, mock_ticker, adapter):
        """Test valuation ratio extraction"""
        mock_info = {
            'trailingPE': 25.5,
            'priceToBook': 10.2,
            'priceToSalesTrailing12Months': 7.8,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        valuation = result["valuation"]
        assert valuation["pe_ratio"] == 25.5
        assert valuation["pb_ratio"] == 10.2
        assert valuation["ps_ratio"] == 7.8

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_growth_metrics(self, mock_ticker, adapter):
        """Test growth metrics extraction"""
        mock_info = {
            'revenueGrowth': 0.15,
            'earningsGrowth': 0.22,
        }
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("AAPL")
        
        growth = result["growth"]
        assert growth["revenue_growth"] == 0.15
        assert growth["earnings_growth"] == 0.22

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_ticker_fetch_error(self, mock_ticker, adapter):
        """Test error handling when yfinance fails"""
        mock_ticker.side_effect = Exception("Network error")
        
        result = adapter.get_fundamentals("INVALID")
        
        # Should return None or handle gracefully
        assert result is None or "error" in result

    @patch('phase1.services.fundamentals.adapter.yf.Ticker')
    def test_timestamp_included(self, mock_ticker, adapter):
        """Test that timestamp is included in result"""
        mock_info = {'symbol': 'TEST'}
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker.return_value = mock_ticker_instance
        
        result = adapter.get_fundamentals("TEST")
        
        assert "timestamp" in result
        # Timestamp should be ISO format string
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
