import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.services.cache import SimpleTTLCache

load_dotenv()
client = Groq()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
PROMPT_FILE_PATH = Path(__file__).resolve().parent / "prompts" / "stock_analysis.md"

# LLMの分析結果を1時間（3600秒）キャッシュ
_analysis_cache = SimpleTTLCache(default_ttl=3600, maxsize=64)

def _clean_closing_remarks(text: str) -> str:
  """テキスト末尾（最後の1〜3行）に対話的な締めくくり（質問促進等）がある場合のみ除去する。本文内の表現やテーブルは一切干渉しない。"""
  lines = text.rstrip().split('\n')
  closing_keywords = [
    "ご質問", "ご不明な点", "お知らせください", "お尋ねください", 
    "追加データがあれば", "追加の分析", "参考になれば幸い", "お気軽に"
  ]
  while lines:
    last_line = lines[-1].strip()
    if not last_line:
      lines.pop()
      continue
    # 最後の行が挨拶・問い合わせ促進かつ短い文の場合のみ削除
    if any(kw in last_line for kw in closing_keywords) and len(last_line) < 80:
      lines.pop()
    else:
      break
  return '\n'.join(lines).strip()

def generate_financial_analysis(ticker_symbol: str, finance_data: dict) -> str:
  cached_result = _analysis_cache.get(ticker_symbol)
  if cached_result is not None:
    return cached_result

  template = PROMPT_FILE_PATH.read_text(encoding="utf-8")

  prompt = template.format(
    ticker=ticker_symbol,
    company_name=finance_data["company_name"],
    sector=finance_data["sector"],
    market_cap=finance_data["market_cap"],
    pe_ratio=finance_data["pe_ratio"],
    roe=finance_data["roe"],
    dividend_yield=finance_data["dividend_yield"],
    operating_cashflow=finance_data["operating_cashflow"],
    free_cashflow=finance_data["free_cashflow"],
    past_earnings_date=finance_data["past_earnings_date"],
    next_earnings_date=finance_data["next_earnings_date"],
  )

  chat_completion = client.chat.completions.create(
    messages=[
      {
        "role": "user",
        "content": prompt,
      }
    ],
    model=DEFAULT_MODEL,
  )
  
  raw_result = chat_completion.choices[0].message.content or ""
  result = _clean_closing_remarks(raw_result)
  _analysis_cache.set(ticker_symbol, result)
  return result