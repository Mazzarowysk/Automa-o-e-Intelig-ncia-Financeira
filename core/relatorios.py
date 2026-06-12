import os
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from core import banco_dados as bd

# Garantir que a pasta relatorios existe
RELATORIOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'relatorios')
os.makedirs(RELATORIOS_DIR, exist_ok=True)


def _interpretar_ativo(row):
    """Gera um resumo analítico textual automático para um ativo."""
    linhas = []

    # --- Sinal e previsão ---
    sinal = row['Sinal']
    pct = row['Previsao Pct']
    conf = row['Confianca (%)']
    rmse = row['RMSE']
    r2 = row['R2']
    sent = row['Sentimento']
    score = row['Score Sentimento']
    preco = row['Preco Base']

    # Força do sinal
    if abs(pct) < 0.2:
        forca = "muito fraca"
    elif abs(pct) < 0.5:
        forca = "moderada"
    elif abs(pct) < 1.0:
        forca = "relevante"
    else:
        forca = "forte"

    direcao = "alta" if sinal == "ALTA" else "queda"
    linhas.append(
        f"O modelo XGBoost projeta uma {direcao} de {abs(pct):.2f}% ({forca}) "
        f"em relacao ao ultimo fechamento de R$ {preco:.2f}."
    )

    # Confiança
    if conf >= 60:
        linhas.append(f"A acuracia direcional de {conf:.1f}% e considerada boa, "
                      f"indicando que o modelo acertou a direcao em mais de 60%% dos testes historicos.")
    elif conf >= 52:
        linhas.append(f"A acuracia direcional de {conf:.1f}% e modesta (ligeiramente acima do acaso). "
                      f"Use este sinal com cautela adicional.")
    else:
        linhas.append(f"A acuracia direcional de {conf:.1f}%% esta proxima do acaso (50%%). "
                      f"O modelo nao demonstra vantagem estatistica clara neste periodo.")

    # R² e RMSE
    margem_pct = (rmse / preco) * 100 if preco > 0 else 0
    if r2 >= 0.1:
        linhas.append(f"O R2 de {r2:.4f} indica que o modelo explica parte significativa "
                      f"das variacoes de preco. RMSE de R$ {rmse:.2f} (~{margem_pct:.1f}%% do preco).")
    elif r2 >= 0.01:
        linhas.append(f"O R2 de {r2:.4f} mostra poder de explicacao moderado. "
                      f"RMSE de R$ {rmse:.2f} (~{margem_pct:.1f}%% do preco base).")
    else:
        linhas.append(f"O R2 de {r2:.4f} esta proximo de zero, indicando baixo poder preditivo. "
                      f"Recomenda-se retreinar com uma janela de tempo mais recente (3-6 meses). "
                      f"RMSE de R$ {rmse:.2f}.")

    # Sentimento
    if score >= 0.3:
        linhas.append(f"O sentimento de midia e '{sent}' (score: {score:.2f}), "
                      f"reforçando o sinal de alta da IA.")
    elif score >= 0.05:
        linhas.append(f"O sentimento de midia e '{sent}' (score: {score:.2f}), "
                      f"levemente positivo e consistente com a projecao.")
    elif score <= -0.3:
        linhas.append(f"O sentimento de midia e '{sent}' (score: {score:.2f}), "
                      f"divergindo negativamente do sinal. Atenção ao risco de reversao.")
    elif score <= -0.05:
        linhas.append(f"O sentimento de midia e '{sent}' (score: {score:.2f}), "
                      f"levemente pessimista. Monitorar fluxo de noticias.")
    else:
        linhas.append(f"O sentimento de midia e neutro (score: {score:.2f}), "
                      f"sem viés claro de noticias no periodo.")

    # Confluência IA x Sentimento
    ia_alta = sinal == "ALTA"
    sent_pos = score >= 0.05
    if ia_alta and sent_pos:
        linhas.append("CONFLUENCIA: IA e Sentimento apontam na MESMA direcao (alta). "
                      "Sinal com maior consistência.")
    elif not ia_alta and not sent_pos:
        linhas.append("CONFLUENCIA: IA e Sentimento apontam na MESMA direcao (baixa). "
                      "Sinal com maior consistência.")
    elif ia_alta and not sent_pos:
        linhas.append("DIVERGENCIA: IA e Sentimento apontam em direcoes opostas. "
                      "Mercado pode ser contraditorio -- maior incerteza.")
    elif not ia_alta and sent_pos:
        linhas.append("DIVERGENCIA: IA e Sentimento apontam em direcoes opostas. "
                      "Mercado pode ser contraditorio -- maior incerteza.")

    return " ".join(linhas)


