import streamlit as st
import os
import sys
import time as tm # Usamos alias para evitar conflictos
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

# --- SEGURIDAD Y CONTEXTO ---
if 'carpeta_cliente' not in st.session_state:
    st.error("🚫 Acceso denegado. Inicia sesión.")
    st.stop()

cliente_id = st.session_state.carpeta_cliente # Ej: "facha_shila"

# --- REFERENCIAS A NUEVAS COLECCIONES ANIDADAS ---
ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

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
    # Guardamos en sesión
    st.session_state.carrito.append({
        "id": producto['id'],
        "modelo": producto.get('modelo', 'Sin Nombre'),
        "marca": producto.get('marca', ''),
        "precio_venta": producto.get('precio_venta', 0),
        "costo": producto.get('costo', 0),
        "variante_idx": variante_idx, # Indice vital para descontar stock
        "detalle_variante": nombre_variante, 
        "cantidad": 1
    })
    st.toast(f"🛒 Agregado: {producto.get('modelo')} ({nombre_variante})")

# --- INTERFAZ ---
st.title(f"💸 Ventas: {cliente_id.replace('_', ' ').title()}")

col_catalogo, col_carrito = st.columns([1.5, 1])

# ==============================================================================
# COLUMNA 1: CATÁLOGO Y BÚSQUEDA
# ==============================================================================
with col_catalogo:
    st.subheader("🔍 Buscar Producto")
    busqueda = st.text_input("Escribe modelo, marca o color...", placeholder="Ej: Remera Batik...")
    
    # Solo buscamos si escribe algo para no cargar todo de golpe (opcional)
    # O cargamos todo si son pocos productos
    docs = ref_productos.stream()
    resultados = []
    
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        
        # Filtro en memoria
        texto_busqueda = f"{d.get('modelo','')} {d.get('marca','')} {d.get('categoria','')}".lower()
        if busqueda.lower() in texto_busqueda:
            resultados.append(d)
    
    if busqueda and not resultados:
        st.info("No se encontraron productos.")
    
    # Mostramos resultados (limitado a 20 para no saturar si no hay búsqueda)
    for p in resultados[:20]:
        with st.container():
            st.markdown(f"""
            <div class="prod-card">
                <b>{p.get('modelo')}</b> <span style="color:gray">({p.get('marca', '')})</span><br>
                <span class="price-tag">${p.get('precio_venta', 0):,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([3, 1])
            
            # LOGICA DE VARIANTES
            variantes = p.get('variantes', [])
            if variantes:
                opciones_vars = []
                indices_reales = [] 
                
                for i, v in enumerate(variantes):
                    if v['stock'] > 0:
                        label = f"{v['talle']} | {v['color']} (Disp: {v['stock']})"
                        opciones_vars.append(label)
                        indices_reales.append(i)
                
                if opciones_vars:
                    sel_idx_local = c1.selectbox(
                        f"Variante", 
                        range(len(opciones_vars)), 
                        format_func=lambda x: opciones_vars[x],
                        key=f"sel_{p['id']}",
                        label_visibility="collapsed"
                    )
                    
                    idx_db = indices_reales[sel_idx_local]
                    nombre_var_elegida = opciones_vars[sel_idx_local].split("(")[0].strip()
                    
                    if c2.button("➕ Añadir", key=f"btn_{p['id']}"):
                        agregar_al_carrito(p, idx_db, nombre_var_elegida)
                else:
                    c1.error("🚫 Sin Stock")
            else:
                c1.warning("Producto antiguo / Sin variantes")

# ==============================================================================
# COLUMNA 2: CARRITO Y COBRO
# ==============================================================================
with col_carrito:
    st.markdown("### 🛒 Tu Pedido")
    
    if not st.session_state.carrito:
        st.info("Carrito vacío.")
    else:
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

        st.markdown(f"#### Subtotal: ${total_acumulado:,.2f}")
        
        es_promo = st.checkbox("🎟️ Aplicar Descuento / Precio Manual")
        
        if es_promo:
            precio_final = st.number_input("Total a Cobrar", value=float(total_acumulado), step=100.0)
        else:
            precio_final = total_acumulado
            
        ganancia_real = precio_final - costo_acumulado
        color_g = "green" if ganancia_real > 0 else "red"
        st.markdown(f"**Ganancia:** <span style='color:{color_g}'>${ganancia_real:,.2f}</span>", unsafe_allow_html=True)
        
        btn_cols = st.columns([1, 4])
        
        # --- PROCESO DE VENTA ---
        if btn_cols[1].button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
            if precio_final >= 0:
                try:
                    batch = db.batch()
                    items_desc = []
                    
                    # Agrupamos items por ID para optimizar lecturas
                    from collections import defaultdict
                    items_por_id = defaultdict(list)
                    for item in st.session_state.carrito:
                        items_por_id[item['id']].append(item)
                    
                    # Validación de Stock en DB
                    for pid, lista_items in items_por_id.items():
                        ref_p = ref_productos.document(pid)
                        doc_snap = ref_p.get()
                        
                        if not doc_snap.exists:
                            st.error(f"El producto {pid} fue borrado.")
                            st.stop()
                        
                        data_p = doc_snap.to_dict()
                        variantes_db = data_p.get('variantes', [])
                        
                        for item_venta in lista_items:
                            idx = item_venta['variante_idx']
                            # Verificamos si hay stock suficiente
                            if idx < len(variantes_db):
                                if variantes_db[idx]['stock'] > 0:
                                    variantes_db[idx]['stock'] -= 1
                                    items_desc.append(f"{item_venta['modelo']} ({item_venta['detalle_variante']})")
                                else:
                                    st.error(f"¡Se acabó el stock de {item_venta['modelo']} recién!")
                                    st.stop()
                        
                        # Actualizamos producto en el lote
                        batch.update(ref_p, {"variantes": variantes_db})
                    
                    # Registro de Movimiento
                    mov_id = f"VTA-{int(tm.time())}"
                    
                    batch.set(ref_movimientos.document(mov_id), {
                        "tipo": "Venta",
                        "fecha": datetime.now(),
                        "monto": precio_final,
                        "ganancia": ganancia_real,
                        "productos": items_desc,
                        "es_promo": es_promo,
                        "vendedor": st.session_state.get('usuario', 'Sistema')
                    })
                    
                    batch.commit()
                    
                    st.session_state.carrito = []
                    st.success(f"✅ ¡Venta exitosa!")
                    st.balloons()
                    tm.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error en venta: {e}")
            else:
                st.warning("Precio inválido.")
        
        if btn_cols[0].button("🗑️"):
            st.session_state.carrito = []
            st.rerun()