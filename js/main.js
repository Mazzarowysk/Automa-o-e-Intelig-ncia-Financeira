/**
 * ITUB4 Quantum - Main JavaScript
 * Focado em RSI e R² (XGBoost)
 */

document.addEventListener('DOMContentLoaded', () => {
    // Inicialização
    loadMetrics();
    loadChartData();
    setupEventListeners();
    setupTrainingPanel();
    setupChartTimeframeControls();
    setupAnalystDiary();
    setupSentimentFilters();
    initDateEnd();
    setupCollapsiblePanels();
});

/**
 * Renderiza os dados de sentimento nos elementos HTML.
 * Aceita o objeto de dados diretamente (do cache JSON ou da API).
 */
function renderSentimentData(data) {
    const statusEl = document.getElementById('sentiment-status');
    const scoreTextEl = document.getElementById('sentiment-score-text');
    const periodInfoEl = document.getElementById('sentiment-period-info');
    const fill = document.getElementById('sentiment-fill');
    const newsList = document.getElementById('sentiment-news-list');

    // Badge e aviso dinâmico de fonte da API
    const noticeEl     = document.getElementById('sentiment-api-notice');
    const sourceBadgeEl= document.getElementById('sentiment-source-badge');
    const isAlphaVantage = data.fonte && data.fonte.includes('Alpha Vantage');

    if (noticeEl) {
        if (isAlphaVantage) {
            noticeEl.innerHTML = '✅ <strong>Alpha Vantage</strong> ativa — até 50 notícias históricas reais por período.';
            noticeEl.style.color = '#10b981';
        } else {
            noticeEl.innerHTML = '⚠️ Modo Yahoo Finance — limite de ~10 notícias recentes. Configure a chave Alpha Vantage em <code>config.py</code> para dados históricos completos.';
            noticeEl.style.color = '#f59e0b';
        }
    }
    if (sourceBadgeEl) {
        sourceBadgeEl.textContent = data.fonte || 'Yahoo Finance + VADER NLP';
        sourceBadgeEl.style.color = isAlphaVantage ? '#10b981' : '#f59e0b';
    }

    if (data.erro && !data.noticias?.length) {
        statusEl.textContent = 'Indisponível';
        statusEl.style.color = '#94a3b8';
        scoreTextEl.textContent = data.erro;
        if (periodInfoEl) periodInfoEl.textContent = '';
        newsList.innerHTML = `<p style="color:#94a3b8">Nenhuma notícia analisada para este período.</p>`;
        return;
    }

    const score    = data.score_medio ?? 0;
    const cls      = data.classificacao ?? 'Neutro';
    const percent  = ((score + 1) / 2) * 100;
    const newsCount= data.noticias?.length ?? 0;

    // Salvar globalmente para uso no gráfico de previsão híbrida
    window.currentSentimentScore = score;
    window.currentSentimentClass = cls;
    
    // Atualiza imediatamente o painel de confluência, se houver
    if (typeof updateConfluencePanel === 'function') {
        updateConfluencePanel();
    }

    const countEl = document.getElementById('sentiment-news-count');
    if (countEl) countEl.textContent = newsCount;

    fill.style.width = percent + '%';

    // Thresholds adaptados por fonte
    const thr = isAlphaVantage ? 0.05 : 0.15;
    let mainEmoji = '😐';
    if (score >= thr)  mainEmoji = '😃';
    if (score <= -thr) mainEmoji = '😡';

    statusEl.textContent      = `${mainEmoji} ${cls}`;
    scoreTextEl.textContent   = `Score Médio: ${score.toFixed(4)}`;
    statusEl.style.color      = score >= thr ? '#10b981' : score <= -thr ? '#ef4444' : '#f59e0b';

    if (periodInfoEl && data.periodo) {
        const { inicio, fim } = data.periodo;
        if (inicio || fim) {
            const fmtDate = d => d ? new Date(d + 'T00:00:00').toLocaleDateString('pt-BR') : 'início';
            periodInfoEl.textContent = `Período: ${fmtDate(inicio)} → ${fmtDate(fim)}`;
        } else {
            periodInfoEl.textContent = `Atualizado: ${data.atualizado_em ?? ''}`;
        }
    }

    newsList.innerHTML = '';
    if (data.noticias && data.noticias.length > 0) {
        data.noticias.forEach(news => {
            let badgeColor = '#f59e0b', badgeText = '😐 NEUTRO';
            if (news.score >= thr)  { badgeColor = '#10b981'; badgeText = '😃 OTIMISMO'; }
            if (news.score <= -thr) { badgeColor = '#ef4444'; badgeText = '😡 PESSIMISMO'; }

            const linkOpen  = news.link ? `<a href="${news.link}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;">` : '';
            const linkClose = news.link ? `</a>` : '';
            // Alpha Vantage envia 'fonte' (veículo); Yahoo não envia
            const fonteHtml = news.fonte ? `<span style="color:#475569;font-size:0.68rem;margin-left:6px;">📰 ${news.fonte}</span>` : '';

            newsList.innerHTML += `
                <div style="background:rgba(255,255,255,0.03);padding:10px;border-radius:8px;border-left:3px solid ${badgeColor};">
                    ${linkOpen}
                    <h5 style="margin:0 0 5px 0;font-size:0.9rem;color:#f8fafc;display:flex;justify-content:space-between;align-items:flex-start;">
                        <span style="flex:1;margin-right:8px">${news.titulo}</span>
                        <span style="background:${badgeColor}20;color:${badgeColor};padding:2px 6px;border-radius:4px;font-size:0.7rem;white-space:nowrap;flex-shrink:0">${badgeText}</span>
                    </h5>
                    <p style="margin:0 0 5px 0;font-size:0.8rem;color:#94a3b8;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${news.resumo || 'Sem resumo disponível.'}</p>
                    <div style="display:flex;align-items:center;gap:4px;">
                        <small style="color:#64748b;font-size:0.7rem;">${news.data || 'Data desconhecida'}</small>
                        ${fonteHtml}
                    </div>
                    ${linkClose}
                </div>`;
        });
    } else {
        newsList.innerHTML = `<p style="color:#94a3b8;font-size:0.9rem;">Nenhuma notícia encontrada para este período.</p>`;
    }
}

/**
 * Carrega sentimento do cache local (itub4_sentimento.json).
 */
async function loadSentimentData() {
    try {
        const response = await fetch('itub4_sentimento.json?t=' + Date.now());
        if (!response.ok) throw new Error('JSON não encontrado');
        const data = await response.json();
        renderSentimentData(data);
    } catch (e) {
        console.warn('Sentimento (cache) não disponível:', e.message);
        document.getElementById('sentiment-status').textContent = 'Sem dados';
        document.getElementById('sentiment-score-text').textContent = 'Execute o treinamento para gerar análise.';
    }
}

/**
 * Busca sentimento via servidor para um período específico.
 * @param {string|null} startDate - YYYY-MM-DD ou null
 * @param {string|null} endDate   - YYYY-MM-DD ou null
 */
async function fetchSentimentByPeriod(startDate, endDate) {
    const loadingEl = document.getElementById('sentiment-loading');
    const statusEl  = document.getElementById('sentiment-status');

    if (loadingEl) loadingEl.style.display = 'flex';
    statusEl.textContent = 'Buscando...';

    try {
        const body = JSON.stringify({ start: startDate, end: endDate });
        const response = await fetch('/sentiment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body
        });

        if (!response.ok) throw new Error(`Servidor retornou ${response.status}`);
        const data = await response.json();
        renderSentimentData(data);
    } catch (e) {
        console.error('Erro ao buscar sentimento:', e);
        statusEl.textContent = 'Erro';
        document.getElementById('sentiment-score-text').textContent = 'Falha na comunicação com o servidor.';
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

/**
 * Configura os botões de filtro de período do sentimento.
 */
function setupSentimentFilters() {
    const periodBtns = document.querySelectorAll('[data-sentiment-period]');
    const customDatesEl = document.getElementById('sentiment-custom-dates');
    const sentimentStartEl = document.getElementById('sentiment-start');
    const sentimentEndEl   = document.getElementById('sentiment-end');
    const searchBtn = document.getElementById('btn-sentiment-search');

    // Inicializar campos de data com valores padrão
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    const weekAgo = new Date(today); weekAgo.setDate(today.getDate() - 7);
    const weekAgoStr = weekAgo.toISOString().split('T')[0];

    if (sentimentStartEl) sentimentStartEl.value = weekAgoStr;
    if (sentimentEndEl)   sentimentEndEl.value   = todayStr;

    // Carregar dados iniciais (período padrão = 1 semana)
    const startInit = weekAgoStr;
    const endInit   = todayStr;
    fetchSentimentByPeriod(startInit, endInit);

    periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            periodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const period = btn.dataset.sentimentPeriod;

            if (period === 'custom') {
                if (customDatesEl) customDatesEl.style.display = 'flex';
                // Não disparar busca ainda — aguardar o clique em "Buscar"
                return;
            }

            if (customDatesEl) customDatesEl.style.display = 'none';

            const end = new Date();
            end.setHours(23, 59, 59);
            let start = null;

            if (period !== 'all') {
                start = new Date();
                const days = { '7d': 7, '30d': 30, '90d': 90, '180d': 180, '365d': 365 }[period];
                if (days) start.setDate(start.getDate() - days);
            }

            const startStr = start ? start.toISOString().split('T')[0] : null;
            const endStr   = end.toISOString().split('T')[0];

            fetchSentimentByPeriod(startStr, endStr);
        });
    });

    // Botão Buscar (período personalizado)
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const start = sentimentStartEl?.value || null;
            const end   = sentimentEndEl?.value   || null;
            if (!start && !end) {
                alert('Por favor, preencha ao menos uma data.');
                return;
            }
            fetchSentimentByPeriod(start, end);
        });
    }
}

function initDateEnd() {
    const endInput = document.getElementById('train-end');
    if (endInput && !endInput.value) {
        const today = new Date();
        endInput.value = today.toISOString().split('T')[0];
    }

    // Heartbeat ping: avisa ao servidor a cada 2s que o navegador ainda está aberto
    setInterval(() => {
        fetch('/ping').catch(() => {});
    }, 2000);
}

function formatDateLabel(value) {
    if (!value) return '';
    const raw = String(value).trim();
    const datePart = raw.split(' ')[0];
    const isoMatch = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (isoMatch) {
        const [, year, month, day] = isoMatch;
        return `${day}/${month}/${year}`;
    }
    const brMatch = datePart.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (brMatch) {
        return datePart;
    }
    const parsed = new Date(datePart);
    if (!isNaN(parsed)) {
        return parsed.toLocaleDateString('pt-BR');
    }
    return datePart;
}

let activeChartTimeFrame = 'all';
let activeChartCustomStart = null;
let activeChartCustomEnd = null;

let activeTechChartTimeFrame = 'all'; // Padrao agora é all (Global) para unificar
let activeTechCustomStart = null;
let activeTechCustomEnd = null;

let activeRsiChartTimeFrame = 'all';
let activeRsiCustomStart = null;
let activeRsiCustomEnd = null;

function filterHistoryByTimeframe(data, timeframe, customStart = null, customEnd = null) {
    if (!Array.isArray(data) || data.length === 0) return [];
    if (timeframe === 'all') return data;

    if (timeframe === 'custom') {
        const s = customStart ? new Date(`${customStart}T00:00:00`) : new Date('1900-01-01');
        const e = customEnd ? new Date(`${customEnd}T23:59:59`) : new Date('2100-01-01');
        return data.filter(row => {
            const rowDateString = String(row.Date).split(' ')[0];
            const rowDate = new Date(`${rowDateString}T00:00:00`);
            return rowDate >= s && rowDate <= e;
        });
    }

    // Ancorar o filtro na última data disponível no conjunto de dados para evitar erros de fuso horário ou relógio local desatualizado
    let anchorDate = new Date();
    if (data.length > 0) {
        const lastRowDateString = String(data[data.length - 1].Date).split(' ')[0];
        const parsedLastDate = new Date(`${lastRowDateString}T00:00:00`);
        if (!isNaN(parsedLastDate.getTime())) {
            anchorDate = parsedLastDate;
        }
    }
    anchorDate.setHours(0, 0, 0, 0);
    const startDate = new Date(anchorDate);

    if (timeframe === '5Y') {
        startDate.setFullYear(startDate.getFullYear() - 5);
    } else if (timeframe === '3Y') {
        startDate.setFullYear(startDate.getFullYear() - 3);
    } else if (timeframe === '1Y') {
        startDate.setFullYear(startDate.getFullYear() - 1);
    } else if (timeframe === '6M') {
        startDate.setMonth(startDate.getMonth() - 6);
    } else if (timeframe === '3M') {
        startDate.setMonth(startDate.getMonth() - 3);
    } else if (timeframe === '1M') {
        startDate.setMonth(startDate.getMonth() - 1);
    }

    return data.filter(row => {
        const rowDateString = String(row.Date).split(' ')[0];
        const rowDate = new Date(`${rowDateString}T00:00:00`);
        return rowDate >= startDate;
    });
}

