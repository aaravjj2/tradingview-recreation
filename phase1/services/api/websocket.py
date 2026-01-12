"""
WebSocket handler for real-time bar streaming.
"""

import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from ..models import Bar, BarMessage, BarState


logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and subscriptions.
    
    Handles:
    - Connection lifecycle
    - Symbol/timeframe subscriptions
    - Broadcasting bar updates
    """
    
    def __init__(self):
        # Active connections: {websocket: {(symbol, timeframe), ...}}
        self._connections: Dict[WebSocket, Set[tuple]] = {}
        
        # Subscription index: {(symbol, timeframe): {websocket, ...}}
        self._subscriptions: Dict[tuple, Set[WebSocket]] = {}
        
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="ws_manager")
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = set()
        self.logger.info("ws_connected", client=id(websocket))
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
        async with self._lock:
            # Remove from subscriptions
            if websocket in self._connections:
                for key in self._connections[websocket]:
                    if key in self._subscriptions:
                        self._subscriptions[key].discard(websocket)
                        if not self._subscriptions[key]:
                            del self._subscriptions[key]
                del self._connections[websocket]
        self.logger.info("ws_disconnected", client=id(websocket))
    
    async def subscribe(
        self,
        websocket: WebSocket,
        symbol: str,
        timeframe: str,
    ) -> None:
        """Subscribe a connection to a symbol/timeframe."""
        key = (symbol.upper(), timeframe)
        async with self._lock:
            if websocket not in self._connections:
                return
            
            self._connections[websocket].add(key)
            
            if key not in self._subscriptions:
                self._subscriptions[key] = set()
            self._subscriptions[key].add(websocket)
        
        self.logger.info("ws_subscribed", symbol=symbol, timeframe=timeframe)
    
    async def unsubscribe(
        self,
        websocket: WebSocket,
        symbol: str,
        timeframe: str,
    ) -> None:
        """Unsubscribe a connection from a symbol/timeframe."""
        key = (symbol.upper(), timeframe)
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].discard(key)
            
            if key in self._subscriptions:
                self._subscriptions[key].discard(websocket)
                if not self._subscriptions[key]:
                    del self._subscriptions[key]
        
        self.logger.info("ws_unsubscribed", symbol=symbol, timeframe=timeframe)
    
    async def broadcast_bar(self, bar: Bar) -> None:
        """Broadcast bar update to all subscribed connections."""
        key = (bar.symbol, bar.timeframe)
        
        async with self._lock:
            subscribers = self._subscriptions.get(key, set()).copy()
        
        if not subscribers:
            return
        
        # Create message
        message = BarMessage.from_bar(bar)
        json_data = message.model_dump_json()
        
        # Send to all subscribers
        disconnected = []
        for websocket in subscribers:
            try:
                await websocket.send_text(json_data)
            except Exception as e:
                self.logger.warning("ws_send_error", error=str(e))
                disconnected.append(websocket)
        
        # Clean up disconnected
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def send_personal(
        self,
        websocket: WebSocket,
        message: dict,
    ) -> None:
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.warning("ws_send_error", error=str(e))
    
    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)
    
    @property
    def subscription_count(self) -> int:
        """Get number of active subscriptions."""
        return sum(len(subs) for subs in self._subscriptions.values())


# Global connection manager
manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


@router.websocket("/bars/{symbol}/{timeframe}")
async def websocket_bars(
    websocket: WebSocket,
    symbol: str,
    timeframe: str,
):
    """
    WebSocket endpoint for bar streaming.
    
    Connects and automatically subscribes to the specified symbol/timeframe.
    
    Messages sent:
    - BAR_FORMING: On each tick update
    - BAR_CONFIRMED: When bar is locked
    
    Messages received:
    - {"action": "subscribe", "symbol": "...", "timeframe": "..."}
    - {"action": "unsubscribe", "symbol": "...", "timeframe": "..."}
    - {"action": "ping"}
    """
    await manager.connect(websocket)
    
    try:
        # Auto-subscribe to requested symbol/timeframe
        await manager.subscribe(websocket, symbol, timeframe)
        
        # Send confirmation
        await manager.send_personal(websocket, {
            "type": "SUBSCRIBED",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
        })

        # Send recent history (Backfill)
        try:
            from ..persistence.repository import BarRepository
            repo = BarRepository()
            history = await repo.get_bars(symbol.upper(), timeframe, limit=1000)
            
            if history:
                # Send history in chronological order
                for bar in sorted(history, key=lambda b: b.ts_start_ms):
                    msg = BarMessage.from_bar(bar)
                    # Use HISTORICAL type (frontend handles it) or CONFIRMED
                    # msg.type = BarState.CONFIRMED.value 
                    await manager.send_personal(websocket, msg.model_dump())
                    
                logger.info("ws_sent_history", symbol=symbol, count=len(history))
        except Exception as e:
            logger.error("ws_history_send_error", error=str(e))
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                await handle_client_message(websocket, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("ws_receive_error", error=str(e))
                break
    finally:
        await manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, data: str) -> None:
    """Handle incoming client message."""
    try:
        message = json.loads(data)
        action = message.get("action", "").lower()
        
        if action == "subscribe":
            symbol = message.get("symbol", "")
            timeframe = message.get("timeframe", "")
            if symbol and timeframe:
                await manager.subscribe(websocket, symbol, timeframe)
                await manager.send_personal(websocket, {
                    "type": "SUBSCRIBED",
                    "symbol": symbol.upper(),
                    "timeframe": timeframe,
                })
        
        elif action == "unsubscribe":
            symbol = message.get("symbol", "")
            timeframe = message.get("timeframe", "")
            if symbol and timeframe:
                await manager.unsubscribe(websocket, symbol, timeframe)
                await manager.send_personal(websocket, {
                    "type": "UNSUBSCRIBED",
                    "symbol": symbol.upper(),
                    "timeframe": timeframe,
                })
        
        elif action == "ping":
            await manager.send_personal(websocket, {"type": "PONG"})
        
        else:
            await manager.send_personal(websocket, {
                "type": "ERROR",
                "message": f"Unknown action: {action}",
            })
    
    except json.JSONDecodeError:
        await manager.send_personal(websocket, {
            "type": "ERROR",
            "message": "Invalid JSON",
        })


# Callback functions to integrate with bar engine
async def on_bar_update(bar: Bar) -> None:
    """Callback for bar updates (forming state)."""
    await manager.broadcast_bar(bar)


async def on_bar_confirmed(bar: Bar) -> None:
    """Callback for bar confirmations."""
    await manager.broadcast_bar(bar)