# ---------------------------------------------
# LEGENDA DAS COLUNAS
# ---------------------------------------------
LEGENDA = [
    ("Ativo",        "Codigo do ativo na B3 (ex: ITUB4, PETR4)."),
    ("Preco(R$)",    "Ultimo preco de fechamento real registrado pelo Yahoo Finance."),
    ("Prev(%)",      "Variacao percentual prevista pelo modelo XGBoost para o proximo pregao."),
    ("Sinal",        "Direcao da previsao: ALTA (modelo espera subida) ou BAIXA (espera queda)."),
    ("Conf(%)",      "Acuracia Direcional: % de vezes que o modelo acertou a direcao (sobe/cai) nos dados de teste historico. Acima de 55% e considerado bom."),
    ("RMSE",         "Raiz do Erro Quadratico Medio em R$. Representa a margem de erro tipica da previsao de preco."),
    ("R2",           "Poder de Explicacao do modelo (0 a 1). Quanto mais proximo de 1, melhor. Negativo = modelo sem poder preditivo."),
    ("Sentimento",   "Classificacao do humor das noticias do periodo (VADER/Alpha Vantage): Otimismo Extremo, Otimismo, Neutro, Pessimismo, Pessimismo Extremo."),
]


class PDFBoletim(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Boletim Diario de Projecoes (Morning Call)', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Gerado em: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} | B3 Quantum - IA de Investimentos', 0, 0, 'C')


def coletar_dados_relatorio(tickers):
    """Reune as metricas, sentimentos e a previsao do 1o dia util para cada ticker."""
    dados_compilados = []

    for ticker in tickers:
        previsoes = bd.carregar_previsoes_json(ticker)
        metricas = bd.carregar_metricas_json(ticker)
        sentimento = bd.carregar_sentimento_json(ticker)

        if not previsoes:
            continue

        previsoes.sort(key=lambda x: x['Data'])
        prev_hoje = previsoes[0]

        rmse = metricas.get('RMSE', 0) if metricas else 0
        r2 = metricas.get('R²', metricas.get('R2', 0)) if metricas else 0

        if sentimento:
            sent_score = sentimento.get('score_medio', 0.0)
            sent_class = sentimento.get('classificacao', 'Neutro')
        else:
            sent_score = 0.0
            sent_class = "Neutro"

        sinal = "ALTA" if prev_hoje['Previsao_Pct'] > 0 else "BAIXA"

        dados_compilados.append({
            "Ativo": ticker,
            "Preco Base": round(prev_hoje['Preco_Base'], 2),
            "Previsao Pct": round(prev_hoje['Previsao_Pct'], 4),
            "Sinal": sinal,
            "Confianca (%)": round(prev_hoje['Confianca'], 1),
            "RMSE": round(rmse, 4),
            "R2": round(r2, 4),
            "Sentimento": sent_class,
            "Score Sentimento": round(sent_score, 2)
        })

    return dados_compilados


