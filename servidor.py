import http.server
import socketserver
import os
import webbrowser
import threading
import time
import subprocess
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# === Configuração da API Alpha Vantage ===
try:
    from config import ALPHA_VANTAGE_KEY
except ImportError:
    ALPHA_VANTAGE_KEY = ""

USE_ALPHA_VANTAGE = bool(ALPHA_VANTAGE_KEY and ALPHA_VANTAGE_KEY != "SUA_CHAVE_AQUI")

def calcular_data_fim_padrao():
    """Retorna o ultimo dia util (D-1). Se hoje eh segunda, retorna sexta."""
    hoje = datetime.now().date()
    ontem = hoje - timedelta(days=1)
    while ontem.weekday() >= 5:  # 5=sabado, 6=domingo
        ontem -= timedelta(days=1)
    return ontem.strftime("%Y-%m-%d")

PORT = 8000

# Heartbeat: tempo da última confirmação de presença do browser
last_ping_time = time.time() + 15  # 15s de carência inicial para carregar a página

SHUTDOWN_FLAG = threading.Event()

def heartbeat_monitor():
    """Monitora o ping do navegador. Se parar, encerra o servidor e sai completamente."""
    global last_ping_time
    while not SHUTDOWN_FLAG.is_set():
        time.sleep(2)
        elapsed = time.time() - last_ping_time
        if elapsed > 120:
            print(f"\n[INFO] Navegador fechado ou desconectado (sem ping há {elapsed:.0f}s). Encerrando...")
            os._exit(0)  # Encerramento forçado e imediato — fecha a janela do CMD

threading.Thread(target=heartbeat_monitor, daemon=True).start()

# ─────────────────────────────────────────────────────────────
# Mapeamento de labels Alpha Vantage → português
# ─────────────────────────────────────────────────────────────
AV_LABEL_MAP = {
    "Bullish":          ("Otimismo Extremo",  0.6),
    "Somewhat-Bullish": ("Otimismo",           0.25),
    "Neutral":          ("Neutro",             0.0),
    "Somewhat-Bearish": ("Pessimismo",        -0.25),
    "Bearish":          ("Pessimismo Extremo",-0.6),
}


def analisar_sentimento_alpha_vantage(start_date_str=None, end_date_str=None, ticker="ITUB"):
    """
    Busca notícias e sentimento via Alpha Vantage NEWS_SENTIMENT.
    Suporta filtro real de período histórico com até 50 notícias por req.
    """
    resultado = {
        "score_medio": 0.0,
        "classificacao": "Neutro",
        "noticias": [],
        "periodo": {"inicio": start_date_str, "fim": end_date_str},
        "fonte": "Alpha Vantage",
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Formatar datas para o padrão Alpha Vantage: YYYYMMDDTHHMM
    time_from = ""
    time_to   = ""
    if start_date_str:
        try:
            dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            time_from = dt.strftime("%Y%m%dT0000")
        except:
            pass
    if end_date_str:
        try:
            dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            time_to = dt.strftime("%Y%m%dT2359")
        except:
            pass

    # Construir URL
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers":  ticker,
        "limit":    "50",
        "sort":     "LATEST",
        "apikey":   ALPHA_VANTAGE_KEY,
    }
    if time_from:
        params["time_from"] = time_from
    if time_to:
        params["time_to"]   = time_to

    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Quantum-Finance/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        resultado["erro"] = f"Erro na requisição Alpha Vantage: {e}"
        return resultado

    if "Information" in data:
        resultado["erro"] = f"Limite da API atingido: {data['Information']}"
        return resultado

    feed = data.get("feed", [])
    if not feed:
        resultado["erro"] = "Nenhuma notícia retornada pela Alpha Vantage para este período."
        return resultado

    scores = []
    for item in feed:
        title   = item.get("title",   "")
        summary = item.get("summary", "")
        url_art = item.get("url",     "")
        source  = item.get("source",  "")

        # Data publicação: formato "20241201T143000"
        time_pub = item.get("time_published", "")
        pub_date_display = "Data desconhecida"
        if time_pub:
            try:
                dt = datetime.strptime(time_pub[:15], "%Y%m%dT%H%M%S")
                pub_date_display = dt.strftime("%d/%m/%Y")
            except:
                pub_date_display = time_pub[:8]

        ticker_score = None
        for ts in item.get("ticker_sentiment", []):
            if ts.get("ticker", "").upper() == ticker.upper():
                try:
                    ticker_score = float(ts["ticker_sentiment_score"])
                except:
                    pass
                break

        score = ticker_score if ticker_score is not None else item.get("overall_sentiment_score", 0.0)
        try:
            score = float(score)
        except:
            score = 0.0

        scores.append(score)
        resultado["noticias"].append({
            "titulo":  title,
            "resumo":  summary,
            "score":   score,
            "data":    pub_date_display,
            "fonte":   source,
            "link":    url_art,
        })

    if scores:
        media = sum(scores) / len(scores)
        resultado["score_medio"] = round(media, 4)

        if   media >= 0.35:  resultado["classificacao"] = "Otimismo Extremo"
        elif media >= 0.05:  resultado["classificacao"] = "Otimismo"
        elif media > -0.05:  resultado["classificacao"] = "Neutro"
        elif media > -0.35:  resultado["classificacao"] = "Pessimismo"
        else:                resultado["classificacao"] = "Pessimismo Extremo"
    else:
        resultado["classificacao"] = "Sem dados"
        resultado["erro"]          = "Nenhuma notícia encontrada no período selecionado."

    return resultado


