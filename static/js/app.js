import {
  fetchStockAnalysis,
  fetchEarningsCalendar,
  fetchPortfolio,
  addPortfolioTicker,
  removePortfolioTicker,
  updatePortfolio,
} from './api.js';

let isCalendarLoaded = false;

function formatLargeNumber(val) {
  if (val === undefined || val === null || val === 'N/A' || isNaN(Number(val))) {
    return 'N/A';
  }
  const num = Number(val);
  const abs = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  
  if (abs >= 1e12) {
    return `${sign}${(abs / 1e12).toFixed(2)} 兆`;
  } else if (abs >= 1e9) {
    return `${sign}${(abs / 1e9).toFixed(2)} B`;
  } else if (abs >= 1e6) {
    return `${sign}${(abs / 1e6).toFixed(2)} M`;
  }
  return num.toLocaleString();
}

async function loadEarningsCalendar(force = false) {
  const tbody = document.getElementById('earnings-tbody');
  if (force) {
    tbody.innerHTML = '<tr><td colspan="4" class="loading">更新中...</td></tr>';
  }

  try {
    const data = await fetchEarningsCalendar();
    tbody.innerHTML = '';
    
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="loading">登録されている銘柄がありません</td></tr>';
      return;
    }

    data.forEach(item => {
      const tr = document.createElement('tr');
      const safeTicker = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(item.ticker) : item.ticker;
      const safeName = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(item.company_name) : item.company_name;
      const safeDate = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(item.next_earnings_date) : item.next_earnings_date;
      
      tr.innerHTML = `
        <td><a href="#" class="ticker-link" data-ticker="${safeTicker}">${safeTicker}</a></td>
        <td>${safeName}</td>
        <td>${safeDate}</td>
        <td class="action-cell">
          <button type="button" class="delete-ticker-btn" data-ticker="${safeTicker}" title="削除">削除</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // ティッカーリンクのクリックリスナー
    tbody.querySelectorAll('.ticker-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const ticker = e.currentTarget.getAttribute('data-ticker');
        const searchInput = document.getElementById('tickerInput'); 
        if (searchInput) {
          searchInput.value = ticker;
          searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
          searchInput.focus();
        }
      });
    });

    // 削除ボタンのクリックリスナー
    tbody.querySelectorAll('.delete-ticker-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const ticker = e.currentTarget.getAttribute('data-ticker');
        if (!confirm(`銘柄「${ticker}」をポートフォリオから削除しますか？`)) {
          return;
        }
        try {
          btn.disabled = true;
          btn.textContent = '...';
          await removePortfolioTicker(ticker);
          await loadEarningsCalendar(true);
        } catch (err) {
          alert(err.message || '削除に失敗しました');
          btn.disabled = false;
          btn.textContent = '削除';
        }
      });
    });

    isCalendarLoaded = true;
  } catch (error) {
    console.error('Failed to load earnings calendar:', error);
    tbody.innerHTML = '<tr><td colspan="4" class="loading" style="color: #ef4444;">決算データの取得に失敗しました</td></tr>';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // 1. カレンダーウィジェット要素
  const toggleBtn = document.getElementById('toggle-earnings-btn');
  const container = document.getElementById('earnings-container');
  const newTickerInput = document.getElementById('newTickerInput');
  const addTickerBtn = document.getElementById('addTickerBtn');
  
  // 2. モーダル要素
  const managePortfolioBtn = document.getElementById('managePortfolioBtn');
  const portfolioModal = document.getElementById('portfolioModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const savePortfolioBtn = document.getElementById('savePortfolioBtn');
  const portfolioTextarea = document.getElementById('portfolioTextarea');

  // 3. 企業分析要素
  const analyzeBtn = document.getElementById('analyzeBtn');
  const tickerInput = document.getElementById('tickerInput');
  const loadingEl = document.getElementById('loading');
  const resultEl = document.getElementById('resultContainer');

  // --- カレンダー開閉トグル ---
  if (toggleBtn && container) {
    toggleBtn.addEventListener('click', async () => {
      const isCollapsed = container.classList.contains('collapsed');
      if (isCollapsed) {
        container.classList.remove('collapsed');
        toggleBtn.textContent = '非表示';
        if (!isCalendarLoaded) {
          await loadEarningsCalendar();
        }
      } else {
        container.classList.add('collapsed');
        toggleBtn.textContent = '表示する';
      }
    });
  }

  // --- クイック銘柄追加 ---
  const handleAddTicker = async () => {
    if (!newTickerInput || !addTickerBtn) return;
    const ticker = newTickerInput.value.trim().toUpperCase();
    if (!ticker) return;

    addTickerBtn.disabled = true;
    addTickerBtn.textContent = '追加中...';

    try {
      await addPortfolioTicker(ticker);
      newTickerInput.value = '';
      await loadEarningsCalendar(true);
    } catch (err) {
      alert(err.message || '銘柄の追加に失敗しました');
    } finally {
      addTickerBtn.disabled = false;
      addTickerBtn.textContent = '+ 追加';
    }
  };

  if (addTickerBtn) {
    addTickerBtn.addEventListener('click', handleAddTicker);
  }
  if (newTickerInput) {
    newTickerInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        handleAddTicker();
      }
    });
  }

  // --- ポートフォリオ一括編集モーダル ---
  const openModal = async () => {
    if (!portfolioModal || !portfolioTextarea) return;
    portfolioModal.classList.remove('hidden');
    portfolioTextarea.value = '読み込み中...';
    try {
      const res = await fetchPortfolio();
      portfolioTextarea.value = (res.tickers || []).join('\n');
      portfolioTextarea.focus();
    } catch (err) {
      alert(err.message || 'ポートフォリオの取得に失敗しました');
      portfolioTextarea.value = '';
    }
  };

  const closeModal = () => {
    if (portfolioModal) {
      portfolioModal.classList.add('hidden');
    }
  };

  if (managePortfolioBtn) {
    managePortfolioBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openModal();
    });
  }

  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);
  if (portfolioModal) {
    portfolioModal.addEventListener('click', (e) => {
      if (e.target === portfolioModal) {
        closeModal();
      }
    });
  }

  if (savePortfolioBtn) {
    savePortfolioBtn.addEventListener('click', async () => {
      if (!portfolioTextarea) return;
      const text = portfolioTextarea.value;
      const rawTickers = text.split('\n').map(t => t.trim()).filter(Boolean);
      
      savePortfolioBtn.disabled = true;
      savePortfolioBtn.textContent = '保存中...';

      try {
        await updatePortfolio(rawTickers);
        closeModal();
        if (container && !container.classList.contains('collapsed')) {
          await loadEarningsCalendar(true);
        } else {
          isCalendarLoaded = false;
        }
      } catch (err) {
        alert(err.message || '保存に失敗しました');
      } finally {
        savePortfolioBtn.disabled = false;
        savePortfolioBtn.textContent = '保存して反映';
      }
    });
  }

  // --- 企業分析実行 ---
  const executeAnalysis = async () => {
    if (!tickerInput || !loadingEl || !resultEl) return;
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;

    loadingEl.classList.remove('hidden');
    resultEl.classList.add('hidden');

    try {
      const data = await fetchStockAnalysis(ticker);

      const compEl = document.getElementById('companyName');
      if (compEl) compEl.textContent = `${data.company_name} (${data.ticker})`;
      
      const secEl = document.getElementById('sectorBadge');
      if (secEl) secEl.textContent = `セクター: ${data.sector || 'N/A'}`;
      
      const pe = data.pe_ratio !== 'N/A' && !isNaN(Number(data.pe_ratio)) ? `${Number(data.pe_ratio).toFixed(1)} 倍` : data.pe_ratio;
      const peEl = document.getElementById('peRatio');
      if (peEl) peEl.textContent = pe;

      const roeEl = document.getElementById('roe');
      if (roeEl) roeEl.textContent = data.roe || 'N/A';

      const mcEl = document.getElementById('marketCap');
      if (mcEl) mcEl.textContent = formatLargeNumber(data.market_cap);

      const dyEl = document.getElementById('dividendYield');
      if (dyEl) dyEl.textContent = data.dividend_yield || 'N/A';

      const opEl = document.getElementById('operatingCashflow');
      if (opEl) opEl.textContent = formatLargeNumber(data.operating_cashflow);

      const fcfEl = document.getElementById('freeCashflow');
      if (fcfEl) fcfEl.textContent = formatLargeNumber(data.free_cashflow);

      const peDateEl = document.getElementById('pastEarningsDate');
      if (peDateEl) peDateEl.textContent = data.past_earnings_date || 'N/A';

      const neDateEl = document.getElementById('nextEarningsDate');
      if (neDateEl) neDateEl.textContent = data.next_earnings_date || 'N/A';
      
      const rawHtml = marked.parse(data.analysis);
      const cleanHtml = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
      const anaEl = document.getElementById('analysisText');
      if (anaEl) anaEl.innerHTML = cleanHtml;

      resultEl.classList.remove('hidden');
    } catch (error) {
      alert(error.message || '分析に失敗しました');
    } finally {
      loadingEl.classList.add('hidden');
    }
  };

  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', executeAnalysis);
  }

  if (tickerInput) {
    tickerInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        executeAnalysis();
      }
    });
  }
});