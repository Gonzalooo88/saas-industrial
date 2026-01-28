import streamlit as st
import os
from config import db # <--- Conexión centralizada

# --- SETUP ---
st.set_page_config(page_title="SaaS Industrial", layout="wide")

# --- GESTIÓN DE SESIÓN ---
if 'user_session' not in st.session_state:
    st.session_state.user_session = None

def login():
    """Pantalla de Login"""
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔐 Acceso al Sistema")
        st.caption("Plataforma de Gestión Industrial v3.0")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            pw = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                doc = db.collection("clientes").document(user).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("password") == pw:
                        if data.get("activo"):
                            st.session_state.user_session = data
                            st.session_state.user_id = user
                            st.rerun()
                        else:
                            st.error("⛔ Cuenta desactivada. Contacte soporte.")
                    else:
                        st.error("❌ Contraseña incorrecta")
                else:
                    st.error("❌ Usuario no encontrado")

def logout():
    st.session_state.user_session = None
    st.rerun()

# --- CEREBRO DE NAVEGACIÓN ---
if not st.session_state.user_session:
    # Si no hay usuario, solo mostramos Login
    pg = st.navigation([st.Page(login, title="Iniciar Sesión")])
    pg.run()

else:
    # --- USUARIO LOGUEADO: CONSTRUIMOS SU APP A MEDIDA ---
    datos = st.session_state.user_session
    carpeta_cliente = datos.get("script") # Ej: "incotec"
    nombre_cliente = datos.get("nombre")
    
    # Ruta donde están los archivos de este cliente
    path_cliente = os.path.join("instancias_clientes", carpeta_cliente)
    
    paginas = []
    
    # --- ESCÁNER DINÁMICO DE PÁGINAS ---
    # Busca automáticamente todos los .py en la carpeta del cliente
    if os.path.exists(path_cliente):
        archivos = [f for f in os.listdir(path_cliente) if f.endswith(".py") and "__" not in f]
        
        for archivo in archivos:
            # Creamos la ruta completa: instancias_clientes/incotec/stock.py
            ruta_archivo = os.path.join(path_cliente, archivo)
            
            # Nombre bonito para el menú (quitamos el .py y reemplazamos guiones)
            titulo = archivo.replace(".py", "").replace("_", " ").title()
            
            # Agregamos la página al sistema de navegación
            paginas.append(st.Page(ruta_archivo, title=titulo))
            
        # Ordenamos alfabéticamente (opcional)
        paginas.sort(key=lambda x: x.title)
        
    else:
        st.error(f"⚠️ Error Crítico: No encuentro la carpeta '{path_cliente}' en el servidor.")

    # --- EJECUCIÓN ---
    if paginas:
        pg = st.navigation(paginas)
        
        # Sidebar Marca Blanca
        with st.sidebar:
            st.subheader(nombre_cliente)
            st.caption(f"ID: {st.session_state.user_id}")
            st.divider()
            if st.button("Cerrar Sesión", type="primary"):
                logout()
                
        pg.run()
    else:
        st.warning(f"La carpeta '{carpeta_cliente}' está vacía. Crea archivos .py dentro para verlos aquí.")
        if st.button("Salir"): logout()