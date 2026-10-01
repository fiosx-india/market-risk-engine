// ===== STATE =====
let sectorChartInstance = null;
let instrChartInstance = null;

// ===== NAVIGATION =====
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        this.classList.add('active');
        const viewId = 'view-' + this.dataset.view;
        document.getElementById(viewId).classList.add('active');
        // Load view-specific data
        switch(this.dataset.view) {
            case 'dashboard': loadDashboard(); break;
            case 'instruments': loadInstrumentsFull(); break;
            case 'companies': loadCompanies(); break;
            case 'signals': loadSignals(); break;
            case 'forecasts': loadForecasts(); break;
            case 'leadlag': loadLeadLag(); break;
        }
    });
});

// ===== DASHBOARD =====
async function loadDashboard() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();
        const grid = document.getElementById('summaryGrid');
        grid.innerHTML = `
            <div class="summary-card">
                <div class="label">NIFTY 50</div>
                <div class="value ${data.instruments?.[0]?.direction === 'up' ? 'green' : 'red'}">
                    ${data.instruments?.[0]?.price?.toLocaleString() || '--'}
                </div>
                <div class="sub">${data.instruments?.[0]?.change_pct?.toFixed(2) || '0.00'}%</div>
            </div>
            <div class="summary-card">
                <div class="label">Companies Tracked</div>
                <div class="value blue">${data.total_companies}</div>
                <div class="sub">${Object.keys(data.sectors).length} sectors</div>
            </div>
            <div class="summary-card">
                <div class="label">Active Signals</div>
                <div class="value ${data.active_signals_count > 5 ? 'yellow' : 'green'}">${data.active_signals_count}</div>
                <div class="sub">${data.high_confidence_signals} high confidence</div>
            </div>
            <div class="summary-card">
                <div class="label">India VIX</div>
                <div class="value ${data.macro?.india_vix > 20 ? 'red' : 'green'}">${data.macro?.india_vix || '--'}</div>
                <div class="sub">USD/INR: ${data.macro?.usd_inr || '--'}</div>
            </div>
        `;

        // Macro grid
        const macroGrid = document.getElementById('macroGrid');
        const macro = data.macro || {};
        macroGrid.innerHTML = `
            <div class="macro-item"><div class="label">Fed Rate</div><div class="value">${macro.india_vix ? '--' : '--'}</div></div>
            <div class="macro-item"><div class="label">India VIX</div><div class="value">${macro.india_vix || '--'}</div></div>
            <div class="macro-item"><div class="label">USD/INR</div><div class="value">${macro.usd_inr || '--'}</div></div>
            <div class="macro-item"><div class="label">DXY</div><div class="value">${macro.dxy || '--'}</div></div>
        `;

        // Instrument grid
        const instrGrid = document.getElementById('instrumentGrid');
        instrGrid.innerHTML = (data.instruments || []).map(i => `
            <div class="instrument-card" onclick="switchView('instruments')">
                <div class="top">
                    <span class="symbol">${i.symbol}</span>
                    <span class="type">${i.name?.split('(')[0]?.trim() || i.name}</span>
                </div>
                <div class="price">${i.price?.toLocaleString() || '--'}</div>
                <div class="change ${i.direction === 'up' ? 'up' : 'down'}">${i.change_pct?.toFixed(2) || '0.00'}%</div>
            </div>
        `).join('');

        // Sector chart
        buildSectorChart(data.sectors);

        // Recent signals
        const sigRes = await fetch('/api/signals?limit=5');
        const signals = await sigRes.json();
        renderSignalCards(signals, 'dashboardSignals');

    } catch(e) {
        console.error('Dashboard load error:', e);
    }
}

