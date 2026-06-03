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

7. **Geração de Previsões Futuras**
   - Utiliza o melhor modelo treinado para prever os próximos 10 dias úteis de preços (`itub4_previsoes_finais.csv`).

8. **Dashboard Interativo (HTML/JS/CSS)**
   - Sistema de visualização próprio, leve e interativo, focado na experiência do usuário (UX).
   - Gráficos integrados utilizando **Chart.js** (Preços, Previsões, RSI, Médias Móveis).
   - Tooltips (dicas) instrucionais, painel de "Ferramentas do Analista" e métricas KPIs detalhadas.
   - Funcionalidade avançada de **Zoom com Scroll do Mouse** sincronizada e persistente entre gráficos.

#### Tecnologias Utilizadas
- **Backend/IA**: Python 3.12, pandas, numpy, scikit-learn, xgboost.
- **Servidor HTTP**: Servidor local Python (`http.server`) com mecanismo de **Heartbeat** para auto-shutdown.
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript, Chart.js, PapaParse (leitura de CSV local).

### 2. Componentes do Sistema

#### 2.1 Backend e Modelagem
- `itub4_analise_completa.py`: Orquestra todo o pipeline de machine learning e processamento de dados. Pode receber parâmetros de datas customizadas para retreinamento dinâmico.
- `servidor.py`: Servidor HTTP encarregado de servir o dashboard. Contém rotas para retreinamento (`/retrain`), verificação de conexão (`/ping`) e desligamento seguro (`/shutdown`).

#### 2.2 Estrutura de Frontend (Dashboard)
- `index.html`: Interface com múltiplas abas (Dashboard Principal, Indicadores, Análise Técnica, Previsão IA).
- `css/style.css`: Estilização responsiva com design moderno "glassmorphism", ícones Font Awesome e modo noturno padrão.
- `js/main.js`: Lógica de renderização de gráficos, aplicação de zoom inteligente (Chart.getChart), filtros de janelas de tempo (1M, 6M, 1Y, Todo Histórico) e o mecanismo de **Heartbeat** que envia pings ao Python para gerenciar o ciclo de vida do servidor.

#### 2.3 Mecanismo de Heartbeat (Inovação Técnica)
- O servidor Python se fecha de modo gracioso e automático caso o usuário feche a janela/aba do navegador.
- O Frontend (`main.js`) dispara requisições a cada 5 segundos. O backend monitora este pulso de vida. Se passar mais de 10 segundos sem receber um "ping", o Python deduz que a sessão do usuário foi finalizada e encerra o processo no terminal.

### 3. Arquivos de Dados (CSV / JSON)
- `itub4_historico.csv`: Histórico bruto importado.
- `itub4_processado_final.csv`: Histórico processado contendo os novos indicadores técnicos.
- `itub4_previsoes_finais.csv`: Projeções de 10 dias futuros originadas pelo XGBoost.
- `itub4_metricas.json`: Base de dados dos resultados de validação cruzada do modelo.

### 4. Fluxo de Operação

1. **Início e Treinamento**
   - O usuário executa o `start_dashboard.bat`.
   - O Python gera e avalia as projeções e depois ergue o `servidor.py`.

2. **Interação com a Interface**
   - O usuário acessa o dashboard. O Javascript coleta os CSVs via PapaParse e pinta os canvas do Chart.js.
   - O usuário pode aplicar zoom, alterar períodos, analisar osciladores isoladamente (ex: RSI em 1Y) e ler a análise técnica no diário.

3. **Encerramento**
   - O usuário finaliza sua análise e simplesmente fecha o Chrome.
   - O servidor intercepta a falha do *heartbeat* e finaliza os processos, limpando a memória.

### 5. Sugestões de Melhoria Futuras
- Otimização Bayesiana de Hiperparâmetros para refino do R².
- Inserção de Análise de Sentimento baseada em notícias ou publicações no X/Twitter.
- Integração em tempo real com APIs de WebSocket (B3) para predições de intraday.

---
*Documentação atualizada de acordo com a arquitetura final Frontend + Heartbeat.*