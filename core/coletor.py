import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

def coletar_dados_yfinance(ticker_symbol="ITUB4"):
    """
    Baixa dados historicos do Yahoo Finance.
    """
    print(f"\n📂 Coletando dados para {ticker_symbol}...")
    
    ticker_yf = f"{ticker_symbol}.SA" if not ticker_symbol.endswith(".SA") else ticker_symbol
    ticker = yf.Ticker(ticker_yf)
    
    # Tenta baixar o maximo possivel
    df = ticker.history(period="max")
    
    if df.empty:
        raise Exception(f"Nenhum dado encontrado para o ticker {ticker_yf}")
    
    df = df.reset_index()
    
    # Padroniza nomes das colunas
    df = df.rename(columns={
        'Date': 'Date',
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume'
    })
    
    # Remove fuso horario (timezone)
    if df['Date'].dt.tz is not None:
        df['Date'] = df['Date'].dt.tz_localize(None)
        
    # Limpa dados inválidos (como falhas no Yahoo Finance que retornam Close = 0)
    df = df.dropna(subset=['Close'])
    df = df[df['Close'] > 0]
    
    # Remove dias onde não houve negociação ou dados incompletos (ex: Open 0 e Volume 0)
    mask_invalida = (df['Volume'] == 0) & (df['Open'] == 0)
    df = df[~mask_invalida]
    
    return df

_USD_CACHE = None

def coletar_dolar_historico():
    """
    Busca o historico do dolar via API do Banco Central (SGS).
    Utilizado como feature macroeconomica.
    Faz cache em memoria para nao sobrecarregar o BCB com os workers do orquestrador.
    """
    global _USD_CACHE
    if _USD_CACHE is not None:
        return _USD_CACHE

    URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
    START = datetime(2010, 1, 1)
    END = datetime.now()
    MAX_YEARS = 10
    
    import time
    print("\n💵 Coletando dados macroeconômicos (Dólar - PTAX)...")
    
    def fetch_window(start, end):
        params = {
            "formato": "json",
            "dataInicial": start.strftime("%d/%m/%Y"),
            "dataFinal": end.strftime("%d/%m/%Y"),
        }
        for tentativa in range(3):
            try:
                resp = requests.get(URL, params=params, headers={"Accept": "application/json"}, timeout=10)
                if resp.status_code == 200:
                    return pd.DataFrame(resp.json())
            except Exception as e:
                time.sleep(2)
        return pd.DataFrame()

    windows = []
    cur = START
    while cur < END:
        win_end = min(cur + timedelta(days=MAX_YEARS * 365 + 2), END)
        df_win = fetch_window(cur, win_end)
        if not df_win.empty:
            df_win["data"] = pd.to_datetime(df_win["data"], dayfirst=True)
            df_win["valor"] = df_win["valor"].astype(float)
            windows.append(df_win)
        cur = win_end + timedelta(days=1)
        
    if not windows:
        return None
        
    usd = pd.concat(windows, ignore_index=True)
    usd = usd.drop_duplicates(subset="data").sort_values("data")
    usd = usd.rename(columns={"data": "Date", "valor": "usd_ptax"})
    _USD_CACHE = usd
    return usd

def enriquecer_com_macro(df):
    """
    Faz o merge dos dados da acao com os dados do dolar.
    """
    df_usd = coletar_dolar_historico()
    if df_usd is not None and not df_usd.empty:
        # Arredonda datas para garantir o merge
        df['Date_merge'] = pd.to_datetime(df['Date']).dt.date
        df_usd['Date_merge'] = pd.to_datetime(df_usd['Date']).dt.date
        
        df = pd.merge(df, df_usd[['Date_merge', 'usd_ptax']], on='Date_merge', how='left')
        
        # Preenche valores nulos do dolar com o ultimo valor valido (ffill)
        df['usd_ptax'] = df['usd_ptax'].ffill().bfill()
        df = df.drop(columns=['Date_merge'])
    else:
        df['usd_ptax'] = 1.0 # fallback
        
    return df
