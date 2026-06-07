# Sistema de Inteligência Financeira para ITUB4
## Documentação Técnica — Versão Atualizada

---

### 1. Visão Geral e Filosofia do Sistema

O dashboard é construído sobre um princípio fundamental: **única fonte de verdade, múltiplas visualizações**.

Todos os gráficos, em todas as abas, partem do mesmo conjunto de dados (`globalData`) e do mesmo estado de sentimento (`window.currentSentimentScore`). Isso garante que, ao mudar o período de sentimento ou retreinar o modelo, **todas as visualizações se atualizam em cascata**, sem inconsistências.

#### Princípio de Interligação

```
┌──────────────────────────────────────────────────────────────────┐
│                        DADOS CENTRALIZADOS                       │
│  globalData.history   →  Histórico de preços e indicadores       │
│  globalData.predictions → 10 previsões futuras do XGBoost        │
│  globalData.metrics   →  MAE, RMSE, R², Acurácia Direcional      │
│  window.currentSentimentScore → Score NLP das notícias (-1 a +1) │
└──────────────────────────┬───────────────────────────────────────┘
                           │  Alimenta
        ┌──────────────────┼───────────────────┐
        ▼                  ▼                   ▼
  Aba Principal      Aba Análise Técnica    Aba Previsão IA
  priceChart         realPriceChart         xgbForecastChart ◄─ Linha Ciano
  (Histórico +       ma20Chart              predictionPointsChart
   Linha Ciano)      xgbForecastChart       (todos leem globalData)
                     predictionPointsChart
                           │
                           └──► Painel de Confluência
                                (cruza IA + Sentimento)
```

---

### 2. Algoritmo de Machine Learning

#### 2.1 Pipeline de Processamento de Dados

1. **Carregamento e Limpeza**
   - Carrega `itub4_historico.csv` com preços OHLCV desde 21/12/2000.
   - Remove valores faltantes e garante cronologia correta.
   - Realiza o cruzamento com dados de cotação do Dólar obtidos do Banco Central (BCB) utilizando **Left Join** (para não descartar dias recentes da B3 quando a API do BCB estiver atrasada ou ausente). Cotações nulas do dólar no fim da série são tratadas com propagação (*forward fill*).

2. **Engenharia de Features (>50 indicadores)**
   - Médias Móveis (SMA 20/50/200, EMA 9/21)
   - RSI (14 períodos), Bandas de Bollinger, Estocástico, MACD
   - Indicadores de volume (OBV, VWAP)
   - Diferenças percentuais, lagged features, momentum e Z-Scores

3. **Padronização**
   - Z-Score (StandardScaler) em todas as features → média 0, desvio padrão 1.

4. **Seleção de Features**
   - Correlação de Pearson + Informação Mútua (`mutual_info_regression`).
   - Reduz ruído e overfitting mantendo os preditores mais poderosos.

5. **Modelagem XGBoost**
   - Três variantes (Rápido, Base, Otimizado) com `TimeSeriesSplit`.
   - Validação cruzada temporal evita vazamento de dados futuros.

6. **Avaliação**
   - MAE, RMSE, R² e Acurácia Direcional → `itub4_metricas.json`.

7. **Projeção Futura**
   - 10 dias úteis projetados → `itub4_previsoes_finais.csv`.

---

### 3. Arquitetura do Frontend — Interligação das Abas

#### 3.1 Estado Global (única fonte de verdade)

O arquivo `js/main.js` mantém dois objetos globais que alimentam **todos** os gráficos simultaneamente:

```javascript
// Cache de dados — partilhado por TODOS os gráficos
let globalData = {
    history: [],       // CSV itub4_processado_final.csv
    predictions: [],   // CSV itub4_previsoes_finais.csv
    metrics: {}        // JSON itub4_metricas.json
};

// Score de sentimento — partilhado pelo painel de confluência e pela Linha Ciano
window.currentSentimentScore = 0;  // Atualizado por renderSentimentData()
window.currentSentimentClass  = 'Neutro';
```

Quando qualquer um destes valores muda (novo sentimento, novo retreinamento), a função `updateConfluencePanel()` é invocada e atualiza:
- O painel de Confluência de Sinais (badge + descrição)
- A linha ciano no gráfico principal (`priceChartInstance`)
- A linha ciano no gráfico técnico (`xgbForecastChartInstance`)

