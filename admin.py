import streamlit as st
import time as tm
import datetime
import os
# Ya no importamos shutil porque no copiaremos nada

# --- CONEXIÓN ---
try:
    from config import db
except ImportError:
    st.error("❌ Falta config.py")
    st.stop()

st.set_page_config(page_title="Super Admin SaaS", page_icon="🛠️", layout="wide")
URL_BASE = "https://tu-app.streamlit.app" 

st.title("🛠️ Super Admin (Modo Custom)")
st.caption("Cada cliente inicia con una carpeta vacía para desarrollo a medida.")
st.markdown("---")

tab_gestion, tab_crear_cliente, tab_crear_usuario = st.tabs([
    "🎛️ Gestionar Clientes", 
    "🏭 Crear Nueva Empresa", 
    "👤 Nuevo Empleado"
])

# ------------------------------------------------------------------------------
# TAB 1: GESTIÓN
# ------------------------------------------------------------------------------
with tab_gestion:
    st.subheader("Estado de Clientes")
    docs = db.collection('instancias').stream()
    
    for doc in docs:
        d = doc.to_dict()
        cid = doc.id
        
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### 🏢 {d.get('nombre')} (`{cid}`)")
                st.caption(f"Link: {URL_BASE}/?empresa={cid}")
                
                # Checkeo físico rápido
                ruta = f"instancias_clientes/{cid}"
                if os.path.exists(ruta):
                    archs = [f for f in os.listdir(ruta) if f.endswith('.py')]
                    st.caption(f"📂 Módulos detectados: {len(archs)} archivos")
                else:
                    st.error("⚠️ La carpeta física NO existe.")

            with c2:
                act = d.get('activo', True)
                if st.toggle("Activo", value=act, key=f"tg_{cid}") != act:
                    db.collection('instancias').document(cid).update({"activo": not act})
                    st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: CREAR NUEVA EMPRESA (VACÍA)
# ------------------------------------------------------------------------------
with tab_crear_cliente:
    st.subheader("🚀 Alta de Nuevo Cliente")
    st.info("Esto creará la carpeta vacía y el usuario admin.")
    
    with st.form("form_new"):
        col_a, col_b = st.columns(2)
        nombre = col_a.text_input("Nombre Negocio")
        id_carp = col_b.text_input("ID Carpeta (ej: nike)")
        
        st.markdown("#### Admin Inicial")
        col_c, col_d = st.columns(2)
        u_adm = col_c.text_input("Usuario")
        p_adm = col_d.text_input("Pass")
        
        if st.form_submit_button("Crear"):
            if id_carp and u_adm:
                # 1. Validar si existe en DB
                if db.collection('instancias').document(id_carp).get().exists:
                    st.error("ID ya existe en DB.")
                    st.stop()
                
                # 2. Validar carpeta física
                ruta_final = f"instancias_clientes/{id_carp}"
                if os.path.exists(ruta_final):
                    st.error("Carpeta ya existe en servidor.")
                    st.stop()
                
                # 3. CREAR CARPETA VACÍA
                try:
                    os.makedirs(ruta_final)
                    # Creamos un archivo dummy para que github/sistema no la ignore
                    with open(f"{ruta_final}/__init__.py", "w") as f:
                        f.write("# Carpeta de cliente")
                    
                    # 4. CREAR EN DB
                    db.collection('instancias').document(id_carp).set({
                        "nombre": nombre, "creado_el": datetime.datetime.now(), "activo": True
                    })
                    db.collection('saas_usuarios_global').add({
                        "usuario": u_adm, "password": p_adm, "rol": "admin",
                        "carpeta_instancia": id_carp, "activo": True, "fecha_alta": datetime.datetime.now()
                    })
                    
                    st.success(f"✅ Cliente creado. Carpeta `{ruta_final}` lista para recibir código.")
                    tm.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creando carpeta: {e}")
            else:
                st.warning("Faltan datos.")

# ------------------------------------------------------------------------------
# TAB 3: CREAR USUARIO (Igual que antes)
# ------------------------------------------------------------------------------
with tab_crear_usuario:
    st.write("Agrega empleados a empresas existentes (código igual al anterior).")
    # ... (Usa el mismo código de creación de usuario de siempre)