import streamlit as st
import os
from config import db  # <--- Conexión centralizada

# --- CONFIGURACIÓN DE PÁGINA ---
# Título genérico en la pestaña del navegador
st.set_page_config(page_title="Portal de Gestión", layout="wide", page_icon="🏢")

# --- GESTIÓN DE ESTADO ---
if 'password_correct' not in st.session_state:
    st.session_state.password_correct = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'empresa_id' not in st.session_state:
    st.session_state.empresa_id = None # Guardamos qué empresa eligió

# --- DETECTAR CLIENTES DISPONIBLES ---
def obtener_empresas():
    """Escanea la carpeta 'instancias_clientes' para ver qué empresas existen."""
    ruta = "instancias_clientes"
    if not os.path.exists(ruta):
        return []
    # Busca carpetas que no sean archivos ocultos ni __pycache__
    empresas = [f for f in os.listdir(ruta) if os.path.isdir(os.path.join(ruta, f)) and "__" not in f]
    return sorted(empresas)

# --- PANTALLA DE LOGIN GENÉRICA ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Portal de Acceso Clientes")
        st.caption("Seleccione su empresa para ingresar al sistema.")
        
        empresas_disponibles = obtener_empresas()
        
        with st.form("login_form"):
            # 1. SELECTOR DE EMPRESA
            # Creamos un diccionario para mostrar nombres bonitos
            # ej: "facha_shila" -> "Facha Shila"
            mapa_nombres = {e: e.replace("_", " ").title() for e in empresas_disponibles}
            empresa_seleccionada = st.selectbox(
                "🏢 Empresa / Negocio", 
                options=["Seleccionar..."] + list(mapa_nombres.values())
            )
            
            st.divider()
            
            # 2. CREDENCIALES
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            submit = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
            if submit:
                # Validaciones básicas
                if empresa_seleccionada == "Seleccionar...":
                    st.warning("⚠️ Por favor selecciona tu empresa.")
                    return
                if not usuario or not password:
                    st.warning("⚠️ Completa usuario y contraseña.")
                    return

                # Recuperar el ID de la carpeta (ej: "Facha Shila" -> "facha_shila")
                # Invertimos el diccionario para buscar la key por el value
                empresa_id = [k for k, v in mapa_nombres.items() if v == empresa_seleccionada][0]

                # Construir nombre de colección: "facha_shila_usuarios"
                collection_name = f"{empresa_id}_usuarios"
                
                # --- VALIDACIÓN EN BASE DE DATOS ---
                doc_ref = db.collection(collection_name).document(usuario)
                doc = doc_ref.get()

                if doc.exists:
                    data = doc.to_dict()
                    
                    # A. Verificar si está ACTIVO
                    if not data.get('activo', True):
                        st.error("🚫 Usuario deshabilitado. Contacte a soporte.")
                        return

                    # B. Verificar CONTRASEÑA
                    if data.get('pass') == password:
                        st.session_state.password_correct = True
                        st.session_state.usuario = usuario
                        st.session_state.rol = data.get('rol', 'vendedor')
                        st.session_state.empresa_id = empresa_id # <--- CLAVE: Guardamos dónde estamos
                        st.toast(f"Bienvenido a {empresa_seleccionada}", icon="🚀")
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta.")
                else:
                    st.error("❌ Usuario no encontrado en esta empresa.")

# --- FUNCIÓN DE LOGOUT ---
def logout():
    st.session_state.password_correct = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.empresa_id = None
    st.rerun()

# --- CEREBRO DE NAVEGACIÓN ---
if not st.session_state.password_correct:
    pg = st.navigation([st.Page(login_screen, title="Acceso")])
    pg.run()

else:
    # --- USUARIO LOGUEADO: CARGAR APP ESPECÍFICA ---
    
    # Usamos la empresa_id guardada para saber qué carpeta leer
    # Ej: instancias_clientes/ferreteria_pepe
    empresa_actual = st.session_state.empresa_id
    path_cliente = os.path.join("instancias_clientes", empresa_actual)
    
    paginas = []
    
    if os.path.exists(path_cliente):
        archivos = [f for f in os.listdir(path_cliente) if f.endswith(".py") and "__" not in f]
        
        for archivo in archivos:
            ruta_archivo = os.path.join(path_cliente, archivo)
            # Nombre menú: "1_ventas.py" -> "Ventas"
            nombre_menu = archivo.replace(".py", "").replace("_", " ").title()
            
            # FILTRO DE SEGURIDAD VISUAL (Opcional)
            # Si el usuario es vendedor, y el archivo dice "Admin", podríamos ocultarlo
            # Pero por ahora lo dejamos simple. Tu admin interno ya tiene contraseña o bloqueo.
            
            paginas.append(st.Page(ruta_archivo, title=nombre_menu))
            
        paginas.sort(key=lambda x: x.title)
        
    else:
        st.error(f"⚠️ Error Crítico: No se encuentra la carpeta de la empresa '{empresa_actual}'.")

    # --- EJECUCIÓN FINAL ---
    if paginas:
        pg = st.navigation(paginas)
        
        with st.sidebar:
            st.subheader(f"🏢 {empresa_actual.replace('_', ' ').title()}")
            st.divider()
            st.write(f"👤 **{st.session_state.usuario}**")
            st.caption(f"Rol: {st.session_state.rol}")
            
            if st.button("Cerrar Sesión", type="primary", use_container_width=True):
                logout()
                
        pg.run()
    else:
        st.warning("No hay módulos disponibles para esta empresa.")
