
import asyncio
import logging
from typing import Optional

from .runloop import AutopilotRunloop
from .config import AutopilotConfig
from .data_fetcher import get_data_provider, MarketDataProvider
from .state_manager import StateManager

logger = logging.getLogger(__name__)

class AutopilotService:
    """
    Singleton service to manage the Autopilot lifecycle.
    Handles initialization, state persistence, and background loops.
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
            
        self.runloop: Optional[AutopilotRunloop] = None
        self.state_manager = StateManager()
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._initialized = True
        
    def initialize(self):
        """Initialize the autopilot runloop if not already done."""
        if self.runloop:
            return

        logger.info("Initializing Autopilot Service...")
        
        # 1. Setup Data Provider
        data_provider = get_data_provider()
        
        # 2. Setup Config
        config = AutopilotConfig()
        
        # 3. Create Runloop
        self.runloop = AutopilotRunloop(
            config=config,
            data_provider=data_provider
        )
        
        # 4. Load Persistence State
        start_fresh = not self.state_manager.load_state(
            self.runloop.positions, 
            self.runloop.broker
        )
        
        if start_fresh:
            logger.info("Started with fresh state")
        else:
            logger.info("Restored previous state")
            
    async def start_background_loop(self, interval_seconds: int = 60):
        """Start the background monitoring loop."""
        if self.is_running:
            logger.warning("Autopilot loop already running")
            return
            
        self.initialize()
        self.is_running = True
        self._loop_task = asyncio.create_task(self._run_loop(interval_seconds))
        logger.info(f"Started Autopilot background loop (interval: {interval_seconds}s)")
        
    async def stop_background_loop(self):
        """Stop the background monitoring loop."""
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        
        # Save state on stop
        if self.runloop:
            self.state_manager.save_state(self.runloop.positions, self.runloop.broker)
            
        logger.info("Stopped Autopilot background loop")
        
    async def _run_loop(self, interval: int):
        """The main background loop."""
        while self.is_running:
            try:
                if self.runloop:
                    logger.info("Running scheduled autopilot cycle...")
                    # Run synchronous cycle in a thread to avoid blocking loop
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, self.runloop.run_cycle)
                    
                    # Save state after every cycle
                    self.state_manager.save_state(
                        self.runloop.positions, 
                        self.runloop.broker
                    )
                    
            except Exception as e:
                logger.error(f"Error in autopilot background loop: {e}", exc_info=True)
                
            await asyncio.sleep(interval)

# Global singleton accessor
_service = None

def get_autopilot_service() -> AutopilotService:
    global _service
    if _service is None:
        _service = AutopilotService()
    return _service
