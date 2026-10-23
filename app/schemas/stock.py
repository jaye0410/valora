from typing import Union
from pydantic import BaseModel

class StockRequest(BaseModel):
  ticker: str

class StockAnalysisResponse(BaseModel):
  ticker: str
  company_name: str
  sector: str
  pe_ratio: Union[float, str]
  market_cap: Union[int, float, str]
  roe: str
  dividend_yield: str
  operating_cashflow: Union[int, float, str]
  free_cashflow: Union[int, float, str]
  past_earnings_date: str
  next_earnings_date: str
  analysis: str

class EarningsCalendarItem(BaseModel):
  ticker: str
  company_name: str
  next_earnings_date: str

class PortfolioAddRequest(BaseModel):
  ticker: str

class PortfolioUpdateRequest(BaseModel):
  tickers: list[str]

class PortfolioResponse(BaseModel):
  tickers: list[str]