# 📊 Indicadores de Previsibilidade — ITUB4 Quantum

Este documento detalha todos os indicadores utilizados no Sistema de Inteligência Financeira ITUB4 para alimentar os modelos preditivos baseados no algoritmo **XGBoost Otimizado**. 

O sistema utiliza um ecossistema com **mais de 50 variáveis (features)** categorizadas entre indicadores técnicos, macroeconômicos, comportamentais e temporais, garantindo uma abordagem robusta para projeções em um horizonte de **10 dias úteis**.

---

## 🗂️ 1. Categorias de Indicadores

### 1.1. Indicadores de Retorno e Tendência (Preço)
Medem o comportamento do preço em diferentes períodos para entender a velocidade da alta ou da queda.
*   **Retornos Percentuais (`ret_1`, `ret_2`, `ret_3`, `ret_5`, `ret_10`, `ret_20`):** Calculam a variação percentual do preço de fechamento ao longo de 1, 2, 3, 5, 10 e 20 pregões passados.
    $$\text{Retorno}(N) = \left( \frac{\text{FechamentoAtual}}{\text{Fechamento}_{t-N}} - 1 \right) \times 100$$
*   **Retornos Suavizados (`ret_suave_1` a `ret_suave_20`):** Média móvel de 5 dias aplicada sobre cada retorno correspondente, reduzindo o ruído e oscilações bruscas intradia.
*   **Tendência de Médias (`tendencia_5`, `tendencia_10`, `tendencia_20`):** Variação percentual das respectivas Médias Móveis. Ensina ao modelo se a média geral de preços está se curvando para cima ou para baixo.

### 1.2. Médias Móveis e Razões
Estabelecem níveis psicológicos de suporte e resistência do mercado em curto, médio e longo prazo.
*   **Médias Móveis Simples - SMA (`ma_5`, `ma_10`, `ma_20`, `ma_50`, `ma_100`, `ma_200`):** Média aritmética do preço de fechamento nos últimos $N$ dias.
*   **Desvio Padrão do Preço (`std_5` a `std_200`):** Mede a dispersão dos preços em relação à sua média móvel no mesmo período.
*   **Razão do Fechamento pela Média (`ratio_ma_5` a `ratio_ma_200`):** Preço de fechamento atual dividido pelo valor da respectiva média. Valores acima de $1.0$ indicam que o preço está acima da média; abaixo de $1.0$, o oposto.
*   **Z-Score Local da Média (`zscore_5` a `zscore_200`):** Distância matemática (em desvios padrões) do preço atual até a média móvel.
    $$\text{Z-Score Local}(N) = \frac{\text{Fechamento} - \text{SMA}_N}{\text{Std}_N}$$

### 1.3. Volatilidade e Oscilação
Ensinam à inteligência artificial a dinâmica do risco e a amplitude das oscilações, diferenciando mercados consolidados de pânicos ou euforias.
*   **Volatilidade Anualizada (`vol_5`, `vol_10`, `vol_20`):** Desvio padrão dos retornos diários multiplicado pela constante anualizada $\sqrt{252}$.
*   **Average True Range - ATR (`atr`):** Média móvel de 14 períodos do *True Range* (o maior valor entre a máxima menos a mínima, máxima menos fechamento anterior, e mínima menos fechamento anterior). Serve para medir a volatilidade absoluta dos preços.
*   **ATR Percentual (`atr_pct`):** O valor do ATR expresso como percentual do preço atual da ação, permitindo comparações históricas independentes da cotação.
*   **Amplitude do Dia (`amplitude`):** Variação entre a máxima e a mínima do pregão expressa em percentual do preço de fechamento.

### 1.4. Momentum e Osciladores Comportamentais
Indicam a força do movimento atual de preços e zonas de saturação da força compradora ou vendedora.
*   **RSI - Índice de Força Relativa (`rsi_7`, `rsi_14`, `rsi_21`):** Indicador de momento de 7, 14 e 21 dias que oscila entre 0 e 100. Níveis acima de 70 sugerem euforia (sobrecompra); abaixo de 30, desespero (sobrevenda).
*   **Posição nas Bandas de Bollinger (`bb_posicao`):** Percentual que indica onde o preço está posicionado entre a Banda Superior e Inferior de 20 dias (de 0% a 100%).
*   **Largura das Bandas de Bollinger (`bb_largura`):** Distância percentual entre a banda superior e a inferior, evidenciando compressão ou expansão de volatilidade (estouro de banda).
*   **Momentum Absoluto (`momento_5`, `momento_10`, `momento_20`):** Variação percentual do fechamento atual contra $N$ pregões anteriores (similar aos retornos).

### 1.5. Indicadores de Volume
Validam a força dos movimentos de preço de acordo com o fluxo financeiro.
*   **Média do Volume (`volume_ma_5`, `volume_ma_20`):** Média móvel do volume de negociações de 5 e 20 dias.
*   **Razão do Volume (`volume_ratio`):** Volume do pregão atual dividido pela média móvel de volume de 20 dias. Valores altos sugerem grande participação institucional.
*   **Tendência do Volume (`volume_trend`):** Razão entre a média do volume de 5 dias e a de 20 dias.
*   **Volume por Preço (`volume_price`):** Volume financeiro dividido pelo preço de fechamento, indicando a "densidade" das transações.

