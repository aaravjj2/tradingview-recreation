"""
Portfolio API - REST endpoints for portfolio and positions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


router = APIRouter(tags=["Portfolio"])


# In-memory portfolio state (would connect to actual portfolio manager)
_portfolio_state = {
    "cash": 100000.0,
    "equity": 100000.0,
    "positions": [],
    "trades": [],
}


class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioResponse(BaseModel):
    cash: float
    equity: float
    total_market_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    return_pct: float
    positions: List[PositionResponse]


class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: str
    commission: float
    gross_value: float
    net_value: float


@router.get("", response_model=PortfolioResponse)
async def get_portfolio():
    """Get current portfolio state."""
    return PortfolioResponse(
        cash=_portfolio_state["cash"],
        equity=_portfolio_state["equity"],
        total_market_value=sum(p.get("market_value", 0) for p in _portfolio_state["positions"]),
        realized_pnl=0.0,
        unrealized_pnl=sum(p.get("unrealized_pnl", 0) for p in _portfolio_state["positions"]),
        total_pnl=0.0,
        return_pct=0.0,
        positions=[PositionResponse(**p) for p in _portfolio_state["positions"]],
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions():
    """Get all positions."""
    return [PositionResponse(**p) for p in _portfolio_state["positions"]]


@router.get("/positions/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str):
    """Get position for a specific symbol."""
    for p in _portfolio_state["positions"]:
        if p["symbol"].upper() == symbol.upper():
            return PositionResponse(**p)
    
    raise HTTPException(status_code=404, detail="Position not found")


class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    submitted_at: str
    filled_at: Optional[str] = None
    limit_price: Optional[float] = None
    filled_price: Optional[float] = None


# In-memory orders state
_orders_state: List[dict] = []


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(status: Optional[str] = None, limit: int = 100):
    """Get pending and recent orders."""
    orders = _orders_state
    
    if status:
        orders = [o for o in orders if o.get("status", "").lower() == status.lower()]
    
    return [OrderResponse(**o) for o in orders[-limit:]]


@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(limit: int = 100, symbol: Optional[str] = None):
    """Get trade history."""
    trades = _portfolio_state["trades"]
    
    if symbol:
        trades = [t for t in trades if t["symbol"].upper() == symbol.upper()]
    
    return [TradeResponse(**t) for t in trades[-limit:]]


@router.get("/trades/export")
async def export_trades(format: str = "json"):
    """Export trade history as JSON or CSV."""
    trades = _portfolio_state["trades"]
    
    if format == "csv":
        lines = ["id,symbol,side,quantity,price,timestamp,commission,gross_value,net_value"]
        for t in trades:
            lines.append(
                f"{t['id']},{t['symbol']},{t['side']},{t['quantity']},"
                f"{t['price']},{t['timestamp']},{t['commission']},"
                f"{t['gross_value']},{t['net_value']}"
            )
        return {"format": "csv", "data": "\n".join(lines)}
    
    return {"format": "json", "data": trades}


@router.get("/metrics")
async def get_portfolio_metrics():
    """Get portfolio performance metrics."""
    return {
        "equity": _portfolio_state["equity"],
        "cash": _portfolio_state["cash"],
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "total_return_pct": 0.0,
        "position_count": len(_portfolio_state["positions"]),
        "trade_count": len(_portfolio_state["trades"]),
    }


@router.get("/unified")
async def get_unified_portfolio():
    """
    Get unified portfolio view with positions, orders, and stats.
    Used by the frontend EnhancedPortfolioView component.
    """
    positions = _portfolio_state.get("positions", [])
    orders = _orders_state
    
    total_market_value = sum(p.get("market_value", 0) for p in positions)
    unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
    
    return {
        "positions": positions,
        "orders": orders,
        "stats": {
            "total_equity": _portfolio_state.get("equity", 0),
            "total_cash": _portfolio_state.get("cash", 0),
            "buying_power": _portfolio_state.get("cash", 0) * 2,  # Simplified
            "open_pnl": unrealized_pnl,
            "day_pnl": 0.0,  # Would need to track this
            "position_count": len(positions),
            "order_count": len(orders),
            "options_exposure": sum(
                p.get("market_value", 0) 
                for p in positions 
                if p.get("asset_type") == "option"
            ),
        }
    }
