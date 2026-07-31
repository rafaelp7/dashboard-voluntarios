import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Voluntários & Horas",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Painel de Controle - Atividades e Voluntários")
st.markdown("---")

# Mapeamento dos setores fornecidos
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

# Igrejas que não devem ser cobradas nas pendências
IGREJAS_IGNORADAS = [
    'ADM - MARINGÁ - PR', 
    'PIA - MARINGÁ', 
    'BR 14-0601 - MARINGÁ - CENTRO'
]

# Função para carregar os dados do arquivo .txt do Fechamento Mensal
@st.cache_data
def load_fechamento_data(mes, ano):
    mes_str = str(mes).zfill(2)
    file_name = f'FECHAMENTO MENSAL {mes_str}-{ano}.txt'
    try:
        df_fechamento = pd.read_csv(file_name, sep='\t', skiprows=1, names=['Igreja', 'Status'])
        # Limpar os dados
        df_fechamento['Igreja'] = df_fechamento['Igreja'].str.strip()
        df_fechamento['Status'] = df_fechamento['Status'].str.strip()
        return df_fechamento
    except FileNotFoundError:
        return None

# Lista unificada de todas as igrejas esperadas e filtradas
todas_igrejas = [igreja for lista in SETORES.values() for igreja in lista]
igrejas_cobradas_base = [igreja for igreja in todas_igrejas if igreja not in IGREJAS_IGNORADAS]

def classificar_setor(localidade):
    for setor, locais in SETORES.items():
        if localidade in locais:
            return setor
    return 'Não Classificado'

@st.cache_data
def load_data():
    try:
        df = pd.read_excel('tabela.xlsx')
    except FileNotFoundError:
        return None
    
    df.columns = df.columns.str.strip()
    
    col_mapping = {
        'Localida': 'Localidade',
        'Voluntá': 'Voluntario',
        'Data Na': 'Data Nasc',
        'H. Des': 'Horas Desconto'
    }
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
        df_form.columns = df_form.columns.str.strip()
        
        if 'MÊS' in df_form.columns:
            df_form['Mes_Submissao'] = pd.to_numeric(df_form['MÊS'], errors='coerce')
        else:
            df_form['Mes_Submissao'] = None
            
        if 'ANO' in df_form.columns:
            df_form['Ano_Submissao'] = pd.to_numeric(df_form['ANO'], errors='coerce')
        else:
            df_form['Ano_Submissao'] = None
        
        colunas_igreja = ['ESCOLHA A CASA DE ORAÇÃO', 'ESCOLHA A CASA DE ORAÇÃO 2', 'ESCOLHA A CASA DE ORAÇÃO 3']
        
        def extrair_igreja_da_linha(row):
            for col in colunas_igreja:
                if col in row.index and pd.notna(row[col]) and str(row[col]).strip() != '':
                    return str(row[col]).strip()
            return None
            
        df_form['Igreja_Bruta'] = df_form.apply(extrair_igreja_da_linha, axis=1)

        def normalizar_igreja(valor):
            if pd.isna(valor) or not valor: return None
            val_limpo = str(valor).strip().upper()
            for ig_oficial in todas_igrejas:
                if ig_oficial.upper() in val_limpo or val_limpo in ig_oficial.upper():
                    return ig_oficial
            return val_limpo

        df_form['Igreja_Identificada'] = df_form['Igreja_Bruta'].apply(normalizar_igreja)
            
        return df_form
    except FileNotFoundError:
        return None

# Mapeamento dos meses globais para serem usados no Form e no Fechamento
meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 
               7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

hoje = datetime.date.today()
mes_atual = hoje.month
ano_atual = hoje.year
mes_anterior = 12 if mes_atual == 1 else mes_atual - 1
ano_padrao = ano_atual - 1 if mes_atual == 1 else ano_atual


# Carregamento dos dados
df = load_data()
df_form = load_form_data()

# =========================================================
# 🔍 BARRA LATERAL: FILTROS GLOBAIS
# =========================================================
st.sidebar.header("🔍 Filtros de Visualização")

selected_setor = "Todos"
selected_localidade = "Todas"
selected_atividade = "Todas"

