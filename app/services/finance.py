from datetime import datetime
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# import yfinance as yf  # Deprecated, using unified data provider
from data_provider import get_symbol_earnings, get_earnings_calendar as provider_earnings_calendar
import pandas as pd

from app.services.cache import ttl_cache

logger = logging.getLogger(__name__)

PORTFOLIO_PATH = Path(__file__).resolve().parent / "json" / "portfolio.json"

def normalize_ticker(symbol: str) -> str:
  """ティッカーシンボルの大文字化と、4桁数字への.T補正を行う。"""
  cleaned = symbol.strip().upper()
  if cleaned.isdigit() and len(cleaned) == 4:
    cleaned = f"{cleaned}.T"
  return cleaned

def load_portfolio() -> list[str]:
  if not PORTFOLIO_PATH.exists():
    return []
  with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    return data.get("tickers", [])

def save_portfolio(tickers: list[str]) -> list[str]:
  """ポートフォリオを保存し、決算カレンダーのキャッシュを無効化する。"""
  unique_tickers = []
  for t in tickers:
    norm = normalize_ticker(t)
    if norm and norm not in unique_tickers:
      unique_tickers.append(norm)

  PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
  with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
    json.dump({"tickers": unique_tickers}, f, indent=2, ensure_ascii=False)
  
  if hasattr(get_earnings_calendar, "cache"):
    get_earnings_calendar.cache.clear()
    
  return unique_tickers

def add_portfolio_ticker(ticker_symbol: str) -> list[str]:
  norm = normalize_ticker(ticker_symbol)
  if not norm:
    raise ValueError("ティッカーシンボルを入力してください")
  tickers = load_portfolio()
  if norm not in tickers:
    tickers.append(norm)
    save_portfolio(tickers)
  return tickers

def remove_portfolio_ticker(ticker_symbol: str) -> list[str]:
  norm = normalize_ticker(ticker_symbol)
  tickers = load_portfolio()
  new_tickers = [t for t in tickers if t != norm]
  save_portfolio(new_tickers)
  return new_tickers

def _fetch_single_calendar(ticker_symbol: str) -> dict:
    """Fetch earnings calendar for a single ticker using the unified data provider.
    Returns a dict compatible with the previous yfinance based implementation.
    """
    try:
        # Retrieve earnings data via the provider
        data = get_symbol_earnings(ticker_symbol)
        # Determine next earnings date from provider response
        next_date = "N/A"
        # Alpha Vantage format
        if isinstance(data, dict) and "quarterlyEarnings" in data:
            try:
                recent = data["quarterlyEarnings"][-1]
                next_date = recent.get("reportedDate", "N/A")
            except Exception:
                pass
        # Finnhub format
        if isinstance(data, dict) and "earningsCalendar" in data:
            try:
                from datetime import datetime
                today = datetime.utcnow().date()
                future = [e for e in data["earningsCalendar"] if e.get("date")]
                dates = [datetime.fromisoformat(e["date"]).date() for e in future]
                future_dates = [d for d in dates if d >= today]
                if future_dates:
                    next_date = min(future_dates).isoformat()
            except Exception:
                pass
        company_name = data.get("symbol", ticker_symbol)
        return {
            "ticker": ticker_symbol,
            "company_name": company_name,
            "next_earnings_date": next_date,
        }
    except Exception as e:
        logger.warning(f"Error fetching earnings for {ticker_symbol}: {e}")
        return {
            "ticker": ticker_symbol,
            "company_name": "Error fetching data",
            "next_earnings_date": "N/A",
        }

@ttl_cache(ttl=1800)
def get_earnings_calendar() -> list[dict]:
  """保有銘柄の決算スケジュールを並列で取得（30分間キャッシュ）"""
  tickers = load_portfolio()
  if not tickers:
    return []

  with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(_fetch_single_calendar, tickers))

  results.sort(key=lambda x: x["next_earnings_date"] if x["next_earnings_date"] != "N/A" else "9999-12-31")
  return results

@ttl_cache(ttl=1800)
def get_stock_data(ticker_symbol: str) -> dict:
  cleaned_ticker = normalize_ticker(ticker_symbol)
  stock = yf.Ticker(cleaned_ticker)
  info = stock.info
  
  company_name = info.get("shortName", ticker_symbol)
  sector = info.get("sector", "N/A")
  pe_ratio = info.get("trailingPE", "N/A")
  if pe_ratio is None:
    pe_ratio = "N/A"
  market_cap = info.get("marketCap", "N/A")
  if market_cap is None:
    market_cap = "N/A"

  # 主要な指標の取得（取得できない場合は "N/A" や適切なデフォルト値）
  roe = info.get("returnOnEquity", "N/A")
  if isinstance(roe, (int, float)):
    roe = f"{roe * 100:.2f}%"  # パーセンテージ表記に整形
  else:
    roe = "N/A"
      
  dividend_yield = info.get("dividendYield", "N/A")
  if isinstance(dividend_yield, (int, float)):
    dividend_yield = f"{dividend_yield:.2f}%"
  else:
    dividend_yield = "N/A"
      
  operating_cashflow = info.get("operatingCashflow", "N/A")
  if operating_cashflow is None:
    operating_cashflow = "N/A"
  free_cashflow = info.get("freeCashflow", "N/A")
  if free_cashflow is None:
    free_cashflow = "N/A"
  
  # 決算日（過去・次回）の取得
  past_earnings_date_str = "N/A"
  next_earnings_date_str = "N/A"

  try:
    earnings_dates = stock.earnings_dates
    if earnings_dates is not None and not earnings_dates.empty:
      today = pd.Timestamp.today(tz=earnings_dates.index.tz) if earnings_dates.index.tz is not None else pd.Timestamp.today()
        
      # 過去の直近決算日
      past_earnings = earnings_dates[earnings_dates.index <= today]
      if not past_earnings.empty:
        latest_past = past_earnings.index[0]
        past_earnings_date_str = latest_past.strftime('%Y-%m-%d') if isinstance(latest_past, pd.Timestamp) else str(latest_past)
          
      # 次回の決算発表予定日（今日より後の日付から、最も近いもの＝末尾側）
      future_earnings = earnings_dates[earnings_dates.index > today]
      if not future_earnings.empty:
        # earnings_dates は通常降順なので、今日より後の中で最も古い（直近の）未来日を取得
        earliest_future = future_earnings.index[-1]
        next_earnings_date_str = earliest_future.strftime('%Y-%m-%d') if isinstance(earliest_future, pd.Timestamp) else str(earliest_future)
  except Exception:
    pass

  return {
    "company_name": company_name,
    "sector": sector,
    "pe_ratio": pe_ratio,
    "market_cap": market_cap,
    "roe": roe,
    "dividend_yield": dividend_yield,
    "operating_cashflow": operating_cashflow,
    "free_cashflow": free_cashflow,
    "past_earnings_date": past_earnings_date_str,
    "next_earnings_date": next_earnings_date_str,
  }