function setupChartTimeframeControls() {
    function setupGroup(groupId, setActiveTimeFrame, setActiveCustom, redrawFunc) {
        const group = document.getElementById(groupId);
        if (!group) return;
        const controls = group.querySelectorAll('.chart-toggle-btn[data-period]');
        const customContainer = group.querySelector('.custom-dates-container');
        const customStart = group.querySelector('.custom-start-date');
        const customEnd = group.querySelector('.custom-end-date');
        const customBtn = group.querySelector('.custom-search-btn');

        controls.forEach(btn => {
            btn.addEventListener('click', () => {
                const period = btn.dataset.period;
                controls.forEach(item => item.classList.remove('active'));
                btn.classList.add('active');

                if (period === 'custom') {
                    if (customContainer) customContainer.style.display = 'flex';
                } else {
                    if (customContainer) customContainer.style.display = 'none';
                    setActiveTimeFrame(period);
                    redrawFunc();
                }
            });
        });

        if (customBtn) {
            customBtn.addEventListener('click', () => {
                const start = customStart ? customStart.value : null;
                const end = customEnd ? customEnd.value : null;
                if (!start && !end) {
                    alert('Preencha ao menos uma data.');
                    return;
                }
                setActiveTimeFrame('custom');
                setActiveCustom(start, end);
                redrawFunc();
            });
        }
    }

    setupGroup('timeframe-controls', 
        (tf) => { activeChartTimeFrame = tf; }, 
        (start, end) => { activeChartCustomStart = start; activeChartCustomEnd = end; }, 
        drawCharts
    );

    setupGroup('tech-timeframe-controls', 
        (tf) => { activeTechChartTimeFrame = tf; }, 
        (start, end) => { activeTechCustomStart = start; activeTechCustomEnd = end; }, 
        drawTechCharts
    );

    setupGroup('rsi-timeframe-controls', 
        (tf) => { activeRsiChartTimeFrame = tf; }, 
        (start, end) => { activeRsiCustomStart = start; activeRsiCustomEnd = end; }, 
        drawRsiChart
    );

    // Modal também
    setupGroup('modal-timeframe-controls', 
        (tf) => { activeTechChartTimeFrame = tf; }, 
        (start, end) => { activeTechCustomStart = start; activeTechCustomEnd = end; }, 
        () => {
            drawTechCharts();
            if (window.currentExpandedChartId) {
                // Dispara o evento de expandir novamente para recarregar o modal
                const btn = document.querySelector(`.btn-expand-chart[data-chart="${window.currentExpandedChartId}"]`);
                if (btn) btn.click();
            }
        }
    );

    const resetZoomBtn = document.getElementById('reset-zoom-btn');
    if (resetZoomBtn) resetZoomBtn.addEventListener('click', resetPriceChartZoom);

    const techResetZoomBtn = document.getElementById('tech-reset-zoom-btn');
    if (techResetZoomBtn) {
        techResetZoomBtn.addEventListener('click', () => {
            [realPriceChartInstance, ma20ChartInstance, xgbForecastChartInstance, predictionPointsChartInstance]
                .filter(Boolean)
                .forEach(chart => chart.resetZoom());
        });
    }

    const rsiResetZoomBtn = document.getElementById('rsi-reset-zoom-btn');
    if (rsiResetZoomBtn) {
        rsiResetZoomBtn.addEventListener('click', () => {
            if (rsiChartInstance && rsiChartInstance.options && rsiChartInstance.options.scales && rsiChartInstance.options.scales.x) {
                rsiChartInstance.options.scales.x.min = undefined;
                rsiChartInstance.options.scales.x.max = undefined;
                rsiChartInstance.update('none');
            }
        });
    }
}

function resetPriceChartZoom() {
    if (!priceChartInstance || !priceChartInstance.options || !priceChartInstance.options.scales || !priceChartInstance.options.scales.x) return;
    priceChartInstance.options.scales.x.min = undefined;
    priceChartInstance.options.scales.x.max = undefined;
    priceChartInstance.update('none');
}

// Cache global
let globalData = {
    history: [],
    predictions: [],
    metrics: {}
};
window.globalData = globalData;

// Instâncias do Chart.js
let priceChartInstance = null;
let rsiChartInstance = null;
let realPriceChartInstance = null;
let ma20ChartInstance = null;
let xgbForecastChartInstance = null;
let predictionPointsChartInstance = null;

let expandedChartInstance = null;

/**
 * Event Listeners Principais
 */
function setupEventListeners() {
    document.getElementById('btn-refresh').addEventListener('click', () => {
        const btn = document.getElementById('btn-refresh');
        const icon = btn.querySelector('i');
        icon.classList.add('fa-spin');
        
        Promise.all([
            loadMetrics(),
            loadSentimentData(),
            loadChartData()
        ]).then(() => {
            setTimeout(() => icon.classList.remove('fa-spin'), 500);
            updateTimestamp();
        });
    });

    // Lógica do Painel de Informações
    const btnToggleInfo = document.getElementById('btn-toggle-info');
    const btnCloseInfo = document.getElementById('btn-close-info');
    const infoPanel = document.getElementById('info-panel');

    if (btnToggleInfo && infoPanel) {
        btnToggleInfo.addEventListener('click', () => {
            infoPanel.classList.toggle('active');
        });
    }

    if (btnCloseInfo && infoPanel) {
        btnCloseInfo.addEventListener('click', () => {
            infoPanel.classList.remove('active');
        });
    }

    const kpiModalOverlay = document.getElementById('kpi-modal');
    const chartExpandModal = document.getElementById('chart-expand-modal');
    
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (kpiModalOverlay && kpiModalOverlay.classList.contains('active')) {
                kpiModalOverlay.classList.remove('active');
            }
            if (chartExpandModal && chartExpandModal.classList.contains('active')) {
                chartExpandModal.classList.remove('active');
                if (expandedChartInstance) expandedChartInstance.destroy();
            }
            if (infoPanel && infoPanel.classList.contains('active')) {
                infoPanel.classList.remove('active');
            }
        }
    });

    const btnCloseExpanded = document.getElementById('btn-close-expanded');
    if (btnCloseExpanded) {
        btnCloseExpanded.addEventListener('click', () => {
            if (chartExpandModal) chartExpandModal.classList.remove('active');
            if (expandedChartInstance) expandedChartInstance.destroy();
        });
    }

    // Function to expand a specific chart
    function expandChart(chartId) {
        if (!realPriceChartInstance || !ma20ChartInstance || !xgbForecastChartInstance || !predictionPointsChartInstance) return;

        let title = '';
        if (chartId === 'realPriceChart') { title = 'Preço Real (ITUB4)'; }
        else if (chartId === 'ma20Chart') { title = 'Média Móvel (20d)'; }
        else if (chartId === 'xgbForecastChart') { title = 'Previsão IA (XGBoost)'; }
        else if (chartId === 'predictionPointsChart') { title = 'Pontos de Previsão'; }
        
        if (chartExpandModal) {
            window.currentExpandedChartId = chartId;
            document.getElementById('expanded-chart-title').innerText = "Análise Técnica - " + title;
            chartExpandModal.classList.add('active');
            
            // Sync active period button in modal
            const modalControls = document.querySelectorAll('#modal-timeframe-controls .chart-toggle-btn');
            modalControls.forEach(btn => {
                btn.classList.remove('active');
                if(btn.dataset.period === activeTechChartTimeFrame) btn.classList.add('active');
            });

            const ctx = document.getElementById('expandedChart').getContext('2d');
            if (expandedChartInstance) expandedChartInstance.destroy();
            
            // Base labels from XGBoost chart (includes historical + future)
            const combinedLabels = JSON.parse(JSON.stringify(xgbForecastChartInstance.data.labels));
            
            // Deep clone all datasets
            const realPriceDataset = JSON.parse(JSON.stringify(realPriceChartInstance.data.datasets[0]));
            const ma20Dataset = JSON.parse(JSON.stringify(ma20ChartInstance.data.datasets[0]));
            const xgbDatasets = JSON.parse(JSON.stringify(xgbForecastChartInstance.data.datasets));
            const predictionDataset = JSON.parse(JSON.stringify(predictionPointsChartInstance.data.datasets[0]));
            
            // Hide datasets that were not clicked
            if (chartId !== 'realPriceChart') realPriceDataset.hidden = true;
            if (chartId !== 'ma20Chart') ma20Dataset.hidden = true;
            if (chartId !== 'xgbForecastChart') xgbDatasets.forEach(ds => ds.hidden = true);
            if (chartId !== 'predictionPointsChart') predictionDataset.hidden = true;

            const allDatasets = [realPriceDataset, ma20Dataset, ...xgbDatasets, predictionDataset];

            // Use XGBoost options as base
            const sourceOptions = JSON.parse(JSON.stringify(xgbForecastChartInstance.options));
            
            // Restore callbacks lost during JSON stringify
            if (sourceOptions.plugins && sourceOptions.plugins.tooltip && xgbForecastChartInstance.options.plugins.tooltip.callbacks) {
                sourceOptions.plugins.tooltip.callbacks = xgbForecastChartInstance.options.plugins.tooltip.callbacks;
            }
            if (sourceOptions.scales && sourceOptions.scales.x && sourceOptions.scales.x.ticks && xgbForecastChartInstance.options.scales.x.ticks.callback) {
                sourceOptions.scales.x.ticks.callback = xgbForecastChartInstance.options.scales.x.ticks.callback;
            }
            
            // Ajustar opções para visualização grande
            if (sourceOptions.plugins && sourceOptions.plugins.legend && sourceOptions.plugins.legend.labels) {
                sourceOptions.plugins.legend.labels.font.size = 14;
            }
            if (sourceOptions.plugins && sourceOptions.plugins.tooltip) {
                sourceOptions.plugins.tooltip.titleFont = sourceOptions.plugins.tooltip.titleFont || {};
                sourceOptions.plugins.tooltip.bodyFont = sourceOptions.plugins.tooltip.bodyFont || {};
                sourceOptions.plugins.tooltip.titleFont.size = 16;
                sourceOptions.plugins.tooltip.bodyFont.size = 14;
            }
            if (sourceOptions.scales && sourceOptions.scales.x) sourceOptions.scales.x.ticks.font = {size: 14};
            if (sourceOptions.scales && sourceOptions.scales.y) sourceOptions.scales.y.ticks.font = {size: 14};
            
            // Ativar zoom no expanded chart
            sourceOptions.plugins = sourceOptions.plugins || {};
            sourceOptions.plugins.zoom = {
                pan: { enabled: true, mode: 'x' },
                zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
            };

            const pluginsToCopy = [...xgbForecastChartInstance.config.plugins];

            expandedChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: combinedLabels,
                    datasets: allDatasets
                },
                options: sourceOptions,
                plugins: pluginsToCopy
            });
        }
    }

    // Lógica para botões de expandir gráficos e clique nos gráficos
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-expand-chart');
        if (btn) {
            expandChart(btn.getAttribute('data-chart'));
            return;
        }

        const canvas = e.target.closest('canvas');
        if (canvas && ['realPriceChart', 'ma20Chart', 'xgbForecastChart', 'predictionPointsChart'].includes(canvas.id)) {
            expandChart(canvas.id);
        }
    });

    // Handle timeframe changes in modal
    const modalTechControls = document.querySelectorAll('#modal-timeframe-controls .chart-toggle-btn[data-period]');
    if (modalTechControls && modalTechControls.length > 0) {
        modalTechControls.forEach(btn => {
            btn.addEventListener('click', () => {
                modalTechControls.forEach(item => item.classList.remove('active'));
                btn.classList.add('active');
                
                activeTechChartTimeFrame = btn.dataset.period || 'all';
                
                // Sync main page buttons
                const techControls = document.querySelectorAll('#tech-timeframe-controls .chart-toggle-btn[data-period]');
                techControls.forEach(item => {
                    item.classList.remove('active');
                    if(item.dataset.period === activeTechChartTimeFrame) {
                        item.classList.add('active');
                    }
                });
                
                drawTechCharts(); // redraw small charts with new timeframe
                
                // Refresh modal chart
                if (window.currentExpandedChartId) {
                    expandChart(window.currentExpandedChartId);
                }
            });
        });
    }

    // Lógica de Desligamento Inteligente do Servidor
    const btnShutdown = document.getElementById('btn-shutdown');
    if (btnShutdown) {
        btnShutdown.addEventListener('click', async () => {
            if(confirm("Tem certeza que deseja desligar o servidor do Dashboard? A página parará de funcionar.")) {
                try {
                    await fetch('/shutdown');
                } catch(e) {
                    // Ignora o erro pois o fetch falhará quando o servidor morrer
                }
                btnShutdown.innerHTML = '<i class="fa-solid fa-check"></i> Desligado';
                btnShutdown.style.background = 'var(--danger)';
                btnShutdown.style.color = 'white';
                btnShutdown.disabled = true;
                document.body.style.opacity = '0.5';
                document.body.style.pointerEvents = 'none';
                alert("Servidor finalizado com sucesso! Você já pode fechar esta aba e a janela preta do CMD de forma limpa.");
            }
        });
    }

    // Navegação na Sidebar (Abas)
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            const targetId = item.getAttribute('data-target');
            
            const kpiSection = document.getElementById('kpi-section');
            const chartPrice = document.getElementById('chart-price');
            const chartRsi = document.getElementById('chart-rsi');

            const analystTools = document.getElementById('analyst-tools');
            const trainingSection = document.getElementById('training-section');

            if (targetId === 'all') {
                kpiSection.style.display = 'grid';
                chartPrice.style.display = 'block';
                chartRsi.style.display = 'block';
                if (analystTools) analystTools.style.display = 'none';
                if (trainingSection) trainingSection.style.display = 'block';
            } else if (targetId === 'kpi') {
                kpiSection.style.display = 'grid';
                chartPrice.style.display = 'none';
                chartRsi.style.display = 'none';
                if (analystTools) analystTools.style.display = 'none';
                if (trainingSection) trainingSection.style.display = 'none';
            } else if (targetId === 'tech') {
                kpiSection.style.display = 'none';
                chartPrice.style.display = 'none';
                chartRsi.style.display = 'block';
                if (analystTools) analystTools.style.display = 'block';
                if (trainingSection) trainingSection.style.display = 'none';
            } else if (targetId === 'ai') {
                kpiSection.style.display = 'none';
                chartPrice.style.display = 'block';
                chartRsi.style.display = 'none';
                if (analystTools) analystTools.style.display = 'none';
                if (trainingSection) trainingSection.style.display = 'none';
            }
            refreshChartsOnTab(targetId);
        });
    });

    // Lógica do Modal de KPIs
    const kpiCards = document.querySelectorAll('.kpi-card[data-kpi]');
    const modalOverlay = document.getElementById('kpi-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalIcon = document.getElementById('modal-icon');
    const modalValue = document.getElementById('modal-value');
    const modalBody = document.getElementById('modal-body');

    const closeModal = () => {
        if (modalOverlay) modalOverlay.classList.remove('active');
    };

    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', closeModal);
    }

    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) closeModal();
        });
    }

    if (kpiCards.length === 0) {
        console.warn('Nenhum card KPI encontrado para abrir o modal. Verifique o seletor .kpi-card[data-kpi]');
    }

    kpiCards.forEach((card) => {
        card.addEventListener('click', () => {
            const key = card.dataset.kpi;
            const data = buildModalData()[key];
            if (!data) return;

            if (modalTitle) modalTitle.innerText = data.title;
            if (modalIcon) modalIcon.innerHTML = `<i class="fa-solid ${data.icon}"></i>`;
            if (modalValue) {
                const valEl = document.getElementById(data.valId);
                modalValue.innerText = valEl ? valEl.innerText : '--';
                const valClass = valEl ? valEl.className.replace('kpi-value', '').trim() : '';
                modalValue.className = `modal-value-large ${valClass}`.trim();
            }
            if (modalBody) modalBody.innerHTML = data.desc;

            if (modalOverlay) modalOverlay.classList.add('active');
        });
    });
}

