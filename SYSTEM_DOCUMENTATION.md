# Sistema de Inteligência Financeira para ITUB4
## Documentação Técnica para Apresentação Acadêmica

### 1. Descrição do Algoritmo

#### Objetivo
Prever a direção e o valor futuro das ações ITUB4 com alta acurácia utilizando dados históricos e indicadores técnicos, fornecendo uma interface interativa e avançada para visualização das previsões.

#### Passos do Algoritmo

1. **Carregamento e Limpeza de Dados**
   - Carrega o dataset histórico `itub4_historico.csv` contendo preços de abertura, alta, baixa, fechamento e volume.
   - Remove linhas com valores faltantes e garante a cronologia correta dos dados.

2. **Criação de Características (Features)**
   - Gera mais de 50 indicadores técnicos incluindo:
     - Médias Móveis Simples (SMA) e Exponenciais (EMA)
     - Índice de Força Relativa (RSI)
     - Bandas de Bollinger e Oscilador Estocástico
     - MACD (Moving Average Convergence Divergence)
     - Indicadores de volume (OBV, VWAP)
     - Diferenças percentuais, lagged features e momentum.

3. **Padronização**
   - Aplica Z-score (StandardScaler) para normalizar todas as features, garantindo média 0 e desvio padrão 1.

4. **Seleção de Características**
   - Utiliza técnicas combinadas: Correlação com a variável alvo e Informação Mútua (mutual_info_regression) para capturar relações não lineares.
   - Seleciona as características mais relevantes para reduzir ruído e overfitting.

5. **Modelagem com XGBoost**
   - Treina três variantes do modelo XGBoost Regressor (Rápido, Base, Otimizado).
   - Utiliza `TimeSeriesSplit` para validação cruzada temporal, evitando vazamento de dados futuros.

6. **Avaliação de Desempenho**
   - Calcula métricas (MAE, RMSE, R² e Acurácia de Direção).
   - Armazena resultados em `itub4_metricas.json`.

7. **Geração de Previsões Futuras e Projeção Híbrida**
   - Utiliza o melhor modelo treinado para prever os próximos 10 dias úteis de preços (`itub4_previsoes_finais.csv`).
   - A previsão puramente matemática é traçada no gráfico em vermelho.
   - Uma **Projeção Ajustada pelo Sentimento** (linha azul pontilhada) é calculada dinamicamente no frontend: ela desvia a projeção matemática baseando-se no grau de otimismo ou pessimismo atual das notícias da Alpha Vantage.

8. **Dashboard Interativo (HTML/JS/CSS)**
   - Sistema de visualização próprio, leve e interativo, focado na experiência do usuário (UX).
   - Painel exclusivo de **Análise de Confluência de Sinais**, que emite alertas automatizados (Compra Forte, Venda Forte, Alerta de Risco) baseados no cruzamento entre a tendência da IA matemática e o sentimento humano.
   - Gráficos integrados utilizando **Chart.js** (Preços, Previsões Híbridas, RSI, Médias Móveis).
   - Funcionalidade avançada de **Zoom com Scroll do Mouse** sincronizada e persistente.

#### Tecnologias Utilizadas
- **Backend/IA**: Python 3.12, pandas, numpy, scikit-learn, xgboost.
- **Servidor HTTP**: Servidor local Python (`http.server`) com mecanismo de **Heartbeat** para auto-shutdown.
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript, Chart.js, PapaParse (leitura de CSV local).
- **APIs de Notícias**: Alpha Vantage `NEWS_SENTIMENT` (primária, requer chave gratuita) ou Yahoo Finance via `yfinance` (fallback automático).

### 2. Componentes do Sistema

#### 2.1 Backend e Modelagem
- `itub4_analise_completa.py`: Orquestra todo o pipeline de machine learning e processamento de dados. Pode receber parâmetros de datas customizadas para retreinamento dinâmico.
- `servidor.py`: Servidor HTTP com rotas para retreinamento (`/retrain`), sentimento (`/sentiment`), verificação de conexão (`/ping`) e desligamento seguro (`/shutdown`).

#### 2.2 Estrutura de Frontend (Dashboard)
- `index.html`: Interface com múltiplas abas (Dashboard Principal, Indicadores, Análise Técnica, Previsão IA).
- `css/style.css`: Estilização responsiva com design moderno "glassmorphism", ícones Font Awesome e modo noturno padrão.
- `js/main.js`: Lógica de renderização de gráficos, zoom inteligente, filtros de janelas de tempo e mecanismo de **Heartbeat**.

#### 2.3 Mecanismo de Heartbeat (Inovação Técnica)
- O servidor Python se fecha de modo gracioso e automático caso o usuário feche a janela/aba do navegador.
- O Frontend (`main.js`) dispara requisições a cada 2 segundos. O backend monitora este pulso de vida. Se passar mais de 4 segundos sem receber um "ping", o Python deduz que a sessão foi finalizada e encerra o processo, fechando automaticamente a janela do terminal.

#### 2.4 Funcionalidade de Zoom e Estado Persistente
- O sistema conta com recursos avançados de interatividade nos gráficos, permitindo **Zoom através do Scroll do Mouse** (via `chartjs-plugin-zoom`).
- O estado de zoom é persistente e sincronizado entre visões minimizadas e o painel expandido, garantindo uma análise técnica fluida sem perder o contexto temporal.
- Controles temporais modulares (1W a 5Y, Global, Personalizado) interagem diretamente com as instâncias dos gráficos.

