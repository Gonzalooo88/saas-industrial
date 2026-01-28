import streamlit as st
from config import db
import time
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Stock Facha y Shila", layout="wide")

# Estilos personalizados para alertas de stock bajo
st.markdown("""
    <style>
    .low-stock { color: #ff4b4b; font-weight: bold; }
    .ok-stock { color: #00ff00; }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 Gestión de Inventario")

# --- PESTAÑAS: BUSCADOR vs CARGA ---
tab_ver, tab_carga = st.tabs(["🔍 Ver y Reponer Stock", "➕ Cargar Nuevo Modelo"])

# ==========================================
# PESTAÑA 1: VISUALIZACIÓN, FILTROS Y REPOSICIÓN
# ==========================================
with tab_ver:
    st.subheader("Buscador y Filtros")
    
    # Fila de filtros
    c1, c2, c3 = st.columns([2, 1, 1])
    search_query = c1.text_input("Buscar por modelo o marca...", placeholder="Ej: Remera Batik")
    cat_filter = c2.selectbox("Filtrar Categoría:", ["Todas", "Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
    orden = c3.selectbox("Ordenar por:", ["Más nuevo", "Precio (Menor a Mayor)", "Ganancia"])

    # --- LÓGICA DE FIREBASE PARA OBTENER PRODUCTOS ---
    try:
        query = db.collection("productos")
        # Aplicar filtro de categoría si no es "Todas"
        if cat_filter != "Todas":
            query = query.where("categoria", "==", cat_filter)
        
        docs = list(query.stream())
        
        if not docs:
            st.info("No hay productos registrados aún.")
        else:
            productos_data = []
            for doc in docs:
                p = doc.to_dict()
                p['id'] = doc.id
                # Búsqueda simple por texto
                if search_query.lower() in p['modelo'].lower() or search_query.lower() in p.get('marca', '').lower():
                    productos_data.append(p)

            # --- RENDERIZADO DE LA TABLA ---
            for prod in productos_data:
                det = prod.get('detalles', {})
                with st.container(border=True):
                    col_info, col_stock, col_reponer = st.columns([2, 1, 1])
                    
                    with col_info:
                        st.markdown(f"#### {prod['modelo']}")
                        st.caption(f"Categoría: {prod['categoria']} | Marca: {prod.get('marca', 'S/M')}")
                        # Mostrar detalles según tipo
                        if prod['categoria'] == "Ropa":
                            st.write(f"🎨 Color: {det.get('color')} | 📏 Talles: {', '.join(det.get('talles', []))}")
                        elif prod['categoria'] == "Accesorios (Joyas)":
                            st.write(f"💎 {det.get('tipo')} de {det.get('material')} {det.get('medida_extra', '')}")
                        
                    with col_stock:
                        # Lógica de stock actual
                        actual = det.get('stock', det.get('stock_por_talle', 0))
                        st.write(f"**Precio:** ${prod['precio_venta']:,.2f}")
                        if actual <= 3:
                            st.markdown(f"**Stock:** <span class='low-stock'>{actual} unid.</span> (Bajo)", unsafe_allow_html=True)
                        else:
                            st.write(f"**Stock:** {actual} unidades")

                    with col_reponer:
                        # BOTÓN DE REPOSICIÓN RÁPIDA
                        new_qty = st.number_input("Sumar stock:", min_value=0, step=1, key=f"add_{prod['id']}")
                        if st.button(f"Reponer {prod['modelo'][:10]}...", key=f"btn_{prod['id']}"):
                            # Actualizar en Firebase
                            ref = db.collection("productos").document(prod['id'])
                            # Detectamos qué campo de stock usa
                            stock_key = 'stock_por_talle' if prod['categoria'] == "Ropa" else 'stock'
                            ref.update({f"detalles.{stock_key}": actual + new_qty})
                            st.toast(f"✅ Stock actualizado para {prod['modelo']}")
                            time.sleep(1)
                            st.rerun()

    except Exception as e:
        st.error(f"Error al cargar stock: {e}")

# ==========================================
# PESTAÑA 2: CARGAR NUEVO MODELO (Lógica anterior)
# ==========================================
with tab_carga:
    with st.form("registro_stock", clear_on_submit=True):
        st.subheader("📌 Información Básica")
        
        col_1, col_2 = st.columns(2)
        modelo = col_1.text_input("Modelo / Nombre del artículo")
        marca = col_2.text_input("Marca / Proveedor (Opcional)")

        c_f1, c_f2, c_f3 = st.columns(3)
        costo = c_f1.number_input("Costo unitario ($)", min_value=0.0, step=50.0)
        precio_venta = c_f2.number_input("Precio de venta ($)", min_value=0.0, step=50.0)
        
        ganancia = precio_venta - costo
        c_f3.metric("Margen", f"${ganancia:,.2f}")

        st.divider()

        detalles_especificos = {}
        # Usamos la categoría seleccionada fuera del form o una nueva aquí
        cat_nueva = st.selectbox("Categoría:", ["Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"], key="cat_new")

        if cat_nueva == "Ropa":
            col_r1, col_r2 = st.columns(2)
            talles = col_r1.multiselect("Talles", ["S", "M", "L", "XL", "XXL", "Único"])
            color = col_r2.text_input("Color")
            stock_inicial = st.number_input("Cant. inicial", min_value=1)
            detalles_especificos = {"talles": talles, "color": color, "stock_por_talle": stock_inicial}

        elif cat_nueva == "Accesorios (Joyas)":
            tipo_acc = st.radio("Tipo:", ["Collar", "Anillo", "Pulsera", "Aritos"], horizontal=True)
            material = st.selectbox("Material", ["Acero Quirúrgico", "Plata 925", "Oro", "Fantasía"])
            stock_acc = st.number_input("Cantidad total", min_value=1)
            extra = st.text_input("Medida / Talle (opcional)")
            detalles_especificos = {"tipo": tipo_acc, "material": material, "stock": stock_acc, "medida_extra": extra}

        elif cat_nueva == "Cosmética / Belleza":
            tipo_cosm = st.radio("Producto:", ["Labial", "Mascarilla", "Esmalte"], horizontal=True)
            variedad = st.text_input("Tono / Variedad")
            stock_cosm = st.number_input("Cantidad total", min_value=1)
            detalles_especificos = {"tipo": tipo_cosm, "variedad": variedad, "stock": stock_cosm}

        if st.form_submit_button("🔥 REGISTRAR EN STOCK"):
            if modelo and precio_venta > 0:
                prod_id = f"{cat_nueva[:3].upper()}-{modelo.replace(' ', '_').lower()}-{int(time.time())}"
                payload = {
                    "modelo": modelo, "marca": marca, "categoria": cat_nueva,
                    "costo": costo, "precio_venta": precio_venta, "ganancia": ganancia,
                    "detalles": detalles_especificos, "fecha_ingreso": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                db.collection("productos").document(prod_id).set(payload)
                st.success("¡Producto cargado!")
                st.rerun()