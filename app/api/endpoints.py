from fastapi import APIRouter, HTTPException
from app.schemas.stock import (
  EarningsCalendarItem,
  StockRequest,
  StockAnalysisResponse,
  PortfolioAddRequest,
  PortfolioUpdateRequest,
  PortfolioResponse,
)
from app.services.finance import (
  get_earnings_calendar,
  get_stock_data,
  load_portfolio,
  save_portfolio,
  add_portfolio_ticker,
  remove_portfolio_ticker,
)
from app.services.llm import generate_financial_analysis

router = APIRouter()

@router.post("/analyze", response_model=StockAnalysisResponse)
def analyze_stock(req: StockRequest):
  ticker_symbol = req.ticker.strip().upper()
  try:
    finance_data = get_stock_data(ticker_symbol)
    analysis_result = generate_financial_analysis(ticker_symbol, finance_data)
    
    return StockAnalysisResponse(
      ticker=ticker_symbol,
      company_name=finance_data["company_name"],
      sector=finance_data["sector"],
      pe_ratio=finance_data["pe_ratio"],
      market_cap=finance_data["market_cap"],
      roe=finance_data["roe"],
      dividend_yield=finance_data["dividend_yield"],
      operating_cashflow=finance_data["operating_cashflow"],
      free_cashflow=finance_data["free_cashflow"],
      past_earnings_date=finance_data["past_earnings_date"],
      next_earnings_date=finance_data["next_earnings_date"],
      analysis=analysis_result
    )
  except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))

@router.get("/portfolio/earnings", response_model=list[EarningsCalendarItem])
def get_portfolio_earnings():
  try:
    calendar_data = get_earnings_calendar()
    return calendar_data
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio():
  try:
    return PortfolioResponse(tickers=load_portfolio())
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/portfolio", response_model=PortfolioResponse)
def add_ticker_to_portfolio(req: PortfolioAddRequest):
  try:
    updated = add_portfolio_ticker(req.ticker)
    return PortfolioResponse(tickers=updated)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.delete("/portfolio/{ticker}", response_model=PortfolioResponse)
def remove_ticker_from_portfolio(ticker: str):
  try:
    updated = remove_portfolio_ticker(ticker)
    return PortfolioResponse(tickers=updated)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.put("/portfolio", response_model=PortfolioResponse)
def update_portfolio(req: PortfolioUpdateRequest):
  try:
    updated = save_portfolio(req.tickers)
    return PortfolioResponse(tickers=updated)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))