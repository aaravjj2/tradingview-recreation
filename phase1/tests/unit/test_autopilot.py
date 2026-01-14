"""
Unit tests for Autopilot Module
"""
import pytest
from datetime import datetime, timezone

from services.autopilot import (
    AutopilotConfig, 
    AutopilotMode,
    RiskLimits, 
    StrategyTemplate,
    StrategyConstraints,
    UniverseManager,
    UniverseSymbol,
    TradeValidator,
    ValidationResult,
    RejectionCode,
    PaperBroker,
    PaperOrder,
    OrderType,
    PositionManager,
    OptionsPosition,
    PositionMonitor,
    ExitReason,
    ReportGenerator,
    ActivityLogger,
    AutopilotRunloop,
    CycleResult,
)


class TestAutopilotConfig:
    """Tests for AutopilotConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = AutopilotConfig()
        
        assert config.paper_equity == 1000.0
        assert config.mode == AutopilotMode.PAPER
        assert len(config.allowed_strategies) == 5
        
    def test_risk_limits_defaults(self):
        """Test default risk limits"""
        limits = RiskLimits()
        
        assert limits.max_risk_per_trade == 50.0
        assert limits.max_total_risk == 400.0
        assert limits.max_daily_loss == 30.0
        assert limits.max_open_positions == 10
        
    def test_config_universe(self):
        """Test universe configuration"""
        config = AutopilotConfig()
        
        assert "AAPL" in config.universe
        assert "SPY" in config.universe
        assert len(config.universe) == 18


class TestUniverseManager:
    """Tests for UniverseManager"""
    
    def test_initialize_universe(self):
        """Test universe initialization"""
        allowed = ["AAPL", "MSFT", "GOOGL"]
        manager = UniverseManager(allowed_symbols=allowed)
        manager.initialize(["AAPL", "MSFT", "GOOGL", "UNKNOWN"])
        
        # Only allowed symbols should be in universe
        assert "AAPL" in manager.symbols
        assert "MSFT" in manager.symbols
        assert "GOOGL" in manager.symbols
        assert "UNKNOWN" not in manager.symbols
        
    def test_get_all_symbols(self):
        """Test getting all symbols"""
        allowed = ["AAPL", "MSFT"]
        manager = UniverseManager(allowed_symbols=allowed)
        manager.initialize(["AAPL", "MSFT"])
        
        symbols = manager.get_all_symbols()
        assert len(symbols) == 2


class TestActivityLogger:
    """Tests for ActivityLogger"""
    
    def test_log_entry(self):
        """Test logging an entry"""
        logger = ActivityLogger()
        
        logger.log(
            event_type="test_event",
            message="Test message",
            level="info",
        )
        
        entries = logger.get_entries(limit=10)
        assert len(entries) > 0
        assert entries[-1]["event_type"] == "test_event"
        
    def test_log_with_details(self):
        """Test logging with details"""
        logger = ActivityLogger()
        
        logger.log(
            event_type="trade",
            message="Trade executed",
            level="info",
            details={"price": 150.0, "quantity": 1},
        )
        
        entries = logger.get_entries(limit=10)
        assert entries[-1]["details"]["price"] == 150.0


class TestAutopilotRunloop:
    """Tests for AutopilotRunloop"""
    
    def test_runloop_creation(self):
        """Test runloop can be created"""
        config = AutopilotConfig()
        # Use allowed_symbols list from config
        runloop = AutopilotRunloop(config)
        
        assert runloop is not None
        assert runloop.config == config
        
    def test_kill_switch(self):
        """Test kill switch activation"""
        config = AutopilotConfig()
        runloop = AutopilotRunloop(config)
        
        assert runloop.validator.kill_switch_active is False
        
        runloop.activate_kill_switch()
        assert runloop.validator.kill_switch_active is True
        
        runloop.deactivate_kill_switch()
        assert runloop.validator.kill_switch_active is False
        
    def test_pause_resume(self):
        """Test pause and resume"""
        from services.autopilot.runloop import RunloopState
        
        config = AutopilotConfig()
        runloop = AutopilotRunloop(config)
        
        runloop.pause()
        assert runloop.state == RunloopState.PAUSED
        
        runloop.resume()
        assert runloop.state == RunloopState.IDLE


class TestStrategyTemplates:
    """Tests for strategy template definitions"""
    
    def test_all_templates_defined(self):
        """Test all strategy templates are defined"""
        templates = list(StrategyTemplate)
        
        assert StrategyTemplate.PUT_CREDIT_SPREAD in templates
        assert StrategyTemplate.CALL_CREDIT_SPREAD in templates
        assert StrategyTemplate.IRON_CONDOR in templates
        assert StrategyTemplate.CALL_DEBIT_SPREAD in templates
        assert StrategyTemplate.PUT_DEBIT_SPREAD in templates


class TestStrategyConstraints:
    """Tests for strategy constraints"""
    
    def test_default_constraints(self):
        """Test default strategy constraints"""
        constraints = StrategyConstraints()
        
        assert constraints.min_dte == 14
        assert constraints.max_dte == 45
        assert constraints.min_short_delta == 0.15
        assert constraints.max_short_delta == 0.35
        assert constraints.take_profit_pct == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
