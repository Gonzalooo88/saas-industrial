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

# --- DEFINICIÓN DE PESTAÑAS (Ahora son 4) ---
tab_retro, tab_producto, tab_ventas, tab_usuarios = st.tabs([
    "📅 Cargar Venta Pasada", 
    "📦 Eliminar Producto", 
    "🗑️ Eliminar Venta",
    "👥 Gestión Usuarios"
])

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
        # Mostramos todo, incluso sin stock, por si fue un error de conteo
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
                
                # Aviso de stock pero permitimos cargar igual (es retroactivo)
                stock_actual = prod.get('stock_actual', 0)
                if cantidad > stock_actual:
                    st.warning(f"Ojo: El stock actual es {stock_actual}, pero descontaremos igual.")
                
                fecha_completa = datetime.combine(fecha_elegida, time(12, 0, 0))
                total = prod.get('precio_venta', 0) * cantidad
                
                # Guardar movimiento
                db.collection('facha_shila_movimientos').add({
                    "fecha": fecha_completa, "tipo": "Venta", "producto_modelo": prod.get('modelo'),
                    "cantidad": cantidad, "monto_total": total, "vendedor": vendedor, "nota": "Carga retroactiva"
                })
                
                # Actualizar stock
                ref_stock.document(pid).update({"stock_actual": stock_actual - cantidad})
                st.success(f"✅ Venta registrada con fecha {fecha_elegida}.")
                st.rerun()

# ---------------------------------------------------------
# TAB 2: ELIMINAR PRODUCTO
# ---------------------------------------------------------
with tab_producto:
    st.subheader("Borrar productos del catálogo")
    all_docs = ref_stock.stream()
    # Recargamos diccionario por si hubo cambios
    dict_prods = {d.id: d.to_dict() for d in all_docs}
    
    lista_borrar = {f"{d['modelo']} ({d['color']} {d['talle']})": id_ for id_, d in dict_prods.items()}
    seleccion_borrar = st.selectbox("Selecciona producto a eliminar", [""] + list(lista_borrar.keys()))
    
    if seleccion_borrar:
        id_borrar = lista_borrar[seleccion_borrar]
        if st.button("🔥 Confirmar Eliminación", type="primary"):
            ref_stock.document(id_borrar).delete()
            st.success("Producto eliminado del sistema.")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: ELIMINAR VENTAS
# ---------------------------------------------------------
with tab_ventas:
    st.subheader("Anular Ventas Registradas")
    
    ref_movs = db.collection('facha_shila_movimientos')
    
    # Truco para evitar error de índices: Traemos los últimos 50 y filtramos en Python
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
        st.warning("No hay ventas recientes para mostrar.")
    else:
        opcion_elegida = st.selectbox("Selecciona la venta a borrar", options=lista_movs, format_func=lambda x: x[0])
        
        if opcion_elegida:
            label, datos_venta = opcion_elegida
            
            st.write(f"Vas a borrar: **{label}**")
            devolver_stock = st.checkbox("🔄 Devolver stock al inventario", value=True)

            if st.button("🗑️ Eliminar Venta Definitivamente", type="primary"):
                # A. Devolver Stock
                if devolver_stock and datos_venta.get('producto_modelo'):
                    # Buscamos el producto por nombre (modelo)
                    q_stock = ref_stock.where("modelo", "==", datos_venta['producto_modelo']).limit(1).stream()
                    found_prod = list(q_stock)
                    
                    if found_prod:
                        doc_prod = found_prod[0]
                        nuevo_st = doc_prod.to_dict().get('stock_actual', 0) + datos_venta.get('cantidad', 1)
                        ref_stock.document(doc_prod.id).update({"stock_actual": nuevo_st})
                        st.caption(f"✅ Stock devuelto.")
                    else:
                        st.warning("El producto ya no existe en el catálogo, no se pudo devolver stock.")

                # B. Borrar el movimiento
                ref_movs.document(datos_venta['id']).delete()
                st.success("Venta eliminada.")
                st.rerun()

# ---------------------------------------------------------
# TAB 4: GESTIÓN DE USUARIOS (NUEVO)
# ---------------------------------------------------------
with tab_usuarios:
    st.subheader("👥 Control de Acceso")
    st.info("Activa o desactiva vendedores. Si desactivas a alguien, no podrá entrar a la App.")

    ref_users = db.collection('facha_shila_usuarios')
    docs_users = list(ref_users.stream())

    # --- AUTO-CREACIÓN DE USUARIOS (Si es la primera vez) ---
    if not docs_users:
        st.warning("⚠️ No hay usuarios en la base de datos. Creando los iniciales...")
        usuarios_default = {
            "Bianca": {"pass": "1234", "activo": True, "rol": "admin"},
            "Luciano": {"pass": "1234", "activo": True, "rol": "admin"},
            "Empleado": {"pass": "0000", "activo": True, "rol": "vendedor"}
        }
        for nombre, datos in usuarios_default.items():
            ref_users.document(nombre).set(datos)
        st.success("✅ Usuarios creados. Por favor recarga la página.")
        st.stop()

    # --- LISTADO DE USUARIOS ---
    st.write("---")
    for doc in docs_users:
        user_id = doc.id
        data = doc.to_dict()
        
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        
        with c1:
            st.markdown(f"### 👤 {user_id}")
            st.caption(f"Rol: {data.get('rol', 'vendedor')}")
            
        with c2:
            # INTERRUPTOR MÁGICO
            estado_actual = data.get('activo', True)
            nuevo_estado = st.toggle(f"Habilitado", value=estado_actual, key=f"toggle_{user_id}")
            
            if nuevo_estado != estado_actual:
                ref_users.document(user_id).update({"activo": nuevo_estado})
                st.toast(f"Permiso actualizado para {user_id}")
        
        with c3:
            # CAMBIO DE CLAVE
            nueva_pass = st.text_input(f"Cambiar Clave", type="password", key=f"pass_{user_id}", placeholder="Nueva...")
            if st.button("💾", key=f"btn_{user_id}", help="Guardar nueva clave"):
                if nueva_pass:
                    ref_users.document(user_id).update({"pass": nueva_pass})
                    st.success(f"Clave de {user_id} actualizada.")
        
        st.divider()
                st.success("Venta eliminada correctamente.")
                st.rerun()

