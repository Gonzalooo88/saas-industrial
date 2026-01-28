import streamlit as st
import pandas as pd
from datetime import datetime, time
from config import db 

st.header("⚙️ Administración Operativa")
st.warning("⚠️ Zona de corrección de datos.")

# Bloqueo simple
bloqueo = st.toggle("Habilitar Edición")
if not bloqueo:
    st.info("Activa el interruptor para realizar cambios.")
    st.stop()

# SOLO 3 PESTAÑAS (Operativas)
tab_retro, tab_producto, tab_ventas = st.tabs([
    "📅 Cargar Venta Pasada", 
    "📦 Eliminar Producto", 
    "🗑️ Eliminar Venta"
])

# ---------------------------------------------------------
# TAB 1: CARGA RETROACTIVA
# ---------------------------------------------------------
with tab_retro:
    st.subheader("Cargar venta con fecha anterior")
    
    # Traemos productos
    ref_stock = db.collection('facha_shila_productos')
    docs = ref_stock.stream()
    productos_dict = {doc.id: doc.to_dict() for doc in docs}
    
    opciones = {}
    for pid, data in productos_dict.items():
        label = f"{data.get('modelo')} | {data.get('color')} {data.get('talle')}"
        opciones[label] = pid

    with st.form("form_retroactivo"):
        col_fecha, col_vend = st.columns(2)
        fecha_elegida = col_fecha.date_input("Fecha real de la venta", value="today")
        vendedor = col_vend.selectbox("¿Quién vendió?", ["Bianca", "Luciano", "Empleado"])
        
        c1, c2 = st.columns([3, 1])
        seleccion = c1.selectbox("Producto", list(opciones.keys()))
        cantidad = c2.number_input("Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("💾 Guardar Venta"):
            if seleccion:
                pid = opciones[seleccion]
                prod = productos_dict[pid]
                
                fecha_completa = datetime.combine(fecha_elegida, time(12, 0, 0))
                total = prod.get('precio_venta', 0) * cantidad
                
                db.collection('facha_shila_movimientos').add({
                    "fecha": fecha_completa, "tipo": "Venta", "producto_modelo": prod.get('modelo'),
                    "cantidad": cantidad, "monto_total": total, "vendedor": vendedor, "nota": "Carga retroactiva"
                })
                
                ref_stock.document(pid).update({"stock_actual": prod.get('stock_actual', 0) - cantidad})
                st.success(f"✅ Venta guardada.")
                st.rerun()

# ---------------------------------------------------------
# TAB 2: ELIMINAR PRODUCTO
# ---------------------------------------------------------
with tab_producto:
    st.subheader("Limpiar catálogo")
    st.caption("Borrar productos que ya no existen.")
    
    all_docs = ref_stock.stream()
    dict_prods = {d.id: d.to_dict() for d in all_docs}
    
    lista_borrar = {f"{d['modelo']} ({d['color']} {d['talle']})": id_ for id_, d in dict_prods.items()}
    seleccion_borrar = st.selectbox("Producto a eliminar", [""] + list(lista_borrar.keys()))
    
    if seleccion_borrar:
        id_borrar = lista_borrar[seleccion_borrar]
        if st.button("🔥 Borrar Definitivamente", type="primary"):
            ref_stock.document(id_borrar).delete()
            st.success("Producto eliminado.")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: ELIMINAR VENTAS
# ---------------------------------------------------------
with tab_ventas:
    st.subheader("Anular Ventas")
    
    ref_movs = db.collection('facha_shila_movimientos')
    # Traemos ultimas 50 y filtramos en Python para evitar errores de índice
    docs_raw = ref_movs.order_by("fecha", direction="DESCENDING").limit(50).stream()
    
    lista_movs = []
    for doc in docs_raw:
        d = doc.to_dict()
        if d.get('tipo') == 'Venta':
            fecha_str = d['fecha'].strftime('%d/%m %H:%M') if d.get('fecha') else "S/F"
            label = f"{fecha_str} | {d.get('producto_modelo')} | ${d.get('monto_total',0):,.0f} ({d.get('vendedor')})"
            d['id'] = doc.id
            lista_movs.append((label, d))

    if not lista_movs:
        st.info("No hay ventas recientes.")
    else:
        opcion = st.selectbox("Selecciona venta a borrar", options=lista_movs, format_func=lambda x: x[0])
        
        if opcion:
            lbl, dat = opcion
            st.write(f"Vas a borrar: **{lbl}**")
            devolver = st.checkbox("Devolver stock", value=True)

            if st.button("🗑️ Eliminar", type="primary"):
                if devolver and dat.get('producto_modelo'):
                    q = ref_stock.where("modelo", "==", dat['producto_modelo']).limit(1).stream()
                    found = list(q)
                    if found:
                        current = found[0].to_dict().get('stock_actual', 0)
                        ref_stock.document(found[0].id).update({"stock_actual": current + dat.get('cantidad', 1)})
                
                ref_movs.document(dat['id']).delete()
                st.success("Venta eliminada.")
                st.rerun()
