from fastapi import APIRouter, HTTPException
from app.models.schemas import BacktestRequest, BacktestResult
from app.services.backtest_service import run_backtest

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.post("/", response_model=BacktestResult)
def backtest(req: BacktestRequest):
    """Run a strategy backtest on historical data."""
    try:
        return run_backtest(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
