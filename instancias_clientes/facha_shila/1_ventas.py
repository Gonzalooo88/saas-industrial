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

# --- CONFIGURACIÓN ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

st.set_page_config(page_title="Punto de Venta", layout="wide", page_icon="💸")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .prod-card { border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; margin-bottom: 10px; background-color: white; }
    .price-tag { color: #2ecc71; font-weight: bold; font-size: 1.1em; }
    .stock-tag { font-size: 0.9em; color: #666; }
    </style>
""", unsafe_allow_html=True)

# --- ESTADO DEL CARRITO ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES ---
def agregar_al_carrito(producto, variante_idx, nombre_variante):
    # Verificamos si ya está en el carrito para no duplicar visualmente (opcional)
    # Aquí permitimos duplicados por si quiere agregar 2 veces el mismo item por separado
    st.session_state.carrito.append({
        "id": producto['id'],
        "modelo": producto['modelo'],
        "marca": producto.get('marca', ''),
        "precio_venta": producto['precio_venta'],
        "costo": producto['costo'],
        "variante_idx": variante_idx, # Guardamos el índice para encontrarlo rápido al vender
        "detalle_variante": nombre_variante, # Texto "L - Negro"
        "cantidad": 1
    })
    st.toast(f"🛒 Agregado: {producto['modelo']} ({nombre_variante})")

# --- INTERFAZ ---
st.title(f"💸 Ventas: {cliente_id.replace('_', ' ').title()}")

col_catalogo, col_carrito = st.columns([1.5, 1])

# ==============================================================================
# COLUMNA 1: CATÁLOGO Y BÚSQUEDA
# ==============================================================================
with col_catalogo:
    st.subheader("🔍 Buscar Producto")
    busqueda = st.text_input("Escribe modelo, marca o color...", placeholder="Ej: Remera Batik...")
    
    if busqueda:
        # Traemos todo y filtramos en memoria (Firebase no permite búsquedas parciales nativas fáciles)
        docs = db.collection(COLECCION_PRODUCTOS).stream()
        resultados = []
        
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            # Búsqueda simple
            texto_busqueda = f"{d.get('modelo','')} {d.get('marca','')} {d.get('categoria','')}".lower()
            if busqueda.lower() in texto_busqueda:
                resultados.append(d)
        
        if not resultados:
            st.info("No se encontraron productos.")
        
        for p in resultados:
            with st.container():
                st.markdown(f"""
                <div class="prod-card">
                    <b>{p['modelo']}</b> <span style="color:gray">({p.get('marca', '')})</span><br>
                    <span class="price-tag">${p['precio_venta']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([3, 1])
                
                # LOGICA DE VARIANTES
                variantes = p.get('variantes', [])
                if variantes:
                    # Crear opciones legibles: "L | Negro (Stock: 5)"
                    # Solo mostramos las que tienen stock > 0
                    opciones_vars = []
                    indices_reales = [] # Para saber qué indice del array original es
                    
                    for i, v in enumerate(variantes):
                        if v['stock'] > 0:
                            label = f"{v['talle']} | {v['color']} (Disp: {v['stock']})"
                            opciones_vars.append(label)
                            indices_reales.append(i)
                    
                    if opciones_vars:
                        sel_idx_local = c1.selectbox(
                            f"Selecciona Variante ({p['id']})", 
                            range(len(opciones_vars)), 
                            format_func=lambda x: opciones_vars[x],
                            key=f"sel_{p['id']}",
                            label_visibility="collapsed"
                        )
                        
                        # El indice real en la DB
                        idx_db = indices_reales[sel_idx_local]
                        nombre_var_elegida = opciones_vars[sel_idx_local].split("(")[0].strip() # "L | Negro"
                        
                        if c2.button("➕ Añadir", key=f"btn_{p['id']}"):
                            agregar_al_carrito(p, idx_db, nombre_var_elegida)
                    else:
                        c1.error("🚫 Sin Stock Disponible")
                else:
                    c1.warning("Producto con formato antiguo o sin stock.")

# ==============================================================================
# COLUMNA 2: CARRITO Y COBRO
# ==============================================================================
with col_carrito:
    st.markdown("### 🛒 Tu Pedido")
    
    if not st.session_state.carrito:
        st.info("El carrito está vacío. Agrega productos de la izquierda.")
    else:
        # LISTADO DE ITEMS
        total_acumulado = 0
        costo_acumulado = 0
        
        for i, item in enumerate(st.session_state.carrito):
            col_it1, col_it2 = st.columns([4, 1])
            with col_it1:
                st.write(f"**{item['modelo']}**")
                st.caption(f"{item['detalle_variante']} - ${item['precio_venta']:,.0f}")
            with col_it2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.carrito.pop(i)
                    st.rerun()
            
            total_acumulado += item['precio_venta']
            costo_acumulado += item['costo']
            st.divider()

        # --- SECCIÓN DE PAGO ---
        st.markdown(f"#### Subtotal: ${total_acumulado:,.2f}")
        
        # MODO PROMO / DESCUENTO
        es_promo = st.checkbox("🎟️ Aplicar Descuento / Precio Manual")
        
        if es_promo:
            precio_final = st.number_input("Monto a Cobrar ($)", value=float(total_acumulado), step=100.0)
            st.caption(f"Original: ${total_acumulado:,.2f}")
        else:
            precio_final = total_acumulado
            
        # CALCULO DE GANANCIA EN VIVO
        ganancia_real = precio_final - costo_acumulado
        color_g = "green" if ganancia_real > 0 else "red"
        st.markdown(f"**Ganancia Neta:** <span style='color:{color_g}'>${ganancia_real:,.2f}</span>", unsafe_allow_html=True)
        
        # --- BOTÓN DE CONFIRMACIÓN ---
        btn_cols = st.columns([1, 4])
        if btn_cols[1].button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
            if precio_final >= 0:
                try:
                    batch = db.batch()
                    items_desc = []
                    
                    # PROCESO DE DESCUENTO DE STOCK
                    # Agrupamos por producto para no leer el mismo doc mil veces
                    from collections import defaultdict
                    items_por_id = defaultdict(list)
                    for item in st.session_state.carrito:
                        items_por_id[item['id']].append(item)
                    
                    for pid, lista_items in items_por_id.items():
                        ref_p = db.collection(COLECCION_PRODUCTOS).document(pid)
                        # Leemos la versión más reciente de la DB
                        doc_snap = ref_p.get()
                        if not doc_snap.exists:
                            st.error(f"El producto {pid} ya no existe.")
                            st.stop()
                        
                        data_p = doc_snap.to_dict()
                        variantes_db = data_p.get('variantes', [])
                        
                        # Descontamos en memoria
                        for item_venta in lista_items:
                            idx = item_venta['variante_idx']
                            # Validación extra por si cambió el array
                            if idx < len(variantes_db):
                                if variantes_db[idx]['stock'] > 0:
                                    variantes_db[idx]['stock'] -= 1
                                    items_desc.append(f"{item_venta['modelo']} ({item_venta['detalle_variante']})")
                                else:
                                    st.error(f"¡Error! Alguien se llevó el último {item_venta['modelo']} recién.")
                                    st.stop()
                        
                        # Agregamos la actualización al batch
                        batch.update(ref_p, {"variantes": variantes_db})
                    
                    # REGISTRO DE MOVIMIENTO
                    mov_id = f"VTA-{int(time.time())}"
                    ref_mov = db.collection(COLECCION_MOVIMIENTOS).document(mov_id)
                    batch.set(ref_mov, {
                        "tipo": "Venta",
                        "fecha": datetime.now(),
                        "monto": precio_final,
                        "ganancia": ganancia_real,
                        "productos": items_desc,
                        "es_promo": es_promo
                    })
                    
                    batch.commit()
                    
                    # FINALIZAR
                    st.session_state.carrito = []
                    st.success(f"✅ ¡Venta registrada por ${precio_final:,.0f}!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error procesando la venta: {e}")
            else:
                st.warning("El precio no puede ser negativo.")
        
        if btn_cols[0].button("🗑️", help="Vaciar Carrito"):
            st.session_state.carrito = []
            st.rerun()