import streamlit as st
import pandas as pd
import time as tm
import datetime
import os
import sys

# --- CONEXIÓN BASE DE DATOS ---
# Busca el config.py en la misma carpeta
try:
    from config import db
except ImportError:
    st.error("❌ No encuentro el archivo config.py en esta carpeta.")
    st.stop()

# --- CONFIGURACIÓN DE TU PANEL ---
st.set_page_config(page_title="Super Admin SaaS", page_icon="🛠️", layout="wide")

st.title("🛠️ Tu Panel de Control (Super Admin)")
st.markdown("Desde aquí controlas la arquitectura de tu SaaS. **Sin login.**")
st.markdown("---")

# ==============================================================================
# TABS DE GESTIÓN
# ==============================================================================
tab_gestion, tab_crear_cliente, tab_crear_usuario = st.tabs([
    "🎛️ Gestionar Clientes", 
    "🏭 Crear Nueva Empresa", 
    "👤 Agregar Empleado a Empresa"
])

# ------------------------------------------------------------------------------
# TAB 1: GESTIÓN (HABILITAR / DESHABILITAR)
# ------------------------------------------------------------------------------
with tab_gestion:
    st.subheader("Estado de Clientes (Instancias)")
    
    # 1. Buscamos las carpetas de clientes en la colección 'instancias'
    ref_instancias = db.collection('instancias')
    docs = ref_instancias.stream()
    
    lista_clientes = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id # El ID es el nombre de la carpeta (ej: facha_shila)
        lista_clientes.append(d)
        
    if not lista_clientes:
        st.info("No hay empresas creadas con la nueva estructura de carpetas.")
    else:
        # Mostramos lista de clientes
        for cli in lista_clientes:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                
                with c1:
                    st.markdown(f"### 📂 {cli['id']}")
                    st.caption(f"Creado: {cli.get('creado_el', 'S/F')}")
                
                with c2:
                    # INTERRUPTOR MAESTRO
                    # Si desactivas esto, NADIE de esa empresa podrá entrar (ni el dueño ni empleados)
                    estado_actual = cli.get('activo', True)
                    nuevo_estado = st.toggle("Habilitado", value=estado_actual, key=f"toggle_{cli['id']}")
                    
                    if nuevo_estado != estado_actual:
                        ref_instancias.document(cli['id']).update({"activo": nuevo_estado})
                        st.toast(f"Estado de {cli['id']} actualizado.")
                        tm.sleep(0.5)
                        st.rerun()
                
                with c3:
                    if st.button("🗑️ Borrar", key=f"del_{cli['id']}"):
                        st.error("Borrar una instancia completa es peligroso. Hazlo desde Firebase Console si estás seguro.")

# ------------------------------------------------------------------------------
# TAB 2: CREAR NUEVA EMPRESA (Genera la Carpeta)
# ------------------------------------------------------------------------------
with tab_crear_cliente:
    st.subheader("🚀 Alta de Nuevo Cliente")
    st.info("Esto crea la **Carpeta Maestra** y el **Primer Usuario (Admin)** para que el cliente pueda entrar.")
    
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
                # 1. Validar si ya existe la carpeta
                doc_check = ref_instancias.document(id_carpeta).get()
                if doc_check.exists:
                    st.error("⚠️ Ya existe una carpeta con ese ID. Usa otro.")
                else:
                    # 2. CREAR LA CARPETA (DOCUMENTO EN 'INSTANCIAS')
                    # Esto es lo que ordena tu base de datos.
                    ref_instancias.document(id_carpeta).set({
                        "nombre": nombre_fantasia,
                        "creado_el": datetime.datetime.now(),
                        "activo": True
                    })
                    
                    # 3. CREAR EL USUARIO EN LA GUÍA GLOBAL (Para que pueda loguearse)
                    db.collection('saas_usuarios_global').add({
                        "usuario": user_admin,
                        "password": pass_admin,
                        "rol": "admin", # Es el dueño
                        "carpeta_instancia": id_carpeta, # <--- ESTO LO VINCULA A SU CARPETA
                        "activo": True,
                        "fecha_alta": datetime.datetime.now()
                    })
                    
                    st.success(f"✅ ¡Listo! Carpeta `instancias/{id_carpeta}` creada y usuario `{user_admin}` asignado.")
                    tm.sleep(2)
                    st.rerun()
            else:
                st.warning("Completa todos los campos.")

# ------------------------------------------------------------------------------
# TAB 3: AGREGAR EMPLEADO (A Empresa Existente)
# ------------------------------------------------------------------------------
with tab_crear_usuario:
    st.subheader("👤 Agregar Empleado a Cliente Existente")
    
    # Solo mostramos carpetas que existen
    opciones_carpetas = [c['id'] for c in lista_clientes]
    
    if not opciones_carpetas:
        st.warning("Primero debes crear una empresa en la pestaña anterior.")
    else:
        with st.form("form_nuevo_empleado"):
            target_carpeta = st.selectbox("¿A qué empresa pertenece?", opciones_carpetas)
            
            c1, c2, c3 = st.columns(3)
            new_user = c1.text_input("Usuario")
            new_pass = c2.text_input("Contraseña")
            new_rol = c3.selectbox("Rol", ["vendedor", "empleado", "admin"])
            
            if st.form_submit_button("Registrar Usuario"):
                if new_user and new_pass:
                    # Validar que el usuario no exista globalmente (para evitar conflictos de login)
                    q = db.collection('saas_usuarios_global').where("usuario", "==", new_user).stream()
                    if len(list(q)) > 0:
                        st.error("⚠️ Ese nombre de usuario ya está ocupado.")
                    else:
                        db.collection('saas_usuarios_global').add({
                            "usuario": new_user,
                            "password": new_pass,
                            "rol": new_rol,
                            "carpeta_instancia": target_carpeta, # Lo vinculamos a la carpeta seleccionada
                            "activo": True,
                            "fecha_alta": datetime.datetime.now()
                        })
                        st.success(f"✅ Usuario `{new_user}` agregado al equipo de `{target_carpeta}`.")
                        tm.sleep(1.5)
                        st.rerun()