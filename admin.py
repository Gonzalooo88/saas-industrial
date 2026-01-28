import streamlit as st
import pandas as pd
# --- CORRECCIÓN DE IMPORT ---
# Importamos 'time' como módulo para usar sleep
import time 
# Importamos 'time' de datetime con un ALIAS (dt_time) para no confundirnos
from datetime import datetime, time as dt_time 
import os
import sys

# --- CONEXIÓN CON CONFIG.PY (Ruta Dinámica) ---
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

st.header(f"⚙️ Administración: {cliente_id.replace('_', ' ').title()}")
st.warning("⚠️ Zona de corrección de datos. Ten cuidado.")

# Bloqueo de seguridad
bloqueo = st.toggle("🔓 Habilitar Edición", value=False)
if not bloqueo:
    st.info("Activa el interruptor arriba para realizar cambios.")
    st.stop()

# SOLO 3 PESTAÑAS (Operativas)
tab_retro, tab_producto, tab_ventas = st.tabs([
    "📅 Cargar Venta Pasada", 
    "📦 Eliminar Producto", 
    "🗑️ Eliminar Venta"
])

# ==============================================================================
# TAB 1: CARGA RETROACTIVA (Adaptada a Variantes)
# ==============================================================================
with tab_retro:
    st.subheader("Cargar venta con fecha anterior")
    st.caption("Útil si te olvidaste de cargar algo ayer o la semana pasada.")
    
    # 1. Traer productos
    ref_stock = db.collection(COLECCION_PRODUCTOS)
    docs = ref_stock.stream()
    
    # Creamos un diccionario inteligente para el selector
    opciones_productos = {}
    datos_completos = {} # Para guardar la info y no volver a consultar
    
    for doc in docs:
        d = doc.to_dict()
        pid = doc.id
        modelo = d.get('modelo', 'Sin Nombre')
        
        # Guardamos en memoria
        datos_completos[pid] = d
        opciones_productos[pid] = f"{modelo} ({d.get('marca', '')})"

    # Formulario
    with st.form("form_retroactivo"):
        col_fecha, col_vend = st.columns(2)
        fecha_elegida = col_fecha.date_input("Fecha real de la venta", value="today")
        vendedor = col_vend.selectbox("¿Quién vendió?", ["Dueño", "Vendedor 1", "Vendedor 2"])
        
        # Selección del Modelo
        pid_seleccionado = st.selectbox("1. Selecciona el Modelo", options=list(opciones_productos.keys()), format_func=lambda x: opciones_productos[x])
        
        # Selección de la Variante (Talle/Color)
        variant_str = "N/A"
        variante_seleccionada_idx = -1
        
        if pid_seleccionado:
            prod_data = datos_completos[pid_seleccionado]
            variantes = prod_data.get('variantes', [])
            
            if variantes:
                # Crear lista legible: "L - Negro (Stock: 5)"
                opts_vars = [f"{v['talle']} - {v['color']} (Stock: {v['stock']})" for v in variantes]
                idx_var = st.selectbox("2. Selecciona Variante", range(len(opts_vars)), format_func=lambda i: opts_vars[i])
                variante_seleccionada_idx = idx_var
            else:
                st.warning("Este producto no tiene variantes configuradas.")

        cantidad = st.number_input("3. Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("💾 Guardar Venta Retroactiva"):
            if pid_seleccionado and variante_seleccionada_idx >= 0:
                try:
                    p_info = datos_completos[pid_seleccionado]
                    vars_actuales = p_info.get('variantes', [])
                    var_elegida = vars_actuales[variante_seleccionada_idx]
                    
                    # Cálculos
                    precio_u = p_info.get('precio_venta', 0)
                    costo_u = p_info.get('costo', 0)
                    total = precio_u * cantidad
                    ganancia = (precio_u - costo_u) * cantidad
                    
                    # ACTUALIZAR STOCK EN LA LISTA
                    vars_actuales[variante_seleccionada_idx]['stock'] -= cantidad
                    
                    batch = db.batch()
                    
                    # 1. Actualizar producto
                    ref_p = db.collection(COLECCION_PRODUCTOS).document(pid_seleccionado)
                    batch.update(ref_p, {"variantes": vars_actuales})
                    
                    # 2. Crear movimiento con fecha vieja
                    # USAMOS dt_time AQUI PARA EVITAR EL ERROR
                    fecha_completa = datetime.combine(fecha_elegida, dt_time(12, 0, 0))
                    desc_prod = f"{p_info['modelo']} ({var_elegida['talle']} {var_elegida['color']})"
                    
                    batch.add(db.collection(COLECCION_MOVIMIENTOS), {
                        "fecha": fecha_completa, 
                        "tipo": "Venta Retroactiva", 
                        "productos": [desc_prod],
                        "monto": total, 
                        "ganancia": ganancia,
                        "vendedor": vendedor
                    })
                    
                    batch.commit()
                    st.success(f"✅ Venta guardada del día {fecha_elegida}")
                    time.sleep(1) # Ahora sí funciona el sleep
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==============================================================================
# TAB 2: ELIMINAR PRODUCTO
# ==============================================================================
with tab_producto:
    st.subheader("Limpiar catálogo")
    st.caption("Borrar productos obsoletos o mal cargados.")
    
    # Reutilizamos la consulta de arriba para ser eficientes
    lista_borrar = {}
    for pid, d in datos_completos.items():
        # Generamos etiqueta segura, sin asumir que existen campos
        cant_vars = len(d.get('variantes', []))
        label = f"{d.get('modelo', '???')} - {d.get('marca','')} ({cant_vars} var.)"
        lista_borrar[label] = pid
    
    seleccion_borrar = st.selectbox("Producto a eliminar", options=list(lista_borrar.keys()))
    
    if seleccion_borrar:
        id_borrar = lista_borrar[seleccion_borrar]
        col_b1, col_b2 = st.columns([1, 4])
        if col_b1.button("🔥 Borrar", type="primary"):
            db.collection(COLECCION_PRODUCTOS).document(id_borrar).delete()
            st.toast("Producto eliminado.")
            time.sleep(1)
            st.rerun()

# ==============================================================================
# TAB 3: ELIMINAR VENTAS
# ==============================================================================
with tab_ventas:
    st.subheader("Anular Ventas")
    
    ref_movs = db.collection(COLECCION_MOVIMIENTOS)
    # Traemos ultimas 50
    docs_raw = ref_movs.order_by("fecha", direction="DESCENDING").limit(50).stream()
    
    lista_movs = []
    for doc in docs_raw:
        d = doc.to_dict()
        # Filtramos visualmente solo Ventas o Reposiciones
        if d.get('tipo') in ['Venta', 'Venta Retroactiva']:
            fecha_str = d['fecha'].strftime('%d/%m %H:%M') if d.get('fecha') else "S/F"
            # Manejo de lista de productos para el label
            prods_str = ", ".join(d.get('productos', [])) if isinstance(d.get('productos'), list) else str(d.get('producto_modelo', 'Varios'))
            
            label = f"{fecha_str} | {prods_str} | ${d.get('monto', 0):,.0f}"
            lista_movs.append((label, doc.id, d))

    if not lista_movs:
        st.info("No hay ventas recientes para anular.")
    else:
        opcion = st.selectbox("Selecciona venta a borrar", options=lista_movs, format_func=lambda x: x[0])
        
        if opcion:
            lbl, mov_id, datos_mov = opcion
            
            st.info(f"Vas a eliminar: **{lbl}**")
            st.warning("⚠️ Nota: Al borrar la venta, el dinero se descuenta de la caja, pero el STOCK NO SE REPONE automáticamente (para evitar errores en variantes). Debes reponerlo manualmente en la pestaña de Stock.")
            
            if st.button("🗑️ Confirmar Eliminación", type="primary"):
                ref_movs.document(mov_id).delete()
                st.success("Registro de venta eliminado correctamente.")
                time.sleep(1.5) # Aquí estaba el error, ahora funcionará
                st.rerun()