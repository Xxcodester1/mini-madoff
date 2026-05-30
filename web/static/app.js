let chart = null;
let logIndex = 0;
let botRunning = false;

// ── Init ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initChart();
  refreshPortfolio();
  setInterval(refreshPortfolio, 30000);
  setInterval(pollLog, 2000);
});

// ── Portfolio ────────────────────────────────────────────
async function refreshPortfolio() {
  try {
    const res = await fetch('/api/portfolio');
    const data = await res.json();
    if (data.error) return;

    updateStats(data.account, data.positions);
    updatePositions(data.positions);
    updateChart(data.history);

    document.getElementById('last-updated').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error('Portfolio fetch error:', e);
  }
}

function updateStats(acct, positions) {
  const pv       = acct.portfolio_value;
  const cash     = acct.cash;
  const invested = pv - cash;
  const pl       = positions.reduce((s, p) => s + p.unrealized_pl, 0);

  setStatCard('stat-portfolio', fmt(pv),      false);
  setStatCard('stat-cash',      fmt(cash),    false);
  setStatCard('stat-invested',  fmt(invested),false);
  setStatCard('stat-pl',        fmtPl(pl),    pl >= 0 ? 'positive' : 'negative');
}

function setStatCard(id, value, cls) {
  const el = document.getElementById(id);
  el.textContent = value;
  el.className = 'stat-value' + (cls ? ' ' + cls : '');
}

function fmt(n) {
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPl(n) {
  const sign = n >= 0 ? '+' : '';
  return sign + fmt(n);
}

// ── Positions Table ──────────────────────────────────────
function updatePositions(positions) {
  const tbody = document.getElementById('positions-tbody');
  const badge = document.getElementById('positions-badge');
  badge.textContent = positions.length + ' positions';

  if (!positions.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="no-positions">No open positions</td></tr>';
    return;
  }

  tbody.innerHTML = positions.map(p => {
    const pl    = p.unrealized_pl;
    const pct   = (p.unrealized_plpc * 100).toFixed(2);
    const cls   = pl >= 0 ? 'positive' : 'negative';
    const sign  = pl >= 0 ? '+' : '';
    const arrow = pl >= 0 ? '▲' : '▼';
    return `
      <tr>
        <td class="symbol">${p.symbol}</td>
        <td>${Math.round(p.qty)}</td>
        <td>${fmt(p.avg_entry_price)}</td>
        <td>${fmt(p.current_price)}</td>
        <td>${fmt(p.market_value)}</td>
        <td class="${cls}">${sign}${fmt(pl)}</td>
        <td class="${cls}">${arrow} ${sign}${pct}%</td>
      </tr>`;
  }).join('');
}

// ── Chart ────────────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById('portfolioChart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [{
      data: [],
      borderColor: '#FFB300',
      backgroundColor: 'rgba(255,179,0,0.07)',
      fill: true,
      tension: 0.4,
      pointRadius: 2,
      pointBackgroundColor: '#FFB300',
      borderWidth: 2,
    }]},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1400',
          borderColor: '#2a2200',
          borderWidth: 1,
          titleColor: '#FFB300',
          bodyColor: '#e0e0e0',
          callbacks: {
            label: ctx => ' $' + Number(ctx.raw).toLocaleString('en-US', {minimumFractionDigits: 2})
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,179,0,0.05)' },
          ticks: { color: '#444', font: { family: 'Space Mono', size: 10 }, maxTicksLimit: 8 }
        },
        y: {
          grid: { color: 'rgba(255,179,0,0.05)' },
          ticks: {
            color: '#444',
            font: { family: 'Space Mono', size: 10 },
            callback: v => '$' + (v/1000).toFixed(0) + 'k'
          }
        }
      }
    }
  });
}

function updateChart(history) {
  if (!chart || !history.length) return;
  chart.data.labels = history.map(h => h.t);
  chart.data.datasets[0].data = history.map(h => h.v);
  chart.update('none');
}

// ── Bot Log ──────────────────────────────────────────────
async function pollLog() {
  try {
    const res  = await fetch('/api/log?since=' + logIndex);
    const data = await res.json();

    botRunning = data.running;
    updateBotStatus();

    if (data.messages.length) {
      const container = document.getElementById('log-body');
      const isEmpty   = container.querySelector('.log-empty');
      if (isEmpty) isEmpty.remove();

      data.messages.forEach(msg => {
        const line = document.createElement('div');
        line.className = 'log-line';
        const cls = getMsgClass(msg.m);
        line.innerHTML =
          '<span class="log-time">' + msg.t + '</span>' +
          '<span class="log-msg ' + cls + '">' + escapeHtml(msg.m) + '</span>';
        container.appendChild(line);
      });

      container.scrollTop = container.scrollHeight;
      logIndex = data.total;
    }
  } catch (e) {}
}

function getMsgClass(msg) {
  const m = msg.toLowerCase();
  if (m.includes('error') || m.includes('failed')) return 'error';
  if (m.includes('complete') || m.includes('approved') || m.includes('buy') || m.includes('sell')) return 'success';
  if (m.includes('starting') || m.includes('[tool]') || m.includes('[dry')) return 'highlight';
  return '';
}

function updateBotStatus() {
  const dot   = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  const btnRun = document.getElementById('btn-run');
  const btnDry = document.getElementById('btn-dry');

  dot.className   = 'dot' + (botRunning ? ' running' : '');
  label.textContent = botRunning ? 'Bot Running' : 'Idle';
  btnRun.disabled = botRunning;
  btnDry.disabled = botRunning;
}

// ── Bot Controls ─────────────────────────────────────────
async function runBot(dry) {
  const password = document.getElementById('password').value;
  if (!password) {
    alert('Enter your dashboard password first.');
    return;
  }

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password, dry_run: dry })
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Error starting bot');
      return;
    }

    botRunning = true;
    updateBotStatus();
  } catch (e) {
    alert('Connection error: ' + e.message);
  }
}

// ── Helpers ──────────────────────────────────────────────
function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
