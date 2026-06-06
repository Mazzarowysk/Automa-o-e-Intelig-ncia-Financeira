# Documentação Técnica do Sistema - ITUB4 Inteligência Financeira

Este documento detalha o funcionamento interno, as métricas de interface e a arquitetura preditiva do sistema de previsão baseado em XGBoost da cotação ITUB4.

---

## 1. Arquitetura e Funcionalidades Globais

O ecossistema do painel "ITUB4 Quantum" foi construído mesclando três grandes frentes:

1. **Pipeline de Dados Macro e Micro:** Através das bibliotecas `yfinance` e de comunicação HTTP com a API do Banco Central (SGS do BCB), o sistema une os dados de pregões do Itaú (Abertura, Máxima, Mínima, Fechamento e Volume) à oscilação da taxa de câmbio diária. Os dados são carregados no arquivo *itub4_historico.csv*. Para garantir a integridade dos dados e evitar o descarte de pregões recentes da B3 devido a atrasos ou indisponibilidade na API do BCB, o cruzamento é feito via **Left Join** e as cotações faltantes do dólar são preenchidas por propagação (*forward fill*).
2. **Engenharia de Variáveis (Feature Engineering):** Como o mercado financeiro depende muito de padrões repetitivos, o backend usa a biblioteca `pandas` para compilar mais de 50 indicadores técnicos baseados no preço puro da ação antes de entregar ao modelo.
3. **Machine Learning (XGBoost Otimizado):** O cérebro do sistema utiliza validação cruzada (`TimeSeriesSplit`) e Hyperparameter Tuning. A IA cria várias árvores de decisão para projetar os fechamentos em um horizonte de 10 dias no futuro.
4. **Dashboard Dinâmico Local:** Toda interação é servida em *Vanilla JS* associada à renderização avançada do *Chart.js*, com zoom por scroll do mouse e customização de timeframes globais.

### Princípio de Estado Único (Single Source of Truth)

Todos os gráficos, em todas as abas, partem do mesmo conjunto de dados centralizado no objeto `globalData` e do mesmo score de sentimento em `window.currentSentimentScore`. Qualquer mudança de parâmetro (período de sentimento, retreinamento, novo período de notícias) propaga automaticamente para todas as abas e gráficos, sem inconsistências.

---

## 2. Indicadores do Dashboard (Cards Principais)

A interface na *Aba Indicadores* e *Dashboard Principal* baseia-se em *Cards de KPIs* (Key Performance Indicators).

* **MAE (Erro Médio Absoluto):** A principal métrica de risco do painel. Exibida em Reais (R$), mede a distância histórica média entre as previsões do XGBoost e o preço que de fato ocorreu.
* **RMSE (Raiz do Erro Quadrático Médio):** Uma métrica mais punitiva aos erros extremos. Mede o erro em Reais, dando peso maior a previsões com erros drásticos.
* **Poder de Explicação (R²):** Oscila até 1 (100%). Mostra que porcentagem das variações do preço foram explicadas pelo modelo (e não pelo acaso). Quanto mais próximo de 1, maior a consistência do modelo.
* **RSI Atual (14d):** *Índice de Força Relativa*. Termômetro comportamental dos últimos 14 dias: acima de 70 = sobrecomprada (euforia). Abaixo de 30 = sobrevendida (pânico).
* **Último Fechamento:** Ponto de partida real para as previsões futuras (último pregão computado).
* **Acurácia Direcional:** Percentual de acerto da direção do ativo (subida ou queda) nas previsões históricas do modelo.

---

## 3. Mapa de Gráficos — Interligação entre Abas

O sistema possui **6 gráficos ativos** distribuídos em duas abas. Todos compartilham o mesmo `globalData`.

### 3.1 Dashboard Principal

| Gráfico | ID Canvas | O que Mostra | Conectado ao Sentimento? |
|---------|-----------|--------------|--------------------------|
| Histórico + Previsão | `priceChart` | Preço real, MM20, XGBoost futuro (vermelho), **Linha Ciano** (ajuste por sentimento) | ✅ Sim — cone de risco atualiza em tempo real |
| Oscilador RSI | `rsiChart` | RSI 14 períodos com zonas 30/70 coloridas | ❌ Indicador técnico puro |