#### 3.2 Gráficos por Aba — O que cada um mostra

| Aba | Gráfico | Dados | Interligação com Sentimento |
|-----|---------|-------|----------------------------|
| **Dashboard Principal** | `priceChart` | Histórico real + MM20 + XGBoost histórico + XGBoost futuro (vermelho) + **Linha Ciano** (azul tracejada) | ✅ Atualiza linha ciano via `updateConfluencePanel` |
| **Dashboard Principal** | `rsiChart` | RSI (14 períodos), zonas 30/70 coloridas | ❌ Indicador técnico puro |
| **Análise Técnica** | `realPriceChart` | Preço real ITUB4 | ❌ Visualização isolada |
| **Análise Técnica** | `ma20Chart` | Média Móvel 20 dias | ❌ Visualização isolada |
| **Análise Técnica** | `xgbForecastChart` | XGBoost histórico + XGBoost futuro (vermelho) + **Linha Ciano** | ✅ Atualiza linha ciano via `updateConfluencePanel` |
| **Análise Técnica** | `predictionPointsChart` | Pontos de previsão (losangos roxos) + linha de conexão | ❌ Visualização isolada |

#### 3.3 A Linha Ciano — Projeção Híbrida (IA + Sentimento)

A linha azul ciano tracejada representa a **Previsão Ajustada pelo Humor do Mercado**. É calculada no frontend com base matemática simples e transparente:

```javascript
// Amplificador Visual: garante separação mínima visível entre as linhas
let visualSentiment = sentimentScore;
if (Math.abs(sentimentScore) > 0.01 && Math.abs(sentimentScore) < 0.3) {
    visualSentiment = sentimentScore > 0 ? 0.3 : -0.3; // mínimo garantido
}

const ajusteDiario = visualSentiment * 0.015; // 1.5% máx por dia de acumulação

// Para cada dia futuro (1 a 10):
const fatorAjuste = 1 + (ajusteDiario * diasFuturos);
const precoAjustado = precoXGBoost * fatorAjuste;
```

**Leitura visual do Cone de Risco:**
- Linha **vermelha** acima da ciano → sentimento pessimista (notícias indicam risco de queda além da IA)
- Linha **ciano** acima da vermelha → sentimento otimista (notícias indicam potencial adicional de alta)
- A área entre as linhas é colorida (verde = bullish, vermelho = bearish)

**Onde aparece:**
- Gráfico principal (`priceChart`) — aba Dashboard
- Gráfico `xgbForecastChart` — aba Análise Técnica

**Comportamento em Diferentes Períodos (Resiliência Temporal):**
Para evitar que a linha ciano suma ou fique deslocada incorretamente ao aplicar zooms ou trocar o período visual do gráfico (1M, 3M, 1A, etc.):
1. O preenchimento da linha usa o histórico visível de cada gráfico (`getVisibleHistory()` e `getVisibleTechHistory()`) para calcular o deslocamento (padding de nulos) dinamicamente.
2. A filtragem por timeframe usa a última data disponível no CSV (`anchorDate`) como referência no lugar do relógio do sistema local, prevenindo desalinhamentos por fusos horários ou atrasos de atualização de dados da B3.
3. O dataset do gráfico de análise técnica está alinhado sob o mesmo nome de label (`'Ajuste c/ Sentimento Notícias'`), o que garante a correta sincronia e evita erros no console no callback do `updateConfluencePanel()`.

#### 3.4 Painel de Confluência de Sinais

Localizado acima do gráfico principal, cruza dois vetores de informação em tempo real:

| Vetor | Fonte | Threshold |
|-------|-------|-----------|
| **Sinal Matemático (IA)** | Variação % entre preço atual e último alvo XGBoost | > +0.1% = Alta / < -0.1% = Baixa |
| **Humor do Mercado (NLP)** | `window.currentSentimentScore` | > +0.05 = Otimista / < -0.05 = Pessimista |

**Matriz de Decisão:**

