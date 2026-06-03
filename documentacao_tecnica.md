# Documentação Técnica do Sistema - ITUB4 Inteligência Financeira

Este documento detalha o funcionamento interno, as métricas de interface e a arquitetura preditiva do sistema de previsão baseado em XGBoost da cotação ITUB4.

---

## 1. Arquitetura e Funcionalidades Globais

O ecossistema do painel "ITUB4 Quantum" foi construído mesclando três grandes frentes:

1. **Pipeline de Dados Macro e Micro:** Através das bibliotecas `yfinance` e de comunicação HTTP com a API do Banco Central (SGS do BCB), o sistema une os dados de pregões do Itau (Abertura, Máxima, Mínima, Fechamento e Volume) à oscilação da taxa de câmbio diária. Os dados são carregados no arquivo *itub4_historico.csv*.
2. **Engenharia de Variáveis (Feature Engineering):** Como o mercado financeiro depende muito de padrões repetitivos, o backend usa a biblioteca `pandas` para compilar mais de 147 variáveis temporais baseadas no preço puro da ação antes de entregar ao modelo.
3. **Machine Learning (XGBoost Otimizado):** O cérebro do sistema utiliza validação cruzada (`TimeSeriesSplit`) e Hyperparameter Tuning (`GridSearchCV` ou `RandomizedSearchCV`). A IA cria várias árvores de decisão para projetar os fechamentos em um horizonte estendido de 10 dias no futuro.
4. **Dashboard Dinâmico Local:** Toda interação é servida em *Vanilla JS* associada à renderização avançada do *Chart.js*, com zoom expansível e customização de "timeframes" globais.

---

## 2. Indicadores do Dashboard (Cards Principais)

A interface na *Aba Indicadores* e *Dashboard Principal* baseia-se em *Cards de KPIs* (Key Performance Indicators). 

* **MAE (Erro Médio Absoluto):** A principal métrica de risco do painel. Exibida em Reais (R$), mede a distância histórica média entre as "apostas" do XGBoost e o preço que de fato ocorreu.
* **RMSE (Raiz do Erro Quadrático Médio):** Uma métrica mais punitiva aos erros extremos. Mede também o erro em Reais, mas dá um peso maior se a IA errou a previsão por valores drásticos.
* **Poder de Explicação (R²):** Oscila até 1 (ou 100%). Mostra que porcentagem das variações do preço foram explicadas perfeitamente pelas variáveis do modelo (e não pelo acaso/mercado cego). 
* **RSI Atual (14d):** *Índice de Força Relativa*. Funciona como um termômetro comportamental dos últimos 14 dias: acima de 70 = ação está cara / euforia de compra (*sobrecomprada*). Abaixo de 30 = excesso de pânico (*sobrevendida*).
* **Último Fechamento:** Demonstra de onde a previsão inicial está partindo (o preço real do último pregão com mercado aberto computado).
* **Acurácia Direcional:** Mostra o percentual de acerto da direção do ativo, ou seja, quantas vezes a inteligência consegue prever corretamente se a ação terminará em tendência de subida ou de descida.

---

## 3. Mapa de Gráficos (Aba Principal e Técnica)

O sistema de gráficos utiliza canvas robustos com janelas modais (`chart-expand-modal`) para avaliações minuciosas:

* **Gráfico Histórico de Preços e Previsão (`priceChart`):** O gráfico primário da tela. O longo traçado histórico termina e se conecta a uma "Trilha de Previsão" azul, indicando visualmente a oscilação esperada pela IA nos pregões que não ocorreram.
* **Oscilador RSI (`rsiChart`):** Um gráfico inferior acompanhando o Preço Real, limitado entre o eixo 0 e 100.
* **Preço Real (`realPriceChart`):** Canvas simplificado dos últimos D dias, focado na inspeção manual do comportamento direcional limpo.
* **Média Móvel de 20 dias (`ma20Chart`):** Um traçado onde o "ruído" diário é diluído em uma linha de base, indicando tendências de reversões no médio prazo.
* **Previsão IA (XGBoost) Isolada (`xgbForecastChart`):** Isola a linha preditiva, muito útil na aba técnica para contrastar a projeção antes da conexão macro no HTML principal.
* **Pontos de Previsão (`predictionPointsChart`):** Scatter plot exibindo os pontos no qual o robô encontrou inflexões diretas no preço, correlacionando aos níveis de preço atual.

---

## 4. Engenharia de Features e a Padronização (Z-Score)

As colunas alimentadas ao `XGBRegressor` são as responsáveis pelo poder preditivo. Elas incluem:

* **Retornos (`ret_1`, `ret_3`, `ret_5`...):** Variação percentual de crescimento em diferentes escalas de pregões.
* **Retornos Suavizados (`ret_suave_...`):** Variação de tendências contínuas com atenuação dos picos intra-dia.
* **Médias Móveis (`ma_5`, `ma_10`, `ma_200...`):** Custo de suporte psicológico do mercado em 1 semana, 1 quinzena, e 1 ano letivo respectivamente.
* **Momentum e Razões (`momento_X`, `ratio_ma_X`):** Calculam a velocidade relativa do preço contra as médias temporais.
* **Volatilidade (`vol_X`):** Instabilidade estatística do preço. Isso ensina ao modelo as diferenças de comportamento de fases de consolidação VS pânicos/euforias.
* **Dólar (`Dolar_Fechamento`):** Integração macroeconômica.

### Padronização Z-Score Absoluta e Rolante
O mercado de 2004 oscilava centavos. O de 2026 oscila reais inteiros diariamente. O modelo de Inteligência Artificial falharia ao tentar treinar com escalas numéricas tão discrepantes.
A padronização via **Z-Score** resolve isso. A equação `(X - Média) / Desvio Padrão` normaliza a base temporal inteira. Isso garante que altas drásticas absolutas do passado conversem em peso matemático igual a oscilações menores de anos mais estáveis.

---

## 5. O Alvo Previsto (Entendimento Categórico)

O **Alvo Previsto (Previsão 10 Dias)** é uma variável interpretativa baseada no resultado da matriz final:

1. **Significado Estatístico:** O "Alvo" (exemplo: R$ 38.86) sinalizado no painel indica o valor exato no **último vetor de encerramento do 10º pregão futuro**, segundo a inferência da rede XGBoost.
2. **Dependência Crítica (MAE):** O Alvo não é uma garantia matemática de cotação exata, é apenas o cerne da curva da parábola de probabilidade. Ele é inseparável do *Erro Médio Absoluto (MAE)*. Um alvo de R$ 38.00 atrelado a um MAE de R$ 1.50 define que a janela de encerramento do 10º pregão futuro reside estatisticamente na *Nuvem de R$ 36.50 a R$ 39.50*.
3. **Uso Técnico:** Essa inferência atua como a expectativa basilar do robô direcional. Operadores utilizam o alvo em comparação aos limites do oscilador e de fechamento para atestar probabilidades reais de Swing Trades e Position.
