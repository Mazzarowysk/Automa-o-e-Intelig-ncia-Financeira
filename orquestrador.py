import time
import concurrent.futures
import pandas as pd
from core.coletor import coletar_dados_yfinance, enriquecer_com_macro
from core.features import criar_features_otimizadas, selecionar_features
from core.modelo import ModeloXGBoost
from core.sentimento import analisar_sentimento_noticias
from core.notificador import verificar_alertas
import core.banco_dados as bd

TICKERS_PADRAO = [
    "ITUB4", "PETR4", "VALE3", "BBDC4", "ABEV3", 
    "BBAS3", "WEGE3", "MGLU3", "B3SA3", "RENT3", "SUZB3"
]

def processar_ticker(ticker, start_date=None, end_date=None):
    print(f"\n{'='*50}\n🚀 INICIANDO PROCESSAMENTO: {ticker}\n{'='*50}")
    if start_date or end_date:
        print(f"📅 Filtro de Treinamento - De: {start_date or 'Início'} Até: {end_date or 'Hoje'}")
    inicio = time.time()
    
    try:
        # 1. Coleta
        df_raw = coletar_dados_yfinance(ticker)
        df_macro = enriquecer_com_macro(df_raw)
        
        # 2. Features
        df_features = criar_features_otimizadas(df_macro, padronizar=True)
        
        # Filtro de datas para treinamento (após cálculo das features para não quebrar médias móveis)
        if start_date:
            df_features = df_features[df_features['Date'] >= pd.to_datetime(start_date)]
        if end_date:
            df_features = df_features[df_features['Date'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
            
        if len(df_features) < 30:
            print(f"⚠️ Aviso: Poucos dados após o filtro de datas ({len(df_features)} linhas). Treinamento pode ser impreciso.")

        # 3. Seleção
        melhores_features = selecionar_features(df_features, target_col='target', n_features=30)
        
        # 4. Modelo
        modelo_agente = ModeloXGBoost(df_features, melhores_features, target_col='target')
        X_train, X_test, y_train, y_test = modelo_agente.preparar_dados()
        modelo_agente.treinar_xgboost_base(X_train, y_train, X_test, y_test)
        
        # 5. Previsoes
        df_previsoes = modelo_agente.prever()
        
        # 6. Sentimento
        sentimento = analisar_sentimento_noticias(ticker)
        
        # 7. Salvar no Banco de Dados
        bd.salvar_historico_processado(df_features, ticker)
        if df_previsoes is not None and not df_previsoes.empty:
            bd.salvar_previsoes(df_previsoes, ticker)
        bd.salvar_metricas(ticker, modelo_agente.metricas)
        bd.salvar_sentimento(ticker, sentimento)
        
        # 8. Alertas
        # Formatar dicionário de métricas para a funcao de alerta
        melhor_modelo_nome = max(modelo_agente.metricas.keys(), key=lambda k: modelo_agente.metricas[k]['Acurácia'])
        melhor_metrica = modelo_agente.metricas[melhor_modelo_nome]
        verificar_alertas(ticker, melhor_metrica, sentimento, df_previsoes)
        
        tempo = time.time() - inicio
        print(f"\n✅ PROCESSAMENTO CONCLUÍDO: {ticker} (Tempo: {tempo:.1f}s)")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL AO PROCESSAR {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return False

def processar_lote_paralelo(tickers=TICKERS_PADRAO, max_workers=4):
    print(f"\n{'='*60}")
    print(f"🔄 INICIANDO PROCESSAMENTO EM LOTE PARA {len(tickers)} ATIVOS")
    print(f"⚙️ Workers em Paralelo: {max_workers}")
    print(f"{'='*60}\n")
    
    inicio_total = time.time()
    
    # Pre-inicializa banco de dados
    bd.init_db()
    
    sucessos = 0
    erros = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados = list(executor.map(processar_ticker, tickers))
        
    for res in resultados:
        if res:
            sucessos += 1
        else:
            erros += 1
            
    tempo_total = time.time() - inicio_total
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMO DO PROCESSAMENTO")
    print(f"✅ Sucesso: {sucessos} | ❌ Erros: {erros}")
    print(f"⏱️ Tempo Total: {tempo_total:.1f}s")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    processar_lote_paralelo()
