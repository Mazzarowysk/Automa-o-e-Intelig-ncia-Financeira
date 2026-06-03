"""
ITUB4 - ANÁLISE COMPLETA COM XGBOOST OTIMIZADO
Versão com alta acurácia usando XGBoost + validação cruzada + Padronização Z-Score
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

warnings.filterwarnings('ignore')

# Machine Learning - XGBoost
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.feature_selection import mutual_info_regression

# ============================================
# DETECTAR SE ESTÁ RODANDO NO STREAMLIT
# ============================================
EM_STREAMLIT = 'streamlit' in sys.modules or 'streamlit.runtime' in sys.modules

if not EM_STREAMLIT:
    print("="*80)
    print("🏦 ITUB4 - ANÁLISE COM XGBOOST OTIMIZADO + PADRONIZAÇÃO Z-SCORE")
    print("="*80)

# ============================================
# 1. CARREGAMENTO E LIMPEZA DOS DADOS
# ============================================

class ProcessadorDados:
    """Classe para processamento completo dos dados ITUB4"""
    
    def __init__(self, caminho_arquivo):
        self.caminho_arquivo = caminho_arquivo
        self.df = None
        self.df_features = None
        self.zscore_stats = {}  # Armazenar estatísticas da padronização
        
    def carregar_dados(self):
        """Carrega e estrutura os dados do CSV"""
        if not EM_STREAMLIT:
            print("\n📂 1. CARREGANDO DADOS...")
        
        # Tentar diferentes encodings
        df = None
        for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
            try:
                df_temp = pd.read_csv(self.caminho_arquivo, encoding=encoding)
                if not EM_STREAMLIT:
                    print(f"   ✅ Arquivo carregado com encoding: {encoding}")
                df = df_temp
                break
            except:
                continue
        
        if df is None:
            raise Exception("Não foi possível carregar o arquivo")
        
        # Mapeamento de colunas
        colunas_mapeamento = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'date' in col_lower:
                colunas_mapeamento[col] = 'Date'
            elif 'close' in col_lower:
                colunas_mapeamento[col] = 'Close'
            elif 'high' in col_lower:
                colunas_mapeamento[col] = 'High'
            elif 'low' in col_lower:
                colunas_mapeamento[col] = 'Low'
            elif 'open' in col_lower:
                colunas_mapeamento[col] = 'Open'
            elif 'volume' in col_lower:
                colunas_mapeamento[col] = 'Volume'
        
        df = df.rename(columns=colunas_mapeamento)
        
        if 'Date' not in df.columns:
            df['Date'] = pd.date_range(start='2020-01-02', periods=len(df), freq='B')
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        if 'Close' not in df.columns:
            for col in df.columns:
                if col.lower() not in ['date', 'volume', 'ticker']:
                    try:
                        test_price = pd.to_numeric(df[col], errors='coerce')
                        if test_price.notna().sum() > len(df) * 0.7:
                            df['Close'] = test_price
                            break
                    except:
                        pass
        
        if 'High' not in df.columns:
            df['High'] = df['Close']
        if 'Low' not in df.columns:
            df['Low'] = df['Close']
        if 'Open' not in df.columns:
            df['Open'] = df['Close'].shift(1).fillna(df['Close'])
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        
        for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['Close'])
        
        self.df = df
        if not EM_STREAMLIT:
            print(f"   ✅ Dados carregados: {len(df)} registros")
            print(f"   💰 Preço atual: R$ {df['Close'].iloc[-1]:.2f}")
        
        return self.df
    
    def validar_consistencia(self):
        if not EM_STREAMLIT:
            print("\n🔧 2. VALIDANDO CONSISTÊNCIA...")
        df = self.df.copy()
        correcoes = 0
        
        mask_high_low = df['High'] < df['Low']
        if mask_high_low.sum() > 0:
            df.loc[mask_high_low, 'High'] = df.loc[mask_high_low, ['High', 'Low']].max(axis=1)
            df.loc[mask_high_low, 'Low'] = df.loc[mask_high_low, ['High', 'Low']].min(axis=1)
            correcoes += mask_high_low.sum()
        
        mask_close_low = df['Close'] < df['Low']
        mask_close_high = df['Close'] > df['High']
        if mask_close_low.sum() > 0:
            df.loc[mask_close_low, 'Close'] = df.loc[mask_close_low, 'Low']
            correcoes += mask_close_low.sum()
        if mask_close_high.sum() > 0:
            df.loc[mask_close_high, 'Close'] = df.loc[mask_close_high, 'High']
            correcoes += mask_close_high.sum()
        
        if 'Date' in df.columns:
            dup_count = df['Date'].duplicated().sum()
            if dup_count > 0:
                df = df.drop_duplicates(subset=['Date'], keep='first')
                correcoes += dup_count
        
        if not EM_STREAMLIT:
            print(f"   ✅ {correcoes} correções aplicadas")
        
        self.df = df
        return self.df
    
    def tratar_nulos(self):
        if not EM_STREAMLIT:
            print("\n🔧 3. TRATANDO VALORES NULOS...")
        df = self.df.copy()
        
        cols_numericas = df.select_dtypes(include=[np.number]).columns
        for col in cols_numericas:
            if df[col].isnull().sum() > 0:
                df[col] = df[col].interpolate(method='linear', limit_direction='both')
        df = df.ffill().bfill()
        
        self.df = df
        return self.df
    
    def aplicar_padronizacao_zscore(self, df, colunas=None, usar_rolling=False, janela=252):
        """
        Aplica padronização Z-Score nos dados
        
        Z = (X - μ) / σ
        
        Parameters:
        -----------
        df : DataFrame
            Dados a serem padronizados
        colunas : list
            Lista de colunas para padronizar (None = todas numéricas exceto Date/target)
        usar_rolling : bool
            Se True, usa média e desvio móveis (janela deslizante)
        janela : int
            Tamanho da janela para rolling (padrão: 252 dias = 1 ano)
        
        Returns:
        --------
        DataFrame com colunas padronizadas adicionadas
        """
        if not EM_STREAMLIT:
            print("\n📊 4a. APLICANDO PADRONIZAÇÃO Z-SCORE...")
        
        df_resultado = df.copy()
        
        # Definir colunas para padronizar
        if colunas is None:
            colunas = df.select_dtypes(include=[np.number]).columns.tolist()
            # Excluir colunas que não devem ser padronizadas
            colunas_excluir = ['target', 'Close', 'High', 'Low', 'Open']
            colunas = [c for c in colunas if c not in colunas_excluir and 'zscore' not in c.lower()]
        
        # Estatísticas da padronização
        self.zscore_stats = {}
        
        for col in colunas:
            if col in df.columns and df[col].notna().any():
                if usar_rolling and len(df) > janela:
                    # Padronização móvel (rolling z-score)
                    media_rolling = df[col].rolling(window=janela, min_periods=30).mean()
                    std_rolling = df[col].rolling(window=janela, min_periods=30).std()
                    # Corrigir: usar where para evitar divisão por zero
                    std_safe = std_rolling.where(std_rolling > 0, 1)
                    df_resultado[f'{col}_zscore_rolling'] = (df[col] - media_rolling) / std_safe
                    
                    # Armazenar estatísticas finais
                    self.zscore_stats[col] = {
                        'media_final': df[col].iloc[-1] if not df[col].empty else 0,
                        'std_final': std_rolling.iloc[-1] if not std_rolling.empty else 1,
                        'media_historica': df[col].mean(),
                        'std_historico': df[col].std(),
                        'ultimo_zscore': df_resultado[f'{col}_zscore_rolling'].iloc[-1] if not df_resultado[f'{col}_zscore_rolling'].isna().all() else 0
                    }
                else:
                    # Padronização global
                    media = df[col].mean()
                    std = df[col].std()
                    # Evitar divisão por zero
                    if std == 0 or pd.isna(std):
                        std = 1
                    df_resultado[f'{col}_zscore'] = (df[col] - media) / std
                    
                    self.zscore_stats[col] = {
                        'media': media,
                        'desvio_padrao': std,
                        'min_zscore': df_resultado[f'{col}_zscore'].min(),
                        'max_zscore': df_resultado[f'{col}_zscore'].max(),
                        'ultimo_zscore': df_resultado[f'{col}_zscore'].iloc[-1] if not df_resultado[f'{col}_zscore'].empty else 0
                    }
        
        if not EM_STREAMLIT:
            print(f"   ✅ {len(colunas)} colunas padronizadas com Z-Score")
            print(f"   📊 Método: {'Rolling (janela móvel)' if usar_rolling else 'Global'}")
        
        return df_resultado
    
    def criar_features_otimizadas(self, padronizar=True):
        """Cria features otimizadas para XGBoost com opção de padronização"""
        if not EM_STREAMLIT:
            print("\n🔧 4. CRIANDO FEATURES OTIMIZADAS PARA XGBOOST...")
        
        df = self.df.copy()
        
        # === RETORNOS ===
        for periodo in [1, 2, 3, 5, 10, 20]:
            df[f'ret_{periodo}'] = df['Close'].pct_change(periodo) * 100
            df[f'ret_suave_{periodo}'] = df[f'ret_{periodo}'].rolling(5, min_periods=1).mean()
        
        # === MÉDIAS MÓVEIS ===
        for periodo in [5, 10, 20, 50, 100, 200]:
            if len(df) > periodo:
                ma_col = f'ma_{periodo}'
                df[ma_col] = df['Close'].rolling(periodo, min_periods=1).mean()
                std_col = f'std_{periodo}'
                df[std_col] = df['Close'].rolling(periodo, min_periods=1).std()
                df[f'ratio_ma_{periodo}'] = df['Close'] / df[ma_col]
                # Evitar divisão por zero
                std_safe = df[std_col].replace(0, 1)
                df[f'zscore_{periodo}'] = (df['Close'] - df[ma_col]) / std_safe
        
        # === TENDÊNCIA ===
        for periodo in [5, 10, 20]:
            ma_col = f'ma_{periodo}'
            if ma_col in df.columns:
                df[f'tendencia_{periodo}'] = df[ma_col].pct_change(periodo) * 100
        
        # === VOLATILIDADE ===
        if 'ret_1' in df.columns:
            df['vol_5'] = df['ret_1'].rolling(5, min_periods=3).std() * np.sqrt(252)
            df['vol_10'] = df['ret_1'].rolling(10, min_periods=5).std() * np.sqrt(252)
            df['vol_20'] = df['ret_1'].rolling(20, min_periods=10).std() * np.sqrt(252)
        
        # === RSI ===
        def calc_rsi(close, periodo=14):
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=periodo, min_periods=5).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=periodo, min_periods=5).mean()
            # Evitar divisão por zero
            loss = loss.replace(0, 1)
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        df['rsi_14'] = calc_rsi(df['Close'], 14).fillna(50)
        df['rsi_7'] = calc_rsi(df['Close'], 7).fillna(50)
        df['rsi_21'] = calc_rsi(df['Close'], 21).fillna(50)
        
        # === BANDAS DE BOLLINGER ===
        bb_periodo = 20
        df['bb_media'] = df['Close'].rolling(bb_periodo, min_periods=1).mean()
        bb_std = df['Close'].rolling(bb_periodo, min_periods=1).std()
        df['bb_superior'] = df['bb_media'] + (bb_std * 2)
        df['bb_inferior'] = df['bb_media'] - (bb_std * 2)
        df['bb_posicao'] = ((df['Close'] - df['bb_inferior']) / (df['bb_superior'] - df['bb_inferior'] + 0.0001)) * 100
        df['bb_largura'] = ((df['bb_superior'] - df['bb_inferior']) / df['bb_media']) * 100
        
        # === ATR ===
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift(1))
        low_close = abs(df['Low'] - df['Close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14, min_periods=5).mean()
        df['atr_pct'] = (df['atr'] / df['Close']) * 100
        
        # === VOLUME ===
        if df['Volume'].sum() > 0:
            df['volume_ma_5'] = df['Volume'].rolling(5, min_periods=1).mean()
            df['volume_ma_20'] = df['Volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['Volume'] / df['volume_ma_20'].replace(0, 1)
            df['volume_trend'] = df['volume_ma_5'] / df['volume_ma_20'].replace(0, 1)
            df['volume_price'] = df['Volume'] / df['Close']
        
        # === PREÇO INTRADAY ===
        df['amplitude'] = ((df['High'] - df['Low']) / df['Close']) * 100
        df['gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
        df['posicao_intraday'] = ((df['Close'] - df['Low']) / (df['High'] - df['Low'] + 0.0001)) * 100
        
        # === MOMENTUM ===
        for periodo in [5, 10, 20]:
            df[f'momento_{periodo}'] = df['Close'].pct_change(periodo) * 100
        
        # === FEATURES TEMPORAIS ===
        if 'Date' in df.columns:
            df['dia_semana'] = df['Date'].dt.dayofweek
            df['mes'] = df['Date'].dt.month
            df['trimestre'] = df['Date'].dt.quarter
            df['dia_mes'] = df['Date'].dt.day
            df['dia_semana_sin'] = np.sin(2 * np.pi * df['dia_semana'] / 5)
            df['dia_semana_cos'] = np.cos(2 * np.pi * df['dia_semana'] / 5)
        
        # === TARGET ===
        df['target'] = df['Close'].shift(-1) / df['Close'] - 1
        df['target'] = df['target'] * 100
        
        # === LIMPEZA ===
        df = df.replace([np.inf, -np.inf], np.nan)
        cols_num = df.select_dtypes(include=[np.number]).columns
        df[cols_num] = df[cols_num].interpolate(method='linear', limit_direction='both')
        df = df.bfill().ffill()
        
        # Aplicar padronização Z-Score nas features (exceto target e preços)
        if padronizar:
            # Identificar colunas para padronizar (features numéricas)
            cols_para_padronizar = [col for col in df.columns 
                                   if col not in ['Date', 'Close', 'High', 'Low', 'Open', 'target'] 
                                   and df[col].dtype in ['float64', 'int64']]
            
            # Aplicar padronização global primeiro
            df = self.aplicar_padronizacao_zscore(df, colunas=cols_para_padronizar, usar_rolling=False)
            
            # Também criar versões rolling z-score para features importantes
            cols_rolling = ['ret_1', 'ret_5', 'vol_5', 'volume_ratio', 'atr_pct']
            cols_rolling = [c for c in cols_rolling if c in df.columns]
            if cols_rolling:
                df_rolling = self.aplicar_padronizacao_zscore(df, colunas=cols_rolling, usar_rolling=True, janela=252)
                # Manter apenas as colunas rolling adicionais
                for col in cols_rolling:
                    if f'{col}_zscore_rolling' in df_rolling.columns:
                        df[f'{col}_zscore_rolling'] = df_rolling[f'{col}_zscore_rolling']
        
        min_periodo = 250
        if len(df) > min_periodo:
            df = df.iloc[min_periodo:].reset_index(drop=True)
        
        self.df_features = df
        if not EM_STREAMLIT:
            print(f"   ✅ {len(df.columns)} features criadas")
            print(f"   📊 Dados finais: {len(df)} registros")
            if padronizar:
                print(f"   📈 Padronização Z-Score aplicada com sucesso")
        
        return self.df_features
    
    def relatorio_padronizacao(self):
        """Gera relatório detalhado da padronização Z-Score"""
        if not self.zscore_stats:
            print("\n⚠️ Nenhuma padronização foi aplicada ainda.")
            return
        
        print("\n" + "="*80)
        print("📊 RELATÓRIO DE PADRONIZAÇÃO Z-SCORE")
        print("="*80)
        
        # Criar DataFrame com estatísticas
        stats_list = []
        for col, stats in self.zscore_stats.items():
            stats_dict = {'feature': col}
            stats_dict.update(stats)
            stats_list.append(stats_dict)
        
        df_stats = pd.DataFrame(stats_list)
        
        print("\n📈 Estatísticas das Features Padronizadas (primeiras 20):")
        print(df_stats.head(20).to_string(index=False))
        
        # Análise de outliers baseada em Z-Score
        print("\n" + "-"*80)
        print("🔍 ANÁLISE DE OUTLIERS (|Z| > 3)")
        print("-"*80)
        
        outlier_count = 0
        for col, stats in self.zscore_stats.items():
            ultimo_z = stats.get('ultimo_zscore', 0)
            if isinstance(ultimo_z, (int, float)) and abs(ultimo_z) > 3:
                print(f"⚠️ {col}: Z-Score atual = {ultimo_z:.2f} (OUTLIER DETECTADO)")
                outlier_count += 1
            elif isinstance(ultimo_z, (int, float)) and abs(ultimo_z) > 2:
                print(f"⚡ {col}: Z-Score atual = {ultimo_z:.2f} (Valor atípico)")
            elif isinstance(ultimo_z, (int, float)):
                print(f"✅ {col}: Z-Score atual = {ultimo_z:.2f} (Normal)")
        
        if outlier_count == 0:
            print("✅ Nenhum outlier grave detectado (|Z| > 3)")


class SelecaoFeatures:
    """Seleção de features otimizada para XGBoost"""
    
    def __init__(self, df, target_col='target'):
        self.df = df
        self.target_col = target_col
        self.features_selecionadas = None
        
    def selecionar_features(self, n_features=30):
        if not EM_STREAMLIT:
            print("\n🎯 5. SELECIONANDO MELHORES FEATURES PARA XGBOOST...")
        
        exclude_cols = ['Date', 'Close', 'High', 'Low', 'Open', 'target']
        
        feature_cols = [col for col in self.df.columns 
                       if col not in exclude_cols and self.df[col].dtype in ['float64', 'int64']]
        
        if len(feature_cols) == 0:
            return []
        
        X = self.df[feature_cols].copy()
        y = self.df[self.target_col].copy()
        
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            return feature_cols[:n_features]
        
        # Correlação com o target
        correlacoes = X.corrwith(y).abs()
        
        # Mutual Information
        try:
            mi = mutual_info_regression(X.fillna(0), y.fillna(0), random_state=42)
            mi_scores = pd.Series(mi, index=feature_cols)
        except:
            mi_scores = correlacoes
        
        # Score combinado
        scores = (correlacoes * 0.5 + mi_scores * 0.5).sort_values(ascending=False)
        
        n_features = min(n_features, len(scores))
        self.features_selecionadas = scores.head(n_features).index.tolist()
        
        if not EM_STREAMLIT:
            print(f"   ✅ {len(self.features_selecionadas)} features selecionadas")
            print(f"\n   📊 TOP 15 FEATURES:")
            for i, (feature, score) in enumerate(scores.head(15).items(), 1):
                print(f"      {i:2d}. {feature[:35]:35s} - score: {score:.4f}")
        
        return self.features_selecionadas


class ModeloXGBoost:
    """Classe especializada em XGBoost com otimização"""
    
    def __init__(self, df, features, target_col='target'):
        self.df = df
        self.features = features
        self.target_col = target_col
        self.modelo = None
        self.scaler = None
        self.metricas = {}
        self.melhores_params = {}
        
    def preparar_dados(self, test_size=0.2):
        X = self.df[self.features].copy()
        y = self.df[self.target_col].copy()
        
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]
        
        split_idx = int(len(X) * (1 - test_size))
        
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        # XGBoost não precisa de escalonamento, mas vamos padronizar para consistência
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        if not EM_STREAMLIT:
            print(f"\n   📊 Treino: {len(X_train)} | Teste: {len(X_test)}")
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def treinar_xgboost_base(self, X_train, y_train, X_test, y_test):
        """XGBoost com parâmetros otimizados"""
        if not EM_STREAMLIT:
            print("\n   🚀 Treinando XGBoost (Otimizado)...")
        
        # Parâmetros otimizados para dados financeiros
        xgb = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=50,
            eval_metric='mae'
        )
        
        # Validação cruzada temporal
        tscv = TimeSeriesSplit(n_splits=5)
        
        try:
            # Cross-validation
            cv_scores = cross_val_score(xgb, X_train, y_train, cv=tscv, 
                                        scoring='neg_mean_absolute_error', n_jobs=-1)
            cv_r2 = cross_val_score(xgb, X_train, y_train, cv=tscv, 
                                     scoring='r2', n_jobs=-1)
        except:
            cv_scores = np.array([0])
            cv_r2 = np.array([0])
        
        # Treinar com early stopping
        eval_set = [(X_train, y_train)]
        xgb.fit(X_train, y_train, 
                eval_set=eval_set, 
                verbose=False)
        
        y_pred = xgb.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        direcao = np.mean(np.sign(y_test) == np.sign(y_pred))
        
        self.metricas['XGBoost Base'] = {
            'MAE': mae,
            'RMSE': rmse,
            'R²': r2,
            'Acurácia': direcao,
            'CV_MAE_medio': -cv_scores.mean() if len(cv_scores) > 0 else 0,
            'CV_R2_medio': cv_r2.mean() if len(cv_r2) > 0 else 0,
            'modelo': xgb,
            'y_pred': y_pred
        }
        
        if not EM_STREAMLIT:
            print(f"      ✅ Acurácia: {direcao*100:.1f}% | MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
            if len(cv_scores) > 0:
                print(f"      📊 Validação Cruzada - MAE médio: {-cv_scores.mean():.4f}")
        
        return xgb
    
    def treinar_xgboost_otimizado(self, X_train, y_train, X_test, y_test):
        """XGBoost com busca de hiperparâmetros otimizada"""
        if not EM_STREAMLIT:
            print("\n   🎯 Treinando XGBoost com Otimização de Hiperparâmetros...")
        
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Grid de parâmetros reduzido para busca mais rápida
        param_grid = {
            'max_depth': [4, 6, 8],
            'learning_rate': [0.005, 0.01, 0.02],
            'n_estimators': [100, 200, 300],
            'subsample': [0.7, 0.8, 0.9],
            'colsample_bytree': [0.7, 0.8, 0.9]
        }
        
        xgb = XGBRegressor(
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=30,
            eval_metric='mae'
        )
        
        try:
            # Randomized search para melhor performance
            random_search = RandomizedSearchCV(
                xgb,
                param_distributions=param_grid,
                n_iter=20,
                cv=tscv,
                scoring='neg_mean_absolute_error',
                random_state=42,
                n_jobs=-1
            )
            random_search.fit(X_train, y_train)
            
            melhores_params = random_search.best_params_
            melhor_score = -random_search.best_score_
        except:
            melhores_params = {
                'max_depth': 6,
                'learning_rate': 0.01,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            }
            melhor_score = 0
        
        self.melhores_params['XGBoost'] = melhores_params
        
        # Treinar modelo final com melhores parâmetros
        xgb_opt = XGBRegressor(
            **melhores_params,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=50,
            eval_metric='mae'
        )
        
        eval_set = [(X_train, y_train)]
        xgb_opt.fit(X_train, y_train, eval_set=eval_set, verbose=False)
        y_pred = xgb_opt.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        direcao = np.mean(np.sign(y_test) == np.sign(y_pred))
        
        self.metricas['XGBoost Otimizado'] = {
            'MAE': mae,
            'RMSE': rmse,
            'R²': r2,
            'Acurácia': direcao,
            'melhores_params': melhores_params,
            'melhor_score': melhor_score,
            'modelo': xgb_opt,
            'y_pred': y_pred
        }
        
        if not EM_STREAMLIT:
            print(f"      ✅ Acurácia: {direcao*100:.1f}% | MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
            print(f"      🎯 Melhores parâmetros: max_depth={melhores_params.get('max_depth', '-')}, "
                  f"lr={melhores_params.get('learning_rate', '-')}, "
                  f"estimators={melhores_params.get('n_estimators', '-')}")
        
        return xgb_opt
    
    def treinar_xgboost_rapido(self, X_train, y_train, X_test, y_test):
        """XGBoost rápido para comparação"""
        if not EM_STREAMLIT:
            print("\n   ⚡ Treinando XGBoost Rápido...")
        
        xgb = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
            n_jobs=-1
        )
        
        xgb.fit(X_train, y_train)
        y_pred = xgb.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        direcao = np.mean(np.sign(y_test) == np.sign(y_pred))
        
        self.metricas['XGBoost Rápido'] = {
            'MAE': mae,
            'RMSE': rmse,
            'R²': r2,
            'Acurácia': direcao,
            'modelo': xgb,
            'y_pred': y_pred
        }
        
        if not EM_STREAMLIT:
            print(f"      ✅ Acurácia: {direcao*100:.1f}% | MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
        
        return xgb
    
    def treinar_todos(self):
        """Treina todos os modelos XGBoost"""
        if not EM_STREAMLIT:
            print("\n🤖 6. TREINANDO MODELOS XGBOOST...")
        
        if len(self.features) == 0:
            return None, {}
        
        X_train, X_test, y_train, y_test = self.preparar_dados()
        
        self.treinar_xgboost_rapido(X_train, y_train, X_test, y_test)
        self.treinar_xgboost_base(X_train, y_train, X_test, y_test)
        self.treinar_xgboost_otimizado(X_train, y_train, X_test, y_test)
        
        melhor_nome = max(self.metricas.keys(), key=lambda x: self.metricas[x]['Acurácia'])
        self.modelo = self.metricas[melhor_nome]['modelo']
        
        if not EM_STREAMLIT:
            print(f"\n   🏆 MELHOR MODELO: {melhor_nome}")
            print(f"      Acurácia: {self.metricas[melhor_nome]['Acurácia']*100:.1f}%")
            print(f"      MAE: {self.metricas[melhor_nome]['MAE']:.4f}")
            print(f"      R²: {self.metricas[melhor_nome]['R²']:.4f}")
        
        return self.modelo, self.metricas


def prever_futuro(modelo, scaler, df, features, dias=10):
    """Gera previsões usando o melhor modelo"""
    if not EM_STREAMLIT:
        print("\n🔮 7. GERANDO PREVISÕES...")
    
    if len(features) == 0:
        return pd.DataFrame()
    
    ultimo = df.iloc[-1:][features].copy()
    ultimo_preco = df['Close'].iloc[-1]
    ultima_data = df['Date'].iloc[-1] if 'Date' in df.columns else datetime.now()
    
    previsoes = []
    preco_atual = ultimo_preco
    
    for i in range(dias):
        X_pred = scaler.transform(ultimo)
        retorno_prev = modelo.predict(X_pred)[0] / 100
        
        preco_atual = preco_atual * (1 + retorno_prev)
        preco_atual = round(preco_atual, 2)
        
        previsoes.append({
            'Dia': i + 1,
            'Data': (ultima_data + timedelta(days=i+1)).strftime('%Y-%m-%d'),
            'Preco_Previsto': preco_atual,
            'Retorno_Previsto': retorno_prev * 100
        })
        
        if i < dias - 1:
            ultimo = ultimo.copy()
            for col in features:
                if 'ret_' in col:
                    ultimo[col] = retorno_prev * 100
    
    df_previsoes = pd.DataFrame(previsoes)
    if not EM_STREAMLIT:
        print(f"   ✅ {len(df_previsoes)} previsões geradas")
    
    return df_previsoes


# ============================================
# DASHBOARD STREAMLIT
# ============================================

def criar_dashboard_streamlit():
    import streamlit as st
    import plotly.graph_objects as go
    import json
    
    st.set_page_config(page_title="ITUB4 - XGBoost + Z-Score", page_icon="🏦", layout="wide")
    
    st.title("🏦 ITUB4 - Análise com XGBoost Otimizado + Padronização Z-Score")
    st.markdown("---")
    
    # Carregar dados processados
    if os.path.exists('itub4_processado_final.csv'):
        with st.spinner("🔄 Carregando dados processados..."):
            df = pd.read_csv('itub4_processado_final.csv')
            df['Date'] = pd.to_datetime(df['Date'])
            
            if os.path.exists('itub4_previsoes_finais.csv'):
                df_previsoes = pd.read_csv('itub4_previsoes_finais.csv')
            else:
                df_previsoes = pd.DataFrame()
            
            metricas = {}
            if os.path.exists('itub4_metricas.json'):
                with open('itub4_metricas.json', 'r') as f:
                    metricas = json.load(f)
    else:
        st.error("❌ Arquivo não encontrado. Execute primeiro o processamento.")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Informações")
        st.metric("📅 Registros", f"{len(df):,}")
        st.metric("💰 Preço Atual", f"R$ {df['Close'].iloc[-1]:.2f}")
        
        if len(df) > 1:
            var = (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100
            st.metric("📈 Variação Diária", f"{var:+.2f}%")
        if 'ret_1' in df.columns:
            dias_com_movimentacao = (df['ret_1'].abs() > 0.0001).sum()
            st.metric(
                "📈 Dias com Movimentação", 
                f"{dias_com_movimentacao:,}",
                help="Número de pregões em que o preço da ação teve variação diferente de zero (considerando margem de erro de 0,001%)"
            )
        
        if 'rsi_14' in df.columns:
            st.metric("🔄 RSI", f"{df['rsi_14'].iloc[-1]:.1f}")
        
        st.markdown("---")
        st.header("🤖 Modelo XGBoost")
        
        if metricas:
            melhor_nome = max(metricas.keys(), key=lambda x: metricas[x].get('Acurácia', 0))
            melhor = metricas[melhor_nome]
            st.metric("Melhor Modelo", melhor_nome)
            st.metric("📉 MAE", f"{melhor.get('MAE', 0):.4f}")
            st.metric("📈 RMSE", f"{melhor.get('RMSE', 0):.4f}")
            if 'R²' in melhor:
                st.metric("📊 R²", f"{melhor['R²']:.4f}")
    # Gráfico de Preço
    st.subheader("📈 Histórico de Preço")
    
    fig_preco = go.Figure()
    fig_preco.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'],
        mode='lines', name='ITUB4',
        line=dict(color='blue', width=2)
    ))
    
    if 'ma_20' in df.columns:
        fig_preco.add_trace(go.Scatter(
            x=df['Date'], y=df['ma_20'],
            mode='lines', name='MM20',
            line=dict(color='orange', width=1, dash='dash')
        ))
    
    if 'ma_50' in df.columns:
        fig_preco.add_trace(go.Scatter(
            x=df['Date'], y=df['ma_50'],
            mode='lines', name='MM50',
            line=dict(color='red', width=1, dash='dash')
        ))
    
    fig_preco.update_layout(height=500, template='plotly_white', hovermode='x unified')
    st.plotly_chart(fig_preco, use_container_width=True)
    
    # Gráfico de Z-Score (se disponível)
    zscore_cols = [col for col in df.columns if 'zscore' in col.lower()]
    if zscore_cols:
        st.subheader("📊 Evolução dos Z-Scores (Padronização)")
        
        fig_zscore = go.Figure()
        # Mostrar até 5 colunas de z-score
        for col in zscore_cols[:5]:
            fig_zscore.add_trace(go.Scatter(
                x=df['Date'], y=df[col],
                mode='lines', name=col,
                line=dict(width=1.5)
            ))
        
        fig_zscore.add_hline(y=3, line_dash="dash", line_color="red", 
                              annotation_text="+3σ (Outlier)")
        fig_zscore.add_hline(y=-3, line_dash="dash", line_color="red", 
                              annotation_text="-3σ (Outlier)")
        fig_zscore.add_hline(y=2, line_dash="dot", line_color="orange", 
                              annotation_text="+2σ")
        fig_zscore.add_hline(y=-2, line_dash="dot", line_color="orange", 
                              annotation_text="-2σ")
        fig_zscore.add_hline(y=0, line_dash="solid", line_color="gray", 
                              annotation_text="Média")
        
        fig_zscore.update_layout(height=400, template='plotly_white')
        st.plotly_chart(fig_zscore, use_container_width=True)
        
        # Tabela de Z-Scores atuais
        st.subheader("📋 Z-Scores Atuais")
        zscore_atual = {}
        for col in zscore_cols:
            if not df[col].isna().all():
                zscore_atual[col] = df[col].iloc[-1]
        
        if zscore_atual:
            df_zscore = pd.DataFrame(list(zscore_atual.items()), columns=['Feature', 'Z-Score Atual'])
            df_zscore['Status'] = df_zscore['Z-Score Atual'].apply(
                lambda x: '🔴 Outlier' if abs(x) > 3 else ('🟡 Atípico' if abs(x) > 2 else '🟢 Normal')
            )
            st.dataframe(df_zscore, use_container_width=True)
    
    # Previsões
    if len(df_previsoes) > 0:
        st.subheader("🔮 Previsões para os Próximos Dias")
        
        cols = st.columns(min(5, len(df_previsoes)))
        for i, col in enumerate(cols):
            if i < len(df_previsoes):
                with col:
                    st.metric(
                        f"Dia {int(df_previsoes.iloc[i]['Dia'])}",
                        f"R$ {df_previsoes.iloc[i]['Preco_Previsto']:.2f}",
                        f"{df_previsoes.iloc[i]['Retorno_Previsto']:+.2f}%"
                    )
        
        fig_prev = go.Figure()
        
        ultimos = df.iloc[-60:].copy()
        fig_prev.add_trace(go.Scatter(
            x=ultimos['Date'], y=ultimos['Close'],
            mode='lines', name='Histórico',
            line=dict(color='blue', width=2)
        ))
        
        datas_prev = [df['Date'].iloc[-1] + timedelta(days=i+1) 
                      for i in range(len(df_previsoes))]
        fig_prev.add_trace(go.Scatter(
            x=datas_prev, y=df_previsoes['Preco_Previsto'],
            mode='lines', name='Previsão XGBoost',
            line=dict(color='red', width=2, dash='dash')
        ))
        fig_prev.add_trace(go.Scatter(
            x=datas_prev, y=df_previsoes['Preco_Previsto'],
            mode='markers', name='Pontos de Previsão',
            marker=dict(color='red', size=8, symbol='circle')
        ))
        
        fig_prev.update_layout(height=400, template='plotly_white')
        st.plotly_chart(fig_prev, use_container_width=True)
    
    # RSI
    if 'rsi_14' in df.columns:
        st.subheader("📊 RSI (Relative Strength Index)")
        
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df['Date'], y=df['rsi_14'],
            mode='lines', name='RSI 14',
            line=dict(color='purple', width=2)
        ))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                          annotation_text="Sobrecomprado")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", 
                          annotation_text="Sobrevendido")
        fig_rsi.update_layout(yaxis_range=[0, 100], height=400, template='plotly_white')
        st.plotly_chart(fig_rsi, use_container_width=True)
    
    st.markdown("---")
    st.caption(f"📅 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.caption("📈 Z-Score: (Valor - Média) / Desvio Padrão | |Z|>3 = Outlier")


# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================

def executar_streamlit():
    script_path = os.path.abspath(__file__)
    
    print("\n" + "="*80)
    print("🚀 Abrindo dashboard Streamlit...")
    print("="*80)
    
    webbrowser.open('http://localhost:8501')
    subprocess.run([sys.executable, '-m', 'streamlit', 'run', script_path, '--', '--modo-streamlit'])


def calcular_data_fim_padrao():
    """Retorna o dia util anterior a hoje (D-1).
    Se hoje eh segunda, retorna sexta-feira anterior.
    Isso garante que a API sempre busca ate o ultimo pregao disponivel."""
    hoje = datetime.now().date()
    # Voltar 1 dia
    ontem = hoje - timedelta(days=1)
    # Se ontem for sabado (5) ou domingo (6), voltar para sexta
    while ontem.weekday() >= 5:
        ontem -= timedelta(days=1)
    return ontem.strftime("%Y-%m-%d")


def baixar_dados_dolar(start="1995-01-01", end=None):
    try:
        import requests
        if end is None:
            end = calcular_data_fim_padrao()
        # Converter datas para o formato do BCB dd/MM/yyyy
        dt_start = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
        dt_end = datetime.strptime(end, "%Y-%m-%d").strftime("%d/%m/%Y")
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
        params = {
            "formato": "json",
            "dataInicial": dt_start,
            "dataFinal": dt_end
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        df = pd.DataFrame(response.json())
        df["data"] = pd.to_datetime(df["data"], dayfirst=True)
        df["Dolar_Fechamento"] = df["valor"].astype(float)
        df.drop(columns=["valor"], inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Erro ao baixar dados do Dólar (BCB): {e}")
        return pd.DataFrame()

def atualizar_dados_yfinance(ticker="ITUB4.SA", start="1995-01-01", end=None, arquivo="itub4_historico.csv"):
    if end is None:
        end = calcular_data_fim_padrao()
    if not 'streamlit' in sys.modules and not 'streamlit.runtime' in sys.modules:
        print(f"\n📥 Baixando dados atualizados de {ticker} via yfinance e Dólar via BCB...")
    try:
        dados = yf.download(ticker, start=start, end=end)
        if not dados.empty:
            dados.reset_index(inplace=True)
            # Flatten multi-index columns if yfinance returns them
            if isinstance(dados.columns, pd.MultiIndex):
                dados.columns = [col[0] for col in dados.columns]
            
            # Garantir formato datetime na coluna Date
            col_date = 'Date' if 'Date' in dados.columns else dados.columns[0]
            dados[col_date] = pd.to_datetime(dados[col_date]).dt.normalize()
            
            # Baixar e fazer merge com os dados do Dólar
            df_dolar = baixar_dados_dolar(start, end)
            if not df_dolar.empty:
                # Merge sugerido pelo usuário: Inner Join
                dados = pd.merge(dados, df_dolar, left_on=col_date, right_on="data", how="inner")
                dados.drop(columns=["data"], inplace=True)
                # Calcular retorno percentual após o merge para refletir dias úteis da B3
                dados["Dolar_Retorno"] = dados["Dolar_Fechamento"].pct_change() * 100
                
                if not 'streamlit' in sys.modules and not 'streamlit.runtime' in sys.modules:
                    print(f"   ✅ Merge com Dólar (BCB) realizado com sucesso!")
                    
            dados.to_csv(arquivo, index=False)
            if not 'streamlit' in sys.modules and not 'streamlit.runtime' in sys.modules:
                print(f"✅ Dados históricos salvos com sucesso em {arquivo} ({len(dados)} registros)")
        else:
            if not 'streamlit' in sys.modules and not 'streamlit.runtime' in sys.modules:
                print(f"⚠️ Aviso: Nenhum dado retornado para {ticker} pelo yfinance.")
    except Exception as e:
        if not 'streamlit' in sys.modules and not 'streamlit.runtime' in sys.modules:
            print(f"❌ Erro ao baixar dados: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ITUB4 Analysis")
    # Valor padrao do end date: D-1 (ultimo dia util)
    data_fim_padrao = calcular_data_fim_padrao()
    parser.add_argument('--start', type=str, default="1995-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument('--end', type=str, default=data_fim_padrao, help="End date YYYY-MM-DD (padrao: D-1)")
    parser.add_argument('--modo-streamlit', action='store_true', help="Run in Streamlit mode")
    parser.add_argument('--no-dashboard', action='store_true', help="Do not start Streamlit server after processing")
    
    args, unknown = parser.parse_known_args()

    if args.modo_streamlit:
        criar_dashboard_streamlit()
    else:
        print(f"\n🚀 Iniciando processamento com XGBOOST OTIMIZADO + Z-SCORE...")
        print(f"   Período Selecionado: {args.start} até {args.end}")
        
        try:
            import streamlit
            import xgboost
            print(f"   ✅ XGBoost versão: {xgboost.__version__}")
        except ImportError as e:
            print(f"❌ Dependência não instalada: {e}")
            print("   Instale com: pip install xgboost streamlit plotly scikit-learn")
            return
        
        print("📊 Processando dados...")
        atualizar_dados_yfinance(ticker="ITUB4.SA", start=args.start, end=args.end, arquivo="itub4_historico.csv")
        processador = ProcessadorDados('itub4_historico.csv')
        processador.carregar_dados()
        processador.validar_consistencia()
        processador.tratar_nulos()
        processador.criar_features_otimizadas(padronizar=True)
        
        # Gerar relatório de padronização
        processador.relatorio_padronizacao()
        
        selecionador = SelecaoFeatures(processador.df_features, target_col='target')
        features = selecionador.selecionar_features(n_features=30)
        
        modelo_ml = ModeloXGBoost(processador.df_features, features, target_col='target')
        modelo, metricas = modelo_ml.treinar_todos()
        
        df_previsoes = prever_futuro(modelo, modelo_ml.scaler, 
                                     processador.df_features, features, dias=10)
        
        # Gerar previsões históricas XGBoost para exibir em todo o período
        df_historico = processador.df_features.copy()
        if modelo is not None and len(features) > 0:
            X_all = df_historico[features].copy()
            X_all_scaled = modelo_ml.scaler.transform(X_all)
            hist_retornos = modelo.predict(X_all_scaled)
            df_historico['XGBoost_Retorno_Previsto'] = hist_retornos
            df_historico['XGBoost_Preco_Previsto'] = (
                df_historico['Close'].shift(1) *
                (1 + df_historico['XGBoost_Retorno_Previsto'].shift(1) / 100)
            )
        else:
            df_historico['XGBoost_Retorno_Previsto'] = np.nan
            df_historico['XGBoost_Preco_Previsto'] = np.nan
        
        # Salvar resultados
        df_historico.to_csv('itub4_processado_final.csv', index=False)
        if len(df_previsoes) > 0:
            df_previsoes.to_csv('itub4_previsoes_finais.csv', index=False)
        
        # Salvar métricas
        import json
        metricas_serializable = {}
        for k, v in metricas.items():
            metricas_serializable[k] = {
                'MAE': float(v['MAE']),
                'RMSE': float(v.get('RMSE', 0)),
                'R²': float(v['R²']),
                'Acurácia': float(v['Acurácia']) if 'Acurácia' in v else None
            }
        
        with open('itub4_metricas.json', 'w') as f:
            json.dump(metricas_serializable, f, indent=2)
        
        print("\n✅ Dados processados e salvos!")
        print(f"   Melhor acurácia: {max(m['Acurácia'] for m in metricas.values())*100:.1f}%")
        
        if not args.no_dashboard:
            print("   O navegador será aberto automaticamente...")
            executar_streamlit()
        else:
            print("   [INFO] Modo silencioso (--no-dashboard) - Dashboard não será iniciado automaticamente.")


if __name__ == "__main__":
    main()