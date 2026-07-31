import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os
import requests

st.set_page_config(
    page_title="Dashboard de Voluntários & Fechamento",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

esconder_estilo = """
    <style>
    /* Oculta o menu de desenvolvedor e botão de deploy */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Regras específicas para celulares */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        h1 {
            font-size: 1.6rem !important;
        }
    }
    
    .filtros-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    </style>
"""
st.markdown(esconder_estilo, unsafe_allow_html=True)

if 'setor' not in st.session_state:
    st.session_state.setor = "Todos"
if 'igreja' not in st.session_state:
    st.session_state.igreja = "Todas"

def set_setor(s):
    st.session_state.setor = s
    st.session_state.igreja = "Todas"

def set_igreja(i):
    st.session_state.igreja = i

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

ATIVIDADES_OBRIGATORIAS = ['LIMPEZA', 'GEM', 'PÁTIO', 'MANUTENÇÃO PREVENTIVA', 'ESPAÇO INFANTIL', 'COZINHA']
IGREJAS_IGNORADAS = ['ADM - MARINGÁ - PR', 'PIA - MARINGÁ', 'BR 14-0601 - MARINGÁ - CENTRO']

def classificar_setor(localidade):
    for setor, locais in SETORES.items():
        if localidade in locais:
            return setor
    return 'Não Classificado'

@st.cache_data
def load_data(mes, ano):
    nome_arquivo = f"tabela {mes}-{ano}.xlsx"
    try:
        df = pd.read_excel(nome_arquivo)
    except FileNotFoundError:
        return None
    
    df.columns = df.columns.str.strip()
    col_mapping = {'Localida': 'Localidade', 'Voluntá': 'Voluntario', 'Data Na': 'Data Nasc', 'H. Des': 'Horas Desconto'}
    df = df.rename(columns=lambda x: col_mapping.get(x, x))

    if 'Valor' in df.columns:
        if df['Valor'].dtype == object:
            df['Valor'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
            
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)

    if 'Localidade' in df.columns:
        df['Setor'] = df['Localidade'].apply(classificar_setor)

    return df

@st.cache_data
def load_form_data():
    try:
        df_form = pd.read_excel('FORMULÁRIO QUALITATIVO 2026 (respostas).xlsx')
        colunas_igreja = [c for c in df_form.columns if 'ESCOLHA A CASA DE ORAÇÃO' in str(c).upper()]
        
        def extrair_igreja(row):
            for col in colunas_igreja:
                if pd.notna(row[col]) and str(row[col]).strip() != "":
                    return str(row[col]).strip()
            return None
            
        if colunas_igreja:
            df_form['Igreja_Identificada'] = df_form.apply(extrair_igreja, axis=1)
        else:
            df_form['Igreja_Identificada'] = None
            
        if 'MÊS' in df_form.columns:
            df_form['Mes_Submissao'] = pd.to_numeric(df_form['MÊS'], errors='coerce')
        if 'ANO' in df_form.columns:
            df_form['Ano_Submissao'] = pd.to_numeric(df_form['ANO'], errors='coerce')

        return df_form
    except FileNotFoundError:
        return None

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

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_google_drive_data(mes, ano, api_key):
    """ Busca PDFs no Google Drive cruzando os nomes exatos. """
    if not api_key:
        return None

    def search_drive(query):
        url = "https://www.googleapis.com/drive/v3/files"
        params = {'q': query, 'key': api_key, 'fields': "files(id, name, mimeType)"}
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                return res.json().get('files', [])
        except:
            pass
        return []

    folder_mes_name = f"{mes}-{ano}"
    # Busca a pasta do mês (ex: 06-2026) em qualquer lugar do Drive compartilhado
    pastas_mes = search_drive(f"name = '{folder_mes_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false")
    
    if not pastas_mes:
        return {} 
        
    mes_id = pastas_mes[0]['id']
    drive_resultados = {}
    
    # Pega tudo dentro da pasta do mês (SETOR_01, SETOR_02, etc)
    pastas_setores = search_drive(f"'{mes_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false")
    
    for setor in pastas_setores:
        # Pega as pastas de igrejas dentro de cada setor
        pastas_igrejas = search_drive(f"'{setor['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false")
        
        for igreja_folder in pastas_igrejas:
            arquivos_igreja = search_drive(f"'{igreja_folder['id']}' in parents and trashed=false")
            
            status_arquivos = {
                "PÁTIO": False, "GEM": False, "LIMPEZA": False,
                "COZINHA": False, "ESPAÇO INFANTIL": False, "MANUTENÇÃO PREVENTIVA": False
            }
            
            for arq in arquivos_igreja:
                nome_upper = arq['name'].upper()
                if 'OCORRENC' in nome_upper or 'RELAT' in nome_upper: continue
                if 'ESTAC' in nome_upper or 'PÁTIO' in nome_upper or 'PATIO' in nome_upper: status_arquivos["PÁTIO"] = True
                if 'GEM' in nome_upper or 'G.E.M' in nome_upper: status_arquivos["GEM"] = True
                if 'MPEZA' in nome_upper or 'MPESA' in nome_upper: status_arquivos["LIMPEZA"] = True
                if 'COZINHA' in nome_upper: status_arquivos["COZINHA"] = True
                if 'INFA' in nome_upper or 'EBI' in nome_upper or 'E.B.I' in nome_upper: status_arquivos["ESPAÇO INFANTIL"] = True
                if 'MAN' in nome_upper: status_arquivos["MANUTENÇÃO PREVENTIVA"] = True
            
            # CORREÇÃO: Extrai o código exatamente como o sistema usa: "BR 14-0603"
            codigo_igreja = igreja_folder['name'].split(" - ")[0].strip()
            drive_resultados[codigo_igreja] = status_arquivos
            
    return drive_resultados

def buscar_status_drive_da_igreja(nome_igreja, drive_data):
    if not drive_data: return None
    # Extrai o "BR 14-XXXX" da tabela para casar exato com a leitura do Drive
    codigo_alvo = nome_igreja.split(" - ")[0].strip()
    return drive_data.get(codigo_alvo, {
        "PÁTIO": False, "GEM": False, "LIMPEZA": False,
        "COZINHA": False, "ESPAÇO INFANTIL": False, "MANUTENÇÃO PREVENTIVA": False
    })

st.title("📊 Painel de Comando - Voluntários e Fechamento")

st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
st.markdown("<b>📅 Escolha o Período e a Atividade:</b>", unsafe_allow_html=True)

hoje = datetime.date.today()
meses = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
anos = [str(y) for y in range(2023, 2030)]

idx_mes = (hoje.month - 2) % 12
ano_padrao = str(hoje.year if hoje.month > 1 else hoje.year - 1)
idx_ano = anos.index(ano_padrao) if ano_padrao in anos else 3

col_data1, col_data2, col_data3 = st.columns(3)
selected_mes = col_data1.selectbox("🗓️ Mês", meses, index=idx_mes)
selected_ano = col_data2.selectbox("📅 Ano", anos, index=idx_ano)
selected_atividade = col_data3.selectbox("🎯 Filtrar Métricas por Atividade:", ["Todas", "LIMPEZA", "GEM", "PÁTIO", "MANUTENÇÃO PREVENTIVA", "ESPAÇO INFANTIL", "COZINHA"])

st.markdown('</div>', unsafe_allow_html=True)

df = load_data(selected_mes, selected_ano)
df_form = load_form_data()
df_fechamento = load_fechamento_data(selected_mes, selected_ano)

# Tentativa de ler a API Key do Streamlit Cloud
api_key = st.secrets.get("GDRIVE_API_KEY", None) if hasattr(st, "secrets") else None
with st.spinner("Sincronizando com Google Drive..."):
    drive_data = fetch_google_drive_data(selected_mes, selected_ano, api_key)

if df is not None:
    st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
    st.markdown("<b>🏢 Selecione o Setor de Atuação:</b>", unsafe_allow_html=True)
    
    setores_opcoes = ["Todos", "Setor 1", "Setor 2", "Setor 3", "Não Classificado"]
    cols_setores = st.columns(5)
    for i, s in enumerate(setores_opcoes):
        with cols_setores[i]:
            estilo = "primary" if st.session_state.setor == s else "secondary"
            st.button(s, type=estilo, use_container_width=True, on_click=set_setor, args=(s,))
            
    if st.session_state.setor != "Todos":
        st.markdown(f"<br><b>⛪ Selecione a Igreja ({st.session_state.setor}):</b>", unsafe_allow_html=True)
        if st.session_state.setor in SETORES:
            igrejas_do_setor = sorted([l for l in SETORES[st.session_state.setor] if l not in IGREJAS_IGNORADAS])
        else:
            igrejas_do_setor = sorted([l for l in df[df['Setor'] == 'Não Classificado']['Localidade'].dropna().unique() if l not in IGREJAS_IGNORADAS])
            
        igrejas_opcoes = ["Todas"] + igrejas_do_setor
        cols_por_linha = 4
        for i in range(0, len(igrejas_opcoes), cols_por_linha):
            cols_igrejas = st.columns(cols_por_linha)
            for j in range(cols_por_linha):
                if i + j < len(igrejas_opcoes):
                    igreja_nome = igrejas_opcoes[i + j]
                    nome_curto = igreja_nome.split('-')[-1].strip() if igreja_nome != "Todas" else "Todas"
                    with cols_igrejas[j]:
                        estilo_igreja = "primary" if st.session_state.igreja == igreja_nome else "secondary"
                        st.button(
                            nome_curto, help=igreja_nome, type=estilo_igreja, 
                            use_container_width=True, on_click=set_igreja, args=(igreja_nome,),
                            key=f"btn_{igreja_nome}"
                        )
    st.markdown('</div>', unsafe_allow_html=True)

    if selected_atividade != "Todas":
        df = df[df['Livro'].str.upper() == selected_atividade]
    if st.session_state.setor != "Todos":
        df = df[df['Setor'] == st.session_state.setor]
    if st.session_state.igreja != "Todas":
        df = df[df['Localidade'] == st.session_state.igreja]

    st.header(f"🚨 Alertas e Pendências ({selected_mes}/{selected_ano})")
    
    if st.session_state.igreja != "Todas":
        igrejas_cobradas = [st.session_state.igreja]
    elif st.session_state.setor != "Todos":
        igrejas_cobradas = [igreja for igreja in SETORES.get(st.session_state.setor, []) if igreja not in IGREJAS_IGNORADAS]
    else:
        igrejas_cobradas = [igreja for lista in SETORES.values() for igreja in lista if igreja not in IGREJAS_IGNORADAS]

    pendencias_atividades_siga = []
    pendencias_anexos_drive = []

    if 'Livro' in df.columns and 'Localidade' in df.columns:
        for igreja in igrejas_cobradas:
            df_igreja = df[df['Localidade'] == igreja]
            livros_lancados = [str(x).upper() for x in df_igreja['Livro'].dropna().unique().tolist()]
            texto_livros_lancados = ' '.join(livros_lancados)
            
            status_drive = buscar_status_drive_da_igreja(igreja, drive_data)
            faltam_no_siga = []
            faltam_anexos = []

            for ativ in ATIVIDADES_OBRIGATORIAS:
                # 1. Avaliação de Lançamentos (SIGA)
                if ativ not in texto_livros_lancados:
                    if ativ in ['LIMPEZA', 'GEM', 'PÁTIO']:
                        faltam_no_siga.append(ativ) # Obrigatórias (Sempre cobra)
                    elif ativ in ['MANUTENÇÃO PREVENTIVA', 'ESPAÇO INFANTIL', 'COZINHA']:
                        # Esporádicas: Só cobra se a equipe scaneou o PDF no Drive mas esqueceu de lançar no SIGA
                        if status_drive is not None and status_drive.get(ativ) == True:
                            faltam_no_siga.append(f"{ativ} (Esqueceu SIGA)") 
                            
                # 2. Avaliação de Anexos (Drive)
                # Só cobra o PDF se a atividade FOI LANÇADA no SIGA
                if status_drive is not None and ativ in texto_livros_lancados:
                    if not status_drive.get(ativ):
                        faltam_anexos.append(ativ)

            if faltam_no_siga:
                pendencias_atividades_siga.append({
                    'Setor': classificar_setor(igreja), 'Igreja': igreja, 'Falta Lançar no Sistema': ", ".join(faltam_no_siga)
                })
            
            if faltam_anexos:
                pendencias_anexos_drive.append({
                    'Setor': classificar_setor(igreja), 'Igreja': igreja, 'Falta Anexar PDF no Drive': ", ".join(faltam_anexos)
                })

    g_col_a, g_col_b = st.columns(2)
    with g_col_a:
        st.markdown("**1. Pendentes no Sistema (SIGA)**")
        if pendencias_atividades_siga:
            st.dataframe(pd.DataFrame(pendencias_atividades_siga), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Atividades em dia!")
            
    with g_col_b:
        st.markdown("**2. PDFs não encontrados (Google Drive)**")
        if not api_key:
            st.error("Configure a GDRIVE_API_KEY no Streamlit Secrets!")
        elif pendencias_anexos_drive:
            st.dataframe(pd.DataFrame(pendencias_anexos_drive), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os lançamentos possuem arquivo correspondente!")

    st.subheader("📂 Status de Fechamento Mensal")
    if df_fechamento is not None:
        fechamento_filtrado = df_fechamento[df_fechamento['Localidade'].isin(igrejas_cobradas)].copy()
        fechamento_filtrado['Setor'] = fechamento_filtrado['Localidade'].apply(classificar_setor)
        
        igrejas_abertas = fechamento_filtrado[fechamento_filtrado['Status'].str.upper() == 'ABERTO']
        if not igrejas_abertas.empty:
            st.warning(f"⚠️ Existem {len(igrejas_abertas)} igrejas com o status ABERTO.")
            st.dataframe(igrejas_abertas[['Setor', 'Localidade', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ Todos os fechamentos avaliados estão ENCERRADOS.")
    else:
        st.info(f"ℹ️ Arquivo 'FECHAMENTO MENSAL {selected_mes}-{selected_ano}.txt' não encontrado.")

    st.subheader("📋 Pendências Formulário Qualitativo")
    if df_form is not None:
        mes_num = int(selected_mes)
        ano_num = int(selected_ano)
        df_form_filtrado = df_form[(df_form['Mes_Submissao'] == mes_num) & (df_form['Ano_Submissao'] == ano_num)]
        igrejas_que_responderam = df_form_filtrado['Igreja_Identificada'].dropna().unique().tolist()
        
        # --- INÍCIO DA ALTERAÇÃO 3: NOVA LÓGICA QUALITATIVO E GRÁFICO ---
        # 1. Congregações que NÃO enviaram o formulário
        faltam_form = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_que_responderam]
        
        st.markdown("**1. Formulários Não Enviados**")
        if faltam_form:
            df_faltam_form = pd.DataFrame(faltam_form, columns=["Igreja"])
            df_faltam_form['Setor'] = df_faltam_form['Igreja'].apply(classificar_setor)
            with st.expander(f"⚠️ {len(faltam_form)} congregações não enviaram o formulário", expanded=False):
                st.dataframe(df_faltam_form[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todas as congregações enviaram o formulário!")

        # 2. Atividades NÃO informadas/analisadas no formulário
        st.markdown("**2. Atividades Não Analisadas no Formulário**")
        colunas_analisadas = [c for c in df_form_filtrado.columns if 'ASSINALAR AS ATIVIDADES' in str(c).upper()]
        
        pendencias_ativ_qualitativo = []
        
        if colunas_analisadas:
            for igreja in igrejas_que_responderam:
                if igreja in igrejas_cobradas: # Somente avalia igrejas dentro do filtro atual
                    # Pegar livros lançados no SIGA
                    df_igreja_siga = df[df['Localidade'] == igreja]
                    livros_lancados_siga = [str(x).upper() for x in df_igreja_siga['Livro'].dropna().unique().tolist()] if 'Livro' in df_igreja_siga.columns else []
                    
                    # Pegar status do Drive
                    status_drive = buscar_status_drive_da_igreja(igreja, drive_data)
                    
                    # Agrupar todas as respostas desta igreja (caso mais de um colaborador tenha preenchido)
                    respostas_igreja = df_form_filtrado[df_form_filtrado['Igreja_Identificada'] == igreja]
                    texto_analisadas = " ".join([str(x).upper() for col in colunas_analisadas for x in respostas_igreja[col].dropna().tolist()])
                    
                    faltam_na_analise = []
                    for ativ in ATIVIDADES_OBRIGATORIAS:
                        # Regra: Só exige no form se foi lançada no SIGA OU se o PDF existe no Drive
                        is_required = (ativ in livros_lancados_siga) or (status_drive is not None and status_drive.get(ativ) == True)
                        
                        if is_required and (ativ not in texto_analisadas):
                            faltam_na_analise.append(ativ)
                            
                    if faltam_na_analise:
                        pendencias_ativ_qualitativo.append({
                            'Setor': classificar_setor(igreja),
                            'Igreja': igreja,
                            'Falta Analisar no Form': ", ".join(faltam_na_analise)
                        })
        
        if pendencias_ativ_qualitativo:
            with st.expander(f"⚠️ {len(pendencias_ativ_qualitativo)} congregações com atividades faltando no preenchimento", expanded=False):
                st.dataframe(pd.DataFrame(pendencias_ativ_qualitativo), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todas as atividades obrigatórias foram analisadas!")

        st.subheader("📊 Taxa de Erros Qualitativos (Por Atividade)")
        df_form_grafico = df_form_filtrado[df_form_filtrado['Igreja_Identificada'].isin(igrejas_cobradas)]
        
        erros_por_atividade = []
        for ativ in ATIVIDADES_OBRIGATORIAS:
            erros_totais = 0
            # Busca todas as colunas que têm a Atividade E alguma palavra de erro
            colunas_alvo = [c for c in df_form_grafico.columns if ativ.upper() in str(c).upper() and 
                            ('RASURA' in str(c).upper() or 'ERRO' in str(c).upper() or 'BRANCO' in str(c).upper())]
            for col in colunas_alvo:
                erros_totais += pd.to_numeric(df_form_grafico[col], errors='coerce').sum()
                
            # Verifica o total de lançamentos na tabela local
            lancamentos_totais = df[df['Livro'].astype(str).str.upper().str.contains(ativ.upper(), na=False)].shape[0] if 'Livro' in df.columns else 0
            taxa = (erros_totais / lancamentos_totais * 100) if lancamentos_totais > 0 else 0
            
            erros_por_atividade.append({
                'Atividade': ativ, 'Taxa de Erro (%)': taxa,
                'Erros (Qtd)': erros_totais, 'Lançamentos': lancamentos_totais
            })
            
        df_grafico_erros = pd.DataFrame(erros_por_atividade)
        fig_erros = px.bar(
            df_grafico_erros, x='Atividade', y='Taxa de Erro (%)',
            title="Taxa de Erro vs Lançamentos (Baseado no Form Qualitativo)",
            hover_data=['Erros (Qtd)', 'Lançamentos'], text_auto='.1f',
            color='Taxa de Erro (%)', color_continuous_scale="Reds"
        )
        
        # --- REMOVE A BARRA DE CORES LATERAL DA LEGENDA ---
        fig_erros.update_layout(coloraxis_showscale=False) 
        
        st.plotly_chart(fig_erros, use_container_width=True)
        # --- FIM DA ALTERAÇÃO 3 ---
    else:
        st.info("ℹ️ Arquivo 'FORMULÁRIO QUALITATIVO 2026 (respostas).xlsx' não encontrado.")

    st.markdown("---")
    st.subheader("📌 Métricas Gerais Financeiras")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    total_registros = len(df)
    total_valor = df['Valor'].sum() if 'Valor' in df.columns else 0
    media_valor = df['Valor'].mean() if 'Valor' in df.columns and total_registros > 0 else 0

    col_kpi1.metric("Total de Lançamentos", f"{total_registros}")
    col_kpi2.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col_kpi3.metric("Ticket Médio (R$)", f"R$ {media_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    g_col1, g_col2 = st.columns(2)
    with g_col1:
        if 'Localidade' in df.columns and 'Valor' in df.columns:
            df_grafico1 = df.groupby('Setor' if st.session_state.setor == "Todos" else 'Localidade')['Valor'].sum().reset_index()
            x_axis = 'Setor' if st.session_state.setor == "Todos" else 'Localidade'
            
            fig_loc = px.bar(
                df_grafico1, x=x_axis, y='Valor', title="Custo Total (R$)",
                text_auto='.2f', color=x_axis, color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_loc.update_layout(showlegend=False)
            st.plotly_chart(fig_loc, use_container_width=True)

    with g_col2:
        if 'Livro' in df.columns and 'Valor' in df.columns:
            df_fun = df.groupby('Livro')['Valor'].sum().reset_index()
            fig_fun = px.pie(
                df_fun, names='Livro', values='Valor', 
                title="Distribuição de Custo por Atividade", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_fun, use_container_width=True)

else:
    st.error(f"⚠️ Base de dados não encontrada: 'tabela {selected_mes}-{selected_ano}.xlsx'. Certifique-se de que o arquivo foi enviado para o repositório.")
