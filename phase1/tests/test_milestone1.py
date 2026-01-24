"""
Milestone 1 Integration Test

Tests the full open→monitor→exit lifecycle:
1. State machine transitions correctly
2. Exit monitor triggers stops with smoothing
3. Execution ladder retries work
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock

# Add path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from services.autopilot.state_machine import AgentStateMachine, AgentState, AgentAction
from services.autopilot.exit_monitor import ExitMonitor, ExitTrigger, StopSmoother
from services.autopilot.execution_ladder import LimitOrderLadder, ExecutionState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("M1Test")

def test_state_machine():
    logger.info("--- Testing State Machine ---")
    
    sm = AgentStateMachine(cooldown_seconds=60)
    
    # Initial state should be TOKEN_TRADE_PENDING
    assert sm.state == AgentState.TOKEN_TRADE_PENDING, f"Expected TOKEN_TRADE_PENDING, got {sm.state}"
    logger.info(f"✅ Initial state: {sm.state}")
    
    # Allowed actions
    actions = sm.get_allowed_actions()
    assert AgentAction.OPEN_POSITION in actions
    assert AgentAction.PLACE_TOKEN_TRADE in actions
    logger.info(f"✅ Allowed actions: {actions}")
    
    # Open position
    sm.on_position_opened("pos-001", is_token=False)
    assert sm.state == AgentState.IN_TRADE
    logger.info(f"✅ After open: {sm.state}")
    
    # Only exit allowed
    actions = sm.get_allowed_actions()
    assert AgentAction.EXIT_POSITION in actions
    assert AgentAction.OPEN_POSITION not in actions
    logger.info(f"✅ Actions in trade: {actions}")
    
    # Initiate exit
    sm.on_exit_initiated("pos-001", "stop_loss")
    assert sm.state == AgentState.EXITING
    logger.info(f"✅ After exit init: {sm.state}")
    
    # Close position
    sm.on_position_closed("pos-001", pnl=-25.0)
    assert sm.state == AgentState.COOLDOWN
    logger.info(f"✅ After close: {sm.state}")
    
    # Check transition history
    history = sm.get_transition_history()
    assert len(history) >= 3
    logger.info(f"✅ Transition history has {len(history)} entries")

def test_stop_smoother():
    logger.info("--- Testing Stop Smoother ---")
    
    smoother = StopSmoother(window_size=3, required_breaches=2)
    
    # First sample breached - not confirmed
    assert smoother.record_sample(True) == False
    logger.info("✅ 1 breach: not confirmed")
    
    # Second sample not breached - still not confirmed
    assert smoother.record_sample(False) == False
    logger.info("✅ 1/2: not confirmed")
    
    # Third sample breached - NOW confirmed (2-of-3)
    assert smoother.record_sample(True) == True
    logger.info("✅ 2/3 breaches: CONFIRMED")
    
    # Reset and test non-confirmation
    smoother.reset()
    smoother.record_sample(True)
    smoother.record_sample(False)
    assert smoother.record_sample(False) == False  # Only 1-of-3
    logger.info("✅ 1/3 breaches: not confirmed")

def test_exit_monitor():
    logger.info("--- Testing Exit Monitor ---")
    
    monitor = ExitMonitor()
    now = datetime.now(timezone.utc)
    
    # Register position
    pos = monitor.register_position(
        position_id="pos-002",
        entry_price=1.00,
        entry_time=now,
        is_debit=True,
        template_type="debit"
    )
    
    # Sample 1: 10% loss - no trigger
    signals = monitor.check_position("pos-002", 0.90)
    triggered = [s for s in signals if s.triggered]
    assert len(triggered) == 0
    logger.info("✅ -10%: no triggers")
    
    # Sample 2: 22% loss - soft stop breached once
    signals = monitor.check_position("pos-002", 0.78)
    soft_triggers = [s for s in signals if s.trigger == ExitTrigger.SOFT_STOP and s.triggered]
    assert len(soft_triggers) == 0  # Not confirmed yet (need 2-of-3)
    logger.info("✅ -22%: soft stop breached but not confirmed (1/3)")
    
    # Sample 3: Recovery to 15% loss
    signals = monitor.check_position("pos-002", 0.85)
    logger.info("✅ -15%: recovery, still 1-of-3")
    
    # Sample 4: 25% loss again
    signals = monitor.check_position("pos-002", 0.75)
    soft_triggers = [s for s in signals if s.trigger == ExitTrigger.SOFT_STOP and s.triggered]
    # Now we have 2-of-3 breaches
    assert len(soft_triggers) == 1
    logger.info("✅ -25%: SOFT STOP CONFIRMED (2-of-3)")
    
    # Test hard stop (immediate)
    monitor.register_position("pos-003", 1.00, now, True, "debit")
    signals = monitor.check_position("pos-003", 0.55)  # 45% loss
    hard_triggers = [s for s in signals if s.trigger == ExitTrigger.HARD_STOP and s.triggered]
    assert len(hard_triggers) == 1
    logger.info("✅ -45%: HARD STOP (immediate)")

async def test_execution_ladder():
    logger.info("--- Testing Execution Ladder ---")
    
    ladder = LimitOrderLadder(
        step_pct=0.15,
        max_improve_pct=0.45,
        max_attempts=3,
        attempt_interval_sec=0.1,  # Fast for testing
    )
    
    # Mock functions
    order_counter = [0]
    
    async def mock_submit(symbol, side, qty, limit_price):
        order_counter[0] += 1
        logger.info(f"  Mock submit: {side} {qty}x {symbol} @ {limit_price:.2f}")
        return f"order-{order_counter[0]}"
    
    async def mock_check_fill(order_id):
        # Simulate fill on 2nd attempt
        if "2" in order_id:
            return ("filled", 1, 2.15)
        return ("open", 0, None)
    
    async def mock_cancel(order_id):
        logger.info(f"  Mock cancel: {order_id}")
        return True
    
    result = await ladder.execute(
        symbol="TEST",
        side="buy",
        qty=1,
        bid=2.00,
        ask=2.20,
        submit_fn=mock_submit,
        check_fn=mock_check_fill,
        cancel_fn=mock_cancel,
    )
    
    assert result.success
    assert result.state == ExecutionState.FILLED
    assert result.total_attempts == 2
    logger.info(f"✅ Execution ladder: {result.state} after {result.total_attempts} attempts")
    logger.info(f"   Fill price: ${result.avg_fill_price:.2f}, Slippage: {result.slippage_bps:.1f} bps")

if __name__ == "__main__":
    test_state_machine()
    test_stop_smoother()
    test_exit_monitor()
    asyncio.run(test_execution_ladder())
    
    logger.info("\n🎉 All Milestone 1 tests passed!")
