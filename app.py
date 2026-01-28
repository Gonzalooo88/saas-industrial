import streamlit as st
import time as tm # Usamos tm para evitar errores
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
# FUNCIÓN DE LOGIN
# ==============================================================================
def login():
    st.title("🔐 Iniciar Sesión")
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
                    
                    # 2. VERIFICAMOS SI EL USUARIO ESTÁ ACTIVO
                    if not user_data.get('activo', True):
                        st.error("⛔ Tu usuario ha sido deshabilitado por el administrador.")
                        return

                    # 3. VERIFICAMOS SI LA EMPRESA ESTÁ ACTIVA
                    carpeta = user_data.get('carpeta_instancia')
                    instancia_doc = db.collection('instancias').document(carpeta).get()
                    
                    if instancia_doc.exists:
                        instancia_data = instancia_doc.to_dict()
                        if not instancia_data.get('activo', True):
                            st.error("🏢 La empresa a la que perteneces está suspendida temporalmente.")
                            return
                    else:
                        # Si no existe la carpeta en 'instancias', es un error crítico de datos
                        st.warning(f"⚠️ Error de sistema: No encuentro la carpeta '{carpeta}'. Contacta soporte.")
                        return

                    # 4. ÉXITO: GUARDAMOS DATOS EN SESIÓN
                    st.session_state.logueado = True
                    st.session_state.usuario = user_data['usuario']
                    st.session_state.rol = user_data['rol']
                    st.session_state.carpeta_cliente = carpeta 
                    
                    st.success(f"Bienvenido {user_data['usuario']} ({carpeta})")
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
    # Aquí cargamos el archivo de Inicio primero y corregimos el ícono de Caja
    
    pg = st.navigation([
        st.Page("instancias_clientes/facha_shila/0_inicio.py", title="Inicio", icon="🏠"),
        st.Page("instancias_clientes/facha_shila/1_ventas.py", title="💰 Ventas", icon="🛒"),
        st.Page("instancias_clientes/facha_shila/2_stock.py", title="📦 Stock", icon="📦"),
        st.Page("instancias_clientes/facha_shila/3_movimientos.py", title="💵 movimientos", icon="💵"), # Icono corregido
        st.Page("instancias_clientes/facha_shila/4_admin.py", title="⚙️ Admin Local", icon="⚙️"),
    ])
    
    try:
        pg.run()
    except Exception as e:
        st.error(f"Error cargando la página: {e}")
        st.info("💡 Posible causa: Verifica que todos los archivos (0_inicio, 1_ventas, etc.) existan en la carpeta.")