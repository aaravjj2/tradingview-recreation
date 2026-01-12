"""
Data Manager Module for Options Supergraph Dashboard
Handles all Alpaca API interactions for stock and options data
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import numpy as np

from config import ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_ENDPOINT


class AlpacaDataManager:
    """Manages all data fetching from Alpaca API"""
    
    def __init__(self):
        self.api_key = ALPACA_API_KEY
        self.api_secret = ALPACA_API_SECRET
        self.base_url = ALPACA_ENDPOINT
        self.data_url = "https://data.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        }
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Fetch the current stock price for a given ticker
        
        Args:
            ticker: Stock symbol (e.g., 'SPY', 'NVDA')
            
        Returns:
            Current stock price or None if failed
        """
        try:
            url = f"{self.data_url}/v2/stocks/{ticker}/quotes/latest"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                # Use mid-price between bid and ask
                bid = data.get("quote", {}).get("bp", 0)
                ask = data.get("quote", {}).get("ap", 0)
                if bid and ask:
                    return (bid + ask) / 2
                # Fallback to last trade
                return self._get_last_trade(ticker)
            else:
                print(f"Error fetching quote: {response.status_code} - {response.text}")
                return self._get_last_trade(ticker)
        except Exception as e:
            print(f"Exception fetching price: {e}")
            return None
    
    def _get_last_trade(self, ticker: str) -> Optional[float]:
        """Fallback to get last trade price"""
        try:
            url = f"{self.data_url}/v2/stocks/{ticker}/trades/latest"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("trade", {}).get("p")
            return None
        except Exception:
            return None
    
    def get_options_chain(self, ticker: str, expiration_date: Optional[str] = None) -> Dict:
        """
        Fetch options chain for a ticker
        
        Args:
            ticker: Stock symbol
            expiration_date: Optional specific expiration (YYYY-MM-DD format)
            
        Returns:
            Dictionary with 'calls' and 'puts' lists
        """
        try:
            # Get available expirations first
            url = f"{self.data_url}/v1beta1/options/snapshots/{ticker}"
            params = {"feed": "indicative"}
            
            if expiration_date:
                params["expiration_date"] = expiration_date
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                calls = []
                puts = []
                
                snapshots = data.get("snapshots", {})
                for symbol, snapshot in snapshots.items():
                    option_data = self._parse_option_snapshot(symbol, snapshot)
                    if option_data:
                        if option_data["type"] == "call":
                            calls.append(option_data)
                        else:
                            puts.append(option_data)
                
                # Sort by strike price
                calls.sort(key=lambda x: x["strike"])
                puts.sort(key=lambda x: x["strike"])
                
                return {"calls": calls, "puts": puts}
            else:
                print(f"Error fetching options chain: {response.status_code}")
                return {"calls": [], "puts": []}
        except Exception as e:
            print(f"Exception fetching options chain: {e}")
            return {"calls": [], "puts": []}
    
    def _parse_option_snapshot(self, symbol: str, snapshot: Dict) -> Optional[Dict]:
        """Parse an option snapshot into a standardized format"""
        try:
            # Parse the OCC symbol format
            # Example: SPY240119C00500000 = SPY Jan 19 2024 $500 Call
            quote = snapshot.get("latestQuote", {})
            greeks = snapshot.get("greeks", {})
            
            # Extract strike and type from symbol
            # OCC format: SYMBOL + YYMMDD + C/P + Strike*1000 (8 digits)
            base_symbol = symbol[:6].rstrip('0123456789')  # Get underlying
            rest = symbol[len(base_symbol):]
            
            if len(rest) >= 15:
                date_part = rest[:6]  # YYMMDD
                option_type = "call" if rest[6] == "C" else "put"
                strike = int(rest[7:15]) / 1000  # Convert to actual price
                
                # Parse expiration date
                year = 2000 + int(date_part[:2])
                month = int(date_part[2:4])
                day = int(date_part[4:6])
                expiration = f"{year}-{month:02d}-{day:02d}"
                
                bid = quote.get("bp", 0) or 0
                ask = quote.get("ap", 0) or 0
                mid_price = (bid + ask) / 2 if bid and ask else 0
                
                return {
                    "symbol": symbol,
                    "underlying": base_symbol,
                    "strike": strike,
                    "type": option_type,
                    "expiration": expiration,
                    "bid": bid,
                    "ask": ask,
                    "mid": mid_price,
                    "iv": greeks.get("impliedVolatility", 0.30),
                    "delta": greeks.get("delta", 0),
                    "gamma": greeks.get("gamma", 0),
                    "theta": greeks.get("theta", 0),
                    "vega": greeks.get("vega", 0)
                }
            return None
        except Exception as e:
            print(f"Error parsing option: {e}")
            return None
    
    def get_available_expirations(self, ticker: str) -> List[str]:
        """Get list of available expiration dates for a ticker"""
        try:
            # Get next 4 weeks of Fridays as common expirations
            expirations = []
            today = datetime.now()
            
            # Find next Friday
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.hour >= 16:
                days_until_friday = 7
            
            next_friday = today + timedelta(days=days_until_friday)
            
            # Add next 8 weekly expirations
            for i in range(8):
                exp_date = next_friday + timedelta(weeks=i)
                expirations.append(exp_date.strftime("%Y-%m-%d"))
            
            return expirations
        except Exception as e:
            print(f"Error getting expirations: {e}")
            return []
    
    def get_implied_volatility(self, ticker: str, current_price: float) -> float:
        """
        Calculate average implied volatility from ATM options
        
        Args:
            ticker: Stock symbol
            current_price: Current stock price
            
        Returns:
            Average IV as decimal (e.g., 0.25 for 25%)
        """
        try:
            options = self.get_options_chain(ticker)
            
            # Find ATM options (closest to current price)
            all_options = options["calls"] + options["puts"]
            
            if not all_options:
                return 0.30  # Default 30% IV if no data
            
            # Sort by distance from current price
            atm_options = sorted(
                all_options,
                key=lambda x: abs(x["strike"] - current_price)
            )[:4]  # Get 4 closest options
            
            ivs = [opt["iv"] for opt in atm_options if opt["iv"] > 0]
            
            if ivs:
                return sum(ivs) / len(ivs)
            return 0.30
        except Exception as e:
            print(f"Error calculating IV: {e}")
            return 0.30
    
    def get_option_price(self, ticker: str, strike: float, expiration: str, 
                         option_type: str) -> Optional[float]:
        """
        Get the current price for a specific option contract
        
        Args:
            ticker: Underlying symbol
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            
        Returns:
            Mid-price of the option or None
        """
        try:
            options = self.get_options_chain(ticker, expiration)
            option_list = options["calls"] if option_type == "call" else options["puts"]
            
            # Find matching strike
            for opt in option_list:
                if abs(opt["strike"] - strike) < 0.01:
                    return opt["mid"]
            return None
        except Exception:
            return None


# Singleton instance
data_manager = AlpacaDataManager()


def get_current_price(ticker: str) -> Optional[float]:
    """Convenience function to get current stock price"""
    return data_manager.get_current_price(ticker)


def get_implied_volatility(ticker: str, current_price: float) -> float:
    """Convenience function to get implied volatility"""
    return data_manager.get_implied_volatility(ticker, current_price)


def get_options_chain(ticker: str, expiration: Optional[str] = None) -> Dict:
    """Convenience function to get options chain"""
    return data_manager.get_options_chain(ticker, expiration)


def get_available_expirations(ticker: str) -> List[str]:
    """Convenience function to get available expirations"""
    return data_manager.get_available_expirations(ticker)