| IA | Notícias | Sinal Emitido |
|----|---------|---------------|
| Alta | Otimistas | 🟢 **COMPRA FORTE** |
| Baixa | Pessimistas | 🔴 **VENDA FORTE** |
| Alta | Pessimistas | 🟡 **ALERTA DE RISCO** |
| Baixa | Otimistas | 🟡 **ALERTA DE RISCO** |
| Neutro (qualquer) | Neutro (qualquer) | ⚪ **SINAL NEUTRO** |

O painel é **clicável** e abre o **"Raio-X da Confluência"** com valores numéricos exatos. Os indicadores contidos no Raio-X ("Sinal Matemático (IA)" e "Humor do Mercado (Notícias)") possuem um ícone de ajuda (sinal de interrogação) que mostra uma descrição detalhada de seu significado ao posicionar o cursor do mouse.

---

### 4. Correlações entre Gráficos — O que Muda Juntos

Ao alterar qualquer variável de entrada, os seguintes componentes se atualizam automaticamente:

#### 4.1 Mudar período do Termômetro de Sentimento
→ `fetchSentimentByPeriod()` → `renderSentimentData()` → atualiza `window.currentSentimentScore` → `updateConfluencePanel()`:
- Badge do painel de confluência
- Descrição textual da confluência
- Linha ciano no `priceChart` (aba Principal)
- Linha ciano no `xgbForecastChart` (aba Análise Técnica)

#### 4.2 Retreinar o Modelo (novo período de treinamento)
→ `servidor.py` executa `itub4_analise_completa.py` → gera novos CSVs → `loadChartData()` → `globalData` atualizado → redesenha **todos** os gráficos → `updateConfluencePanel()` re-executa.

#### 4.3 Mudar período temporal dos gráficos
- Controles `timeframe-controls` (Principal) → `drawCharts()` → redesenha `priceChart` + `rsiChart`
- Controles `tech-timeframe-controls` (Análise Técnica) → `drawTechCharts()` → redesenha os 4 gráficos técnicos
- Os controles são **independentes entre abas** (zoom do RSI não afeta o gráfico de preço, por exemplo)

---

### 5. Componentes do Sistema

#### 5.1 Backend e Modelagem
- `itub4_analise_completa.py`: Pipeline completo de ML. Aceita datas customizadas via argparse para retreinamento dinâmico.
- `servidor.py`: Servidor HTTP Python com rotas:
  - `GET /` → serve o dashboard
  - `POST /retrain` → dispara retreinamento com datas customizadas
  - `POST /sentiment` → busca notícias por período (Alpha Vantage ou Yahoo)
  - `GET /ping` → heartbeat do frontend
  - `POST /shutdown` → encerramento gracioso

#### 5.2 Frontend
- `index.html`: Interface com 4 seções navegáveis (Dashboard Principal, Indicadores, Análise Técnica, Previsão IA), painel de confluência e termômetro de sentimento.
- `css/style.css`: Design glassmorphism, dark mode, animações CSS e responsividade.
- `js/main.js`: Lógica central (~2500 linhas):
  - Carregamento e parsing de CSV/JSON
  - Renderização de 6 gráficos Chart.js
  - Zoom por scroll com estado persistente
  - Filtros temporais por aba
  - Heartbeat, modais de detalhe, diário do analista
  - Painel de confluência e linha híbrida ciano

#### 5.3 Mecanismo de Heartbeat
O servidor Python auto-encerra após 120 segundos (2 minutos) sem receber pings do navegador (evitando desligamentos acidentais durante recarregamentos). Implementado com:
- `setInterval(() => fetch('/ping'), 2000)` no frontend
- Monitor de última atividade no servidor Python (`elapsed > 120` em `servidor.py`)

#### 5.4 Zoom Inteligente e Persistente
- Zoom via scroll do mouse em todos os gráficos
- Estado preservado entre minimizado e modal expandido
- Duplo clique para reset de zoom
- Controles independentes por aba (RSI tem seu próprio timeframe)

---

### 6. Análise de Sentimento — Modo Duplo e Limiares

O sistema detecta automaticamente a disponibilidade da chave API e escolhe a melhor fonte, aplicando limiares de decisão (thresholds) específicos para cada uma no frontend e backend:

