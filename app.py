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

# Lista unificada de todas as igrejas esperadas
todas_igrejas = [igreja for lista in SETORES.values() for igreja in lista]
igrejas_cobradas = [igreja for igreja in todas_igrejas if igreja not in IGREJAS_IGNORADAS]

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
        
        # 1. Encontrar coluna de data de submissão
        date_col = None
        for col in df_form.columns:
            # Procura palavras-chave comuns de formulário
            if any(word in str(col).lower() for word in ['data', 'carimbo', 'timestamp', 'hora']):
                date_col = col
                break
        
        if not date_col:
            date_col = df_form.columns[0] # Assume a primeira se não achar nome óbvio
            
        df_form['Data_Submissao'] = pd.to_datetime(df_form[date_col], errors='coerce')
        df_form['Mes_Submissao'] = df_form['Data_Submissao'].dt.month
        
        # 2. Encontrar qual coluna tem o nome da Igreja e padronizar
        def normalizar_igreja(valor):
            if pd.isna(valor): return None
            val_limpo = str(valor).strip().upper()
            for ig_oficial in todas_igrejas:
                if ig_oficial.upper() in val_limpo or val_limpo in ig_oficial.upper():
                    return ig_oficial
            return val_limpo

        church_col = None
        for col in df_form.columns:
            if df_form[col].dtype == object:
                amostra = df_form[col].dropna().astype(str).str.upper().tolist()
                # Se pelo menos uma das nossas igrejas aparecer nesta coluna, achamos ela!
                if any(ig.upper() in amostra_str for ig in todas_igrejas for amostra_str in amostra):
                    church_col = col
                    break
                    
        if church_col:
            df_form['Igreja_Identificada'] = df_form[church_col].apply(normalizar_igreja)
        else:
            df_form['Igreja_Identificada'] = 'Não identificada'
            
        return df_form
    except FileNotFoundError:
        return None

df = load_data()
df_form = load_form_data()

# =========================================================
# 🚨 SEÇÃO DE ALERTAS E PENDÊNCIAS GERAIS
# =========================================================
st.header("🚨 Alertas e Pendências (Tabela Base)")

