import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="App Faturas", page_icon="🧾", layout="centered")

# --- FORÇAR ÍCONE NO CELULAR (Link Direto) ---
st.markdown("""
    <script>
        var logoUrl = "https://raw.githubusercontent.com/servicosmille-png/app-faturas-mille/main/logo_mille.png";
        var links = document.querySelectorAll("link[rel*='icon']");
        links.forEach(l => l.href = logoUrl);
        var appleIcon = document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = logoUrl;
        document.head.appendChild(appleIcon);
    </script>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O FIREBASE (NUVEM E LOCAL) ---
@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        if "firebase_json" in st.secrets:
            key_dict = json.loads(st.secrets["firebase_json"])
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = conectar_firebase()

# --- FUNÇÕES AUXILIARES ---
def formatar_data(data_str):
    if not data_str: return ""
    partes = data_str.split('-')
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_str

def calcular_dias_vencimento(data_vencimento):
    if not data_vencimento: return 999
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        ano, mes, dia = map(int, data_vencimento.split('-'))
        data_venc = datetime(ano, mes, dia)
        diff = (data_venc - hoje).days
        return diff
    except:
        return 999

def verificar_status(fat):
    status_banco = fat.get('status', 'Pendente')
    if status_banco in ['Cancelado', 'Pago']:
        return status_banco

    dias = calcular_dias_vencimento(fat.get('vencimento', ''))
    if dias < 0:
        return 'Atrasado'
    return 'Pendente'

def atualizar_status(doc_id, novo_status):
    db.collection("faturas").document(doc_id).update({"status": novo_status})
    st.toast(f"✅ Fatura marcada como {novo_status}!")

# --- BUSCAR DADOS ---
def buscar_faturas():
    faturas_ref = db.collection("faturas")
    docs = faturas_ref.stream()
    lista = []
    for doc in docs:
        fat = doc.to_dict()
        fat['id'] = doc.id
        fat['status_real'] = verificar_status(fat)
        lista.append(fat)
    lista.sort(key=lambda x: x.get('dataRegistro', ''), reverse=True)
    return lista

faturas = buscar_faturas()

# --- INTERFACE DO APLICATIVO ---
st.title("📱 Gestão de Faturas")
st.markdown("Mille Viagens e Turismo")

# 1. CAIXA DE ALERTAS
faturas_alerta = [f for f in faturas if f['status_real'] == 'Pendente' and 0 <= calcular_dias_vencimento(f.get('vencimento', '')) <= 2]

if faturas_alerta:
    st.warning("⚠️ **Atenção: Faturas vencendo em breve!**")
    for fat in faturas_alerta:
        dias = calcular_dias_vencimento(fat.get('vencimento', ''))
        texto_dias = "VENCE HOJE!" if dias == 0 else f"Vence em {dias} dia(s)"
        st.error(f"**#{fat.get('fatura')}** - {fat.get('cliente')} (R$ {fat.get('valor')})  \n👉 {texto_dias}")
    st.divider()

# 2. LISTA DE FATURAS
st.subheader("Faturas Pendentes / Atrasadas")

faturas_ativas = [f for f in faturas if f['status_real'] not in ['Pago', 'Cancelado']]

if not faturas_ativas:
    st.success("Tudo limpo! Nenhuma fatura pendente.")
else:
    for fat in faturas_ativas:
        with st.expander(f"#{fat.get('fatura')} - {fat.get('cliente')} (R$ {fat.get('valor')})"):
            st.write(f"**Vencimento:** {formatar_data(fat.get('vencimento', ''))}")
            st.write(f"**Status:** {fat['status_real']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💲 Marcar Pago", key=f"pago_{fat['id']}", use_container_width=True):
                    atualizar_status(fat['id'], 'Pago')
                    st.rerun()
            with col2:
                if st.button("❌ Cancelar", key=f"canc_{fat['id']}", use_container_width=True):
                    atualizar_status(fat['id'], 'Cancelado')
                    st.rerun()

st.divider()

# 3. HISTÓRICO DE PAGAS
with st.expander("Ver Histórico de Faturas Pagas"):
    faturas_pagas = [f for f in faturas if f['status_real'] == 'Pago']
    if not faturas_pagas:
        st.write("Nenhuma fatura paga ainda.")
    else:
        for fat in faturas_pagas:
            st.write(f"✅ **#{fat.get('fatura')}** - {fat.get('cliente')} (R$ {fat.get('valor')})")
