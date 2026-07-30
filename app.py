import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Voluntários & Horas",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Painel de Controle - Atividades e Voluntários")
st.markdown("---")


# Função para carregar e tratar os dados
@st.cache_data
def load_data(file):
    df = pd.read_excel(file)

    # Padronização de nomes de colunas
    col_mapping = {
        'Localida': 'Localidade',
        'Voluntá': 'Voluntario',
        'Data Na': 'Data Nasc',
        'H. Des': 'Horas Desconto'
    }
    df = df.rename(columns=lambda x: col_mapping.get(x.strip(), x.strip()))

    # Tratamento da coluna Valor (formatação numéricas)
    if 'Valor' in df.columns:
        if df['Valor'].dtype == object:
            df['Valor'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)

    # Conversão de datas
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)

    return df


# Upload da planilha na barra lateral
uploaded_file = st.sidebar.file_uploader("📂 Faça upload da sua planilha (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)

    # --- FILTROS LATERAIS ---
    st.sidebar.header("🔍 Filtros")

    if 'Localidade' in df.columns:
        localidades = ["Todas"] + list(df['Localidade'].dropna().unique())
        selected_localidade = st.sidebar.selectbox("Localidade", localidades)
        if selected_localidade != "Todas":
            df = df[df['Localidade'] == selected_localidade]

    if 'Função' in df.columns:
        funcoes = ["Todas"] + list(df['Função'].dropna().unique())
        selected_funcao = st.sidebar.selectbox("Função", funcoes)
        if selected_funcao != "Todas":
            df = df[df['Função'] == selected_funcao]

    if 'Voluntario' in df.columns:
        voluntarios = ["Todos"] + list(df['Voluntario'].dropna().unique())
        selected_voluntario = st.sidebar.selectbox("Voluntário", voluntarios)
        if selected_voluntario != "Todos":
            df = df[df['Voluntario'] == selected_voluntario]

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
            df_loc = df.groupby('Localidade')['Valor'].sum().reset_index()
            fig_loc = px.bar(
                df_loc,
                x='Localidade',
                y='Valor',
                title="Total (R$) por Localidade",
                text_auto='.2f',
                color='Localidade',
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_loc.update_layout(showlegend=False)
            st.plotly_chart(fig_loc, use_container_width=True)

    with g_col2:
        if 'Função' in df.columns and 'Valor' in df.columns:
            df_fun = df.groupby('Função')['Valor'].sum().reset_index()
            df_fun['Função'] = df_fun['Função'].astype(str)
            fig_fun = px.pie(
                df_fun,
                names='Função',
                values='Valor',
                title="Distribuição do Valor por Função",
                hole=0.4
            )
            st.plotly_chart(fig_fun, use_container_width=True)

    st.markdown("---")

    # --- TABELA DE DADOS ---
    st.subheader("📄 Tabela Completa de Dados")

    df_display = df.copy()
    if 'Data' in df_display.columns:
        df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Exportação de dados
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar dados filtrados em CSV",
        data=csv,
        file_name="dados_filtrados.csv",
        mime="text/csv"
    )

else:
    st.info("👈 Por favor, faça o upload de um arquivo Excel (.xlsx) na barra lateral para carregar o painel.")