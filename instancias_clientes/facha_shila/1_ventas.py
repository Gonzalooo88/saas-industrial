import streamlit as st
import os
import sys
import time
from datetime import datetime

# --- CONEXIÓN CON CONFIG.PY ---
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

st.set_page_config(page_title="Ventas - Facha y Shila", layout="wide")

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

st.title("💸 Punto de Venta")

col_busqueda, col_carrito = st.columns([1.2, 1])

with col_busqueda:
    st.subheader("🔍 Buscar Productos")
    busqueda = st.text_input("Modelo o marca...")
    
    if busqueda:
        docs = db.collection(COLECCION_PRODUCTOS).stream()
        for d in docs:
            p = d.to_dict()
            p['id'] = d.id
            if busqueda.lower() in p['modelo'].lower():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    stock_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
                    actual = p.get('detalles', {}).get(stock_key, 0)
                    
                    c1.write(f"**{p['modelo']}** | ${p['precio_venta']:.2f}")
                    if actual > 0:
                        t_sel = None
                        if p['categoria'] == "Ropa":
                            t_sel = c1.selectbox("Talle", p['detalles'].get('talles', []), key=f"v_{p['id']}")
                        if c2.button("➕", key=f"add_{p['id']}"):
                            st.session_state.carrito.append({
                                "id": p['id'], "modelo": p['modelo'], 
                                "precio": p['precio_venta'], "costo": p['costo'],
                                "categoria": p['categoria'], "talle": t_sel
                            })
                            st.rerun()
                    else:
                        c1.error("Sin stock")

with col_carrito:
    st.subheader("🛒 Carrito de Compra")
    if not st.session_state.carrito:
        st.info("Carrito vacío")
    else:
        total_v = sum(i['precio'] for i in st.session_state.carrito)
        costo_v = sum(i['costo'] for i in st.session_state.carrito)
        
        promo = st.toggle("✨ Modo Promo / Descuento")
        precio_final = st.number_input("Precio Final Cobrado", value=total_v) if promo else total_v
        
        ganancia = precio_final - costo_v
        st.metric("Ganancia de esta venta", f"${ganancia:.2f}")

        if st.button("🚀 CONFIRMAR VENTA", use_container_width=True):
            batch = db.batch()
            for item in st.session_state.carrito:
                p_ref = db.collection(COLECCION_PRODUCTOS).document(item['id'])
                p_doc = p_ref.get().to_dict()
                s_key = 'stock_por_talle' if item['categoria'] == "Ropa" else 'stock'
                batch.update(p_ref, {f"detalles.{s_key}": p_doc['detalles'][s_key] - 1})

            mov_id = f"VTA-{int(time.time())}"
            batch.set(db.collection(COLECCION_MOVIMIENTOS).document(mov_id), {
                "tipo": "Venta",
                "monto": precio_final,
                "ganancia": ganancia,
                "productos": [f"{i['modelo']} ({i.get('talle', 'N/A')})" for i in st.session_state.carrito],
                "fecha": datetime.now()
            })
            batch.commit()
            st.session_state.carrito = []
            st.success("✅ Venta registrada con éxito")
            time.sleep(1)
            st.rerun()