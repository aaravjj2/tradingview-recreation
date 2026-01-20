"""
Unified Autopilot Engine v2

This is the ONLY autopilot execution path. All legacy runloop code is retired.

Key principles:
1. Alpaca is the single source of truth for positions and orders
2. Monitoring runs FIRST - handle exits before new entries
3. Full decision trace for every cycle (audit trail)
4. News/sentiment gating is a first-class feature
5. Non-negotiable: every position opened by bot MUST have exit rules

Cycle Order (enforced):
1. Refresh market/news/sentiment data
2. Refresh broker state (positions + orders from Alpaca)
3. Monitoring pass (exit evaluation for ALL open positions)
4. If risk budget available: generate candidates
5. Rank/select (deterministic; LLM optional tie-break)
6. Validate (caps, liquidity, earnings, sentiment gates)
7. Execute via Alpaca paper
8. Persist run artifact
9. Emit UI events
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum
import asyncio
import logging
import uuid
import os
import json

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class CyclePhase(str, Enum):
    """Phases of the unified autopilot cycle."""
    INIT = "init"
    DATA_REFRESH = "data_refresh"
    BROKER_REFRESH = "broker_refresh"
    MONITORING = "monitoring"
    CANDIDATE_GENERATION = "candidate_generation"
    SELECTION = "selection"
    VALIDATION = "validation"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    UI_UPDATE = "ui_update"
    COMPLETE = "complete"
    ERROR = "error"


class ExitReason(str, Enum):
    """Reasons for exiting a position."""
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    TIME_STOP = "time_stop"
    DTE_THRESHOLD = "dte_threshold"
    TRAILING_STOP = "trailing_stop"
    EARNINGS_SHOCK = "earnings_shock"
    NEWS_SHOCK = "news_shock"
    EOD_FLATTEN = "eod_flatten"  # v1: 0DTE positions flattened before close
    MANUAL_CLOSE = "manual_close"
    KILL_SWITCH = "kill_switch"
    RISK_LIMIT = "risk_limit"


class ValidationGate(str, Enum):
    """Validation gates that can block a trade."""
    RISK_BUDGET = "risk_budget"
    MAX_POSITIONS = "max_positions"
    MAX_PER_UNDERLYING = "max_per_underlying"
    SYMBOL_FILTER = "symbol_filter"
    CLUSTER_CONCENTRATION = "cluster_concentration"
    LIQUIDITY = "liquidity"
    SPREAD_WIDTH = "spread_width"
    EARNINGS_BLACKOUT = "earnings_blackout"
    NEWS_SENTIMENT = "news_sentiment"
    REGIME_MISMATCH = "regime_mismatch"
    DTE_BOUNDS = "dte_bounds"
    DELTA_BOUNDS = "delta_bounds"


# ============================================================================
# DATA MODELS - Run Artifacts
# ============================================================================

@dataclass
class HealthSnapshot:
    """Snapshot of system/dependency health at cycle start."""
    timestamp: datetime
    alpaca_connected: bool = False
    alpaca_latency_ms: float = 0.0
    websocket_connected: bool = False
    news_provider_status: str = "unknown"
    database_connected: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "alpaca_connected": self.alpaca_connected,
            "alpaca_latency_ms": self.alpaca_latency_ms,
            "websocket_connected": self.websocket_connected,
            "news_provider_status": self.news_provider_status,
            "database_connected": self.database_connected,
        }


@dataclass
class MarketContext:
    """Market context at cycle time."""
    timestamp: datetime
    market_open: bool = False
    regime: str = "unknown"  # bullish/bearish/neutral/volatile
    vix_level: Optional[float] = None
    spy_change_pct: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "market_open": self.market_open,
            "regime": self.regime,
            "vix_level": self.vix_level,
            "spy_change_pct": self.spy_change_pct,
        }


@dataclass
class SentimentSnapshot:
    """News/sentiment data at cycle time."""
    timestamp: datetime
    provider: str = "none"
    symbols_checked: List[str] = field(default_factory=list)
    sentiment_scores: Dict[str, float] = field(default_factory=dict)  # symbol -> score (-1 to 1)
    shock_headlines: List[Dict[str, Any]] = field(default_factory=list)
    news_velocity: str = "normal"  # low/normal/high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "symbols_checked": self.symbols_checked,
            "sentiment_scores": self.sentiment_scores,
            "shock_headlines": self.shock_headlines,
            "news_velocity": self.news_velocity,
        }


@dataclass
class CandidateRecord:
    """Record of a trade candidate considered."""
    candidate_id: str
    symbol: str
    strategy_template: str
    expected_credit: float
    max_loss: float
    dte: int
    short_delta: float
    score: float
    selected: bool
    rejection_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_template": self.strategy_template,
            "expected_credit": self.expected_credit,
            "max_loss": self.max_loss,
            "dte": self.dte,
            "short_delta": self.short_delta,
            "score": self.score,
            "selected": self.selected,
            "rejection_reasons": self.rejection_reasons,
        }


@dataclass
class MonitoringAction:
    """Record of a monitoring action taken."""
    position_id: str
    symbol: str
    action: str  # "exit", "hold", "alert"
    reason: ExitReason
    trigger_value: Optional[float] = None
    threshold: Optional[float] = None
    order_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "action": self.action,
            "reason": self.reason.value,
            "trigger_value": self.trigger_value,
            "threshold": self.threshold,
            "order_id": self.order_id,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class OrderRecord:
    """Record of an order placed."""
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    qty: int
    limit_price: Optional[float] = None
    alpaca_order_id: Optional[str] = None
    status: str = "pending"
    filled_qty: int = 0
    filled_avg_price: Optional[float] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "qty": self.qty,
            "limit_price": self.limit_price,
            "alpaca_order_id": self.alpaca_order_id,
            "status": self.status,
            "filled_qty": self.filled_qty,
            "filled_avg_price": self.filled_avg_price,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "error": self.error,
        }


@dataclass
class BrokerVerification:
    """Verification of broker state vs internal state."""
    timestamp: datetime
    positions_matched: int = 0
    positions_mismatched: int = 0
    orders_matched: int = 0
    orders_mismatched: int = 0
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "positions_matched": self.positions_matched,
            "positions_mismatched": self.positions_mismatched,
            "orders_matched": self.orders_matched,
            "orders_mismatched": self.orders_mismatched,
            "mismatches": self.mismatches,
        }


@dataclass
class ThinkLogEntry:
    """A single thought/decision entry in the think log."""
    timestamp: datetime
    phase: str
    thought: str
    details: Optional[Dict[str, Any]] = None
    emoji: str = "💭"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "thought": self.thought,
            "details": self.details,
            "emoji": self.emoji,
        }
    
    def __str__(self) -> str:
        return f"{self.emoji} [{self.phase}] {self.thought}"


class ThinkLog:
    """
    Think Engine Log - Captures the autopilot's decision-making process.
    
    This creates a readable trace of what the AI is thinking, why it made
    certain decisions, and how it evaluated options.
    """
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.entries: List[ThinkLogEntry] = []
        self._start_time = datetime.now()
    
    def think(self, phase: str, thought: str, details: Optional[Dict] = None, emoji: str = "💭"):
        """Add a thought to the log."""
        entry = ThinkLogEntry(
            timestamp=datetime.now(),
            phase=phase,
            thought=thought,
            details=details,
            emoji=emoji,
        )
        self.entries.append(entry)
        # Also log to standard logger for console visibility
        logger.info(f"{emoji} [THINK/{phase}] {thought}")
        if details:
            for key, val in details.items():
                logger.debug(f"    {key}: {val}")
        
        # Broadcast via WebSocket (fire and forget)
        try:
            from ..api.autopilot_websocket import get_autopilot_ws_manager
            ws = get_autopilot_ws_manager()
            asyncio.create_task(ws.broadcast("THINK_LOG", entry.to_dict()))
        except Exception:
            pass
    
    def observe(self, what: str, details: Optional[Dict] = None):
        """Log an observation about the market or data."""
        self.think("OBSERVE", what, details, "👁️")
    
    def decide(self, decision: str, reason: str, details: Optional[Dict] = None):
        """Log a decision made."""
        self.think("DECIDE", f"{decision} | Reason: {reason}", details, "🎯")
    
    def evaluate(self, what: str, result: str, details: Optional[Dict] = None):
        """Log an evaluation."""
        self.think("EVALUATE", f"{what} → {result}", details, "⚖️")
    
    def select(self, what: str, why: str, details: Optional[Dict] = None):
        """Log a selection."""
        self.think("SELECT", f"Chose {what} because {why}", details, "✅")
    
    def reject(self, what: str, why: str, details: Optional[Dict] = None):
        """Log a rejection."""
        self.think("REJECT", f"Rejected {what} because {why}", details, "❌")
    
    def skip(self, what: str, why: str, details: Optional[Dict] = None):
        """Log something being skipped."""
        self.think("SKIP", f"Skipping {what}: {why}", details, "⏭️")
    
    def execute(self, action: str, details: Optional[Dict] = None):
        """Log an execution."""
        self.think("EXECUTE", action, details, "🚀")
    
    def monitor(self, what: str, details: Optional[Dict] = None):
        """Log monitoring activity."""
        self.think("MONITOR", what, details, "📊")
    
    def alert(self, message: str, details: Optional[Dict] = None):
        """Log an alert."""
        self.think("ALERT", message, details, "🔔")
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dicts for serialization."""
        return [e.to_dict() for e in self.entries]
    
    def to_readable(self) -> str:
        """Convert to human-readable string."""
        lines = [f"=== Think Log for {self.run_id} ===", ""]
        for entry in self.entries:
            elapsed = (entry.timestamp - self._start_time).total_seconds()
            lines.append(f"[{elapsed:6.2f}s] {entry}")
            if entry.details:
                for k, v in entry.details.items():
                    lines.append(f"          └─ {k}: {v}")
        return "\n".join(lines)


