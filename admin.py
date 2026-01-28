import streamlit as st
import pandas as pd
import os
import sys

# --- PROTECCIÓN CONTRA EL ERROR DE TIEMPO ---
import time as tm
import datetime
# --------------------------------------------

# --- CONEXIÓN CON BASE DE DATOS ---
try:
    from config import db
except ImportError:
    st.error("❌ No se encontró el archivo config.py en la raíz.")
    st.stop()

st.set_page_config(page_title="Master Admin SaaS", page_icon="👑", layout="wide")

st.title("👑 Panel Maestro del SaaS")
st.markdown("---")

# ==============================================================================
# CARGA DE DATOS (Centralizada)
# ==============================================================================
# Cargamos TODOS los usuarios para procesarlos
try:
    users_ref = db.collection('usuarios')
    docs = users_ref.stream()
    lista_usuarios = []
    clientes_unicos = set()
    
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        lista_usuarios.append(d)
        if 'carpeta_instancia' in d:
            clientes_unicos.add(d['carpeta_instancia'])
            
except Exception as e:
    st.error(f"Error crítico conectando a la base de datos: {e}")
    st.stop()

# ==============================================================================
# INTERFAZ PRINCIPAL
# ==============================================================================

tab_clientes, tab_usuarios, tab_altas = st.tabs([
    "🏢 Gestión de Clientes (Empresas)", 
    "👤 Gestión de Usuarios", 
    "➕ Altas Nuevas"
])

# ------------------------------------------------------------------------------
# TAB 1: GESTIÓN DE CLIENTES (Bloqueo Masivo)
# ------------------------------------------------------------------------------
with tab_clientes:
    st.subheader("🏢 Control de Inquilinos (Clientes)")
    st.caption("Aquí puedes habilitar o bloquear una empresa entera. Al bloquearla, TODOS sus usuarios perderán acceso.")
    
    if not clientes_unicos:
        st.info("No hay clientes registrados.")
    else:
        # Mostramos cada cliente único encontrado
        for cliente_folder in sorted(list(clientes_unicos)):
            # Buscamos los usuarios de este cliente
            users_del_cliente = [u for u in lista_usuarios if u.get('carpeta_instancia') == cliente_folder]
            
            # Calculamos estado general (Si al menos uno está activo, lo mostramos activo, o lógica personalizada)
            activos = sum(1 for u in users_del_cliente if u.get('activo', True))
            total = len(users_del_cliente)
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                
                with c1:
                    st.markdown(f"### 📂 {cliente_folder.replace('_', ' ').title()}")
                    st.caption(f"Carpeta: `{cliente_folder}` | Usuarios registrados: {total}")
                
                with c2:
                    st.write(f"**{activos}/{total} Activos**")
                
                with c3:
                    # BOTONES DE ACCIÓN MASIVA
                    if st.button("⛔ BLOQUEAR TODO", key=f"block_{cliente_folder}", type="primary"):
                        batch = db.batch()
                        for u in users_del_cliente:
                            ref = users_ref.document(u['id'])
                            batch.update(ref, {"activo": False})
                        batch.commit()
                        st.toast(f"Cliente {cliente_folder} bloqueado totalmente.")
                        tm.sleep(1)
                        st.rerun()
                        
                    if st.button("✅ HABILITAR TODO", key=f"allow_{cliente_folder}"):
                        batch = db.batch()
                        for u in users_del_cliente:
                            ref = users_ref.document(u['id'])
                            batch.update(ref, {"activo": True})
                        batch.commit()
                        st.toast(f"Cliente {cliente_folder} habilitado.")
                        tm.sleep(1)
                        st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: GESTIÓN DE USUARIOS (Control Granular)
# ------------------------------------------------------------------------------
with tab_usuarios:
    st.subheader("👤 Control Individual de Usuarios")
    st.caption("Habilita o deshabilita usuarios específicos sin afectar a toda la empresa.")
    
    # Filtros
    filtro_cliente = st.selectbox("Filtrar por Cliente", ["Todos"] + list(clientes_unicos))
    
    # Aplicar filtro
    usuarios_filtrados = lista_usuarios
    if filtro_cliente != "Todos":
        usuarios_filtrados = [u for u in lista_usuarios if u.get('carpeta_instancia') == filtro_cliente]
    
    if not usuarios_filtrados:
        st.warning("No se encontraron usuarios.")
    else:
        # Convertimos a DataFrame para una tabla editable rápida, o iteramos
        for u in usuarios_filtrados:
            col_u1, col_u2, col_u3, col_u4 = st.columns([2, 2, 1, 1])
            
            with col_u1:
                st.write(f"**{u.get('usuario')}**")
            with col_u2:
                st.caption(f"{u.get('carpeta_instancia')} ({u.get('rol')})")
            
            with col_u3:
                # TOGGLE INDIVIDUAL
                estado = u.get('activo', True)
                new_estado = st.toggle("Activo", value=estado, key=f"user_{u['id']}")
                if new_estado != estado:
                    users_ref.document(u['id']).update({"activo": new_estado})
                    st.toast("Estado actualizado")
                    tm.sleep(0.5)
                    st.rerun()
            
            with col_u4:
                if st.button("🗑️", key=f"del_u_{u['id']}"):
                    users_ref.document(u['id']).delete()
                    st.toast("Usuario eliminado")
                    tm.sleep(0.5)
                    st.rerun()
            st.divider()

