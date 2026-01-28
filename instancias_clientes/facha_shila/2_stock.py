import streamlit as st
import os
import sys
import time

# --- CONEXIÓN CON CONFIG.PY (RAÍZ) ---
# Esta lógica permite que el archivo encuentre config.py aunque esté 2 carpetas arriba
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except ImportError:
    st.error("❌ No se pudo conectar con la base de datos central. Verifica la ubicación de config.py")
    st.stop()

# --- CONFIGURACIÓN DE PRIVACIDAD ---
# El nombre de la colección será, por ejemplo: 'facha_y_shila_productos'
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title=f"Stock - {cliente_id.replace('_', ' ').title()}", layout="wide")

st.markdown("""
    <style>
    .low-stock { color: #ff4b4b; font-weight: bold; }
    .ok-stock { color: #2ecc71; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📦 Inventario: {cliente_id.replace('_', ' ').title()}")

tab_ver, tab_carga = st.tabs(["🔍 Ver y Reponer Stock", "➕ Cargar Nuevo Modelo"])

# ==========================================
# PESTAÑA 1: VISUALIZACIÓN Y REPOSICIÓN
# ==========================================
with tab_ver:
    c1, c2 = st.columns([2, 1])
    search_query = c1.text_input("🔍 Buscar modelo o marca...", placeholder="Ej: Remera Batik")
    cat_filter = c2.selectbox("Categoría:", ["Todas", "Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
    
    try:
        query = db.collection(COLECCION_PRODUCTOS)
        if cat_filter != "Todas":
            query = query.where("categoria", "==", cat_filter)
        
        docs = list(query.stream())
        
        if not docs:
            st.info("No hay productos registrados aún.")
        else:
            for doc in docs:
                p = doc.to_dict()
                p_id = doc.id
                det = p.get('detalles', {})

                if search_query.lower() in p['modelo'].lower() or search_query.lower() in p.get('marca', '').lower():
                    with st.container(border=True):
                        col_info, col_valores, col_reponer = st.columns([2, 1, 1])
                        
                        with col_info:
                            st.markdown(f"#### {p['modelo']}")
                            st.caption(f"Marca: {p.get('marca', 'S/M')} | {p['categoria']}")
                            if p['categoria'] == "Ropa":
                                st.write(f"🎨 {det.get('color')} | 📏 {', '.join(det.get('talles', []))}")
                            elif p['categoria'] == "Accesorios (Joyas)":
                                st.write(f"💎 {det.get('tipo')} de {det.get('material')} | {det.get('medida_extra', '')}")
                            elif p['categoria'] == "Cosmética / Belleza":
                                st.write(f"💄 {det.get('tipo')} | Tono/Var: {det.get('variedad', 'N/A')}")
                        
                        with col_valores:
                            st.write(f"**Precio:** ${p['precio_venta']:,.2f}")
                            stock_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
                            stock_actual = det.get(stock_key, 0)
                            
                            if stock_actual <= 3:
                                st.markdown(f"**Stock:** <span class='low-stock'>{stock_actual} unid.</span> ⚠️", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**Stock:** <span class='ok-stock'>{stock_actual} unid.</span>", unsafe_allow_html=True)

                        with col_reponer:
                            sumar = st.number_input("Sumar:", min_value=0, step=1, key=f"add_{p_id}")
                            if st.button(f"Actualizar", key=f"btn_{p_id}"):
                                db.collection(COLECCION_PRODUCTOS).document(p_id).update({
                                    f"detalles.{stock_key}": stock_actual + sumar
                                })
                                st.toast(f"✅ Stock actualizado")
                                time.sleep(0.5)
                                st.rerun()
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

# ==========================================
# PESTAÑA 2: CARGA DINÁMICA
# ==========================================
with tab_carga:
    with st.form("nuevo_producto", clear_on_submit=True):
        st.subheader("📌 Datos Principales")
        c_p1, c_p2 = st.columns(2)
        modelo = c_p1.text_input("Modelo / Nombre")
        marca = c_p2.text_input("Marca / Proveedor")

        c_f1, c_f2, c_f3 = st.columns(3)
        costo = c_f1.number_input("Costo ($)", min_value=0.0)
        precio_v = c_f2.number_input("Precio Venta ($)", min_value=0.0)
        ganancia = precio_v - costo
        c_f3.metric("Ganancia", f"${ganancia:,.2f}")

        st.divider()
        cat_new = st.selectbox("Categoría:", ["Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
        detalles = {}

        if cat_new == "Ropa":
            col_r1, col_r2 = st.columns(2)
            talles = col_r1.multiselect("Talles", ["S", "M", "L", "XL", "XXL", "Único"])
            color = col_r2.text_input("Color")
            stock_i = st.number_input("Stock inicial", min_value=1)
            detalles = {"talles": talles, "color": color, "stock_por_talle": stock_i}

        elif cat_new == "Accesorios (Joyas)":
            tipo_acc = st.radio("Tipo:", ["Collar", "Anillo", "Pulsera", "Aritos"], horizontal=True)
            mat = st.selectbox("Material", ["Acero Quirúrgico", "Plata 925", "Oro", "Fantasía"])
            extra_inf = st.text_input("Largo / Talle (opcional)")
            stock_a = st.number_input("Cantidad inicial", min_value=1)
            detalles = {"tipo": tipo_acc, "material": mat, "medida_extra": extra_inf, "stock": stock_a}

        elif cat_new == "Cosmética / Belleza":
            tipo_cos = st.radio("Producto:", ["Labial", "Mascarilla", "Esmalte", "Otro"], horizontal=True)
            tono = st.text_input("Tono / Variedad")
            stock_c = st.number_input("Cantidad inicial", min_value=1)
            detalles = {"tipo": tipo_cos, "variedad": tono, "stock": stock_c}

        if st.form_submit_button("🚀 GUARDAR EN MI STOCK"):
            if modelo and precio_v > 0:
                p_id = f"{cat_new[:3].upper()}-{modelo.replace(' ', '_').lower()}-{int(time.time())}"
                payload = {
                    "modelo": modelo, "marca": marca, "categoria": cat_new,
                    "costo": costo, "precio_venta": precio_v, "ganancia": ganancia,
                    "detalles": detalles, "fecha": time.strftime("%Y-%m-%d")
                }
                db.collection(COLECCION_PRODUCTOS).document(p_id).set(payload)
                st.success(f"Registrado con éxito!")
                st.rerun()
            else:
                st.warning("El modelo y el precio son obligatorios.")