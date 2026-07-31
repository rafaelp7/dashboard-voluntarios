import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# ---------------------------------------------------------
# CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Voluntários",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" # Esconde a barra lateral por padrão
)

esconder_estilo = """
    <style>
    /* Oculta o menu do Streamlit e o ícone do GitHub */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp > header {display: none;}
    
    /* Regras específicas para telas de celular (menores que 768px) */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        /* Ajuste de espaçamento dos botões no celular */
        .stButton > button {
            margin-bottom: 5px;
        }
    }
    
    /* Deixa a área de botões visualmente separada */
    .filtros-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
"""
st.markdown(esconder_estilo, unsafe_allow_html=True)

# ---------------------------------------------------------
# VARIÁVEIS DE ESTADO (Para os botões funcionarem)
# ---------------------------------------------------------
if 'setor' not in st.session_state:
    st.session_state.setor = "Todos"
if 'igreja' not in st.session_state:
    st.session_state.igreja = "Todas"

def set_setor(s):
    st.session_state.setor = s
    st.session_state.igreja = "Todas" # Reseta a igreja ao trocar de setor

def set_igreja(i):
    st.session_state.igreja = i

# ---------------------------------------------------------
# DADOS GERAIS
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# CARREGAMENTO DE DADOS (CACHED) DINÂMICO
# ---------------------------------------------------------
@st.cache_data
def load_data(mes, ano):
    nome_arquivo = f"tabela {mes:02d}-{ano}.xlsx"
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
    nome_arquivo = f"FECHAMENTO MENSAL {mes:02d}-{ano}.txt"
    try:
        df_fechamento = pd.read_csv(nome_arquivo, sep='\t', skiprows=1, names=["Localidade", "Status"])
        df_fechamento['Localidade'] = df_fechamento['Localidade'].str.strip()
        df_fechamento['Status'] = df_fechamento['Status'].str.strip()
        return df_fechamento
    except FileNotFoundError:
        return None

# --- Início da Aplicação ---
st.title("📊 Painel de Comando - Voluntários e Fechamento")

# ---------------------------------------------------------
# NOVO CABEÇALHO: FILTROS DINÂMICOS DE DATA
# ---------------------------------------------------------
st.markdown('<div class="filtros-container">', unsafe_allow_html=True)

hoje = datetime.date.today()
mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
ano_padrao = hoje.year if hoje.month > 1 else hoje.year - 1
meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

col_data1, col_data2 = st.columns(2)
mes_selecionado_nome = col_data1.selectbox("🗓️ Mês Referência:", list(meses_nomes.values()), index=mes_anterior - 1)
ano_selecionado = col_data2.number_input("📅 Ano:", min_value=2020, max_value=2100, value=ano_padrao, step=1)
mes_selecionado_num = list(meses_nomes.keys())[list(meses_nomes.values()).index(mes_selecionado_nome)]

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# CARREGAR DADOS COM BASE NA DATA SELECIONADA
# ---------------------------------------------------------
df = load_data(mes_selecionado_num, ano_selecionado)
df_form = load_form_data()
df_fechamento = load_fechamento_data(mes_selecionado_num, ano_selecionado)