#### Modo Primário: Alpha Vantage NEWS_SENTIMENT
- Endpoint: `https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=ITUB`
- Até 50 notícias por requisição com filtro histórico real (`time_from`/`time_to`)
- Score pré-calculado pela IA da Alpha Vantage (escala -1.0 a +1.0)
- Thresholds de Sentimento: `≥ +0.05` Otimismo / `≤ -0.05` Pessimismo / entre: Neutro
- Plano gratuito: 25 requisições/dia
- Configuração: inserir chave em `config.py` (arquivo ignorado pelo Git)

#### Modo Fallback: Yahoo Finance + VADER NLP
- ~10 notícias recentes via `yfinance`
- Processamento NLP local com `vaderSentiment`
- Thresholds de Sentimento: `≥ +0.15` Otimismo / `≤ -0.15` Pessimismo (escala do VADER adaptada no frontend e backend)
- Indicadores visuais: badge verde (Alpha Vantage) ou amarelo (Yahoo)

---

### 6.1 Modo Alternativo: Dashboard Streamlit

Além do frontend principal em HTML/CSS/JS servido por `servidor.py`, o script de processamento `itub4_analise_completa.py` possui um modo de visualização alternativo e independente utilizando a biblioteca **Streamlit**.
- Execução: `python itub4_analise_completa.py --modo-streamlit`
- Porta padrão: `8501`
- Recursos: Exibição interativa com Plotly de preços históricos, evolução de Z-Scores de padronização, e previsões do XGBoost.

---

### 7. Arquivos de Dados

| Arquivo | Conteúdo | Gerado por |
|---------|----------|------------|
| `itub4_historico.csv` | OHLCV histórico bruto | Yahoo Finance |
| `itub4_processado_final.csv` | Histórico + 50+ indicadores técnicos | `itub4_analise_completa.py` |
| `itub4_previsoes_finais.csv` | 10 dias de previsão XGBoost | `itub4_analise_completa.py` |
| `itub4_metricas.json` | MAE, RMSE, R², Acurácia | `itub4_analise_completa.py` |
| `itub4_sentimento.json` | Cache do último sentimento | `servidor.py` |
| `config.py` | Chave Alpha Vantage (não versionado) | Usuário |
| `config.example.py` | Template de configuração | Repositório |

---

### 8. Fluxo de Operação

```
1. start_dashboard.bat
   └─► Python: itub4_analise_completa.py (treina modelo, gera CSVs)
   └─► Python: servidor.py (sobe na porta 8000)
   └─► Chrome: abre http://localhost:8000

2. Frontend inicializa:
   ├─ loadMetrics()      → lê itub4_metricas.json → KPI cards
   ├─ loadChartData()    → lê CSVs → globalData → desenha gráficos
   ├─ setupSentimentFilters() → busca notícias (padrão: 1 semana)
   │     └─► renderSentimentData() → currentSentimentScore
   │           └─► updateConfluencePanel() → badge + linha ciano
   └─ setupTrainingPanel(), setupAnalystDiary(), etc.

3. Usuário interage:
   ├─ Muda período sentimento → linha ciano atualiza em TODOS os gráficos
   ├─ Clica em ponto de previsão → modal com detalhes do dia
   ├─ Retreat modelo → todos os gráficos redesenhados
   └─ Zoom/filtros → independentes por aba, estado persistente

4. Encerramento:
   └─ Usuário fecha navegador → heartbeat falha → servidor auto-encerra
```

---

### 9. Sugestões de Melhoria Futuras

- **Correlação Histórica Sentimento→Preço**: Incorporar `currentSentimentScore` como feature no XGBoost para que o modelo aprenda a correlação histórica entre humor do mercado e variações de preço.
- **Upgrade Alpha Vantage Premium**: 75+ requisições/dia para análises mais frequentes.
- **Integração WebSocket B3**: Cotações em tempo real para predições intraday.
- **Alertas e Notificações**: E-mail ou push notification em variações expressivas.
- **Otimização Bayesiana de Hiperparâmetros**: Refino automático do R² do modelo.
- **Histórico de Confluência**: Registrar sinais anteriores (Compra/Venda) para auditoria e backtesting da qualidade das confluências.

---
*Documentação atualizada — Arquitetura de interligação entre abas e gráficos documentada. Linha Ciano (Previsão Híbrida) implementada no Dashboard Principal e na aba Análise Técnica.*