import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import os
import math
from fpdf import FPDF # Importação para gerar os PDFs

st.set_page_config(page_title="Dashboard de Voluntários", page_icon="📊", layout="wide")

def gerar_pdf(titulo_relatorio, sessoes_dados):
    """
    Gera um PDF a partir de uma lista de tuplas (Titulo_da_Sessao, DataFrame).
    """
    pdf = FPDF(orientation='L') # Paisagem para caber mais colunas
    pdf.add_page()
    
    # Título Principal
    pdf.set_font("Arial", "B", 16)
    # Tratamento de encoding para acentos no FPDF
    titulo_seguro = str(titulo_relatorio).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, titulo_seguro, 0, 1, "C")
    pdf.ln(5)

    for subtitulo, df in sessoes_dados:
        pdf.set_font("Arial", "B", 12)
        sub_seguro = str(subtitulo).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, sub_seguro, 0, 1)
        pdf.set_font("Arial", "", 10)

        if df is not None and not df.empty:
            # Cálculos de largura das colunas
            colunas = list(df.columns)
            largura_util = pdf.w - 20 # 10 margem de cada lado
            col_width = largura_util / len(colunas)
            line_height = pdf.font_size * 2

            # Cabeçalho da Tabela
            pdf.set_font("Arial", "B", 9)
            for col in colunas:
                txt = str(col).encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(col_width, line_height, txt[:30], border=1)
            pdf.ln(line_height)

            # Linhas da Tabela
            pdf.set_font("Arial", "", 8)
            for _, row in df.iterrows():
                for item in row:
                    txt = str(item).encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(col_width, line_height, txt[:45], border=1)
                pdf.ln(line_height)
        else:
            pdf.cell(0, 10, "Nenhuma pendencia ou dado encontrado para esta sessao.", 0, 1)
        pdf.ln(10)

    # Exporta em bytes para o st.download_button
    try:
        # Tenta o método fpdf2 mais moderno
        return bytes(pdf.output())
    except TypeError:
        # Fallback para fpdf mais antigo
        return pdf.output(dest='S').encode('latin-1')

SETORES = {
    'Setor 1': [
        'BR 14-2362 - ZONA 6 - MARINGÁ VELHO', 'BR 14-2601 - JARDIM ESPANHA', 
        'BR 14-0603 - VILA OPERÁRIA', 'BR 14-0607 - VILA MORANGUEIRA', 
        'BR 14-1115 - DISTRITO DE FLORIANO', 'BR 14-1118 - JARDIM VITÓRIA', 
        'BR 14-1399 - JARDIM VERÔNICA', 'BR 14-1518 - PARQUE ITAIPU', 
        'BR 14-1613 - PARQUE RESIDENCIAL AEROPORTO - 3ª PARTE', 
        'BR 14-1614 - JARDIM CATEDRAL', 'BR 14-1686 - JARDIM UNIVERSO', 
        'BR 14-2380 - JARDIM ORIENTAL - DIAMANTE'
    ],
    'Setor 2': [
        'BR 14-0445 - DISTRITO DE IGUATEMI', 'BR 14-0606 - VILA SANTA IZABEL', 
        'BR 14-1611 - PARQUE HORTÊNCIA - 1ª PARTE', 'BR 14-1615 - PARQUE DAS LARANJEIRAS', 
        'BR 14-1748 - PARQUE AVENIDA', 'BR 14-1749 - JARDIM OLÍMPICO', 
        'BR 14-2174 - JARDIM OURO COLA', 'BR 14-2296 - JARDIM MONTE REI', 
        'BR 14-2446 - GLEBA PATRIMÔNIO MARINGÁ - JARDIM INDAIÁ'
    ],
    'Setor 3': [
        'BR 14-0602 - VILA SANTO ANTÔNIO', 'BR 14-0605 - JARDIM ALVORADA', 
        'BR 14-1116 - PARQUE RESIDENCIAL TUIUTI', 'BR 14-1400 - JARDIM LIBERDADE', 
        'BR 14-1612 - JARDIM ALVORADA III - EBENEZER', 'BR 14-1635 - JARDIM PIATÃ', 
        'BR 14-1636 - CONJUNTO REQUIÃO', 'BR 14-1970 - CONJUNTO RESIDENCIAL GUAIAPÓ', 
        'BR 14-2402 - LOTEAMENTO SUMARÉ'
    ]
}

ATIVIDADES_OBRIGATORIAS = ['LIMPEZA', 'GEM', 'PÁTIO']
ATIVIDADES_ESPORADICAS = ['MANUTENÇÃO PREVENTIVA', 'ESPAÇO INFANTIL', 'COZINHA']
IGREJAS_IGNORADAS = ['ADM - MARINGÁ - PR', 'PIA - MARINGÁ', 'BR 14-0601 - MARINGÁ - CENTRO']

