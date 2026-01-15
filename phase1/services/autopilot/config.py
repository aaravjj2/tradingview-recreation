"""
Autopilot Configuration

Manages all settings for the paper-only AI options autopilot including:
- Budget and risk limits
- Universe and strategy whitelists
- Forecast influence settings
- LLM enablement
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from functools import lru_cache
import json
import os
import logging

logger = logging.getLogger(__name__)


class AutopilotMode(str, Enum):
    """Autopilot operating mode."""
    PAUSED = "paused"
    PAPER = "paper"  # Only paper mode supported


class StrategyTemplate(str, Enum):
    """Available strategy templates."""
    PUT_CREDIT_SPREAD = "put_credit_spread"
    CALL_CREDIT_SPREAD = "call_credit_spread"
    IRON_CONDOR = "iron_condor"
    CALL_DEBIT_SPREAD = "call_debit_spread"
    PUT_DEBIT_SPREAD = "put_debit_spread"


# Default liquid universe
DEFAULT_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD",
    # Core ETFs
    "SPY", "QQQ", "IWM", "DIA",
    # Sector ETFs
    "XLK", "SMH", "XLF", "XLE",
    # Optional hedges
    "TLT", "GLD",
]

# Universe clusters for concentration limits
UNIVERSE_CLUSTERS = {
    "mega_tech": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"],
    "broad_etfs": ["SPY", "QQQ", "IWM", "DIA"],
    "sector_tech": ["XLK", "SMH"],
    "sector_fin": ["XLF"],
    "sector_energy": ["XLE"],
    "hedges": ["TLT", "GLD"],
}


@dataclass
class RiskLimits:
    """Risk management limits for paper trading."""
    max_risk_per_trade: float = 50.0  # 5% of $1000
    max_total_risk: float = 400.0  # 40% of equity
    max_daily_loss: float = 30.0  # 3% of equity
    max_open_positions: int = 10
    max_positions_per_underlying: int = 2
    max_positions_per_cluster: int = 2
    max_cluster_risk_pct: float = 0.6  # 60% max in any cluster


@dataclass
class StrategyConstraints:
    """Constraints for strategy templates."""
    min_dte: int = 1
    max_dte: int = 60
    min_short_delta: float = 0.15
    max_short_delta: float = 0.35
    min_spread_width: float = 1.0
    max_spread_width: float = 10.0
    max_slippage_pct: float = 0.05
    # Exit rules
    take_profit_pct: float = 0.50  # 50% of max profit
    time_stop_dte: int = 1  # Close when DTE <= 1
    loss_stop_multiplier: float = 2.0  # 2x credit received


@dataclass
class EarningsPolicy:
    """Earnings event handling policy."""
    blackout_days_before: int = 7  # No new short premium 7 days before
    auto_close_before_earnings: bool = True  # Close short premium before event
    close_days_before: int = 1  # Days before earnings to close


@dataclass
class ForecastSettings:
    """Settings for forecast influence on decisions."""
    enabled: bool = True
    influence_weight: float = 0.3  # 0-1, how much forecast affects scoring
    min_confidence: float = 0.4  # Minimum confidence to use forecast
    auto_downweight_on_miscalibration: bool = True


class LLMMode(str, Enum):
    """LLM selection mode."""
    OFF = "off"
    GROQ = "groq"
    GEMINI = "gemini"
    HYBRID = "hybrid"  # Groq for ranking, Gemini for validation
    DETERMINISTIC = "deterministic"  # Fallback only


@dataclass
class LLMSettings:
    """Settings for optional LLM ranking."""
    enabled: bool = False
    mode: LLMMode = LLMMode.DETERMINISTIC
    groq_model: Optional[str] = None  # Defaults to groq/compound
    gemini_model: Optional[str] = None  # Defaults to gemini-1.5-flash
    endpoint_url: Optional[str] = None  # For custom HTTP endpoints
    timeout_seconds: float = 30.0
    fallback_to_deterministic: bool = True


@dataclass
class AutopilotConfig:
    """Complete autopilot configuration."""
    # Mode
    mode: AutopilotMode = AutopilotMode.PAPER
    auto_execute: bool = True  # Auto-execute paper trades
    enable_alpaca: bool = True  # Enable mirroring trades to Alpaca
    
    # Budget (paper equity)
    paper_equity: float = 1000.0
    
    # Risk limits
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    
    # Universe
    universe: List[str] = field(default_factory=lambda: DEFAULT_UNIVERSE.copy())
    
    # Strategy whitelist
    allowed_strategies: List[StrategyTemplate] = field(
        default_factory=lambda: list(StrategyTemplate)
    )
    
    # Strategy constraints
    strategy_constraints: StrategyConstraints = field(
        default_factory=StrategyConstraints
    )
    
    # Earnings policy
    earnings_policy: EarningsPolicy = field(default_factory=EarningsPolicy)
    
    # Forecast settings
    forecast_settings: ForecastSettings = field(default_factory=ForecastSettings)
    
    # LLM settings
    llm_settings: LLMSettings = field(default_factory=LLMSettings)
    
    # Schedule (times in HH:MM format, America/New_York)
    scan_times: List[str] = field(default_factory=lambda: ["09:35", "12:00", "15:30"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for API/storage."""
        return {
            "mode": self.mode.value,
            "auto_execute": self.auto_execute,
            "paper_equity": self.paper_equity,
            "risk_limits": {
                "max_risk_per_trade": self.risk_limits.max_risk_per_trade,
                "max_total_risk": self.risk_limits.max_total_risk,
                "max_daily_loss": self.risk_limits.max_daily_loss,
                "max_open_positions": self.risk_limits.max_open_positions,
                "max_positions_per_underlying": self.risk_limits.max_positions_per_underlying,
                "max_positions_per_cluster": self.risk_limits.max_positions_per_cluster,
                "max_cluster_risk_pct": self.risk_limits.max_cluster_risk_pct,
            },
            "universe": self.universe,
            "allowed_strategies": [s.value for s in self.allowed_strategies],
            "strategy_constraints": {
                "min_dte": self.strategy_constraints.min_dte,
                "max_dte": self.strategy_constraints.max_dte,
                "min_short_delta": self.strategy_constraints.min_short_delta,
                "max_short_delta": self.strategy_constraints.max_short_delta,
                "min_spread_width": self.strategy_constraints.min_spread_width,
                "max_spread_width": self.strategy_constraints.max_spread_width,
                "take_profit_pct": self.strategy_constraints.take_profit_pct,
                "time_stop_dte": self.strategy_constraints.time_stop_dte,
                "loss_stop_multiplier": self.strategy_constraints.loss_stop_multiplier,
            },
            "earnings_policy": {
                "blackout_days_before": self.earnings_policy.blackout_days_before,
                "auto_close_before_earnings": self.earnings_policy.auto_close_before_earnings,
                "close_days_before": self.earnings_policy.close_days_before,
            },
            "forecast_settings": {
                "enabled": self.forecast_settings.enabled,
                "influence_weight": self.forecast_settings.influence_weight,
                "min_confidence": self.forecast_settings.min_confidence,
            },
            "llm_settings": {
                "enabled": self.llm_settings.enabled,
                "endpoint_url": self.llm_settings.endpoint_url,
                "fallback_to_deterministic": self.llm_settings.fallback_to_deterministic,
            },
            "scan_times": self.scan_times,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutopilotConfig':
        """Create config from dictionary."""
        config = cls()
        
        if "mode" in data:
            config.mode = AutopilotMode(data["mode"])
        if "auto_execute" in data:
            config.auto_execute = data["auto_execute"]
        if "paper_equity" in data:
            config.paper_equity = float(data["paper_equity"])
        
        if "risk_limits" in data:
            rl = data["risk_limits"]
            config.risk_limits = RiskLimits(
                max_risk_per_trade=rl.get("max_risk_per_trade", 50.0),
                max_total_risk=rl.get("max_total_risk", 400.0),
                max_daily_loss=rl.get("max_daily_loss", 30.0),
                max_open_positions=rl.get("max_open_positions", 10),
                max_positions_per_underlying=rl.get("max_positions_per_underlying", 2),
                max_positions_per_cluster=rl.get("max_positions_per_cluster", 2),
                max_cluster_risk_pct=rl.get("max_cluster_risk_pct", 0.6),
            )
        
        if "universe" in data:
            config.universe = data["universe"]
        
        if "allowed_strategies" in data:
            config.allowed_strategies = [
                StrategyTemplate(s) for s in data["allowed_strategies"]
            ]
        
        if "strategy_constraints" in data:
            sc = data["strategy_constraints"]
            config.strategy_constraints = StrategyConstraints(
                min_dte=sc.get("min_dte", 14),
                max_dte=sc.get("max_dte", 45),
                min_short_delta=sc.get("min_short_delta", 0.15),
                max_short_delta=sc.get("max_short_delta", 0.35),
                min_spread_width=sc.get("min_spread_width", 1.0),
                max_spread_width=sc.get("max_spread_width", 10.0),
                take_profit_pct=sc.get("take_profit_pct", 0.50),
                time_stop_dte=sc.get("time_stop_dte", 7),
                loss_stop_multiplier=sc.get("loss_stop_multiplier", 2.0),
            )
        
        if "earnings_policy" in data:
            ep = data["earnings_policy"]
            config.earnings_policy = EarningsPolicy(
                blackout_days_before=ep.get("blackout_days_before", 7),
                auto_close_before_earnings=ep.get("auto_close_before_earnings", True),
                close_days_before=ep.get("close_days_before", 1),
            )
        
        if "forecast_settings" in data:
            fs = data["forecast_settings"]
            config.forecast_settings = ForecastSettings(
                enabled=fs.get("enabled", True),
                influence_weight=fs.get("influence_weight", 0.3),
                min_confidence=fs.get("min_confidence", 0.4),
            )
        
        if "llm_settings" in data:
            ls = data["llm_settings"]
            config.llm_settings = LLMSettings(
                enabled=ls.get("enabled", False),
                endpoint_url=ls.get("endpoint_url"),
                fallback_to_deterministic=ls.get("fallback_to_deterministic", True),
            )
        
        if "scan_times" in data:
            config.scan_times = data["scan_times"]
        
        return config
    
    def get_cluster_for_symbol(self, symbol: str) -> Optional[str]:
        """Get the cluster name for a symbol."""
        for cluster_name, symbols in UNIVERSE_CLUSTERS.items():
            if symbol in symbols:
                return cluster_name
        return None


# Config storage path
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "autopilot_config.json"
)

