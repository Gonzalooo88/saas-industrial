import streamlit as st
import os
from config import db 

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Panel Super Admin", page_icon="🛠️", layout="wide")

# 🔗 TU LINK DE LA APP (Asegúrate que sea el correcto)
LINK_APP = "https://saas-industrial-vbqr4pex367axdvgtuxiyw.streamlit.app/"

st.title("🛠️ Panel CTO (Super Admin)")
st.caption(f"Gestión de Clientes y Accesos | App: {LINK_APP}")

# --- LÓGICA DE DIRECTORIOS ---
path_clientes = "instancias_clientes"
if not os.path.exists(path_clientes):
    os.makedirs(path_clientes)

# Detectar clientes existentes
clientes_existentes = [f for f in os.listdir(path_clientes) if os.path.isdir(os.path.join(path_clientes, f)) and "__" not in f]
clientes_existentes.sort()

# --- PESTAÑAS ---
tab_clientes, tab_usuarios = st.tabs(["🏭 Nuevo Cliente", "👥 Gestión de Usuarios"])

# ==========================================
# PESTAÑA 1: CREAR NUEVO CLIENTE
# ==========================================
with tab_clientes:
    st.header("Alta de Negocio (Tenant)")
    
    with st.form("new_client"):
        c_name = st.text_input("Nombre Fantasía (Ej: Ferretería Pepe)")
        c_id = st.text_input("ID Carpeta (sin espacios, ej: ferreteria_pepe)").lower().strip()
        
        if st.form_submit_button("Crear Cliente"):
            if c_id and c_name:
                ruta = os.path.join(path_clientes, c_id)
                if os.path.exists(ruta):
                    st.error("¡Esa carpeta ya existe!")
                else:
                    os.makedirs(ruta)
                    
                    # 1. Crear Ventas
                    with open(os.path.join(ruta, "1_ventas.py"), "w", encoding="utf-8") as f:
                        f.write(f'import streamlit as st\nst.title("🛒 {c_name}")\nst.success("Sistema instalado.")')

                    # 2. Crear Admin Operativo
                    with open(os.path.join(ruta, "4_admin.py"), "w", encoding="utf-8") as f:
                        f.write(f'import streamlit as st\nst.title("⚙️ Admin {c_name}")\nst.write("Panel del cliente.")')
                    
                    st.success(f"✅ Cliente '{c_name}' creado en `{ruta}`")
                    st.rerun()
            else:
                st.warning("Completa todos los campos.")

# ==========================================
# PESTAÑA 2: GESTIÓN DE USUARIOS + DESHABILITAR
# ==========================================
with tab_usuarios:
    st.header("Control de Accesos")
    
    if not clientes_existentes:
        st.warning("No hay clientes creados.")
        st.stop()

    # 1. SELECCIONAR CLIENTE
    col_sel, col_info = st.columns([2, 1])
    with col_sel:
        cliente_sel = st.selectbox("Selecciona Cliente:", clientes_existentes)
    with col_info:
        collection_name = f"{cliente_sel}_usuarios"
        st.info(f"📂 Base de Datos: `{collection_name}`")

    ref_users = db.collection(collection_name)
    docs = list(ref_users.stream())

    col_list, col_create = st.columns([1.5, 1])

    # --- A. LISTA DE USUARIOS (CON INTERRUPTOR) ---
    with col_list:
        st.subheader("📋 Usuarios Activos")
        if not docs:
            st.caption("No hay usuarios. Crea uno a la derecha 👉")
        
        for doc in docs:
            data = doc.to_dict()
            uid = doc.id
            is_active = data.get('activo', True) # Si no tiene el campo, asumimos True
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1.5, 0.5])
                
                # Datos
                c1.markdown(f"**{uid}**")
                c1.caption(f"Clave: `{data.get('pass')}` | Rol: {data.get('rol')}")
                
                # --- AQUÍ ESTÁ LA MAGIA: EL INTERRUPTOR ---
                # Usamos key única para que no se mezclen
                nuevo_estado = c2.toggle("Habilitado", value=is_active, key=f"toggle_{cliente_sel}_{uid}")
                
                # Si cambiaste el interruptor, guardamos en Firebase al instante
                if nuevo_estado != is_active:
                    ref_users.document(uid).update({"activo": nuevo_estado})
                    st.toast(f"Estado de {uid} actualizado!")
                    st.rerun() # Recargamos para confirmar visualmente
                
                # Botón Borrar
                if c3.button("🗑️", key=f"del_{uid}"):
                    ref_users.document(uid).delete()
                    st.rerun()

                # Generador de Invitación WhatsApp
                with st.expander(f"💬 Link de invitación para {uid}"):
                    link_magico = f"{LINK_APP}/?cliente={cliente_sel}"
                    mensaje = f"🚀 *Hola {uid}*\n\n🔗 *Entra aquí:* {link_magico}\n\n👤 Usuario: {uid}\n🔑 Clave: {data.get('pass')}"
                    st.text_area("Copiar:", value=mensaje, height=150, key=f"msg_{uid}")

    # --- B. CREAR NUEVO USUARIO ---
    with col_create:
        st.subheader("➕ Nuevo Usuario")
        with st.form("add_user_final"):
            u_user = st.text_input("Usuario")
            u_pass = st.text_input("Contraseña")
            u_rol = st.selectbox("Rol", ["vendedor", "admin"])
            
            if st.form_submit_button("Guardar Usuario"):
                if u_user and u_pass:
                    ref_users.document(u_user).set({
                        "pass": u_pass,
                        "rol": u_rol,
                        "activo": True  # Nace activo por defecto
                    })
                    st.success(f"Creado: {u_user}")
                    st.rerun()
                else:
                    st.error("Faltan datos.")