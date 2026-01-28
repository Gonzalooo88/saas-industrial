import streamlit as st
import os
import sys
import time
from datetime import datetime

# --- CONEXIÓN CON CONFIG.PY (RAÍZ) ---
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- CONFIGURACIÓN DE PRIVACIDAD ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

st.set_page_config(page_title="Stock Detallado", layout="wide")

# Estilos para las tarjetas
st.markdown("""
    <style>
    .card-container { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 10px; background-color: #f9f9f9; }
    .label-bold { font-weight: bold; color: #333; }
    .price-tag { color: #2ecc71; font-weight: bold; font-size: 1.1em; }
    .profit-tag { color: #3498db; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 Inventario Detallado")

tab_ver, tab_carga = st.tabs(["🔍 Visualizar Stock", "➕ Cargar Nuevo Modelo"])

# ==========================================
# TAB 1: VISUALIZACIÓN DETALLADA POR TARJETA
# ==========================================
with tab_ver:
    st.subheader("Listado de Modelos")
    docs = db.collection(COLECCION_PRODUCTOS).stream()
    
    for doc in docs:
        p = doc.to_dict()
        p_id = doc.id
        det = p.get('detalles', {})
        
        # Tarjeta de Modelo
        with st.container(border=True):
            col_main, col_stats, col_repo = st.columns([2, 1, 1])
            
            with col_main:
                st.markdown(f"### {p['modelo']}")
                st.caption(f"Categoría: {p['categoria']} | Marca: {p.get('marca', 'S/M')}")
                
                # Detalle de Variantes
                if p['categoria'] == "Ropa":
                    st.markdown(f"<span class='label-bold'>🎨 Color:</span> {det.get('color', 'N/A')}", unsafe_allow_html=True)
                    st.markdown(f"<span class='label-bold'>📏 Talles en Stock:</span> {', '.join(det.get('talles', []))}", unsafe_allow_html=True)
                elif p['categoria'] == "Accesorios (Joyas)":
                    st.markdown(f"<span class='label-bold'>💎 Material:</span> {det.get('material', 'N/A')}", unsafe_allow_html=True)
                    if det.get('medida_extra'): st.write(f"📏 Medida: {det['medida_extra']}")
            
            with col_stats:
                st.markdown(f"<span class='label-bold'>💰 Venta:</span> <span class='price-tag'>${p['precio_venta']:,.2f}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='label-bold'>📈 Ganancia:</span> <span class='profit-tag'>${p['ganancia']:,.2f}</span>", unsafe_allow_html=True)
                
                stock_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
                actual = det.get(stock_key, 0)
                st.write(f"**Total Unidades:** {actual}")

            with col_repo:
                sumar = st.number_input("Añadir unidades", min_value=0, step=1, key=f"s_{p_id}")
                if st.button("Actualizar Stock", key=f"b_{p_id}", use_container_width=True):
                    if sumar > 0:
                        batch = db.batch()
                        batch.update(db.collection(COLECCION_PRODUCTOS).document(p_id), {f"detalles.{stock_key}": actual + sumar})
                        
                        # Registrar el movimiento
                        mov_id = f"REP-{int(time.time())}"
                        batch.set(db.collection(COLECCION_MOVIMIENTOS).document(mov_id), {
                            "tipo": "Reposición",
                            "monto": 0,
                            "ganancia": 0,
                            "productos": [f"{p['modelo']} (+{sumar})"],
                            "fecha": datetime.now()
                        })
                        batch.commit()
                        st.success(f"Stock de {p['modelo']} actualizado")
                        time.sleep(0.5)
                        st.rerun()

# ==========================================
# TAB 2: CARGA (CON CÁLCULOS DINÁMICOS)
# ==========================================
with tab_carga:
    with st.form("nuevo_p_detalle", clear_on_submit=True):
        st.subheader("📌 Datos del Nuevo Modelo")
        
        c1, c2 = st.columns(2)
        modelo_n = c1.text_input("Nombre del Modelo")
        marca_n = c2.text_input("Marca")
        
        f1, f2 = st.columns(2)
        costo_n = f1.number_input("Costo Unitario ($)", min_value=0.0, format="%.2f")
        precio_n = f2.number_input("Precio Venta ($)", min_value=0.0, format="%.2f")
        
        # Ganancia en tiempo real dentro del form
        ganancia_n = precio_n - costo_n
        st.metric("Ganancia por unidad", f"${ganancia_n:,.2f}")
        
        st.divider()
        cat_n = st.selectbox("Categoría", ["Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
        
        detalles_n = {}
        if cat_n == "Ropa":
            r1, r2 = st.columns(2)
            talles_n = r1.multiselect("Talles", ["S", "M", "L", "XL", "Único"])
            color_n = r2.text_input("Color")
            stock_n = st.number_input("Stock Inicial", min_value=1)
            detalles_n = {"talles": talles_n, "color": color_n, "stock_por_talle": stock_n}
        elif cat_n == "Accesorios (Joyas)":
            a1, a2 = st.columns(2)
            tipo_a = a1.selectbox("Tipo", ["Collar", "Anillo", "Pulsera", "Aritos"])
            material_a = a2.selectbox("Material", ["Plata 925", "Acero Quirúrgico", "Oro", "Fantasía"])
            medida_a = st.text_input("Largo / Medida")
            stock_a = st.number_input("Stock Inicial", min_value=1)
            detalles_n = {"tipo": tipo_a, "material": material_a, "medida_extra": medida_a, "stock": stock_a}
        # ... (puedes añadir más elif para cosmética)

        if st.form_submit_button("🔥 GUARDAR MODELO"):
            if modelo_n and precio_n > 0:
                p_id_n = f"PROD-{int(time.time())}"
                db.collection(COLECCION_PRODUCTOS).document(p_id_n).set({
                    "modelo": modelo_n,
                    "marca": marca_n,
                    "costo": costo_n,
                    "precio_venta": precio_n,
                    "ganancia": ganancia_n,
                    "categoria": cat_n,
                    "detalles": detalles_n,
                    "fecha_carga": datetime.now()
                })
                st.success(f"Modelo '{modelo_n}' guardado con éxito.")
                st.rerun()