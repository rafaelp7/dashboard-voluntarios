import os
import re
import json
import glob
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (MODERNO)
# ==============================================================================
st.set_page_config(
    page_title="Gestão de Atividade Voluntária - Maringá",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; color: #ffffff; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.9; font-size: 0.95rem; }
    .section-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #2563eb;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .section-card.danger { border-left-color: #dc2626; }
    .section-card.warning { border-left-color: #d97706; }
    .section-card.info { border-left-color: #0891b2; }
    .section-card.purple { border-left-color: #7c3aed; }
    .section-title { font-size: 1.15rem; font-weight: 700; color: #1e293b; margin: 0; }
    .section-desc { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ESTRUTURA DE SETORES E ATIVIDADES
# ==============================================================================
SETORES_PADRAO = {
    "Setor 1": [
        'BR 14-2362 - ZONA 6 - MARINGÁ VELHO',
        'BR 14-2601 - JARDIM ESPANHA',
        'BR 14-0603 - VILA OPERÁRIA',
        'BR 14-0607 - VILA MORANGUEIRA',
        'BR 14-1115 - DISTRITO DE FLORIANO',
        'BR 14-1118 - JARDIM VITÓRIA',
        'BR 14-1399 - JARDIM VERÔNICA',
        'BR 14-1518 - PARQUE ITAIPU',
        'BR 14-1613 - PARQUE RESIDENCIAL AEROPORTO - 3ª PARTE',
        'BR 14-1614 - JARDIM CATEDRAL',
        'BR 14-1686 - JARDIM UNIVERSO',
        'BR 14-2380 - JARDIM ORIENTAL - DIAMANTE'
    ],
    "Setor 2": [
        'BR 14-0445 - DISTRITO DE IGUATEMI',
        'BR 14-0606 - VILA SANTA IZABEL',
        'BR 14-1611 - PARQUE HORTÊNCIA - 1ª PARTE',
        'BR 14-1615 - PARQUE DAS LARANJEIRAS',
        'BR 14-1748 - PARQUE AVENIDA',
        'BR 14-1749 - JARDIM OLÍMPICO',
        'BR 14-2174 - JARDIM OURO COLA',
        'BR 14-2296 - JARDIM MONTE REI',
        'BR 14-2446 - GLEBA PATRIMÔNIO MARINGÁ - JARDIM INDAIÁ'
    ],
    "Setor 3": [
        'BR 14-0602 - VILA SANTO ANTÔNIO',
        'BR 14-0605 - JARDIM ALVORADA',
        'BR 14-1116 - PARQUE RESIDENCIAL TUIUTI',
        'BR 14-1400 - JARDIM LIBERDADE',
        'BR 14-1612 - JARDIM ALVORADA III - EBENEZER',
        'BR 14-1635 - JARDIM PIATÃ',
        'BR 14-1636 - CONJUNTO REQUIÃO',
        'BR 14-1970 - CONJUNTO RESIDENCIAL GUAIAPÓ',
        'BR 14-2402 - LOTEAMENTO SUMARÉ'
    ]
}

IGREJA_PARA_SETOR = {
    igreja.strip(): setor
    for setor, lista in SETORES_PADRAO.items()
    for igreja in lista
}
TODAS_IGREJAS = list(IGREJA_PARA_SETOR.keys())

ATIVIDADES = [
    "Limpeza",
    "GEM",
    "Pátio",
    "Manutenção Preventiva",
    "Espaço Infantil",
    "Cozinha"
]

OBRIGATORIAS_FIXAS_PADRAO = ["Limpeza", "GEM", "Pátio"]
CONFIG_FILE = "config_obrigatoriedade.json"

# ==============================================================================
# FUNÇÕES DE CONFIGURAÇÃO DE OBRIGATORIEDADE (SUBPÁGINA COM SENHA)
# ==============================================================================
def carregar_config_obrigatoriedade():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ig in TODAS_IGREJAS:
                if ig not in data:
                    data[ig] = {at: (at in OBRIGATORIAS_FIXAS_PADRAO) for at in ATIVIDADES}
            return data
        except Exception:
            pass
    return {
        ig: {at: (at in OBRIGATORIAS_FIXAS_PADRAO) for at in ATIVIDADES}
        for ig in TODAS_IGREJAS
    }

def salvar_config_obrigatoriedade(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)

# ==============================================================================
# FUNÇÕES DE NORMALIZAÇÃO E LEITURA DE ARQUIVOS MÊS A MÊS
# ==============================================================================
def normalizar_igreja(nome):
    if pd.isna(nome):
        return ""
    s = str(nome).strip()
    m = re.match(r"^(BR\s*\d{2}-\d{4})", s.upper())
    if m:
        codigo = m.group(1).replace(" ", "")
        for ig in TODAS_IGREJAS:
            if ig.upper().replace(" ", "").startswith(codigo):
                return ig
    return s

def mapear_livro_para_atividade(livro):
    if pd.isna(livro):
        return None
    s = str(livro).upper().strip()
    if "ANEXO" in s and "ADM" in s:
        return None
    if "LIMPEZA" in s:
        return "Limpeza"
    if "GEM" in s:
        return "GEM"
    if "PÁTIO" in s or "PATIO" in s or "ESTACIONAMENTO" in s:
        return "Pátio"
    if "MANUTENÇÃO" in s or "MANUTENCAO" in s or "PREVENTIVA" in s:
        return "Manutenção Preventiva"
    if "INFANTIL" in s or "EBI" in s:
        return "Espaço Infantil"
    if "COZINHA" in s:
        return "Cozinha"
    return None

def descobrir_periodos():
    periodos = set()
    padrao = re.compile(r"(\d{2})-(\d{4})")
    for arq in os.listdir("."):
        low = arq.lower()
        if any(low.startswith(p) for p in ["tabela", "relatorio anexos", "fechamento mensal"]):
            m = padrao.search(arq)
            if m:
                periodos.add(f"{m.group(1)}-{m.group(2)}")
    return sorted(list(periodos), key=lambda x: (int(x.split("-")[1]), int(x.split("-")[0])), reverse=True)

def ler_planilha_flexivel(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    if ext == ".ods":
        return pd.read_excel(caminho, engine="odf")
    elif ext in [".xlsx", ".xls"]:
        return pd.read_excel(caminho)
    elif ext == ".csv":
        return pd.read_csv(caminho, sep=None, engine="python")
    return pd.DataFrame()

@st.cache_data(ttl=60)
def carregar_dados_periodo(periodo):
    mes_int = int(periodo.split("-")[0])
    ano_int = int(periodo.split("-")[1])

    # 1. Arquivo de Lançamentos: tabela mm-aaaa
    df_lanc = pd.DataFrame(columns=["Igreja", "Atividade", "Livro", "Data", "Horas", "Valor"])
    arquivos_tabela = [f for f in os.listdir(".") if f.lower().startswith(f"tabela {periodo}".lower())]
    if arquivos_tabela:
        raw_t = ler_planilha_flexivel(arquivos_tabela[0])
        col_loc = next((c for c in raw_t.columns if "localidade" in str(c).lower()), None)
        col_liv = next((c for c in raw_t.columns if "livro" in str(c).lower()), None)
        if col_loc and col_liv:
            raw_t = raw_t.dropna(subset=[col_loc, col_liv]).copy()
            raw_t["Igreja"] = raw_t[col_loc].apply(normalizar_igreja)
            raw_t["Atividade"] = raw_t[col_liv].apply(mapear_livro_para_atividade)
            df_lanc = raw_t[raw_t["Igreja"].isin(TODAS_IGREJAS) & raw_t["Atividade"].notna()].copy()

    # 2. Arquivo de Anexos: relatorio anexos mm-aaaa
    df_anexos = pd.DataFrame(columns=["Igreja", "Atividade", "Valor_Anexo", "Paginas_Estimadas"])
    arquivos_anexo = [f for f in os.listdir(".") if f.lower().startswith(f"relatorio anexos {periodo}".lower())]
    if arquivos_anexo:
        raw_a = ler_planilha_flexivel(arquivos_anexo[0])
        col_ig = next((c for c in raw_a.columns if "igreja" in str(c).lower() or "localidade" in str(c).lower()), None)
        if col_ig:
            raw_a["Igreja"] = raw_a[col_ig].apply(normalizar_igreja)
            raw_a = raw_a[raw_a["Igreja"].isin(TODAS_IGREJAS)].copy()
            mapa_col_ativ = {
                "Limpeza": next((c for c in raw_a.columns if "limpeza" in str(c).lower()), None),
                "GEM": next((c for c in raw_a.columns if "gem" in str(c).lower()), None),
                "Pátio": next((c for c in raw_a.columns if "pátio" in str(c).lower() or "patio" in str(c).lower()), None),
                "Espaço Infantil": next((c for c in raw_a.columns if "infantil" in str(c).lower()), None),
                "Manutenção Preventiva": next((c for c in raw_a.columns if "manuten" in str(c).lower()), None),
                "Cozinha": next((c for c in raw_a.columns if "cozinha" in str(c).lower()), None),
            }
            linhas_anexo = []
            for _, row in raw_a.iterrows():
                ig = row["Igreja"]
                for ativ, col_name in mapa_col_ativ.items():
                    val = 0.0
                    if col_name and col_name in raw_a.columns:
                        v = pd.to_numeric(row[col_name], errors="coerce")
                        val = 0.0 if pd.isna(v) else float(v)
                    # Na planilha relatorio anexos, os valores já vêm multiplicados por 14 (ex: 14, 28, 42...) ou em páginas
                    # Se for múltiplo >= 14 ou valor bruto, tratamos de forma consistente:
                    # Regra 6: relatorio anexos possui quantidade de páginas multiplicada por 14 (linhas de apontamentos)
                    valor_provavel = val if (val == 0 or val >= 14) else val * 14
                    paginas = val / 14.0 if val >= 14 else val
                    linhas_anexo.append({
                        "Igreja": ig,
                        "Atividade": ativ,
                        "Valor_Anexo": valor_provavel,
                        "Paginas_Estimadas": paginas
                    })
            df_anexos = pd.DataFrame(linhas_anexo)

    # 3. Arquivo de Fechamento Mensal: FECHAMENTO MENSAL mm-aaaa.txt
    df_fech = pd.DataFrame(columns=["Igreja", "Status"])
    arquivos_fech = [f for f in os.listdir(".") if f.lower().startswith(f"fechamento mensal {periodo}".lower())]
    if arquivos_fech:
        linhas_f = []
        with open(arquivos_fech[0], "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or "fechamento mensal" in line.lower() or line.lower().startswith("localidade"):
                    continue
                partes = re.split(r"\t+|\s{2,}", line)
                if len(partes) >= 2:
                    loc, st_val = partes[0].strip(), partes[-1].strip()
                else:
                    m_st = re.search(r"(Encerrado|Aberto)$", line, re.IGNORECASE)
                    if m_st:
                        st_val = m_st.group(1)
                        loc = line[:m_st.start()].strip()
                    else:
                        continue
                ig_norm = normalizar_igreja(loc)
                if ig_norm in TODAS_IGREJAS:
                    linhas_f.append({"Igreja": ig_norm, "Status": st_val.capitalize()})
        df_fech = pd.DataFrame(linhas_f)

    # 4. Arquivo Formulário Qualitativo: FORMULÁRIO QUALITATIVO YYYY (respostas).xlsx
    df_qual_ativ = pd.DataFrame(columns=["Igreja", "Atividade", "Preenchido", "Rasuras", "Erros_Horario", "Campos_Branco", "Total_Erros"])
    arquivos_qual = [f for f in os.listdir(".") if "qualitativo" in f.lower() and (f.endswith(".xlsx") or f.endswith(".ods"))]
    if arquivos_qual:
        raw_q = ler_planilha_flexivel(arquivos_qual[0])
        col_mes = next((c for c in raw_q.columns if str(c).strip().upper() == "MÊS" or "mes" in str(c).lower()), None)
        col_ano = next((c for c in raw_q.columns if str(c).strip().upper() == "ANO"), None)
        if col_mes is not None:
            raw_q = raw_q[pd.to_numeric(raw_q[col_mes], errors="coerce") == mes_int].copy()
        if col_ano is not None and not raw_q.empty:
            raw_q = raw_q[pd.to_numeric(raw_q[col_ano], errors="coerce") == ano_int].copy()

        cols_igreja = [c for c in raw_q.columns if "casa de oração" in str(c).lower() or "casa de oracao" in str(c).lower()]
        col_assinalar = next((c for c in raw_q.columns if "assinalar as atividades" in str(c).lower()), None)

        def obter_igreja_linha(r):
            for c in cols_igreja:
                if pd.notna(r[c]) and str(r[c]).strip():
                    return normalizar_igreja(r[c])
            return ""

        if not raw_q.empty:
            raw_q["Igreja"] = raw_q.apply(obter_igreja_linha, axis=1)
            raw_q = raw_q[raw_q["Igreja"].isin(TODAS_IGREJAS)].copy()
            # Caso haja mais de uma resposta para a mesma igreja no mês, mantém a mais recente
            raw_q = raw_q.drop_duplicates(subset=["Igreja"], keep="last")

        mapa_erros_cols = {
            "Limpeza": ("(limpeza)", ["LIMPEZA"]),
            "GEM": ("(gem)", ["GEM"]),
            "Pátio": ("(pátio)", ["PÁTIO", "PATIO", "ESTACIONAMENTO"]),
            "Manutenção Preventiva": ("(manutenção preventiva)", ["MANUTENÇÃO", "MANUTENCAO", "PREVENTIVA"]),
            "Espaço Infantil": ("(espaço infantil)", ["ESPAÇO INFANTIL", "ESPACO INFANTIL", "INFANTIL"]),
            "Cozinha": ("(cozinha)", ["COZINHA"])
        }

        reg_qual = []
        for _, r in raw_q.iterrows():
            ig = r["Igreja"]
            texto_assinalado = str(r[col_assinalar]).upper() if (col_assinalar and pd.notna(r[col_assinalar])) else ""
            for ativ, (sufixo, termos_busca) in mapa_erros_cols.items():
                foi_analisada = any(t in texto_assinalado for t in termos_busca)
                c_ras = next((c for c in raw_q.columns if "rasuras" in str(c).lower() and sufixo in str(c).lower()), None)
                c_hor = next((c for c in raw_q.columns if "horário" in str(c).lower() and sufixo in str(c).lower()), None)
                c_bra = next((c for c in raw_q.columns if "branco" in str(c).lower() and sufixo in str(c).lower()), None)

                def num_seguro(col):
                    if not col:
                        return 0
                    val = pd.to_numeric(r[col], errors="coerce")
                    return 0 if pd.isna(val) else int(round(float(val)))

                v_ras = num_seguro(c_ras)
                v_hor = num_seguro(c_hor)
                v_bra = num_seguro(c_bra)
                tot_err = v_ras + v_hor + v_bra

                # Se reportou erro numérico > 0 na atividade, também considera como analisada
                if tot_err > 0:
                    foi_analisada = True

                reg_qual.append({
                    "Igreja": ig,
                    "Atividade": ativ,
                    "Preenchido": foi_analisada,
                    "Rasuras": int(v_ras),
                    "Erros_Horario": int(v_hor),
                    "Campos_Branco": int(v_bra),
                    "Total_Erros": int(tot_err)
                })
        if reg_qual:
            df_qual_ativ = pd.DataFrame(reg_qual)

    return df_lanc, df_anexos, df_fech, df_qual_ativ

# ==============================================================================
# CONSOLIDAÇÃO E REGRAS DE NEGÓCIO (ITENS 1 A 6)
# ==============================================================================
def processar_auditoria(periodo, config_obrig):
    df_lanc, df_anexos, df_fech, df_qual = carregar_dados_periodo(periodo)

    # Contagem de lançamentos por Igreja e Atividade
    cont_lanc = df_lanc.groupby(["Igreja", "Atividade"]).size().reset_index(name="Qtd_Lancamentos")

    # Malha completa de Igrejas x Atividades
    malha = []
    for ig in TODAS_IGREJAS:
        setor = IGREJA_PARA_SETOR[ig]
        for ativ in ATIVIDADES:
            malha.append({"Setor": setor, "Igreja": ig, "Atividade": ativ})
    df_base = pd.DataFrame(malha)

    # Merge Lançamentos
    df_base = df_base.merge(cont_lanc, on=["Igreja", "Atividade"], how="left")
    df_base["Qtd_Lancamentos"] = df_base["Qtd_Lancamentos"].fillna(0).astype(int)

    # Merge Anexos
    if not df_anexos.empty:
        df_base = df_base.merge(df_anexos, on=["Igreja", "Atividade"], how="left")
    else:
        df_base["Valor_Anexo"] = 0.0
        df_base["Paginas_Estimadas"] = 0.0
    df_base["Valor_Anexo"] = df_base["Valor_Anexo"].fillna(0).astype(int)
    df_base["Paginas_Estimadas"] = df_base["Paginas_Estimadas"].fillna(0.0).round(1)

    # Merge Qualitativo
    if not df_qual.empty:
        df_base = df_base.merge(df_qual, on=["Igreja", "Atividade"], how="left")
    else:
        df_base["Preenchido"] = False
        df_base["Rasuras"] = 0
        df_base["Erros_Horario"] = 0
        df_base["Campos_Branco"] = 0
        df_base["Total_Erros"] = 0

    df_base["Preenchido"] = df_base["Preenchido"].fillna(False).astype(bool)
    for col_e in ["Rasuras", "Erros_Horario", "Campos_Branco", "Total_Erros"]:
        df_base[col_e] = df_base[col_e].fillna(0).astype(int)

    # Merge Fechamento Mensal
    if not df_fech.empty:
        df_base = df_base.merge(df_fech, on="Igreja", how="left")
    else:
        df_base["Status"] = "Não informado"
    df_base["Status"] = df_base["Status"].fillna("Não encontrado")

    # Determinação de Obrigatoriedade e Origem da Pendência (Regra 1)
    origens = []
    obrigatorio_flags = []
    for _, row in df_base.iterrows():
        ig = row["Igreja"]
        ativ = row["Atividade"]
        tem_anexo = row["Valor_Anexo"] > 0
        tem_qual = row["Preenchido"]
        cfg_fixa = config_obrig.get(ig, {}).get(ativ, ativ in OBRIGATORIAS_FIXAS_PADRAO)

        motivos = []
        if cfg_fixa:
            motivos.append("Atividade obrigatória fixa da igreja")
        if tem_anexo:
            motivos.append(f"Anexou formulário com apontamentos ({row['Valor_Anexo']} linhas esp. no relatório anexos)")
        if tem_qual:
            motivos.append("Assinalou/preencheu atividade no Formulário Qualitativo")

        eh_obrig = cfg_fixa or tem_anexo or tem_qual
        obrigatorio_flags.append(eh_obrig)
        origens.append(" | ".join(motivos) if motivos else "Não obrigatório")

    df_base["Obrigatorio"] = obrigatorio_flags
    df_base["Origem_Pendencia"] = origens

    return df_base

# ==============================================================================
# GERADORES DE RELATÓRIO (HTML MODERNO E PDF)
# ==============================================================================
def gerar_relatorio_html(periodo, filtro_info, df1, df2, df3, df4, df6):
    data_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Pendências - Atividade Voluntária ({periodo})</title>
        <style>
            body {{ font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #1e293b; background: #f8fafc; margin: 0; padding: 30px; }}
            .container {{ max-width: 1100px; margin: auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }}
            .header {{ border-bottom: 3px solid #1e3a8a; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: #1e3a8a; font-size: 24px; }}
            .header p {{ margin: 4px 0 0 0; color: #64748b; font-size: 13px; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 30px; }}
            .card {{ background: #f1f5f9; padding: 14px; border-radius: 8px; text-align: center; border-top: 4px solid #1e3a8a; }}
            .card h3 {{ margin: 0; font-size: 22px; color: #0f172a; }}
            .card span {{ font-size: 11px; color: #475569; text-transform: uppercase; font-weight: 600; }}
            h2 {{ color: #1e3a8a; font-size: 16px; margin-top: 28px; border-left: 4px solid #2563eb; padding-left: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
            th {{ background: #1e3a8a; color: white; text-align: left; padding: 9px 10px; }}
            td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
            tr:nth-child(even) {{ background: #f8fafc; }}
            .ok-msg {{ color: #16a34a; font-weight: 600; font-size: 13px; padding: 10px; background: #f0fdf4; border-radius: 6px; }}
            .note {{ font-size: 11px; color: #64748b; background: #fffbeb; border: 1px solid #fde68a; padding: 10px; border-radius: 6px; margin-top: 8px; }}
            @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>Relatório de Auditoria e Pendências - Atividade Voluntária</h1>
                    <p>Congregação Cristã no Brasil - Maringá / PR | Competência: <strong>{periodo}</strong></p>
                    <p>Filtros Aplicados: {filtro_info}</p>
                </div>
                <div style="text-align:right; font-size:12px; color:#64748b;">
                    Emitido em:<br><strong>{data_emissao}</strong>
                </div>
            </div>

            <div class="summary-grid">
                <div class="card"><h3>{len(df1)}</h3><span>1. Sem Lançamento (Obrig.)</span></div>
                <div class="card"><h3>{len(df2)}</h3><span>2. Anexo/Qualit. s/ Lanç.</span></div>
                <div class="card"><h3>{len(df3)}</h3><span>3. Fechamento em Aberto</span></div>
                <div class="card"><h3>{len(df4)}</h3><span>4. Sem Qualitativo</span></div>
                <div class="card"><h3>{len(df6)}</h3><span>6. Divergência Batimento</span></div>
            </div>

            <h2>1. Igrejas que não constam lançamento em atividades obrigatórias</h2>
            {df1.to_html(index=False) if not df1.empty else '<div class="ok-msg">✔ Nenhuma pendência encontrada nesta categoria.</div>'}

            <h2>2. Igrejas com Anexos ou Qualitativo preenchido, mas sem lançamento na Tabela</h2>
            {df2.to_html(index=False) if not df2.empty else '<div class="ok-msg">✔ Nenhuma pendência encontrada nesta categoria.</div>'}

            <h2>3. Igrejas que não realizaram o Encerramento Mensal</h2>
            {df3.to_html(index=False) if not df3.empty else '<div class="ok-msg">✔ Todas as igrejas filtradas estão com fechamento encerrado.</div>'}

            <h2>4. Igrejas pendentes de preenchimento do Formulário Qualitativo (com movimento/anexo)</h2>
            {df4.to_html(index=False) if not df4.empty else '<div class="ok-msg">✔ Todos os qualitativos exigidos foram preenchidos.</div>'}

            <h2>6. Batimento: Quantidade Provável (Anexos x 14) vs Lançamentos Realizados</h2>
            <div class="note">
                <strong>Observação Metodológica:</strong> O cálculo multiplica a quantidade de páginas do relatório de anexos por 14 linhas de apontamentos.
                Diferenças inferiores a 14 indicam provável falta de lançamento, porém folhas anexadas a mais ou nomenclatura incorreta podem gerar divergências.
            </div>
            {df6.to_html(index=False) if not df6.empty else '<div class="ok-msg">✔ Nenhuma divergência de batimento identificada.</div>'}
        </div>
    </body>
    </html>
    """
    return html.encode("utf-8")

def limpar_texto_pdf(txt):
    return str(txt).encode("latin-1", "replace").decode("latin-1")

def gerar_relatorio_pdf(periodo, filtro_info, sec_list):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 15)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 10, limpar_texto_pdf(f"RELATORIO DE PENDENCIAS - ATIVIDADE VOLUNTARIA MARINGA ({periodo})"), ln=True)

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, limpar_texto_pdf(f"Filtros: {filtro_info} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"), ln=True)
    pdf.ln(3)

    for titulo, df_sec in sec_list:
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 236, 245)
        pdf.set_text_color(20, 40, 90)
        pdf.cell(0, 8, limpar_texto_pdf(f" {titulo} ({len(df_sec)} registros)"), ln=True, fill=True)
        pdf.ln(1)

        if df_sec.empty:
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(34, 139, 34)
            pdf.cell(0, 6, limpar_texto_pdf("Nenhuma pendencia encontrada para este item."), ln=True)
            pdf.ln(3)
            continue

        cols = list(df_sec.columns)
        largura_total = 275
        larg_col = largura_total / len(cols)

        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(0, 0, 0)
        for c in cols:
            pdf.cell(larg_col, 6, limpar_texto_pdf(str(c)[:30]), border=1)
        pdf.ln()

        pdf.set_font("Arial", "", 7)
        for _, r in df_sec.iterrows():
            for c in cols:
                val_str = str(r[c])
                if len(val_str) > 42:
                    val_str = val_str[:39] + "..."
                pdf.cell(larg_col, 5.5, limpar_texto_pdf(val_str), border=1)
            pdf.ln()
        pdf.ln(4)

    return pdf.output(dest="S").encode("latin-1")

# ==============================================================================
# INTERFACE PRINCIPAL E BARRA LATERAL
# ==============================================================================
periodos_disp = descobrir_periodos()
config_obrig = carregar_config_obrigatoriedade()

with st.sidebar:
    st.markdown("### 🏛️ Navegação")
    pagina = st.radio(
        "Selecione a página:",
        ["📊 Painel de Auditoria e Pendências", "🔐 Configurar Obrigatoriedade"],
        index=0
    )
    st.markdown("---")

    if periodos_disp:
        periodo_sel = st.selectbox("📅 Competência (mm-aaaa):", periodos_disp, index=0)
    else:
        st.error("Nenhum arquivo mensal (`mm-aaaa`) encontrado no diretório.")
        st.stop()

    st.markdown("### 🔍 Filtros Independentes")
    setores_opcoes = ["Todos"] + list(SETORES_PADRAO.keys())
    filtro_setor = st.multiselect("Setor:", options= list(SETORES_PADRAO.keys()), default=list(SETORES_PADRAO.keys()))

    # Lista de igrejas respeitando o filtro de setor (mas permitindo seleção independente)
    igrejas_disponiveis = [
        ig for ig in TODAS_IGREJAS
        if (not filtro_setor or IGREJA_PARA_SETOR[ig] in filtro_setor)
    ]
    filtro_igreja = st.multiselect("Igreja (Casa de Oração):", options=igrejas_disponiveis, default=[])
    filtro_atividade = st.multiselect("Atividade:", options=ATIVIDADES, default=[])

    if st.button("🔄 Recarregar Arquivos do GitHub", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==============================================================================
# SUBPÁGINA: CONFIGURAR OBRIGATORIEDADE POR IGREJA (SENHA: voluntarios)
# ==============================================================================
if pagina == "🔐 Configurar Obrigatoriedade":
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Configuração de Atividades Obrigatórias por Igreja</h1>
        <p>Marque abaixo quais atividades são fixas/obrigatórias em cada Casa de Oração.</p>
    </div>
    """, unsafe_allow_html=True)

    senha_digitada = st.text_input("Digite a senha de acesso para liberar a edição:", type="password")
    if senha_digitada != "voluntarios":
        st.warning("🔒 Informe a senha padrão (`voluntarios`) para visualizar e editar as regras de obrigatoriedade.")
        st.stop()

    st.success("🔓 Acesso liberado! As alterações salvas aqui refletem imediatamente na crítica do Item 1.")

    linhas_cfg = []
    for ig in TODAS_IGREJAS:
        row_d = {"Setor": IGREJA_PARA_SETOR[ig], "Igreja": ig}
        for at in ATIVIDADES:
            row_d[at] = bool(config_obrig.get(ig, {}).get(at, at in OBRIGATORIAS_FIXAS_PADRAO))
        linhas_cfg.append(row_d)
    df_cfg = pd.DataFrame(linhas_cfg)

    setor_cfg_filtro = st.selectbox("Filtrar tabela por Setor:", ["Todos"] + list(SETORES_PADRAO.keys()))
    if setor_cfg_filtro != "Todos":
        df_cfg_view = df_cfg[df_cfg["Setor"] == setor_cfg_filtro].copy()
    else:
        df_cfg_view = df_cfg.copy()

    df_editado = st.data_editor(
        df_cfg_view,
        disabled=["Setor", "Igreja"],
        use_container_width=True,
        hide_index=True,
        height=600
    )

    col_b1, col_b2 = st.columns([1, 3])
    with col_b1:
        if st.button("💾 Salvar Configurações", type="primary", use_container_width=True):
            for _, r in df_editado.iterrows():
                ig_k = r["Igreja"]
                config_obrig[ig_k] = {at: bool(r[at]) for at in ATIVIDADES}
            salvar_config_obrigatoriedade(config_obrig)
            st.toast("Configurações salvas com sucesso!", icon="✅")
            st.success("Obrigatoriedades atualizadas com sucesso!")
    with col_b2:
        if st.button("↩️ Restaurar Padrão (Limpeza, GEM e Pátio obrigatórios)", use_container_width=False):
            padrao_novo = {
                ig: {at: (at in OBRIGATORIAS_FIXAS_PADRAO) for at in ATIVIDADES}
                for ig in TODAS_IGREJAS
            }
            salvar_config_obrigatoriedade(padrao_novo)
            st.rerun()

# ==============================================================================
# PÁGINA PRINCIPAL: PAINEL DE AUDITORIA E PENDÊNCIAS (ORDEM 1 A 6)
# ==============================================================================
else:
    df_auditoria = processar_auditoria(periodo_sel, config_obrig)

    # Aplicação dos filtros independentes (Setor, Igreja e Atividade)
    df_filtrado = df_auditoria.copy()
    if filtro_setor:
        df_filtrado = df_filtrado[df_filtrado["Setor"].isin(filtro_setor)]
    if filtro_igreja:
        df_filtrado = df_filtrado[df_filtrado["Igreja"].isin(filtro_igreja)]
    if filtro_atividade:
        df_filtrado = df_filtrado[df_filtrado["Atividade"].isin(filtro_atividade)]

    # Processamento das 6 seções na ordem solicitada
    # 1º - Sem lançamento na tabela mm-aaaa, sendo obrigatório (Fixo/Config ou Anexo > 0 ou Qualitativo preenchido)
    df_item1 = df_filtrado[
        (df_filtrado["Obrigatorio"] == True) &
        (df_filtrado["Qtd_Lancamentos"] == 0)
    ][["Setor", "Igreja", "Atividade", "Origem_Pendencia", "Valor_Anexo", "Preenchido"]].rename(columns={
        "Origem_Pendencia": "De onde vem a pendência",
        "Valor_Anexo": "Apontamentos Esperados (Anexo)",
        "Preenchido": "Preencheu Qualitativo?"
    })

    # 2º - Anexaram formulários com apontamentos (>0) OU preencheram qualitativo, mas NÃO fizeram lançamentos
    df_item2 = df_filtrado[
        ((df_filtrado["Valor_Anexo"] > 0) | (df_filtrado["Preenchido"] == True)) &
        (df_filtrado["Qtd_Lancamentos"] == 0)
    ].copy()
    df_item2["Motivo Específico"] = df_item2.apply(
        lambda r: "Anexou formulário + Preencheu Qualitativo sem lançar"
        if (r["Valor_Anexo"] > 0 and r["Preenchido"])
        else ("Anexou formulário (relatório anexos) sem lançar" if r["Valor_Anexo"] > 0 else "Preencheu Qualitativo sem lançar"),
        axis=1
    )
    df_item2 = df_item2[["Setor", "Igreja", "Atividade", "Motivo Específico", "Valor_Anexo", "Qtd_Lancamentos"]].rename(columns={
        "Valor_Anexo": "Linhas Esperadas (Anexos)",
        "Qtd_Lancamentos": "Lançamentos na Tabela"
    })

    # 3º - Igrejas que não fizeram o encerramento mensal (Status != Encerrado)
    df_item3 = (
        df_filtrado[["Setor", "Igreja", "Status"]]
        .drop_duplicates()
        .query("Status != 'Encerrado'")
        .sort_values(["Setor", "Igreja"])
        .rename(columns={"Status": "Status Fechamento Mensal"})
    )

    # 4º - Igrejas que não preencheram (por atividade) o qualitativo, ficando pendente SOMENTE atividades com lançamentos ou anexos
    df_item4 = df_filtrado[
        (df_filtrado["Preenchido"] == False) &
        ((df_filtrado["Qtd_Lancamentos"] > 0) | (df_filtrado["Valor_Anexo"] > 0))
    ].copy()
    df_item4["Gatilho da Obrigatoriedade"] = df_item4.apply(
        lambda r: f"Possui {r['Qtd_Lancamentos']} lançamento(s) e {r['Valor_Anexo']} linha(s) de anexo"
        if (r["Qtd_Lancamentos"] > 0 and r["Valor_Anexo"] > 0)
        else (f"Possui {r['Qtd_Lancamentos']} lançamento(s) na tabela" if r["Qtd_Lancamentos"] > 0 else f"Possui anexo ({r['Valor_Anexo']} linhas esp.)"),
        axis=1
    )
    df_item4 = df_item4[["Setor", "Igreja", "Atividade", "Gatilho da Obrigatoriedade", "Qtd_Lancamentos", "Valor_Anexo"]].rename(columns={
        "Qtd_Lancamentos": "Lançamentos Realizados",
        "Valor_Anexo": "Linhas no Anexo"
    })

    # 6º - Batimento: Anexo (Páginas x 14) vs Lançamentos Realizados
    df_item6 = df_filtrado[
        (df_filtrado["Valor_Anexo"] > 0) | (df_filtrado["Qtd_Lancamentos"] > 0)
    ].copy()
    df_item6["Diferenca"] = df_item6["Valor_Anexo"] - df_item6["Qtd_Lancamentos"]

    def classificar_batimento(r):
        esp = r["Valor_Anexo"]
        real = r["Qtd_Lancamentos"]
        if esp == 0 and real > 0:
            return "⚠️ Lançou na tabela, mas consta 0 no Relatório de Anexos"
        if real == 0 and esp > 0:
            return f"🚨 Sem lançamentos (Esperado: ~{esp} lançamentos)"
        if real < esp:
            faltam = esp - real
            return f"🔻 Abaixo do esperado: Faltam aprox. {faltam} lançamento(s) (possível folha parcial ou lançamento pendente)"
        if real == esp:
            return "✅ Batimento Exato (14 por página)"
        return f"ℹ️ Acima da estimativa (+{real - esp} lançamentos que o múltiplo de 14)"

    df_item6["Diagnóstico do Batimento"] = df_item6.apply(classificar_batimento, axis=1)
    # Filtra para destacar onde há alerta/divergência ou abaixo do esperado
    df_item6_pend = df_item6[df_item6["Qtd_Lancamentos"] < df_item6["Valor_Anexo"]].copy()

    # Cabeçalho Principal e Botões de Relatório
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 Painel de Auditoria - Atividade Voluntária (Maringá)</h1>
        <p>Competência em análise: <strong>{periodo_sel}</strong> | Monitoramento automático de Lançamentos, Anexos, Fechamento e Qualitativo</p>
    </div>
    """, unsafe_allow_html=True)

    # KPIs de Resumo no Topo
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("1️⃣ Sem Lançamento (Obrig.)", f"{len(df_item1)}", delta="Crítico" if len(df_item1) > 0 else "Em dia", delta_color="inverse")
    k2.metric("2️⃣ Anexo/Qualit. s/ Lanç.", f"{len(df_item2)}", delta="Atenção" if len(df_item2) > 0 else "Em dia", delta_color="inverse")
    k3.metric("3️⃣ Fechamento Aberto", f"{len(df_item3)}", delta="Pendente" if len(df_item3) > 0 else "Encerrado", delta_color="inverse")
    k4.metric("4️⃣ Qualitativo Pendente", f"{len(df_item4)}", delta="Pendente" if len(df_item4) > 0 else "Em dia", delta_color="inverse")
    k5.metric("6️⃣ Abaixo do Batimento (x14)", f"{len(df_item6_pend)}", delta="Conferir" if len(df_item6_pend) > 0 else "OK", delta_color="inverse")

    # Barra de Exportação de Relatórios Bonitos
    resumo_filtros = f"Setores: {', '.join(filtro_setor) if filtro_setor else 'Todos'} | Igrejas: {len(filtro_igreja) if filtro_igreja else 'Todas'} | Atividades: {', '.join(filtro_atividade) if filtro_atividade else 'Todas'}"
    col_exp1, col_exp2, col_exp3 = st.columns([2, 2, 2])
    with col_exp1:
        html_bytes = gerar_relatorio_html(
            periodo_sel, resumo_filtros,
            df_item1, df_item2, df_item3, df_item4,
            df_item6_pend[["Setor", "Igreja", "Atividade", "Paginas_Estimadas", "Valor_Anexo", "Qtd_Lancamentos", "Diagnóstico do Batimento"]]
        )
        st.download_button(
            label="🖨️ Baixar Relatório Completo Estilizado (HTML / Imprimir)",
            data=html_bytes,
            file_name=f"Relatorio_Pendencias_{periodo_sel}.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )
    with col_exp2:
        pdf_bytes = gerar_relatorio_pdf(
            periodo_sel, resumo_filtros,
            [
                ("1. Sem Lancamento em Atividade Obrigatoria", df_item1),
                ("2. Anexo ou Qualitativo Preenchido Sem Lancamento", df_item2),
                ("3. Igrejas Sem Encerramento Mensal", df_item3),
                ("4. Pendentes de Formulario Qualitativo", df_item4),
                ("6. Batimento Abaixo do Esperado (Paginas x 14)", df_item6_pend[["Setor", "Igreja", "Atividade", "Valor_Anexo", "Qtd_Lancamentos", "Diagnóstico do Batimento"]])
            ]
        )
        st.download_button(
            label="📄 Baixar Relatório Executivo (PDF)",
            data=pdf_bytes,
            file_name=f"Relatorio_Pendencias_{periodo_sel}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_exp3:
        # Gerador de resumo rápido para WhatsApp
        linhas_zap = [f"*📋 RESUMO DE PENDÊNCIAS - {periodo_sel}*"]
        linhas_zap.append(f"• Sem Lançamento (Obrig.): *{len(df_item1)}*")
        linhas_zap.append(f"• Anexo/Qualit. s/ Lanç.: *{len(df_item2)}*")
        linhas_zap.append(f"• Fechamento em Aberto: *{len(df_item3)}*")
        linhas_zap.append(f"• Qualitativo Pendente: *{len(df_item4)}*")
        linhas_zap.append(f"• Divergência Batimento: *{len(df_item6_pend)}*")
        texto_zap = "\n".join(linhas_zap)
        st.download_button(
            label="📲 Baixar Resumo p/ WhatsApp (.txt)",
            data=texto_zap.encode("utf-8"),
            file_name=f"Resumo_WhatsApp_{periodo_sel}.txt",
            mime="text/plain",
            use_container_width=True
        )

    # --------------------------------------------------------------------------
    # ORDEM 1: IGREJAS QUE NÃO CONSTAM LANÇAMENTO EM ATIVIDADES OBRIGATÓRIAS
    # --------------------------------------------------------------------------
    st.markdown("""
    <div class="section-card danger">
        <div class="section-title">1º — Igrejas sem Lançamento em Atividades Obrigatórias</div>
        <div class="section-desc">
            Critica apenas atividades obrigatórias (Limpeza, GEM e Pátio por padrão/configuração, além de Manutenção Preventiva, Cozinha e Espaço Infantil quando houver página no Relatório de Anexos > 0 ou apontamento no Formulário Qualitativo).
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_item1.empty:
        st.success("✅ Nenhuma pendência! Todas as atividades obrigatórias possuem lançamentos registrados.")
    else:
        st.dataframe(df_item1, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # ORDEM 2: ANEXARAM FORMULÁRIOS OU PREENCHERAM QUALITATIVO MAS NÃO LANÇARAM
    # --------------------------------------------------------------------------
    st.markdown("""
    <div class="section-card warning">
        <div class="section-title">2º — Igrejas (por Atividade) com Anexo ou Qualitativo Preenchido, mas sem Lançamentos</div>
        <div class="section-desc">
            Atividades onde houve envio de folha de apontamentos (Relatório de Anexos) ou análise no Formulário Qualitativo, porém constam 0 lançamentos na Tabela do mês.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_item2.empty:
        st.success("✅ Nenhuma inconsistência! Todas as atividades com anexo ou qualitativo possuem lançamentos.")
    else:
        st.dataframe(df_item2, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # ORDEM 3: IGREJAS QUE NÃO FIZERAM O ENCERRAMENTO MENSAL
    # --------------------------------------------------------------------------
    st.markdown(f"""
    <div class="section-card danger">
        <div class="section-title">3º — Igrejas pendentes de Fechamento Mensal (FECHAMENTO MENSAL {periodo_sel})</div>
        <div class="section-desc">
            Casas de Oração cujo status no arquivo de fechamento mensal ainda consta como <strong>Aberto</strong> ou não encerrado.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_item3.empty:
        st.success("✅ Todas as igrejas filtradas já realizaram o encerramento mensal!")
    else:
        st.dataframe(df_item3, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # ORDEM 4: IGREJAS QUE NÃO PREENCHERAM O QUALITATIVO (POR ATIVIDADE COM MOVIMENTO)
    # --------------------------------------------------------------------------
    st.markdown("""
    <div class="section-card info">
        <div class="section-title">4º — Igrejas que não preencheram o Formulário Qualitativo (por Atividade)</div>
        <div class="section-desc">
            Exibe exclusivamente as atividades que tiveram lançamentos na tabela ou páginas anexadas, mas não foram assinaladas/analisadas no Formulário Qualitativo.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_item4.empty:
        st.success("✅ Todas as atividades com lançamento ou anexo foram analisadas no Formulário Qualitativo!")
    else:
        st.dataframe(df_item4, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # ORDEM 5: GRÁFICO INTERATIVO DO FORMULÁRIO QUALITATIVO (% ERROS VS LANÇAMENTOS)
    # --------------------------------------------------------------------------
    st.markdown("""
    <div class="section-card purple">
        <div class="section-title">5º — Análise Gráfica Interativa do Formulário Qualitativo (% de Erros vs Lançamentos)</div>
        <div class="section-desc">
            Proporção da quantidade de erros (Rasuras/Borrões, Erros de Horário e Campos em Branco) em relação ao total de lançamentos de cada atividade. Clique em qualquer barra para abrir o detalhamento da origem dos erros logo abaixo.
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_graf_base = df_filtrado[(df_filtrado["Qtd_Lancamentos"] > 0) | (df_filtrado["Total_Erros"] > 0)].copy()

    if df_graf_base.empty:
        st.info("Não há dados de lançamentos ou erros qualitativos para os filtros selecionados.")
    else:
        col_g1, col_g2 = st.columns([1.5, 2.5])
        with col_g1:
            eixo_agrupamento = st.selectbox(
                "Agrupar eixo principal das barras por:",
                ["Atividade", "Setor", "Igreja"],
                index=0
            )
        with col_g2:
            tipos_erro_sel = st.multiselect(
                "Tipos de erro considerados no cálculo:",
                ["Rasuras", "Erros_Horario", "Campos_Branco"],
                default=["Rasuras", "Erros_Horario", "Campos_Branco"],
                format_func=lambda x: {
                    "Rasuras": "Rasuras / Borrões",
                    "Erros_Horario": "Erros de Horário",
                    "Campos_Branco": "Campos Obrigatórios em Branco"
                }[x]
            )

        if not tipos_erro_sel:
            st.warning("Selecione ao menos um tipo de erro para visualizar o gráfico.")
        else:
            # Transforma em formato longo por tipo de erro para permitir barra empilhada interativa
            registros_long = []
            mapa_nomes_erro = {
                "Rasuras": "Rasuras / Borrões",
                "Erros_Horario": "Erros de Horário",
                "Campos_Branco": "Campos em Branco"
            }
            for _, r in df_graf_base.iterrows():
                for te in tipos_erro_sel:
                    registros_long.append({
                        "Setor": r["Setor"],
                        "Igreja": r["Igreja"],
                        "Atividade": r["Atividade"],
                        "Tipo_Erro": mapa_nomes_erro[te],
                        "Qtd_Erros": r[te],
                        "Qtd_Lancamentos": r["Qtd_Lancamentos"]
                    })
            df_long = pd.DataFrame(registros_long)

            # Cálculo do denominador total de lançamentos por grupo do eixo X
            lanc_por_grupo = df_graf_base.groupby(eixo_agrupamento)["Qtd_Lancamentos"].sum().reset_index(name="Total_Lanc_Grupo")
            erros_por_grupo = df_long.groupby([eixo_agrupamento, "Tipo_Erro"])["Qtd_Erros"].sum().reset_index()
            df_plot = erros_por_grupo.merge(lanc_por_grupo, on=eixo_agrupamento, how="left")
            df_plot["Pct_Erro"] = df_plot.apply(
                lambda r: round((r["Qtd_Erros"] / r["Total_Lanc_Grupo"]) * 100, 2) if r["Total_Lanc_Grupo"] > 0 else 0.0,
                axis=1
            )

            fig = px.bar(
                df_plot,
                x=eixo_agrupamento,
                y="Pct_Erro",
                color="Tipo_Erro",
                barmode="stack",
                text=df_plot.apply(lambda r: f"{r['Pct_Erro']:.1f}% ({int(r['Qtd_Erros'])})" if r["Qtd_Erros"] > 0 else "", axis=1),
                hover_data={"Qtd_Erros": True, "Total_Lanc_Grupo": True, "Pct_Erro": ":.2f"},
                labels={
                    "Pct_Erro": "% de Erros sobre Lançamentos",
                    "Tipo_Erro": "Natureza do Erro",
                    "Qtd_Erros": "Qtd. de Erros",
                    "Total_Lanc_Grupo": "Total de Lançamentos"
                },
                color_discrete_map={
                    "Rasuras / Borrões": "#ef4444",
                    "Erros de Horário": "#f59e0b",
                    "Campos em Branco": "#6366f1"
                },
                title=f"Taxa de Erros Qualitativos vs Lançamentos por {eixo_agrupamento} (Clique em uma barra para detalhar)"
            )
            fig.update_layout(
                plot_bgcolor="#ffffff",
                yaxis_title="% de Erros (Erros / Lançamentos)",
                xaxis_title=eixo_agrupamento,
                legend_title="Tipo de Apontamento",
                height=430
            )

            # Renderização com suporte a clique nativo do Streamlit
            evento_clique = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

            # Detalhamento automático ao clicar na barra (ou seletor manual de apoio)
            item_clicado = None
            if evento_clique and "selection" in evento_clique and evento_clique["selection"].get("points"):
                ponto = evento_clique["selection"]["points"][0]
                item_clicado = ponto.get("x")

            st.markdown("#### 🔎 Detalhamento da Origem dos Erros (Drill-down)")
            opcoes_drill = ["Mostrar Todos com Erro"] + sorted(df_graf_base[eixo_agrupamento].unique().tolist())
            idx_padrao = opcoes_drill.index(item_clicado) if item_clicado in opcoes_drill else 0
            escolha_drill = st.selectbox(
                f"Selecionado pelo clique no gráfico (ou altere manualmente o {eixo_agrupamento}):",
                options=opcoes_drill,
                index=idx_padrao
            )

            df_detalhe_erros = df_graf_base[df_graf_base["Total_Erros"] > 0].copy()
            if escolha_drill != "Mostrar Todos com Erro":
                df_detalhe_erros = df_detalhe_erros[df_detalhe_erros[eixo_agrupamento] == escolha_drill]

            df_detalhe_erros["% Erro / Lançamentos"] = df_detalhe_erros.apply(
                lambda r: f"{(r['Total_Erros'] / r['Qtd_Lancamentos'] * 100):.1f}%" if r["Qtd_Lancamentos"] > 0 else "Sem lanç. (100%)",
                axis=1
            )

            if df_detalhe_erros.empty:
                st.info("Nenhum erro registrado no Formulário Qualitativo para a seleção atual.")
            else:
                st.dataframe(
                    df_detalhe_erros[[
                        "Setor", "Igreja", "Atividade", "Qtd_Lancamentos",
                        "Rasuras", "Erros_Horario", "Campos_Branco", "Total_Erros", "% Erro / Lançamentos"
                    ]].rename(columns={
                        "Qtd_Lancamentos": "Lançamentos",
                        "Rasuras": "Rasuras / Borrões",
                        "Erros_Horario": "Erros de Horário",
                        "Campos_Branco": "Campos em Branco",
                        "Total_Erros": "Total de Erros"
                    }).sort_values("Total de Erros", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

    # --------------------------------------------------------------------------
    # ORDEM 6: BATIMENTO (RELATÓRIO DE ANEXOS x 14 vs LANÇAMENTOS)
    # --------------------------------------------------------------------------
    st.markdown("""
    <div class="section-card warning">
        <div class="section-title">6º — Batimento de Lançamentos: Relatório de Anexos (Páginas × 14) vs Tabela</div>
        <div class="section-desc">
            Comparativo entre a capacidade máxima das folhas anexadas (14 linhas de apontamentos por página) e os lançamentos efetivamente digitados no sistema.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "📌 **Como é feito o cálculo e observação importante:** Cada página anexada no arquivo `relatorio anexos mm-aaaa` comporta até **14 linhas de apontamentos** "
        "(valor provável de lançamentos = páginas × 14). Quando o número de lançamentos realizados fica abaixo desse múltiplo (ou a diferença na última página é inferior a 14), "
        "o sistema sinaliza que podem ter ficado lançamentos sem fazer (ou que a última folha não foi totalmente preenchida). "
        "**Atenção:** caso tenham sido anexadas folhas a mais em branco/duplicadas ou com nomenclatura incorreta na pasta, podem ocorrer divergências no batimento."
    )

    aba_bat1, aba_bat2 = st.tabs([
        f"⚠️ Abaixo do Valor Provável / Pendentes ({len(df_item6_pend)})",
        f"📋 Todos os Registros do Batimento ({len(df_item6)})"
    ])

    cols_exib_bat = [
        "Setor", "Igreja", "Atividade", "Paginas_Estimadas",
        "Valor_Anexo", "Qtd_Lancamentos", "Diferenca", "Diagnóstico do Batimento"
    ]
    nomes_col_bat = {
        "Paginas_Estimadas": "Páginas Anexadas",
        "Valor_Anexo": "Lanç. Prováveis (Pág × 14)",
        "Qtd_Lancamentos": "Lançamentos Realizados",
        "Diferenca": "Saldo Sem Lançar"
    }

    with aba_bat1:
        if df_item6_pend.empty:
            st.success("✅ Nenhuma igreja/atividade está abaixo da estimativa de páginas × 14.")
        else:
            st.dataframe(
                df_item6_pend[cols_exib_bat].rename(columns=nomes_col_bat).sort_values("Saldo Sem Lançar", ascending=False),
                use_container_width=True,
                hide_index=True
            )

    with aba_bat2:
        st.dataframe(
            df_item6[cols_exib_bat].rename(columns=nomes_col_bat).sort_values(["Setor", "Igreja", "Atividade"]),
            use_container_width=True,
            hide_index=True
        )