_cached_config: Optional[AutopilotConfig] = None


def get_autopilot_config() -> AutopilotConfig:
    """Get the current autopilot configuration."""
    global _cached_config
    
    if _cached_config is not None:
        return _cached_config
    
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r") as f:
                data = json.load(f)
            _cached_config = AutopilotConfig.from_dict(data)
        except Exception:
            _cached_config = AutopilotConfig()
    else:
        _cached_config = AutopilotConfig()
    
    return _cached_config


def save_autopilot_config(config: AutopilotConfig) -> None:
    """Save autopilot configuration."""
    global _cached_config
    
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
    
    _cached_config = config


def reset_config_cache() -> None:
    """Reset the config cache (for testing)."""
    global _cached_config
    _cached_config = None


def load_llm_config_from_env() -> LLMSettings:
    """
    Load LLM configuration from environment variables.
    
    Environment variables:
    - LLM_MODE: off|groq|gemini|hybrid|deterministic (default: deterministic)
    - GROQ_MODEL: Model name for Groq (default: groq/compound)
    - GEMINI_MODEL: Model name for Gemini (default: gemini-1.5-flash)
    - GROQ_API_KEY: API key for Groq
    - GEMINI_API_KEY: API key for Gemini
    """
    mode_str = os.environ.get("LLM_MODE", "deterministic").lower()
    
    # Map string to enum
    mode_map = {
        "off": LLMMode.OFF,
        "groq": LLMMode.GROQ,
        "gemini": LLMMode.GEMINI,
        "hybrid": LLMMode.HYBRID,
        "deterministic": LLMMode.DETERMINISTIC,
    }
    mode = mode_map.get(mode_str, LLMMode.DETERMINISTIC)
    
    # Check if keys are present
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    # Auto-downgrade if keys missing
    if mode == LLMMode.GROQ and not groq_key:
        mode = LLMMode.DETERMINISTIC
        logger.warning("GROQ mode selected but GROQ_API_KEY not set, falling back to DETERMINISTIC")
    elif mode == LLMMode.GEMINI and not gemini_key:
        mode = LLMMode.DETERMINISTIC
        logger.warning("GEMINI mode selected but GEMINI_API_KEY not set, falling back to DETERMINISTIC")
    elif mode == LLMMode.HYBRID and (not groq_key or not gemini_key):
        if groq_key and not gemini_key:
            mode = LLMMode.GROQ
            logger.warning("HYBRID mode selected but GEMINI_API_KEY not set, using GROQ only")
        elif gemini_key and not groq_key:
            mode = LLMMode.GEMINI
            logger.warning("HYBRID mode selected but GROQ_API_KEY not set, using GEMINI only")
        else:
            mode = LLMMode.DETERMINISTIC
            logger.warning("HYBRID mode selected but no API keys set, falling back to DETERMINISTIC")
    
    enabled = mode != LLMMode.OFF and mode != LLMMode.DETERMINISTIC
    
    return LLMSettings(
        enabled=enabled,
        mode=mode,
        groq_model=os.environ.get("GROQ_MODEL"),
        gemini_model=os.environ.get("GEMINI_MODEL"),
        timeout_seconds=float(os.environ.get("LLM_TIMEOUT", "30")),
        fallback_to_deterministic=True,
    )
