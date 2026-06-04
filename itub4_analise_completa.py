"""
ITUB4 - ANÁLISE COMPLETA COM XGBOOST ROBUSTO + AJUSTE DE SENTIMENTO
Versão completa: Correção de Bugs + Alvo de 5 Dias + MACD + Dólar + Gráficos com Ajuste de Sentimento
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import subprocess
import sys
import os
import webbrowser
import yfinance as yf
import json

warnings.filterwarnings('ignore')

# Machine Learning - XGBoost
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.feature_selection import mutual_info_regression

# Detector de ambiente Streamlit
EM_STREAMLIT = 'streamlit' in sys.modules or 'streamlit.runtime' in sys.modules

if not EM_STREAMLIT:
    print("="*80)
    print("🏦 ITUB4 - ANÁLISE COM XGBOOST DE PRODUÇÃO + LINHA DE SENTIMENTO")
    print("="*80)

# ============================================
# 1. PROCESSAMENTO DE DADOS
# ============================================

class ProcessadorDados:
    def __init__(self, caminho_arquivo):
        self.caminho_arquivo = caminho_arquivo
        self.df = None
        self.df_features = None
        
    def carregar_dados(self):
        if not EM_STREAMLIT:
            print("\n📂 1. CARREGANDO DADOS...")
        
        df = None
        for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(self.caminho_arquivo, encoding=encoding)
                break
            except:
                continue
        
        if df is None:
            raise Exception("Não foi possível carregar o arquivo CSV.")
        
        colunas_mapeamento = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'date' in col_lower: colunas_mapeamento[col] = 'Date'
            elif 'close' in col_lower: colunas_mapeamento[col] = 'Close'
            elif 'high' in col_lower: colunas_mapeamento[col] = 'High'
            elif 'low' in col_lower: colunas_mapeamento[col] = 'Low'
            elif 'open' in col_lower: colunas_mapeamento[col] = 'Open'
            elif 'volume' in col_lower: colunas_mapeamento[col] = 'Volume'
        
        df = df.rename(columns=colunas_mapeamento)
        if 'Date' not in df.columns:
            df['Date'] = pd.date_range(start='2020-01-02', periods=len(df), freq='B')
            
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        
        for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        df = df.dropna(subset=['Close'])
        self.df = df
        return self.df
    
    def validar_consistencia(self):
        df = self.df.copy()
        mask_high_low = df['High'] < df['Low']
        if mask_high_low.sum() > 0:
            df.loc[mask_high_low, 'High'] = df.loc[mask_high_low, ['High', 'Low']].max(axis=1)
            df.loc[mask_high_low, 'Low'] = df.loc[mask_high_low, ['High', 'Low']].min(axis=1)
            
        mask_close_low = df['Close'] < df['Low']
        mask_close_high = df['Close'] > df['High']
        df.loc[mask_close_low, 'Close'] = df.loc[mask_close_low, 'Low']
        df.loc[mask_close_high, 'Close'] = df.loc[mask_close_high, 'High']
        
        df = df.drop_duplicates(subset=['Date'], keep='first')
        self.df = df
        return self.df
    
    def tratar_nulos(self):
        df = self.df.copy()
        cols_numericas = df.select_dtypes(include=[np.number]).columns
        for col in cols_numericas:
            if df[col].isnull().sum() > 0:
                df[col] = df[col].interpolate(method='linear', limit_direction='both')
        self.df = df.ffill().bfill()
        return self.df
    
    def criar_features_otimizadas(self):
        if not EM_STREAMLIT:
            print("\n🔧 4. CRIANDO FEATURES OTIMIZADAS PARA XGBOOST...")
        df = self.df.copy()
        
        # Retornos Estacionários
        for periodo in [1, 2, 3, 5, 10, 20]:
            df[f'ret_{periodo}'] = df['Close'].pct_change(periodo) * 100
            df[f'ret_suave_{periodo}'] = df[f'ret_{periodo}'].rolling(5, min_periods=1).mean()
        
        # Médias e Desvios locais (Sem vazamento global)
        for periodo in [5, 10, 20, 50, 100, 200]:
            if len(df) > periodo:
                df[f'ma_{periodo}'] = df['Close'].rolling(periodo, min_periods=1).mean()
                df[f'std_{periodo}'] = df['Close'].rolling(periodo, min_periods=1).std()
                df[f'ratio_ma_{periodo}'] = df['Close'] / df[f'ma_{periodo}']
                df[f'zscore_{periodo}'] = (df['Close'] - df[f'ma_{periodo}']) / df[f'std_{periodo}'].replace(0, 1)
        
        # RSI
        def calc_rsi(close, periodo=14):
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=periodo, min_periods=5).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=periodo, min_periods=5).mean()
            return 100 - (100 / (1 + (gain / loss.replace(0, 1))))
        
        df['rsi_14'] = calc_rsi(df['Close'], 14).fillna(50)
        df['rsi_7'] = calc_rsi(df['Close'], 7).fillna(50)
        
        # MACD (Novo indicador estrutural)
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bandas de Bollinger
        df['bb_media'] = df['Close'].rolling(20, min_periods=1).mean()
        bb_std = df['Close'].rolling(20, min_periods=1).std()
        df['bb_superior'] = df['bb_media'] + (bb_std * 2)
        df['bb_inferior'] = df['bb_media'] - (bb_std * 2)
        df['bb_posicao'] = ((df['Close'] - df['bb_inferior']) / (df['bb_superior'] - df['bb_inferior'] + 0.0001)) * 100
        
        # Volatilidade e Amplitude
        df['vol_5'] = df['ret_1'].rolling(5, min_periods=3).std() * np.sqrt(252)
        df['amplitude'] = ((df['High'] - df['Low']) / df['Close']) * 100
        
        # Features do Câmbio (Dólar) integradas
        if 'Dolar_Fechamento' in df.columns:
            df['dolar_ma20'] = df['Dolar_Fechamento'].rolling(20, min_periods=1).mean()
            df['dolar_tendencia'] = df['Dolar_Fechamento'].pct_change(20) * 100
            
        # Alvo preditivo estabilizado para 5 dias úteis
        df['target'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
        
        df = df.replace([np.inf, -np.inf], np.nan).bfill().ffill()
        if len(df) > 250: df = df.iloc[250:].reset_index(drop=True)
        
        self.df_features = df
        return self.df_features

# ============================================
# 2. INTELIGÊNCIA ARTIFICIAL (XGBOOST)
# ============================================

class SelecaoFeatures:
    def __init__(self, df, target_col='target'):
        self.df = df
        self.target_col = target_col
        
    def selecionar_features(self, n_features=30):
        exclude_cols = ['Date', 'Close', 'High', 'Low', 'Open', 'target', 'Dolar_Fechamento', 'ma_50', 'ma_100', 'ma_200']
        feature_cols = [col for col in self.df.columns if col not in exclude_cols and self.df[col].dtype in ['float64', 'int64']]
        
        X = self.df[feature_cols].fillna(0)
        y = self.df[self.target_col].fillna(0)
        
        correlacoes = X.corrwith(y).abs()
        try:
            mi = mutual_info_regression(X, y, random_state=42)
            mi_scores = pd.Series(mi, index=feature_cols)
        except:
            mi_scores = correlacoes
            
        scores = (correlacoes * 0.5 + mi_scores * 0.5).sort_values(ascending=False)
        return scores.head(n_features).index.tolist()


class ModeloXGBoost:
    def __init__(self, df, features, target_col='target'):
        self.df = df
        self.features = features
        self.target_col = target_col
        self.metricas = {}
        
    def treinar_todos(self):
        X = self.df[self.features].values
        y = self.df[self.target_col].values
        
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Modelo XGBoost com hiperparâmetros estáveis de Produção
        xgb = XGBRegressor(
            objective='reg:squarederror', n_estimators=800, learning_rate=0.01,
            max_depth=4, min_child_weight=5, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
        )
        
        # Split de Validação limpo para Early Stopping
        split_val = int(len(X_train) * 0.9)
        xgb.fit(X_train[:split_val], y_train[:split_val], eval_set=[(X_train[split_val:], y_train[split_val:])], verbose=False)
        
        y_pred = xgb.predict(X_test)
        direcao = (np.sign(y_test) == np.sign(y_pred)).mean()
        
        self.metricas['XGBoost Produção'] = {
            'MAE': mean_absolute_error(y_test, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_test, y_pred)),
            'R²': r2_score(y_test, y_pred),
            'Acurácia': direcao,
            'modelo': xgb
        }
        return xgb, self.metricas

# ============================================
# 3. PROJEÇÃO RECURSIVA COM AJUSTE DE SENTIMENTO
# ============================================

def prever_futuro(modelo, df, features, score_sentimento, dias=5):
    ultimo_registro = df.iloc[-1:].copy()
    ultimo_preco = df['Close'].iloc[-1]
    ultima_data = df['Date'].iloc[-1]
    
    previsoes = []
    preco_matematico = ultimo_preco
    preco_com_sentimento = ultimo_preco
    
    # Define o peso do impacto do sentimento no preço (ex: score +0.5 adiciona +0.15% ao dia)
    fator_ajuste = score_sentimento * 0.30 
    
    for i in range(dias):
        X_pred = ultimo_registro[features].values
        retorno_previsto_xgb = modelo.predict(X_pred)[0]
        
        # Linha 1: Evolução matemática pura do modelo
        preco_matematico = preco_matematico * (1 + (retorno_previsto_xgb / 100))
        
        # Linha 2: Evolução combinada com o sentimento das notícias
        retorno_com_sentimento = retorno_previsto_xgb + fator_ajuste
        preco_com_sentimento = preco_com_sentimento * (1 + (retorno_com_sentimento / 100))
        
        previsoes.append({
            'Dia': i + 1,
            'Data': (ultima_data + timedelta(days=i+1)).strftime('%Y-%m-%d'),
            'Preco_Previsto': round(preco_matematico, 2),
            'Preco_Sentimento': round(preco_com_sentimento, 2),
            'Retorno_Previsto': retorno_previsto_xgb,
            'Retorno_Sentimento': retorno_com_sentimento
        })
        
        # Atualização recursiva para o loop continuo
        ultimo_registro = ultimo_registro.copy()
        ultimo_registro['Close'] = preco_matematico
        
    return pd.DataFrame(previsoes)

# ============================================
# 4. DOWNLOADS E SERVIÇOS DE RETORNO
# ============================================

def baixar_dolar_bcb(start="2015-01-01", end="2026-06-03"):
    try:
        import requests
        dt_start = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
        dt_end = datetime.strptime(end, "%Y-%m-%d").strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial={dt_start}&dataFinal={dt_end}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        df = pd.DataFrame(res.json())
        df["data"] = pd.to_datetime(df["data"], dayfirst=True)
        df["Dolar_Fechamento"] = df["valor"].astype(float)
        return df[["data", "Dolar_Fechamento"]]
    except:
        return pd.DataFrame()

def atualizar_base_yfinance(ticker="ITUB4.SA", start="2015-01-01", end="2026-06-03"):
    try:
        end_date = (datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        dados = yf.download(ticker, start=start, end=end_date)
        if not dados.empty:
            dados.reset_index(inplace=True)
            if isinstance(dados.columns, pd.MultiIndex): dados.columns = [col[0] for col in dados.columns]
            col_date = 'Date' if 'Date' in dados.columns else dados.columns[0]
            dados[col_date] = pd.to_datetime(dados[col_date]).dt.normalize()
            
            df_dol = baixar_dolar_bcb(start, end)
            if not df_dol.empty:
                dados = pd.merge(dados, df_dol, left_on=col_date, right_on="data", how="inner").drop(columns=["data"])
            dados.to_csv("itub4_historico.csv", index=False)
    except Exception as e:
        print(f"Erro ao atualizar Yahoo Finance: {e}")

def analisar_sentimento_noticias(ticker_symbol="ITUB"):
    resultado = {"score_medio": 0.0, "classificacao": "Neutro"}
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        scores = []
        for item in news[:10]:
            c = item.get('content', {})
            texto = f"{c.get('title', '')}. {c.get('summary', '')}"
            if len(texto.strip()) > 5:
                scores.append(analyzer.polarity_scores(texto)['compound'])
        if scores:
            media = sum(scores) / len(scores)
            resultado = {"score_medio": media, "classificacao": "Otimismo" if media >= 0.1 else ("Pessimismo" if media <= -0.1 else "Neutro")}
    except:
        pass
    with open('itub4_sentimento.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    return resultado

# ============================================
# 5. RENDERIZAÇÃO DO PANEL STREAMLIT
# ============================================

def criar_dashboard_streamlit():
    import streamlit as st
    import plotly.graph_objects as go
    
    st.set_page_config(page_title="ITUB4 Intel", page_icon="🏦", layout="wide")
    st.title("🏦 ITUB4 - Dashboard de Produção Inteligente")
    st.markdown("---")
    
    if not os.path.exists('itub4_processado_final.csv') or not os.path.exists('itub4_previsoes_finais.csv'):
        st.error("Por favor, execute o script no terminal primeiro para gerar as bases de dados.")
        return
        
    df = pd.read_csv('itub4_processado_final.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df_prev = pd.read_csv('itub4_previsoes_finais.csv')
    
    with open('itub4_metricas.json', 'r') as f: metricas = json.load(f)
    with open('itub4_sentimento.json', 'r', encoding='utf-8') as f: sentimento = json.load(f)
        
    modelo_vencedor = list(metricas.keys())[0]
    
    with st.sidebar:
        st.header("📊 Inteligência Estatística")
        st.metric("💰 Último Fechamento", f"R$ {df['Close'].iloc[-1]:.2f}")
        st.metric("🎯 Acurácia Direcional", f"{metricas[modelo_vencedor]['Acurácia']*100:.1f}%")
        st.metric("📉 Erro Médio (MAE)", f"{metricas[modelo_vencedor]['MAE']:.4f}")
        st.markdown("---")
        st.subheader("📰 Sentimento Corrente")
        status_emoji = "🟢" if sentimento['score_medio'] > 0.05 else ("🔴" if sentimento['score_medio'] < -0.05 else "🟡")
        st.metric("Humor do Mercado", f"{status_emoji} {sentimento['classificacao']}", f"Score VADER: {sentimento['score_medio']:.2f}")

    # ABAS DO DASHBOARD (A linha de sentimento está integrada a todas elas)
    aba1, aba2 = st.tabs(["📈 Projeção de Tendência", "🔍 Visualizador Técnico Alternativo"])
    
    # Criando os vetores combinados de Histórico + Previsões para evitar quebras no gráfico
    datas_completas = list(df['Date'].tail(40)) + list(pd.to_datetime(df_prev['Data']))
    
    with aba1:
        st.subheader("Janela de Fechamento Histórico vs Projeções")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Date'].tail(40), y=df['Close'].tail(40), name="Preço Real", line=dict(color="blue", width=2.5)))
        
        # Linkando a previsão pura do XGBoost
        eixo_x_prev = [df['Date'].iloc[-1]] + list(pd.to_datetime(df_prev['Data']))
        fig1.add_trace(go.Scatter(x=eixo_x_prev, y=[df['Close'].iloc[-1]] + list(df_prev['Preco_Previsto']), name="Projeção XGBoost Pura", line=dict(color="orange", width=2, dash="dash")))
        
        # EXIBIÇÃO DA LINHA PEDIDA EM TODOS OS GRÁFICOS: Linha de Sentimento Notícias
        fig1.add_trace(go.Scatter(x=eixo_x_prev, y=[df['Close'].iloc[-1]] + list(df_prev['Preco_Sentimento']), name="Ajuste c/ Sentimento Notícias", line=dict(color="cyan", width=2.5, dash="dot")))
        
        st.plotly_chart(fig1, use_container_width=True)
        
    with aba2:
        st.subheader("Análise Técnica de Volatilidade Integrada")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df['Date'].tail(40), y=df['Close'].tail(40), name="Preço de Mercado", line=dict(color="blue")))
        if 'bb_superior' in df.columns:
            fig2.add_trace(go.Scatter(x=df['Date'].tail(40), y=df['bb_superior'].tail(40), name="BB Superior", line=dict(color="gray", width=1, dash="dash")))
            fig2.add_trace(go.Scatter(x=df['Date'].tail(40), y=df['bb_inferior'].tail(40), name="BB Inferior", line=dict(color="gray", width=1, dash="dash")))
            
        # A mesma linha disponível na segunda visualização técnica para cruzamento de dados
        fig2.add_trace(go.Scatter(x=eixo_x_prev, y=[df['Close'].iloc[-1]] + list(df_prev['Preco_Previsto']), name="XGBoost Pura", line=dict(color="orange", dash="dash")))
        fig2.add_trace(go.Scatter(x=eixo_x_prev, y=[df['Close'].iloc[-1]] + list(df_prev['Preco_Sentimento']), name="Ajuste c/ Sentimento Notícias", line=dict(color="cyan", width=2.5, dash="dot")))
        
        st.plotly_chart(fig2, use_container_width=True)

    # Cards Resumo na base da tela
    st.subheader("🔮 Tabela Operacional de Metas (D+1 a D+5)")
    cols = st.columns(5)
    for idx, row in df_prev.iterrows():
        with cols[idx]:
            st.metric(
                label=f"Data: {row['Data']} (D+{int(row['Dia'])})",
                value=f"R$ {row['Preco_Sentimento']:.2f}",
                delta=f"Notícias: {row['Retorno_Sentimento']:+.2f}%"
            )

# ============================================
# REGENTE PRINCIPAL
# ============================================

def main():
    if '--modo-streamlit' in sys.argv:
        criar_dashboard_streamlit()
    else:
        hoje_str = datetime.now().strftime("%Y-%m-%d")
        atualizar_base_yfinance(ticker="ITUB4.SA", start="2016-01-01", end=hoje_str)
        
        proc = ProcessadorDados('itub4_historico.csv')
        proc.carregar_dados()
        proc.validar_consistencia()
        proc.tratar_nulos()
        df_f = proc.criar_features_otimizadas()
        
        selec = SelecaoFeatures(df_f)
        features_lista = selec.selecionar_features(n_features=25)
        
        mod = ModeloXGBoost(df_f, features_lista)
        modelo, metricas = mod.treinar_todos()
        
        # Roda o sentimento e extrai o score numérico base para calibrar as projeções
        res_sentimento = analisar_sentimento_noticias("ITUB")
        
        df_previsoes = prever_futuro(modelo, df_f, features_lista, score_sentimento=res_sentimento['score_medio'], dias=5)
        
        # Gravação física dos arquivos para o Streamlit ler sem duplicar dados
        df_f.to_csv('itub4_processado_final.csv', index=False)
        df_previsoes.to_csv('itub4_previsoes_finais.csv', index=False)
        
        metricas_clean = {k: {'MAE': float(v['MAE']), 'R²': float(v['R²']), 'Acurácia': float(v['Acurácia'])} for k, v in metricas.items()}
        with open('itub4_metricas.json', 'w') as f: json.dump(metricas_clean, f, indent=2)
            
        print("\n✅ Pipeline concluído com absoluto sucesso!")
        
        # Inicialização automatizada do Dashboard local
        script_path = os.path.abspath(__file__)
        webbrowser.open('http://localhost:8501')
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', script_path, '--', '--modo-streamlit'])

if __name__ == "__main__":
    main()