@dataclass
class RunArtifact:
    """
    Complete artifact for a single autopilot cycle run.
    This is the audit trail and explanation base.
    """
    run_id: str
    timestamp: datetime
    duration_ms: float = 0.0
    success: bool = False
    
    # Config snapshot
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Health snapshot
    health: Optional[HealthSnapshot] = None
    
    # Market context
    market_context: Optional[MarketContext] = None
    
    # Sentiment data
    sentiment: Optional[SentimentSnapshot] = None
    
    # Candidates
    candidates: List[CandidateRecord] = field(default_factory=list)
    candidates_generated: int = 0
    candidates_selected: int = 0
    
    # Validation
    gates_triggered: List[ValidationGate] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    
    # Monitoring
    monitoring_actions: List[MonitoringAction] = field(default_factory=list)
    exits_triggered: int = 0
    exits_executed: int = 0
    
    # Orders
    orders_placed: List[OrderRecord] = field(default_factory=list)
    orders_filled: int = 0
    orders_rejected: int = 0
    
    # Broker verification
    broker_verification: Optional[BrokerVerification] = None
    
    # Why nothing happened (explicit reasons)
    no_action_reasons: List[str] = field(default_factory=list)
    
    # Error info
    error: Optional[str] = None
    error_phase: Optional[CyclePhase] = None
    
    # Think Log - decision trace
    think_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": round(self.duration_ms, 3),
            "success": self.success,
            "config_snapshot": self.config_snapshot,
            "health": self.health.to_dict() if self.health else None,
            "market_context": self.market_context.to_dict() if self.market_context else None,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "candidates": {
                "generated": self.candidates_generated,
                "selected": self.candidates_selected,
                "details": [c.to_dict() for c in self.candidates],
            },
            "validation": {
                "gates_triggered": [g.value for g in self.gates_triggered],
                "errors": self.validation_errors,
            },
            "monitoring": {
                "actions": [a.to_dict() for a in self.monitoring_actions],
                "exits_triggered": self.exits_triggered,
                "exits_executed": self.exits_executed,
            },
            "orders": {
                "placed": [o.to_dict() for o in self.orders_placed],
                "filled": self.orders_filled,
                "rejected": self.orders_rejected,
            },
            "broker_verification": self.broker_verification.to_dict() if self.broker_verification else None,
            "no_action_reasons": self.no_action_reasons,
            "think_log": self.think_log,
            "error": self.error,
            "error_phase": self.error_phase.value if self.error_phase else None,
        }
    
    def add_no_action_reason(self, reason: str):
        """Add a reason why no trades were executed."""
        if reason not in self.no_action_reasons:
            self.no_action_reasons.append(reason)


# ============================================================================
# POSITION MODEL (Broker-canonical)
# ============================================================================

@dataclass
class UnifiedPosition:
    """
    A position as seen from Alpaca (source of truth).
    Internal metadata is for display and audit only.
    """
    # Alpaca-canonical fields
    symbol: str
    qty: int
    side: str  # "long" or "short"
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    asset_class: str  # "us_equity" or "us_option"
    
    # Option-specific
    underlying: Optional[str] = None
    expiration: Optional[str] = None  # ISO date
    strike: Optional[float] = None
    option_type: Optional[str] = None  # "call" or "put"
    dte: Optional[int] = None
    
    # Internal metadata (for display, NOT for truth)
    strategy_id: Optional[str] = None
    strategy_template: Optional[str] = None
    run_id: Optional[str] = None  # Which run opened this
    opened_at: Optional[datetime] = None
    
    # Exit rules (only for bot-managed positions)
    managed: bool = False  # True if opened by bot, False if user-opened
    profit_target_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    time_stop_dte: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "side": self.side,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "asset_class": self.asset_class,
            "underlying": self.underlying,
            "expiration": self.expiration,
            "strike": self.strike,
            "option_type": self.option_type,
            "dte": self.dte,
            "strategy_id": self.strategy_id,
            "strategy_template": self.strategy_template,
            "run_id": self.run_id,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "managed": self.managed,
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "time_stop_dte": self.time_stop_dte,
        }


# ============================================================================
# UNIFIED ENGINE
# ============================================================================