MAPEAMENTO_DIRETO = {
    "4 - COZINHA": "COZINHA",
    "2 - MANUTENÇÃO PREVENTIVA": "MANUTENÇÃO PREVENTIVA",
    "4 - ANEXO - ADMINISTRATIVO": "MANUTENÇÃO PREVENTIVA",
    "4 - ANEXO - INSTRUTORES GEL": "GEL",
    "4 - ALMOXARIFADO - PIEDADE": "PIEDADE",
    "4 - ANEXO - INSTRUTORES GEM": "GEM",
    "4 - GEM": "GEM",
    "4 - ANEXO - COZINHA": "COZINHA",
    "4 - ANEXO - LIMPEZA": "LIMPEZA",
    "4 - LIMPEZA": "LIMPEZA",
    "4 - INSTRUTORES GEM": "GEM",
    "4 - PÁTIO/ESTACIONAMENTO": "PÁTIO",
    "4 - PÁTIO": "PÁTIO",
    "2 - REFORMA CENTRAL": "REFORMA",
    "4 - INSTRUTORES - GEM": "GEM",
    "4 - ESPAÇO INFANTIL": "ESPAÇO INFANTIL",
    "4 - EBI - ESPAÇO INFANTIL": "ESPAÇO INFANTIL",
    "4 - EBI - ENSINO BÍBLICO INFANTIL -": "ESPAÇO INFANTIL",
    "4 - PÁTIO EXTERNO/ESTACIONAMENTO": "PÁTIO",
}

MAPEAMENTO_ATIVIDADES = {
    "LIMPEZA": ["LIMPEZA", "MPEZA", "MPESA"],
    "GEM": ["GEM", "G.E.M"],
    "PÁTIO": ["PÁTIO", "PATIO", "ESTACIONAMENTO", "ESTAC"],
    "ESPAÇO INFANTIL": ["ESPAÇO INFANTIL", "EBI", "ESPAÇO BÍBLICO INFANTIL", "ESPAÇO BIBLICO INFANTIL", "INFA"],
    "MANUTENÇÃO PREVENTIVA": ["MANUTENÇÃO PREVENTIVA", "MANUT", "MAN.", "PREVENT", "MAN"],
    "COZINHA": ["COZINHA"]
}

def classificar_setor(localidade):
    for setor, locais in SETORES.items():
        if localidade in locais:
            return setor
    return 'Não Classificado'

@st.cache_data(ttl=3600)
def load_arquivos_relatorio(mes, ano):
    nome_xlsx = f"relatorio anexos {mes}-{ano}.xlsx"
    nome_ods = f"relatorio anexos {mes}-{ano}.ods"
    
    arquivos_encontrados = {}
    df = None
    nome_arquivo = None
    
    if os.path.exists(nome_xlsx):
        nome_arquivo = nome_xlsx
        df = pd.read_excel(nome_arquivo)
    elif os.path.exists(nome_ods):
        nome_arquivo = nome_ods
        df = pd.read_excel(nome_arquivo, engine="odf")
    else:
        st.warning(f"⚠️ Relatório de anexos não encontrado para este período: '{nome_xlsx}' ou '{nome_ods}'. As pendências de anexo serão avaliadas como 0.")
        return arquivos_encontrados, None
    
    df_raw = df.copy()
    
    try:
        col_igreja = df.columns[0]
        for c in df.columns:
            if any(x in str(c).upper() for x in ['IGREJA', 'LOCALIDADE', 'CÓDIGO']):
                col_igreja = c
                break
                
        df_raw = df_raw.rename(columns={col_igreja: 'Igreja_Relatorio'})

        for _, row in df.iterrows():
            igreja_str = str(row[col_igreja]).strip()
            igreja_cod = igreja_str.split(' - ')[0].strip().upper() if '-' in igreja_str else igreja_str.upper()
            arquivos_encontrados[igreja_cod] = {}
            
            for col in df.columns:
                if col != col_igreja:
                    col_name = str(col).strip().upper()
                    valor = row[col]
                    try:
                        num = float(valor)
                        if pd.isna(num): num = 0
                    except (ValueError, TypeError):
                        num = 0
                    arquivos_encontrados[igreja_cod][col_name] = num
                        
    except Exception as e:
        st.error(f"Erro ao ler o relatório de anexos '{nome_arquivo}': {e}")
        
    return arquivos_encontrados, df_raw