#### 2.5 Filtros Globais e Períodos Personalizados
- Em todos os locais onde há recortes temporais (Gráficos, Sentimento, Treinamento da IA), existe a possibilidade de selecionar **Modo Global** (todo histórico) ou **Personalizado** (datas exatas de início e fim).
- Ao realizar o **Retreinamento do Modelo**, a Análise de Sentimento é automaticamente orientada a adotar as exatas datas escolhidas.

#### 2.6 Análise de Sentimento — Modo Duplo (Alpha Vantage + Fallback VADER)

O sistema opera em **dois modos de análise de sentimento**, selecionados automaticamente:

##### Modo Primário: Alpha Vantage NEWS_SENTIMENT API
- Ativado quando a chave de API estiver configurada em `config.py`.
- **Endpoint**: `https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=ITUB`
- **Capacidade**: Até **50 notícias por requisição**, com filtro real de período histórico (`time_from` / `time_to` em formato `YYYYMMDDTHHMM`).
- **Sentimento pré-calculado**: O score de sentimento por ticker é retornado diretamente pela API (IA da Alpha Vantage), sem necessidade de processamento NLP local.
- **Escala de score**: -1.0 a +1.0, com thresholds de classificação:
  - `>= +0.35` → Otimismo Extremo
  - `>= +0.05` → Otimismo
  - `> -0.05`  → Neutro
  - `> -0.35`  → Pessimismo
  - `<= -0.35` → Pessimismo Extremo
- **Plano gratuito**: 25 requisições/dia — suficiente para uso diário do dashboard.
- **Como configurar**: Registre-se em https://www.alphavantage.co/support/#api-key e insira a chave em `config.py`.

##### Modo Fallback: Yahoo Finance + VADER NLP
- Ativado automaticamente quando `config.py` não existe ou a chave não está preenchida.
- Busca até ~10 notícias recentes via `yfinance` (limitação da API pública gratuita do Yahoo).
- Calcula sentimento localmente usando a biblioteca `vaderSentiment` (VADER — Valence Aware Dictionary and sEntiment Reasoner).
- Filtros históricos funcionam apenas dentro do lote das 10 notícias mais recentes disponíveis.

##### Indicadores Visuais no Dashboard
- Badge dinâmico mostra a fonte ativa: ✅ **Alpha Vantage** (verde) ou ⚠️ Yahoo Finance (amarelo).
- Cada card de notícia exibe o **veículo de publicação** (ex: "📰 Benzinga", "📰 Reuters") quando disponível.
- Contador de notícias atualizado dinamicamente ao mudar o período.

### 3. Arquivos de Dados (CSV / JSON)
- `itub4_historico.csv`: Histórico bruto importado.
- `itub4_processado_final.csv`: Histórico processado contendo os novos indicadores técnicos.
- `itub4_previsoes_finais.csv`: Projeções de 10 dias futuros originadas pelo XGBoost.
- `itub4_metricas.json`: Base de dados dos resultados de validação cruzada do modelo.
- `itub4_sentimento.json`: Cache local do último resultado de análise de sentimento.

### 4. Configuração de APIs (`config.py`)
O arquivo `config.py` (ignorado pelo Git para proteger credenciais) centraliza as chaves de APIs externas:

```python
# config.py — NÃO COMMITAR
ALPHA_VANTAGE_KEY = "sua_chave_aqui"
```

- Um arquivo `config.example.py` é fornecido como template para novos colaboradores.
- Se `config.py` não existir ou a chave estiver em branco, o sistema usa automaticamente o fallback Yahoo Finance + VADER.

### 5. Fluxo de Operação

1. **Início e Treinamento**
   - O usuário executa o `start_dashboard.bat`.
   - O Python gera e avalia as projeções e depois ergue o `servidor.py`.

2. **Interação com a Interface**
   - O usuário acessa o dashboard. O Javascript coleta os CSVs via PapaParse e pinta os canvas do Chart.js.
   - O usuário pode aplicar zoom, alterar períodos, analisar osciladores isoladamente (ex: RSI em 1Y) e ler a análise técnica no diário.

3. **Encerramento**
   - O usuário finaliza sua análise e simplesmente fecha o Chrome.
   - O servidor intercepta a falha do *heartbeat* em ~4 segundos e finaliza o processo Python.
   - A janela do terminal (`cmd`) se fecha automaticamente via `exit` no `.bat`.

### 6. Sugestões de Melhoria Futuras
- **Upgrade Alpha Vantage Premium**: Aumentar de 25 para 75+ requisições/dia para análises mais frequentes.
- **Integração com WebSocket B3**: Cotações em tempo real para predições de intraday.
- **Treinamento com Sentimento Histórico**: Incorporar o score de sentimento como feature no XGBoost para correlacionar humor do mercado com movimentações de preço.
- **Otimização Bayesiana de Hiperparâmetros**: Refino automático do R² do modelo.
- **Alertas e Notificações**: Envio de e-mail ou push notification quando o modelo previr variação significativa.

---
*Documentação atualizada — Integração Alpha Vantage NEWS_SENTIMENT implementada com fallback automático para Yahoo Finance + VADER NLP.*