/**
 * Gera análise descritiva dinâmica baseada nos valores reais do modelo
 */
function refreshChartsOnTab(targetId) {
    requestAnimationFrame(() => {
        const chartsToResize = [priceChartInstance, rsiChartInstance, realPriceChartInstance, ma20ChartInstance, xgbForecastChartInstance, predictionPointsChartInstance];
        chartsToResize.forEach(chart => {
            if (chart && chart.canvas && chart.canvas.offsetParent !== null) {
                chart.resize();
                chart.update('none');
            }
        });
    });
}

function buildModalData() {
    const metrics = globalData.metrics || {};
    const history = globalData.history || [];
    const lastRow = history.length > 0 ? history[history.length - 1] : {};
    const prevRow = history.length > 1 ? history[history.length - 2] : {};

    // ---- R² ----
    const r2Raw = metrics['R²'] || 0;
    const r2Pct = (r2Raw * 100).toFixed(1);
    const maeVal = metrics['MAE'] ? `R$ ${metrics['MAE'].toFixed(2)}` : 'N/A';
    let r2Nivel, r2Cor, r2Analise, r2Contexto, r2Sugestoes;

    if (r2Raw > 0.5) {
        r2Nivel = 'EXCELENTE';
        r2Cor = '#10b981';
        r2Analise = `Com <strong>${r2Pct}%</strong> de poder explicativo, o modelo XGBoost está capturando mais da metade de toda a variância dos preços da ITUB4. Isso é <strong>excepcional</strong> para renda variável, onde a aleatoriedade domina. Os indicadores técnicos (RSI, Bollinger, Volatilidade, Volume) estão funcionando como preditores muito fortes.`;
        r2Contexto = `Para contexto: fundos quantitativos profissionais costumam operar com modelos entre 5% e 30% de R². Seu modelo está significativamente acima dessa faixa.`;
        r2Sugestoes = `✅ O modelo está em excelente forma. Mantenha os dados atualizados e monitore a Acurácia Direcional para confirmar que a qualidade se mantém ao longo do tempo.`;
    } else if (r2Raw > 0.15) {
        r2Nivel = 'BOM';
        r2Cor = '#22d3ee';
        r2Analise = `Com <strong>${r2Pct}%</strong> de poder explicativo, o modelo está capturando uma parcela significativa das tendências de preço da ITUB4. Esse resultado indica que os indicadores técnicos do algoritmo (RSI, Bollinger, Médias Móveis) estão conseguindo <strong>identificar padrões reais</strong> no comportamento do ativo.`;
        r2Contexto = `Para referência: a maioria dos modelos de machine learning aplicados ao mercado financeiro opera na faixa de 5% a 30% de R². Seu resultado está dentro ou acima dessa faixa de mercado.`;
        r2Sugestoes = `💡 <strong>Sugestão:</strong> Experimente adicionar features macroeconômicas (taxa Selic, dólar, IBOVESPA) ou aumentar o histórico de treinamento para potencializar esse resultado.`;
    } else if (r2Raw > 0) {
        r2Nivel = 'MODERADO';
        r2Cor = '#f59e0b';
        r2Analise = `Com <strong>${r2Pct}%</strong> de poder explicativo, o modelo tem uma capacidade <strong>parcial</strong> de capturar variações de preço. Embora o R² seja baixo, um valor positivo significa que o modelo ainda é <strong>melhor</strong> do que simplesmente prever a média histórica do mercado — ele está extraindo algum sinal dos indicadores técnicos.`;
        r2Contexto = `Isso é comum em mercados eficientes como a B3, onde muita informação já está precificada. Mesmo fundos quantitativos operam com R² baixos, compensando com volume e frequência de operações.`;
        r2Sugestoes = `💡 <strong>Sugestões para melhorar:</strong><br>• Aumentar o volume de dados históricos no CSV<br>• Testar novas features (ex: volume relativo, MACD, OBV)<br>• Ajustar os hiperparâmetros do XGBoost (learning_rate, max_depth)<br>• Considerar janelas de treinamento mais curtas (regime recente)`;
    } else if (r2Raw > -0.25) {
        r2Nivel = 'EM CALIBRAÇÃO';
        r2Cor = '#f97316';
        r2Analise = `O R² de <strong>${r2Pct}%</strong> indica que o modelo está levemente abaixo da linha de base (a média simples do mercado). Porém, <strong>isso não significa que o modelo é inútil</strong>. Um R² levemente negativo é extremamente comum em modelos financeiros, especialmente quando:`;
        r2Contexto = `<strong>1.</strong> O mercado passou por um evento atípico (ex: crise, earnings surprise) que nenhum indicador técnico poderia antecipar.<br><strong>2.</strong> O modelo foi treinado em um regime de mercado (ex: tendência de alta) e está sendo testado em outro (ex: consolidação lateral).<br><strong>3.</strong> A janela de validação é curta demais, fazendo poucos dias ruins pesarem muito na métrica.`;
        r2Sugestoes = `🔧 <strong>O que fazer agora:</strong><br>• <strong>Não descarte o modelo</strong> — verifique se a Acurácia Direcional está acima de 50%. Se sim, o modelo tem valor mesmo com R² negativo<br>• Atualize os dados CSV com pregões mais recentes<br>• Rode o treinamento novamente para que o modelo se adapte ao regime atual<br>• O MAE atual é de <strong>${maeVal}</strong> — se for menor que a variação diária média, o modelo ainda tem utilidade prática`;
    } else {
        r2Nivel = 'REQUER REVISÃO';
        r2Cor = '#ef4444';
        r2Analise = `O R² de <strong>${r2Pct}%</strong> está significativamente abaixo de zero, indicando que o modelo está tendo dificuldade considerável com o regime atual de mercado. As previsões estão se afastando mais da realidade do que uma simples média histórica faria.`;
        r2Contexto = `<strong>Causas mais prováveis:</strong><br>• O modelo pode estar em <strong>overfitting</strong> — ele memorizou padrões do treino que não se repetem no futuro<br>• Os dados podem conter <strong>ruído excessivo</strong> ou valores faltantes que prejudicam o treinamento<br>• O mercado pode estar em um <strong>regime estruturalmente diferente</strong> do período de treino (ex: crise, mudança regulatória)`;
        r2Sugestoes = `🔧 <strong>Ações recomendadas:</strong><br>• <strong>Retreinar o modelo</strong> com dados mais recentes (atualizar o CSV)<br>• Reduzir o max_depth do XGBoost para combater overfitting<br>• Testar com validação temporal (walk-forward) em vez de split aleatório<br>• Verificar se os dados de entrada estão limpos (sem NaN, sem outliers extremos)<br>• O MAE atual é de <strong>${maeVal}</strong> — use-o como referência ao comparar versões do modelo`;
    }

    const r2Desc = `
        <p>O <strong>R² (R-Quadrado)</strong> mede o quanto da variação total do preço da ITUB4 é explicada pelo modelo XGBoost. É a métrica que responde: <em>"Os indicadores técnicos realmente conseguem prever esse ativo?"</em></p>
        <div class="modal-insights">
            <h4><i class="fa-solid fa-stethoscope"></i> Diagnóstico: <span style="color:${r2Cor}">${r2Nivel}</span></h4>
            <p>${r2Analise}</p>
        </div>
        <div class="modal-insights" style="border-left-color: #818cf8; margin-top: 1rem;">
            <h4><i class="fa-solid fa-magnifying-glass-chart"></i> Contexto</h4>
            <p>${r2Contexto}</p>
        </div>
        <div class="modal-insights" style="border-left-color: ${r2Cor}; margin-top: 1rem;">
            <h4><i class="fa-solid fa-wrench"></i> Próximos Passos</h4>
            <p>${r2Sugestoes}</p>
        </div>
        <div class="modal-insights" style="border-left-color: #64748b; margin-top: 1rem;">
            <h4><i class="fa-solid fa-scale-balanced"></i> Escala de Referência (Mercado Financeiro)</h4>
            <p>
                <strong style="color:#ef4444">Abaixo de -25%</strong> → Modelo precisa de revisão profunda<br>
                <strong style="color:#f97316">-25% a 0%</strong> → Em calibração — comum em mercados voláteis<br>
                <strong style="color:#f59e0b">0% a 15%</strong> → Captura parcial — modelo operacional<br>
                <strong style="color:#22d3ee">15% a 50%</strong> → Bom — acima da maioria dos fundos quant<br>
                <strong style="color:#10b981">Acima de 50%</strong> → Excepcional — raro em renda variável
            </p>
        </div>`;

    // ---- RSI ----
    const rsiVal = lastRow.rsi_14 || 50;
    let rsiZona, rsiCor, rsiAnalise, rsiAcao;
    if (rsiVal >= 70) {
        rsiZona = 'SOBRECOMPRADO';
        rsiCor = '#ef4444';
        rsiAnalise = `O RSI atual de <strong>${rsiVal.toFixed(1)}</strong> está acima de 70, indicando que a ITUB4 subiu <strong>muito rápido</strong> nos últimos 14 pregões. Historicamente, isso precede correções de preço.`;
        rsiAcao = `⚠️ Considere <strong>realizar lucros</strong> ou aguardar confirmação de reversão antes de novas compras.`;
    } else if (rsiVal <= 30) {
        rsiZona = 'SOBREVENDIDO';
        rsiCor = '#10b981';
        rsiAnalise = `O RSI atual de <strong>${rsiVal.toFixed(1)}</strong> está abaixo de 30, indicando que a ITUB4 sofreu <strong>quedas excessivas</strong> nos últimos 14 pregões. Historicamente, isso representa oportunidades de compra.`;
        rsiAcao = `💡 Possível <strong>oportunidade de entrada</strong>. Aguarde sinais de reversão (RSI cruzando acima de 30) para maior segurança.`;
    } else {
        rsiZona = 'NEUTRO';
        rsiCor = '#38bdf8';
        rsiAnalise = `O RSI atual de <strong>${rsiVal.toFixed(1)}</strong> está na zona neutra (entre 30 e 70). Não há sinais extremos de sobrecompra ou sobrevenda. O mercado está em <strong>equilíbrio</strong>.`;
        rsiAcao = `📊 Zona de <strong>indecisão</strong>. Combine com outros indicadores (Bollinger, Volume) para tomar decisões.`;
    }

    const rsiDesc = `
        <p>O <strong>RSI (Relative Strength Index)</strong> é um oscilador de momento que compara a magnitude dos ganhos recentes com as perdas recentes em uma janela de 14 dias.</p>
        <div class="modal-insights">
            <h4><i class="fa-solid fa-stethoscope"></i> Diagnóstico: <span style="color:${rsiCor}">${rsiZona}</span></h4>
            <p>${rsiAnalise}</p>
        </div>
        <div class="modal-insights" style="border-left-color: ${rsiCor}; margin-top: 1rem;">
            <h4><i class="fa-solid fa-hand-point-right"></i> Recomendação</h4>
            <p>${rsiAcao}</p>
        </div>`;

    // ---- Acurácia ----
    const accRaw = metrics['Acurácia'] || 0;
    const accPct = (accRaw * 100).toFixed(1);
    let accNivel, accCor, accAnalise;
    if (accRaw > 0.55) {
        accNivel = 'EDGE FORTE';
        accCor = '#10b981';
        accAnalise = `Com <strong>${accPct}%</strong> de acurácia direcional, o modelo acerta a direção (subir/cair) em mais de 55 a cada 100 operações. Isso representa uma <strong>vantagem estatística (Edge) significativa</strong>. Em séries longas de operações, essa margem gera retornos consistentes acima do mercado aleatório.`;
    } else if (accRaw > 0.50) {
        accNivel = 'EDGE LEVE';
        accCor = '#f59e0b';
        accAnalise = `Com <strong>${accPct}%</strong> de acurácia, o modelo tem uma leve vantagem sobre o acaso (50%). É como um dado levemente viciado a seu favor. Embora a margem seja <strong>pequena</strong>, se combinada com boa gestão de risco (stop loss + take profit), pode gerar retornos positivos no longo prazo.`;
    } else {
        accNivel = 'SEM EDGE';
        accCor = '#ef4444';
        accAnalise = `Com <strong>${accPct}%</strong>, o modelo não possui vantagem direcional. Ele acerta menos do que uma moeda jogada ao ar. Isso <strong>não</strong> significa que o modelo é inútil — o MAE (erro absoluto) pode ainda ser baixo — mas para operações de day trade direcional, não há Edge.`;
    }

    const accDesc = `
        <p>A <strong>Acurácia de Direção</strong> responde: "De todas as vezes que o modelo disse que a ITUB4 ia subir (ou cair), em quantas ele acertou?"</p>
        <div class="modal-insights">
            <h4><i class="fa-solid fa-stethoscope"></i> Diagnóstico: <span style="color:${accCor}">${accNivel}</span></h4>
            <p>${accAnalise}</p>
        </div>
        <div class="modal-insights" style="border-left-color: ${accCor}; margin-top: 1rem;">
            <h4><i class="fa-solid fa-scale-balanced"></i> Escala de Referência</h4>
            <p>
                <strong style="color:#ef4444">Abaixo de 50%</strong> → Pior que cara ou coroa<br>
                <strong style="color:#f59e0b">50% a 55%</strong> → Leve vantagem estatística<br>
                <strong style="color:#10b981">Acima de 55%</strong> → Edge de trading confirmado
            </p>
        </div>`;

    // ---- Preço ----
    const price = lastRow.Close || 0;
    const prevPrice = prevRow.Close || 0;
    const varPct = prevPrice > 0 ? ((price / prevPrice) - 1) * 100 : 0;
    const varDir = varPct >= 0 ? 'alta' : 'queda';
    const varCor = varPct >= 0 ? '#10b981' : '#ef4444';
    const varIcon = varPct >= 0 ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down';
    const totalDias = globalData.history.length;
    
    const priceDesc = `
        <p>O <strong>Último Fechamento</strong> registrado no CSV histórico foi de <strong>R$ ${price.toFixed(2)}</strong>, representando uma <span style="color:${varCor}">${varDir} de ${Math.abs(varPct).toFixed(2)}%</span> em relação ao pregão anterior.</p>
        <div class="modal-insights">
            <h4><i class="fa-solid ${varIcon}"></i> Movimento: <span style="color:${varCor}">${varPct >= 0 ? '+' : ''}${varPct.toFixed(2)}%</span></h4>
            <p>O modelo XGBoost foi treinado com <strong>${totalDias} pregões</strong> de dados limpos. Todas as previsões de D+1 partem deste último fechamento como âncora. O MAE (Erro Médio Absoluto) do modelo indica a margem de variação esperada acima e abaixo deste valor.</p>
        </div>
        <div class="modal-insights" style="border-left-color: #818cf8; margin-top: 1rem;">
            <h4><i class="fa-solid fa-lightbulb"></i> Dica</h4>
            <p>Mantenha o CSV sempre atualizado com os dados mais recentes da B3 para que as previsões reflitam o cenário mais atual do mercado.</p>
        </div>`;

    return {
        mae: { title: "MAE (Erro Médio Absoluto)", icon: "fa-calculator", valId: "val-mae", desc: `<p>O <strong>MAE</strong> mede o erro médio absoluto das previsões do modelo em reais. Ele mostra, em média, quanto as previsões do XGBoost se desviam do preço de fechamento real da ITUB4.</p>
            <div class="modal-insights">
                <h4><i class="fa-solid fa-scale-balanced"></i> Interpretação</h4>
                <p>Um MAE mais baixo indica previsões mais próximas do valor real. Como estamos trabalhando com preços de ações, um MAE menor que R$ 2 costuma ser considerado competitivo para horizontes de curto prazo.</p>
            </div>` },
        rmse: { title: "RMSE (Raiz do Erro Quadrático Médio)", icon: "fa-chart-line", valId: "val-rmse", desc: `<p>O <strong>RMSE</strong> penaliza erros maiores de forma mais forte que o MAE. Ele é útil para avaliar a dispersão das previsões e medir o impacto de outliers.</p>
            <div class="modal-insights">
                <h4><i class="fa-solid fa-bolt"></i> O que significa</h4>
                <p>Como o RMSE dá mais peso a grandes distâncias entre previsão e real, ele é um bom indicador de risco de previsão. Valores menores indicam maior estabilidade do modelo.</p>
            </div>` },
        r2: { title: "Poder de Explicação (R²)", icon: "fa-bullseye", valId: "val-r2", desc: r2Desc },
        rsi: { title: "Índice de Força Relativa (RSI)", icon: "fa-arrow-right-arrow-left", valId: "val-rsi", desc: rsiDesc },
        price: { title: "Último Fechamento", icon: "fa-dollar-sign", valId: "val-price", desc: priceDesc }
    };
}

