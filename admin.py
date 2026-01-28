import streamlit as st
import pandas as pd
import time as tm
import datetime
import os
import sys

# --- CONEXIÓN BASE DE DATOS ---
try:
    from config import db
except ImportError:
    st.error("❌ No encuentro el archivo config.py en esta carpeta.")
    st.stop()

# --- CONFIGURACIÓN DE TU PANEL ---
st.set_page_config(page_title="Super Admin SaaS", page_icon="🛠️", layout="wide")

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL DOMINIO (Para los links de invitación)
# -----------------------------------------------------------------------------
# Cambia esto por tu URL real cuando lo subas a producción
# Ej: "https://mi-saas-industrial.streamlit.app"
URL_BASE = st.sidebar.text_input("URL de tu App (Para generar links)", value="http://localhost:8501")

st.title("🛠️ Tu Panel de Control (Super Admin)")
st.markdown("Desde aquí controlas la arquitectura de tu SaaS. **Sin login.**")
st.markdown("---")

# ==============================================================================
# TABS DE GESTIÓN
# ==============================================================================
tab_gestion, tab_crear_cliente, tab_crear_usuario = st.tabs([
    "🎛️ Gestionar Clientes y Usuarios", 
    "🏭 Crear Nueva Empresa", 
    "👤 Agregar Empleado a Empresa"
])

# ------------------------------------------------------------------------------
# TAB 1: GESTIÓN (CLIENTES + USUARIOS)
# ------------------------------------------------------------------------------
with tab_gestion:
    st.subheader("Estado de Clientes y sus Usuarios")
    
    ref_instancias = db.collection('instancias')
    docs = ref_instancias.stream()
    
    lista_clientes = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        lista_clientes.append(d)
        
    if not lista_clientes:
        st.info("No hay empresas creadas.")
    else:
        for cli in lista_clientes:
            # --- TARJETA DE EMPRESA ---
            with st.container(border=True):
                # CABECERA DE LA EMPRESA
                c1, c2, c3 = st.columns([3, 1, 1])
                
                with c1:
                    st.markdown(f"### 🏢 {cli['nombre']} (`{cli['id']}`)")
                    st.caption(f"Creado: {cli.get('creado_el', 'S/F')}")
                    
                    # Generamos el link mágico
                    # Suponemos que tu app leerá ?empresa=facha_shila
                    link_invitacion = f"{URL_BASE}/?empresa={cli['id']}"
                    st.code(link_invitacion, language="text")
                    st.caption("👆 Copia este link para que los empleados entren directo a esta empresa.")

                with c2:
                    st.write("**Estado Empresa**")
                    estado_actual = cli.get('activo', True)
                    nuevo_estado = st.toggle("Habilitada", value=estado_actual, key=f"tg_cli_{cli['id']}")
                    
                    if nuevo_estado != estado_actual:
                        ref_instancias.document(cli['id']).update({"activo": nuevo_estado})
                        st.toast(f"Empresa {cli['id']} actualizada.")
                        tm.sleep(0.5)
                        st.rerun()
                
                with c3:
                    if st.button("🗑️ Borrar Emp.", key=f"del_cli_{cli['id']}"):
                        st.error("Acción bloqueada por seguridad. Hazlo en Firebase.")

                st.divider()
                
                # --- LISTADO DE USUARIOS DE ESTA EMPRESA ---
                with st.expander(f"👥 Ver Usuarios de {cli['nombre']}"):
                    # Buscamos SOLO los usuarios de esta carpeta
                    users_ref = db.collection('saas_usuarios_global')
                    query = users_ref.where('carpeta_instancia', '==', cli['id']).stream()
                    users_list = []
                    for u in query:
                        ud = u.to_dict()
                        ud['doc_id'] = u.id
                        users_list.append(ud)
                    
                    if not users_list:
                        st.warning("Esta empresa no tiene usuarios asignados.")
                    else:
                        # Encabezados de tabla
                        h1, h2, h3, h4 = st.columns([2, 2, 1, 1])
                        h1.markdown("**Usuario**")
                        h2.markdown("**Rol / Pass**")
                        h3.markdown("**Acceso**")
                        h4.markdown("**Acción**")
                        
                        for user in users_list:
                            uc1, uc2, uc3, uc4 = st.columns([2, 2, 1, 1])
                            
                            with uc1:
                                st.write(f"👤 {user.get('usuario')}")
                            
                            with uc2:
                                st.caption(f"Rol: {user.get('rol')}")
                                # Opcional: Mostrar contraseña si eres super admin
                                st.caption(f"🔑 {user.get('password')}") 
                            
                            with uc3:
                                # TOGGLE USUARIO INDIVIDUAL
                                act_user = user.get('activo', True)
                                if st.toggle("On/Off", value=act_user, key=f"tg_usr_{user['doc_id']}") != act_user:
                                    users_ref.document(user['doc_id']).update({"activo": not act_user})
                                    st.toast(f"Usuario {user.get('usuario')} actualizado.")
                                    tm.sleep(0.5)
                                    st.rerun()
                            
                            with uc4:
                                # BORRAR USUARIO
                                if st.button("❌", key=f"del_usr_{user['doc_id']}", help="Eliminar usuario permanentemente"):
                                    users_ref.document(user['doc_id']).delete()
                                    st.toast(f"Usuario eliminado.")
                                    tm.sleep(0.5)
                                    st.rerun()
                            st.markdown("---")