if df is not None:
    setores_disponiveis = ["Todos"] + sorted(list(df['Setor'].unique()))
    selected_setor = st.sidebar.selectbox("Selecione o Setor", setores_disponiveis)
    
    # Prepara lista de igrejas dependendo do setor escolhido
    if selected_setor != "Todos":
        igrejas_no_setor = sorted(list(df[df['Setor'] == selected_setor]['Localidade'].dropna().unique()))
        localidades_disponiveis = ["Todas"] + igrejas_no_setor
    else:
        localidades_disponiveis = ["Todas"] + sorted(list(df['Localidade'].dropna().unique()))

    selected_localidade = st.sidebar.selectbox("Selecione a Igreja", localidades_disponiveis)
    
    # NOVO FILTRO DE ATIVIDADE
    if 'Livro' in df.columns:
        atividades_disponiveis = ["Todas"] + sorted(list(df['Livro'].dropna().unique()))
        selected_atividade = st.sidebar.selectbox("Selecione a Atividade", atividades_disponiveis)

# =========================================================
# 🚨 SEÇÃO DE ALERTAS E PENDÊNCIAS (EM BLOCO ÚNICO VERTICAL)
# =========================================================
st.header("🚨 Alertas e Pendências")

if df is not None:
    igrejas_cobradas = igrejas_cobradas_base.copy()
    if selected_setor != "Todos":
        igrejas_cobradas = [ig for ig in igrejas_cobradas if ig in SETORES[selected_setor]]
    if selected_localidade != "Todas":
        igrejas_cobradas = [selected_localidade] if selected_localidade in igrejas_cobradas else []

    igrejas_presentes_geral = df['Localidade'].dropna().unique().tolist()
    igrejas_sem_lancamento = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_presentes_geral]
    
    # 1. Tabela: Nenhuma atividade lançada
    st.subheader("❌ Nenhuma atividade lançada")
    if igrejas_sem_lancamento:
        df_sem_lanc = pd.DataFrame(igrejas_sem_lancamento, columns=["Igreja"])
        df_sem_lanc['Setor'] = df_sem_lanc['Igreja'].apply(classificar_setor)
        st.dataframe(df_sem_lanc[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
    else:
        st.success("Nenhuma pendência total de lançamento para a seleção atual!")

    st.markdown("---")
    
    # 2. Tabela: Atividades faltando
    st.subheader("⚠️ Atividades faltando")
    if 'Livro' in df.columns and 'Localidade' in df.columns:
        pendencias_atividades = []
        igrejas_para_avaliar_livro = [ig for ig in igrejas_cobradas if ig in igrejas_presentes_geral]
        
        for igreja in igrejas_para_avaliar_livro:
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
            st.success("Todas as atividades registradas para a seleção atual!")

    st.markdown("---")

    # Controles unificados de Data para as pendências abaixo
    st.subheader("🗓️ Filtros de Período para Pendências Mensais")
    col_mes_pend, col_ano_pend = st.columns([3, 2])
    with col_mes_pend:
        mes_selecionado_nome = st.selectbox("Mês de Referência:", list(meses_nomes.values()), index=mes_anterior - 1)
    with col_ano_pend:
        ano_selecionado = st.number_input("Ano de Referência:", min_value=2020, max_value=2100, value=ano_padrao, step=1)

    mes_selecionado_num = list(meses_nomes.keys())[list(meses_nomes.values()).index(mes_selecionado_nome)]
    
    st.markdown("---")
    
    # 3. Tabela: Formulário Qualitativo
    st.subheader("📋 Pendências Formulário Qualitativo")

    if df_form is not None:
        df_form_filtrado = df_form[
            (df_form['Mes_Submissao'] == mes_selecionado_num) & 
            (df_form['Ano_Submissao'] == ano_selecionado)
        ]
        igrejas_que_responderam = df_form_filtrado['Igreja_Identificada'].dropna().unique().tolist()
        faltam_form = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_que_responderam]
        
        if faltam_form:
            df_faltam_form = pd.DataFrame(faltam_form, columns=["Igreja"])
            df_faltam_form['Setor'] = df_faltam_form['Igreja'].apply(classificar_setor)
            st.warning(f"⚠️ {len(faltam_form)} pendências em {mes_selecionado_nome}.")
            st.dataframe(df_faltam_form[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ Formulários em dia ({mes_selecionado_nome})!")
    else:
        st.info("Arquivo de respostas não encontrado.")
        
    st.markdown("---")
    
    # 4. Tabela: Status do Fechamento Mensal
    st.subheader(f"📅 Status do Fechamento Mensal ({mes_selecionado_nome}/{ano_selecionado})")
    
    # Carrega o arquivo dinâmico
    df_fechamento_raw = load_fechamento_data(mes_selecionado_num, ano_selecionado)

    if df_fechamento_raw is not None:
        df_fechamento_raw['Setor'] = df_fechamento_raw['Igreja'].apply(classificar_setor)
    
        # Filtra o fechamento pelo Setor e Localidade do menu lateral
        if selected_setor != "Todos":
            df_fechamento_raw = df_fechamento_raw[df_fechamento_raw['Setor'] == selected_setor]
        if selected_localidade != "Todas":
            df_fechamento_raw = df_fechamento_raw[df_fechamento_raw['Igreja'] == selected_localidade]
            
        fechamentos_abertos = df_fechamento_raw[df_fechamento_raw['Status'] == 'Aberto']
    
        if not fechamentos_abertos.empty:
            st.warning(f"⚠️ {len(fechamentos_abertos)} igrejas com Fechamento Mensal ABERTO.")
            st.dataframe(fechamentos_abertos[['Setor', 'Igreja', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os fechamentos mensais estão encerrados para a seleção atual!")
            
        with st.expander("Ver todos os status de fechamento neste período"):
            st.dataframe(df_fechamento_raw[['Setor', 'Igreja', 'Status']], use_container_width=True, hide_index=True)
    else:
        mes_str_aviso = str(mes_selecionado_num).zfill(2)
        st.info(f"Arquivo 'FECHAMENTO MENSAL {mes_str_aviso}-{ano_selecionado}.txt' não encontrado no servidor.")

else:
    st.error("Base de dados 'tabela.xlsx' não encontrada.")

st.markdown("---")

# =========================================================
# 📌 CARTÕES DE MÉTRICAS E GRÁFICOS (Base Filtrada)
# =========================================================
if df is not None:
    # Aplica os filtros nos DADOS para as métricas e gráficos
    df_filtrado = df.copy()
    if selected_setor != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Setor'] == selected_setor]
    if selected_localidade != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Localidade'] == selected_localidade]
    if selected_atividade != "Todas" and 'Livro' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Livro'] == selected_atividade]


    st.subheader(f"📌 Métricas - {selected_setor if selected_localidade == 'Todas' else selected_localidade}")
    col1, col2, col3 = st.columns(3)

    total_registros = len(df_filtrado)
    total_valor = df_filtrado['Valor'].sum() if 'Valor' in df_filtrado.columns else 0
    media_valor = df_filtrado['Valor'].mean() if 'Valor' in df_filtrado.columns else 0

    col1.metric("Total de Registros", f"{total_registros}")
    col2.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col3.metric("Valor Médio (R$)", f"R$ {media_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    st.markdown("---")

    st.subheader("📈 Análises Gráficas")
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        if 'Localidade' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
            if selected_setor == "Todos" and selected_localidade == "Todas":
                df_grafico1 = df_filtrado.groupby('Setor')['Valor'].sum().reset_index()
                x_axis = 'Setor'
                titulo_graf = "Total (R$) por Setor"
            else:
                df_grafico1 = df_filtrado.groupby('Localidade')['Valor'].sum().reset_index()
                x_axis = 'Localidade'
                titulo_graf = f"Total (R$) nas Igrejas"

            if not df_grafico1.empty:
                fig_loc = px.bar(
                    df_grafico1, x=x_axis, y='Valor', title=titulo_graf,
                    text_auto='.2f', color=x_axis, color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_loc.update_layout(showlegend=False)
                st.plotly_chart(fig_loc, use_container_width=True)

    with g_col2:
        # Alterado de Função para Atividade (Livro)
        if 'Livro' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
            df_ativ = df_filtrado.groupby('Livro')['Valor'].sum().reset_index()
            df_ativ['Livro'] = df_ativ['Livro'].astype(str)
            if not df_ativ.empty:
                fig_ativ = px.pie(
                    df_ativ, names='Livro', values='Valor', 
                    title="Distribuição do Valor por Atividade", hole=0.4
                )
                st.plotly_chart(fig_ativ, use_container_width=True)
