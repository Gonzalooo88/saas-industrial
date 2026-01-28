import streamlit as st
import os
import sys
import time
import pandas as pd

# --- CONEXIÓN CON CONFIG.PY (RAÍZ) ---
# Subimos niveles para encontrar la raíz desde instancias_clientes/cliente/
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except ImportError:
    st.error("❌ No se pudo conectar con la base de datos central. Revisa la ubicación de config.py")
    st.stop()

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Stock Facha y Shila", layout="wide")

# Estilos para alertas de stock
st.markdown("""
    <style>
    .low-stock { color: #ff4b4b; font-weight: bold; }
    .ok-stock { color: #2ecc71; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 Gestión de Inventario")

# --- PESTAÑAS ---
tab_ver, tab_carga = st.tabs(["🔍 Ver y Reponer Stock", "➕ Cargar Nuevo Modelo"])

# ==========================================
# PESTAÑA 1: VISUALIZACIÓN Y REPOSICIÓN
# ==========================================
with tab_ver:
    st.subheader("Control de Mercadería")
    
    # Buscador y Filtros
    c1, c2, c3 = st.columns([2, 1, 1])
    search_query = c1.text_input("🔍 Buscar por modelo o marca...", placeholder="Ej: Remera Batik")
    cat_filter = c2.selectbox("Filtrar Categoría:", ["Todas", "Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
    
    try:
        # Obtenemos productos de Firebase
        query = db.collection("productos")
        if cat_filter != "Todas":
            query = query.where("categoria", "==", cat_filter)
        
        docs = list(query.stream())
        
        if not docs:
            st.info("No hay productos registrados en esta categoría.")
        else:
            for doc in docs:
                p = doc.to_dict()
                p_id = doc.id
                det = p.get('detalles', {})

                # Filtrado por texto (Buscador)
                if search_query.lower() in p['modelo'].lower() or search_query.lower() in p.get('marca', '').lower():
                    with st.container(border=True):
                        col_info, col_valores, col_reponer = st.columns([2, 1, 1])
                        
                        with col_info:
                            st.markdown(f"#### {p['modelo']}")
                            st.caption(f"Marca: {p.get('marca', 'S/M')} | {p['categoria']}")
                            # Detalles específicos según tipo
                            if p['categoria'] == "Ropa":
                                st.write(f"🎨 {det.get('color')} | 📏 {', '.join(det.get('talles', []))}")
                            elif p['categoria'] == "Accesorios (Joyas)":
                                st.write(f"💎 {det.get('tipo')} de {det.get('material')} | {det.get('medida_extra', '')}")
                            elif p['categoria'] == "Cosmética / Belleza":
                                st.write(f"💄 {det.get('tipo')} | Tono: {det.get('variedad', 'N/A')}")
                        
                        with col_valores:
                            st.write(f"**Venta:** ${p['precio_venta']:,.2f}")
                            # Detectar qué campo de stock usar
                            stock_actual = det.get('stock', det.get('stock_por_talle', 0))
                            if stock_actual <= 3:
                                st.markdown(f"**Stock:** <span class='low-stock'>{stock_actual} unid.</span> ⚠️", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**Stock:** <span class='ok-stock'>{stock_actual} unid.</span>", unsafe_allow_html=True)

                        with col_reponer:
                            # Reposición rápida
                            sumar = st.number_input("Sumar stock:", min_value=0, step=1, key=f"add_{p_id}")
                            if st.button(f"Reponer", key=f"btn_{p_id}"):
                                stock_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
                                db.collection("productos").document(p_id).update({
                                    f"detalles.{stock_key}": stock_actual + sumar
                                })
                                st.toast(f"✅ Stock actualizado: {p['modelo']}")
                                time.sleep(1)
                                st.rerun()
    except Exception as e:
        st.error(f"Error al cargar: {e}")

# ==========================================
# PESTAÑA 2: CARGA DINÁMICA
# ==========================================
with tab_carga:
    with st.form("nuevo_producto", clear_on_submit=True):
        st.subheader("📌 Datos Principales")
        
        c_p1, c_p2 = st.columns(2)
        modelo = c_p1.text_input("Modelo / Nombre del artículo")
        marca = c_p2.text_input("Marca / Proveedor")

        c_f1, c_f2, c_f3 = st.columns(3)
        costo = c_f1.number_input("Costo unitario ($)", min_value=0.0)
        precio_v = c_f2.number_input("Precio Venta ($)", min_value=0.0)
        ganancia = precio_v - costo
        c_f3.metric("Ganancia", f"${ganancia:,.2f}")

        st.divider()
        
        cat_new = st.selectbox("Categoría de Producto:", ["Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
        detalles = {}

        if cat_new == "Ropa":
            col_r1, col_r2 = st.columns(2)
            talles = col_r1.multiselect("Talles", ["S", "M", "L", "XL", "XXL", "Único"])
            color = col_r2.text_input("Color/Estampado")
            stock_i = st.number_input("Stock inicial por talle", min_value=1)
            detalles = {"talles": talles, "color": color, "stock_por_talle": stock_i}

        elif cat_new == "Accesorios (Joyas)":
            tipo_acc = st.radio("Tipo:", ["Collar", "Anillo", "Pulsera", "Aritos"], horizontal=True)
            mat = st.selectbox("Material", ["Acero Quirúrgico", "Plata 925", "Oro", "Fantasía"])
            extra_inf = st.text_input("Largo / Talle de anillo (opcional)")
            stock_a = st.number_input("Cantidad total inicial", min_value=1)
            detalles = {"tipo": tipo_acc, "material": mat, "medida_extra": extra_inf, "stock": stock_a}

        elif cat_new == "Cosmética / Belleza":
            tipo_cos = st.radio("Producto:", ["Labial", "Mascarilla", "Esmalte", "Otro"], horizontal=True)
            tono = st.text_input("Tono / Número / Variedad")
            stock_c = st.number_input("Cantidad total inicial", min_value=1)
            detalles = {"tipo": tipo_cos, "variedad": tono, "stock": stock_c}

        if st.form_submit_button("🔥 REGISTRAR PRODUCTO"):
            if modelo and precio_v > 0:
                p_id = f"{cat_new[:3].upper()}-{modelo.replace(' ', '_').lower()}-{int(time.time())}"
                payload = {
                    "modelo": modelo, "marca": marca, "categoria": cat_new,
                    "costo": costo, "precio_venta": precio_v, "ganancia": ganancia,
                    "detalles": detalles, "fecha": time.strftime("%Y-%m-%d")
                }
                db.collection("productos").document(p_id).set(payload)
                st.success(f"Guardado: {modelo}")
                st.rerun()
            else:
                st.warning("Completa modelo y precio.")