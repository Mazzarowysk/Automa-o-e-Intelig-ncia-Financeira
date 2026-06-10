import pandas as pd
import numpy as np

def validar_consistencia(df):
    """
    Remove inconsistências como High < Low, ou Open > High.
    """
    df = df.copy()
    
    # Corrige High < Low
    mask_high_low = df['High'] < df['Low']
    if mask_high_low.sum() > 0:
        df.loc[mask_high_low, 'High'] = df.loc[mask_high_low, ['High', 'Low']].max(axis=1)
        df.loc[mask_high_low, 'Low'] = df.loc[mask_high_low, ['High', 'Low']].min(axis=1)
    
    # Corrige Close fora de High/Low
    mask_close_low = df['Close'] < df['Low']
    mask_close_high = df['Close'] > df['High']
    if mask_close_low.sum() > 0:
        df.loc[mask_close_low, 'Close'] = df.loc[mask_close_low, 'Low']
    if mask_close_high.sum() > 0:
        df.loc[mask_close_high, 'Close'] = df.loc[mask_close_high, 'High']
        
    # Remove duplicados
    if 'Date' in df.columns:
        df = df.drop_duplicates(subset=['Date'], keep='first')
        
    return df

def tratar_nulos(df):
    df = df.copy()
    cols_numericas = df.select_dtypes(include=[np.number]).columns
    for col in cols_numericas:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].interpolate(method='linear', limit_direction='both')
    df = df.ffill().bfill()
    return df

def aplicar_padronizacao_zscore(df, colunas=None, usar_rolling=False, janela=252):
    df_resultado = df.copy()
    if colunas is None:
        colunas = df.select_dtypes(include=[np.number]).columns.tolist()
        colunas_excluir = ['target', 'Close', 'High', 'Low', 'Open']
        colunas = [c for c in colunas if c not in colunas_excluir and 'zscore' not in c.lower()]
        
    for col in colunas:
        if col in df.columns and df[col].notna().any():
            if usar_rolling and len(df) > janela:
                media_rolling = df[col].rolling(window=janela, min_periods=30).mean()
                std_rolling = df[col].rolling(window=janela, min_periods=30).std()
                std_safe = std_rolling.where(std_rolling > 0, 1)
                df_resultado[f'{col}_zscore_rolling'] = (df[col] - media_rolling) / std_safe
            else:
                media = df[col].mean()
                std = df[col].std()
                if std == 0 or pd.isna(std):
                    std = 1
                df_resultado[f'{col}_zscore'] = (df[col] - media) / std
                
    return df_resultado

