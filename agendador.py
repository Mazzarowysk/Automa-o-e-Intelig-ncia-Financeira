import schedule
import time
from datetime import datetime
from orquestrador import processar_lote_paralelo

def job_diario():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Executando processamento agendado...")
    try:
        processar_lote_paralelo()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Processamento agendado concluído com sucesso!")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Erro durante o processamento agendado: {e}")

# Agenda para rodar todo dia util as 18:30 (pós pregão)
schedule.every().monday.at("18:30").do(job_diario)
schedule.every().tuesday.at("18:30").do(job_diario)
schedule.every().wednesday.at("18:30").do(job_diario)
schedule.every().thursday.at("18:30").do(job_diario)
schedule.every().friday.at("18:30").do(job_diario)

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📅 Agendador B3 Quantum Iniciado.")
    print("O sistema rodará automaticamente de Seg-Sex às 18:30.")
    print("Pressione Ctrl+C para encerrar.\n")
    
    # Para testar, descomente a linha abaixo para rodar imediatamente ao iniciar:
    # job_diario()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
