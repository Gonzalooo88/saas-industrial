import streamlit as st
import pandas as pd
from datetime import datetime
from config import db 

st.header("🛍️ Carga de Ventas")

# --- 1. CONFIGURACIÓN ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# Detectar usuario
datos_usuario = st.session_state.get('user_session', {})
vendedor_actual = datos_usuario.get('nombre', 'Desconocido')

st.caption(f"Vendedor activo: **{vendedor_actual}**")

# --- 2. CARGA DE DATOS ---
ref_stock = db.collection('facha_shila_productos')
docs = ref_stock.stream()
productos_dict = {doc.id: doc.to_dict() for doc in docs}

opciones_select = {}
for pid, data in productos_dict.items():
    if data.get('stock_actual', 0) > 0:
        # Formato: Modelo | Color Talle ($Precio)
        label = f"{data.get('modelo')} | {data.get('color')} {data.get('talle')} (${data.get('precio_venta')})"
        opciones_select[label] = pid

# --- 3. SELECCIÓN DE PRODUCTOS ---
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    
    seleccion = c1.selectbox("Elegir Producto", [""] + list(opciones_select.keys()))
    cantidad = c2.number_input("Cant.", min_value=1, value=1)
    
    # Botón simple para añadir a la lista
    if c3.button("➕ Agregar"):
        if seleccion:
            pid = opciones_select[seleccion]
            prod = productos_dict[pid]
            
            # Validación stock
            en_carrito = sum([i['cantidad'] for i in st.session_state.carrito if i['id'] == pid])
            disponible = prod['stock_actual'] - en_carrito
            
            if cantidad > disponible:
                st.error(f"Solo quedan {disponible} unidades.")
            else:
                item = {
                    "id": pid,
                    "modelo": prod['modelo'],
                    "detalle": f"{prod['color']} {prod['talle']}",
                    "precio": prod['precio_venta'],
                    "cantidad": cantidad,
                    "subtotal": prod['precio_venta'] * cantidad
                }
                st.session_state.carrito.append(item)
                st.rerun()

# --- 4. RESUMEN Y 'SUBIR' ---
if st.session_state.carrito:
    st.subheader("Resumen del Pedido")
    df = pd.DataFrame(st.session_state.carrito)
    
    st.dataframe(
        df[["modelo", "detalle", "cantidad", "subtotal"]], 
        use_container_width=True, 
        hide_index=True
    )
    
    total = df["subtotal"].sum()
    st.markdown(f"### Total: **${total:,.0f}**")

    c_conf, c_borrar = st.columns([3,1])
    
    # CAMBIO SOLICITADO: Botón "Subir" en vez de "Cobrar"
    if c_conf.button("🚀 Subir Venta", type="primary", use_container_width=True):
        
        batch = db.batch()
        ref_movs = db.collection('facha_shila_movimientos')
        
        for item in st.session_state.carrito:
            # 1. Guardar Movimiento
            nuevo_mov = ref_movs.document()
            nuevo_mov.set({
                "fecha": datetime.now(),
                "tipo": "Venta",
                "producto_modelo": item['modelo'],
                "cantidad": item['cantidad'],
                "monto_total": item['subtotal'],
                "vendedor": vendedor_actual
            })
            
            # 2. Actualizar Stock
            stock_nuevo = productos_dict[item['id']]['stock_actual'] - item['cantidad']
            ref_stock.document(item['id']).update({"stock_actual": stock_nuevo})

        st.session_state.carrito = []
        st.balloons()
        st.success("¡Venta subida exitosamente!")
        st.rerun()

    if c_borrar.button("❌ Cancelar"):
        st.session_state.carrito = []
        st.rerun()