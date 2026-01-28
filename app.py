import streamlit as st
import time as tm
import os
import sys

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Acceso SaaS", page_icon="🔐", layout="centered")

# --- CONEXIÓN A LA BASE DE DATOS ---
try:
    from config import db
except ImportError:
    st.error("❌ Error: No se encuentra config.py")
    st.stop()

# --- GESTIÓN DE SESIÓN ---
if 'logueado' not in st.session_state:
    st.session_state.logueado = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = ""
if 'rol' not in st.session_state:
    st.session_state.rol = ""
if 'carpeta_cliente' not in st.session_state:
    st.session_state.carpeta_cliente = ""

# ==============================================================================
# LÓGICA DE PARAMETROS URL (LINK DE INVITACIÓN)
# ==============================================================================
# Detectamos si viene ?empresa=algo en el link
query_params = st.query_params
empresa_param = query_params.get("empresa", None)

# ==============================================================================
# FUNCIÓN DE LOGIN
# ==============================================================================
def login():
    st.title("🔐 Iniciar Sesión")
    
    # Si viene con link de invitación, mostramos un mensaje personalizado
    if empresa_param:
        st.info(f"🏢 Ingresando al portal de: **{empresa_param.upper().replace('_', ' ')}**")
    else:
        st.markdown("Bienvenido al Sistema de Gestión.")
    
    with st.form("login_form"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.form_submit_button("Ingresar", type="primary"):
            if not user_input or not pass_input:
                st.warning("Por favor ingrese usuario y contraseña.")
                return

            try:
                # 1. BUSCAMOS EN LA GUÍA GLOBAL
                users_ref = db.collection('saas_usuarios_global')
                query = users_ref.where('usuario', '==', user_input).where('password', '==', pass_input).stream()
                
                results = list(query)
                
                if len(results) == 0:
                    st.error("Usuario o contraseña incorrectos.")
                else:
                    user_data = results[0].to_dict()
                    carpeta_usuario = user_data.get('carpeta_instancia')
                    
                    # --- VALIDACIÓN DE LINK DE INVITACIÓN ---
                    # Si el usuario usó un link de invitación, verificamos que pertenezca a esa empresa
                    if empresa_param and carpeta_usuario != empresa_param:
                        st.error(f"⛔ Error de seguridad: Tu usuario pertenece a '{carpeta_usuario}', no puedes ingresar mediante el enlace de '{empresa_param}'.")
                        return

                    # 2. VERIFICAMOS SI EL USUARIO ESTÁ ACTIVO
                    if not user_data.get('activo', True):
                        st.error("⛔ Tu usuario ha sido deshabilitado por el administrador.")
                        return

                    # 3. VERIFICAMOS SI LA EMPRESA ESTÁ ACTIVA
                    instancia_doc = db.collection('instancias').document(carpeta_usuario).get()
                    
                    if instancia_doc.exists:
                        instancia_data = instancia_doc.to_dict()
                        if not instancia_data.get('activo', True):
                            st.error("🏢 La empresa a la que perteneces está suspendida temporalmente.")
                            return
                    else:
                        st.warning(f"⚠️ Error crítico: No encuentro la carpeta '{carpeta_usuario}'.")
                        return

                    # 4. ÉXITO
                    st.session_state.logueado = True
                    st.session_state.usuario = user_data['usuario']
                    st.session_state.rol = user_data['rol']
                    st.session_state.carpeta_cliente = carpeta_usuario
                    
                    st.success(f"Bienvenido {user_data['usuario']} ({carpeta_usuario})")
                    tm.sleep(1)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error de conexión: {e}")

# ==============================================================================
# FUNCIÓN DE LOGOUT
# ==============================================================================
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==============================================================================
# LÓGICA PRINCIPAL (NAVIGATOR)
# ==============================================================================
if not st.session_state.logueado:
    login()
else:
    # --- MENÚ LATERAL ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.usuario}**")
        st.caption(f"Empresa: {st.session_state.carpeta_cliente.upper()}")
        st.caption(f"Rol: {st.session_state.rol}")
        
        st.divider()
        
        if st.button("Cerrar Sesión"):
            logout()

    # --- RUTEO DE PÁGINAS ---
    # NOTA: Asegúrate de que los archivos existan en la carpeta con ESTOS nombres exactos.
    # Si tu archivo de caja se llama '3_movimientos.py', cambia la línea de abajo.
    
    pg = st.navigation([
        st.Page("instancias_clientes/facha_shila/0_inicio.py", title="Inicio", icon="🏠"),
        st.Page("instancias_clientes/facha_shila/1_ventas.py", title="Ventas", icon="🛒"),
        st.Page("instancias_clientes/facha_shila/2_stock.py", title="Stock", icon="📦"),
        st.Page("instancias_clientes/facha_shila/3_movimientos.py", title="movimientos", icon="💵"), 
        st.Page("instancias_clientes/facha_shila/4_admin.py", title="Admin Local", icon="⚙️"),
    ])
    
    try:
        pg.run()
    except Exception as e:
        st.error(f"Error cargando la página: {e}")
        st.info("💡 Consejo: Revisa que el archivo '3_movimientos.py' o '3_movimientos.py' exista y coincida con el nombre en app.py")