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
except ImportError:
    st.error("❌ No se pudo conectar con la base de datos central.")
    st.stop()

# --- CONFIGURACIÓN DE PRIVACIDAD ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_VENTAS = f"{cliente_id}_ventas"

st.set_page_config(page_title="Ventas - Facha y Shila", layout="wide")

# --- ESTADO DEL CARRITO ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

def agregar_al_carrito(producto, talle_seleccionado=None):
    item = {
        "id": producto['id'],
        "modelo": producto['modelo'],
        "precio_unitario": producto['precio_venta'],
        "costo_unitario": producto['costo'],
        "categoria": producto['categoria'],
        "talle": talle_seleccionado
    }
    st.session_state.carrito.append(item)
    st.toast(f"✅ Añadido: {producto['modelo']}")

# --- INTERFAZ ---
st.title("💸 Punto de Venta")

col_busqueda, col_carrito = st.columns([1.2, 1])

# ==========================================
# COLUMNA IZQUIERDA: BUSCADOR DE PRODUCTOS
# ==========================================
with col_busqueda:
    st.subheader("🔍 Buscar Productos")
    busqueda = st.text_input("Buscar por nombre...", placeholder="Ej: Remera")
    
    if busqueda:
        docs = db.collection(COLECCION_PRODUCTOS).stream()
        encontrados = []
        for d in docs:
            p = d.to_dict()
            p['id'] = d.id
            if busqueda.lower() in p['modelo'].lower():
                encontrados.append(p)
        
        for p in encontrados:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                stock_key = 'stock_por_talle' if p['categoria'] == "Ropa" else 'stock'
                stock_actual = p.get('detalles', {}).get(stock_key, 0)
                
                c1.markdown(f"**{p['modelo']}** (${p['precio_venta']:,.2f})")
                c1.caption(f"Stock disponible: {stock_actual}")
                
                if stock_actual > 0:
                    talle_sel = None
                    if p['categoria'] == "Ropa":
                        talle_sel = c1.selectbox(f"Talle para {p['modelo']}", p['detalles'].get('talles', []), key=f"talle_{p['id']}")
                    
                    if c2.button("➕ Añadir", key=f"btn_{p['id']}"):
                        agregar_al_carrito(p, talle_sel)
                else:
                    c2.error("Sin Stock")

# ==========================================
# COLUMNA DERECHA: CARRITO Y PROMOCIONES
# ==========================================
with col_carrito:
    st.subheader("🛒 Resumen de Venta")
    
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        total_original = sum(item['precio_unitario'] for item in st.session_state.carrito)
        costo_total = sum(item['costo_unitario'] for item in st.session_state.carrito)
        
        # --- SECCIÓN PROMO ---
        es_promo = st.toggle("✨ Activar Modo Promo")
        
        if es_promo:
            precio_final = st.number_input("Precio Final de la Promo ($)", min_value=0.0, value=total_original)
            st.warning(f"Precio original: ${total_original:,.2f}")
        else:
            precio_final = total_original
            st.write(f"### Total: ${precio_final:,.2f}")

        # Cálculo de Ganancia
        ganancia_venta = precio_final - costo_total
        color_ganancia = "green" if ganancia_venta > 0 else "red"
        st.markdown(f"**Ganancia de esta venta: <span style='color:{color_ganancia}'>${ganancia_venta:,.2f}</span>**", unsafe_allow_html=True)

        # Listado de productos en el carrito
        for i, item in enumerate(st.session_state.carrito):
            with st.expander(f"{item['modelo']} - {item.get('talle', '')}"):
                st.write(f"Precio base: ${item['precio_unitario']}")
                if st.button("❌ Quitar", key=f"remove_{i}"):
                    st.session_state.carrito.pop(i)
                    st.rerun()

        st.divider()

        # --- BOTÓN FINAL DE VENTA ---
        if st.button("🚀 CONFIRMAR VENTA Y DESCONTAR STOCK", use_container_width=True):
            try:
                batch = db.batch() # Usamos batch para que se haga todo o nada
                
                for item in st.session_state.carrito:
                    # 1. Referencia al producto
                    prod_ref = db.collection(COLECCION_PRODUCTOS).document(item['id'])
                    
                    # 2. Descontar stock (Lógica dinámica)
                    p_doc = prod_ref.get().to_dict()
                    stock_key = 'stock_por_talle' if item['categoria'] == "Ropa" else 'stock'
                    stock_actual = p_doc['detalles'][stock_key]
                    
                    batch.update(prod_ref, {f"detalles.{stock_key}": stock_actual - 1})

                # 3. Registrar la venta en el historial
                venta_id = f"VTA-{int(time.time())}"
                venta_data = {
                    "fecha": datetime.now(),
                    "productos": st.session_state.carrito,
                    "total_cobrado": precio_final,
                    "ganancia_total": ganancia_venta,
                    "es_promo": es_promo
                }
                batch.set(db.collection(COLECCION_VENTAS).document(venta_id), venta_data)

                # Ejecutar todos los cambios juntos
                batch.commit()
                
                st.success("✅ Venta realizada. Stock actualizado.")
                st.session_state.carrito = [] # Limpiar carrito
                st.balloons()
                time.sleep(2)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error al procesar la venta: {e}")

        if st.button("Clear Carrito"):
            st.session_state.carrito = []
            st.rerun()