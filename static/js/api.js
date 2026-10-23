export async function fetchStockAnalysis(ticker) {
  const response = await fetch('/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ticker: ticker })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || '分析データの取得に失敗しました');
  }

  return await response.json();
}

export async function fetchPortfolio() {
  const response = await fetch('/portfolio');
  if (!response.ok) {
    throw new Error('ポートフォリオの取得に失敗しました');
  }
  return await response.json();
}

export async function fetchEarningsCalendar() {
  const response = await fetch('/portfolio/earnings');
  if (!response.ok) {
    throw new Error('データの取得に失敗しました');
  }
  return await response.json();
}

export async function addPortfolioTicker(ticker) {
  const response = await fetch('/portfolio', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ticker: ticker })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || '銘柄の追加に失敗しました');
  }

  return await response.json();
}

export async function removePortfolioTicker(ticker) {
  const response = await fetch(`/portfolio/${encodeURIComponent(ticker)}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || '銘柄の削除に失敗しました');
  }

  return await response.json();
}

export async function updatePortfolio(tickers) {
  const response = await fetch('/portfolio', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ tickers: tickers })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'ポートフォリオの更新に失敗しました');
  }

  return await response.json();
}