@st.cache_data
def load_data(mes, ano):
    nome_xlsx = f"tabela {mes}-{ano}.xlsx"
    nome_ods = f"tabela {mes}-{ano}.ods"
    
    df = None
    if os.path.exists(nome_xlsx):
        df = pd.read_excel(nome_xlsx)
    elif os.path.exists(nome_ods):
        df = pd.read_excel(nome_ods, engine="odf")
    else:
        return None
    
    df.columns = df.columns.str.strip()
    col_mapping = {'Localida': 'Localidade', 'Voluntá': 'Voluntario', 'Data Na': 'Data Nasc', 'H. Des': 'Horas Desconto'}
    df = df.rename(columns=lambda x: col_mapping.get(x, x))
    
    if 'Valor' in df.columns and df['Valor'].dtype == object:
        df['Valor'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        
    if 'Localidade' in df.columns:
        df['Setor'] = df['Localidade'].apply(classificar_setor)
        
    if 'Livro' in df.columns:
        df['Livro'] = df['Livro'].apply(
            lambda x: MAPEAMENTO_DIRETO.get(str(x).strip().upper(), str(x).strip().upper()) if pd.notna(x) else x
        )
        
    return df

@st.cache_data
def load_fechamento_data(mes, ano):
    nome_arquivo = f"FECHAMENTO MENSAL {mes}-{ano}.txt"
    try:
        df_fechamento = pd.read_csv(nome_arquivo, sep='\t', skiprows=1, names=["Localidade", "Status"])
        df_fechamento['Localidade'] = df_fechamento['Localidade'].str.strip()
        df_fechamento['Status'] = df_fechamento['Status'].str.strip()
        return df_fechamento
    except FileNotFoundError:
        return None

@st.cache_data
def load_form_data():
    nome_xlsx = 'FORMULÁRIO QUALITATIVO 2026 (respostas).xlsx'
    nome_ods = 'FORMULÁRIO QUALITATIVO 2026 (respostas).ods'
    
    df_form = None
    if os.path.exists(nome_xlsx):
        df_form = pd.read_excel(nome_xlsx)
    elif os.path.exists(nome_ods):
        df_form = pd.read_excel(nome_ods, engine="odf")
    else:
        return None

    try:
        colunas_igreja = [c for c in df_form.columns if 'ESCOLHA A CASA DE ORAÇÃO' in str(c).upper()]
        def extrair_igreja(row):
            for col in colunas_igreja:
                if pd.notna(row[col]) and str(row[col]).strip() != "":
                    return str(row[col]).strip()
            return None
        if colunas_igreja:
            df_form['Igreja_Identificada'] = df_form.apply(extrair_igreja, axis=1)
        else: df_form['Igreja_Identificada'] = None
        if 'MÊS' in df_form.columns: df_form['Mes_Submissao'] = pd.to_numeric(df_form['MÊS'], errors='coerce')
        if 'ANO' in df_form.columns: df_form['Ano_Submissao'] = pd.to_numeric(df_form['ANO'], errors='coerce')
        return df_form
    except Exception as e:
        return None

if 'filtro_setor' not in st.session_state:
    st.session_state.filtro_setor = 'Todos'
if 'filtro_igreja' not in st.session_state:
    st.session_state.filtro_igreja = 'Todas'
if 'filtro_atividade' not in st.session_state:
    st.session_state.filtro_atividade = 'Todas'

def ao_mudar_periodo():
    st.session_state.filtro_setor = 'Todos'
    st.session_state.filtro_igreja = 'Todas'
    st.session_state.filtro_atividade = 'Todas'

st.title("📊 Painel de Controle - Voluntários")

# ==========================================
# CÁLCULO DINÂMICO DO MÊS ANTERIOR
# ==========================================
hoje = datetime.now()
if hoje.month == 1:
    mes_anterior_num = 12
    ano_anterior_num = hoje.year - 1
else:
    mes_anterior_num = hoje.month - 1
    ano_anterior_num = hoje.year

opcoes_meses = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
opcoes_anos = ["2024", "2025", "2026", "2027", "2028", "2029", "2030"]

idx_mes_padrao = mes_anterior_num - 1
idx_ano_padrao = opcoes_anos.index(str(ano_anterior_num)) if str(ano_anterior_num) in opcoes_anos else 0

with st.container(border=True):
    st.subheader("📅 Período de Análise")
    
    col_data1, col_data2, col_btn, _ = st.columns([2, 2, 2, 4])
    selected_mes = col_data1.selectbox("Selecione o Mês", opcoes_meses, index=idx_mes_padrao, on_change=ao_mudar_periodo)
    selected_ano = col_data2.selectbox("Selecione o Ano", opcoes_anos, index=idx_ano_padrao, on_change=ao_mudar_periodo)
    
    # Botão para atualizar dados
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear() 
            st.rerun()
    
    df_original = load_data(selected_mes, selected_ano)
    df_form = load_form_data()
    df_fechamento = load_fechamento_data(selected_mes, selected_ano)
    arquivos_anexos, df_anexos_raw = load_arquivos_relatorio(selected_mes, selected_ano)

    if df_original is not None:
        st.markdown("---")
        
        # 1. BOTÕES DE SETOR
        st.markdown("**Selecione o Setor:**")
        botoes_setores = ['Todos', 'Setor 1', 'Setor 2', 'Setor 3', 'Não Classificado']
        cols_setores = st.columns(len(botoes_setores))
        
        for i, setor_nome in enumerate(botoes_setores):
            is_selected = (st.session_state.filtro_setor == setor_nome)
            if cols_setores[i].button(setor_nome, use_container_width=True, type="primary" if is_selected else "secondary", key=f"btn_{setor_nome}"):
                st.session_state.filtro_setor = setor_nome
                st.session_state.filtro_igreja = 'Todas'
                st.rerun()

        # 2. BOTÕES DE IGREJA
        if st.session_state.filtro_setor != "Todos":
            df_temp = df_original[df_original['Setor'] == st.session_state.filtro_setor]
            lista_igrejas = ["Todas"] + sorted([str(x) for x in df_temp['Localidade'].dropna().unique() if x not in IGREJAS_IGNORADAS])

            st.markdown("**Selecione a Igreja:**")
            cols_por_linha = 4 
            
            for i in range(0, len(lista_igrejas), cols_por_linha):
                cols_ig = st.columns(cols_por_linha)
                for j in range(cols_por_linha):
                    idx = i + j
                    if idx < len(lista_igrejas):
                        ig_nome = lista_igrejas[idx]
                        is_selected = (st.session_state.filtro_igreja == ig_nome)
                        btn_label = ig_nome if len(ig_nome) < 40 else ig_nome[:37] + "..." 
                        if cols_ig[j].button(btn_label, use_container_width=True, type="primary" if is_selected else "secondary", key=f"btn_ig_{idx}"):
                            st.session_state.filtro_igreja = ig_nome
                            st.rerun()
        else:
            st.session_state.filtro_igreja = 'Todas'

        # 3. BOTÕES FIXOS DE ATIVIDADE
        if 'Livro' in df_original.columns:
            st.markdown("**Selecione a Atividade:**")
            lista_atividades = ["Todas", "LIMPEZA", "GEM", "PÁTIO", "ESPAÇO INFANTIL", "MANUTENÇÃO PREVENTIVA", "COZINHA"]
            cols_atv = st.columns(len(lista_atividades))
            
            for i, ativ_nome in enumerate(lista_atividades):
                is_selected = (st.session_state.filtro_atividade == ativ_nome)
                if cols_atv[i].button(ativ_nome, use_container_width=True, type="primary" if is_selected else "secondary", key=f"btn_at_{i}"):
                    st.session_state.filtro_atividade = ativ_nome
                    st.rerun()

filtro_setor = st.session_state.filtro_setor
filtro_igreja = st.session_state.filtro_igreja
filtro_atividade = st.session_state.filtro_atividade

if df_original is not None:
    # 1. FILTRAR SETOR E IGREJA PRIMEIRO
    df = df_original.copy()
    if filtro_setor != "Todos": df = df[df['Setor'] == filtro_setor]
    if filtro_igreja != "Todas": df = df[df['Localidade'] == filtro_igreja]
    
    # 2. BASE DE DADOS PARA AUDITORIA
    df_base_pendencias = df.copy()

    # 3. APLICAR FILTRO DE ATIVIDADE NO DF DE EXIBIÇÃO / KPIs
    if filtro_atividade != "Todas" and 'Livro' in df.columns:
        palavras_chave = MAPEAMENTO_ATIVIDADES.get(filtro_atividade, [filtro_atividade])
        regex_pattern = '|'.join(palavras_chave)
        df = df[df['Livro'].astype(str).str.upper().str.contains(regex_pattern, regex=True, na=False)]

    st.markdown("---")
    st.subheader("⚠️ Controle de Atividades, Anexos e Lançamentos Pendentes")

    todas_igrejas_cadastro = []
    for s_nome, locais in SETORES.items():
        if filtro_setor == "Todos" or filtro_setor == s_nome:
            for loc in locais:
                if loc not in IGREJAS_IGNORADAS:
                    if filtro_igreja == "Todas" or filtro_igreja == loc:
                        todas_igrejas_cadastro.append((s_nome, loc))

    pendencias_siga = []
    pendencias_drive = []
    pendencias_quantidade_lancamentos = []
    
    mapa_lancamentos_siga = {}
    if 'Livro' in df_base_pendencias.columns:
        for (setor_grp, loc_grp), df_grp in df_base_pendencias.groupby(['Setor', 'Localidade']):
            mapa_lancamentos_siga[loc_grp] = df_grp
    else:
        st.error("A coluna 'Livro' não foi encontrada na planilha do SIGA.")

    df_anexos_qnt = None
    if df_anexos_raw is not None:
        df_anexos_qnt = df_anexos_raw.copy()
        col_ig_anexos = 'Igreja_Relatorio'
        df_anexos_qnt['Codigo_Igreja'] = df_anexos_qnt[col_ig_anexos].apply(
            lambda x: str(x).split(' - ')[0].strip().upper() if '-' in str(x) else str(x).upper()
        )

    for setor_igreja, igreja_completa in todas_igrejas_cadastro:
        codigo_igreja = str(igreja_completa).split(' - ')[0].strip().upper()
        contagens_igreja = arquivos_anexos.get(codigo_igreja, {})
        
        dados_siga_igreja = mapa_lancamentos_siga.get(igreja_completa, pd.DataFrame())
        
        if not dados_siga_igreja.empty and 'Livro' in dados_siga_igreja.columns:
            atividades_lancadas = [str(a).upper() for a in dados_siga_igreja['Livro'].dropna().unique()]
        else:
            atividades_lancadas = []

        falta_siga = []
        for atv in ATIVIDADES_OBRIGATORIAS:
            if not any(atv in lancado for lancado in atividades_lancadas):
                falta_siga.append(atv)
                
        for atv_esp in ATIVIDADES_ESPORADICAS:
            if not any(atv_esp in lancado for lancado in atividades_lancadas):
                def verificar_contagem_esporadica(atividade):
                    for col_name, count in contagens_igreja.items():
                        if atividade in col_name and count > 0:
                            return True
                    return False

                if atv_esp == "MANUTENÇÃO PREVENTIVA":
                    for col_name, count in contagens_igreja.items():
                        if any(x in col_name for x in ['MANUT', 'MAN.', 'PREVENT']) and count > 0:
                            falta_siga.append(atv_esp)
                            break
                elif atv_esp == "ESPAÇO INFANTIL":
                    for col_name, count in contagens_igreja.items():
                        if any(x in col_name for x in ['INFA', 'EBI', 'E.B.I']) and count > 0:
                            falta_siga.append(atv_esp)
                            break
                elif atv_esp == "COZINHA":
                    if verificar_contagem_esporadica("COZINHA"):
                        falta_siga.append(atv_esp)

        if falta_siga:
            pendencias_siga.append({
                'Setor': setor_igreja,
                'Igreja': igreja_completa,
                'Falta Lançar no Sistema': ", ".join(falta_siga)
            })

        falta_drive = []
        for lancado in atividades_lancadas:
            encontrou = False
            
            def buscar_nas_contagens(termos_busca):
                for termo in termos_busca:
                    for col_name, count in contagens_igreja.items():
                        if termo in col_name and 'OCORRENC' not in col_name and 'RELAT' not in col_name:
                            if count > 0:
                                return True
                return False

            if 'ESTAC' in lancado or 'PÁTIO' in lancado or 'PATIO' in lancado: 
                encontrou = buscar_nas_contagens(['ESTAC', 'PÁTIO', 'PATIO'])
            elif 'GEM' in lancado or 'G.E.M' in lancado: 
                encontrou = buscar_nas_contagens(['GEM', 'G.E.M'])
            elif 'MPEZA' in lancado or 'MPESA' in lancado: 
                encontrou = buscar_nas_contagens(['MPEZA', 'MPESA'])
            elif 'COZINHA' in lancado: 
                encontrou = buscar_nas_contagens(['COZINHA'])
            elif 'INFA' in lancado or 'EBI' in lancado or 'E.B.I' in lancado: 
                encontrou = buscar_nas_contagens(['INFA', 'EBI', 'E.B.I'])
            elif 'MANUT' in lancado: 
                encontrou = buscar_nas_contagens(['MANUT'])
            else: 
                encontrou = True

            if not encontrou and any(base in lancado for base in ATIVIDADES_OBRIGATORIAS + ATIVIDADES_ESPORADICAS):
                falta_drive.append(lancado)

        if falta_drive:
            pendencias_drive.append({
                'Setor': setor_igreja,
                'Igreja': igreja_completa,
                'Falta Anexar PDF no Drive': ", ".join(falta_drive)
            })

        if df_anexos_qnt is not None:
            dados_anexos_igreja = df_anexos_qnt[df_anexos_qnt['Codigo_Igreja'] == codigo_igreja]
            if not dados_anexos_igreja.empty:
                linha_anexo = dados_anexos_igreja.iloc[0]
                for ativ_chave, ativ_variacoes in MAPEAMENTO_ATIVIDADES.items():
                    regex_pattern = '|'.join(ativ_variacoes)
                    
                    if not dados_siga_igreja.empty and 'Livro' in dados_siga_igreja.columns:
                        qtd_lancada = dados_siga_igreja[
                            dados_siga_igreja['Livro'].astype(str).str.upper().str.contains(regex_pattern, regex=True, na=False)
                        ].shape[0]
                    else:
                        qtd_lancada = 0
                    
                    qtd_esperada = 0
                    for col in df_anexos_qnt.columns:
                        col_upper = str(col).upper()
                        if col_upper in ['IGREJA_RELATORIO', 'CODIGO_IGREJA'] or 'OCORRENC' in col_upper or 'RELAT' in col_upper:
                            continue
                        if any(var in col_upper for var in ativ_variacoes):
                            try:
                                qtd_esperada = float(linha_anexo[col])
                                if pd.isna(qtd_esperada): qtd_esperada = 0
                                break
                            except (ValueError, TypeError):
                                qtd_esperada = 0
                                
                    if qtd_esperada > 0:
                        diferenca = qtd_esperada - qtd_lancada
                        if diferenca >= 14:
                            pendencias_quantidade_lancamentos.append({
                                'Setor': setor_igreja,
                                'Igreja': igreja_completa,
                                'Atividade': ativ_chave,
                                'Lançamentos Informados (Anexos)': int(qtd_esperada),
                                'Qtd Lançada (Sistema)': int(qtd_lancada),
                                'Diferença (Faltam)': int(diferenca)
                            })

    df_pendencias_siga = pd.DataFrame(pendencias_siga) if pendencias_siga else pd.DataFrame()
    df_pendencias_drive = pd.DataFrame(pendencias_drive) if pendencias_drive else pd.DataFrame()
    df_pendencias_qnt = pd.DataFrame(pendencias_quantidade_lancamentos) if pendencias_quantidade_lancamentos else pd.DataFrame()

    if filtro_atividade != "Todas":
        if not df_pendencias_siga.empty:
            df_pendencias_siga = df_pendencias_siga[df_pendencias_siga['Falta Lançar no Sistema'].str.upper().str.contains(filtro_atividade, na=False)]
        
        if not df_pendencias_drive.empty:
            palavras_chave_drive = MAPEAMENTO_ATIVIDADES.get(filtro_atividade, [filtro_atividade])
            regex_drive = '|'.join(palavras_chave_drive)
            df_pendencias_drive = df_pendencias_drive[df_pendencias_drive['Falta Anexar PDF no Drive'].str.upper().str.contains(regex_drive, regex=True, na=False)]
            
        if not df_pendencias_qnt.empty:
            df_pendencias_qnt = df_pendencias_qnt[df_pendencias_qnt['Atividade'] == filtro_atividade]

    with st.expander(f"⚠️ {len(df_pendencias_siga)} congregações com pendências de categorias no Sistema (SIGA)"):
        if not df_pendencias_siga.empty: 
            st.dataframe(df_pendencias_siga, use_container_width=True, hide_index=True)
            pdf_bytes = gerar_pdf("Pendencias de Categorias no Sistema (SIGA)", [("Pendências", df_pendencias_siga)])
            st.download_button("📥 Gerar PDF (Pendências Categoria SIGA)", data=pdf_bytes, file_name="Pendencias_Categoria_SIGA.pdf", mime="application/pdf")
        else: 
            st.success("Tudo certo no SIGA para as categorias avaliadas nos filtros selecionados!")

    with st.expander(f"📁 {len(df_pendencias_drive)} Pendencia de anexo no fechamento mensal"):
        if not df_pendencias_drive.empty: 
            st.dataframe(df_pendencias_drive, use_container_width=True, hide_index=True)
            pdf_bytes = gerar_pdf("Pendencia de anexo no fechamento", [("Pendências Anexos", df_pendencias_drive)])
            st.download_button("📥 Gerar PDF (Pendências Anexos)", data=pdf_bytes, file_name="Pendencias_Anexos.pdf", mime="application/pdf")
        else: 
            st.success("Todos os lançamentos filtrados possuem arquivo correspondente no Relatório de Anexos!")

    st.markdown("---")
    st.subheader("📂 Status de Fechamento Mensal")
    
    df_igrejas_abertas = pd.DataFrame()
    if df_fechamento is not None:
        fechamento_filtrado = df_fechamento[~df_fechamento['Localidade'].isin(IGREJAS_IGNORADAS)].copy()
        fechamento_filtrado['Setor'] = fechamento_filtrado['Localidade'].apply(classificar_setor)
        
        if filtro_setor != "Todos": fechamento_filtrado = fechamento_filtrado[fechamento_filtrado['Setor'] == filtro_setor]
        if filtro_igreja != "Todas": fechamento_filtrado = fechamento_filtrado[fechamento_filtrado['Localidade'] == filtro_igreja]
            
        igrejas_abertas = fechamento_filtrado[fechamento_filtrado['Status'].str.upper() == 'ABERTO']
        if not igrejas_abertas.empty:
            df_igrejas_abertas = igrejas_abertas[['Setor', 'Localidade', 'Status']]
            
        with st.expander(f"⚠️ {len(igrejas_abertas)} igrejas com o status ABERTO"):
            if not df_igrejas_abertas.empty: 
                st.dataframe(df_igrejas_abertas, use_container_width=True, hide_index=True)
                pdf_bytes = gerar_pdf("Status de Fechamento: ABERTO", [("Igrejas Abertas", df_igrejas_abertas)])
                st.download_button("📥 Gerar PDF (Fechamento Aberto)", data=pdf_bytes, file_name="Fechamentos_Abertos.pdf", mime="application/pdf")
            else: 
                st.success("Todos os fechamentos avaliados estão ENCERRADOS.")
    else: st.info("Arquivo de fechamento não encontrado para este mês.")

    st.markdown("---")
    st.subheader("📋 Pendências Formulário Qualitativo")
    
    df_faltam = pd.DataFrame()
    df_pendencias_ativ_form = pd.DataFrame()
    
    if df_form is not None:
        mes_num, ano_num = int(selected_mes), int(selected_ano)
        df_form_mes = df_form[(df_form['Mes_Submissao'] == mes_num) & (df_form['Ano_Submissao'] == ano_num)]
        igrejas_que_responderam = df_form_mes['Igreja_Identificada'].dropna().unique().tolist()
        
        igrejas_alvo = [loc for s_n, loc in todas_igrejas_cadastro]
        faltam_form = [ig for ig in igrejas_alvo if ig not in igrejas_que_responderam and ig not in IGREJAS_IGNORADAS]
        
        with st.expander(f"⚠️ {len(faltam_form)} congregações não enviaram o formulário"):
            if faltam_form:
                df_faltam = pd.DataFrame(faltam_form, columns=["Igreja"])
                df_faltam['Setor'] = df_faltam['Igreja'].apply(classificar_setor)
                df_faltam = df_faltam[['Setor', 'Igreja']]
                st.dataframe(df_faltam, use_container_width=True, hide_index=True)
                pdf_bytes = gerar_pdf("Igrejas que nao enviaram o Formulario", [("Faltam Formularios", df_faltam)])
                st.download_button("📥 Gerar PDF (Sem Formulário)", data=pdf_bytes, file_name="Faltam_Formularios.pdf", mime="application/pdf")
            else: 
                st.success("Todas as congregações filtradas enviaram o formulário!")

        colunas_analisadas = [c for c in df_form_mes.columns if 'ASSINALAR AS ATIVIDADES' in str(c).upper()]
        pendencias_ativ_form = []
        
        if colunas_analisadas:
            for igreja in igrejas_que_responderam:
                if filtro_igreja != "Todas" and igreja != filtro_igreja: continue
                if filtro_setor != "Todos" and classificar_setor(igreja) != filtro_setor: continue
                    
                atividades_exigidas = set()
                df_igreja_siga = df_base_pendencias[df_base_pendencias['Localidade'] == igreja]
                
                if 'Livro' in df_igreja_siga.columns:
                    for atv in df_igreja_siga['Livro'].dropna(): atividades_exigidas.add(str(atv).upper())
                
                cod_ig = str(igreja).split(' - ')[0].strip()
                contagens_ig = arquivos_anexos.get(cod_ig, {})
                
                def buscar_nas_contagens_form(termos_busca):
                    for termo in termos_busca:
                        for col_name, count in contagens_ig.items():
                            if termo in col_name and count > 0:
                                return True
                    return False

                if buscar_nas_contagens_form(['ESTAC', 'PÁTIO', 'PATIO']): atividades_exigidas.add("PÁTIO")
                if buscar_nas_contagens_form(['GEM', 'G.E.M']): atividades_exigidas.add("GEM")
                if buscar_nas_contagens_form(['MPEZA', 'MPESA']): atividades_exigidas.add("LIMPEZA")
                if buscar_nas_contagens_form(['COZINHA']): atividades_exigidas.add("COZINHA")
                if buscar_nas_contagens_form(['INFA', 'EBI', 'E.B.I']): atividades_exigidas.add("ESPAÇO INFANTIL")
                if buscar_nas_contagens_form(['MANUT']): atividades_exigidas.add("MANUTENÇÃO PREVENTIVA")

                respostas_igreja = df_form_mes[df_form_mes['Igreja_Identificada'] == igreja]
                texto_marcado = " ".join([str(x).upper() for col in colunas_analisadas for x in respostas_igreja[col].dropna().tolist()])
                
                falta_marcar = []
                for atv_req in atividades_exigidas:
                    for atv_padrao in ATIVIDADES_OBRIGATORIAS + ATIVIDADES_ESPORADICAS:
                        if atv_padrao in atv_req and atv_padrao not in texto_marcado: falta_marcar.append(atv_padrao)
                            
                falta_marcar = list(set(falta_marcar))
                if falta_marcar: pendencias_ativ_form.append({'Setor': classificar_setor(igreja), 'Igreja': igreja, 'Faltou analisar no Form': ", ".join(falta_marcar)})

        df_pendencias_ativ_form = pd.DataFrame(pendencias_ativ_form) if pendencias_ativ_form else pd.DataFrame()
        
        if filtro_atividade != "Todas":
            if not df_pendencias_ativ_form.empty:
                df_pendencias_ativ_form = df_pendencias_ativ_form[df_pendencias_ativ_form['Faltou analisar no Form'].str.upper().str.contains(filtro_atividade, na=False)]
        
        with st.expander(f"⚠️ {len(df_pendencias_ativ_form)} congregações com atividades faltando no preenchimento do Form"):
            if not df_pendencias_ativ_form.empty: 
                st.dataframe(df_pendencias_ativ_form, use_container_width=True, hide_index=True)
                pdf_bytes = gerar_pdf("Atividades Faltando no Form", [("Pendências de Preenchimento", df_pendencias_ativ_form)])
                st.download_button("📥 Gerar PDF (Atividades Faltando)", data=pdf_bytes, file_name="Atividades_Faltando_Form.pdf", mime="application/pdf")
            else: 
                st.success("Todas as atividades lançadas foram analisadas nos formulários!")

        erros_por_atividade = []
        for ativ in ATIVIDADES_OBRIGATORIAS + ATIVIDADES_ESPORADICAS:
            erros_totais = 0
            col_alvo = [c for c in df_form_mes.columns if ativ.upper() in str(c).upper() and ('RASURA' in str(c).upper() or 'ERRO' in str(c).upper() or 'BRANCO' in str(c).upper())]
            for col in col_alvo: erros_totais += pd.to_numeric(df_form_mes[col], errors='coerce').sum()
            lancamentos_totais = df[df['Livro'].astype(str).str.upper().str.contains(ativ.upper(), na=False)].shape[0] if 'Livro' in df.columns else 0
            taxa = (erros_totais / lancamentos_totais * 100) if lancamentos_totais > 0 else 0
            erros_por_atividade.append({'Atividade': ativ, 'Taxa (%)': taxa, 'Erros': erros_totais, 'Lançamentos': lancamentos_totais})
            
        fig_erros = px.bar(pd.DataFrame(erros_por_atividade), x='Atividade', y='Taxa (%)', title="Taxa de Erro vs Lançamentos (Formulário Qualitativo) - Clique na barra para detalhar", hover_data=['Erros', 'Lançamentos'], text_auto='.1f', color='Taxa (%)', color_continuous_scale="Reds")
        
        fig_erros.update_layout(
            coloraxis_showscale=False,
            dragmode=False, 
            xaxis=dict(fixedrange=True), 
            yaxis=dict(fixedrange=True)  
        )
        
        eventos = st.plotly_chart(
            fig_erros, 
            use_container_width=True, 
            config={'displayModeBar': False},
            on_select="rerun"
        )

        if filtro_igreja == "Todas" and eventos and len(eventos.selection.points) > 0:
            atividade_selecionada = eventos.selection.points[0]["x"]
            
            st.markdown("---")
            st.markdown(f"### 🔍 Origem dos Erros: {atividade_selecionada}")
            
            erros_por_igreja = []
            col_alvo_detalhe = [c for c in df_form_mes.columns if atividade_selecionada.upper() in str(c).upper() and ('RASURA' in str(c).upper() or 'ERRO' in str(c).upper() or 'BRANCO' in str(c).upper())]
            
            for ig in df_form_mes['Igreja_Identificada'].dropna().unique():
                df_ig_form = df_form_mes[df_form_mes['Igreja_Identificada'] == ig]
                erros_ig = 0
                for col in col_alvo_detalhe:
                    erros_ig += pd.to_numeric(df_ig_form[col], errors='coerce').sum()
                
                if erros_ig > 0:
                    erros_por_igreja.append({'Igreja': ig, 'Erros': erros_ig})
            
            if erros_por_igreja:
                df_erros_detalhe = pd.DataFrame(erros_por_igreja).sort_values(by='Erros', ascending=True)
                
                fig_detalhe = px.bar(
                    df_erros_detalhe, 
                    x='Erros', 
                    y='Igreja', 
                    orientation='h', 
                    title=f"Igrejas com erros apontados em {atividade_selecionada}",
                    text_auto=True,
                    color='Erros',
                    color_continuous_scale="Reds"
                )
                
                fig_detalhe.update_layout(
                    coloraxis_showscale=False, 
                    dragmode=False,
                    xaxis=dict(fixedrange=True),
                    yaxis=dict(fixedrange=True)
                )
                
                st.plotly_chart(fig_detalhe, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info(f"Nenhum erro detalhado encontrado para a atividade: {atividade_selecionada}.")

    st.markdown("---")
    total_registros = len(df)
    total_valor = df['Valor'].sum() if 'Valor' in df.columns else 0
    media_valor = df['Valor'].mean() if 'Valor' in df.columns and total_registros > 0 else 0

    st.subheader("📌 Métricas Gerais Financeiras (Filtradas)")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Lançamentos (Filtro Atual)", f"{total_registros}")
    col_kpi2.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col_kpi3.metric("Ticket Médio (R$)", f"R$ {media_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    st.markdown("---")
    st.subheader("Alertas de Verificação (Diferença de Quantidades)")
    st.warning("⚠️ **Aviso Importante para Verificação Manual:** O valor esperado de lançamentos (vindo da planilha de anexos) é calculado por páginas. Se, por algum motivo, um anexo for enviado com páginas a mais (ex: páginas adicionais em branco, canceladas ou preenchidas incorretamente na origem), isso levará a um alerta de falso positivo nesta seção. Utilize esta lista apenas para verificação manual de possíveis esquecimentos na digitação.")
    
    with st.expander(f"📉 {len(df_pendencias_qnt)} Alertas de Quantidade de Lançamentos (Diferença Esperado vs Realizado >= 14)"):
        if not df_pendencias_qnt.empty:
            st.dataframe(df_pendencias_qnt, use_container_width=True, hide_index=True)
            pdf_bytes = gerar_pdf("Alertas de Quantidade de Lancamentos", [("Diferença Lançado vs Esperado", df_pendencias_qnt)])
            st.download_button("📥 Gerar PDF (Alertas Quantidade)", data=pdf_bytes, file_name="Alertas_Quantidade_Lancamentos.pdf", mime="application/pdf")
        else:
            st.success("Nenhum alerta de quantidade de lançamentos encontrado. Todas as igrejas parecem ter lançado os voluntários proporcionalmente ao indicado no anexo.")

    st.markdown("---")
    st.subheader("📑 Geração de Relatório Consolidado (Tudo)")
    st.info("O arquivo gerado abaixo conterá todas as tabelas e métricas pendentes relativas aos filtros selecionados acima.")
    
    sessoes_gerais = [
        ("Pendencias de Categorias (SIGA)", df_pendencias_siga),
        ("Pendencias de Quantidade de Lancamentos", df_pendencias_qnt),
        ("Pendencia de anexo no fechamento", df_pendencias_drive),
        ("Fechamentos Mensais com status ABERTO", df_igrejas_abertas),
        ("Igrejas que não enviaram o Formulario", df_faltam),
        ("Atividades faltando no preenchimento do Form", df_pendencias_ativ_form)
    ]
    
    pdf_geral_bytes = gerar_pdf(f"Relatorio Geral de Pendencias - {selected_mes}/{selected_ano}", sessoes_gerais)
    
    st.download_button(
        label="📥 Baixar Relatório Geral em PDF",
        data=pdf_geral_bytes,
        file_name=f"Relatorio_Geral_{selected_mes}_{selected_ano}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )

else: 
    st.error(f"⚠️ Base de dados principal não encontrada: 'tabela {selected_mes}-{selected_ano}.xlsx' ou '.ods'.")
