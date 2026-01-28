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

st.set_page_config(page_title="Stock - Facha y Shila", layout="wide")

tab_ver, tab_carga = st.tabs(["🔍 Ver y Reponer Stock", "➕ Cargar Nuevo Modelo"])

# ==========================================
# TAB 1: VER Y REPONER
# ==========================================
with tab_ver:
    docs = db.collection(COLECCION_PRODUCTOS).stream()
    for doc in docs:
        p = doc.to_dict()
        p_id = doc.id
        det = p.get('detalles', {})
        with st.container(border=True):
            c1, c2, c3 = st.columns([2,1,1])
            c1.markdown(f"#### {p['modelo']}")
            
            s_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
            actual = det.get(s_key, 0)
            c2.write(f"Stock: {actual}")
            
            sumar = c3.number_input("Sumar", min_value=0, step=1, key=f"s_{p_id}")
            if c3.button("Reponer", key=f"b_{p_id}"):
                batch = db.batch()
                batch.update(db.collection(COLECCION_PRODUCTOS).document(p_id), {f"detalles.{s_key}": actual + sumar})
                mov_id = f"REP-{int(time.time())}"
                batch.set(db.collection(COLECCION_MOVIMIENTOS).document(mov_id), {
                    "tipo": "Reposición",
                    "monto": 0,
                    "ganancia": 0,
                    "productos": [f"{p['modelo']} (+{sumar})"],
                    "fecha": datetime.now()
                })
                batch.commit()
                st.rerun()

# ==========================================
# TAB 2: CARGA (GANANCIA EN TIEMPO REAL)
# ==========================================
with tab_carga:
    with st.form("nuevo_p"):
        modelo = st.text_input("Modelo")
        costo = st.number_input("Costo ($)", min_value=0.0)
        precio_v = st.number_input("Venta ($)", min_value=0.0)
        
        # Ganancia en tiempo real
        st.metric("Margen esperado", f"${precio_v - costo:.2f}")
        
        cat = st.selectbox("Categoría", ["Ropa", "Accesorios (Joyas)", "Cosmética / Belleza"])
        
        if st.form_submit_button("Guardar"):
            p_id = f"PROD-{int(time.time())}"
            db.collection(COLECCION_PRODUCTOS).document(p_id).set({
                "modelo": modelo, "costo": costo, "precio_venta": precio_v,
                "categoria": cat, "detalles": {"stock": 1, "stock_por_talle": 1} # simplificado
            })
            st.success("Guardado")