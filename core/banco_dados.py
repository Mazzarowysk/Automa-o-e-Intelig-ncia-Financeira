import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados', 'b3_quantum.db')

def get_connection():
    """Retorna uma conexao com o banco SQLite."""
    # Garante que a pasta existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Inicializa as tabelas do banco de dados se nao existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Métricas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metricas (
        ticker TEXT PRIMARY KEY,
        mae REAL,
        rmse REAL,
        r2 REAL,
        acuracia REAL,
        melhor_modelo TEXT,
        data_atualizacao TEXT
    )
    ''')
    
    # Tabela de Sentimento
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sentimento (
        ticker TEXT PRIMARY KEY,
        score_medio REAL,
        classificacao TEXT,
        dados_completos TEXT, -- JSON completo da API
        data_atualizacao TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def salvar_historico_processado(df, ticker):
    """Salva o dataframe historico processado no banco de dados."""
    conn = get_connection()
    df_save = df.copy()
    df_save['ticker'] = ticker
    # Sobrescreve dados do ticker no banco
    # Pandas tem um limite, entao apagamos os dados velhos desse ticker
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM historico WHERE ticker = ?", (ticker,))
    conn.commit()
    
    df_save.to_sql('historico', conn, if_exists='append', index=False)
    conn.close()

def salvar_previsoes(df, ticker):
    """Salva o dataframe de previsoes no banco de dados."""
    conn = get_connection()
    df_save = df.copy()
    df_save['ticker'] = ticker
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='previsoes'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM previsoes WHERE ticker = ?", (ticker,))
    conn.commit()
    
    df_save.to_sql('previsoes', conn, if_exists='append', index=False)
    conn.close()

def salvar_metricas(ticker, metricas_dict):
    """Salva as metricas resumidas no banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()
    
    melhor_nome = max(metricas_dict.keys(), key=lambda x: metricas_dict[x]['Acurácia'])
    melhor = metricas_dict[melhor_nome]
    
    cursor.execute('''
    INSERT OR REPLACE INTO metricas (ticker, mae, rmse, r2, acuracia, melhor_modelo, data_atualizacao)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticker, 
        melhor['MAE'], 
        melhor['RMSE'], 
        melhor['R²'], 
        melhor['Acurácia'], 
        melhor_nome, 
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def salvar_sentimento(ticker, resultado_dict):
    """Salva o JSON completo de sentimento no banco."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO sentimento (ticker, score_medio, classificacao, dados_completos, data_atualizacao)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        ticker,
        resultado_dict.get('score_medio', 0.0),
        resultado_dict.get('classificacao', 'Neutro'),
        json.dumps(resultado_dict, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def carregar_historico_json(ticker):
    """Carrega historico em formato JSON para a API."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM historico WHERE ticker = ?", conn, params=(ticker,))
        if df.empty:
            return []
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Erro ao carregar histórico de {ticker}: {e}")
        return []
    finally:
        conn.close()

def carregar_previsoes_json(ticker):
    """Carrega previsoes em formato JSON para a API."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM previsoes WHERE ticker = ?", conn, params=(ticker,))
        if df.empty:
            return []
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Erro ao carregar previsões de {ticker}: {e}")
        return []
    finally:
        conn.close()

def carregar_metricas_json(ticker):
    """Carrega metricas em formato JSON."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT mae, rmse, r2, acuracia, melhor_modelo, data_atualizacao FROM metricas WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "MAE": row[0],
            "RMSE": row[1],
            "R²": row[2],
            "Acurácia": row[3],
            "modelo": row[4],
            "atualizado_em": row[5]
        }
    except Exception:
        return None
    finally:
        conn.close()

def carregar_sentimento_json(ticker):
    """Carrega sentimento guardado no banco."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dados_completos FROM sentimento WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        if not row:
            return None
        return json.loads(row[0])
    except Exception:
        return None
    finally:
        conn.close()

# Inicializa banco de dados ao importar o modulo
init_db()
