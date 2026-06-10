import os
from datetime import datetime
import json

def verificar_alertas(ticker, metricas, sentimento, previsoes_df):
    """
    Verifica a matriz de confluencia para disparar alertas.
    """
    # Lógica de confluência
    confluencia = "Neutra"
    if metricas and previsoes_df is not None and not previsoes_df.empty:
        # Acuracia
        acuracia = metricas.get("Acurácia", 0) * 100
        # Previsao média dos proximos 3 dias
        if len(previsoes_df) >= 3:
            retorno_medio_3d = previsoes_df['Previsao_Pct'].head(3).mean()
        else:
            retorno_medio_3d = 0.0
            
        score_sentimento = sentimento.get("score_medio", 0.0)
        
        # Regra de Compra Forte
        if acuracia > 55 and retorno_medio_3d > 0 and score_sentimento > 0.15:
            confluencia = "Compra Forte"
        elif acuracia > 55 and retorno_medio_3d < 0 and score_sentimento < -0.15:
            confluencia = "Venda Forte"
            
    if confluencia in ["Compra Forte", "Venda Forte"]:
        enviar_alerta_log(ticker, confluencia, acuracia, retorno_medio_3d, score_sentimento)
        
def enviar_alerta_log(ticker, tipo, acuracia, previsao, sentimento):
    """
    Registra o alerta em um arquivo de log na pasta dados/.
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'alertas.log')
    
    msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERTA PARA {ticker}: {tipo} | Acurácia: {acuracia:.1f}% | Previsão 3D: {previsao:.2f}% | Sentimento: {sentimento:.2f}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(msg)
        
    print(f"\n🔔 {msg}")
