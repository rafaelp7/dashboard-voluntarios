import streamlit as st
import pandas as pd
from datetime import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Dashboard de Voluntários", layout="wide")

# --- CONEXÃO COM O GOOGLE DRIVE (SERVICE ACCOUNT) ---
@st.cache_resource
def get_drive_service():
    try:
        # Carrega o JSON com as credenciais do robô (Service Account)
        creds_json = st.secrets["GCP_CREDENTIALS"]
        creds_dict = json.loads(creds_json)
        
        # Autenticação profissional
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, 
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        st.warning("⚠️ Credenciais do Google Drive (GCP_CREDENTIALS) não configuradas ou incorretas nos Secrets.")
        return None

# --- FUNÇÃO PARA VASCULHAR O DRIVE ---
@st.cache_data(ttl=3600)
def fetch_google_drive_data(mes_ano, pasta_raiz_id="1vIBw5h1iuqGyRXBCrKl9kZORfVJzLlQ5"):
    service = get_drive_service()
    if not service:
        return {}
    
    arquivos_encontrados = {}
    
    try:
        # 1. Busca a pasta do Mês/Ano (ex: 06-2026)
        query_mes = f"name = '{mes_ano}' and '{pasta_raiz_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results_mes = service.files().list(q=query_mes, fields="files(id, name)").execute()
        pastas_mes = results_mes.get('files', [])
        
        if not pastas_mes:
            return {}
        
        pasta_mes_id = pastas_mes[0]['id']
        
        # 2. Busca os Setores dentro do Mês
        query_setores = f"'{pasta_mes_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results_setores = service.files().list(q=query_setores, fields="files(id, name)").execute()
        
        for setor in results_setores.get('files', []):
            # 3. Busca as Igrejas dentro de cada Setor
            query_igrejas = f"'{setor['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results_igrejas = service.files().list(q=query_igrejas, fields="files(id, name)").execute()
            
            for igreja in results_igrejas.get('files', []):
                # 4. Busca os PDFs/Arquivos dentro da Igreja
                query_arquivos = f"'{igreja['id']}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
                results_arquivos = service.files().list(q=query_arquivos, fields="files(name)").execute()
                
                lista_arquivos = [arq['name'].upper() for arq in results_arquivos.get('files', [])]
                
                # Extrai apenas o código da igreja (ex: "BR 14-0603") para garantir o cruzamento exato
                codigo_igreja = igreja['name'].split(' - ')[0].strip()
                arquivos_encontrados[codigo_igreja] = lista_arquivos
                
    except Exception as e:
        st.error(f"Erro ao acessar o Drive: {e}")
        
    return arquivos_encontrados

# --- FUNÇÃO PARA CARREGAR DADOS LOCAIS ---
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

    if 'Valor' in df.columns and df['Valor'].dtype == object:
        df['Valor'] = df['Valor'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
            
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)

    if 'Localidade' in df.columns:
        df['Setor'] = df['Localidade'].apply(classificar_setor)
        
    return df

def classificar_setor(localidade):
    localidade_upper = str(localidade).upper()
    setor1 = ["MARINGÁ VELHO", "JARDIM ESPANHA", "DISTRITO DE FLORIANO", "VILA OPERÁRIA", "VILA MORANGUEIRA", "JARDIM VITÓRIA", "JARDIM VERÔNICA", "PARQUE ITAIPU", "AEROPORTO", "JARDIM CATEDRAL", "JARDIM UNIVERSO", "JARDIM ORIENTAL"]
    setor2 = ["CÂNDIDO DE ABREU", "CASTELO BRANCO", "COLORADO", "FLORESTA", "ITAMBÉ", "MANDAGUAÇU", "NOVA ESPERANÇA", "SANTA FÉ", "SÃO JORGE DO IVAÍ", "ASTORGA", "DOUTOR CAMARGO", "MUNHOZ DE MELO"]
    setor3 = ["CAMPO MOURÃO", "CIANORTE", "TERRA BOA", "UBIRATÃ", "PEABIRU", "ENGENHEIRO BELTRÃO", "ARARUNA", "TAPEJARA", "JUSSARA"]
    
    if any(igreja in localidade_upper for igreja in setor1): return "Setor 1"
    if any(igreja in localidade_upper for igreja in setor2): return "Setor 2"
    if any(igreja in localidade_upper for igreja in setor3): return "Setor 3"
    return "Não Classificado"

# --- INTERFACE PRINCIPAL (CABEÇALHO E FILTROS) ---
st.title("📊 Painel de Controle - Voluntários")