def analisar_sentimento_yfinance(start_date_str=None, end_date_str=None, ticker="ITUB"):
    """
    Fallback: busca notícias do Yahoo Finance e calcula sentimento com VADER.
    Limitado a ~10 notícias recentes (restrição da API gratuita do Yahoo).
    """
    resultado = {
        "score_medio": 0.0,
        "classificacao": "Neutro",
        "noticias": [],
        "periodo": {"inicio": start_date_str, "fim": end_date_str},
        "fonte": "Yahoo Finance + VADER NLP",
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        resultado["erro"] = "Biblioteca vaderSentiment não instalada."
        return resultado

    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news
        if not news:
            resultado["erro"] = "Nenhuma notícia encontrada."
            return resultado

        start_ts = None
        end_ts   = None
        if start_date_str:
            try:
                start_ts = datetime.strptime(start_date_str, "%Y-%m-%d").timestamp()
            except:
                pass
        if end_date_str:
            try:
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                end_ts = end_dt.timestamp()
            except:
                pass

        scores = []
        for item in news[:30]:
            content = item.get('content', {})
            title   = content.get('title',   '') or item.get('title',   '')
            summary = content.get('summary', '') or item.get('summary', '')
            texto   = f"{title}. {summary}".strip()
            if not texto or texto == ".":
                continue

            pub_date_raw = content.get('pubDate', '') or item.get('providerPublishTime', '')
            pub_ts = None
            pub_date_display = 'Data desconhecida'

            if isinstance(pub_date_raw, (int, float)):
                pub_ts = float(pub_date_raw)
                pub_date_display = datetime.fromtimestamp(pub_ts).strftime("%d/%m/%Y")
            elif isinstance(pub_date_raw, str) and pub_date_raw:
                try:
                    dt = datetime.fromisoformat(pub_date_raw.replace('Z', '+00:00'))
                    pub_ts = dt.timestamp()
                    pub_date_display = dt.strftime("%d/%m/%Y")
                except:
                    pub_date_display = pub_date_raw.split('T')[0] if 'T' in pub_date_raw else pub_date_raw

            if pub_ts is not None:
                if start_ts and pub_ts < start_ts: continue
                if end_ts   and pub_ts > end_ts:   continue

            vs = analyzer.polarity_scores(texto)
            compound = vs['compound']
            scores.append(compound)
            resultado["noticias"].append({
                "titulo": title,
                "resumo": summary,
                "score":  compound,
                "data":   pub_date_display,
                "link":   content.get('canonicalUrl', {}).get('url', '') or item.get('link', '')
            })
            if len(scores) >= 15:
                break

        if scores:
            media = sum(scores) / len(scores)
            resultado["score_medio"] = round(media, 4)
            if   media >= 0.5:  resultado["classificacao"] = "Otimismo Extremo"
            elif media >= 0.15: resultado["classificacao"] = "Otimismo"
            elif media > -0.15: resultado["classificacao"] = "Neutro"
            elif media > -0.5:  resultado["classificacao"] = "Pessimismo"
            else:               resultado["classificacao"] = "Pessimismo Extremo"
        else:
            resultado["classificacao"] = "Sem dados"
            resultado["erro"] = "Nenhuma notícia encontrada no período selecionado."

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


def analisar_sentimento_por_periodo(start_date_str=None, end_date_str=None, ticker="ITUB"):
    """
    Ponto de entrada único para análise de sentimento.
    Usa Alpha Vantage se a chave estiver configurada; caso contrário, usa yfinance + VADER.
    """
    if USE_ALPHA_VANTAGE:
        print(f"[INFO] Usando Alpha Vantage para sentimento ({start_date_str} -> {end_date_str}) para {ticker}")
        return analisar_sentimento_alpha_vantage(start_date_str, end_date_str, ticker)
    else:
        print(f"[INFO] Usando Yahoo Finance + VADER para sentimento (chave Alpha Vantage não configurada) para {ticker}")
        return analisar_sentimento_yfinance(start_date_str, end_date_str, ticker)


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    # HTTP/1.1 para suporte a keep-alive e ping consistente
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        # Suprimir logs de ping para não poluir o console
        if args and isinstance(args[0], str) and '/ping' in args[0]:
            return
        super().log_message(format, *args)

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        global last_ping_time

        # ===== /ping =====
        if self.path == '/ping':
            last_ping_time = time.time()
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ===== /shutdown (GET fallback) =====
        if self.path == '/shutdown':
            body = b'{"status":"shutdown"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            print("\n[INFO] Sinal de desligamento (GET) recebido. Encerrando...")
            threading.Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
            return

        return super().do_GET()

    def do_POST(self):
        global last_ping_time

        # ===== /shutdown =====
        if self.path == '/shutdown':
            body = b'{"status":"shutdown"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            print("\n[INFO] Sinal de desligamento (POST) recebido. Encerrando...")
            threading.Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
            return

        # ===== /retrain =====
        if self.path == '/retrain':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                start_date = data.get('start', '1995-01-01')
                end_date = data.get('end', calcular_data_fim_padrao())
                ticker = data.get('ticker', 'ITUB4.SA')

                print(f"\n[INFO] Retreinamento: {start_date} -> {end_date} para {ticker}")

                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                cmd = f'python itub4_analise_completa.py --start "{start_date}" --end "{end_date}" --ticker "{ticker}" --no-dashboard'
                process = subprocess.run(cmd, shell=True, env=env)

                if process.returncode == 0:
                    body = b'{"status":"success"}'
                else:
                    raise Exception("Erro na execucao do script.")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                error_msg = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.send_header('Content-Length', str(len(error_msg)))
                self.end_headers()
                self.wfile.write(error_msg)
            return

        # ===== /sentiment =====
        if self.path == '/sentiment':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data) if post_data else {}
                start_date = data.get('start', None)
                end_date = data.get('end', None)
                ticker = data.get('ticker', 'ITUB4.SA')
                ticker_base = ticker.split('.')[0]

                print(f"\n[INFO] Analise de sentimento: {start_date or 'inicio'} -> {end_date or 'hoje'} para {ticker_base}")

                resultado = analisar_sentimento_por_periodo(start_date, end_date, ticker_base)

                # Salvar também no arquivo para cache
                with open('itub4_sentimento.json', 'w', encoding='utf-8') as f:
                    json.dump(resultado, f, ensure_ascii=False, indent=2)

                body = json.dumps(resultado, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_cors_headers()
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                error_msg = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.send_header('Content-Length', str(len(error_msg)))
                self.end_headers()
                self.wfile.write(error_msg)
            return

        self.send_response(404)
        self.send_header('Content-Length', '0')
        self.end_headers()


def start_server():
    # Limpar processos fantasmas na porta 8000 usando netstat/taskkill (mais robusto que wmic, que é depreciado)
    try:
        import subprocess
        output = subprocess.check_output('netstat -aon | findstr :8000', shell=True).decode('utf-8')
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and (parts[1].endswith(':8000') or parts[1].endswith('.0.0.0:8000') or parts[1].endswith('[::]:8000')):
                pid = parts[-1]
                subprocess.run(f'taskkill /f /pid {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    try:
        with ThreadedTCPServer(("", PORT), CustomHandler) as httpd:
            print("="*55)
            print(f"   QUANTUM FINANCE - SERVIDOR ATIVO")
            print(f"   http://localhost:{PORT}")
            print(f"   Servidor encerrara automaticamente ao fechar o navegador")
            print("="*55)
            webbrowser.open(f"http://localhost:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"\nErro: Porta {PORT} em uso. Feche o processo anterior e tente novamente.")


if __name__ == '__main__':
    start_server()
