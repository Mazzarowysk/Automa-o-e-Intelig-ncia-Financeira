# Sistema de Inteligência Financeira para ITUB4
## Documentação Técnica para Apresentação Acadêmica

### 1. Descrição do Algoritmo

#### Objetivo
Prever a direção e o valor futuro das ações ITUB4 com alta acurácia utilizando dados históricos e indicadores técnicos, fornecendo uma interface interativa para visualização das previsões.

#### Passos do Algoritmo

1. **Carregamento e Limpeza de Dados**
   - Carrega o dataset histórico `itub4_historico.csv` contendo preços de abertura, alta, baixa, fechamento e volume.
   - Remove linhas com valores faltantes.
   - Garante que os dados estejam ordenados cronologicamente.

2. **Criação de Características (Features)**
   - Gera mais de 50 indicadores técnicos incluindo:
     - Médias Móveis Simples (SMA) e Exponenciais (EMA)
     - Índice de Força Relativa (RSI)
     - Bandas de Bollinger
     - Oscilador Estocástico
     - MACD (Moving Average Convergence Divergence)
     - Indicadores de volume (OBV, VWAP)
     - Diferenças percentuais e lagged features
     - Características de volatilidade e momentum

3. **Padronização**
   - Aplica Z-score (StandardScaler) para normalizar todas as features, garantindo média 0 e desvio padrão 1.

4. **Seleção de Características**
   - Utiliza duas técnicas combinadas:
     - Correlação com a variável alvo (próximo retorno)
     - Informação Mútua (mutual_info_regression) para capturar relações não lineares
   - Seleciona as características mais relevantes para reduzir ruído e overfitting.

5. **Modelagem com XGBoost**
   - Treina três variantes do modelo XGBoost Regressor:
     - **XGBoost Rápido**: configuração básica para iterabilidade rápida
     - **XGBoost Base**: parâmetros balanceados de desempenho
     - **XGBoost Otimizado**: hiperparâmetros ajustados via validação cruzada
   - Utiliza `TimeSeriesSplit` para validação cruzada temporal, evitando vazamento de dados futuros.

6. **Avaliação de Desempenho**
   - Calcula métricas para cada modelo:
     - Erro Absoluto Médio (MAE)
     - Coeficiente de Determinação (R²)
     - Acurácia de Direção (percentual de previsões corretas de alta/baixa)
   - Métricas armazenadas em `itub4_metricas.json`

7. **Geração de Previsões Futuras**
   - Utiliza o melhor modelo (geralmente o XGBoost Otimizado) para prever os próximos 10 dias de preços.
   - Gera o arquivo `itub4_previsoes_finais.csv` contendo datas e valores previstos.

8. **Dashboard Interativo (Streamlit)**
   - Interface web para visualização:
     - Gráficos de preços históricos e previstos
     - Métricas de desempenho dos modelos
     - Importância das características
     - Opção para retreinar o modelo via endpoint `/retrain`

#### Tecnologias Utilizadas
- Linguagem: Python 3.12.10
- Bibliotecas principais: pandas, numpy, scikit-learn, xgboost, streamlit
- Fonte de dados externos: Banco Central do Brasil (taxa de câmbio USD/BRL via API)
- Servidor HTTP personalizado para gerenciamento de estado

### 2. Especificações dos Bancos de Dados CSV

#### 2.1 itub4_historico.csv
- **Propósito**: Dados históricos brutos das ações ITUB4
- **Fonte**: Provavelmente extraído de API de mercado financeiro (ex: Yahoo Finance, Alpha Vantage)
- **Período**: Múltiplos anos (aproximadamente 602.000 registros)
- **Colunas**:
  - `Date`: Data no formato YYYY-MM-DD
  - `Open`: Preço de abertura
  - `High`: Preço mais alto do dia
  - `Low`: Preço mais baixo do dia
  - `Close`: Preço de fechamento (variável alvo principal)
  - `Volume`: Volume negociado
- **Tamanho**: Aproximadamente 25 MB
- **Uso**: Entrada principal para o pipeline de processamento

#### 2.2 itub4_processado_final.csv
- **Propósito**: Dataset totalmente processado com todas as features engineered
- **Gerado por**: `itub4_analise_completa.py` durante a fase de preparação de dados
- **Colunas**:
  - Todas as colunas de `itub4_historico.csv`
  - + >50 colunas de indicadores técnicos (ex: `SMA_10`, `EMA_20`, `RSI`, `MACD`, `BB_upper`, `BB_lower`, `OBV`, etc.)
  - + Colunas de características derivadas (lagged returns, volatilidade rolling, etc.)
  - + Coluna target (geralmente `Next_Return` ou similar para previsão de retorno)
- **Tamanho**: Aproximadamente 16.7 MB
- **Uso**: Entrada para os modelos de machine learning após seleção de características

#### 2.3 itub4_previsoes_finais.csv
- **Propósito**: Armazena as previsões futuras geradas pelo modelo
- **Gerado por**: `itub4_analise_completa.py` na seção de forecast
- **Colunas**:
  - `Date`: Data da previsão (datas futuras)
  - `Predicted_Close`: Preço de fechamento previsto
  - Possivelmente colunas de intervalo de confiança (se implementado)
