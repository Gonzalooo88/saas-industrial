import streamlit as st
import time as tm
import os
import sys

st.set_page_config(page_title="Acceso SaaS", page_icon="🔐", layout="centered")

try:
    from config import db
except ImportError:
    st.error("❌ Falta config.py")
    st.stop()

# --- SESIÓN ---
if 'logueado' not in st.session_state: st.session_state.logueado = False
if 'usuario' not in st.session_state: st.session_state.usuario = ""
if 'rol' not in st.session_state: st.session_state.rol = ""
if 'carpeta_cliente' not in st.session_state: st.session_state.carpeta_cliente = ""

# --- DICCIONARIO VISUAL ---
INFO_MODULOS = {
    "0_inicio.py":      {"titulo": "Inicio",       "icon": "🏠"},
    "1_ventas.py":      {"titulo": "Ventas",       "icon": "🛒"},
    "2_stock.py":       {"titulo": "Stock",        "icon": "📦"},
    "3_movimientos.py": {"titulo": "Movimientos",  "icon": "💵"},
    "4_admin.py":       {"titulo": "Admin",        "icon": "⚙️"},
}

query_params = st.query_params
empresa_param = query_params.get("empresa", None)

# --- LOGIN ---
def login():
    st.title("🔐 Login")
    if empresa_param: st.info(f"Portal: **{empresa_param.upper().replace('_', ' ')}**")
    
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Pass", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            # 1. Buscar usuario global
            res = list(db.collection('saas_usuarios_global').where('usuario', '==', u).where('password', '==', p).stream())
            
            if not res:
                st.error("Datos incorrectos.")
                return
            
            data = res[0].to_dict()
            carpeta = data.get('carpeta_instancia')
            
            # --- VALIDACIONES DE SEGURIDAD ---

            # 1. Validar Link de Invitación
            if empresa_param and carpeta != empresa_param:
                st.error("Usuario no autorizado en este portal.")
                return
            
            # 2. Validar Estado del Usuario (Toggle Individual)
            if not data.get('activo', True):
                st.error("⛔ Usuario inactivo. Contacte a su administrador.")
                return

            # 3. Validar Estado de la Empresa (Toggle General del Super Admin) [NUEVO]
            doc_empresa = db.collection('instancias').document(carpeta).get()
            
            if doc_empresa.exists:
                empresa_data = doc_empresa.to_dict()
                if not empresa_data.get('activo', True):
                    st.error("⛔ La empresa ha sido deshabilitada temporalmente. Contacte soporte.")
                    return
            else:
                st.error("⚠️ Error crítico: La empresa asignada no existe en base de datos.")
                return

            # 4. Validar que la carpeta exista físicamente
            ruta = f"instancias_clientes/{carpeta}"
            if not os.path.isdir(ruta):
                st.error(f"⚠️ Error Crítico: No se encuentra el software para '{carpeta}'. Contacte soporte.")
                return

            # --- LOGIN EXITOSO ---
            st.session_state.logueado = True
            st.session_state.usuario = data['usuario']
            st.session_state.rol = data['rol']
            st.session_state.carpeta_cliente = carpeta
            st.rerun()

def logout():
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

# --- NAVIGATOR ---
if not st.session_state.logueado:
    login()
else:
    with st.sidebar:
        st.write(f"👤 {st.session_state.usuario}")
        st.caption(f"Cliente: {st.session_state.carpeta_cliente}")
        st.divider()
        if st.button("Salir"): logout()

    # --- LÓGICA DE DETECCIÓN DE ARCHIVOS ---
    ruta_cliente = f"instancias_clientes/{st.session_state.carpeta_cliente}"
    
    # Listar archivos .py ignorando los que empiezan con _
    if os.path.exists(ruta_cliente):
        archivos = [f for f in os.listdir(ruta_cliente) if f.endswith(".py") and not f.startswith("_")]
        archivos.sort()
    else:
        archivos = []
    
    paginas = []
    for arch in archivos:
        # Detectamos nombre bonito e icono usando el diccionario
        info = INFO_MODULOS.get(arch, {"titulo": arch.replace(".py","").title(), "icon": "📄"})
        paginas.append(st.Page(f"{ruta_cliente}/{arch}", title=info['titulo'], icon=info['icon']))
    
    if not paginas:
        st.warning("⚠️ Esta empresa aún no tiene módulos cargados.")
    else:
        pg = st.navigation(paginas)
        try:
            pg.run()
        except Exception as e:
            st.error(f"Error en módulo: {e}")