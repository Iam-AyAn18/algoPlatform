from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.models.schemas import QuoteResponse, HistoricalResponse
from app.services.market_data import get_quote, get_historical, NIFTY50_SYMBOLS

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/quote/{symbol}", response_model=QuoteResponse)
def quote(symbol: str, exchange: str = Query("NSE", description="NSE or BSE")):
    """Get live quote for a stock."""
    try:
        return get_quote(symbol, exchange)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/quotes", response_model=List[QuoteResponse])
def bulk_quotes(
    symbols: str = Query(..., description="Comma-separated symbols e.g. RELIANCE,TCS"),
    exchange: str = Query("NSE"),
):
    """Fetch quotes for multiple symbols."""
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    results = []
    for sym in sym_list[:20]:  # cap at 20
        try:
            results.append(get_quote(sym, exchange))
        except Exception:
            pass
    return results


@router.get("/nifty50", response_model=List[QuoteResponse])
def nifty50_overview():
    """Live quotes for Nifty-50 sample stocks."""
    results = []
    for sym in NIFTY50_SYMBOLS[:10]:  # top 10 to keep latency low
        try:
            results.append(get_quote(sym, "NSE"))
        except Exception:
            pass
    return results


@router.get("/historical/{symbol}", response_model=HistoricalResponse)
def historical(
    symbol: str,
    exchange: str = Query("NSE"),
    period: str = Query("1y", description="1d,5d,1mo,3mo,6mo,1y,2y,5y"),
    interval: str = Query("1d", description="1m,5m,15m,1h,1d,1wk,1mo"),
):
    """Historical OHLCV data for charting."""
    try:
        bars = get_historical(symbol, exchange, period, interval)
        return HistoricalResponse(symbol=symbol.upper(), exchange=exchange.upper(), interval=interval, bars=bars)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