- **Uso**: Consumo pelo dashboard Streamlit para exibição de previsões

#### 2.4 itub4_metricas.json
- **Propósito**: Armazena métricas de avaliação dos três modelos XGBoost
- **Gerado por**: `itub4_analise_completa.py` após validação cruzada
- **Estrutura JSON**:
  ```json
  {
    "XGBoost Rápido": {
      "MAE": 1.2159380035538387,
      "R2": -0.09535241195639821,
      "Acurácia": 0.48
    },
    "XGBoost Base": {
      "MAE": 1.1656491505190065,
      "R2": -0.030237978028945456,
      "Acurácia": 0.47836734693877553
    },
    "XGBoost Otimizado": {
      "MAE": 1.1535215452789025,
      "R2": -0.0135907720801689,
      "Acurácia": 0.4881632653061225
    }
  }
  ```
- **Interpretação**:
  - MAE menor indica melhor desempenho (erro médio absoluto em unidades de preço)
  - R² próximo de 1 indica melhor explicação da variância (valores negativos indicam pior que média)
  - Acurácia de Direção: percentual de vezes que o modelo acertou a direção (subida/queda) do preço

### 3. Componentes do Sistema

#### 3.1 Scripts Principais
- `itub4_analise_completa.py`: Orquestra todo o pipeline de machine learning
- `extract_docx.py`: Utilitário para extrair texto de arquivos .docx (usado para obter esta documentação)
- `fetch_usd.py`: Busca taxa de câmbio USD/BRL do Banco Central do Brasil para potencial uso como feature externa
- `servidor.py`: Servidor HTTP personalizado que fornece endpoints `/shutdown` e `/retrain` e serve arquivos estáticos do dashboard

#### 3.2 Arquivos de Configuração e Execução
- `start_dashboard.bat`: Arquivo em lote para inicializar o dashboard Streamlit
- `Python_Financial_Intelligence (1).pptx`: Apresentação existente que pode ser usada como referência visual

#### 3.3 Estrutura de Frontend (Dashboard)
- `index.html`: Página principal do dashboard
- `css/`: Folhas de estilo para customização visual
- `js/`: Scripts JavaScript para interatividade e comunicação com o backend

### 4. Fluxo de Operação

1. **Execução Inicial**
   - O usuário executa `itub4_analise_completa.py` (ou via `start_dashboard.bat`)
   - O script carrega `itub4_historico.csv`
   - Gera `itub4_processado_final.csv` com features
   - Treina e avalia os três modelos XGBoost
   - Salva métricas em `itub4_metricas.json`
   - Gera previsões futuras em `itub4_previsoes_finais.csv`
   - Inicia o servidor Streamlit para visualização

2. **Modo Servidor**
   - O `servidor.py` roda na porta 8000
   - Fornece:
     - Endpoint `/shutdown`: para encerrar o servidor graciosamente
     - Endpoint `/retrain`: para disparar um novo ciclo de treinamento (útil para atualização com novos dados)
   - Serve os arquivos estáticos do dashboard (HTML, CSS, JS)

3. **Interatividade do Usuário**
   - Através do dashboard, o usuário pode:
     - Visualizar preços históricos vs previstos
     - Ver métricas de desempenho dos modelos
     - Analisar importância das features
     - Acionar retreinamento sob demanda

### 5. Considerações para Reprodução

#### Requisitos de Sistema
- Python 3.12 ou superior
- Bibliotecas: pandas, numpy, scikit-learn, xgboost, streamlit, requests
- Conexão com internet para busca de taxa de câmbio (opcional, se usada como feature)

#### Passos para Reprodução
1. Garantir que `itub4_historico.csv` esteja presente na mesma directory
2. Executar: `python itub4_analise_completa.py`
3. Aguardar conclusão do processamento (pode levar vários minutos dependendo do volume de dados)
4. Acessar o dashboard via navegador em `http://localhost:8000` (se iniciado pelo script) ou conforme indicado no terminal

### 6. Limitações e Próximos Passos

#### Limitações Identificadas
- Dependência da qualidade e completude dos dados históricos
- Overfitting potencial apesar das técnicas de regularização e validação temporal
- As métricas de R² negativas sugerem que os modelos têm dificuldade em explicar a variância absoluta dos preços (comum em séries temporais financeiras)
- A acurácia de direção ~48% indica desempenho pouco melhor que aleatório para esta métrica específica

#### Sugestões de Melhoria
- Incorporar dados fundamentais (balanços, demonstrações de resultados)
- Experimentar outras arquiteturas (LSTM, Prophet, modelos de ensemble)
- Implementar caminhada forward (walk-forward) mais robusta
- Adicionar características de sentimento de notícias e redes sociais
- Otimização bayesiana de hiperparâmetros

### 7. Conclusão
Este sistema demonstra uma abordagem prática para aplicação de machine learning em previsão de ações, combinando engenharia de características financeiras com modelos de boosting e uma interface acessível para stakeholders. Apesar dos desafios inerentes à previsão de mercados financeiros, o framework fornece uma base sólida para experimentação e aprimoramento contínuo.

---
*Documentação gerada em: $(Get-Date -Format yyyy-MM-dd)*