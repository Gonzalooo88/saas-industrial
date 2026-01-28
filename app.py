import streamlit as st
import os
from config import db  # <--- Conexión centralizada

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Facha & Shila System", layout="wide", page_icon="👕")

# --- GESTIÓN DE ESTADO (SESSION STATE) ---
if 'password_correct' not in st.session_state:
    st.session_state.password_correct = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

# --- FUNCIÓN DE LOGIN (Conectada a tu Base de Datos) ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Facha & Shila")
        st.caption("Sistema de Gestión de Stock y Ventas")
        
        with st.form("login_form"):
            # Usamos selectbox para que sea más rápido en el celular
            usuario = st.selectbox("Selecciona tu usuario", ["Seleccionar...", "Bianca", "Luciano", "Empleado"])
            password = st.text_input("Contraseña", type="password")
            
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                if usuario == "Seleccionar...":
                    st.warning("Por favor elige un usuario.")
                    return

                # 1. Buscamos el usuario en la base de datos REAL
                doc_ref = db.collection('facha_shila_usuarios').document(usuario)
                doc = doc_ref.get()

                if doc.exists:
                    data = doc.to_dict()
                    
                    # A. Verificamos si está ACTIVO (El interruptor del Admin)
                    if not data.get('activo', True):
                        st.error("🚫 Tu usuario está desactivado. Contacta al administrador.")
                        return

                    # B. Verificamos la CONTRASEÑA
                    if data.get('pass') == password:
                        st.session_state.password_correct = True
                        st.session_state.usuario = usuario
                        st.session_state.rol = data.get('rol', 'vendedor')
                        st.toast(f"¡Hola {usuario}!", icon="👋")
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta.")
                else:
                    # C. MODO RESPALDO (Por si borraste usuarios o es la primera vez)
                    # Esto te permite entrar con 1234 si el usuario no existe en la BD
                    if password == "1234":
                        st.warning("⚠️ Entrando en modo respaldo (Usuario no en BD).")
                        st.session_state.password_correct = True
                        st.session_state.usuario = usuario
                        st.session_state.rol = "admin"
                        st.rerun()
                    else:
                        st.error("❌ Usuario no encontrado.")

# --- FUNCIÓN DE LOGOUT ---
def logout():
    st.session_state.password_correct = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.rerun()

# --- CEREBRO DE NAVEGACIÓN ---
if not st.session_state.password_correct:
    # Si NO está logueado, mostramos solo la pantalla de Login
    pg = st.navigation([st.Page(login_screen, title="Iniciar Sesión")])
    pg.run()

else:
    # --- SI ESTÁ LOGUEADO: CARGAMOS LA APP ---
    
    # Ruta específica de Facha & Shila
    path_cliente = os.path.join("instancias_clientes", "facha_shila")
    
    paginas = []
    
    # Escáner de archivos: Busca automáticamente los .py en la carpeta
    if os.path.exists(path_cliente):
        archivos = [f for f in os.listdir(path_cliente) if f.endswith(".py") and "__" not in f]
        
        for archivo in archivos:
            ruta_archivo = os.path.join(path_cliente, archivo)
            
            # Limpiamos el nombre para el menú (ej: "1_ventas.py" -> "Ventas")
            nombre_menu = archivo.replace(".py", "").replace("_", " ").title()
            
            # Si el nombre empieza con números (ej: 1, 2, 3), los quitamos visualmente si quieres
            # O los dejamos para que se ordenen bien.
            
            paginas.append(st.Page(ruta_archivo, title=nombre_menu))
            
        # Ordenamos alfabéticamente para que salgan en orden (1, 2, 3, 4)
        paginas.sort(key=lambda x: x.title)
        
    else:
        st.error(f"⚠️ Error: No encuentro la carpeta '{path_cliente}'. Revisa tu GitHub.")

    # --- EJECUCIÓN FINAL ---
    if paginas:
        pg = st.navigation(paginas)
        
        # Barra lateral con info de usuario
        with st.sidebar:
            st.write(f"👤 **{st.session_state.usuario}**")
            st.caption(f"Rol: {st.session_state.rol}")
            if st.button("Cerrar Sesión", type="primary", use_container_width=True):
                logout()
                
        pg.run()
    else:
        st.warning("No se encontraron módulos en la carpeta del sistema.")

        if st.button("Salir"): logout()
