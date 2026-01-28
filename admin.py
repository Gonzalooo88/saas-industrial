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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Super Admin SaaS", page_icon="🛠️", layout="wide")

# URL FIJA DE TU APP (Para generar invitaciones)
URL_APP = "https://saas-industrial-vbqr4pex367axdvgtuxiyw.streamlit.app"

st.title("🛠️ Panel de Control")
st.caption(f"🔗 Dominio configurado: `{URL_APP}`") # <--- AQUI ESTA EL CAMBIO ESTETICO
st.markdown("---")

# ==============================================================================
# TABS
# ==============================================================================
tab_gestion, tab_crear_cliente, tab_crear_usuario = st.tabs([
    "🎛️ Clientes y Usuarios", 
    "🏭 Nueva Empresa", 
    "👤 Nuevo Empleado"
])

# ------------------------------------------------------------------------------
# TAB 1: GESTIÓN COMPLETA
# ------------------------------------------------------------------------------
with tab_gestion:
    st.subheader("Directorio de Empresas")
    
    ref_instancias = db.collection('instancias')
    docs = ref_instancias.stream()
    
    lista_clientes = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        lista_clientes.append(d)
        
    if not lista_clientes:
        st.info("No hay empresas registradas.")
    else:
        for cli in lista_clientes:
            # --- TARJETA DE EMPRESA ---
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.markdown(f"### 🏢 {cli.get('nombre', 'Sin Nombre')} (`{cli['id']}`)")
                    # Link de invitación limpio
                    link = f"{URL_APP}/?empresa={cli['id']}"
                    st.text_input(f"Link Invitación {cli['nombre']}", value=link, disabled=True, key=f"lnk_{cli['id']}")

                with c2:
                    st.write("**Estado**")
                    act = cli.get('activo', True)
                    if st.toggle("Activo", value=act, key=f"tg_cli_{cli['id']}") != act:
                        ref_instancias.document(cli['id']).update({"activo": not act})
                        st.rerun()
                
                # --- GESTIÓN DE USUARIOS DE ESTA EMPRESA ---
                with st.expander(f"👥 Gestionar Usuarios de {cli['nombre']}"):
                    users_ref = db.collection('saas_usuarios_global')
                    query = users_ref.where('carpeta_instancia', '==', cli['id']).stream()
                    
                    users = []
                    for u in query:
                        ud = u.to_dict()
                        ud['uid'] = u.id
                        users.append(ud)
                    
                    if not users:
                        st.warning("Sin usuarios.")
                    else:
                        for u in users:
                            uc1, uc2, uc3 = st.columns([2, 1, 1])
                            uc1.write(f"👤 **{u['usuario']}** ({u.get('rol')})")
                            uc1.caption(f"Pass: {u.get('password')}")
                            
                            with uc2:
                                u_act = u.get('activo', True)
                                if st.checkbox("Habilitado", value=u_act, key=f"u_act_{u['uid']}") != u_act:
                                    users_ref.document(u['uid']).update({"activo": not u_act})
                                    st.toast("Estado usuario actualizado")
                                    tm.sleep(0.5)
                                    st.rerun()
                            
                            with uc3:
                                if st.button("🗑️", key=f"del_{u['uid']}"):
                                    users_ref.document(u['uid']).delete()
                                    st.toast("Usuario eliminado")
                                    tm.sleep(0.5)
                                    st.rerun()
                            st.divider()

# ------------------------------------------------------------------------------
# TAB 2: CREAR EMPRESA
# ------------------------------------------------------------------------------
with tab_crear_cliente:
    st.subheader("Alta de Empresa")
    with st.form("new_corp"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre Fantasía")
        id_carp = c2.text_input("ID Carpeta (único, sin espacios)")
        
        st.markdown("**Usuario Admin Inicial**")
        c3, c4 = st.columns(2)
        u_adm = c3.text_input("Usuario")
        p_adm = c4.text_input("Contraseña")
        
        if st.form_submit_button("Crear"):
            if id_carp and u_adm and p_adm:
                check = ref_instancias.document(id_carp).get()
                if check.exists:
                    st.error("ID ocupado.")
                else:
                    # Crear carpeta
                    ref_instancias.document(id_carp).set({
                        "nombre": nombre, "creado_el": datetime.datetime.now(), "activo": True
                    })
                    # Crear admin
                    db.collection('saas_usuarios_global').add({
                        "usuario": u_adm, "password": p_adm, "rol": "admin",
                        "carpeta_instancia": id_carp, "activo": True, "fecha_alta": datetime.datetime.now()
                    })
                    st.success("Empresa creada.")
                    tm.sleep(1)
                    st.rerun()

# ------------------------------------------------------------------------------
# TAB 3: AGREGAR EMPLEADO
# ------------------------------------------------------------------------------
with tab_crear_usuario:
    st.subheader("Alta de Empleado")
    opts = [c['id'] for c in lista_clientes]
    if not opts:
        st.warning("No hay empresas.")
    else:
        with st.form("new_emp"):
            empresa = st.selectbox("Empresa", opts)
            c1, c2, c3 = st.columns(3)
            usr = c1.text_input("Usuario")
            pwd = c2.text_input("Pass")
            rol = c3.selectbox("Rol", ["vendedor", "empleado", "admin"])
            
            if st.form_submit_button("Crear Usuario"):
                check = db.collection('saas_usuarios_global').where("usuario", "==", usr).stream()
                if len(list(check)) > 0:
                    st.error("Usuario ya existe.")
                else:
                    db.collection('saas_usuarios_global').add({
                        "usuario": usr, "password": pwd, "rol": rol,
                        "carpeta_instancia": empresa, "activo": True, "fecha_alta": datetime.datetime.now()
                    })
                    st.success("Usuario creado.")
                    tm.sleep(1)
                    st.rerun()