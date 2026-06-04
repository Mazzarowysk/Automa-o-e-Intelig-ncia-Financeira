# ANCHORED SUMMARY — ITUB4 Quantum Dashboard

## Estado Atual do Projeto

Sistema de inteligência financeira para análise e previsão de ações ITUB4 com dashboard interativo.

### Stack
- **Backend/ML:** Python 3.12, XGBoost, pandas, scikit-learn, yfinance, vaderSentiment
- **Servidor:** Python `http.server` customizado com rotas REST
- **Frontend:** HTML5 + Vanilla CSS (glassmorphism dark mode) + JavaScript puro + Chart.js
- **APIs Externas:** Alpha Vantage NEWS_SENTIMENT (primária) / Yahoo Finance (fallback)

---

## Arquitetura de Estado (Single Source of Truth)

```
globalData { history[], predictions[], metrics{} }
window.currentSentimentScore   →  Score NLP -1 a +1
window.currentSentimentClass   →  "Otimista" | "Neutro" | "Pessimista"
```

Ao mudar qualquer parâmetro → `updateConfluencePanel()` propaga para:
- Badge e texto do painel de confluência
- Linha ciano no `priceChart` (Dashboard Principal)
- Linha ciano no `xgbForecastChartInstance` (Aba Análise Técnica)

---

## Gráficos Ativos e Interligação

| Canvas ID | Aba | Sentimento? | Controle Temporal |
|-----------|-----|-------------|-------------------|
| `priceChart` | Principal | ✅ linha ciano | `timeframe-controls` |
| `rsiChart` | Principal | ❌ | `rsi-timeframe-controls` |
| `realPriceChart` | Análise Técnica | ❌ | `tech-timeframe-controls` |
| `ma20Chart` | Análise Técnica | ❌ | `tech-timeframe-controls` |
| `xgbForecastChart` | Análise Técnica | ✅ linha ciano | `tech-timeframe-controls` |
| `predictionPointsChart` | Análise Técnica | ❌ | `tech-timeframe-controls` |

---

## Funcionalidades Implementadas

- [x] Pipeline XGBoost com >50 features e TimeSeriesSplit
- [x] Previsão de 10 dias futuros
- [x] Dashboard com 4 abas (Principal, Indicadores, Análise Técnica, Previsão IA)
- [x] Zoom por scroll em todos os gráficos (estado persistente)
- [x] Controles temporais independentes por aba
- [x] Análise de sentimento NLP (Alpha Vantage + fallback Yahoo/VADER)
- [x] Painel de Confluência de Sinais (IA × Notícias) — expansível com Raio-X
- [x] Linha Ciano (Previsão Híbrida) no Dashboard Principal
- [x] Linha Ciano (Previsão Híbrida) na Aba Análise Técnica (`xgbForecastChart`)
- [x] Cone de risco colorido entre linha vermelha e ciano
- [x] Amplificador visual mínimo (separação garantida ≥ 0.30 de sentimento visual)
- [x] Retreinamento dinâmico com período customizável
- [x] Heartbeat (auto-shutdown ao fechar navegador)
- [x] Diário do Analista com persistência localStorage
- [x] Modais de detalhe por ponto de previsão (clique no gráfico)
- [x] Badge dinâmico de fonte de dados (Alpha Vantage vs Yahoo Finance)

---

## Arquivos Relevantes

| Arquivo | Papel |
|---------|-------|
| `js/main.js` | Toda a lógica frontend (~2500 linhas) |
| `index.html` | Estrutura HTML das 4 abas e componentes |
| `css/style.css` | Estilos glassmorphism dark mode |
| `servidor.py` | Servidor HTTP + rotas REST |
| `itub4_analise_completa.py` | Pipeline ML + geração de CSVs |
| `itub4_processado_final.csv` | Histórico + indicadores técnicos |
| `itub4_previsoes_finais.csv` | 10 previsões futuras XGBoost |
| `itub4_metricas.json` | MAE, RMSE, R², Acurácia |
| `itub4_sentimento.json` | Cache de sentimento NLP |
| `config.py` | Chave Alpha Vantage (não versionado) |

---

## Função Central de Propagação

```javascript
window.updateConfluencePanel = function() {
    // 1. Calcula tendência IA (variação % do XGBoost vs preço atual)
    // 2. Lê window.currentSentimentScore
    // 3. Emite badge: COMPRA FORTE / VENDA FORTE / ALERTA / NEUTRO
    // 4. Atualiza linha ciano no priceChart (Principal)
    // 5. Atualiza linha ciano no xgbForecastChartInstance (Análise Técnica)
}
```

Chamada por: `renderSentimentData()` (toda vez que o sentimento muda) e `drawCharts()` (após redesenho dos gráficos).

---

*Atualizado em 2026-06-04 — Linha ciano implementada nas duas abas com gráficos. Documentações SYSTEM_DOCUMENTATION.md e documentacao_tecnica.md atualizadas.*