function updateTimestamp() {
    const now = new Date();
    document.getElementById('last-update').innerText = `Atualizado: ${now.toLocaleTimeString()}`;
}

/**
 * Carrega o JSON de Métricas (itub4_metricas.json)
 */
async function loadMetrics() {
    try {
        const res = await fetch('itub4_metricas.json?' + new Date().getTime());
        if (!res.ok) throw new Error("JSON não encontrado");
        
        const data = await res.json();
        
        // Encontrar o melhor modelo (geralmente XGBoost Otimizado)
        let bestModelKey = Object.keys(data)[0];
        let bestMae = Number.POSITIVE_INFINITY;
        
        for (const [key, metrics] of Object.entries(data)) {
            if (metrics.MAE !== undefined && metrics.MAE < bestMae) {
                bestMae = metrics.MAE;
                bestModelKey = key;
            }
        }
        
        const bestModel = data[bestModelKey] || {};
        globalData.metrics = bestModel;
        
        // Atualizar MAE
        const maeElement = document.getElementById('val-mae');
        const descMae = maeElement.nextElementSibling;
        if (typeof bestModel.MAE === 'number') {
            maeElement.innerText = `R$ ${bestModel.MAE.toFixed(2)}`;
            descMae.innerText = 'Erro médio absoluto da previsão';
        } else {
            maeElement.innerText = 'N/A';
            descMae.innerText = 'Dados indisponíveis.';
        }
        
        // Atualizar RMSE
        const rmseElement = document.getElementById('val-rmse');
        const descRmse = rmseElement.nextElementSibling;
        if (typeof bestModel.RMSE === 'number') {
            rmseElement.innerText = `R$ ${bestModel.RMSE.toFixed(2)}`;
            descRmse.innerText = 'Erro quadrático médio ajustado';
        } else {
            rmseElement.innerText = 'N/A';
            descRmse.innerText = 'Dados indisponíveis.';
        }
        
        // Atualizar R²
        const r2Element = document.getElementById('val-r2');
        const descR2 = r2Element.nextElementSibling; // div.kpi-desc
        if (bestModel['R²']) {
            const r2Value = bestModel['R²'] * 100;
            r2Element.innerText = `${r2Value.toFixed(1)}%`;
            if (r2Value > 50) {
                r2Element.className = 'kpi-value text-success';
                descR2.innerText = 'Excelente! Alto poder preditivo.';
            } else if (r2Value > 0) {
                r2Element.className = 'kpi-value text-warning';
                descR2.innerText = 'Bom. Captura tendências moderadas.';
            } else {
                r2Element.className = 'kpi-value text-danger';
                descR2.innerText = 'Atenção. Preditibilidade baixa.';
            }
        } else {
            r2Element.innerText = 'N/A';
            descR2.innerText = 'Dados insuficientes.';
        }
        
    } catch (error) {
        console.error("Erro ao carregar métricas:", error);
    }
}

/**
 * Carrega os CSVs (Histórico e Previsões)
 */
async function loadChartData() {
    try {
        const timestamp = new Date().getTime();
        const historyPromise = fetch(`itub4_processado_final.csv?${timestamp}`).then(async res => {
            if (!res.ok) throw new Error('CSV histórico não encontrado');
            return res.text();
        });

        const predictionPromise = fetch(`itub4_previsoes_finais.csv?${timestamp}`).then(async res => {
            if (!res.ok) return null;
            return res.text();
        }).catch(() => null);

        const [textHist, textPrev] = await Promise.all([historyPromise, predictionPromise]);
        const resultsHist = Papa.parse(textHist, { header: true, dynamicTyping: true });
        const allData = resultsHist.data.filter(row => row.Date && row.Close);
        globalData.history = allData;

        if (globalData.history.length > 0) {
            const firstDate = formatDateLabel(allData[0].Date);
            const lastDate = formatDateLabel(allData[allData.length - 1].Date);
            const rangeInfo = document.getElementById('training-range-info');
            if (rangeInfo) {
                rangeInfo.innerHTML = `<strong>${firstDate}</strong> até <strong>${lastDate}</strong> (${allData.length} pregões)`;
            }
        }

        updateCurrentPriceAndRSI();

        if (textPrev) {
            const resultsPrev = Papa.parse(textPrev, { header: true, dynamicTyping: true });
            globalData.predictions = resultsPrev.data.filter(row => row.Data && row.Preco_Previsto);
        } else {
            globalData.predictions = [];
        }

        drawCharts();
    } catch (error) {
        console.error('Erro ao carregar CSVs:', error);
        drawCharts();
    }
}

/**
 * Atualiza os Cards de Preço e RSI com o último dado do CSV
 */
function updateCurrentPriceAndRSI() {
    if (globalData.history.length === 0) return;
    
    const lastRow = globalData.history[globalData.history.length - 1];
    const prevRow = globalData.history[globalData.history.length - 2];
    
    // Preço
    if (lastRow.Close) {
        document.getElementById('val-price').innerText = `R$ ${lastRow.Close.toFixed(2)}`;
        
        if (prevRow && prevRow.Close) {
            const varPct = ((lastRow.Close / prevRow.Close) - 1) * 100;
            const descPrice = document.getElementById('desc-price');
            const dateStr = lastRow.Date ? formatDateLabel(lastRow.Date) : '';
            descPrice.innerHTML = `${varPct > 0 ? '+' : ''}${varPct.toFixed(2)}% vs Ontem <span style="opacity: 0.75; font-size: 0.75rem; display: block; margin-top: 4px;">(${dateStr})</span>`;
            descPrice.className = `kpi-desc ${varPct >= 0 ? 'text-success' : 'text-danger'}`;
        }
    }
    
    // RSI
    if (lastRow.rsi_14) {
        const rsiVal = lastRow.rsi_14;
        const rsiEl = document.getElementById('val-rsi');
        const descRsi = document.getElementById('desc-rsi');
        
        rsiEl.innerText = rsiVal.toFixed(1);
        
        if (rsiVal >= 70) {
            rsiEl.className = 'kpi-value text-danger';
            descRsi.innerText = 'Sobrecomprado (Alerta de Venda)';
            descRsi.className = 'kpi-desc text-danger';
        } else if (rsiVal <= 30) {
            rsiEl.className = 'kpi-value text-success';
            descRsi.innerText = 'Sobrevendido (Alerta de Compra)';
            descRsi.className = 'kpi-desc text-success';
        } else {
            rsiEl.className = 'kpi-value';
            descRsi.innerText = 'Zona Neutra';
            descRsi.className = 'kpi-desc';
        }
    }
}