if df is not None:
    # ---------------------------------------------------------
    # NOVO CABEÇALHO: BOTÕES DE SETOR E IGREJA
    # ---------------------------------------------------------
    st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
    
    # Filtro de Atividade extraído da base já carregada
    atividades_disp = ["Todas"] + sorted(list(df['Livro'].dropna().unique())) if 'Livro' in df.columns else ["Todas"]
    selected_atividade = st.selectbox("🎯 Filtrar Atividade Específica (Gráficos/Métricas):", atividades_disp)

    st.markdown("<br><b>🏢 Selecione o Setor de Atuação:</b>", unsafe_allow_html=True)
    
    # Botões de Setor
    setores_opcoes = ["Todos", "Setor 1", "Setor 2", "Setor 3", "Não Classificado"]
    cols_setores = st.columns(5)
    for i, s in enumerate(setores_opcoes):
        with cols_setores[i]:
            estilo = "primary" if st.session_state.setor == s else "secondary"
            st.button(s, type=estilo, use_container_width=True, on_click=set_setor, args=(s,))
            
    # Botões de Igreja (Aparecem dinamicamente)
    if st.session_state.setor != "Todos":
        st.markdown(f"<b>⛪ Selecione a Igreja ({st.session_state.setor}):</b>", unsafe_allow_html=True)
        
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
                    with cols_igrejas[j]:
                        estilo_igreja = "primary" if st.session_state.igreja == igreja_nome else "secondary"
                        st.button(
                            igreja_nome.split('-')[-1].strip() if igreja_nome != "Todas" else "Todas",
                            help=igreja_nome, 
                            type=estilo_igreja, 
                            use_container_width=True, 
                            on_click=set_igreja, 
                            args=(igreja_nome,),
                            key=f"btn_{igreja_nome}"
                        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ---------------------------------------------------------
    # APLICAÇÃO GLOBAL DOS FILTROS NOS DADOS
    # ---------------------------------------------------------
    # A data já foi filtrada na leitura do arquivo!
    
    # 1. Filtro de Atividade
    if selected_atividade != "Todas":
        df = df[df['Livro'] == selected_atividade]

    # 2. Filtros de Botão (Setor e Igreja)
    if st.session_state.setor != "Todos":
        df = df[df['Setor'] == st.session_state.setor]
        
    if st.session_state.igreja != "Todas":
        df = df[df['Localidade'] == st.session_state.igreja]


    # ---------------------------------------------------------
    # 🚨 SEÇÃO DE ALERTAS E PENDÊNCIAS
    # ---------------------------------------------------------
    st.header(f"🚨 Alertas e Pendências ({mes_selecionado_nome}/{ano_selecionado})")
    
    if st.session_state.igreja != "Todas":
        igrejas_cobradas = [st.session_state.igreja]
    elif st.session_state.setor != "Todos":
        igrejas_cobradas = [igreja for igreja in SETORES.get(st.session_state.setor, []) if igreja not in IGREJAS_IGNORADAS]
    else:
        igrejas_cobradas = [igreja for lista in SETORES.values() for igreja in lista if igreja not in IGREJAS_IGNORADAS]

    igrejas_presentes_df = df['Localidade'].dropna().unique().tolist() if 'Localidade' in df.columns else []

    # BLOCO 1: Nenhuma atividade
    st.subheader("❌ Nenhuma atividade lançada")
    igrejas_sem_lancamento = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_presentes_df]
    if igrejas_sem_lancamento:
        df_sem_lanc = pd.DataFrame(igrejas_sem_lancamento, columns=["Igreja"])
        df_sem_lanc['Setor'] = df_sem_lanc['Igreja'].apply(classificar_setor)
        st.dataframe(df_sem_lanc[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
    else:
        st.success("✅ Todas as igrejas da seleção atual possuem lançamentos!")

    # BLOCO 2: Atividades Faltando
    st.subheader("⚠️ Atividades faltando")
    if 'Livro' in df.columns and 'Localidade' in df.columns:
        pendencias_atividades = []
        for igreja in igrejas_presentes_df:
            if igreja in igrejas_cobradas:
                df_igreja = df[df['Localidade'] == igreja]
                texto_livros = ' '.join(df_igreja['Livro'].dropna().astype(str).str.upper().tolist())
                faltam = [ativ for ativ in ATIVIDADES_OBRIGATORIAS if ativ not in texto_livros]
                
                if faltam:
                    pendencias_atividades.append({
                        'Setor': classificar_setor(igreja),
                        'Igreja': igreja,
                        'Atividades Faltantes': ", ".join(faltam)
                    })
        
        if pendencias_atividades:
            df_pend_ativ = pd.DataFrame(pendencias_atividades)
            st.dataframe(df_pend_ativ, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todas as atividades obrigatórias foram registradas na seleção!")

    # BLOCO 3: Fechamento Mensal
    st.subheader("📂 Status de Fechamento Mensal")
    if df_fechamento is not None:
        fechamento_filtrado = df_fechamento[df_fechamento['Localidade'].isin(igrejas_cobradas)].copy()
        fechamento_filtrado['Setor'] = fechamento_filtrado['Localidade'].apply(classificar_setor)
        
        igrejas_abertas = fechamento_filtrado[fechamento_filtrado['Status'].str.upper() == 'ABERTO']
        if not igrejas_abertas.empty:
            st.warning(f"⚠️ Existem {len(igrejas_abertas)} igrejas com o status ABERTO em {mes_selecionado_nome}/{ano_selecionado}.")
            st.dataframe(igrejas_abertas[['Setor', 'Localidade', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ Todos os fechamentos avaliados estão ENCERRADOS ({mes_selecionado_nome}/{ano_selecionado}).")
    else:
        st.info(f"ℹ️ Arquivo 'FECHAMENTO MENSAL {mes_selecionado_num:02d}-{ano_selecionado}.txt' não encontrado.")

    # BLOCO 4: Pendências Formulário Qualitativo
    st.subheader("📋 Pendências Formulário Qualitativo")
    if df_form is not None:
        df_form_filtrado = df_form[(df_form['Mes_Submissao'] == mes_selecionado_num) & (df_form['Ano_Submissao'] == ano_selecionado)]
        igrejas_que_responderam = df_form_filtrado['Igreja_Identificada'].dropna().unique().tolist()
        faltam_form = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_que_responderam]
        
        if faltam_form:
            df_faltam_form = pd.DataFrame(faltam_form, columns=["Igreja"])
            df_faltam_form['Setor'] = df_faltam_form['Igreja'].apply(classificar_setor)
            st.warning(f"⚠️ {len(faltam_form)} congregações não enviaram o formulário qualitativo em {mes_selecionado_nome}.")
            st.dataframe(df_faltam_form[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ Formulários em dia ({mes_selecionado_nome})!")

        # Gráfico Taxa de Erros
        st.subheader("📊 Taxa de Erros Qualitativos (Por Atividade)")
        df_form_grafico = df_form_filtrado[df_form_filtrado['Igreja_Identificada'].isin(igrejas_cobradas)]
        
        erros_por_atividade = []
        for ativ in ATIVIDADES_OBRIGATORIAS:
            erros_totais = 0
            colunas_alvo = [c for c in df_form_grafico.columns if ativ.upper() in str(c).upper() and 
                            ('RASURA' in str(c).upper() or 'ERRO' in str(c).upper() or 'BRANCO' in str(c).upper())]
            for col in colunas_alvo:
                erros_totais += pd.to_numeric(df_form_grafico[col], errors='coerce').sum()
                
            lancamentos_totais = df[df['Livro'].astype(str).str.upper().str.contains(ativ.upper(), na=False)].shape[0]
            
            taxa = (erros_totais / lancamentos_totais * 100) if lancamentos_totais > 0 else 0
            erros_por_atividade.append({
                'Atividade': ativ,
                'Taxa de Erro (%)': taxa,
                'Erros (Qtd)': erros_totais,
                'Lançamentos': lancamentos_totais
            })
            
        df_grafico_erros = pd.DataFrame(erros_por_atividade)
        fig_erros = px.bar(
            df_grafico_erros, x='Atividade', y='Taxa de Erro (%)',
            title=f"Taxa de Erro vs Lançamentos ({mes_selecionado_nome})",
            hover_data=['Erros (Qtd)', 'Lançamentos'], text_auto='.1f',
            color='Taxa de Erro (%)', color_continuous_scale="Reds"
        )
        st.plotly_chart(fig_erros, use_container_width=True)
    else:
        st.info("ℹ️ Arquivo 'FORMULÁRIO QUALITATIVO 2026 (respostas).xlsx' não encontrado.")

    st.markdown("---")

    # ---------------------------------------------------------
    # MÉTRICAS E ANÁLISES FINANCEIRAS
    # ---------------------------------------------------------
    st.subheader("📌 Métricas Gerais Financeiras (Filtradas)")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    total_registros = len(df)
    total_valor = df['Valor'].sum() if 'Valor' in df.columns else 0
    media_valor = df['Valor'].mean() if 'Valor' in df.columns and total_registros > 0 else 0

    col_kpi1.metric("Total de Lançamentos", f"{total_registros}")
    col_kpi2.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col_kpi3.metric("Ticket Médio (R$)", f"R$ {media_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    st.markdown("---")

    st.subheader("📈 Distribuição Financeira")
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        if 'Localidade' in df.columns and 'Valor' in df.columns:
            if st.session_state.setor == "Todos":
                df_grafico1 = df.groupby('Setor')['Valor'].sum().reset_index()
                x_axis = 'Setor'
                titulo_graf = "Custo Total (R$) por Setor"
            else:
                df_grafico1 = df.groupby('Localidade')['Valor'].sum().reset_index()
                x_axis = 'Localidade'
                titulo_graf = f"Custo Total (R$) nas Igrejas"

            fig_loc = px.bar(
                df_grafico1, x=x_axis, y='Valor', title=titulo_graf,
                text_auto='.2f', color=x_axis, color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_loc.update_layout(showlegend=False)
            st.plotly_chart(fig_loc, use_container_width=True)

    with g_col2:
        if 'Livro' in df.columns and 'Valor' in df.columns:
            df_fun = df.groupby('Livro')['Valor'].sum().reset_index()
            df_fun['Livro'] = df_fun['Livro'].astype(str)
            fig_fun = px.pie(
                df_fun, names='Livro', values='Valor', 
                title="Distribuição do Custo por Atividade", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_fun, use_container_width=True)

else:
    st.error(f"⚠️ Base de dados não encontrada: 'tabela {mes_selecionado_num:02d}-{ano_selecionado}.xlsx'. Certifique-se de que o arquivo foi enviado para o repositório.")
