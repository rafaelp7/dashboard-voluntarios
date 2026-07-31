<!-- ... existing code ... -->
# Carregamento dos dados
df = load_data()
df_form = load_form_data()

# =========================================================
# 🔍 BARRA LATERAL: FILTROS GLOBAIS
# =========================================================
st.sidebar.header("🗓️ Período")
mes_selecionado_nome = st.sidebar.selectbox("Mês de Referência:", list(meses_nomes.values()), index=mes_anterior - 1)
ano_selecionado = st.sidebar.number_input("Ano de Referência:", min_value=2020, max_value=2100, value=ano_padrao, step=1)
mes_selecionado_num = list(meses_nomes.keys())[list(meses_nomes.values()).index(mes_selecionado_nome)]

st.sidebar.markdown("---")

# APLICA O FILTRO DE DATA GLOBALMENTE NO BANCO DE DADOS PRINCIPAL
if df is not None and 'Data' in df.columns:
    df = df[(df['Data'].dt.month == mes_selecionado_num) & (df['Data'].dt.year == ano_selecionado)]

st.sidebar.header("🔍 Filtros de Visualização")

selected_setor = "Todos"
selected_localidade = "Todas"
selected_atividade = "Todas"

if df is not None:
    setores_disponiveis = ["Todos"] + sorted(list(SETORES.keys()))
    selected_setor = st.sidebar.selectbox("Selecione o Setor", setores_disponiveis)
    
    # Prepara lista de igrejas dependendo do setor escolhido
    if selected_setor != "Todos":
        localidades_disponiveis = ["Todas"] + sorted(SETORES[selected_setor])
    else:
        localidades_disponiveis = ["Todas"] + sorted([igreja for lista in SETORES.values() for igreja in lista])

    selected_localidade = st.sidebar.selectbox("Selecione a Igreja", localidades_disponiveis)
    
    # NOVO FILTRO DE ATIVIDADE
    if 'Livro' in df.columns:
        atividades_disponiveis = ["Todas"] + sorted(list(df['Livro'].dropna().unique()))
        selected_atividade = st.sidebar.selectbox("Selecione a Atividade", atividades_disponiveis)

# =========================================================
# 🚨 SEÇÃO DE ALERTAS E PENDÊNCIAS (EM BLOCO ÚNICO VERTICAL)
# =========================================================
st.header("🚨 Alertas e Pendências")
<!-- ... existing code ... -->
```

### 2ª Alteração: Remover os filtros de Data que ficavam no meio da tela
Agora que a data foi para a barra lateral, precisamos apagar as caixinhas de data antigas que ficavam antes do painel do Formulário Qualitativo, e ajustar o gráfico para que ele não tente filtrar a data novamente.

Localize o meio do seu código (por volta da linha 213) e substitua:

```python:Dashboard Atualizado:app.py
<!-- ... existing code ... -->
        if pendencias_atividades:
            df_pend_ativ = pd.DataFrame(pendencias_atividades)
            st.dataframe(df_pend_ativ, use_container_width=True, hide_index=True)
        else:
            st.success("Todas as atividades registradas para a seleção atual!")

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

        # --- NOVO GRÁFICO DE QUALIDADE ---
        st.subheader("📊 Análise de Qualidade (Taxa de Erros por Atividade)")
        
        # Prepara base da tabela principal (df) filtrada pela competência, setor e igreja
        df_base_grafico = df.copy()
        if selected_setor != "Todos":
            df_base_grafico = df_base_grafico[df_base_grafico['Setor'] == selected_setor]
        if selected_localidade != "Todas":
            df_base_grafico = df_base_grafico[df_base_grafico['Localidade'] == selected_localidade]
            
        # Prepara base do formulário filtrada por setor e igreja
        df_form_grafico = df_form_filtrado.copy()
<!-- ... existing code ... -->
```

Feito isso, faça o **Commit changes** no GitHub.
A partir de agora, o painel abrirá por padrão exibindo **apenas os lançamentos e as pendências do mês de Junho**. Se alguém quiser auditar meses passados (ou o mês atual), basta trocar no menu esquerdo superior!