### 3.2 Aba Análise Técnica

| Gráfico | ID Canvas | O que Mostra | Conectado ao Sentimento? |
|---------|-----------|--------------|--------------------------|
| Preço Real | `realPriceChart` | Histórico real simples | ❌ Visualização isolada |
| Média Móvel 20d | `ma20Chart` | Tendência de médio prazo | ❌ Visualização isolada |
| Previsão IA (XGBoost) | `xgbForecastChart` | XGBoost histórico + XGBoost futuro (vermelho) + **Linha Ciano** | ✅ Sim — cone de risco espelhado do Principal |
| Pontos de Previsão | `predictionPointsChart` | Losangos roxos nos alvos diários | ❌ Visualização isolada |

### 3.3 Controles de Período — Independência por Aba

Cada aba tem seus próprios controles temporais, permitindo análises cruzadas:
- **Gráfico Principal:** `timeframe-controls` → redesenha `priceChart` + `rsiChart`
- **Análise Técnica:** `tech-timeframe-controls` → redesenha os 4 gráficos técnicos
- **RSI:** `rsi-timeframe-controls` → redesenha apenas o `rsiChart`

Isso permite, por exemplo, visualizar o RSI em 1 Mês enquanto o gráfico principal exibe o histórico Global, ou comparar a Previsão IA em 3 Meses com o Preço Real em 1 Ano.

---

## 4. Análise de Confluência (IA + Notícias) — O Painel Inteligente

Localizado acima do gráfico principal, cruza dois vetores de informação em tempo real:

### 4.1 Vetores de Entrada

| Vetor | Fonte | Threshold de Gatilho |
|-------|-------|----------------------|
| **Sinal Matemático (IA)** | Variação % entre preço atual e último alvo XGBoost | > +0.1% = Alta \| < -0.1% = Baixa |
| **Humor do Mercado (NLP)** | `window.currentSentimentScore` (-1 a +1) | > +0.05 (Alpha Vantage) ou > +0.15 (Yahoo/VADER) = Otimista \| < -0.05 (Alpha Vantage) ou < -0.15 (Yahoo/VADER) = Pessimista |

### 4.2 Matriz de Decisão e Sinais

| IA Prevê | Notícias | Sinal | Interpretação |
|----------|---------|-------|---------------|
| Alta | Otimistas | 🟢 **COMPRA FORTE** | Confluência total — matemática e sentimento alinhados |
| Baixa | Pessimistas | 🔴 **VENDA FORTE** | Confluência total — ambos os vetores apontam queda |
| Alta | Pessimistas | 🟡 **ALERTA DE RISCO** | Divergência — mercado pode contrariar os gráficos por pânico |
| Baixa | Otimistas | 🟡 **ALERTA DE RISCO** | Divergência — notícias podem ignorar tendência técnica |
| Neutro | Neutro | ⚪ **SINAL NEUTRO** | Falta de confluência direcional clara |

### 4.3 O Raio-X da Confluência e Dicas de Ajuda (Tooltips)

Ao clicar no painel de confluência, abre-se o painel expansível **"Raio-X da Confluência"**, que detalha os dois pilares analíticos. Para facilitar a compreensão do usuário, foram adicionados ícones de ajuda interativos (sinal de interrogação) que exibem descrições no hover:
- **Sinal Matemático (IA):** Informa a tendência direcional calculada pela IA (XGBoost) comparando a projeção futura com o preço de fechamento atual.
- **Humor do Mercado (Notícias):** Explica a pontuação de sentimento (otimista, pessimista ou neutro) extraído das últimas notícias através de Processamento de Linguagem Natural (NLP).

### 4.4 A Linha Ciano — Projeção Híbrida (IA + Sentimento)

A linha ciano tracejada representa a **Previsão Ajustada pelo Humor do Mercado**. Aparece em dois lugares:
1. No gráfico `priceChart` (Dashboard Principal)
2. No gráfico `xgbForecastChart` (Aba Análise Técnica)

**Fórmula de cálculo (frontend):**

```
ajusteDiario = sentimentScore * 1.5%
precoAjustado(dia N) = precoXGBoost * (1 + ajusteDiario × N)
```

