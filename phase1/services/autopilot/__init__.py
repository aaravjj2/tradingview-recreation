"""
AI Options Autopilot - Paper Trading System

This module implements a fully automated options trading system operating
in paper mode only. The system uses deterministic risk rules with optional
LLM-based candidate ranking.

Components:
- config: Autopilot configuration and budget management
- universe: Liquid options universe management
- features: Market feature computation (regime, IV, liquidity)
- candidates: Deterministic trade candidate generation
- selector: Ranking/selection interface (deterministic + LLM)
- validator: Hard risk rule enforcement
- paper_broker: Paper trade execution simulation
- position_manager: Options position ledger with Greeks
- monitor: Exit monitoring and risk management
- reporting: Daily P&L and attribution reports
- runloop: Main orchestration loop
"""

from .config import (
    AutopilotConfig,
    AutopilotMode,
    StrategyTemplate,
    RiskLimits,
    StrategyConstraints,
    EarningsPolicy,
    ForecastSettings,
    LLMSettings,
)
from .universe import UniverseManager, UniverseSymbol, LiquidityFilter
from .features import (
    FeatureEngine,
    SymbolFeatures,
    TrendDirection,
    VolatilityRegime,
    PriceForecast,
)
from .candidates import (
    CandidateGenerator,
    TradeCandidate,
    OptionLeg,
    CandidateStatus,
)
from .selector import (
    CandidateSelector,
    DeterministicRanker,
    LLMRanker,
    SelectionResult,
    create_selector,
)
from .validator import (
    TradeValidator,
    ValidationResult,
    BatchValidationResult,
    RejectionCode,
)
from .paper_broker import (
    PaperBroker,
    PaperOrder,
    PaperFill,
    OrderStatus,
    OrderType,
    FillMetrics,
)
from .position_manager import (
    PositionManager,
    OptionsPosition,
    PositionStatus,
    PositionGreeks,
    PortfolioState,
)
from .monitor import (
    PositionMonitor,
    ExitSignal,
    ExitReason,
    RiskAlert,
    MonitoringResult,
)
from .reporting import (
    ReportGenerator,
    DailyReport,
    TemplateAttribution,
    SymbolAttribution,
    RunCycleLog,
    ActivityLogger,
)
from .runloop import (
    AutopilotRunloop,
    CycleResult,
    RunloopState,
)
from .unified_cycle import (
    UnifiedAutopilot,
    CyclePhase,
    CycleMetrics,
    DecisionTrace,
)
from .trade_stream import (
    TradeUpdateType,
    TradeUpdate,
    AlpacaTradeStream,
    TradeUpdateHandler,
    get_trade_handler,
)
from .news_sentiment import (
    NewsCategory,
    SentimentBucket,
    RecencyBucket,
    NewsArticle,
    SentimentScore,
    FinnhubNewsProvider,
    SentimentEngine,
    get_news_provider,
    get_sentiment_engine,
)

__all__ = [
    # Config
    'AutopilotConfig',
    'AutopilotMode',
    'StrategyTemplate',
    'RiskLimits',
    'StrategyConstraints',
    'EarningsPolicy',
    'ForecastSettings',
    'LLMSettings',
    # Universe
    'UniverseManager',
    'UniverseSymbol',
    'LiquidityFilter',
    # Features
    'FeatureEngine',
    'SymbolFeatures',
    'TrendDirection',
    'VolatilityRegime',
    'PriceForecast',
    # Candidates
    'CandidateGenerator',
    'TradeCandidate',
    'OptionLeg',
    'CandidateStatus',
    # Selector
    'CandidateSelector',
    'DeterministicRanker',
    'LLMRanker',
    'SelectionResult',
    'create_selector',
    # Validator
    'TradeValidator',
    'ValidationResult',
    'BatchValidationResult',
    'RejectionCode',
    # Paper Broker
    'PaperBroker',
    'PaperOrder',
    'PaperFill',
    'OrderStatus',
    'OrderType',
    'FillMetrics',
    # Position Manager
    'PositionManager',
    'OptionsPosition',
    'PositionStatus',
    'PositionGreeks',
    'PortfolioState',
    # Monitor
    'PositionMonitor',
    'ExitSignal',
    'ExitReason',
    'RiskAlert',
    'MonitoringResult',
    # Reporting
    'ReportGenerator',
    'DailyReport',
    'TemplateAttribution',
    'SymbolAttribution',
    'RunCycleLog',
    'ActivityLogger',
    # Runloop
    'AutopilotRunloop',
    'CycleResult',
    'RunloopState',
    # Unified Cycle
    'UnifiedAutopilot',
    'CyclePhase',
    'CycleMetrics',
    'DecisionTrace',
    # Trade Stream
    'TradeUpdateType',
    'TradeUpdate',
    'AlpacaTradeStream',
    'TradeUpdateHandler',
    'get_trade_handler',
    # News Sentiment
    'NewsCategory',
    'SentimentBucket',
    'RecencyBucket',
    'NewsArticle',
    'SentimentScore',
    'FinnhubNewsProvider',
    'SentimentEngine',
    'get_news_provider',
    'get_sentiment_engine',
]