def criar_features_otimizadas(df_raw, padronizar=True):
    print("🔧 Criando features técnicas...")
    df = df_raw.copy()
    df = validar_consistencia(df)
    df = tratar_nulos(df)
    
    # Retornos
    for periodo in [1, 2, 3, 5, 10, 20]:
        df[f'ret_{periodo}'] = df['Close'].pct_change(periodo) * 100
        df[f'ret_suave_{periodo}'] = df[f'ret_{periodo}'].rolling(5, min_periods=1).mean()
        
    # Médias móveis
    for periodo in [5, 10, 20, 50, 100, 200]:
        if len(df) > periodo:
            ma_col = f'ma_{periodo}'
            df[ma_col] = df['Close'].rolling(periodo, min_periods=1).mean()
            std_col = f'std_{periodo}'
            df[std_col] = df['Close'].rolling(periodo, min_periods=1).std()
            df[f'ratio_ma_{periodo}'] = df['Close'] / df[ma_col]
            std_safe = df[std_col].replace(0, 1)
            df[f'zscore_{periodo}'] = (df['Close'] - df[ma_col]) / std_safe

    # Tendência
    for periodo in [5, 10, 20]:
        ma_col = f'ma_{periodo}'
        if ma_col in df.columns:
            df[f'tendencia_{periodo}'] = df[ma_col].pct_change(periodo) * 100

    # Volatilidade
    if 'ret_1' in df.columns:
        df['vol_5'] = df['ret_1'].rolling(5, min_periods=3).std() * np.sqrt(252)
        df['vol_10'] = df['ret_1'].rolling(10, min_periods=5).std() * np.sqrt(252)
        df['vol_20'] = df['ret_1'].rolling(20, min_periods=10).std() * np.sqrt(252)

    # RSI
    def calc_rsi(close, periodo=14):
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=periodo, min_periods=5).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periodo, min_periods=5).mean()
        loss = loss.replace(0, 1)
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    df['rsi_14'] = calc_rsi(df['Close'], 14).fillna(50)
    df['rsi_7'] = calc_rsi(df['Close'], 7).fillna(50)
    df['rsi_21'] = calc_rsi(df['Close'], 21).fillna(50)

    # Bollinger Bands
    bb_periodo = 20
    df['bb_media'] = df['Close'].rolling(bb_periodo, min_periods=1).mean()
    bb_std = df['Close'].rolling(bb_periodo, min_periods=1).std()
    df['bb_superior'] = df['bb_media'] + (bb_std * 2)
    df['bb_inferior'] = df['bb_media'] - (bb_std * 2)
    df['bb_posicao'] = ((df['Close'] - df['bb_inferior']) / (df['bb_superior'] - df['bb_inferior'] + 0.0001)) * 100
    df['bb_largura'] = ((df['bb_superior'] - df['bb_inferior']) / df['bb_media']) * 100

    # ATR
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift(1))
    low_close = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14, min_periods=5).mean()
    df['atr_pct'] = (df['atr'] / df['Close']) * 100

    # Volume
    if df['Volume'].sum() > 0:
        df['volume_ma_5'] = df['Volume'].rolling(5, min_periods=1).mean()
        df['volume_ma_20'] = df['Volume'].rolling(20, min_periods=1).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma_20'].replace(0, 1)
        df['volume_trend'] = df['volume_ma_5'] / df['volume_ma_20'].replace(0, 1)
        df['volume_price'] = df['Volume'] / df['Close']

    # Preço Intraday
    df['amplitude'] = ((df['High'] - df['Low']) / df['Close']) * 100
    df['gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
    df['posicao_intraday'] = ((df['Close'] - df['Low']) / (df['High'] - df['Low'] + 0.0001)) * 100

    # Momentum
    for periodo in [5, 10, 20]:
        df[f'momento_{periodo}'] = df['Close'].pct_change(periodo) * 100

    # Temporal
    if 'Date' in df.columns:
        df['dia_semana'] = df['Date'].dt.dayofweek
        df['mes'] = df['Date'].dt.month
        df['trimestre'] = df['Date'].dt.quarter
        df['dia_mes'] = df['Date'].dt.day
        df['dia_semana_sin'] = np.sin(2 * np.pi * df['dia_semana'] / 5)
        df['dia_semana_cos'] = np.cos(2 * np.pi * df['dia_semana'] / 5)

    # Target (preço de amanhã)
    df['target'] = df['Close'].shift(-1) / df['Close'] - 1
    df['target'] = df['target'] * 100

    # Limpeza final
    df = df.replace([np.inf, -np.inf], np.nan)
    cols_num = df.select_dtypes(include=[np.number]).columns
    df[cols_num] = df[cols_num].interpolate(method='linear', limit_direction='both')
    df = df.bfill().ffill()

    if padronizar:
        cols_para_padronizar = [col for col in df.columns 
                               if col not in ['Date', 'Close', 'High', 'Low', 'Open', 'target'] 
                               and df[col].dtype in ['float64', 'int64']]
        df = aplicar_padronizacao_zscore(df, colunas=cols_para_padronizar, usar_rolling=False)
        
        cols_rolling = ['ret_1', 'ret_5', 'vol_5', 'volume_ratio', 'atr_pct']
        cols_rolling = [c for c in cols_rolling if c in df.columns]
        if cols_rolling:
            df_rolling = aplicar_padronizacao_zscore(df, colunas=cols_rolling, usar_rolling=True, janela=252)
            for col in cols_rolling:
                if f'{col}_zscore_rolling' in df_rolling.columns:
                    df[f'{col}_zscore_rolling'] = df_rolling[f'{col}_zscore_rolling']

    min_periodo = 250
    if len(df) > min_periodo:
        df = df.iloc[min_periodo:].reset_index(drop=True)
        
    return df

def selecionar_features(df, target_col='target', n_features=30):
    from sklearn.feature_selection import mutual_info_regression
    print("🎯 Selecionando melhores features...")
    
    exclude_cols = ['Date', 'Close', 'High', 'Low', 'Open', 'target']
    feature_cols = [col for col in df.columns if col not in exclude_cols and df[col].dtype in ['float64', 'int64']]
    
    if len(feature_cols) == 0:
        return []
        
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Tratamento simples para Selecao de Features
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    y = y.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    mi_scores = mutual_info_regression(X, y, random_state=42)
    mi_scores = pd.Series(mi_scores, name="MI Scores", index=X.columns)
    mi_scores = mi_scores.sort_values(ascending=False)
    
    return mi_scores.head(n_features).index.tolist()