O **amplificador visual** garante separação mínima entre as linhas mesmo em sentimentos fracos:
- Se |score| entre 0.01 e 0.30 → força visualSentiment para ±0.30 para legibilidade

**Cone de risco colorido:**
- Área verde entre as linhas → sentimento otimista (ciano acima da vermelha)
- Área vermelha entre as linhas → sentimento pessimista (ciano abaixo da vermelha)

---

## 5. Engenharia de Features e a Padronização (Z-Score)

As colunas alimentadas ao `XGBRegressor` são as responsáveis pelo poder preditivo:

* **Retornos (`ret_1`, `ret_3`, `ret_5`...):** Variação percentual de crescimento em diferentes escalas de pregões.
* **Retornos Suavizados (`ret_suave_...`):** Variação de tendências contínuas com atenuação dos picos intra-dia.
* **Médias Móveis (`ma_5`, `ma_10`, `ma_200...`):** Custo de suporte psicológico do mercado em 1 semana, 1 quinzena e 1 ano.
* **Momentum e Razões (`momento_X`, `ratio_ma_X`):** Calculam a velocidade relativa do preço contra as médias temporais.
* **Volatilidade (`vol_X`):** Instabilidade estatística do preço. Ensina ao modelo a diferença entre fases de consolidação e pânicos/euforias.
* **Dólar (`Dolar_Fechamento`):** Integração macroeconômica — câmbio influencia ações de bancos.

### Padronização Z-Score Absoluta e Rolante

O mercado de 2004 oscilava centavos. O de 2026 oscila reais inteiros diariamente. A IA falharia ao tentar treinar com escalas numéricas tão discrepantes.

A padronização via **Z-Score** resolve isso: `(X - Média) / Desvio Padrão` normaliza toda a base temporal, garantindo que oscilações de anos diferentes tenham peso matemático equivalente.

---

## 6. O Alvo Previsto (Entendimento Categórico)

O **Alvo Previsto (Previsão 10 Dias)** é uma variável interpretativa baseada no resultado da matriz final:

1. **Significado Estatístico:** O "Alvo" (exemplo: R$ 38.86) indica o valor esperado no **último fechamento do 10º pregão futuro**, segundo a inferência XGBoost.
2. **Dependência Crítica (MAE):** O Alvo não é uma garantia, é o cerne da curva de probabilidade. Um alvo de R$ 38.00 com MAE de R$ 1.50 define uma janela estatística de R$ 36.50 a R$ 39.50.
3. **Uso Técnico:** Operadores comparam o alvo com os limites do oscilador RSI e de fechamento para estimar probabilidades em Swing Trades e Position.

---

## 7. Interatividade Avançada

### Zoom por Scroll do Mouse
- Disponível em todos os gráficos (Principal, RSI, 4 gráficos técnicos)
- Estado de zoom persistente ao expandir gráfico em modal
- Duplo clique para reset de zoom
- Zoom centralizado no ponto do cursor (não na borda do gráfico)

### Diário do Analista
- Textarea com persistência em `localStorage`
- Cada entrada registra: data/hora, viés (Alta/Baixa/Neutro) e preço atual da ITUB4
- Timeline cronológica de anotações com opção de exclusão individual

### Retreinamento Dinâmico e Desligamento
- Seleção de período de treinamento com botões rápidos (1W até Global) ou datas customizadas
- Exibe estimativa de pregões no período selecionado
- Ao retreinar, sincroniza automaticamente o período de análise de sentimento
- O servidor Python auto-encerra após 120 segundos (2 minutos) sem ping do navegador (mecanismo de heartbeat para estabilidade)

### Modo de Visualização Streamlit Alternativo
- O script `itub4_analise_completa.py` pode ser executado em modo Streamlit passando a flag `--modo-streamlit`
- Comando de execução: `python itub4_analise_completa.py --modo-streamlit`
- Porta padrão: `8501`
- Apresenta gráficos em Plotly para analisar o histórico de preço, evolução de Z-Scores de padronização, e previsões futuras do XGBoost.

---

*Documentação atualizada — Interligação entre abas, gráficos, Painel de Confluência e limites de sentimento descritos. Modo Streamlit alternativo e mecanismo de heartbeat de 120s documentados.*
