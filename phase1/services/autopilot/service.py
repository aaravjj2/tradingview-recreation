
import asyncio
import logging
from typing import Optional
from datetime import datetime

# Use UnifiedAutopilotEngine instead of legacy runloop
from .unified_engine import get_unified_engine, UnifiedAutopilotEngine
from .config import AutopilotConfig

logger = logging.getLogger(__name__)

class AutopilotService:
    """
    Singleton service to manage the Autopilot lifecycle.
    Now uses UnifiedAutopilotEngine as the ONLY execution path.
    
    Runs two background loops:
    1. Main cycle loop (60s) - full autopilot cycle
    2. Monitoring loop (15s) - continuous exit trigger checking
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutopilotService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.engine: Optional[UnifiedAutopilotEngine] = None
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._initialized = True
        
    def initialize(self):
        """Initialize the unified autopilot engine if not already done."""
        if self.engine:
            return

        logger.info("Initializing Autopilot Service (Unified Engine)...")
        
        # Get the singleton unified engine
        self.engine = get_unified_engine()
        logger.info("Unified Autopilot Engine initialized")
            
    async def start_background_loop(self, interval_seconds: int = 60):
        """Start the background cycle loop."""
        if self.is_running:
            logger.warning("Autopilot loop already running")
            return
            
        self.initialize()
        self.is_running = True
        self._loop_task = asyncio.create_task(self._run_loop(interval_seconds))
        logger.info(f"Started Autopilot background loop (interval: {interval_seconds}s)")
    
    async def start_monitoring_loop(self, interval_seconds: int = 15):
        """Start the continuous position monitoring loop."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring loop already running")
            return
        
        self.initialize()
        self._monitoring_task = asyncio.create_task(self._run_monitoring_loop(interval_seconds))
        logger.info(f"Started continuous monitoring loop (interval: {interval_seconds}s)")
        
    async def stop_background_loop(self):
        """Stop both background loops."""
        self.is_running = False
        
        # Stop main loop
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        
        # Stop monitoring loop
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            
        logger.info("Stopped all Autopilot background loops")
        
    async def _run_loop(self, interval: int):
        """The main background loop using UnifiedAutopilotEngine."""
        while self.is_running:
            try:
                if self.engine:
                    from .config import get_autopilot_config
                    config = get_autopilot_config()
                    if not config.continuous_run:
                        await asyncio.sleep(interval)
                        continue
                    logger.info("Running scheduled autopilot cycle (Unified Engine)...")
                    # Use the unified engine's run_cycle method (async)
                    result = await self.engine.run_cycle()
                    logger.debug(f"Cycle result: {result}")
                    
            except Exception as e:
                logger.error(f"Error in autopilot background loop: {e}", exc_info=True)
                
            await asyncio.sleep(interval)
    
    async def _run_monitoring_loop(self, interval: int):
        """
        Continuous monitoring loop - checks positions for exit triggers.
        Runs independently of the main cycle.
        """
        from .broker_position_manager import get_broker_position_manager
        from .alpaca_client import get_alpaca_client
        
        logger.info("Monitoring loop started")
        
        while self.is_running:
            try:
                if self.engine and not self.engine.kill_switch_active:
                    manager = get_broker_position_manager()
                    client = get_alpaca_client()
                    
                    if client.is_connected:
                        # Fetch current positions
                        positions = await client.list_positions()
                        
                        if positions:
                            # Evaluate all positions for exit signals
                            enriched = manager.enrich_positions(positions)
                            signals = []
                            
                            for pos in enriched:
                                pos_signals = manager.evaluate_exit_triggers(pos)
                                signals.extend(pos_signals)
                            
                            # Execute urgent exits
                            urgent = [s for s in signals if s.urgency == "critical"]
                            if urgent:
                                logger.warning(f"Found {len(urgent)} urgent exit signals!")
                                await self._execute_urgent_exits(urgent)
                            
                            # Broadcast position update via WebSocket
                            try:
                                from ..api.autopilot_websocket import get_autopilot_ws_manager
                                ws = get_autopilot_ws_manager()
                                await ws.broadcast("POSITIONS_UPDATE", {
                                    "count": len(positions),
                                    "signals": len(signals),
                                    "urgent": len(urgent),
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                            except Exception:
                                pass
                                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                
            await asyncio.sleep(interval)
    
    async def _execute_urgent_exits(self, signals):
        """Execute urgent exit orders immediately."""
        from .alpaca_client import get_alpaca_client
        
        client = get_alpaca_client()
        
        for signal in signals:
            try:
                logger.info(f"Executing urgent exit for {signal.symbol}: {signal.trigger.value}")
                # Close position via Alpaca
                await client.close_position(signal.symbol)
                
                # Broadcast exit event
                try:
                    from ..api.autopilot_websocket import get_autopilot_ws_manager
                    ws = get_autopilot_ws_manager()
                    await ws.broadcast("EXIT_EXECUTED", {
                        "symbol": signal.symbol,
                        "trigger": signal.trigger.value,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception:
                    pass
                    
            except Exception as e:
                logger.error(f"Failed to execute exit for {signal.symbol}: {e}")
    
    def get_status(self) -> dict:
        """Get current autopilot status from unified engine."""
        if not self.engine:
            return {"status": "not_initialized", "running": False}
        
        return {
            "status": "running" if self.is_running else "stopped",
            "running": self.is_running,
            "engine": "unified",
            "kill_switch": self.engine.kill_switch_active,
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
        }

# Global singleton accessor
_service = None

def get_autopilot_service() -> AutopilotService:
    global _service
    if _service is None:
        _service = AutopilotService()
    return _service

