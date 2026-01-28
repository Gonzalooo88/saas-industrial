import streamlit as st
import pandas as pd
from datetime import datetime, time
from config import db 

st.header("⚙️ Administración y Ajustes")
st.warning("⚠️ Esta sección modifica directamente la base de datos. Úsala con precaución.")

# Interruptor de seguridad
bloqueo = st.toggle("Habilitar Edición Avanzada")

if not bloqueo:
    st.info("Activa el interruptor de arriba para realizar cambios.")
    st.stop()

# --- SI PASA EL BLOQUEO ---
tab_retro, tab_producto, tab_ventas = st.tabs(["📅 Cargar Venta Pasada", "📦 Eliminar Producto", "🗑️ Eliminar Venta"])

# ---------------------------------------------------------
# TAB 1: CARGA RETROACTIVA
# ---------------------------------------------------------
with tab_retro:
    st.subheader("Cargar venta de una fecha anterior")
    
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
        fecha_elegida = col_fecha.date_input("Fecha de la venta", value="today")
        vendedor = col_vend.selectbox("¿Quién vendió?", ["Bianca", "Luciano", "Empleado"])
        
        c1, c2 = st.columns([3, 1])
        seleccion = c1.selectbox("Producto", list(opciones.keys()))
        cantidad = c2.number_input("Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("💾 Guardar Venta Pasada"):
            if seleccion:
                pid = opciones[seleccion]
                prod = productos_dict[pid]
                
                if cantidad > prod['stock_actual']:
                    st.error(f"Stock insuficiente. Hay {prod['stock_actual']}.")
                else:
                    fecha_completa = datetime.combine(fecha_elegida, time(12, 0, 0))
                    total = prod['precio_venta'] * cantidad
                    
                    db.collection('facha_shila_movimientos').add({
                        "fecha": fecha_completa,
                        "tipo": "Venta",
                        "producto_modelo": prod['modelo'],
                        "cantidad": cantidad,
                        "monto_total": total,
                        "vendedor": vendedor,
                        "nota": "Carga manual retroactiva"
                    })
                    
                    nuevo_stock = prod['stock_actual'] - cantidad
                    ref_stock.document(pid).update({"stock_actual": nuevo_stock})
                    st.success(f"✅ Venta registrada con fecha {fecha_elegida}.")
                    st.rerun()

# ---------------------------------------------------------
# TAB 2: ELIMINAR PRODUCTO
# ---------------------------------------------------------
with tab_producto:
    st.subheader("Borrar productos del catálogo")
    st.error("Si borras un producto, desaparece del inventario.")
    
    all_docs = ref_stock.stream()
    all_prods = {d.id: d.to_dict() for d in all_docs}
    
    lista_borrar = {f"{d['modelo']} ({d['color']} {d['talle']})": id_ for id_, d in all_prods.items()}
    
    seleccion_borrar = st.selectbox("Selecciona el producto a eliminar", [""] + list(lista_borrar.keys()))
    
    if seleccion_borrar:
        id_a_borrar = lista_borrar[seleccion_borrar]
        if st.button("🔥 Confirmar Eliminación Definitiva", type="primary"):
            ref_stock.document(id_a_borrar).delete()
            st.success("Producto eliminado.")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: ELIMINAR VENTAS (NUEVO)
# ---------------------------------------------------------
with tab_ventas:
    st.subheader("Anular Ventas Registradas")
    st.info("Aquí puedes borrar las ventas de prueba.")

    # 1. Listar últimas ventas
    ref_movs = db.collection('facha_shila_movimientos')
    docs_movs = ref_movs.where("tipo", "==", "Venta").order_by("fecha", direction="DESCENDING").limit(20).stream()
    
    lista_movs = []
    for doc in docs_movs:
        d = doc.to_dict()
        d['id'] = doc.id
        # Formato legible para el selector
        fecha_str = d['fecha'].strftime('%d/%m %H:%M') if d.get('fecha') else "S/F"
        label = f"{fecha_str} | {d.get('producto_modelo')} | ${d.get('monto_total',0):,.0f} ({d.get('vendedor')})"
        lista_movs.append((label, d))

    if not lista_movs:
        st.warning("No hay ventas recientes.")
    else:
        # Selector de venta
        opcion_elegida = st.selectbox("Selecciona la venta a borrar", options=lista_movs, format_func=lambda x: x[0])
        
        if opcion_elegida:
            label, datos_venta = opcion_elegida
            id_venta = datos_venta['id']
            cant_vendida = datos_venta.get('cantidad', 1)
            modelo_vendido = datos_venta.get('producto_modelo')

            st.write("---")
            st.write(f"Vas a eliminar: **{label}**")
            
            # Checkbox importante
            devolver_stock = st.checkbox("🔄 Devolver stock al inventario", value=True, help="Si marcas esto, sumaremos las unidades borradas de nuevo al stock.")

            if st.button("🗑️ Eliminar Venta", type="primary"):
                # A. Devolver Stock (Si se solicitó)
                if devolver_stock and modelo_vendido:
                    # Buscar el producto por modelo (puede haber varios talles, intentamos sumar al genérico o avisar)
                    # Nota: Como en ventas guardamos el modelo pero no el ID exacto en versiones simples, 
                    # intentaremos buscar coincidencias. Si es una prueba, a veces basta con borrar el registro.
                    # Para hacerlo robusto buscamos por nombre exacto:
                    
                    q_stock = ref_stock.where("modelo", "==", modelo_vendido).limit(1).stream()
                    found_prod = list(q_stock)
                    
                    if found_prod:
                        doc_prod = found_prod[0]
                        stock_nuevo = doc_prod.to_dict().get('stock_actual', 0) + cant_vendida
                        ref_stock.document(doc_prod.id).update({"stock_actual": stock_nuevo})
                        st.caption(f"✅ Se devolvieron {cant_vendida} unidades al stock de {modelo_vendido}.")
                    else:
                        st.warning(f"No se encontró el producto '{modelo_vendido}' en stock para devolverlo. Solo se borrará el registro de dinero.")

                # B. Borrar el movimiento
                ref_movs.document(id_venta).delete()
                
                st.success("Venta eliminada correctamente.")
                st.rerun()
