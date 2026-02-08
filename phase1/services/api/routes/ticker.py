"""
Ticker resolution API routes.

Provides endpoints for disambiguating ticker symbols from raw user input.
Handles English word collisions (A, I, ON, IT, ARE) and separator normalization (BRK-B → BRK.B).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from ..ticker_resolver import resolve_ticker, resolve_ticker_batch, get_normalized_form

logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class TickerResolveRequest(BaseModel):
    """Request model for single ticker resolution."""
    symbol: str = Field(..., description="Raw ticker symbol input from user")


class TickerResolveBatchRequest(BaseModel):
    """Request model for batch ticker resolution."""
    symbols: List[str] = Field(..., description="List of raw ticker symbols")


class TickerResolveResponse(BaseModel):
    """Response model for ticker resolution."""
    ticker: str = Field(..., description="Canonical ticker symbol")
    normalized: str = Field(..., description="Normalized form used for lookup")
    confidence: str = Field(..., description="Confidence level: high or low")
    reason: str = Field(..., description="Explanation of resolution result")
    collision: bool = Field(..., description="True if ticker is an English word collision")
    company: Optional[str] = Field(None, description="Company name if known")


class TickerResolveNormalizeRequest(BaseModel):
    """Request model for quick normalization."""
    symbol: str = Field(..., description="Raw ticker symbol input")


class TickerResolveNormalizeResponse(BaseModel):
    """Response model for quick normalization."""
    normalized: str = Field(..., description="Normalized ticker form")


# Endpoints
@router.post("/resolve", response_model=TickerResolveResponse)
async def resolve_ticker_endpoint(req: TickerResolveRequest) -> TickerResolveResponse:
    """
    Resolve a single ticker symbol.
    
    Handles:
    - Separator normalization (BRK-B, BRK/B → BRK.B)
    - Case normalization (aapl → AAPL)
    - Whitespace trimming
    - English word collision detection (A, I, ON, IT, ARE)
    - Unknown ticker handling
    
    Returns low confidence for collision tickers and unknown tickers,
    requiring user confirmation in UX.
    """
    try:
        result = resolve_ticker(req.symbol)
        logger.info(
            "ticker_resolved",
            input=req.symbol,
            ticker=result["ticker"],
            confidence=result["confidence"],
            collision=result["collision"]
        )
        return TickerResolveResponse(**result)
    except Exception as e:
        logger.error("ticker_resolution_failed", input=req.symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"Ticker resolution failed: {str(e)}")


@router.post("/resolve/batch", response_model=List[TickerResolveResponse])
async def resolve_ticker_batch_endpoint(req: TickerResolveBatchRequest) -> List[TickerResolveResponse]:
    """
    Resolve multiple ticker symbols in batch.
    
    Same resolution rules as single endpoint, applied to each symbol.
    """
    try:
        results = resolve_ticker_batch(req.symbols)
        logger.info(
            "ticker_batch_resolved",
            count=len(req.symbols),
            low_confidence_count=sum(1 for r in results if r["confidence"] == "low")
        )
        return [TickerResolveResponse(**r) for r in results]
    except Exception as e:
        logger.error("ticker_batch_resolution_failed", count=len(req.symbols), error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch ticker resolution failed: {str(e)}")


@router.post("/normalize", response_model=TickerResolveNormalizeResponse)
async def normalize_ticker_endpoint(req: TickerResolveNormalizeRequest) -> TickerResolveNormalizeResponse:
    """
    Quick normalization endpoint for display purposes.
    
    Returns normalized form without full resolution logic.
    Useful for frontend display before user confirmation.
    """
    try:
        normalized = get_normalized_form(req.symbol)
        return TickerResolveNormalizeResponse(normalized=normalized)
    except Exception as e:
        logger.error("ticker_normalization_failed", input=req.symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"Ticker normalization failed: {str(e)}")