if df is not None:
    igrejas_presentes = df['Localidade'].dropna().unique().tolist() if 'Localidade' in df.columns else []
    
    # 1. Identificar quem não lançou nada (ignorando exceções)
    igrejas_sem_lancamento = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_presentes]
    
    alerta_col1, alerta_col2 = st.columns(2)
    
    with alerta_col1:
        st.subheader("❌ Nenhuma atividade lançada")
        if igrejas_sem_lancamento:
            df_sem_lanc = pd.DataFrame(igrejas_sem_lancamento, columns=["Igreja"])
            df_sem_lanc['Setor'] = df_sem_lanc['Igreja'].apply(classificar_setor)
            st.dataframe(df_sem_lanc[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
        else:
            st.success("Todas as igrejas exigidas possuem ao menos um lançamento!")

    # 2. Identificar atividades faltando (ignorando exceções)
    with alerta_col2:
        st.subheader("⚠️ Atividades faltando")
        if 'Livro' in df.columns and 'Localidade' in df.columns:
            pendencias_atividades = []
            
            for igreja in igrejas_presentes:
                if igreja in IGREJAS_IGNORADAS:
                    continue # Pula as exceções
                    
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
                st.success("Todas as igrejas exigidas registraram todas as atividades obrigatórias!")
else:
    st.error("Base de dados 'tabela.xlsx' não encontrada.")

st.markdown("---")

# =========================================================
# 📋 CONTROLE DO FORMULÁRIO QUALITATIVO
# =========================================================
st.header("📋 Controle do Formulário Qualitativo")

meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 
               7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

hoje = datetime.date.today()
mes_atual = hoje.month
# Define o mês anterior (Se for janeiro, volta para dezembro do ano anterior)
mes_anterior = 12 if mes_atual == 1 else mes_atual - 1

col_mes, _ = st.columns([1, 3])
with col_mes:
    mes_selecionado_nome = st.selectbox(
        "Mês de envio do formulário:", 
        list(meses_nomes.values()), 
        index=mes_anterior - 1 # Ajuste de índice pois a lista começa em 0
    )

# Descobre o número do mês com base no nome selecionado
mes_selecionado_num = list(meses_nomes.keys())[list(meses_nomes.values()).index(mes_selecionado_nome)]

if df_form is not None:
    # Filtra os envios apenas para o mês escolhido na tela
    df_form_filtrado = df_form[df_form['Mes_Submissao'] == mes_selecionado_num]
    
    igrejas_que_responderam = df_form_filtrado['Igreja_Identificada'].dropna().unique().tolist()
    
    # Verifica quem da lista de cobrança não está nas respostas
    faltam_form = [igreja for igreja in igrejas_cobradas if igreja not in igrejas_que_responderam]
    
    if faltam_form:
        df_faltam_form = pd.DataFrame(faltam_form, columns=["Igreja"])
        df_faltam_form['Setor'] = df_faltam_form['Igreja'].apply(classificar_setor)
        
        st.warning(f"⚠️ {len(faltam_form)} igrejas não preencheram o formulário no mês de {mes_selecionado_nome}.")
        st.dataframe(df_faltam_form[['Setor', 'Igreja']], use_container_width=True, hide_index=True)
    else:
        st.success(f"✅ Todas as igrejas exigidas preencheram o formulário em {mes_selecionado_nome}!")
else:
    st.info("Arquivo 'FORMULÁRIO QUALITATIVO 2026 (respostas).xlsx' não encontrado no repositório. Faça o upload no GitHub para ativar esta verificação.")

st.markdown("---")

# =========================================================
# 🔍 BARRA LATERAL E KPIs
# =========================================================
if df is not None:
    st.sidebar.header("🔍 Filtros de Visualização")

    setores_disponiveis = ["Todos"] + sorted(list(df['Setor'].unique()))
    selected_setor = st.sidebar.selectbox("Selecione o Setor", setores_disponiveis)
    
    if selected_setor != "Todos":
        df = df[df['Setor'] == selected_setor]

    if 'Localidade' in df.columns:
        localidades_disponiveis = ["Todas"] + sorted(list(df['Localidade'].dropna().unique()))
        selected_localidade = st.sidebar.selectbox("Selecione a Igreja", localidades_disponiveis)
        if selected_localidade != "Todas":
            df = df[df['Localidade'] == selected_localidade]

    if 'Função' in df.columns:
        funcoes = ["Todas"] + list(df['Função'].dropna().unique())
        selected_funcao = st.sidebar.selectbox("Função", funcoes)
        if selected_funcao != "Todas":
            df = df[df['Função'] == selected_funcao]


    st.subheader("📌 Métricas Gerais (Filtradas)")
    col1, col2, col3, col4 = st.columns(4)

    total_registros = len(df)
    total_voluntarios = df['Voluntario'].nunique() if 'Voluntario' in df.columns else 0
    total_valor = df['Valor'].sum() if 'Valor' in df.columns else 0
    media_valor = df['Valor'].mean() if 'Valor' in df.columns else 0

    col1.metric("Total de Registros", f"{total_registros}")
    col2.metric("Voluntários Ativos", f"{total_voluntarios}")
    col3.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col4.metric("Valor Médio (R$)", f"R$ {media_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    st.markdown("---")

    st.subheader("📈 Análises Gráficas")
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        if 'Localidade' in df.columns and 'Valor' in df.columns:
            if selected_setor == "Todos":
                df_grafico1 = df.groupby('Setor')['Valor'].sum().reset_index()
                x_axis = 'Setor'
                titulo_graf = "Total (R$) por Setor"
            else:
                df_grafico1 = df.groupby('Localidade')['Valor'].sum().reset_index()
                x_axis = 'Localidade'
                titulo_graf = f"Total (R$) nas Igrejas do {selected_setor}"

            fig_loc = px.bar(
                df_grafico1, x=x_axis, y='Valor', title=titulo_graf,
                text_auto='.2f', color=x_axis, color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_loc.update_layout(showlegend=False)
            st.plotly_chart(fig_loc, use_container_width=True)

    with g_col2:
        if 'Função' in df.columns and 'Valor' in df.columns:
            df_fun = df.groupby('Função')['Valor'].sum().reset_index()
            df_fun['Função'] = df_fun['Função'].astype(str)
            fig_fun = px.pie(
                df_fun, names='Função', values='Valor', 
                title="Distribuição do Valor por Função", hole=0.4
            )
            st.plotly_chart(fig_fun, use_container_width=True)

    st.markdown("---")

    st.subheader("📄 Tabela de Dados Filtrados")
    df_display = df.copy()
    if 'Data' in df_display.columns:
        df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
    
    cols = df_display.columns.tolist()
    if 'Setor' in cols:
        cols.insert(0, cols.pop(cols.index('Setor')))
        df_display = df_display[cols]

    st.dataframe(df_display, use_container_width=True, hide_index=True)
