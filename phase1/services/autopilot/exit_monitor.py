"""
Exit Monitoring Engine - V1 SINGLE EXIT AUTHORITY

V1 COMPLIANCE: This is the ONE and ONLY exit authority.
All exit decisions flow through this module.

Exit Rules (V1 Long Premium):
1. Hard stop at -20% (premium lost 20% of entry value) - IMMEDIATE
2. Profit target at +50% (premium gained 50%)
3. Time stop at DTE <= 1
4. Regime change: CHAOS → close ALL positions - IMMEDIATE
5. EOD flatten for 0DTE positions - IMMEDIATE

NO OTHER MODULE should have independent exit logic.
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import deque

logger = logging.getLogger(__name__)


# ============================================================================
# V1 EXIT CONSTANTS (from V1 contract)
# ============================================================================
from .config import V1_PER_POSITION_STOP_PCT

V1_HARD_STOP_PCT = V1_PER_POSITION_STOP_PCT  # 10% hard stop (V1 contract)
V1_PROFIT_TARGET_PCT = 0.50  # +50% take profit
V1_TIME_STOP_DTE = 1         # Close at DTE <= 1


class ExitTrigger(str, Enum):
    """Exit trigger types."""
    HARD_STOP = "hard_stop"          # V1: -10% immediate
    PROFIT_TARGET = "profit_target"  # +50%
    TIME_STOP = "time_stop"          # DTE <= 1
    EOD_FLATTEN = "eod_flatten"      # End of day 0DTE
    REGIME_CHANGE = "regime_change"  # CHAOS regime
    DAILY_LOSS_CAP = "daily_loss_cap"
    NEWS_SHOCK = "news_shock"
    MANUAL = "manual"

@dataclass
class ExitSignal:
    """Exit signal with details."""
    trigger: ExitTrigger
    triggered: bool
    current_value: float
    threshold: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger.value,
            "triggered": self.triggered,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }

@dataclass
class PositionMonitor:
    """Monitor state for a single position."""
    position_id: str
    entry_price: float
    entry_time: datetime
    is_debit: bool  # True for V1 long premium
    # V1 CONTRACT: -10% hard stop, +50% profit target
    hard_stop_pct: float = V1_HARD_STOP_PCT   # -10% (V1 contract)
    profit_target_pct: float = V1_PROFIT_TARGET_PCT  # +50%
    time_stop_dte: int = V1_TIME_STOP_DTE     # DTE <= 1
    
    # Tracking
    samples: List[Dict[str, Any]] = field(default_factory=list)
    min_price_seen: float = float('inf')
    max_price_seen: float = 0.0
    dte: Optional[int] = None  # Days to expiration
    
    def record_sample(self, current_price: float, timestamp: datetime, dte: Optional[int] = None) -> List[ExitSignal]:
        """
        Record a price sample and evaluate all exit triggers.
        
        V1 CONTRACT: Simplified exit logic for long premium positions.
        
        Returns list of triggered signals.
        """
        self.samples.append({
            "timestamp": timestamp.isoformat(),
            "price": current_price,
        })
        
        if dte is not None:
            self.dte = dte
        
        self.min_price_seen = min(self.min_price_seen, current_price)
        self.max_price_seen = max(self.max_price_seen, current_price)
        
        signals = []
        
        # V1: Long premium positions - loss = price decline from entry
        # (We bought the option, it's now worth less)
        pnl_pct = (current_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        
        # 1. HARD STOP (-20%) - IMMEDIATE (V1 mandate)
        if pnl_pct <= -self.hard_stop_pct:
            logger.warning(f"🛑 V1 HARD STOP: {self.position_id} at {pnl_pct*100:.1f}% loss")
            signals.append(ExitSignal(
                trigger=ExitTrigger.HARD_STOP,
                triggered=True,
                current_value=pnl_pct,
                threshold=-self.hard_stop_pct,
                timestamp=timestamp,
                details={"immediate": True, "v1_mandate": True}
            ))
            return signals  # Hard stop trumps everything
        
        # 2. PROFIT TARGET (+50%)
        if pnl_pct >= self.profit_target_pct:
            logger.info(f"🎯 V1 PROFIT TARGET: {self.position_id} at {pnl_pct*100:.1f}% gain")
            signals.append(ExitSignal(
                trigger=ExitTrigger.PROFIT_TARGET,
                triggered=True,
                current_value=pnl_pct,
                threshold=self.profit_target_pct,
                timestamp=timestamp,
            ))
        
        # 3. TIME STOP (DTE <= 1)
        if self.dte is not None and self.dte <= self.time_stop_dte:
            logger.info(f"⏰ V1 TIME STOP: {self.position_id} at DTE={self.dte}")
            signals.append(ExitSignal(
                trigger=ExitTrigger.TIME_STOP,
                triggered=True,
                current_value=self.dte,
                threshold=self.time_stop_dte,
                timestamp=timestamp,
                details={"dte": self.dte}
            ))
        
        return signals

class ExitMonitor:
    """
    V1 SINGLE EXIT AUTHORITY
    
    Monitors all positions for exit conditions.
    This is the ONLY class that should evaluate exits.
    """
    
    def __init__(
        self,
        eod_exit_minutes: float = 30.0,  # Exit 30 min before close for 0DTE
        daily_loss_cap: float = 500.0,   # Stop trading after this loss
    ):
        self.eod_exit_minutes = eod_exit_minutes
        self.daily_loss_cap = daily_loss_cap
        self._positions: Dict[str, PositionMonitor] = {}
        self._daily_pnl: float = 0.0
        self._current_regime: str = "normal"
        logger.info("V1 ExitMonitor initialized (Single Exit Authority)")
    
    def set_regime(self, regime: str):
        """Set current market regime. CHAOS = force close all."""
        old_regime = self._current_regime
        self._current_regime = regime.lower()
        if old_regime != self._current_regime:
            logger.warning(f"Regime changed: {old_regime} → {self._current_regime}")
    
    def register_position(
        self,
        position_id: str,
        entry_price: float,
        entry_time: datetime,
        dte: Optional[int] = None,
    ) -> PositionMonitor:
        """
        Register a new position for monitoring.
        
        V1 COMPLIANCE: All positions use V1 exit rules (long premium).
        """
        monitor = PositionMonitor(
            position_id=position_id,
            entry_price=entry_price,
            entry_time=entry_time,
            is_debit=True,  # V1: Long premium only
            hard_stop_pct=V1_HARD_STOP_PCT,
            profit_target_pct=V1_PROFIT_TARGET_PCT,
            time_stop_dte=V1_TIME_STOP_DTE,
            dte=dte,
        )
        
        self._positions[position_id] = monitor
        logger.info(f"V1 ExitMonitor: Registered {position_id} (entry=${entry_price:.2f}, DTE={dte})")
        return monitor
    
    def check_position(
        self,
        position_id: str,
        current_price: float,
        market_close_time: Optional[datetime] = None,
        dte: Optional[int] = None,
    ) -> List[ExitSignal]:
        """
        Check a position for exit conditions.
        
        V1 SINGLE AUTHORITY: All exit decisions go through here.
        
        Returns list of triggered exit signals.
        """
        if position_id not in self._positions:
            logger.warning(f"Position {position_id} not registered for monitoring")
            return []
        
        monitor = self._positions[position_id]
        now = datetime.now(timezone.utc)
        
        signals = monitor.record_sample(current_price, now, dte=dte)
        
        # Check CHAOS regime → immediate exit
        if self._current_regime == "chaos":
            logger.warning(f"⚠️ CHAOS REGIME: Force closing {position_id}")
            signals.append(ExitSignal(
                trigger=ExitTrigger.REGIME_CHANGE,
                triggered=True,
                current_value=0,
                threshold=0,
                timestamp=now,
                details={"regime": "chaos", "immediate": True}
            ))
        
        # Check EOD flatten for 0DTE
        if market_close_time and monitor.dte is not None and monitor.dte == 0:
            minutes_to_close = (market_close_time - now).total_seconds() / 60
            if minutes_to_close <= self.eod_exit_minutes:
                logger.info(f"🌅 EOD FLATTEN: {position_id} (0DTE, {minutes_to_close:.0f}m to close)")
                signals.append(ExitSignal(
                    trigger=ExitTrigger.EOD_FLATTEN,
                    triggered=True,
                    current_value=minutes_to_close,
                    threshold=self.eod_exit_minutes,
                    timestamp=now,
                    details={"dte": 0, "minutes_to_close": minutes_to_close}
                ))
        
        # Check daily loss cap
        if self._daily_pnl <= -self.daily_loss_cap:
            signals.append(ExitSignal(
                trigger=ExitTrigger.DAILY_LOSS_CAP,
                triggered=True,
                current_value=self._daily_pnl,
                threshold=-self.daily_loss_cap,
                timestamp=now,
            ))
        
        return signals
    
    def check_all_positions(
        self,
        price_updates: Dict[str, float],
        market_close_time: Optional[datetime] = None,
    ) -> Dict[str, List[ExitSignal]]:
        """
        Check all registered positions for exit conditions.
        
        Args:
            price_updates: Dict mapping position_id to current_price
            market_close_time: When market closes (for EOD logic)
            
        Returns:
            Dict mapping position_id to list of exit signals
        """
        all_signals = {}
        
        for pos_id, monitor in self._positions.items():
            if pos_id in price_updates:
                signals = self.check_position(
                    pos_id,
                    price_updates[pos_id],
                    market_close_time=market_close_time,
                )
                if signals:
                    all_signals[pos_id] = signals
        
        return all_signals
    
    def on_position_closed(self, position_id: str, realized_pnl: float):
        """Record position close and update daily PnL."""
        if position_id in self._positions:
            del self._positions[position_id]
        self._daily_pnl += realized_pnl
        logger.info(f"Position {position_id} closed. PnL: ${realized_pnl:.2f}. Daily: ${self._daily_pnl:.2f}")
    
    def reset_daily(self):
        """Reset for new trading day."""
        self._daily_pnl = 0.0
        logger.info("V1 ExitMonitor: Daily reset complete")


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_exit_monitor: Optional[ExitMonitor] = None


def get_exit_monitor() -> ExitMonitor:
    """Get singleton ExitMonitor instance (V1 Single Authority)."""
    global _exit_monitor
    if _exit_monitor is None:
        _exit_monitor = ExitMonitor()
    return _exit_monitor


def reset_exit_monitor():
    """Reset singleton (for testing)."""
    global _exit_monitor
    _exit_monitor = None