### 1.6. Comportamento Intraday
*   **Gap de Abertura (`gap`):** Variação percentual entre a abertura do pregão atual e o fechamento do pregão anterior.
*   **Posição Intraday (`posicao_intraday`):** Posição relativa do preço de fechamento dentro do canal diário (entre mínima e máxima), onde 0% é a mínima do dia e 100% é a máxima.

### 1.7. Variáveis Macroeconômicas
*   **Cotação do Dólar (`Dolar_Fechamento`):** Taxa diária de câmbio comercial (obtida via SGS do Banco Central). Variações cambiais impactam fortemente a liquidez, o perfil exportador/importador e a atratividade do setor bancário brasileiro para o capital internacional.

### 1.8. Variáveis Temporais
Previnem desvios sazonais e comportamentos de calendário.
*   **Dia da Semana (`dia_semana`, `dia_semana_sin`, `dia_semana_cos`):** Posição na semana de 0 (segunda) a 4 (sexta). As versões `sin` e `cos` realizam a transformação cíclica trigonométrica para evitar descontinuidades numéricas entre sexta-feira e segunda-feira.
*   **Mês (`mes`), Trimestre (`trimestre`) e Dia do Mês (`dia_mes`):** Capturam dinâmicas de fechamento de mês, relatórios trimestrais e sazonabilidade.

---

## 📈 2. Padronização e Resiliência Temporal (Z-Score)

As cotações das ações mudam de escala com o tempo. R$ 10,00 em 2004 representam uma escala dinâmica completamente diferente de R$ 38,00 em 2026. A IA falharia se processasse dados históricos com distorções de escala.

Para resolver esse problema de distorção temporal, o sistema adota duas abordagens de padronização baseadas na fórmula do **Z-Score**:

$$Z = \frac{X - \mu}{\sigma}$$

Onde $X$ é a feature original, $\mu$ é a média e $\sigma$ é o desvio padrão.

1.  **Padronização Global (StandardScaler):** Todas as colunas numéricas (exceto preços de referência e targets) são normalizadas para média 0 e desvio padrão 1 sobre a base histórica completa.
2.  **Padronização Deslizante (Rolling Z-Score - 252 dias):** Aplicada nas colunas de sinal crítico (`ret_1`, `ret_5`, `vol_5`, `volume_ratio`, `atr_pct`). Utiliza apenas a média e o desvio padrão móveis dos últimos 252 dias úteis (1 ano de pregões). Garante que oscilações extremas do passado distante não atenuem a percepção de oscilações significativas no presente.

---

## 🎯 3. Seleção de Variáveis (Feature Selection)

Para evitar o excesso de dados irrelevantes (*overfitting*) e eliminar colunas redundantes, o backend utiliza um método híbrido antes do treinamento do modelo:

1.  **Correlação de Pearson:** Mede a força da relação linear direta de cada feature com o retorno futuro (`target`).
2.  **Informação Mútua (`mutual_info_regression`):** Algoritmo não-linear que mede quanta informação uma variável compartilha com o target, detectando dependências complexas não capturadas pela correlação simples.

O sistema calcula o **score combinado** (50% Correlação + 50% Informação Mútua) e seleciona as **30 melhores variáveis** para alimentar as árvores de decisão do XGBoost.

---

## 🎭 4. O Vetor Comportamental (NLP - Notícias)

O sistema cruza a análise de preços técnica com o **Humor do Mercado**, gerando um indicador qualitativo transformado em pontuação numérica de **-1.0 (Pânico/Baixista)** a **+1.0 (Euforia/Altista)**.

### Fontes e Métodos
*   **Modo Principal (Alpha Vantage):** A pontuação de sentimento é extraída diretamente do endpoint `NEWS_SENTIMENT` para o ticker `ITUB`, calculada por IA robusta.
*   **Modo de Contingência (Yahoo + VADER):** Quando sem chave API, o sistema extrai notícias recentes via `yfinance` e aplica processamento de linguagem natural local através do analisador de regras sintáticas **VADER NLP** no backend.

---

## 🤝 5. Painel de Confluência de Sinais

A tomada de decisão lógica do sistema cruza os dois principais vetores:

1.  **Vetor Técnico (XGBoost):** Variação percentual entre o preço atual e o alvo projetado para daqui a 10 dias.
    *   **Alta:** $> +0.1\%$
    *   **Baixa:** $< -0.1\%$
2.  **Vetor de Sentimento (NLP):** Pontuação de humor atual.
    *   **Otimista:** $> +0.05$ (Alpha Vantage) ou $> +0.15$ (VADER)
    *   **Pessimista:** $< -0.05$ (Alpha Vantage) ou $< -0.15$ (VADER)

### Matriz de Confluência

| Sinal Matemático (IA) | Sentimento de Mercado | Classificação do Painel | Ação Recomendada |
| :--- | :--- | :--- | :--- |
| **Alta** | **Otimista** | 🟢 **COMPRA FORTE** | Alinhamento total entre IA e Notícias. |
| **Baixa** | **Pessimista** | 🔴 **VENDA FORTE** | Ambos os vetores apontam para desvalorização. |
| **Alta** | **Pessimista** | 🟡 **ALERTA DE RISCO** | Divergência. O humor do mercado pode impedir a alta projetada. |
| **Baixa** | **Otimista** | 🟡 **ALERTA DE RISCO** | Divergência. Notícias positivas podem reverter a projeção de queda. |
| **Neutro** | **Neutro** | ⚪ **SINAL NEUTRO** | Ausência de vetores de tendência claros. |