function buildSectorChart(sectors) {
    const canvas = document.getElementById('sectorChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (sectorChartInstance) sectorChartInstance.destroy();

    const labels = Object.keys(sectors);
    const positive = labels.map(l => sectors[l].positive || 0);
    const negative = labels.map(l => -(sectors[l].negative || 0));
    const neutral = labels.map(l => (sectors[l].count || 0) - (sectors[l].positive || 0) - (sectors[l].negative || 0));

    sectorChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Positive', data: positive, backgroundColor: 'rgba(0,200,83,0.7)', borderRadius: 4 },
                { label: 'Negative', data: negative, backgroundColor: 'rgba(255,23,68,0.7)', borderRadius: 4 },
                { label: 'Neutral', data: neutral, backgroundColor: 'rgba(154,160,166,0.4)', borderRadius: 4 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#9aa0a6', font: { size: 11 } } }
            },
            scales: {
                x: { ticks: { color: '#9aa0a6', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#9aa0a6' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// ===== INSTRUMENTS =====
async function loadInstrumentsFull() {
    try {
        const res = await fetch('/api/instruments');
        const data = await res.json();
        const container = document.getElementById('instrumentsFull');
        container.innerHTML = data.map(i => `
            <div class="instrument-card">
                <div class="top">
                    <span class="symbol">${i.symbol}</span>
                    <span class="type">${i.type}</span>
                </div>
                <div class="price">${i.price?.toLocaleString() || '--'}</div>
                <div class="change ${(i.change_pct||0) > 0 ? 'up' : 'down'}">
                    ${i.change_pct?.toFixed(2) || '0.00'}%
                </div>
                <div class="range">
                    <span>H: ${i.high?.toLocaleString() || '--'}</span>
                    <span>L: ${i.low?.toLocaleString() || '--'}</span>
                </div>
                <div class="name" style="font-size:11px;color:var(--text-secondary);margin-top:6px;">${i.name}</div>
            </div>
        `).join('');

        // Build a simple price chart mockup
        buildInstrumentChart(data);
    } catch(e) { console.error(e); }
}

function buildInstrumentChart(instruments) {
    const canvas = document.getElementById('instrChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (instrChartInstance) instrChartInstance.destroy();

    const labels = instruments.map(i => i.symbol);
    const prices = instruments.map(i => i.price || 0);
    const colors = prices.map(p => (instruments[labels.indexOf(labels[prices.indexOf(p)])]?.change_pct||0) > 0
        ? 'rgba(0,200,83,0.7)' : 'rgba(255,23,68,0.7)');

    instrChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Price',
                data: prices,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { ticks: { color: '#9aa0a6', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#9aa0a6' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// ===== COMPANIES =====
async function loadCompanies() {
    try {
        const sector = document.getElementById('sectorFilter')?.value || '';
        const search = document.getElementById('companySearch')?.value || '';
        let url = '/api/companies';
        if (sector) url += `?sector=${encodeURIComponent(sector)}`;
        const res = await fetch(url);
        let companies = await res.json();
        if (search) {
            const q = search.toLowerCase();
            companies = companies.filter(c => c.symbol.toLowerCase().includes(q) || c.name.toLowerCase().includes(q));
        }
        const grid = document.getElementById('companiesGrid');
        grid.innerHTML = companies.map(c => `
            <div class="company-card" onclick="showCompanyDetail('${c.symbol}')">
                <div class="symbol">${c.symbol}</div>
                <div class="name">${c.name}</div>
                <span class="sector-tag">${c.sector}</span>
                <div class="meta">
                    <span title="Lead/Lag">&#9201; ${c.lead_lag || '--'}</span>
                    <span title="Volatility">&#9888; ${c.volatility_character || '--'}</span>
                    <span title="Rate Sensitivity">&#128176; ${((c.interest_rate_sensitivity||0)*100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('');

        // Populate sector filter
        const select = document.getElementById('sectorFilter');
        if (select && select.options.length <= 1) {
            const secRes = await fetch('/api/sectors');
            const sectors = await secRes.json();
            sectors.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.sector;
                opt.textContent = `${s.sector} (${s.count})`;
                select.appendChild(opt);
            });
        }
    } catch(e) { console.error(e); }
}

async function showCompanyDetail(symbol) {
    try {
        const res = await fetch(`/api/company/${symbol}`);
        const data = await res.json();
        const body = document.getElementById('modalBody');
        const profile = data.profile || {};
        const exposures = profile.commodity_exposure || {};

        let exposureHTML = '';
        for (const [instr, exp] of Object.entries(exposures)) {
            const pct = ((exp + 1) / 2 * 100).toFixed(0);
            const color = exp > 0 ? 'var(--accent-green)' : exp < -0.2 ? 'var(--accent-red)' : 'var(--accent-yellow)';
            exposureHTML += `
                <div style="margin:6px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:12px;">
                        <span>${instr}</span>
                        <span>${(exp*100).toFixed(1)}%</span>
                    </div>
                    <div class="exposure-bar"><div class="fill" style="width:${pct}%;background:${color};"></div></div>
                </div>
            `;
        }

        body.innerHTML = `
            <div class="modal-body">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <h2>${data.symbol} — ${data.name}</h2>
                    <span class="sector-tag" style="background:var(--bg-card);padding:4px 12px;border-radius:6px;font-size:12px;">${data.sector}</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-item"><div class="label">Lead/Lag Timing</div><div class="value">${profile.lead_lag || '--'}</div></div>
                    <div class="detail-item"><div class="label">Volatility Character</div><div class="value">${profile.volatility_character || '--'}</div></div>
                    <div class="detail-item"><div class="label">Currency Sensitivity</div><div class="value">${((profile.currency_sensitivity||0)*100).toFixed(1)}%</div></div>
                    <div class="detail-item"><div class="label">Interest Rate Sensitivity</div><div class="value">${((profile.interest_rate_sensitivity||0)*100).toFixed(1)}%</div></div>
                    <div class="detail-item"><div class="label">Supply Chain Dependency</div><div class="value">${((profile.supply_chain_dependency||0)*100).toFixed(0)}%</div></div>
                    <div class="detail-item"><div class="label">Regulatory Exposure</div><div class="value">${((profile.regulatory_exposure||0)*100).toFixed(0)}%</div></div>
                </div>
                <h3 style="margin-top:20px;font-size:15px;">Commodity Exposure Map</h3>
                ${exposureHTML}
                <div class="chart-container" style="margin-top:20px;height:250px;">
                    <canvas id="companyPriceChart"></canvas>
                </div>
            </div>
        `;
        document.getElementById('modalOverlay').classList.add('active');

        // Build price chart
        if (data.price_data && data.price_data.length > 0) {
            setTimeout(() => {
                const canvas = document.getElementById('companyPriceChart');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.price_data.map(d => d.date.slice(0,10)),
                        datasets: [{
                            label: 'Price',
                            data: data.price_data.map(d => d.close),
                            borderColor: '#2979ff',
                            backgroundColor: 'rgba(41,121,255,0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: 2,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: '#9aa0a6' } } },
                        scales: {
                            x: { ticks: { color: '#9aa0a6', font: { size: 9 }, maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            y: { ticks: { color: '#9aa0a6' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                        }
                    }
                });
            }, 100);
        }
    } catch(e) { console.error(e); }
}

// ===== SIGNALS =====
async function loadSignals() {
    try {
        const res = await fetch('/api/signals?limit=20');
        const signals = await res.json();
        renderSignalCards(signals, 'signalsList');
    } catch(e) { console.error(e); }
}

async function generateSignals() {
    try {
        await fetch('/api/signals/generate', { method: 'POST' });
        loadSignals();
    } catch(e) { console.error(e); }
}

function renderSignalCards(signals, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (signals.length === 0) {
        container.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:40px;">No active signals. Market conditions are stable.</div>';
        return;
    }
    container.innerHTML = signals.map(s => `
        <div class="signal-card ${s.direction}">
            <div class="top">
                <div>
                    <span class="signal-instr">${s.instrument}</span>
                    <span class="signal-dir ${s.direction}">${s.direction}</span>
                </div>
                <span style="font-size:11px;color:var(--text-secondary);">ID: #${s.id}</span>
            </div>
            <div class="signal-meta">
                <span>Confidence: <strong>${(s.confidence*100).toFixed(0)}%</strong></span>
                <span>Probability: <strong>${(s.probability*100).toFixed(0)}%</strong></span>
                <span>Impact: <strong>${s.impact_timing || s.time_horizon || '--'}</strong></span>
                <span>Strength: <strong>${s.strength}%</strong></span>
            </div>
            <div class="companies-row">
                ${(s.affected_companies || []).map(c =>
                    `<span class="company-chip" onclick="showCompanyDetail('${c.symbol}')" style="cursor:pointer;">
                        ${c.symbol} (${(c.exposure*100).toFixed(0)}%)
                    </span>`
                ).join('')}
            </div>
            <div class="evidence-row">
                <details>
                    <summary>Evidence Chain (${(s.evidence||[]).length} sources)</summary>
                    ${(s.evidence||[]).map(e =>
                        `<div class="evidence-item">
                            <span class="weight-${e.weight}">&#9679;</span>
                            <strong>${e.source}:</strong> ${e.detail}
                            <span style="color:var(--text-secondary);font-size:10px;">(${e.weight})</span>
                        </div>`
                    ).join('')}
                    ${(s.conflicting_evidence||[]).length > 0 ? `
                        <div style="margin-top:8px;color:var(--accent-red);font-size:11px;">
                            Conflicting evidence: ${s.conflicting_evidence.map(e => e.detail).join('; ')}
                        </div>
                    ` : ''}
                    <div style="margin-top:6px;font-size:10px;color:var(--text-secondary);">
                        Assumptions: ${(s.assumptions||[]).join(', ')}
                    </div>
                    <div style="font-size:10px;color:var(--accent-orange);">
                        Risk factors: ${(s.risk_factors||[]).join(', ')}
                    </div>
                </details>
            </div>
        </div>
    `).join('');
}

// ===== FORECASTS =====
async function loadForecasts() {
    try {
        const res = await fetch('/api/forecasts');
        const forecasts = await res.json();
        const tbody = document.querySelector('#forecastTable tbody');
        if (!tbody) return;

        // Group by instrument
        const grouped = {};
        forecasts.forEach(f => {
            if (!grouped[f.instrument]) grouped[f.instrument] = {};
            grouped[f.instrument][f.horizon] = f;
        });

        tbody.innerHTML = Object.entries(grouped).map(([instr, horizons]) => `
            <tr>
                <td><strong>${instr}</strong></td>
                ${['5 min','15 min','30 min','60 min','Next Session','Next Day'].map(h => {
                    const f = horizons[h];
                    if (!f) return '<td class="forecast-cell">--</td>';
                    return `<td class="forecast-cell">
                        <div class="forecast-dir ${f.direction}">${f.direction.toUpperCase()}</div>
                        <div class="forecast-prob">${(f.probability*100).toFixed(0)}% | ${(f.confidence*100).toFixed(0)}% conf</div>
                        <div style="font-size:10px;color:var(--text-secondary);">
                            ${f.target_range?.low || '--'} - ${f.target_range?.high || '--'}
                        </div>
                    </td>`;
                }).join('')}
            </tr>
        `).join('');
    } catch(e) { console.error(e); }
}

// ===== LEAD/LAG =====
async function loadLeadLag() {
    try {
        const res = await fetch('/api/leadlag');
        const matrix = await res.json();
        const table = document.getElementById('leadlagTable');
        if (!table) return;
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');

        // Get all sectors from first entry
        const sectors = Object.keys(Object.values(matrix)[0]?.sector_timing || {});

        thead.innerHTML = `<tr><th>Instrument</th>${sectors.map(s => `<th>${s}</th>`).join('')}</tr>`;

        tbody.innerHTML = Object.entries(matrix).map(([instr, data]) => `
            <tr>
                <td><strong>${instr}</strong><br><span style="font-size:10px;color:var(--text-secondary);">${data.type}</span></td>
                ${sectors.map(s => {
                    const timing = data.sector_timing[s] || 'Long-Lag';
                    return `<td><span class="leadlag-timing ${timing.replace(' ','-')}">${timing}</span></td>`;
                }).join('')}
            </tr>
        `).join('');
    } catch(e) { console.error(e); }
}

// ===== UTILITY =====
function switchView(viewName) {
    const tab = document.querySelector(`.nav-tab[data-view="${viewName}"]`);
    if (tab) tab.click();
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
}

function refreshData() {
    loadDashboard();
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();

    // Auto-refresh dashboard every 10 seconds
    setInterval(() => {
        if (document.getElementById('view-dashboard').classList.contains('active')) {
            loadDashboard();
        }
    }, 10000);
});
