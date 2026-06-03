import http.server
import socketserver
import os
import webbrowser
import threading
import time
import subprocess
import json
from datetime import datetime, timedelta

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
        if elapsed > 4:
            print(f"\n[INFO] Navegador fechado ou desconectado (sem ping há {elapsed:.0f}s). Encerrando...")
            os._exit(0)  # Encerramento forçado e imediato — fecha a janela do CMD

threading.Thread(target=heartbeat_monitor, daemon=True).start()

def analisar_sentimento_por_periodo(start_date_str=None, end_date_str=None):
    """
    Busca noticias do Yahoo Finance e filtra por periodo.
    Retorna dict com score_medio, classificacao e noticias.
    """
    resultado = {
        "score_medio": 0.0,
        "classificacao": "Neutro",
        "noticias": [],
        "periodo": {"inicio": start_date_str, "fim": end_date_str},
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
        ticker = yf.Ticker("ITUB")
        news = ticker.news

        if not news:
            resultado["erro"] = "Nenhuma notícia encontrada."
            return resultado

        # Converter datas de filtro para timestamps
        start_ts = None
        end_ts = None
        if start_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                start_ts = start_dt.timestamp()
            except:
                pass
        if end_date_str:
            try:
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                end_ts = end_dt.timestamp()
            except:
                pass

        scores = []
        for item in news[:30]:  # Buscar top 30 para ter mais dados após filtro
            content = item.get('content', {})
            title = content.get('title', '') or item.get('title', '')
            summary = content.get('summary', '') or item.get('summary', '')

            texto = f"{title}. {summary}".strip()
            if not texto or texto == ".":
                continue

            # Data da notícia
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

            # Filtrar por período se especificado
            if pub_ts is not None:
                if start_ts and pub_ts < start_ts:
                    continue
                if end_ts and pub_ts > end_ts:
                    continue
            # Se a data é desconhecida e há filtro, incluir mesmo assim (best effort)

            vs = analyzer.polarity_scores(texto)
            compound = vs['compound']
            scores.append(compound)

            resultado["noticias"].append({
                "titulo": title,
                "resumo": summary,
                "score": compound,
                "data": pub_date_display,
                "link": content.get('canonicalUrl', {}).get('url', '') or item.get('link', '')
            })

            if len(scores) >= 15:  # Limitar a 15 noticias
                break

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
        else:
            resultado["classificacao"] = "Sem dados"
            resultado["erro"] = "Nenhuma notícia encontrada no período selecionado."

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


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

                print(f"\n[INFO] Retreinamento: {start_date} → {end_date}")

                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                cmd = f'python itub4_analise_completa.py --start "{start_date}" --end "{end_date}" --no-dashboard'
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

                print(f"\n[INFO] Análise de sentimento: {start_date or 'início'} → {end_date or 'hoje'}")

                resultado = analisar_sentimento_por_periodo(start_date, end_date)

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
    # Limpar processos fantasmas
    os.system('wmic process where "name=\'python.exe\' and (commandline like \'%%servidor.py%%\')" call terminate >nul 2>&1')

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    try:
        with ThreadedTCPServer(("", PORT), CustomHandler) as httpd:
            print("="*55)
            print(f"  🏦 ITUB4 QUANTUM - SERVIDOR ATIVO")
            print(f"  📡 http://localhost:{PORT}")
            print(f"  🔔 Servidor encerrará automaticamente ao fechar o navegador")
            print("="*55)
            webbrowser.open(f"http://localhost:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"\nErro: Porta {PORT} em uso. Feche o processo anterior e tente novamente.")


if __name__ == '__main__':
    start_server()
