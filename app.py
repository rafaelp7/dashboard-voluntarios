import streamlit as st
import pandas as pd
import plotly.express as px
import os

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

# Função auxiliar para classificar a localidade
def classificar_setor(localidade):
    for setor, locais in SETORES.items():
        if localidade in locais:
            return setor
    return 'Não Classificado'

# Função para carregar os dados locais
@st.cache_data
def load_data():
    # O arquivo deve se chamar exatamente 'tabela.xlsx' e estar na mesma pasta no GitHub
    try:
        df = pd.read_excel('tabela.xlsx')
    except FileNotFoundError:
        return None
    
    col_mapping = {
        'Localida': 'Localidade',
        'Voluntá': 'Voluntario',
        'Data Na': 'Data Nasc',
        'H. Des': 'Horas Desconto'
    }
    df = df.rename(columns=lambda x: col_mapping.get(x.strip(), x.strip()))

    if 'Valor' in df.columns:
        if df['Valor'].dtype == object:
            df['Valor'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
            
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)

    # Cria a nova coluna de 'Setor' aplicando a função de classificação
    if 'Localidade' in df.columns:
        df['Setor'] = df['Localidade'].apply(classificar_setor)

    return df

# Tenta carregar a base fixa
df = load_data()

if df is not None:
    # --- BARRA LATERAL: FILTROS HIERÁRQUICOS ---
    st.sidebar.header("🔍 Filtros")

    # 1. Filtro de Setor
    setores_disponiveis = ["Todos"] + sorted(list(df['Setor'].unique()))
    selected_setor = st.sidebar.selectbox("Selecione o Setor", setores_disponiveis)
    
    if selected_setor != "Todos":
        df = df[df['Setor'] == selected_setor]

    # 2. Filtro de Igreja (Localidade) - Depende do setor escolhido
    if 'Localidade' in df.columns:
        localidades_disponiveis = ["Todas"] + sorted(list(df['Localidade'].dropna().unique()))
        selected_localidade = st.sidebar.selectbox("Selecione a Igreja", localidades_disponiveis)
        if selected_localidade != "Todas":
            df = df[df['Localidade'] == selected_localidade]

    # 3. Filtro de Função
    if 'Função' in df.columns:
        funcoes = ["Todas"] + list(df['Função'].dropna().unique())
        selected_funcao = st.sidebar.selectbox("Função", funcoes)
        if selected_funcao != "Todas":
            df = df[df['Função'] == selected_funcao]

    # --- CARTÕES DE MÉTRICAS (KPIs) ---
    st.subheader("📌 Métricas Gerais")
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

    # --- GRÁFICOS INTERATIVOS ---
    st.subheader("📈 Análises Gráficas")
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        if 'Localidade' in df.columns and 'Valor' in df.columns:
            # Se o usuário escolheu um setor específico, mostra as igrejas daquele setor. 
            # Se não, mostra o total por setor.
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

    # --- TABELA DE DADOS ---
    st.subheader("📄 Tabela de Dados Filtrados")
    df_display = df.copy()
    if 'Data' in df_display.columns:
        df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
    
    # Reordenando colunas para mostrar Setor logo no início
    cols = df_display.columns.tolist()
    if 'Setor' in cols:
        cols.insert(0, cols.pop(cols.index('Setor')))
        df_display = df_display[cols]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.error("⚠️ Base de dados não encontrada. Certifique-se de que o arquivo 'tabela.xlsx' foi enviado para o repositório.")
