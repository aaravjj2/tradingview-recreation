"""
Phase 1: Deterministic Data & Bar Engine
Core configuration and settings management.
"""

import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./phase1.db",
        description="Database connection URL"
    )
    
    # API Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=7500)
    
    # Finnhub
    finnhub_api_key: Optional[str] = Field(default=None)
    finnhub2_api_key: Optional[str] = Field(default=None)
    
    # Alpaca
    apca_api_key_id: Optional[str] = Field(default=None, validation_alias="ALPACA3_KEY") 
    apca_api_secret_key: Optional[str] = Field(default=None, validation_alias="ALPACA3_SECRET")
    apca_endpoint: str = Field(default="https://paper-api.alpaca.markets", validation_alias="ALPACA3_ENDPOINT")
    
    # Tiingo (for yfinance fallback)
    tiingo_api_key: Optional[str] = Field(default=None)
    
    # Ingestion
    ingestion_mode: Literal["mock", "live"] = Field(default="live")
    ingestion_symbols: str = Field(default="AAPL,MSFT")
    
    # Bar Engine
    bar_cache_size: int = Field(default=10000, description="LRU cache size for recent bars")
    supported_timeframes: str = Field(default="1m,5m,15m,1h,1d")
    
    # Session Calendar
    enable_extended_hours: bool = Field(default=False)
    default_timezone: str = Field(default="America/New_York")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(default="json")
    debug_mode: bool = Field(default=False)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def timeframes_list(self) -> list[str]:
        """Parse supported timeframes into list."""
        return [tf.strip() for tf in self.supported_timeframes.split(",")]
    
    @property
    def symbols_list(self) -> list[str]:
        """Parse ingestion symbols into list."""
        return [s.strip() for s in self.ingestion_symbols.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Try to load from keys.env in parent directory
    # Try to load from keys.env in parent directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    potential_paths = [
        os.path.join(current_dir, "..", "keys.env"),        # phase1/keys.env
        os.path.join(current_dir, "..", "..", "keys.env"),  # root/keys.env
        os.path.join(current_dir, "keys.env"),              # services/keys.env
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            from dotenv import load_dotenv
            print(f"Loading keys from: {path}")
            load_dotenv(path)
            break
    
    return Settings()


# Timeframe definitions in milliseconds
TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}

# Timeframe hierarchy for aggregation
TIMEFRAME_HIERARCHY = ["1m", "5m", "15m", "1h", "1d"]


def timeframe_to_ms(timeframe: str) -> int:
    """Convert timeframe string to milliseconds."""
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_MS[timeframe]