def gerar_boletim_diario_csv(tickers):
    dados = coletar_dados_relatorio(tickers)
    if not dados:
        print("Nenhum dado encontrado para gerar relatorio.")
        return None

    hoje_str = datetime.now().strftime("%Y-%m-%d")
    caminho_arquivo = os.path.join(RELATORIOS_DIR, f'Boletim_Diario_{hoje_str}.csv')

    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        # Dados principais
        f.write("BOLETIM DIARIO DE PROJECOES - B3 QUANTUM\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("=== PROJECOES DO DIA ===\n")
        df = pd.DataFrame(dados)
        f.write(df.to_csv(index=False, sep=';'))

        f.write("\n=== RESUMO ANALITICO POR ATIVO ===\n")
        for row in sorted(dados, key=lambda x: x['Previsao Pct'], reverse=True):
            f.write(f"\n[{row['Ativo']}]\n")
            f.write(_interpretar_ativo(row) + "\n")

        f.write("\n=== LEGENDA DAS COLUNAS ===\n")
        for col, desc in LEGENDA:
            f.write(f"{col}: {desc}\n")

        f.write("\nNOTA: Este relatorio nao constitui recomendacao de investimento. Carater puramente analitico.\n")

    print(f"[RELATORIO] CSV gerado com sucesso: {caminho_arquivo}")
    return caminho_arquivo


def gerar_boletim_diario_pdf(tickers):
    dados = coletar_dados_relatorio(tickers)
    if not dados:
        return None

    pdf = PDFBoletim()
    pdf.alias_nb_pages()
    pdf.add_page()

    dados = sorted(dados, key=lambda x: x['Previsao Pct'], reverse=True)

    # --- Tabela Principal ---
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(30, 50, 90)
    pdf.set_text_color(255, 255, 255)
    col_widths = [20, 22, 22, 18, 22, 20, 20, 36]
    headers = ["Ativo", "Preco(R$)", "Prev(%)", "Sinal", "Conf(%)", "RMSE", "R2", "Sentimento"]

    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 10, h, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    fill_row = False
    for row in dados:
        pdf.set_fill_color(240, 245, 255) if fill_row else pdf.set_fill_color(255, 255, 255)
        fill_row = not fill_row

        pdf.cell(col_widths[0], 9, str(row['Ativo']), border=1, align='C', fill=True)
        pdf.cell(col_widths[1], 9, f"R$ {row['Preco Base']:.2f}", border=1, align='C', fill=True)

        if row['Sinal'] == "ALTA":
            pdf.set_text_color(0, 130, 0)
        else:
            pdf.set_text_color(190, 0, 0)
        pdf.cell(col_widths[2], 9, f"{row['Previsao Pct']:.2f}%", border=1, align='C', fill=True)
        pdf.cell(col_widths[3], 9, row['Sinal'], border=1, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)

        pdf.cell(col_widths[4], 9, f"{row['Confianca (%)']:.1f}%", border=1, align='C', fill=True)
        pdf.cell(col_widths[5], 9, f"{row['RMSE']:.4f}", border=1, align='C', fill=True)

        r2_val = row['R2']
        if r2_val >= 0.05:
            pdf.set_text_color(0, 130, 0)
        elif r2_val < 0:
            pdf.set_text_color(190, 0, 0)
        pdf.cell(col_widths[6], 9, f"{r2_val:.4f}", border=1, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)

        sent = row['Sentimento']
        score = row['Score Sentimento']
        if score >= 0.05:
            pdf.set_text_color(0, 130, 0)
        elif score <= -0.05:
            pdf.set_text_color(190, 0, 0)
        else:
            pdf.set_text_color(100, 100, 100)
        pdf.cell(col_widths[7], 9, sent, border=1, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    # --- Resumo Analítico por Ativo ---
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, '  Resumo Analitico por Ativo', border=0, align='L', fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    for row in dados:
        pdf.set_font('Arial', 'B', 10)
        if row['Sinal'] == "ALTA":
            pdf.set_text_color(0, 120, 0)
        else:
            pdf.set_text_color(180, 0, 0)
        pdf.cell(0, 8, f"[{row['Ativo']}]  Sinal: {row['Sinal']} {row['Previsao Pct']:.2f}%", ln=True)
        pdf.set_text_color(0, 0, 0)

        pdf.set_font('Arial', '', 9)
        texto = _interpretar_ativo(row)
        pdf.multi_cell(0, 5, texto)
        pdf.ln(4)

    # --- Legenda das Colunas ---
    pdf.ln(4)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, '  Legenda das Colunas', border=0, align='L', fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    for col, desc in LEGENDA:
        pdf.set_font('Arial', 'B', 9)
        pdf.multi_cell(0, 6, f"{col}: ", ln=True)
        pdf.set_x(pdf.get_x() + 8)
        pdf.set_font('Arial', '', 9)
        # Indent description slightly
        pdf.cell(8, 5, '', ln=False)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(1)
    pdf.ln(4)

    # --- Nota de Rodapé ---
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, "NOTA: As projecoes acima sao baseadas no modelo XGBoost otimizado e analise de sentimento de noticias. "
                         "Este relatorio nao constitui recomendacao de investimento, sendo de carater puramente analitico.")

    hoje_str = datetime.now().strftime("%Y-%m-%d")
    caminho_arquivo = os.path.join(RELATORIOS_DIR, f'Boletim_Diario_{hoje_str}.pdf')
    pdf.output(caminho_arquivo)
    print(f"[RELATORIO] PDF gerado com sucesso: {caminho_arquivo}")
    return caminho_arquivo


def gerar_relatorios_finais(tickers):
    print(f"\n{'='*60}")
    print(f"[RELATORIO] GERANDO RELATORIOS DO FECHAMENTO")
    print(f"{'='*60}")
    try:
        csv_path = gerar_boletim_diario_csv(tickers)
        pdf_path = gerar_boletim_diario_pdf(tickers)
        if csv_path and pdf_path:
            print(f"[RELATORIO] Todos os relatorios foram gerados e salvos na pasta /relatorios!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERRO] Erro ao gerar relatorios: {e}")


class PDFDossie(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Dossie Individual de Ativo - B3 Quantum', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Gerado em: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} | B3 Quantum', 0, 0, 'C')


def gerar_dossie_individual_pdf(ticker):
    """Gera um relatorio focado em um unico ativo com historico de 30 dias, previsoes e análise."""
    previsoes = bd.carregar_previsoes_json(ticker)
    metricas = bd.carregar_metricas_json(ticker)
    sentimento = bd.carregar_sentimento_json(ticker)
    historico = bd.carregar_historico_json(ticker)

    if not historico:
        print(f"[ERRO] Sem historico para o ativo {ticker}")
        return None

    pdf = PDFDossie()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Titulo
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Analise Completa: {ticker}", 0, 1, 'L')
    pdf.ln(3)

    # 1. Indicadores
    rmse = metricas.get('RMSE', 0) if metricas else 0
    r2 = metricas.get('R²', metricas.get('R2', 0)) if metricas else 0
    sent_class = sentimento.get('classificacao', 'Neutro') if sentimento else 'Neutro'
    sent_score = sentimento.get('score_medio', 0) if sentimento else 0

    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, '  1. Indicadores de Performance', border=0, fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font('Arial', '', 10)
    pdf.cell(65, 8, f"RMSE (Margem de Erro): R$ {rmse:.4f}", 0, 0)
    pdf.cell(65, 8, f"R2 (Poder Explicativo): {r2:.4f}", 0, 0)
    pdf.cell(65, 8, f"Sentimento: {sent_class} ({sent_score:.2f})", 0, 1)
    pdf.ln(5)

    # 2. Resumo Analítico
    if previsoes:
        previsoes.sort(key=lambda x: x['Data'])
        preco_base = previsoes[0]['Preco_Base']
        pct_d1 = previsoes[0]['Previsao_Pct']
        conf_d1 = previsoes[0]['Confianca']
        sinal = "ALTA" if pct_d1 > 0 else "BAIXA"

        row_analise = {
            "Ativo": ticker,
            "Preco Base": preco_base,
            "Previsao Pct": pct_d1,
            "Sinal": sinal,
            "Confianca (%)": conf_d1,
            "RMSE": rmse,
            "R2": r2,
            "Sentimento": sent_class,
            "Score Sentimento": sent_score,
        }

        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(20, 40, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 9, '  2. Resumo Analitico', border=0, fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, _interpretar_ativo(row_analise))
        pdf.ln(5)

    # 3. Previsões
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, '  3. Projecoes de IA (Proximos 10 dias uteis)', border=0, fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    if previsoes:
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(30, 50, 90)
        pdf.set_text_color(255, 255, 255)
        for h, w in [("Data", 40), ("Preco Previsto", 45), ("Variacao (%)", 35), ("Confianca (%)", 40)]:
            pdf.cell(w, 8, h, border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

        pdf.set_font('Arial', '', 10)
        for row in sorted(previsoes, key=lambda x: x['Data'])[:10]:
            pdf.cell(40, 8, str(row['Data']).split(' ')[0], border=1, align='C')
            pdf.cell(45, 8, f"R$ {row['Preco_Previsto']:.2f}", border=1, align='C')
            var = row['Previsao_Pct']
            if var > 0:
                pdf.set_text_color(0, 130, 0)
            else:
                pdf.set_text_color(190, 0, 0)
            pdf.cell(35, 8, f"{var:.2f}%", border=1, align='C')
            pdf.set_text_color(0, 0, 0)
            pdf.cell(40, 8, f"{row['Confianca']:.1f}%", border=1, align='C')
            pdf.ln()
    else:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 8, "Previsoes indisponiveis.", 0, 1)

    pdf.ln(8)

    # 4. Histórico
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, '  4. Historico Real de Cotacao (Ultimos 30 Pregoes)', border=0, fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    historico_recente = sorted(historico, key=lambda x: x['Date'], reverse=True)[:30]
    colunas_hist = ["Data", "Abertura", "Maxima", "Minima", "Fechamento", "Volume"]
    widths_hist = [30, 27, 27, 27, 28, 32]

    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 50, 90)
    pdf.set_text_color(255, 255, 255)
    for col, w in zip(colunas_hist, widths_hist):
        pdf.cell(w, 8, col, border=1, align='C', fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    pdf.set_font('Arial', '', 9)
    alt = False
    for row in historico_recente:
        pdf.set_fill_color(240, 245, 255) if alt else pdf.set_fill_color(255, 255, 255)
        alt = not alt
        dt = str(row['Date']).split(' ')[0]
        pdf.cell(widths_hist[0], 7, dt, border=1, align='C', fill=True)
        pdf.cell(widths_hist[1], 7, f"R$ {row['Open']:.2f}", border=1, align='C', fill=True)
        pdf.cell(widths_hist[2], 7, f"R$ {row['High']:.2f}", border=1, align='C', fill=True)
        pdf.cell(widths_hist[3], 7, f"R$ {row['Low']:.2f}", border=1, align='C', fill=True)
        pdf.cell(widths_hist[4], 7, f"R$ {row['Close']:.2f}", border=1, align='C', fill=True)
        vol = row['Volume']
        vol_str = f"{vol/1_000_000:.1f}M" if vol >= 1_000_000 else f"{vol:,}"
        pdf.cell(widths_hist[5], 7, vol_str, border=1, align='C', fill=True)
        pdf.ln()

    # 5. Legenda
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(20, 40, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, '  5. Legenda das Colunas do Boletim', border=0, fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font('Arial', '', 9)
    for col, desc in LEGENDA:
        pdf.set_font('Arial', 'B', 9)
        pdf.multi_cell(0, 6, f"{col}: ", ln=True)
        pdf.set_font('Arial', '', 9)
        pdf.cell(8, 5, '', ln=False)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(1)
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, "NOTA: Este relatorio nao constitui recomendacao de investimento. Carater puramente analitico.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_arquivo = os.path.join(RELATORIOS_DIR, f'Dossie_{ticker}_{timestamp}.pdf')
    pdf.output(caminho_arquivo)
    print(f"[RELATORIO] Dossie gerado com sucesso: {caminho_arquivo}")
    return caminho_arquivo


def gerar_dossie_individual_csv(ticker):
    """Gera um relatorio CSV focado em um unico ativo."""
    previsoes = bd.carregar_previsoes_json(ticker)
    historico = bd.carregar_historico_json(ticker)

    if not historico:
        return None

    linhas = []
    historico_recente = sorted(historico, key=lambda x: x['Date'], reverse=True)[:30]
    for row in historico_recente:
        dt = str(row['Date']).split(' ')[0]
        linhas.append({
            "Data": dt, "Tipo": "Historico Real",
            "Preco": round(row['Close'], 2), "Abertura": round(row['Open'], 2),
            "Maxima": round(row['High'], 2), "Minima": round(row['Low'], 2),
            "Volume": row['Volume'], "Variacao_Pct": "", "Confianca": ""
        })

    if previsoes:
        for row in sorted(previsoes, key=lambda x: x['Data'])[:10]:
            dt = str(row['Data']).split(' ')[0]
            linhas.append({
                "Data": dt, "Tipo": "Previsao IA",
                "Preco": round(row['Preco_Previsto'], 2), "Abertura": "", "Maxima": "",
                "Minima": "", "Volume": "",
                "Variacao_Pct": round(row['Previsao_Pct'], 2),
                "Confianca": round(row['Confianca'], 1)
            })

    df = pd.DataFrame(linhas).sort_values(by="Data", ascending=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_arquivo = os.path.join(RELATORIOS_DIR, f'Dossie_{ticker}_{timestamp}.csv')
    df.to_csv(caminho_arquivo, index=False, sep=';', encoding='utf-8')
    print(f"[RELATORIO] Dossie CSV gerado com sucesso: {caminho_arquivo}")
    return caminho_arquivo