with st.container():
    st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
    st.subheader("📅 Período de Análise")
    col_data1, col_data2, col_data3 = st.columns(3)
    with col_data1:
        selected_mes = st.selectbox("Selecione o Mês", ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"], index=5)
    with col_data2:
        selected_ano = st.selectbox("Selecione o Ano", ["2025", "2026", "2027", "2028"], index=1)
    st.markdown('</div>', unsafe_allow_html=True)

df = load_data(selected_mes, selected_ano)

if df is not None:
    # --- ANÁLISE DE PENDÊNCIAS (SIGA VS DRIVE) ---
    st.subheader("⚠️ Controle de Atividades e Anexos (PDFs)")
    
    atividades_obrigatorias = ["LIMPEZA", "GEM", "PÁTIO"]
    atividades_esporadicas = ["MANUTENÇÃO PREVENTIVA", "ESPAÇO INFANTIL", "COZINHA"]
    
    # 1. Mapear o que foi lançado no SIGA
    siga_lancamentos = df.groupby(['Setor', 'Localidade'])['Atividade'].unique().reset_index()
    
    # 2. Buscar no Drive
    arquivos_drive = fetch_google_drive_data(f"{selected_mes}-{selected_ano}")
    
    pendencias_siga = []
    pendencias_drive = []
    
    for index, row in siga_lancamentos.iterrows():
        setor = row['Setor']
        igreja_completa = row['Localidade']
        codigo_igreja = str(igreja_completa).split(' - ')[0].strip()
        atividades_lancadas = [str(a).upper() for a in row['Atividade']]
        
        arquivos_desta_igreja = arquivos_drive.get(codigo_igreja, [])
        
        # A) Verifica Falta no SIGA (Apenas Limpeza, GEM, Pátio)
        falta_siga = []
        for atv in atividades_obrigatorias:
            if not any(atv in lancado for lancado in atividades_lancadas):
                falta_siga.append(atv)
                
        # Esporádicas: Se não está no SIGA, olha no Drive. Se também não está no Drive, cobra.
        for atv_esp in atividades_esporadicas:
            if not any(atv_esp in lancado for lancado in atividades_lancadas):
                if atv_esp == "MANUTENÇÃO PREVENTIVA" and not any('MAN' in arq for arq in arquivos_desta_igreja):
                    falta_siga.append(atv_esp)
                elif atv_esp == "ESPAÇO INFANTIL" and not any(x in arq for arq in arquivos_desta_igreja for x in ['INFA', 'EBI', 'E.B.I']):
                    falta_siga.append(atv_esp)
                elif atv_esp == "COZINHA" and not any('COZINHA' in arq for arq in arquivos_desta_igreja):
                    falta_siga.append(atv_esp)

        if falta_siga:
            pendencias_siga.append({'Setor': setor, 'Igreja': igreja_completa, 'Falta Lançar no Sistema': ", ".join(falta_siga)})

        # B) Verifica Falta de PDF (Apenas para o que FOI lançado no SIGA)
        falta_drive = []
        for lancado in atividades_lancadas:
            encontrou = False
            if 'ESTAC' in lancado or 'PÁTIO' in lancado or 'PATIO' in lancado:
                encontrou = any(('ESTAC' in arq or 'PÁTIO' in arq or 'PATIO' in arq) and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            elif 'GEM' in lancado or 'G.E.M' in lancado:
                encontrou = any(('GEM' in arq or 'G.E.M' in arq) and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            elif 'MPEZA' in lancado or 'MPESA' in lancado:
                encontrou = any(('MPEZA' in arq or 'MPESA' in arq) and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            elif 'COZINHA' in lancado:
                encontrou = any('COZINHA' in arq and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            elif 'INFA' in lancado or 'EBI' in lancado or 'E.B.I' in lancado:
                encontrou = any(('INFA' in arq or 'EBI' in arq or 'E.B.I' in arq) and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            elif 'MAN' in lancado:
                encontrou = any('MAN' in arq and 'OCORRENC' not in arq and 'RELAT' not in arq for arq in arquivos_desta_igreja)
            else:
                encontrou = True # Atividades não rastreadas não cobram anexo

            if not encontrou and lancado in atividades_obrigatorias + atividades_esporadicas:
                falta_drive.append(lancado)

        if falta_drive:
            pendencias_drive.append({'Setor': setor, 'Igreja': igreja_completa, 'Falta Anexar PDF no Drive': ", ".join(falta_drive)})

    # EXIBIÇÃO EM SANFONA (EXPANDERS)
    with st.expander(f"⚠️ {len(pendencias_siga)} congregações com pendências no Sistema (SIGA)"):
        if pendencias_siga:
            st.dataframe(pd.DataFrame(pendencias_siga), use_container_width=True, hide_index=True)
        else:
            st.success("Tudo certo! Todas as igrejas lançaram as atividades obrigatórias.")

    with st.expander(f"📁 {len(pendencias_drive)} congregações com pendências de anexo no fechamento mensal"):
        if pendencias_drive:
            st.dataframe(pd.DataFrame(pendencias_drive), use_container_width=True, hide_index=True)
        else:
            st.success("Todos os lançamentos possuem arquivo correspondente no Google Drive!")

    # --- AUDITORIA DE ARQUIVOS (DRIVE) ---
    st.markdown("---")
    with st.expander("🔍 Auditoria de Arquivos (Ver todos os arquivos lidos no Google Drive)"):
        st.info("O painel salva os arquivos na memória por 1 hora. Se você apagou ou enviou um arquivo no Drive AGORA, clique no botão abaixo para forçar a atualização imediata.")
        if st.button("🔄 Forçar Atualização do Drive"):
            fetch_google_drive_data.clear()
            st.rerun()
            
        if arquivos_drive:
            auditoria_list = []
            for ig, arqs in arquivos_drive.items():
                auditoria_list.append({"Código Igreja": ig, "Arquivos Encontrados": ", ".join(arqs) if arqs else "Pasta Vazia"})
            st.dataframe(pd.DataFrame(auditoria_list), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum arquivo encontrado. O Mês/Ano pode estar sem pastas no Drive ou as credenciais não foram carregadas.")

else:
    st.error(f"⚠️ Base de dados não encontrada: 'tabela {selected_mes}-{selected_ano}.xlsx'.")
