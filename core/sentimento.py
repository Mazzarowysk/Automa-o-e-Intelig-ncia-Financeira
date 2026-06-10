import yfinance as yf
from datetime import datetime
import json

def analisar_sentimento_noticias(ticker_symbol):
    """
    Busca noticias recentes via yfinance e faz analise de sentimento com VADER.
    Retorna o dicionario de resultado.
    """
    print(f"📰 Analisando sentimento de notícias para {ticker_symbol}...")
        
    resultado = {
        "score_medio": 0.0,
        "classificacao": "Neutro",
        "noticias": [],
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        print("⚠️ vaderSentiment não instalado. Pulando análise.")
        resultado["erro"] = "Biblioteca vaderSentiment ausente."
        return resultado
        
    try:
        ticker = yf.Ticker(f"{ticker_symbol}.SA" if not ticker_symbol.endswith(".SA") else ticker_symbol)
        news = ticker.news
        
        if not news:
            print("⚠️ Nenhuma notícia recente encontrada.")
            return resultado
            
        scores = []
        for item in news[:10]: # Top 10 noticias
            content = item.get('content', {})
            title = content.get('title', '')
            summary = content.get('summary', '')
            
            if not title and 'title' in item:
                title = item.get('title', '')
            if not summary and 'summary' in item:
                summary = item.get('summary', '')
                
            texto_completo = f"{title}. {summary}"
            if not texto_completo.strip() or texto_completo == ". ":
                continue
                
            vs = analyzer.polarity_scores(texto_completo)
            compound_score = vs['compound']
            scores.append(compound_score)
            
            pub_date = content.get('pubDate', '') or item.get('providerPublishTime', '')
            if isinstance(pub_date, str) and 'T' in pub_date:
                pub_date = pub_date.split('T')[0]
                
            resultado["noticias"].append({
                "titulo": title,
                "resumo": summary,
                "score": compound_score,
                "data": pub_date,
                "link": content.get('canonicalUrl', {}).get('url', '') or item.get('link', '')
            })
            
        if scores:
            media = sum(scores) / len(scores)
            resultado["score_medio"] = media
            
            if media >= 0.5:
                resultado["classificacao"] = "Otimismo Extremo"
            elif media >= 0.15:
                resultado["classificacao"] = "Otimismo"
            elif media > -0.15:
                resultado["classificacao"] = "Neutro"
            elif media > -0.5:
                resultado["classificacao"] = "Pessimismo"
            else:
                resultado["classificacao"] = "Pessimismo Extremo"
                
            print(f"✅ {len(scores)} notícias analisadas. Score Médio: {media:.2f} ({resultado['classificacao']})")
                
    except Exception as e:
        print(f"❌ Erro ao analisar notícias: {e}")
        resultado["erro"] = str(e)
        
    return resultado