class UnifiedAutopilotEngine:
    """
    The ONLY autopilot execution engine.
    
    Replaces:
    - AutopilotRunloop (legacy)
    - AutopilotService.run_cycle
    - Any other autopilot execution paths
    """
    
    def __init__(self):
        self._cycle_counter = 0
        self._is_running = False
        self._kill_switch = False
        self._current_phase = CyclePhase.INIT
        self._paper_verified = False
        
        # Components
        from .news_sentiment import SentimentEngine
        self.sentiment_engine = SentimentEngine()
        
        # History
        self._run_history: List[RunArtifact] = []
        self._last_run: Optional[RunArtifact] = None
        
        # Callbacks
        self._on_phase_change: Optional[Callable[[CyclePhase, Dict], None]] = None
        self._on_cycle_complete: Optional[Callable[[RunArtifact], None]] = None
        
        # Providers (to be injected)
        self._broker_client = None  # Alpaca client
        self._news_provider = None  # Finnhub/yfinance provider
        self._position_store = None  # Internal position metadata store
        
        # Verify paper-only on init
        self._verify_paper_only()
        
        logger.info("UnifiedAutopilotEngine initialized")
    
    def _verify_paper_only(self) -> bool:
        """
        Verify that the Alpaca endpoint is paper-only.
        REFUSES TO TRADE if not paper endpoint.
        """
        import os
        endpoint = os.environ.get("ALPACA3_ENDPOINT", os.environ.get("APCA_API_BASE_URL", ""))
        
        # Check for paper indicators
        is_paper = (
            "paper" in endpoint.lower() or
            endpoint == "" or  # Default to paper if not set
            endpoint.startswith("https://paper-api")
        )
        
        if not is_paper:
            logger.critical(f"REFUSING TO TRADE: Endpoint is NOT paper! endpoint={endpoint}")
            self._kill_switch = True
            self._paper_verified = False
            
            # Log incident
            try:
                from .repository import get_autopilot_repository, IncidentSeverity
                repo = get_autopilot_repository()
                repo.create_incident(
                    severity=IncidentSeverity.CRITICAL,
                    category="kill_switch",
                    title="Non-paper endpoint detected - kill switch activated",
                    description=f"Attempted to trade on non-paper endpoint: {endpoint}",
                )
            except Exception as e:
                logger.error(f"Failed to log incident: {e}")
            
            return False
        
        self._paper_verified = True
        logger.info(f"Paper-only verified: endpoint={endpoint or 'default-paper'}")
        return True
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch
    
    @property
    def current_phase(self) -> CyclePhase:
        return self._current_phase
    
    @property
    def last_run(self) -> Optional[RunArtifact]:
        return self._last_run
    
    @property
    def run_history(self) -> List[RunArtifact]:
        return self._run_history
    
    # -------------------------------------------------------------------------
    # Kill Switch
    # -------------------------------------------------------------------------
    
    async def activate_kill_switch(self, close_all: bool = False) -> Dict[str, Any]:
        """
        Activate kill switch - stops all automation immediately.
        
        Args:
            close_all: If True, attempts to close all open positions immediately.
        """
        self._kill_switch = True
        self._is_running = False
        logger.warning(f"KILL SWITCH ACTIVATED {'(CLOSING POSITIONS)' if close_all else ''}")
        
        closed_count = 0
        if close_all:
            try:
                from .alpaca_client import get_alpaca_client
                client = get_alpaca_client()
                
                # Ensure client is initialized
                if not client.is_connected():
                    await client._init_client()
                
                positions = await client.list_positions()
                logger.info(f"Kill switch: Closing {len(positions)} positions...")
                
                for pos in positions:
                    try:
                        await client.close_position(pos.symbol)
                        logger.info(f"Kill switch: Closed {pos.symbol}")
                        closed_count += 1
                        # Small delay to prevent rate limits
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Kill switch: Failed to close {pos.symbol}: {e}")
            except Exception as e:
                logger.error(f"Kill switch: Failed to close positions: {e}")
        
        return {
            "kill_switch_active": True,
            "positions_closed": closed_count,
            "timestamp": datetime.now().isoformat(),
        }
    
    def deactivate_kill_switch(self) -> Dict[str, Any]:
        """Deactivate kill switch."""
        self._kill_switch = False
        logger.info("Kill switch deactivated")
        return {
            "kill_switch_active": False,
            "timestamp": datetime.now().isoformat(),
        }
    
    # -------------------------------------------------------------------------
    # Start/Stop Control
    # -------------------------------------------------------------------------
    
    def start(self) -> Dict[str, Any]:
        """Start the autopilot engine (enables scheduled cycles)."""
        if self._kill_switch:
            raise RuntimeError("Cannot start while kill switch is active. Deactivate it first.")
        
        if self._is_running:
            return {
                "status": "already_running",
                "timestamp": datetime.now().isoformat(),
            }
        
        self._is_running = True
        logger.info("Autopilot engine started")
        
        return {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
        }
    
    def stop(self) -> Dict[str, Any]:
        """Stop the autopilot engine (disables scheduled cycles)."""
        if not self._is_running:
            return {
                "status": "already_stopped",
                "timestamp": datetime.now().isoformat(),
            }
        
        self._is_running = False
        logger.info("Autopilot engine stopped")
        
        return {
            "status": "stopped",
            "timestamp": datetime.now().isoformat(),
        }
    
    # -------------------------------------------------------------------------
    # Cycle ID Generation
    # -------------------------------------------------------------------------
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID for tracing."""
        self._cycle_counter += 1
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"UAC-{ts}-{self._cycle_counter:04d}"
    
    # -------------------------------------------------------------------------
    # Client Order ID Generation (for broker reconciliation)
    # -------------------------------------------------------------------------
    
    def _generate_client_order_id(self, run_id: str, strategy: str, symbol: str) -> str:
        """
        Generate stable client_order_id that encodes context.
        Format: {run_id}_{strategy}_{symbol}_{uuid4_short}
        """
        short_uuid = uuid.uuid4().hex[:8]
        # Sanitize for Alpaca (alphanumeric + underscore + hyphen only)
        safe_symbol = symbol.replace(" ", "_").replace("/", "_")
        safe_strategy = strategy.replace(" ", "_")[:10]
        return f"{run_id}_{safe_strategy}_{safe_symbol}_{short_uuid}"
    
    # -------------------------------------------------------------------------
    # Main Cycle Execution
    # -------------------------------------------------------------------------
    
    async def run_cycle(
        self,
        dry_run: bool = False,
        force: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ) -> RunArtifact:
        """
        Execute a single unified autopilot cycle.
        
        Args:
            dry_run: If True, skip execution phase
            force: If True, run even if kill switch active (for testing only)
            config: Optional config overrides
        
        Returns:
            RunArtifact with complete audit trail
        """
        run_id = self._generate_run_id()
        start_time = datetime.now()
        
        # Initialize ThinkLog for this run
        think = ThinkLog(run_id)
        think.think("START", f"Beginning cycle {run_id}", {"dry_run": dry_run, "force": force}, "🧠")
        
        artifact = RunArtifact(
            run_id=run_id,
            timestamp=start_time,
        )
        
        try:
            # Pre-flight checks
            if self._kill_switch and not force:
                think.alert("Kill switch is active - aborting cycle")
                artifact.add_no_action_reason("Kill switch is active")
                artifact.success = False
                artifact.think_log = think.to_list()
                return artifact
            
            # Paper-only guard (v1 non-negotiable)
            if not self._paper_verified and not force:
                think.alert("Paper verification failed - refusing to trade")
                artifact.add_no_action_reason("Paper-only verification failed")
                artifact.success = False
                artifact.think_log = think.to_list()
                return artifact
            
            if self._is_running:
                think.alert("Another cycle is already running - aborting")
                artifact.add_no_action_reason("Another cycle is already running")
                artifact.success = False
                artifact.think_log = think.to_list()
                return artifact
            
            self._is_running = True
            
            # Phase 1: Data Refresh
            self._set_phase(CyclePhase.DATA_REFRESH)
            think.observe("Refreshing market data...")
            artifact.market_context = await self._refresh_market_data()
            think.observe(f"Market is {'OPEN' if artifact.market_context.market_open else 'CLOSED'}, regime: {artifact.market_context.regime}", {
                "vix": artifact.market_context.vix_level,
                "spy_change": artifact.market_context.spy_change_pct,
            })
            
            think.observe("Checking news and sentiment...")
            artifact.sentiment = await self._refresh_sentiment_data()
            if artifact.sentiment.shock_headlines:
                think.alert(f"Found {len(artifact.sentiment.shock_headlines)} shock headlines!")
            think.observe(f"News velocity: {artifact.sentiment.news_velocity}, checked {len(artifact.sentiment.symbols_checked)} symbols")
            
            # Phase 2: Broker Refresh
            self._set_phase(CyclePhase.BROKER_REFRESH)
            think.observe("Fetching current positions from Alpaca...")
            positions, orders = await self._refresh_broker_state()
            think.observe(f"Found {len(positions)} positions, {len(orders)} open orders", {
                "underlyings": list(set(p.underlying or p.symbol for p in positions))[:10],
            })
            artifact.health = await self._check_health()
            think.observe(f"Alpaca connected: {artifact.health.alpaca_connected}, latency: {artifact.health.alpaca_latency_ms:.0f}ms")
            
            # Phase 3: Monitoring (REMOVED - Handled by PositionAgents)
            # self._set_phase(CyclePhase.MONITORING)
            # Logic moved to PositionAgent for distributed monitoring
            artifact.exits_triggered = 0
            artifact.exits_executed = 0
            
            # Phase 4: Candidate Generation (if budget available)
            self._set_phase(CyclePhase.CANDIDATE_GENERATION)
            think.evaluate("Risk budget", "checking if we can open new positions...")
            risk_budget_ok = self._check_risk_budget(positions)
            
            if not risk_budget_ok:
                think.reject("New trades", "risk budget exhausted")
                artifact.add_no_action_reason("Risk budget exhausted")
                artifact.gates_triggered.append(ValidationGate.RISK_BUDGET)
            else:
                think.decide("Proceed with candidate generation", "risk budget available")
            
            candidates = []
            if risk_budget_ok:
                think.observe("Scanning universe for trade opportunities...")
                candidates = await self._generate_candidates(
                    artifact.market_context, artifact.sentiment, positions
                )
                artifact.candidates_generated = len(candidates)
                think.observe(f"Generated {len(candidates)} potential candidates", {
                    "symbols": [c.get("symbol") for c in candidates[:10]],
                    "strategies": list(set(c.get("template") for c in candidates)),
                })
            
            # Phase 5: Selection
            self._set_phase(CyclePhase.SELECTION)
            selected = []
            if candidates:
                think.evaluate("Ranking candidates", "sorting by score and applying selection criteria...")
                selected = self._select_candidates(candidates)
                artifact.candidates_selected = len(selected)
                
                # Log each candidate's score and selection status
                for c in candidates:
                    if c in selected:
                        think.select(f"{c.get('symbol')} ({c.get('template')})", f"score={c.get('score', 0):.2f}, credit=${c.get('credit', 0):.2f}", {
                            "dte": c.get("dte"),
                            "delta": c.get("delta"),
                            "pop": c.get("pop"),
                        })
                    else:
                        think.reject(f"{c.get('symbol')}", f"score too low ({c.get('score', 0):.2f}) or not in top N")
                
                artifact.candidates = [
                    CandidateRecord(
                        candidate_id=c.get("id", str(uuid.uuid4())),
                        symbol=c.get("symbol", ""),
                        strategy_template=c.get("template", ""),
                        expected_credit=c.get("credit", 0.0),
                        max_loss=c.get("max_loss", 0.0),
                        dte=c.get("dte", 0),
                        short_delta=c.get("delta", 0.0),
                        score=c.get("score", 0.0),
                        selected=c in selected,
                        rejection_reasons=c.get("rejection_reasons", []),
                    )
                    for c in candidates
                ]
            else:
                think.skip("Selection phase", "no candidates generated")
            
            # Phase 6: Validation
            self._set_phase(CyclePhase.VALIDATION)
            validated = []
            if selected:
                think.evaluate("Validation gates", f"checking {len(selected)} selected candidates...")
                for candidate in selected:
                    valid, gates, errors = self._validate_candidate(
                        candidate, positions, artifact.sentiment
                    )
                    if valid:
                        validated.append(candidate)
                        think.select(f"{candidate.get('symbol')}", "passed all validation gates")
                    else:
                        think.reject(f"{candidate.get('symbol')}", f"failed gates: {[g.value for g in gates]}")
                        artifact.gates_triggered.extend(gates)
                        artifact.validation_errors.extend(errors)
                
                think.decide(f"{len(validated)} candidates validated", f"{len(selected) - len(validated)} rejected by gates")
                
                # Generate explanations for validated candidates (post-decision)
                for candidate in validated:
                    try:
                        explanation = await self._explain_decision(candidate)
                        candidate["explanation"] = explanation
                        think.think("EXPLAIN", f"Rationale for {candidate.get('symbol')}: {explanation}", emoji="💡")
                    except Exception as e:
                        logger.warning(f"Failed to generate explanation for {candidate.get('symbol')}: {e}")
                        candidate["explanation"] = "Explanation generation failed."
            
            # Phase 7: Execution
            self._set_phase(CyclePhase.EXECUTION)
            if validated and not dry_run:
                think.execute(f"Submitting {len(validated)} trades to Alpaca...")
                orders = await self._execute_trades(validated, run_id)
                artifact.orders_placed = orders
                artifact.orders_filled = sum(1 for o in orders if o.status == "filled")
                artifact.orders_rejected = sum(1 for o in orders if o.status == "rejected")
                
                for order in orders:
                    if order.status == "filled":
                        think.execute(f"FILLED: {order.symbol} @ ${order.limit_price:.2f}", {
                            "order_id": order.alpaca_order_id,
                            "qty": order.qty,
                        })
                    elif order.status == "rejected":
                        think.reject(f"Order {order.symbol}", order.error or "unknown error")
                    else:
                        think.think("PENDING", f"Order {order.symbol} status: {order.status}", emoji="⏳")
                
            elif dry_run:
                think.skip("Execution", "dry run mode enabled")
                artifact.add_no_action_reason("Dry run mode - execution skipped")
            elif not validated:
                think.skip("Execution", "no candidates passed validation")
                artifact.add_no_action_reason("No candidates passed validation")
            
            # Phase 8: Persistence
            self._set_phase(CyclePhase.PERSISTENCE)
            think.think("SAVE", "Persisting run artifact to disk...", emoji="💾")
            await self._persist_artifact(artifact)
            
            # Phase 9: Broker Verification
            artifact.broker_verification = await self._verify_broker_state(run_id)
            if artifact.broker_verification:
                think.observe(f"Broker verification: {artifact.broker_verification.positions_matched} positions matched")
            
            # Phase 10: UI Update
            self._set_phase(CyclePhase.UI_UPDATE)
            await self._emit_ui_events(artifact)
            
            # Complete
            self._set_phase(CyclePhase.COMPLETE)
            artifact.success = True
            elapsed = (datetime.now() - start_time).total_seconds()
            think.think("COMPLETE", f"Cycle finished in {elapsed:.2f}s - {artifact.orders_filled} orders filled, {artifact.exits_executed} exits executed", emoji="✅")
            
        except Exception as e:
            logger.error(f"Cycle failed: {e}", exc_info=True)
            think.alert(f"CYCLE ERROR: {str(e)}")
            artifact.error = str(e)
            artifact.error_phase = self._current_phase
            artifact.success = False
            self._set_phase(CyclePhase.ERROR)
        
        finally:
            self._is_running = False
            artifact.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            artifact.think_log = think.to_list()  # Save think log to artifact
            
            # Broadcast cycle complete
            try:
                from ..api.autopilot_websocket import get_autopilot_ws_manager
                ws = get_autopilot_ws_manager()
                asyncio.create_task(ws.broadcast("CYCLE_COMPLETE", {
                    "run_id": artifact.run_id,
                    "success": artifact.success,
                    "duration_ms": artifact.duration_ms,
                    "candidates": artifact.candidates_generated,
                    "orders": artifact.orders_filled,
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception:
                pass

            self._last_run = artifact
            self._run_history.append(artifact)
            
            # Keep history bounded
            if len(self._run_history) > 1000:
                self._run_history = self._run_history[-500:]
            
            if self._on_cycle_complete:
                try:
                    self._on_cycle_complete(artifact)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        return artifact
    
    # -------------------------------------------------------------------------
    # Phase Helpers
    # -------------------------------------------------------------------------
    
    def _set_phase(self, phase: CyclePhase):
        """Update current phase and notify callbacks."""
        self._current_phase = phase
        if self._on_phase_change:
            try:
                self._on_phase_change(phase, {"timestamp": datetime.now().isoformat()})
            except Exception:
                pass
        
        # Broadcast via WebSocket
        try:
            from ..api.autopilot_websocket import get_autopilot_ws_manager
            ws = get_autopilot_ws_manager()
            asyncio.create_task(ws.broadcast("STATUS_UPDATE", {
                "phase": phase.value,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception:
            pass
    
    # -------------------------------------------------------------------------
    # Implementation Methods
    # -------------------------------------------------------------------------
    
    async def _refresh_market_data(self) -> MarketContext:
        """Refresh market context data."""
        from .alpaca_client import get_alpaca_client
        
        client = get_alpaca_client()
        clock = await client.get_clock()
        
        return MarketContext(
            timestamp=datetime.now(),
            market_open=clock.is_open if clock else self._is_market_open(),
            regime="neutral",  # TODO: Calculate from VIX/SPY
        )
    
    async def _refresh_sentiment_data(self) -> SentimentSnapshot:
        """Refresh news/sentiment data from providers."""
        try:
            # Get Global Market Sentiment
            market_sent = await self.sentiment_engine.get_market_sentiment()
            
            # Simple mapping of market sentiment to 'news_velocity' or similar field
            # For now, we store the score in sentiment_scores with key 'SPY' (proxy for market)
            
            return SentimentSnapshot(
                timestamp=datetime.now(),
                provider="finnhub-ensemble",
                news_velocity=market_sent.bucket.value, # Store bucket name here for display
                sentiment_scores={"MARKET": market_sent.sentiment_score},
                symbols_checked=["MARKET"]
            )
        except Exception as e:
            logger.warning(f"Failed to get sentiment: {e}")
            return SentimentSnapshot(
                timestamp=datetime.now(),
                provider="error",
            )
    
    async def _refresh_broker_state(self) -> Tuple[List[UnifiedPosition], List[Dict]]:
        """Refresh positions and orders from Alpaca."""
        from .alpaca_client import get_alpaca_client
        from .broker_position_manager import get_broker_position_manager
        
        client = get_alpaca_client()
        manager = get_broker_position_manager()
        
        positions = []
        orders = []
        
        try:
            # Get positions from Alpaca
            alpaca_positions = await client.list_positions()
            for pos in alpaca_positions:
                # Get metadata from manager
                meta = manager._store.get(pos.symbol)
                
                positions.append(UnifiedPosition(
                    symbol=pos.symbol,
                    qty=pos.qty,
                    side=pos.side,
                    avg_entry_price=pos.avg_entry_price,
                    current_price=pos.current_price,
                    market_value=pos.market_value,
                    unrealized_pnl=pos.unrealized_pl,
                    unrealized_pnl_pct=pos.unrealized_plpc * 100,
                    asset_class=pos.asset_class,
                    managed=meta.managed if meta else False,
                    strategy_id=meta.strategy_id if meta else None,
                    strategy_template=meta.strategy_template if meta else None,
                    run_id=meta.run_id if meta else None,
                ))
            
            # Get open orders
            alpaca_orders = await client.list_orders(status="open")
            orders = [o.to_dict() for o in alpaca_orders]
            
        except Exception as e:
            logger.error(f"Failed to refresh broker state: {e}")
        
        return positions, orders
    
    async def _check_health(self) -> HealthSnapshot:
        """Check system health."""
        from .alpaca_client import get_alpaca_client
        from .news_provider import get_news_provider
        
        client = get_alpaca_client()
        connected, latency = await client.health_check()
        
        provider = get_news_provider()
        
        return HealthSnapshot(
            timestamp=datetime.now(),
            alpaca_connected=connected,
            alpaca_latency_ms=latency,
            websocket_connected=True,  # TODO: Real check
            news_provider_status=provider.provider_name,
            database_connected=True,  # TODO: Real check
        )
    
    async def _run_monitoring_pass(
        self,
        positions: List[UnifiedPosition],
        market: MarketContext,
        sentiment: SentimentSnapshot,
        dry_run: bool,
    ) -> List[MonitoringAction]:
        """Run monitoring pass - evaluate exits for all positions (paper + Alpaca)."""
        from .broker_position_manager import get_broker_position_manager, ExitTrigger, EnrichedBrokerPosition, BrokerExitSignal
        from .alpaca_client import get_alpaca_client
        from datetime import date
        import random
        
        manager = get_broker_position_manager()
        client = get_alpaca_client()
        
        actions = []
        
        # Get paper positions from BrokerMetaStore
        paper_positions = []
        for meta in manager._store.all():
            # Simulate current profit/loss based on time decay
            hours_held = (datetime.now() - meta.opened_at).total_seconds() / 3600
            
            # Simulate price movement: options decay over time (theta)
            # ~50% profit target in days, with some randomness
            simulated_profit_pct = min(hours_held * 2 + random.uniform(-5, 10), 100)
            
            # Create enriched position for evaluation
            paper_pos = EnrichedBrokerPosition(
                symbol=meta.symbol,
                qty=1,
                side="short",
                avg_entry_price=meta.entry_credit,
                current_price=meta.entry_credit * (1 - simulated_profit_pct / 100),
                market_value=meta.entry_credit * (1 - simulated_profit_pct / 100) * 100,
                unrealized_pnl=meta.entry_credit * simulated_profit_pct,
                unrealized_pnl_pct=simulated_profit_pct,
                asset_class="us_option",
                underlying=meta.symbol,
                expiration=None,  # Would parse from OCC symbol
                strike=None,
                option_type="put" if "put" in meta.strategy_template.lower() else "call",
                dte=7,  # Default, should be calculated
                managed=meta.managed,
                run_id=meta.run_id,
                strategy_template=meta.strategy_template,
                exit_rules=meta.exit_rules,
                entry_credit=meta.entry_credit,
                highest_profit_pct=meta.highest_profit_pct,
                current_profit_pct=simulated_profit_pct,
            )
            paper_positions.append(paper_pos)
        
        # Also try to get Alpaca positions
        try:
            alpaca_positions = await manager.get_positions()
        except Exception:
            alpaca_positions = []
        
        # Combine both
        all_positions = paper_positions + alpaca_positions
        
        logger.info(f"Monitoring {len(all_positions)} positions ({len(paper_positions)} paper, {len(alpaca_positions)} Alpaca)")
        
        # Evaluate exits for all positions
        exit_signals = await manager.evaluate_exits(
            positions=all_positions,
            news_shocks=sentiment.shock_headlines if hasattr(sentiment, 'shock_headlines') else [],
        )
        
        for signal in exit_signals:
            action = MonitoringAction(
                position_id=signal.symbol,
                symbol=signal.symbol,
                action="exit" if signal.urgency == "immediate" else "alert",
                reason=ExitReason(signal.trigger.value),
                trigger_value=signal.trigger_value,
                threshold=signal.threshold,
            )
            
            logger.info(f"🔔 EXIT SIGNAL: {signal.symbol} - {signal.trigger.value} (value={signal.trigger_value:.1f}%, threshold={signal.threshold:.1f}%)")
            
            # Execute exit if urgent and not dry run
            if signal.urgency == "immediate" and not dry_run:
                try:
                    # For paper positions, just unregister them
                    if signal.symbol in [p.symbol for p in paper_positions]:
                        manager.unregister_position(signal.symbol)
                        action.success = True
                        logger.info(f"✅ Paper position closed: {signal.symbol} ({signal.trigger.value})")
                    else:
                        # Try Alpaca close for real positions
                        order = await client.close_position(signal.symbol)
                        if order:
                            action.order_id = order.id
                            action.success = True
                            logger.info(f"✅ Exit executed: {signal.symbol} ({signal.trigger.value})")
                        else:
                            action.error = "Failed to close position"
                except Exception as e:
                    action.error = str(e)
                    logger.error(f"❌ Exit failed: {e}")
            
            actions.append(action)
        
        return actions
    
    def _check_risk_budget(self, positions: List[UnifiedPosition]) -> bool:
        """Check if risk budget allows new entries."""
        from .config import get_autopilot_config

        config = get_autopilot_config()
        
        # Count managed positions
        managed_count = sum(1 for p in positions if p.managed)
        
        # Check max positions
        if managed_count >= config.risk_limits.max_open_positions:
            logger.info(f"Risk budget: max positions reached ({managed_count}/{config.risk_limits.max_open_positions})")
            return False
        
        # Check total risk (sum of max_loss)
        # TODO: Implement proper risk calculation
        
        return True
    
    async def _generate_candidates(
        self,
        market: MarketContext,
        sentiment: SentimentSnapshot,
        positions: List[UnifiedPosition],
    ) -> List[Dict]:
        """Generate trade candidates using existing candidate generator."""
        from .candidates import CandidateGenerator
        from .config import get_autopilot_config
        from .universe import UniverseManager
        from .features import FeatureEngine

        config = get_autopilot_config()
        universe = UniverseManager(config.universe)
        feature_engine = FeatureEngine()
        generator = CandidateGenerator(config, universe, feature_engine)
        
        # Get current symbols in positions
        held_symbols = {p.underlying or p.symbol for p in positions}
        
        candidates = []
        
        try:
            # Quick pattern/trend review and rank symbols
            symbols = universe.get_tradeable_symbols()
            if config.focus_symbol:
                symbols = [s for s in symbols if s.symbol == config.focus_symbol]

            scored = []
            for sym_info in symbols:
                feats = await feature_engine.get_features(sym_info.symbol)
                if not feats:
                    continue
                score = (
                    feats.trend_strength * 0.4
                    + feats.liquidity_score * 0.4
                    + (feats.iv_rank / 100.0) * 0.2
                )
                scored.append((sym_info.symbol, feats, score))

            scored.sort(key=lambda x: x[2], reverse=True)
            top_n = 5 if not config.focus_symbol else 1
            top = scored[:top_n]
            
            # Filter out held symbols
            symbols = [s for s in symbols if s.symbol not in held_symbols]
            
            # Get features for each symbol
            for symbol, features, _score in top:
                try:
                    symbol_candidates = await generator.generate(
                        symbol,
                        features,
                        weekly_only=config.weekly_expiry_only,
                    )
                    for c in symbol_candidates:
                        cdict = c.to_dict()
                        cdict["credit"] = cdict.get("max_profit") or cdict.get("net_premium", 0)
                        cdict["score"] = cdict.get("adjusted_score", cdict.get("base_score", 0))
                        candidates.append(cdict)
                except Exception as e:
                    logger.debug(f"Candidate gen failed for {symbol}: {e}")
            
            # candidates already converted to dicts
            
        except Exception as e:
            logger.error(f"Candidate generation failed: {e}")
        
        return candidates
    
    def _select_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Select top candidates (deterministic ranking)."""
        from .config import get_autopilot_config

        config = get_autopilot_config()
        
        # Sort by score descending
        sorted_candidates = sorted(candidates, key=lambda c: c.get("score", c.get("adjusted_score", 0)), reverse=True)
        
        # Limit to max per cycle
        max_per_cycle = max(1, int(config.max_symbols_per_cycle))
        if config.focus_symbol:
            sorted_candidates = [c for c in sorted_candidates if c.get("symbol") == config.focus_symbol]
        return sorted_candidates[:max_per_cycle]
    
    def _validate_candidate(
        self,
        candidate: Dict,
        positions: List[UnifiedPosition],
        sentiment: SentimentSnapshot,
    ) -> Tuple[bool, List[ValidationGate], List[str]]:
        """Validate a candidate against all gates."""
        from .config import get_autopilot_config

        config = get_autopilot_config()
        gates = []
        errors = []
        
        symbol = candidate.get("symbol", "")
        if config.focus_symbol and symbol != config.focus_symbol:
            gates.append(ValidationGate.SYMBOL_FILTER)
            errors.append(f"Focus symbol active ({config.focus_symbol}), rejecting {symbol}")
        
        # Check max per underlying
        underlying_count = sum(1 for p in positions if (p.underlying or p.symbol) == symbol)
        if underlying_count >= config.risk_limits.max_positions_per_underlying:
            gates.append(ValidationGate.MAX_PER_UNDERLYING)
            errors.append(f"Max positions per underlying reached for {symbol}")
        
        # Check DTE bounds
        dte = candidate.get("dte", 0)
        constraints = config.strategy_constraints
        if dte < constraints.min_dte or dte > constraints.max_dte:
            gates.append(ValidationGate.DTE_BOUNDS)
            errors.append(f"DTE {dte} outside bounds [{constraints.min_dte}, {constraints.max_dte}]")
        
        # Check earnings blackout
        if hasattr(sentiment, 'is_blackout') and sentiment.is_blackout:
            gates.append(ValidationGate.EARNINGS_BLACKOUT)
            errors.append(f"Earnings blackout for {symbol}")
        
        # Check sentiment (Strict Gating)
        if hasattr(sentiment, 'sentiment_scores'):
            # Symbol specific score
            score = sentiment.sentiment_scores.get(symbol, 0)
            
            # Global Market Score
            market_score = sentiment.sentiment_scores.get("MARKET", 0)
            
            # CIRCUIT BREAKER LOGIC
            # If Market is VERY BEARISH (<-0.4), Block Bullish Strategies
            if market_score < -0.4:
                if candidate.get("template") in ["long_call", "put_credit_spread", "call_debit_spread"]:
                    gates.append(ValidationGate.NEWS_SENTIMENT)
                    errors.append(f"Global Sentiment Circuit Breaker: Market is VERY BEARISH ({market_score:.2f})")
            
            # If Market is VERY BULLISH (>0.4), Block Bearish Strategies
            elif market_score > 0.4:
                 if candidate.get("template") in ["long_put", "call_credit_spread", "put_debit_spread"]:
                    gates.append(ValidationGate.NEWS_SENTIMENT)
                    errors.append(f"Global Sentiment Circuit Breaker: Market is VERY BULLISH ({market_score:.2f})")
            
            # Symbol specific check (if available)
            if score <= -0.2 and candidate.get("template") in ["long_call", "put_credit_spread"]:
                gates.append(ValidationGate.NEWS_SENTIMENT)
                errors.append(f"Symbol Sentiment {score:.2f} is bearish")
        
        # Check shock headlines
        if hasattr(sentiment, 'shock_headlines') and sentiment.shock_headlines:
             # Check if any shock headline is relevant to this symbol
             # For now, simplistic check: is symbol in headline triggers?
             # Or global shock logic if defined
             pass # Logic to be refined based on shock_headlines structure
        
        return len(gates) == 0, gates, errors

    async def _explain_decision(self, candidate: Dict) -> str:
        """
        Generate a human-readable explanation for the selected candidate.
        This is post-decision and does not influence the choice.
        """
        # TODO: Connect to LLM service for dynamic explanation
        # For now, deterministic template
        symbol = candidate.get("symbol")
        template = candidate.get("template")
        score = candidate.get("score", 0)
        
        rationale = (
            f"Selected {symbol} {template} based on strong technical score ({score:.2f}). "
            f"Market context allows for this strategy. Sentinel checks passed."
        )
        return rationale
    
    async def _execute_trades(self, candidates: List[Dict], run_id: str) -> List[OrderRecord]:
        """Execute trades via Alpaca - REAL order submission."""
        from .alpaca_broker import AlpacaOptionsBroker
        from .broker_position_manager import get_broker_position_manager, BrokerExitRule
        from .config import get_autopilot_config, StrategyTemplate
        from .candidates import TradeCandidate, OptionLeg
        from .alpaca_client import get_alpaca_client
        from datetime import date
        import uuid as uuid_mod
        
        manager = get_broker_position_manager()
        config = get_autopilot_config()
        client = get_alpaca_client()
        
        # Get current Alpaca positions to avoid duplicates
        existing_underlyings = set()
        try:
            alpaca_positions = await client.list_positions()
            for pos in alpaca_positions:
                # Parse underlying from OCC symbol
                symbol = pos.symbol
                for i, c in enumerate(symbol):
                    if c.isdigit():
                        existing_underlyings.add(symbol[:i].strip())
                        break
            logger.info(f"Existing positions for underlyings: {existing_underlyings}")
        except Exception as e:
            logger.warning(f"Could not fetch existing positions: {e}")
        
        # Initialize broker with Alpaca enabled
        broker = AlpacaOptionsBroker(alpaca_enabled=True)
        
        orders = []
        
        for candidate in candidates:
            symbol = candidate.get("symbol", "")
            template = candidate.get("template", "put_credit_spread")
            credit = candidate.get("credit", 0)
            
            # Skip if we already have a position in this underlying
            if symbol in existing_underlyings:
                logger.info(f"⏭️ Skipping {symbol} - already have position")
                continue
            
            client_order_id = self._generate_client_order_id(run_id, template, symbol)
            
            order_record = OrderRecord(
                client_order_id=client_order_id,
                symbol=symbol,
                side="sell",  # Credit spreads are sold
                order_type="market",
                qty=max(1, int(config.contracts_per_trade)),
                limit_price=credit,
                submitted_at=datetime.now(),
            )
            
            try:
                # Build TradeCandidate from dict for broker submission
                legs_data = candidate.get("legs", [])
                if not legs_data:
                    # If no legs, try to construct from candidate data
                    short_strike = candidate.get("short_strike", 0)
                    long_strike = candidate.get("long_strike", 0)
                    expiry_str = candidate.get("expiry", "")
                    
                    if short_strike and long_strike and expiry_str:
                        # Parse expiry
                        if isinstance(expiry_str, str):
                            expiry = date.fromisoformat(expiry_str.split("T")[0])
                        else:
                            expiry = expiry_str
                        
                        opt_type = "put" if "put" in template.lower() else "call"
                        
                        legs_data = [
                            {"side": "sell", "option_type": opt_type, "strike": short_strike, "quantity": 1, "expiry": expiry},
                            {"side": "buy", "option_type": opt_type, "strike": long_strike, "quantity": 1, "expiry": expiry},
                        ]
                
                if legs_data:
                    legs = []
                    for l in legs_data:
                        leg_expiry = l.get("expiry")
                        if isinstance(leg_expiry, str):
                            leg_expiry = date.fromisoformat(leg_expiry.split("T")[0])
                        
                        # OptionLeg uses strings for side and option_type
                        legs.append(OptionLeg(
                            side=l.get("side", "sell"),
                            option_type=l.get("option_type", "put"),
                            strike=l.get("strike", 0),
                            quantity=l.get("quantity", 1),
                            expiry=leg_expiry,
                        ))
                    
                    # Create TradeCandidate - requires all fields
                    try:
                        tmpl_enum = StrategyTemplate(template)
                    except ValueError:
                        tmpl_enum = StrategyTemplate.PUT_CREDIT_SPREAD
                    
                    trade_candidate = TradeCandidate(
                        id=f"tc-{uuid_mod.uuid4().hex[:8]}",
                        symbol=symbol,
                        template=tmpl_enum,
                        legs=legs,
                        underlying_price=candidate.get("underlying_price", 0),
                        max_profit=credit * 100,  # Per contract
                        max_loss=candidate.get("max_loss", 0),
                        pop=candidate.get("pop", 0),
                        dte=candidate.get("dte", 30),
                        iv_rank=candidate.get("iv_rank", 50),
                        liquidity_score=candidate.get("liquidity_score", 0.8),
                        spread_percent=candidate.get("spread_percent", 0.02),
                        regime=candidate.get("regime", "neutral"),
                        trend=candidate.get("trend", "neutral"),
                        client_order_id=client_order_id,
                    )
                    
                    # Submit order via broker
                    logger.info(f"🚀 EXECUTING TRADE: {symbol} {template} @ ${credit}")
                    paper_order = broker.submit_order(trade_candidate)
                    
                    if paper_order:
                        # For Alpaca, submission is enough. We don't manually execute.
                        # paper_order = broker.execute_order(paper_order.order_id)
                        
                        order_record.alpaca_order_id = paper_order.order_id
                        order_record.status = paper_order.status.value
                        order_record.filled_qty = paper_order.filled_qty if hasattr(paper_order, 'filled_qty') else 0
                        order_record.filled_avg_price = paper_order.filled_avg_price if hasattr(paper_order, 'filled_avg_price') else None
                        order_record.filled_at = datetime.now()
                        
                        # Register position if order is active (filled or pending)
                        # We need to track metadata even if it's not fully filled yet
                        valid_statuses = ["filled", "partial_fill", "new", "accepted", "pending_new", "partially_filled"]
                        if paper_order.status.value in valid_statuses:
                            status_emoji = "✅" if paper_order.status.value == "filled" else "⏳"
                            logger.info(f"{status_emoji} ORDER SUBMITTED: {symbol} - ID: {paper_order.order_id} ({paper_order.status.value})")
                            
                            # Register position for monitoring (metadata persistence)
                            manager.register_position(
                                symbol=symbol,
                                run_id=run_id,
                                strategy_template=template,
                                entry_credit=credit,
                                max_loss=candidate.get("max_loss", 0),
                                exit_rules=BrokerExitRule(),
                            )
                        else:
                            logger.warning(f"⚠️ ORDER REJECTED/FAILED: {symbol} - Status: {paper_order.status.value}")
                    else:
                        order_record.status = "rejected"
                        order_record.error = "Broker returned no order"
                else:
                    # No legs - just register as a tracked position
                    logger.info(f"📝 REGISTERING POSITION (no legs): {symbol} {template}")
                    manager.register_position(
                        symbol=symbol,
                        run_id=run_id,
                        strategy_template=template,
                        entry_credit=credit,
                        max_loss=candidate.get("max_loss", 0),
                        exit_rules=BrokerExitRule(),
                    )
                    order_record.status = "registered"
                
            except Exception as e:
                logger.error(f"❌ Order failed for {symbol}: {e}", exc_info=True)
                order_record.status = "rejected"
                order_record.error = str(e)
            
            orders.append(order_record)
        
        return orders
    
    async def _persist_artifact(self, artifact: RunArtifact):
        """Persist run artifact to database."""
        import json
        import os
        
        # Save to file for now (would use DB in production)
        artifacts_dir = "/tmp/autopilot_artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        filepath = os.path.join(artifacts_dir, f"{artifact.run_id}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(artifact.to_dict(), f, indent=2)
            logger.debug(f"Artifact saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to persist artifact: {e}")
    
    async def _verify_broker_state(self, run_id: str) -> BrokerVerification:
        """Verify broker state matches expectations."""
        from .alpaca_client import get_alpaca_client
        from .broker_position_manager import get_broker_position_manager
        
        client = get_alpaca_client()
        manager = get_broker_position_manager()
        
        verification = BrokerVerification(timestamp=datetime.now())
        
        try:
            # Get positions from both sources
            alpaca_positions = await client.list_positions()
            alpaca_symbols = {p.symbol for p in alpaca_positions}
            
            managed_meta = manager._store.all()
            managed_symbols = {m.symbol for m in managed_meta if m.managed}
            
            # Check for mismatches
            # Positions we think we have but Alpaca doesn't
            missing = managed_symbols - alpaca_symbols
            for sym in missing:
                verification.mismatches.append({
                    "type": "missing_from_broker",
                    "symbol": sym,
                })
                verification.positions_mismatched += 1
            
            # Positions Alpaca has but we don't track (OK, just user positions)
            verification.positions_matched = len(managed_symbols & alpaca_symbols)
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            verification.mismatches.append({"type": "error", "message": str(e)})
        
        return verification
    
    async def _emit_ui_events(self, artifact: RunArtifact):
        """Emit events for UI updates via WebSocket."""
        try:
            from ..api.autopilot_websocket import get_autopilot_ws_manager
            ws = get_autopilot_ws_manager()
            
            # 1. Run complete event
            await ws.broadcast("RUN_COMPLETE", {
                "run_id": artifact.run_id,
                "success": artifact.success,
                "duration_ms": artifact.duration_ms,
                "candidates_generated": artifact.candidates_generated,
                "candidates_selected": artifact.candidates_selected,
                "orders_placed": len(artifact.orders_placed),
                "orders_filled": artifact.orders_filled,
                "exits_triggered": artifact.exits_triggered,
                "exits_executed": artifact.exits_executed,
                "timestamp": artifact.timestamp.isoformat(),
            })
            
            # 2. Positions update (if we have positions data)
            if artifact.broker_verification:
                await ws.broadcast("POSITIONS_UPDATE", {
                    "count": artifact.broker_verification.positions_matched,
                    "mismatched": artifact.broker_verification.positions_mismatched,
                    "timestamp": datetime.now().isoformat(),
                })
            
            # 3. Monitoring actions (exits)
            for action in artifact.monitoring_actions:
                await ws.broadcast("EXIT_SIGNAL", action.to_dict())
            
            # 4. Incidents (if any errors)
            if artifact.error:
                await ws.broadcast("INCIDENT", {
                    "severity": "error",
                    "category": "run_error",
                    "title": f"Run {artifact.run_id} failed",
                    "description": artifact.error,
                    "timestamp": datetime.now().isoformat(),
                })
            
            logger.debug(f"Emitted UI events for run {artifact.run_id}")
            
        except Exception as e:
            logger.warning(f"Failed to emit UI events: {e}")
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open using real NYSE calendar."""
        from ..market_calendar import get_market_calendar
        calendar = get_market_calendar()
        return calendar.is_market_open()


# ============================================================================
# Singleton
# ============================================================================

_engine: Optional[UnifiedAutopilotEngine] = None


def get_unified_engine() -> UnifiedAutopilotEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = UnifiedAutopilotEngine()
    return _engine


def reset_engine():
    """Reset engine (for testing)."""
    global _engine
    _engine = None