/**
 * Desenha os Gráficos Chart.js
 */
function drawCharts() {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    drawPriceChart();
    drawRsiChart();
    drawTechCharts();
    updateTimestamp();
}

function getFilteredChartData() {
    return filterHistoryByTimeframe(globalData.history, activeChartTimeFrame, activeChartCustomStart, activeChartCustomEnd);
}

function getFilteredTechData() {
    return filterHistoryByTimeframe(globalData.history, activeTechChartTimeFrame, activeTechCustomStart, activeTechCustomEnd);
}

function getFilteredRsiData() {
    return filterHistoryByTimeframe(globalData.history, activeRsiChartTimeFrame, activeRsiCustomStart, activeRsiCustomEnd);
}

function getVisibleHistory() {
    return filterHistoryByTimeframe(globalData.history, activeChartTimeFrame, activeChartCustomStart, activeChartCustomEnd);
}

function getVisibleTechHistory() {
    return filterHistoryByTimeframe(globalData.history, activeTechChartTimeFrame, activeTechCustomStart, activeTechCustomEnd);
}

function getVisibleRsiHistory() {
    return filterHistoryByTimeframe(globalData.history, activeRsiChartTimeFrame, activeRsiCustomStart, activeRsiCustomEnd);
}

window.drawCharts = drawCharts;

window.addEventListener('resize', () => {
    requestAnimationFrame(() => {
        [priceChartInstance, rsiChartInstance, realPriceChartInstance, ma20ChartInstance, xgbForecastChartInstance, predictionPointsChartInstance]
            .filter(Boolean)
            .forEach(chart => {
                chart.resize();
                chart.update('none');
            });
    });
});

function drawPriceChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChartInstance) priceChartInstance.destroy();
    
    const histData = getVisibleHistory();
    const predData = globalData.predictions;
    
    const labels = histData.map(d => formatDateLabel(d.Date));
    const closePrices = histData.map(d => d.Close);
    const ma20 = histData.map(d => d.ma_20 || null);
    const xgbLine = histData.map(d => typeof d.XGBoost_Preco_Previsto === 'number' ? d.XGBoost_Preco_Previsto : null);
    const actualPriceByLabel = new Map(histData.map(d => [formatDateLabel(d.Date), d.Close]));
    
    let predLabels = [];
    let xgbFuture = [];
    let predPointData = [];
    
    if (predData.length > 0) {
        predLabels = predData.map(d => formatDateLabel(d.Data));
        labels.push(...predLabels);

        xgbFuture = predData.map(d => d.Preco_Previsto);
        predPointData = new Array(histData.length).fill(null).concat(predData.map(d => d.Preco_Previsto));
    }
    
    const xgbHistorical = xgbLine;
    const xgbFutureOnly = new Array(histData.length).fill(null).concat(xgbFuture);

    // Lógica da Previsão Ajustada pelo Sentimento (Híbrida)
    let xgbFutureAdjustedOnly = [];
    if (predData.length > 0) {
        const sentimentScore = window.currentSentimentScore || 0;
        // Amplificador visual: Garante que a linha ciano "fuja" da sombra da vermelha mesmo com sentimento fraco
        let visualSentiment = sentimentScore;
        if (Math.abs(sentimentScore) > 0.01 && Math.abs(sentimentScore) < 0.3) {
             visualSentiment = sentimentScore > 0 ? 0.3 : -0.3; // Espaçamento mínimo
        }
        const ajusteDiario = visualSentiment * 0.015; 
        
        const xgbFutureAdjusted = xgbFuture.map((preco, index) => {
            const diasFuturos = index + 1; // 1 a 10
            const fatorAjuste = 1 + (ajusteDiario * diasFuturos);
            return preco * fatorAjuste;
        });
        
        xgbFutureAdjustedOnly = new Array(histData.length).fill(null).concat(xgbFutureAdjusted);
        
        // Chamar atualização do painel de confluência
        setTimeout(() => updateConfluencePanel(), 100);
    }

    const futureAreaPlugin = {
        id: 'futureArea',
        beforeDraw: (chart) => {
            const histLen = histData.length;
            if (!chart.scales.x || histLen <= 1 || !predData || predData.length === 0) return;
            const xScale = chart.scales.x;
            const area = chart.chartArea;
            const start = xScale.getPixelForValue(histLen - 0.5);
            if (start >= area.right) return;
            chart.ctx.save();
            chart.ctx.fillStyle = 'rgba(245, 158, 11, 0.15)'; // Vibrant Orange background
            chart.ctx.fillRect(start, area.top, area.right - start, area.bottom - area.top);
            chart.ctx.font = 'bold 15px Inter, sans-serif';
            chart.ctx.fillStyle = '#f59e0b'; // Vibrant Orange text
            chart.ctx.textAlign = 'left';
            chart.ctx.fillText('🌟 PREVISÕES XGBOOST (10 DIAS)', start + 10, area.top + 24);
            
            // Highlight final prediction if available
            if (predData && predData.length > 0) {
                const finalPred = predData[predData.length - 1];
                chart.ctx.font = 'bold 18px Inter, sans-serif';
                chart.ctx.fillStyle = '#10b981'; // Green text
                chart.ctx.fillText(`Alvo: R$ ${finalPred.Preco_Previsto.toFixed(2)}`, start + 10, area.top + 50);
            }
            
            chart.ctx.restore();
        }
    };

    priceChartInstance = new Chart(ctx, {
        type: 'line',
        plugins: [futureAreaPlugin],
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Preço Real (ITUB4)',
                    data: closePrices,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.08)',
                    borderWidth: 3,
                    tension: 0.22,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBorderWidth: 2,
                    pointHoverBackgroundColor: '#2563eb'
                },
                {
                    label: 'Média Móvel (20d)',
                    data: ma20,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.05)',
                    borderWidth: 2,
                    borderDash: [6, 4],
                    tension: 0.16,
                    pointRadius: 0,
                    pointHoverRadius: 6
                },
                {
                    label: 'XGBoost Histórico',
                    data: xgbHistorical,
                    borderColor: '#fb923c',
                    backgroundColor: 'rgba(251, 146, 60, 0.08)',
                    borderWidth: 2,
                    borderDash: [4, 4],
                    tension: 0.1,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'XGBoost Futuro (10 dias)',
                    data: xgbFutureOnly,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 37, 37, 0.12)',
                    borderWidth: 4,
                    borderDash: [10, 6],
                    tension: 0.12,
                    spanGaps: true,
                    pointRadius: 0,
                    pointHoverRadius: 8,
                    fill: false
                },
                {
                    label: 'Ajuste c/ Sentimento Notícias',
                    data: xgbFutureAdjustedOnly,
                    borderColor: '#06b6d4', // Cyan
                    backgroundColor: 'rgba(6, 182, 212, 0.15)',
                    borderWidth: 3,
                    borderDash: [3, 3],
                    tension: 0.12,
                    spanGaps: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: {
                        target: '-1',
                        above: 'rgba(16, 185, 129, 0.15)', // Verde se ajustado > normal
                        below: 'rgba(239, 68, 68, 0.15)'   // Vermelho se ajustado < normal
                    }
                },
                {
                    label: 'Pontos de Previsão',
                    data: predPointData,
                    borderColor: '#8b5cf6',
                    borderWidth: 0,
                    pointRadius: predData.length > 0 ? 12 : 0,
                    pointStyle: 'rectRot',
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 3,
                    pointHoverRadius: 16,
                    pointHoverBorderWidth: 2,
                    showLine: false,
                    clip: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            elements: {
                line: { borderCapStyle: 'round' },
                point: { hoverRadius: 6 }
            },
            interaction: { mode: 'index', intersect: false },
            onClick: (e, activeElements, chart) => {
                if (!activeElements || activeElements.length === 0) return;
                
                const index = activeElements[0].index;
                const histLen = globalData.history.length;
                
                if (index >= histLen) {
                    const predIdx = index - histLen;
                    if (globalData.predictions && globalData.predictions[predIdx]) {
                        try {
                            mostrarDetalhesPrevisao(globalData.predictions[predIdx], predIdx + 1);
                        } catch (err) {
                            console.error("Erro ao mostrar detalhes:", err);
                        }
                    }
                } else if (index === histLen - 1) {
                    const lastReal = globalData.history[index];
                    if (lastReal) {
                        mostrarDetalhesHistorico(lastReal);
                    }
                }
            },
            onHover: (e, activeElements, chart) => {
                const canvas = e.native ? e.native.target : chart.canvas;
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    if (index >= globalData.history.length - 1) {
                        canvas.style.cursor = 'pointer';
                        return;
                    }
                }
                canvas.style.cursor = 'default';
            },
            layout: {
                padding: { top: 10, right: 16, bottom: 6, left: 8 }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 16,
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 14, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 12,
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : '',
                        label: (context) => {
                            const value = context.parsed.y;
                            return value !== null ? `${context.dataset.label}: R$ ${value.toFixed(2)}` : context.dataset.label;
                        },
                        footer: (items) => {
                            if (!items || items.length === 0) return '';
                            const label = formatDateLabel(items[0].label);
                            const actual = actualPriceByLabel.get(label);
                            if (actual !== undefined && actual !== null) {
                                return `Preço Real: R$ ${actual.toFixed(2)}`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
    window.priceChartInstance = priceChartInstance;
    setupPriceChartWheelZoom();
}

function mostrarDetalhesHistorico(realInfo) {
    const modalOverlay = document.getElementById('kpi-modal');
    const dateLabel = realInfo.Date ? formatDateLabel(realInfo.Date) : 'N/A';
    const price = typeof realInfo.Close === 'number' ? realInfo.Close : Number(realInfo.Close || 0);
    const prevRow = globalData.history.length > 1 ? globalData.history[globalData.history.length - 2] : null;
    const prevPrice = prevRow && typeof prevRow.Close === 'number' ? prevRow.Close : Number(prevRow?.Close || 0);
    const diff = prevRow ? price - prevPrice : null;
    const diffText = diff === null ? '' : ` (${diff >= 0 ? '+' : '-'}R$ ${Math.abs(diff).toFixed(2)})`;

    document.getElementById('modal-title').innerText = 'Último Fechamento Real';
    document.getElementById('modal-icon').innerHTML = `<i class="fa-solid fa-chart-line"></i>`;
    document.getElementById('modal-value').innerText = `R$ ${price.toFixed(2)}`;
    document.getElementById('modal-value').className = 'modal-value-large text-primary';
    document.getElementById('modal-body').innerHTML = `
        <p>Este ponto corresponde ao último fechamento real registrado no histórico, antes do início da projeção XGBoost.</p>
        <div class="modal-insights">
            <h4><i class="fa-solid fa-calendar-day"></i> Data</h4>
            <p><strong>${dateLabel}</strong></p>
        </div>
        <div class="modal-insights">
            <h4><i class="fa-solid fa-dollar-sign"></i> Preço real</h4>
            <p><strong>R$ ${price.toFixed(2)}</strong>${diffText}</p>
        </div>
        <div class="modal-insights" style="border-left-color: #60a5fa; margin-top: 1rem;">
            <h4><i class="fa-solid fa-info-circle"></i> Contexto</h4>
            <p>Este é o último fechamento conhecido. A projeção XGBoost subsequente parte desse valor como referência para o próximo período.</p>
        </div>
    `;
    if (modalOverlay) modalOverlay.classList.add('active');
}

function setupPriceChartWheelZoom() {
    const canvas = document.getElementById('priceChart');
    if (!canvas || canvas.__chartWheelZoomAttached) return;

    const handleWheel = (event) => {
        const chart = Chart.getChart(canvas) || window.priceChartInstance;
        if (!chart || !chart.scales || !chart.scales.x) return;

        event.preventDefault();
        const totalPoints = chart.data.labels.length;
        const currentMin = Number.isFinite(chart.options.scales.x.min) ? chart.options.scales.x.min : 0;
        const currentMax = Number.isFinite(chart.options.scales.x.max) ? chart.options.scales.x.max : totalPoints - 1;
        const currentRange = Math.max(5, currentMax - currentMin);
        const zoomStep = Math.max(1, Math.round(currentRange * 0.18));
        const newRange = event.deltaY < 0 ? Math.max(5, currentRange - zoomStep) : Math.min(totalPoints - 1, currentRange + zoomStep);

        const rect = canvas.getBoundingClientRect();
        const xPixel = event.clientX - rect.left;
        let centerValue = chart.scales.x.getValueForPixel ? chart.scales.x.getValueForPixel(xPixel) : currentMin + currentRange / 2;
        if (typeof centerValue !== 'number' || isNaN(centerValue)) {
            centerValue = currentMin + currentRange / 2;
        }

        let newMin = Math.round(centerValue - newRange / 2);
        let newMax = Math.round(centerValue + newRange / 2);
        if (newMin < 0) {
            newMin = 0;
            newMax = newRange;
        }
        if (newMax > totalPoints - 1) {
            newMax = totalPoints - 1;
            newMin = Math.max(0, newMax - newRange);
        }

        chart.options.scales.x.min = newMin;
        chart.options.scales.x.max = newMax;
        chart.update('none');
    };

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    canvas.addEventListener('dblclick', () => {
        const chart = Chart.getChart(canvas) || window.priceChartInstance;
        if (!chart || !chart.options || !chart.options.scales || !chart.options.scales.x) return;
        chart.options.scales.x.min = undefined;
        chart.options.scales.x.max = undefined;
        chart.update('none');
    });
    canvas.__chartWheelZoomAttached = true;
}

function drawTechCharts() {
    const histData = getVisibleTechHistory();
    const predData = globalData.predictions;
    if (!histData || histData.length === 0) return;

    const labels = histData.map(d => formatDateLabel(d.Date));
    const closePrices = histData.map(d => d.Close);
    const ma20 = histData.map(d => d.ma_20 || null);
    const xgbLine = histData.map(d => typeof d.XGBoost_Preco_Previsto === 'number' ? d.XGBoost_Preco_Previsto : null);

    let xgbFuture = [];
    let predPointData = [];

    if (predData.length > 0) {
        xgbFuture = predData.map(d => d.Preco_Previsto);
        predPointData = new Array(histData.length).fill(null).concat(predData.map(d => d.Preco_Previsto));
    }

    const allLabels = labels.concat(predData.map(d => formatDateLabel(d.Data)));

    const realCtx = document.getElementById('realPriceChart').getContext('2d');
    if (realPriceChartInstance) realPriceChartInstance.destroy();
    realPriceChartInstance = new Chart(realCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Preço Real (ITUB4)',
                    data: closePrices,
                    borderColor: '#1d4ed8',
                    backgroundColor: 'rgba(29, 78, 216, 0.16)',
                    borderWidth: 3,
                    tension: 0.16,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            layout: {
                padding: { top: 10, right: 16, bottom: 6, left: 8 }
            },
            plugins: {
                zoom: {
                    pan: { enabled: true, mode: 'x' },
                    zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 14, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 12,
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : '',
                        label: (context) => {
                            const value = context.parsed.y;
                            return value !== null ? `${context.dataset.label}: R$ ${value.toFixed(2)}` : null;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            }
        }
    });
    window.realPriceChartInstance = realPriceChartInstance;

    const maCtx = document.getElementById('ma20Chart').getContext('2d');
    if (ma20ChartInstance) ma20ChartInstance.destroy();
    ma20ChartInstance = new Chart(maCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Média Móvel (20d)',
                    data: ma20,
                    borderColor: '#d97706',
                    borderWidth: 3,
                    borderDash: [6, 4],
                    tension: 0.16,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            layout: {
                padding: { top: 10, right: 16, bottom: 6, left: 8 }
            },
            plugins: {
                zoom: {
                    pan: { enabled: true, mode: 'x' },
                    zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 14, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 12,
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : '',
                        label: (context) => {
                            const value = context.parsed.y;
                            return value !== null ? `${context.dataset.label}: R$ ${value.toFixed(2)}` : null;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            }
        }
    });
    window.ma20ChartInstance = ma20ChartInstance;

    const xgbCtx = document.getElementById('xgbForecastChart').getContext('2d');
    if (xgbForecastChartInstance) xgbForecastChartInstance.destroy();
    const xgbHistoricalTech = xgbLine;
    const xgbFutureTech = new Array(histData.length).fill(null).concat(xgbFuture);

    // Linha Ciano: Previsão Ajustada por Sentimento (mesma lógica do gráfico principal)
    let xgbFutureTechAdjusted = [];
    if (predData.length > 0) {
        const sentimentScore = window.currentSentimentScore || 0;
        let visualSentiment = sentimentScore;
        if (Math.abs(sentimentScore) > 0.01 && Math.abs(sentimentScore) < 0.3) {
            visualSentiment = sentimentScore > 0 ? 0.3 : -0.3;
        }
        const ajusteDiario = visualSentiment * 0.015;
        const adjusted = xgbFuture.map((preco, index) => {
            const diasFuturos = index + 1;
            const fatorAjuste = 1 + (ajusteDiario * diasFuturos);
            return preco * fatorAjuste;
        });
        xgbFutureTechAdjusted = new Array(histData.length).fill(null).concat(adjusted);
    }

    const futureAreaPluginTech = {
        id: 'futureAreaTech',
        beforeDraw: (chart) => {
            const histLen = histData.length;
            if (!chart.scales.x || histLen <= 1 || !predData || predData.length === 0) return;
            const xScale = chart.scales.x;
            const area = chart.chartArea;
            const start = xScale.getPixelForValue(histLen - 0.5);
            if (start >= area.right) return;
            chart.ctx.save();
            chart.ctx.fillStyle = 'rgba(185, 28, 28, 0.08)';
            chart.ctx.fillRect(start, area.top, area.right - start, area.bottom - area.top);
            chart.ctx.font = '600 13px Inter, sans-serif';
            chart.ctx.fillStyle = 'rgba(185, 28, 28, 0.95)';
            chart.ctx.textAlign = 'left';
            chart.ctx.fillText('Previsão futura (10 dias)', start + 10, area.top + 24);
            chart.ctx.restore();
        }
    };

    xgbForecastChartInstance = new Chart(xgbCtx, {
        type: 'line',
        plugins: [futureAreaPluginTech],
        data: {
            labels: allLabels,
            datasets: [
                {
                    label: 'XGBoost Histórico',
                    data: xgbHistoricalTech,
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.12)',
                    borderWidth: 2,
                    borderDash: [4, 4],
                    tension: 0.16,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'XGBoost Futuro (IA)',
                    data: xgbFutureTech,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.12)',
                    borderWidth: 4,
                    borderDash: [10, 6],
                    tension: 0.16,
                    spanGaps: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: false
                },
                {
                    label: 'Ajuste c/ Sentimento Notícias',
                    data: xgbFutureTechAdjusted,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6, 182, 212, 0.10)',
                    borderWidth: 3,
                    borderDash: [3, 3],
                    tension: 0.16,
                    spanGaps: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: { mode: 'index', intersect: false },
            elements: {
                line: { borderCapStyle: 'round' }
            },
            layout: {
                padding: { top: 10, right: 16, bottom: 6, left: 8 }
            },
            plugins: {
                zoom: {
                    pan: { enabled: true, mode: 'x' },
                    zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 14, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 12,
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : '',
                        label: (context) => {
                            const value = context.parsed.y;
                            return value !== null ? `${context.dataset.label}: R$ ${value.toFixed(2)}` : null;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
    window.xgbForecastChartInstance = xgbForecastChartInstance;

    const ptsCtx = document.getElementById('predictionPointsChart').getContext('2d');
    if (predictionPointsChartInstance) predictionPointsChartInstance.destroy();
    predictionPointsChartInstance = new Chart(ptsCtx, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                {
                    label: 'Pontos de Previsão',
                    data: predPointData,
                    borderColor: '#8b5cf6',
                    borderWidth: 0,
                    pointRadius: 12,
                    pointStyle: 'rectRot',
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 3,
                    pointHoverRadius: 14,
                    showLine: false
                },
                {
                    label: 'Linha de Conexão da Previsão',
                    data: xgbFutureTech,
                    borderColor: 'rgba(139, 92, 246, 0.45)',
                    borderWidth: 2,
                    tension: 0.16,
                    pointRadius: 0,
                    spanGaps: true,
                    fill: false,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            layout: {
                padding: { top: 10, right: 16, bottom: 6, left: 8 }
            },
            plugins: {
                zoom: {
                    pan: { enabled: true, mode: 'x' },
                    zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' }
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 14, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 12,
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : '',
                        label: (context) => {
                            const value = context.parsed.y;
                            if (value === null || value === undefined) return null;
                            return `${context.dataset.label}: R$ ${value.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            }
        }
    });
    window.predictionPointsChartInstance = predictionPointsChartInstance;

    // Adicionar zoom via scroll em todos os 4 graficos tecnicos
    ['realPriceChart', 'ma20Chart', 'xgbForecastChart', 'predictionPointsChart'].forEach(canvasId => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        if (canvas.__techWheelZoom) return;
        canvas.addEventListener('wheel', (event) => {
            const instance = Chart.getChart(canvas);
            if (!instance || !instance.scales || !instance.scales.x) return;
            event.preventDefault();
            const total = instance.data.labels.length;
            const currentMin = Number.isFinite(instance.options.scales.x.min) ? instance.options.scales.x.min : 0;
            const currentMax = Number.isFinite(instance.options.scales.x.max) ? instance.options.scales.x.max : total - 1;
            const currentRange = Math.max(5, currentMax - currentMin);
            const zoomStep = Math.max(1, Math.round(currentRange * 0.18));
            const newRange = event.deltaY < 0 ? Math.max(5, currentRange - zoomStep) : Math.min(total - 1, currentRange + zoomStep);
            const rect = canvas.getBoundingClientRect();
            const xPixel = event.clientX - rect.left;
            let centerValue = instance.scales.x.getValueForPixel ? instance.scales.x.getValueForPixel(xPixel) : currentMin + currentRange / 2;
            if (typeof centerValue !== 'number' || isNaN(centerValue)) centerValue = currentMin + currentRange / 2;
            let newMin = Math.round(centerValue - newRange / 2);
            let newMax = Math.round(centerValue + newRange / 2);
            if (newMin < 0) { newMin = 0; newMax = newRange; }
            if (newMax > total - 1) { newMax = total - 1; newMin = Math.max(0, newMax - newRange); }
            instance.options.scales.x.min = newMin;
            instance.options.scales.x.max = newMax;
            instance.update('none');
        }, { passive: false });
        canvas.addEventListener('dblclick', () => {
            const instance = Chart.getChart(canvas);
            if (!instance || !instance.options || !instance.options.scales || !instance.options.scales.x) return;
            instance.options.scales.x.min = undefined;
            instance.options.scales.x.max = undefined;
            instance.update('none');
        });
        canvas.__techWheelZoom = true;
    });
}

function drawRsiChart() {
    const ctx = document.getElementById('rsiChart').getContext('2d');
    if (rsiChartInstance) rsiChartInstance.destroy();
    
    const histData = getVisibleRsiHistory();
    const labels = histData.map(d => formatDateLabel(d.Date));
    const rsiData = histData.map(d => d.rsi_14);
    
    const rsiZonesPlugin = {
        id: 'rsiZones',
        beforeDraw: (chart) => {
            const ctx = chart.ctx;
            const xScale = chart.scales.x;
            const yScale = chart.scales.y;
            if (!xScale || !yScale) return;
            const area = chart.chartArea;
            const top = area.top;
            const bottom = area.bottom;
            const y70 = yScale.getPixelForValue(70);
            const y30 = yScale.getPixelForValue(30);

            ctx.save();
            ctx.fillStyle = 'rgba(239, 68, 68, 0.08)';
            ctx.fillRect(area.left, top, area.right - area.left, y70 - top);
            ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
            ctx.fillRect(area.left, y30, area.right - area.left, bottom - y30);
            ctx.restore();
        }
    };

    rsiChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'RSI (14 Períodos)',
                    data: rsiData,
                    borderColor: '#818cf8',
                    backgroundColor: 'rgba(129, 140, 248, 0.16)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }
            ]
        },
        plugins: [rsiZonesPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { size: 13, family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12, family: "'Inter', sans-serif" },
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        title: (items) => items.length ? formatDateLabel(items[0].label) : ''
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function(value) { return formatDateLabel(this.getLabelForValue(value)); }
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: {
                        color: (context) => {
                            if (context.tick.value === 70) return 'rgba(239, 68, 68, 0.5)'; // Vermelho (Sobrecomprado)
                            if (context.tick.value === 30) return 'rgba(16, 185, 129, 0.5)'; // Verde (Sobrevendido)
                            if (context.tick.value === 50) return 'rgba(255, 255, 255, 0.2)'; // Centro
                            return 'rgba(255, 255, 255, 0.05)';
                        },
                        lineWidth: (context) => {
                            return [30, 50, 70].includes(context.tick.value) ? 2 : 1;
                        }
                    },
                    ticks: {
                        stepSize: 10
                    }
                }
            }
        }
    });
    window.rsiChartInstance = rsiChartInstance;

    const canvas = document.getElementById('rsiChart');
    if (canvas && !canvas.__rsiWheelZoomAttached) {
        canvas.addEventListener('wheel', (event) => {
            const chart = Chart.getChart(canvas);
            if (!chart || !chart.scales || !chart.scales.x) return;
            event.preventDefault();
            const totalPoints = chart.data.labels.length;
            const currentMin = Number.isFinite(chart.options.scales.x.min) ? chart.options.scales.x.min : 0;
            const currentMax = Number.isFinite(chart.options.scales.x.max) ? chart.options.scales.x.max : totalPoints - 1;
            const currentRange = Math.max(5, currentMax - currentMin);
            const zoomStep = Math.max(1, Math.round(currentRange * 0.18));
            const newRange = event.deltaY < 0 ? Math.max(5, currentRange - zoomStep) : Math.min(totalPoints - 1, currentRange + zoomStep);
            const rect = canvas.getBoundingClientRect();
            const xPixel = event.clientX - rect.left;
            let centerValue = chart.scales.x.getValueForPixel ? chart.scales.x.getValueForPixel(xPixel) : currentMin + currentRange / 2;
            if (typeof centerValue !== 'number' || isNaN(centerValue)) centerValue = currentMin + currentRange / 2;
            let newMin = Math.round(centerValue - newRange / 2);
            let newMax = Math.round(centerValue + newRange / 2);
            if (newMin < 0) { newMin = 0; newMax = newRange; }
            if (newMax > totalPoints - 1) { newMax = totalPoints - 1; newMin = Math.max(0, newMax - newRange); }
            chart.options.scales.x.min = newMin;
            chart.options.scales.x.max = newMax;
            chart.update('none');
        }, { passive: false });
        canvas.addEventListener('dblclick', () => {
            const chart = Chart.getChart(canvas);
            if (!chart || !chart.options || !chart.options.scales || !chart.options.scales.x) return;
            chart.options.scales.x.min = undefined;
            chart.options.scales.x.max = undefined;
            chart.update('none');
        });
        canvas.__rsiWheelZoomAttached = true;
    }
}

/**
 * Setup do Painel de Treinamento (com Toggle Switch)
 */
let isRetraining = false;

function setupTrainingPanel() {
    const btnRetrain = document.getElementById('btn-retrain');
    const startInput = document.getElementById('train-start');
    const endInput = document.getElementById('train-end');
    const trainControls = document.querySelectorAll('#train-timeframe-controls .chart-toggle-btn');

    if (!btnRetrain) return;

    function setDatesByPeriod(period) {
        const today = new Date();
        const endStr = today.toISOString().split('T')[0];
        
        if (period === 'all') {
            startInput.value = '2000-12-21';
            endInput.value = endStr;
            startInput.disabled = true;
            endInput.disabled = true;
        } else if (period === 'custom') {
            startInput.disabled = false;
            endInput.disabled = false;
        } else {
            const start = new Date(today);
            const days = { '7d': 7, '30d': 30, '90d': 90, '180d': 180, '365d': 365 }[period];
            if (days) start.setDate(start.getDate() - days);
            startInput.value = start.toISOString().split('T')[0];
            endInput.value = endStr;
            startInput.disabled = true;
            endInput.disabled = true;
        }
        updatePregoesCount();
    }

    if (trainControls && trainControls.length > 0) {
        trainControls.forEach(btn => {
            btn.addEventListener('click', () => {
                trainControls.forEach(item => item.classList.remove('active'));
                btn.classList.add('active');
                setDatesByPeriod(btn.dataset.trainPeriod);
            });
        });
        // Init
        setDatesByPeriod('all');
    }

    function updatePregoesCount() {
        const countSpan = document.getElementById('pregoes-count');
        if (!countSpan) return;
        
        const activeBtn = document.querySelector('#train-timeframe-controls .chart-toggle-btn.active');
        if (activeBtn && activeBtn.dataset.trainPeriod === 'all') {
            countSpan.textContent = '';
            countSpan.style.display = 'none';
        } else {
            const start = startInput.value;
            const end = endInput.value;
            if (start && end && new Date(start) <= new Date(end)) {
                const days = calculateBusinessDays(start, end);
                countSpan.textContent = `(~${days} pregões)`;
                countSpan.style.display = 'inline-block';
            } else {
                countSpan.style.display = 'none';
            }
        }
    }

    [startInput, endInput].forEach(input => {
        input.addEventListener('change', updatePregoesCount);
    });

    // Botão Retreinar
    btnRetrain.addEventListener('click', async () => {
        if (isRetraining) return; // Impedir duplo clique

        const start = startInput.value;
        const end = endInput.value;

        if (!start || !end) {
            alert('Por favor, selecione as datas de início e fim.');
            return;
        }

        isRetraining = true;
        
        // Sincronizar painel de sentimento com as datas de treinamento
        const sentimentStart = document.getElementById('sentiment-start');
        const sentimentEnd = document.getElementById('sentiment-end');
        if (sentimentStart && sentimentEnd) {
            sentimentStart.value = start;
            sentimentEnd.value = end;
            // Atualizar UI dos botoes de sentimento para "Personalizado"
            const sentimentBtns = document.querySelectorAll('[data-sentiment-period]');
            sentimentBtns.forEach(b => b.classList.remove('active'));
            const customBtn = document.querySelector('[data-sentiment-period="custom"]');
            if(customBtn) customBtn.classList.add('active');
            const customDatesEl = document.getElementById('sentiment-custom-dates');
            if(customDatesEl) customDatesEl.style.display = 'flex';
        }
        
        // Disparar a busca de noticias paralelamente ao treinamento
        fetchSentimentByPeriod(start, end);

        const overlay = document.getElementById('loading-overlay');
        const statusDiv = document.getElementById('training-status');
        
        if (overlay) overlay.classList.add('active');
        if (statusDiv) {
            statusDiv.className = 'training-status loading';
            statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Iniciando treinamento do modelo XGBoost...';
        }

        try {
            const response = await fetch('/retrain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start, end })
            });

            const result = await response.json();

            if (result.status === 'success') {
                if (statusDiv) {
                    statusDiv.className = 'training-status success';
                    statusDiv.innerHTML = '<i class="fa-solid fa-circle-check"></i> Treinamento concluído com sucesso!';
                }
                
                // Recarregar os dados para atualizar os gráficos
                await Promise.all([
                    loadMetrics(),
                    loadChartData()
                ]);
                updateTimestamp();
                
                setTimeout(() => {
                    if (statusDiv) {
                        statusDiv.className = 'training-status';
                        statusDiv.innerHTML = '';
                    }
                }, 5000);
            } else {
                throw new Error(result.message || 'Erro desconhecido');
            }
        } catch (error) {
            if (statusDiv) {
                statusDiv.className = 'training-status error';
                statusDiv.innerHTML = '<i class="fa-solid fa-exclamation-circle"></i> Erro: ' + error.message;
            }
        } finally {
            isRetraining = false;
            if (overlay) overlay.classList.remove('active');
            const btn = document.getElementById('btn-retrain');
            if (btn) btn.disabled = false;
        }
    });
}

function mostrarDetalhesPrevisao(predInfo, diaNum) {
    const modalOverlay = document.getElementById('kpi-modal');
    
    document.getElementById('modal-title').innerText = `Detalhes da Previsão - Dia ${diaNum}`;
    document.getElementById('modal-icon').innerHTML = `<i class="fa-solid fa-robot"></i>`;
    document.getElementById('modal-value').innerText = `R$ ${predInfo.Preco_Previsto.toFixed(2)}`;
    document.getElementById('modal-value').className = `modal-value-large text-primary`;
    
    try {
        const retorno = predInfo.Retorno_Previsto || 0;
        const direcao = retorno >= 0 ? "alta" : "queda";
        const cor = retorno >= 0 ? "#10b981" : "#ef4444";
        const setinha = retorno >= 0 ? "📈" : "📉";
        const preco = predInfo.Preco_Previsto ? Number(predInfo.Preco_Previsto) : 0;

        const history = Array.isArray(globalData.history) ? globalData.history : [];
        const lastReal = history.length > 0 ? history[history.length - 1] : null;
        const lastRealDate = lastReal ? formatDateLabel(lastReal.Date) : 'N/A';
        const lastRealValue = lastReal && typeof lastReal.Close === 'number' ? `R$ ${lastReal.Close.toFixed(2)}` : 'N/A';
        const deltaValue = lastReal && typeof lastReal.Close === 'number' ? preco - lastReal.Close : null;
        const deltaSign = deltaValue === null ? '' : deltaValue >= 0 ? '+' : '-';
        const deltaFormatted = deltaValue === null ? '' : ` (${deltaSign}R$ ${Math.abs(deltaValue).toFixed(2)})`;
        
        document.getElementById('modal-value').innerText = `R$ ${preco.toFixed(2)}`;
        document.getElementById('modal-value').className = `modal-value-large text-primary`;
        
        document.getElementById('modal-body').innerHTML = `
            <p>A Inteligência Artificial (XGBoost) analisou os indicadores recentes e calculou uma projeção para a data <strong>${formatDateLabel(predInfo.Data) || 'Futura'}</strong>.</p>
            <div class="modal-insights">
                <h4><i class="fa-solid fa-chart-line"></i> Último fechamento real conhecido</h4>
                <p>Data: <strong>${lastRealDate}</strong></p>
                <p>Preço real: <strong>${lastRealValue}</strong>${deltaFormatted ? `<span style="color:${deltaValue >= 0 ? '#10b981' : '#ef4444'}">${deltaFormatted}</span>` : ''}</p>
            </div>
            <div class="modal-insights">
                <h4><i class="fa-solid fa-calculator"></i> O Cálculo do Algoritmo</h4>
                <p>O modelo processou mais de 30 variáveis padronizadas (como Z-Score do RSI, Bandas de Bollinger, Volatilidade e Tendência). Ele percorreu milhares de Árvores de Decisão otimizadas para identificar padrões similares que ocorreram no histórico completo (desde 2000).</p>
                <p>O resultado matemático projeta uma <strong>${direcao} acumulada de <span style="color:${cor}">${Math.abs(retorno).toFixed(2)}%</span></strong> em relação ao último fechamento real conhecido.</p>
            </div>
            <div class="modal-insights" style="border-left-color: #f59e0b; margin-top: 1rem;">
                <h4><i class="fa-solid fa-triangle-exclamation"></i> Como Interpretar</h4>
                <p>Este valor representa um "alvo estatístico mais provável" ${setinha}. <br><br><strong>Atenção:</strong> Lembre-se de verificar a <em>Acurácia Direcional</em> e o <em>MAE (Erro Médio Absoluto)</em> no painel superior. O MAE estabelece exatamente a margem de oscilação esperada em Reais (R$) para esta projeção.</p>
            </div>
        `;

        modalOverlay.classList.add('active');
    } catch (err) {
        console.error("Erro renderizando modal:", err);
        alert("Ocorreu um erro ao tentar exibir os dados desta previsão.");
    }
}

function calculateBusinessDays(startDate, endDate) {
    let count = 0;
    // Corrige fuso horário para garantir que pega a data certa no JS
    let curDate = new Date(startDate + "T00:00:00");
    const end = new Date(endDate + "T00:00:00");
    
    if (isNaN(curDate) || isNaN(end) || curDate > end) return 0;
    
    while (curDate <= end) {
        const dayOfWeek = curDate.getDay();
        if (dayOfWeek !== 0 && dayOfWeek !== 6) count++;
        curDate.setDate(curDate.getDate() + 1);
    }
    return count;
}

function setupAnalystDiary() {
    const btnSave = document.getElementById('btn-save-diary');
    const textarea = document.getElementById('analyst-diary');
    const timeline = document.getElementById('diary-timeline');
    const sentimentBtns = document.querySelectorAll('.btn-sentiment');
    
    if (!btnSave || !textarea || !timeline) return;

    const savedDraft = localStorage.getItem('itub4_analyst_diary');
    if (savedDraft) {
        textarea.value = savedDraft;
    }

    textarea.addEventListener('input', () => {
        localStorage.setItem('itub4_analyst_diary', textarea.value);
    });

    let currentSentiment = 'neutro';

    sentimentBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            sentimentBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSentiment = btn.getAttribute('data-sentiment');
        });
    });

    const renderTimeline = () => {
        const entries = JSON.parse(localStorage.getItem('itub4_diary_entries') || '[]');
        timeline.innerHTML = '';
        
        if (entries.length === 0) {
            timeline.innerHTML = '<div class="diary-empty">Nenhum lançamento no diário ainda.</div>';
            return;
        }

        // Sort by timestamp descending
        entries.sort((a, b) => b.timestamp - a.timestamp).forEach(entry => {
            const card = document.createElement('div');
            card.className = 'diary-card';
            
            let badgeStyle = '';
            let badgeIcon = '';
            if (entry.sentiment === 'alta') { badgeStyle = 'color: #10b981; border-color: #10b981;'; badgeIcon = 'fa-arrow-trend-up'; }
            else if (entry.sentiment === 'baixa') { badgeStyle = 'color: #ef4444; border-color: #ef4444;'; badgeIcon = 'fa-arrow-trend-down'; }
            else { badgeStyle = 'color: #9ca3af; border-color: #9ca3af;'; badgeIcon = 'fa-minus'; }

            card.innerHTML = `
                <div class="diary-card-header">
                    <div class="diary-meta">
                        <span class="diary-date"><i class="fa-regular fa-clock"></i> ${entry.dateFormatted}</span>
                        <div style="display: flex; gap: 8px; align-items: center; margin-top: 6px;">
                            <span class="diary-price-badge" style="${badgeStyle}"><i class="fa-solid ${badgeIcon}"></i> Viés: ${entry.sentiment.toUpperCase()}</span>
                            ${entry.price ? `<span class="diary-price-badge"><i class="fa-solid fa-tag"></i> ITUB4: R$ ${entry.price}</span>` : ''}
                        </div>
                    </div>
                    <button class="btn-delete-diary" data-id="${entry.id}" title="Excluir anotação"><i class="fa-solid fa-trash-can"></i></button>
                </div>
                <div class="diary-content">${entry.content}</div>
            `;
            timeline.appendChild(card);
        });

        // Add delete events
        document.querySelectorAll('.btn-delete-diary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-id');
                if (confirm('Tem certeza que deseja excluir esta anotação?')) {
                    let updated = JSON.parse(localStorage.getItem('itub4_diary_entries') || '[]');
                    updated = updated.filter(item => item.id !== id);
                    localStorage.setItem('itub4_diary_entries', JSON.stringify(updated));
                    renderTimeline();
                }
            });
        });
    };

    btnSave.addEventListener('click', (e) => {
        e.preventDefault();
        const content = textarea.value.trim();
        if (!content) {
            alert('Escreva alguma coisa antes de salvar.');
            return;
        }

        const now = new Date();
        const dateFormatted = now.toLocaleString('pt-BR');
        
        // Obter preço atual do globalData se disponível
        let currentPrice = null;
        if (globalData.history && globalData.history.length > 0) {
            currentPrice = globalData.history[globalData.history.length - 1].Close.toFixed(2);
        }

        const newEntry = {
            id: Date.now().toString(),
            timestamp: Date.now(),
            dateFormatted: dateFormatted,
            sentiment: currentSentiment,
            content: content,
            price: currentPrice
        };

        const entries = JSON.parse(localStorage.getItem('itub4_diary_entries') || '[]');
        entries.push(newEntry);
        localStorage.setItem('itub4_diary_entries', JSON.stringify(entries));

        // Reset form
        textarea.value = '';
        localStorage.removeItem('itub4_analyst_diary');
        sentimentBtns.forEach(b => b.classList.remove('active'));
        document.querySelector('.btn-sentiment[data-sentiment="neutro"]').classList.add('active');
        currentSentiment = 'neutro';

        renderTimeline();
    });

    // Initial render
    renderTimeline();
}

/**
 * Atualiza o painel de Confluência de Sinais baseado na IA (XGBoost) e no Sentimento das Notícias.
 */
window.updateConfluencePanel = function() {
    const badgeEl = document.getElementById('confluence-badge');
    const descEl = document.getElementById('confluence-desc');
    
    if (!badgeEl || !descEl) return;
    
    // Obter última previsão XGBoost e o preço atual
    if (!globalData || !globalData.predictions || globalData.predictions.length === 0 || !globalData.history || globalData.history.length === 0) {
        return; // Aguarda dados
    }
    
    const currentPrice = globalData.history[globalData.history.length - 1].Close;
    const finalPred = globalData.predictions[globalData.predictions.length - 1].Preco_Previsto;
    
    let aiTrend = 0; // 0=neutro, 1=alta, -1=baixa
    const change = (finalPred - currentPrice) / currentPrice;
    
    // Deixando mais sensível: qualquer variação de > 0.1% já ativa alerta
    if (change > 0.001) aiTrend = 1;
    else if (change < -0.001) aiTrend = -1;
    
    // Obter sentimento (já atualizado no renderSentimentData)
    const sentimentScore = window.currentSentimentScore || 0;
    let sentTrend = 0;
    if (sentimentScore >= 0.05) sentTrend = 1;
    else if (sentimentScore <= -0.05) sentTrend = -1;
    
    // Preencher o Raio-X Expansível
    const confAiDetail = document.getElementById('conf-ai-detail');
    const confAiSub = document.getElementById('conf-ai-sub');
    const confNewsDetail = document.getElementById('conf-news-detail');
    const confNewsSub = document.getElementById('conf-news-sub');

    if (confAiDetail) {
        const changePct = (change * 100).toFixed(2);
        confAiDetail.innerHTML = `Alvo R$ ${finalPred.toFixed(2)} (<span style="color:${aiTrend===1?'#10b981':aiTrend===-1?'#ef4444':'#f59e0b'}">${changePct > 0 ? '+'+changePct : changePct}%</span>)`;
        confAiSub.innerHTML = `Base: Preço Atual de R$ ${currentPrice.toFixed(2)}`;
    }
    if (confNewsDetail) {
        confNewsDetail.innerHTML = `Score Médio: <span style="color:${sentTrend===1?'#10b981':sentTrend===-1?'#ef4444':'#f59e0b'}">${sentimentScore.toFixed(3)}</span>`;
        confNewsSub.innerHTML = `Analisado via Processamento de Linguagem Natural`;
    }

    // Configurar o gatilho de clique expansível (se ainda não tiver)
    const confPanel = document.getElementById('confluence-panel');
    const confDetails = document.getElementById('confluence-details');
    const confArrow = document.getElementById('confluence-arrow');
    if (confPanel && confDetails && !confPanel.dataset.clickableSet) {
        confPanel.dataset.clickableSet = "true";
        confPanel.addEventListener('click', () => {
            if (confDetails.style.display === 'none') {
                confDetails.style.display = 'block';
                confArrow.style.transform = 'rotate(180deg)';
                confPanel.style.borderBottomLeftRadius = '0';
                confPanel.style.borderBottomRightRadius = '0';
            } else {
                confDetails.style.display = 'none';
                confArrow.style.transform = 'rotate(0deg)';
                confPanel.style.borderRadius = '';
            }
        });
    }

    // Lógica de Confluência
    if (aiTrend === 1 && sentTrend === 1) {
        badgeEl.innerHTML = '<i class="fa-solid fa-angles-up"></i> COMPRA FORTE';
        badgeEl.style.background = 'rgba(16, 185, 129, 0.2)';
        badgeEl.style.color = '#10b981';
        badgeEl.style.border = '1px solid #10b981';
        descEl.innerHTML = `A <strong>Matemática da IA</strong> prevê ALTA (+${(change*100).toFixed(2)}%) e as <strong>Notícias</strong> estão OTIMISTAS. Sinal mútuo de crescimento.`;
    } 
    else if (aiTrend === -1 && sentTrend === -1) {
        badgeEl.innerHTML = '<i class="fa-solid fa-angles-down"></i> VENDA FORTE';
        badgeEl.style.background = 'rgba(239, 68, 68, 0.2)';
        badgeEl.style.color = '#ef4444';
        badgeEl.style.border = '1px solid #ef4444';
        descEl.innerHTML = `A <strong>Matemática da IA</strong> prevê QUEDA (${(change*100).toFixed(2)}%) e as <strong>Notícias</strong> estão PESSIMISTAS. Sinal mútuo de retração.`;
    }
    else if (aiTrend === 1 && sentTrend === -1) {
        badgeEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ALERTA DE RISCO';
        badgeEl.style.background = 'rgba(245, 158, 11, 0.2)';
        badgeEl.style.color = '#f59e0b';
        badgeEl.style.border = '1px solid #f59e0b';
        descEl.innerHTML = `Divergência: <strong>IA</strong> prevê ALTA (+${(change*100).toFixed(2)}%), mas as <strong>Notícias</strong> estão PESSIMISTAS. Mercado pode contrariar os gráficos por pânico.`;
    }
    else if (aiTrend === -1 && sentTrend === 1) {
        badgeEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ALERTA DE RISCO';
        badgeEl.style.background = 'rgba(245, 158, 11, 0.2)';
        badgeEl.style.color = '#f59e0b';
        badgeEl.style.border = '1px solid #f59e0b';
        descEl.innerHTML = `Divergência: <strong>IA</strong> prevê QUEDA (${(change*100).toFixed(2)}%), mas as <strong>Notícias</strong> estão OTIMISTAS. Mercado pode ignorar a análise técnica.`;
    }
    else {
        badgeEl.innerHTML = '<i class="fa-solid fa-scale-balanced"></i> SINAL NEUTRO';
        badgeEl.style.background = 'rgba(148, 163, 184, 0.2)';
        badgeEl.style.color = '#94a3b8';
        badgeEl.style.border = '1px solid #94a3b8';
        descEl.innerHTML = 'Falta de confluência direcional clara entre a Matemática (IA) e o Humor das Notícias.';
    }

    // --- ATUALIZAÇÃO DINÂMICA DO GRÁFICO CIANO (GRÁFICO PRINCIPAL) ---
    if (window.priceChartInstance && window.priceChartInstance.data && window.priceChartInstance.data.datasets) {
        const adjustedDataset = window.priceChartInstance.data.datasets.find(ds => ds.label === 'Ajuste c/ Sentimento Notícias');
        if (adjustedDataset && globalData.history && globalData.predictions) {
            const histData = getVisibleHistory();
            const predData = globalData.predictions;
            if (predData.length > 0) {
                const xgbFuture = predData.map(d => d.Preco_Previsto);
                
                let visualSentiment = sentimentScore;
                if (Math.abs(sentimentScore) > 0.01 && Math.abs(sentimentScore) < 0.3) {
                     visualSentiment = sentimentScore > 0 ? 0.3 : -0.3; 
                }
                const ajusteDiario = visualSentiment * 0.015; 
                
                const xgbFutureAdjusted = xgbFuture.map((preco, index) => {
                    const diasFuturos = index + 1;
                    const fatorAjuste = 1 + (ajusteDiario * diasFuturos);
                    return preco * fatorAjuste;
                });
                
                adjustedDataset.data = new Array(histData.length).fill(null).concat(xgbFutureAdjusted);
                window.priceChartInstance.update('none');
            }
        }
    }

    // --- ATUALIZAÇÃO DINÂMICA DO GRÁFICO CIANO (ABA ANÁLISE TÉCNICA) ---
    if (window.xgbForecastChartInstance && window.xgbForecastChartInstance.data && window.xgbForecastChartInstance.data.datasets) {
        const adjustedTechDataset = window.xgbForecastChartInstance.data.datasets.find(ds => ds.label === 'Ajuste c/ Sentimento Notícias');
        if (adjustedTechDataset && globalData.predictions) {
            const predData = globalData.predictions;
            const histLen = getVisibleTechHistory().length;
            if (predData.length > 0 && histLen > 0) {
                const xgbFuture = predData.map(d => d.Preco_Previsto);

                let visualSentiment = sentimentScore;
                if (Math.abs(sentimentScore) > 0.01 && Math.abs(sentimentScore) < 0.3) {
                    visualSentiment = sentimentScore > 0 ? 0.3 : -0.3;
                }
                const ajusteDiario = visualSentiment * 0.015;

                const xgbFutureAdjusted = xgbFuture.map((preco, index) => {
                    const fatorAjuste = 1 + (ajusteDiario * (index + 1));
                    return preco * fatorAjuste;
                });

                adjustedTechDataset.data = new Array(histLen).fill(null).concat(xgbFutureAdjusted);
                window.xgbForecastChartInstance.update('none');
            }
        }
    }
};

/**
 * Configura os botões de recolher/expandir (colapsar) dos painéis.
 */
function setupCollapsiblePanels() {
    const collapseBtns = document.querySelectorAll('.btn-collapse');
    collapseBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Evita cliques indesejados no elemento pai (como no confluência panel)
            const targetId = btn.dataset.target;
            const targetEl = document.getElementById(targetId);
            if (!targetEl) return;
            
            const isCollapsed = targetEl.classList.toggle('panel-collapsed');
            
            // Tratamento especial para o wrapper de confluência
            if (targetId === 'confluence-panel-wrapper') {
                targetEl.classList.toggle('confluence-collapsed', isCollapsed);
            }
            
            // Atualizar o ícone e texto do botão
            if (isCollapsed) {
                btn.innerHTML = `<i class="fa-solid fa-chevron-down"></i> Expandir`;
            } else {
                btn.innerHTML = `<i class="fa-solid fa-chevron-up"></i> Recolher`;
                
                // Redesenhar/atualizar os gráficos para garantir o redimensionamento após expandir
                setTimeout(() => {
                    if (targetId === 'chart-price' && priceChartInstance) {
                        priceChartInstance.resize();
                        priceChartInstance.update('none');
                    } else if (targetId === 'chart-rsi' && rsiChartInstance) {
                        rsiChartInstance.resize();
                        rsiChartInstance.update('none');
                    }
                }, 50);
            }
        });
    });
}