# ------------------------------------------------------------------------------
# TAB 2: CREAR NUEVA EMPRESA
# ------------------------------------------------------------------------------
with tab_crear_cliente:
    st.subheader("🚀 Alta de Nuevo Cliente")
    
    with st.form("form_nueva_empresa"):
        col_a, col_b = st.columns(2)
        nombre_fantasia = col_a.text_input("Nombre del Negocio", placeholder="Ej: Facha & Shila")
        id_carpeta = col_b.text_input("ID de Carpeta (Sin espacios)", placeholder="Ej: facha_shila")
        
        st.markdown("#### Datos del Dueño (Primer Acceso)")
        col_c, col_d = st.columns(2)
        user_admin = col_c.text_input("Usuario Login")
        pass_admin = col_d.text_input("Contraseña")
        
        if st.form_submit_button("Crear Infraestructura"):
            if id_carpeta and user_admin and pass_admin:
                doc_check = ref_instancias.document(id_carpeta).get()
                if doc_check.exists:
                    st.error("⚠️ Ya existe una carpeta con ese ID.")
                else:
                    # 1. Crear Carpeta
                    ref_instancias.document(id_carpeta).set({
                        "nombre": nombre_fantasia,
                        "creado_el": datetime.datetime.now(),
                        "activo": True
                    })
                    # 2. Crear Usuario Admin Global
                    db.collection('saas_usuarios_global').add({
                        "usuario": user_admin,
                        "password": pass_admin,
                        "rol": "admin",
                        "carpeta_instancia": id_carpeta,
                        "activo": True,
                        "fecha_alta": datetime.datetime.now()
                    })
                    st.success(f"✅ Empresa {nombre_fantasia} creada.")
                    tm.sleep(1.5)
                    st.rerun()
            else:
                st.warning("Completa todos los campos.")

# ------------------------------------------------------------------------------
# TAB 3: AGREGAR EMPLEADO
# ------------------------------------------------------------------------------
with tab_crear_usuario:
    st.subheader("👤 Agregar Empleado a Cliente Existente")
    
    opciones_carpetas = [c['id'] for c in lista_clientes]
    
    if not opciones_carpetas:
        st.warning("Primero crea una empresa.")
    else:
        with st.form("form_nuevo_empleado"):
            target_carpeta = st.selectbox("¿A qué empresa pertenece?", opciones_carpetas)
            
            c1, c2, c3 = st.columns(3)
            new_user = c1.text_input("Usuario")
            new_pass = c2.text_input("Contraseña")
            new_rol = c3.selectbox("Rol", ["vendedor", "empleado", "admin"])
            
            if st.form_submit_button("Registrar Usuario"):
                if new_user and new_pass:
                    q = db.collection('saas_usuarios_global').where("usuario", "==", new_user).stream()
                    if len(list(q)) > 0:
                        st.error("⚠️ Ese usuario ya existe.")
                    else:
                        db.collection('saas_usuarios_global').add({
                            "usuario": new_user,
                            "password": new_pass,
                            "rol": new_rol,
                            "carpeta_instancia": target_carpeta,
                            "activo": True,
                            "fecha_alta": datetime.datetime.now()
                        })
                        st.success(f"✅ Usuario `{new_user}` agregado a `{target_carpeta}`.")
                        tm.sleep(1.5)
                        st.rerun()