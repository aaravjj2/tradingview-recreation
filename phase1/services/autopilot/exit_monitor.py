"""
Exit Monitoring Engine (Milestone 1)

Implements the two-layer exit policy:
1. Hard rules (always enforce): catastrophic stop, time stop, EOD, daily loss cap
2. Soft rules: stop smoothing with 2-of-3 sample confirmation

Stop smoothing per spec:
- Soft stop (-20% premium) triggers only if breached in 2 of last 3 samples
- Hard stop (-40% premium) triggers immediately
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import deque

logger = logging.getLogger(__name__)

class ExitTrigger(str, Enum):
    """Exit trigger types."""
    SOFT_STOP = "soft_stop"          # -20% with smoothing
    HARD_STOP = "hard_stop"          # -40% immediate
    PROFIT_TARGET = "profit_target"  # +25% to +50%
    TIME_STOP = "time_stop"          # No movement in N min
    EOD_FLATTEN = "eod_flatten"      # End of day
    DAILY_LOSS_CAP = "daily_loss_cap"
    REGIME_FLIP = "regime_flip"
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

class StopSmoother:
    """
    Implements 2-of-3 sample smoothing for soft stops.
    
    A stop is only confirmed if breached in 2 of the last 3 monitoring samples.
    This prevents noise-triggered exits on 0DTE.
    """
    
    def __init__(self, window_size: int = 3, required_breaches: int = 2):
        self.window_size = window_size
        self.required_breaches = required_breaches
        self._breach_history: deque = deque(maxlen=window_size)
    
    def record_sample(self, breached: bool) -> bool:
        """
        Record a sample and return whether stop is confirmed.
        
        Args:
            breached: Whether the stop threshold was breached this sample
            
        Returns:
            True if stop is confirmed (2-of-3 breaches)
        """
        self._breach_history.append(breached)
        
        if len(self._breach_history) < self.window_size:
            return False  # Not enough samples yet
        
        breach_count = sum(1 for b in self._breach_history if b)
        return breach_count >= self.required_breaches
    
    def reset(self):
        """Reset history for new position."""
        self._breach_history.clear()

@dataclass
class PositionMonitor:
    """Monitor state for a single position."""
    position_id: str
    entry_price: float
    entry_time: datetime
    is_debit: bool  # True for debit spreads, False for credit
    soft_stop_pct: float = 0.20   # -20%
    hard_stop_pct: float = 0.40   # -40%
    profit_target_pct: float = 0.30  # +30%
    time_stop_minutes: float = 45.0
    
    # Smoothing
    stop_smoother: StopSmoother = field(default_factory=StopSmoother)
    
    # Tracking
    samples: List[Dict[str, Any]] = field(default_factory=list)
    min_price_seen: float = float('inf')
    max_price_seen: float = 0.0
    
    def record_sample(self, current_price: float, timestamp: datetime) -> List[ExitSignal]:
        """
        Record a price sample and evaluate all exit triggers.
        
        Returns list of triggered signals.
        """
        self.samples.append({
            "timestamp": timestamp.isoformat(),
            "price": current_price,
        })
        
        self.min_price_seen = min(self.min_price_seen, current_price)
        self.max_price_seen = max(self.max_price_seen, current_price)
        
        signals = []
        
        if self.is_debit:
            # For debit: we paid premium, loss = price decline
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            # For credit: we received premium, loss = price increase
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # 1. Hard Stop (-40%) - Immediate
        if pnl_pct <= -self.hard_stop_pct:
            signals.append(ExitSignal(
                trigger=ExitTrigger.HARD_STOP,
                triggered=True,
                current_value=pnl_pct,
                threshold=-self.hard_stop_pct,
                timestamp=timestamp,
                details={"immediate": True}
            ))
            return signals  # Hard stop trumps everything
        
        # 2. Soft Stop (-20%) - With smoothing
        soft_breached = pnl_pct <= -self.soft_stop_pct
        soft_confirmed = self.stop_smoother.record_sample(soft_breached)
        
        if soft_confirmed:
            signals.append(ExitSignal(
                trigger=ExitTrigger.SOFT_STOP,
                triggered=True,
                current_value=pnl_pct,
                threshold=-self.soft_stop_pct,
                timestamp=timestamp,
                details={"smoothed": True, "sample_count": len(self.samples)}
            ))
        
        # 3. Profit Target
        if pnl_pct >= self.profit_target_pct:
            signals.append(ExitSignal(
                trigger=ExitTrigger.PROFIT_TARGET,
                triggered=True,
                current_value=pnl_pct,
                threshold=self.profit_target_pct,
                timestamp=timestamp,
            ))
        
        # 4. Time Stop
        elapsed = (timestamp - self.entry_time).total_seconds() / 60
        if elapsed >= self.time_stop_minutes:
            # Check if we've at least broken even or close
            if pnl_pct < 0.05:  # Less than 5% profit after time
                signals.append(ExitSignal(
                    trigger=ExitTrigger.TIME_STOP,
                    triggered=True,
                    current_value=elapsed,
                    threshold=self.time_stop_minutes,
                    timestamp=timestamp,
                    details={"pnl_pct": pnl_pct}
                ))
        
        return signals

class ExitMonitor:
    """
    Monitors all positions for exit conditions.
    """
    
    def __init__(
        self,
        eod_exit_minutes: float = 10.0,  # Exit N min before close
        daily_loss_cap: float = 500.0,   # Stop trading after this loss
    ):
        self.eod_exit_minutes = eod_exit_minutes
        self.daily_loss_cap = daily_loss_cap
        self._positions: Dict[str, PositionMonitor] = {}
        self._daily_pnl: float = 0.0
    
    def register_position(
        self,
        position_id: str,
        entry_price: float,
        entry_time: datetime,
        is_debit: bool,
        template_type: str = "debit",
    ) -> PositionMonitor:
        """Register a new position for monitoring."""
        # Set thresholds based on template
        if template_type == "credit":
            monitor = PositionMonitor(
                position_id=position_id,
                entry_price=entry_price,
                entry_time=entry_time,
                is_debit=False,
                soft_stop_pct=0.60,  # 60% of max loss for credit
                hard_stop_pct=0.70,  # 70% of max loss
                profit_target_pct=0.40,  # 40% of credit
                time_stop_minutes=30.0,  # Shorter for credit
            )
        elif template_type == "token":
            monitor = PositionMonitor(
                position_id=position_id,
                entry_price=entry_price,
                entry_time=entry_time,
                is_debit=True,
                soft_stop_pct=0.15,  # Tighter for token
                hard_stop_pct=0.25,
                profit_target_pct=0.20,
                time_stop_minutes=20.0,  # Very short
            )
        else:  # debit default
            monitor = PositionMonitor(
                position_id=position_id,
                entry_price=entry_price,
                entry_time=entry_time,
                is_debit=True,
            )
        
        self._positions[position_id] = monitor
        logger.info(f"Registered position {position_id} for monitoring ({template_type})")
        return monitor
    
    def check_position(
        self,
        position_id: str,
        current_price: float,
        market_close_time: Optional[datetime] = None,
    ) -> List[ExitSignal]:
        """
        Check a position for exit conditions.
        
        Returns list of triggered exit signals.
        """
        if position_id not in self._positions:
            logger.warning(f"Position {position_id} not registered for monitoring")
            return []
        
        monitor = self._positions[position_id]
        now = datetime.now(timezone.utc)
        
        signals = monitor.record_sample(current_price, now)
        
        # Check EOD flatten
        if market_close_time:
            minutes_to_close = (market_close_time - now).total_seconds() / 60
            if minutes_to_close <= self.eod_exit_minutes:
                signals.append(ExitSignal(
                    trigger=ExitTrigger.EOD_FLATTEN,
                    triggered=True,
                    current_value=minutes_to_close,
                    threshold=self.eod_exit_minutes,
                    timestamp=now,
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
    
    def on_position_closed(self, position_id: str, realized_pnl: float):
        """Record position close and update daily PnL."""
        if position_id in self._positions:
            del self._positions[position_id]
        self._daily_pnl += realized_pnl
        logger.info(f"Position {position_id} closed. PnL: ${realized_pnl:.2f}. Daily: ${self._daily_pnl:.2f}")
    
    def reset_daily(self):
        """Reset for new trading day."""
        self._daily_pnl = 0.0
        for monitor in self._positions.values():
            monitor.stop_smoother.reset()
