import streamlit as st
import pandas as pd
from datetime import datetime, time
from config import db 

st.header("⚙️ Administración y Ajustes")
st.warning("⚠️ Esta sección modifica directamente la base de datos. Úsala con precaución.")

# Clave simple para evitar dedos rápidos (Opcional, pero pediste que no sea fácil)
bloqueo = st.toggle("Habilitar Edición Avanzada")

if not bloqueo:
    st.info("Activa el interruptor de arriba para realizar cambios.")
    st.stop()

# --- SI PASA EL BLOQUEO ---

tab_retro, tab_producto = st.tabs(["📅 Cargar Venta Pasada", "🗑️ Eliminar Producto"])

# ---------------------------------------------------------
# SECCIÓN 1: CARGA RETROACTIVA (Para cuando se olvidaron de cargar ayer)
# ---------------------------------------------------------
with tab_retro:
    st.subheader("Cargar venta de una fecha anterior")
    st.caption("Esto descontará stock actual pero registrará la venta en la fecha que elijas.")
    
    # 1. Traer productos
    ref_stock = db.collection('facha_shila_productos')
    docs = ref_stock.stream()
    productos_dict = {doc.id: doc.to_dict() for doc in docs}
    
    opciones = {}
    for pid, data in productos_dict.items():
        if data.get('stock_actual', 0) > 0:
            label = f"{data.get('modelo')} | {data.get('color')} {data.get('talle')}"
            opciones[label] = pid

    with st.form("form_retroactivo"):
        col_fecha, col_vend = st.columns(2)
        
        # Selector de Fecha Pasada
        fecha_elegida = col_fecha.date_input("Fecha de la venta", value="today")
        vendedor = col_vend.selectbox("¿Quién vendió?", ["Bianca", "Luciano", "Empleado"])
        
        c1, c2 = st.columns([3, 1])
        seleccion = c1.selectbox("Producto", list(opciones.keys()))
        cantidad = c2.number_input("Cantidad", min_value=1, value=1)
        
        submit_retro = st.form_submit_button("💾 Guardar Venta Pasada")
        
        if submit_retro and seleccion:
            pid = opciones[seleccion]
            prod = productos_dict[pid]
            
            # Validar Stock
            if cantidad > prod['stock_actual']:
                st.error(f"No puedes cargar esto. Solo tienes {prod['stock_actual']} en stock hoy.")
            else:
                # Construir fecha con hora fija (ej: mediodía) para que no falle el gráfico
                fecha_completa = datetime.combine(fecha_elegida, time(12, 0, 0))
                
                total = prod['precio_venta'] * cantidad
                
                # 1. Guardar Movimiento con fecha vieja
                db.collection('facha_shila_movimientos').add({
                    "fecha": fecha_completa,
                    "tipo": "Venta",
                    "producto_modelo": prod['modelo'], # Guardamos el nombre por si se borra el producto despues
                    "cantidad": cantidad,
                    "monto_total": total,
                    "vendedor": vendedor,
                    "nota": "Carga manual retroactiva"
                })
                
                # 2. Descontar Stock Actual
                nuevo_stock = prod['stock_actual'] - cantidad
                ref_stock.document(pid).update({"stock_actual": nuevo_stock})
                
                st.success(f"✅ Venta del día {fecha_elegida} registrada.")

# ---------------------------------------------------------
# SECCIÓN 2: ELIMINAR PRODUCTO (Catálogo)
# ---------------------------------------------------------
with tab_producto:
    st.subheader("Borrar productos del catálogo")
    st.error("¡Cuidado! Si borras un producto, desaparecerá del inventario y de la caja futura. El historial de ventas antiguas SE MANTIENE.")
    
    # Reutilizamos el diccionario de productos pero sin filtro de stock
    # para poder borrar cosas con stock 0
    all_docs = ref_stock.stream()
    all_prods = {d.id: d.to_dict() for d in all_docs}
    
    lista_borrar = {f"{d['modelo']} ({d['color']} {d['talle']})": id_ for id_, d in all_prods.items()}
    
    seleccion_borrar = st.selectbox("Selecciona el producto a eliminar", [""] + list(lista_borrar.keys()))
    
    if seleccion_borrar:
        id_a_borrar = lista_borrar[seleccion_borrar]
        
        # Botón de confirmación extra
        st.write(f"Vas a eliminar: **{seleccion_borrar}**")
        if st.button("🔥 Confirmar Eliminación Definitiva", type="primary"):
            # Borrar de Firestore
            ref_stock.document(id_a_borrar).delete()
            st.success("Producto eliminado correctamente.")
            st.rerun()