import streamlit as st
import os
from config import db 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal de Acceso", layout="wide", page_icon="🔒")

# --- GESTIÓN DE SESIÓN ---
if 'password_correct' not in st.session_state:
    st.session_state.password_correct = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'empresa_id' not in st.session_state:
    st.session_state.empresa_id = None

# --- DETECTAR SI HAY UN LINK MÁGICO (?cliente=facha_shila) ---
# Esto permite que si entran con el link especial, el campo se llene solo
query_params = st.query_params
empresa_url = query_params.get("cliente", None)

# --- PANTALLA DE LOGIN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Ingreso al Sistema")
        st.caption("Introduce tus credenciales.")
        
        with st.form("login_form"):
            # 1. CÓDIGO DE EMPRESA (Ahora es Texto, no Lista)
            if empresa_url:
                # Si viene del link, lo mostramos bloqueado (más pro)
                empresa_input = st.text_input("🏢 Código de Empresa", value=empresa_url, disabled=True)
                st.caption("🔒 Empresa detectada automáticamente por el enlace.")
            else:
                # Si entra directo, tiene que escribirlo
                empresa_input = st.text_input("🏢 Código de Empresa (ID)", placeholder="Ej: facha_shila")
            
            st.divider()
            
            # 2. CREDENCIALES
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                # Validaciones
                if not empresa_input or not usuario or not password:
                    st.warning("⚠️ Por favor completa todos los campos.")
                    return

                # Normalizamos el ID (minusculas, sin espacios extra)
                empresa_id_clean = empresa_input.lower().strip()
                
                # Verificar si la carpeta existe (Si el cliente es real)
                path_cliente = os.path.join("instancias_clientes", empresa_id_clean)
                
                if not os.path.exists(path_cliente):
                    # SEGURIDAD: Mensaje genérico para no dar pistas
                    st.error("❌ Error: Empresa o usuario incorrecto.") 
                    return

                # --- VALIDACIÓN EN BASE DE DATOS ---
                collection_name = f"{empresa_id_clean}_usuarios"
                doc_ref = db.collection(collection_name).document(usuario)
                doc = doc_ref.get()

                if doc.exists:
                    data = doc.to_dict()
                    
                    if not data.get('activo', True):
                        st.error("🚫 Cuenta deshabilitada.")
                        return

                    if data.get('pass') == password:
                        st.session_state.password_correct = True
                        st.session_state.usuario = usuario
                        st.session_state.rol = data.get('rol', 'vendedor')
                        st.session_state.empresa_id = empresa_id_clean
                        st.rerun()
                    else:
                        st.error("❌ Credenciales inválidas.")
                else:
                    st.error("❌ Credenciales inválidas.")

# --- LOGOUT ---
def logout():
    st.session_state.password_correct = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.empresa_id = None
    st.rerun()

# --- NAVEGACIÓN ---
if not st.session_state.password_correct:
    pg = st.navigation([st.Page(login_screen, title="Acceso")])
    pg.run()
else:
    # --- CARGAR SISTEMA DEL CLIENTE ---
    empresa_actual = st.session_state.empresa_id
    path_cliente = os.path.join("instancias_clientes", empresa_actual)
    
    paginas = []
    
    if os.path.exists(path_cliente):
        archivos = [f for f in os.listdir(path_cliente) if f.endswith(".py") and "__" not in f]
        for archivo in archivos:
            ruta = os.path.join(path_cliente, archivo)
            nombre = archivo.replace(".py", "").replace("_", " ").title()
            paginas.append(st.Page(ruta, title=nombre))
        paginas.sort(key=lambda x: x.title)
    
    if paginas:
        pg = st.navigation(paginas)
        with st.sidebar:
            st.subheader(f"🏢 {empresa_actual.replace('_', ' ').title()}")
            st.divider()
            st.write(f"👤 **{st.session_state.usuario}**")
            if st.button("Salir", type="primary", use_container_width=True):
                logout()
        pg.run()
    else:
        st.error("No se encontraron módulos.")
