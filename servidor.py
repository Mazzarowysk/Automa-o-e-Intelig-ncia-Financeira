import http.server
import socketserver
import os
import webbrowser
import threading
import time
import subprocess
import json

PORT = 8000

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def end_headers(self):
        self.send_header('Connection', 'close')
        super().end_headers()

    def do_GET(self):
        # Rota especial para desligar o servidor via requisição do navegador
        if self.path == '/shutdown':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "shutdown"}')
            print("\n[INFO] Sinal de desligamento recebido do Dashboard.")
            print("[INFO] Fechando o servidor...")
            
            # Executa o desligamento em uma thread paralela para que a requisição possa finalizar e o navegador não fique pendado
            def kill_me():
                time.sleep(1)
                os._exit(0)
            threading.Thread(target=kill_me, daemon=True).start()
            return

        return super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/retrain':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                start_date = data.get('start', '1995-01-01')
                end_date = data.get('end', '2026-06-03')
                
                print(f"\n[INFO] Solicitacao de retreinamento recebida: {start_date} a {end_date}")
                print("[INFO] Treinando modelo... Isso pode levar alguns minutos.")
                
                # Definir a variavel de encoding
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                cmd = f'python itub4_analise_completa.py --start "{start_date}" --end "{end_date}" --no-dashboard'
                process = subprocess.run(cmd, shell=True, env=env)
                
                if process.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "success"}')
                else:
                    raise Exception("Erro na execucao do script de retreinamento.")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_msg = f'{{"status": "error", "message": "{str(e)}" }}'
                self.wfile.write(error_msg.encode('utf-8'))
            return
            
        self.send_response(404)
        self.end_headers()

def start_server():
    # Tenta limpar servidores fantasmas antigos que possam estar rodando esse mesmo script
    os.system('wmic process where "name=\'python.exe\' and (commandline like \'%%servidor.py%%\' or commandline like \'%%http.server%%\')" call terminate >nul 2>&1')
    
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    try:
        with ThreadedTCPServer(("", PORT), CustomHandler) as httpd:
            print("="*50)
            print(f"🏦 ITUB4 QUANTUM - SERVIDOR ATIVO")
            print(f"📡 Rodando em http://localhost:{PORT}")
            print("="*50)
            print("Para fechar o servidor, clique no botao vermelho 'Desligar Servidor' no seu Dashboard!")
            
            webbrowser.open(f"http://localhost:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"\nErro ao iniciar: A porta {PORT} ainda parece estar em uso pelo Windows.")
        print("Tente fechar os processos python pelo Gerenciador de Tarefas e tente novamente.")

if __name__ == '__main__':
    start_server()