# ------------------------------------------------------------------------------
# TAB 3: ALTAS (SEPARADAS)
# ------------------------------------------------------------------------------
with tab_altas:
    st.header("➕ Generadores de Alta")
    
    sub_tab_cliente, sub_tab_usuario = st.tabs(["🏭 Nuevo Cliente (Empresa)", "👤 Nuevo Usuario (Empleado)"])
    
    # --- A. GENERADOR DE CLIENTE NUEVO ---
    with sub_tab_cliente:
        st.info("Esto crea una nueva instancia de negocio y su primer usuario Administrador.")
        with st.form("form_new_client"):
            c_a1, c_a2 = st.columns(2)
            nombre_negocio = c_a1.text_input("Nombre del Negocio (ej: Facha & Shila)")
            carpeta_instancia = c_a2.text_input("Nombre de Carpeta (ID único)", placeholder="ej: facha_shila")
            
            st.markdown("---")
            st.write("**Primer Usuario Administrador**")
            c_u1, c_u2 = st.columns(2)
            admin_user = c_u1.text_input("Usuario Admin")
            admin_pass = c_u2.text_input("Contraseña Admin", type="password")
            
            if st.form_submit_button("🚀 Crear Cliente e Instancia"):
                if nombre_negocio and carpeta_instancia and admin_user and admin_pass:
                    # Validar que no exista carpeta
                    existe = any(u['carpeta_instancia'] == carpeta_instancia for u in lista_usuarios)
                    if existe:
                        st.error("⚠️ Ya existe un cliente con esa carpeta/ID. Elige otro.")
                    else:
                        # Crear usuario admin
                        users_ref.add({
                            "usuario": admin_user,
                            "password": admin_pass,
                            "rol": "admin",
                            "carpeta_instancia": carpeta_instancia,
                            "nombre_negocio": nombre_negocio,
                            "activo": True,
                            "fecha_alta": datetime.datetime.now()
                        })
                        st.success(f"✅ Cliente '{nombre_negocio}' creado con éxito.")
                        tm.sleep(1.5)
                        st.rerun()
                else:
                    st.warning("Todos los campos son obligatorios.")

    # --- B. GENERADOR DE USUARIO NUEVO ---
    with sub_tab_usuario:
        st.info("Esto agrega un usuario extra a un cliente que YA existe.")
        
        if not clientes_unicos:
            st.error("Primero debes crear un cliente en la otra pestaña.")
        else:
            with st.form("form_new_user_add"):
                sel_cliente = st.selectbox("Seleccionar Cliente", list(clientes_unicos))
                
                c_nu1, c_nu2, c_nu3 = st.columns(3)
                n_user = c_nu1.text_input("Nuevo Usuario")
                n_pass = c_nu2.text_input("Contraseña", type="password")
                n_rol = c_nu3.selectbox("Rol", ["vendedor", "admin", "empleado"])
                
                if st.form_submit_button("💾 Agregar Usuario"):
                    if n_user and n_pass:
                        # Validar que no se repita el usuario globalmente (o por cliente, segun prefieras)
                        existe_user = any(u['usuario'] == n_user for u in lista_usuarios)
                        if existe_user:
                            st.error("⚠️ Ese nombre de usuario ya está en uso en el sistema.")
                        else:
                            users_ref.add({
                                "usuario": n_user,
                                "password": n_pass,
                                "rol": n_rol,
                                "carpeta_instancia": sel_cliente,
                                "activo": True,
                                "fecha_alta": datetime.datetime.now()
                            })
                            st.success(f"Usuario {n_user} agregado a {sel_cliente}.")
                            tm.sleep(1.5)
                            st.rerun()
                    else:
                        st.warning("Faltan datos.")