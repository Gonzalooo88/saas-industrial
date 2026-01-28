import streamlit as st
import os
import sys
import time as tm
from datetime import datetime

# --- CONEXIÓN BASE DE DATOS ---
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- SEGURIDAD ---
if 'carpeta_cliente' not in st.session_state:
    st.error("🚫 Acceso denegado. Inicia sesión.")
    st.stop()

cliente_id = st.session_state.carpeta_cliente

# Referencias
ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

st.set_page_config(page_title="Punto de Venta", layout="wide", page_icon="💸")

# --- LISTA DE CATEGORÍAS (Debe coincidir con Stock) ---
CATEGORIAS_DISPONIBLES = ["Todas", "Ropa", "Anillo", "Collar", "Pulsera", "Aros", "Labial", "Accesorio Pelo", "Mascarilla", "Set/Conjunto", "Otro"]

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .prod-card { 
        border: 1px solid #e0e0e0; 
        padding: 12px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        background-color: white; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .cat-tag { 
        background-color: #f3e5f5; 
        color: #7b1fa2; 
        padding: 2px 6px; 
        border-radius: 4px; 
        font-size: 0.7em; 
        font-weight: bold;
        text-transform: uppercase; 
        margin-right: 5px; 
    }
    .price-tag { 
        color: #2e7d32; 
        font-weight: bold; 
        font-size: 1.1em; 
        float: right;
    }
    .btn-add { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- ESTADO DEL CARRITO ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES AUXILIARES ---

def formatear_variante_para_venta(var_dict):
    """Convierte el diccionario de variante en texto legible automáticamente."""
    partes = []
    # Claves a ignorar porque no son atributos del producto
    ignorar = ['stock', 'sku']
    
    for k, v in var_dict.items():
        if k not in ignorar:
            partes.append(str(v))
    
    # Si no tiene atributos (ej: Mascarilla), ponemos "Único"
    descripcion = " - ".join(partes) if partes else "Estándar"
    stock = var_dict.get('stock', 0)
    return f"{descripcion} (Disp: {stock})"

def agregar_al_carrito(producto, idx_variante, desc_variante):
    """Agrega item al carrito de sesión."""
    st.session_state.carrito.append({
        "id": producto['id'],
        "modelo": producto.get('modelo', 'Sin Nombre'),
        "marca": producto.get('marca', ''),
        "categoria": producto.get('categoria', 'Gral'),
        "precio_venta": producto.get('precio_venta', 0),
        "costo": producto.get('costo', 0),
        "idx_variante": idx_variante, # Guardamos el índice para descontar luego
        "detalle": desc_variante,     # Texto para mostrar en ticket
        "cantidad": 1
    })
    st.toast(f"🛒 Agregado: {producto.get('modelo')}")

# --- INTERFAZ PRINCIPAL ---
st.title(f"💸 Ventas: {cliente_id.replace('_', ' ').title()}")

col_catalogo, col_carrito = st.columns([1.6, 1])

# ==============================================================================
# COLUMNA IZQUIERDA: CATÁLOGO
# ==============================================================================
with col_catalogo:
    # 1. Filtros
    # Usamos radio horizontal pequeño para filtrar rápido
    filtro_cat = st.selectbox("Filtrar por Categoría", CATEGORIAS_DISPONIBLES)
    busqueda = st.text_input("Buscar producto...", placeholder="Nombre, Marca, Color...")
    
    st.divider()
    
    # 2. Carga de Datos
    docs = ref_productos.stream()
    resultados = []
    
    for doc in docs:
        p = doc.to_dict()
        p['id'] = doc.id
        
        # Filtro Categoría
        if filtro_cat != "Todas" and p.get('categoria') != filtro_cat:
            continue
            
        # Filtro Texto (Busca en modelo, marca y en las variantes también)
        texto_busq = f"{p.get('modelo','')} {p.get('marca','')}".lower()
        
        # Truco: Si busca "Rojo", miramos dentro de las variantes también
        texto_vars = " ".join([str(v.values()) for v in p.get('variantes', [])]).lower()
        
        if busqueda:
            term = busqueda.lower()
            if term not in texto_busq and term not in texto_vars:
                continue
        
        resultados.append(p)
        
    if not resultados:
        st.info("No hay productos que coincidan.")
        
    # 3. Renderizado de Tarjetas (Máximo 20 para velocidad)
    for p in resultados[:20]:
        with st.container():
            cat = p.get('categoria', 'Gral')
            st.markdown(f"""
            <div class="prod-card">
                <span class="price-tag">${p.get('precio_venta', 0):,.0f}</span>
                <span class="cat-tag">{cat}</span>
                <b>{p.get('modelo')}</b> <span style="color:gray; font-size:0.9em">({p.get('marca','')})</span>
            </div>
            """, unsafe_allow_html=True)
            
            c_sel, c_btn = st.columns([3, 1])
            
            variantes = p.get('variantes', [])
            
            if variantes:
                # Preparamos la lista para el Selectbox
                opciones_display = []
                indices_reales = []
                
                for i, v in enumerate(variantes):
                    if v.get('stock', 0) > 0:
                        opciones_display.append(formatear_variante_para_venta(v))
                        indices_reales.append(i)
                
                if opciones_display:
                    # Selectbox inteligente
                    seleccion = c_sel.selectbox(
                        "Seleccionar Opción", 
                        range(len(opciones_display)), 
                        format_func=lambda x: opciones_display[x],
                        key=f"sel_{p['id']}",
                        label_visibility="collapsed"
                    )
                    
                    # Botón Agregar
                    if c_btn.button("➕", key=f"btn_{p['id']}"):
                        # Limpiamos el texto "(Disp: 5)" para que quede bonito en el carrito
                        desc_limpia = opciones_display[seleccion].split("(Disp")[0].strip()
                        idx_real = indices_reales[seleccion]
                        agregar_al_carrito(p, idx_real, desc_limpia)
                else:
                    c_sel.error("🚫 Agotado")
            else:
                c_sel.warning("Producto sin stock cargado")

# ==============================================================================
# COLUMNA DERECHA: CARRITO
# ==============================================================================
with col_carrito:
    st.markdown("### 🛒 Tu Pedido")
    
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        total = 0
        costo_total = 0
        
        # Listado de items
        for i, item in enumerate(st.session_state.carrito):
            cols_cart = st.columns([4, 1])
            with cols_cart[0]:
                st.write(f"**{item['modelo']}**")
                # Aquí se muestra ej: "Oro - Talle 18" o "Rojo Pasión"
                st.caption(f"{item['detalle']} | ${item['precio_venta']:,.0f}")
            
            with cols_cart[1]:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.carrito.pop(i)
                    st.rerun()
            
            total += item['precio_venta']
            costo_total += item['costo']
            st.divider()
            
        # Totales
        st.markdown(f"#### Subtotal: ${total:,.2f}")
        
        # Checkbox Descuento
        aplicar_desc = st.checkbox("🎟️ Aplicar Descuento / Ajuste")
        if aplicar_desc:
            precio_final = st.number_input("Total a Cobrar", value=float(total))
        else:
            precio_final = total
            
        ganancia = precio_final - costo_total
        color_ganancia = "green" if ganancia > 0 else "red"
        
        st.markdown(f"**Ganancia Neta:** <span style='color:{color_ganancia}'>${ganancia:,.2f}</span>", unsafe_allow_html=True)
        
        # Botones finales
        b_confirm, b_clean = st.columns([3, 1])
        
        if b_confirm.button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
            if precio_final >= 0:
                try:
                    batch = db.batch()
                    items_ticket = []
                    
                    # Agrupar items por ID de producto para optimizar DB
                    from collections import defaultdict
                    items_por_id = defaultdict(list)
                    for it in st.session_state.carrito:
                        items_por_id[it['id']].append(it)
                    
                    # Proceso de validación y descuento
                    for pid, items in items_por_id.items():
                        ref_doc = ref_productos.document(pid)
                        snap = ref_doc.get()
                        
                        if not snap.exists:
                            st.error(f"El producto {pid} fue borrado mientras vendías.")
                            st.stop()
                            
                        data_prod = snap.to_dict()
                        vars_db = data_prod.get('variantes', [])
                        
                        for item_venta in items:
                            idx = item_venta['idx_variante']
                            
                            # Chequeo de seguridad: que el índice exista y tenga stock
                            if idx < len(vars_db) and vars_db[idx]['stock'] > 0:
                                vars_db[idx]['stock'] -= 1
                                items_ticket.append(f"{item_venta['modelo']} ({item_venta['detalle']})")
                            else:
                                st.error(f"¡Se acabó el stock de {item_venta['modelo']} recién!")
                                st.stop()
                        
                        # Actualizamos el array de variantes en la DB
                        batch.update(ref_doc, {"variantes": vars_db})
                    
                    # Crear el Movimiento
                    mov_id = f"VTA-{int(tm.time())}"
                    batch.set(ref_movimientos.document(mov_id), {
                        "tipo": "Venta",
                        "fecha": datetime.now(),
                        "monto": precio_final,
                        "ganancia": ganancia,
                        "productos": items_ticket,
                        "vendedor": st.session_state.get('usuario', 'Sistema')
                    })
                    
                    batch.commit()
                    
                    # Limpieza y Éxito
                    st.session_state.carrito = []
                    st.success("✅ Venta registrada correctamente")
                    st.balloons()
                    tm.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error procesando la venta: {e}")
        
        if b_clean.button("🗑️"):
            st.session_state.carrito = []
            st.rerun()