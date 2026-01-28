import streamlit as st
import pandas as pd
import datetime 
import time as tm # Usamos alias para evitar conflicto con datetime
import os
import sys

# --- CONEXIÓN CON CONFIG.PY ---
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- VERIFICACIÓN DE SESIÓN (SEGURIDAD) ---
if 'carpeta_cliente' not in st.session_state:
    st.error("🚫 Sesión no iniciada. Por favor ve al Login.")
    st.stop()

# --- CONFIGURACIÓN DE RUTAS (NUEVA ESTRUCTURA) ---
cliente_id = st.session_state.carpeta_cliente # Ej: "facha_shila"

# Referencias a las SUB-COLECCIONES (Estructura Anidada)
ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

st.header(f"⚙️ Admin: {cliente_id.replace('_', ' ').title()}")

bloqueo = st.toggle("🔓 Habilitar Edición", value=False)
if not bloqueo:
    st.info("Activa el interruptor para editar.")
    st.stop()

tab_retro, tab_producto, tab_ventas = st.tabs([
    "📅 Cargar Venta Pasada", 
    "📦 Eliminar Producto", 
    "🗑️ Eliminar Venta"
])

# ==============================================================================
# TAB 1: CARGA RETROACTIVA
# ==============================================================================
with tab_retro:
    st.subheader("Cargar venta pasada")
    
    # Usamos la nueva referencia
    docs = ref_productos.stream()
    
    opciones_productos = {}
    datos_completos = {} 
    
    for doc in docs:
        d = doc.to_dict()
        pid = doc.id
        modelo = d.get('modelo', 'Sin Nombre')
        datos_completos[pid] = d
        opciones_productos[pid] = f"{modelo} ({d.get('marca', '')})"

    with st.form("form_retro"):
        col_fecha, col_vend = st.columns(2)
        fecha_elegida = col_fecha.date_input("Fecha venta", value="today")
        vendedor = col_vend.selectbox("Vendedor", ["Dueño", "Vendedor 1", "Vendedor 2"])
        
        pid_sel = st.selectbox("Modelo", list(opciones_productos.keys()), format_func=lambda x: opciones_productos[x])
        
        idx_var = -1
        if pid_sel:
            p_data = datos_completos[pid_sel]
            vars_list = p_data.get('variantes', [])
            if vars_list:
                opts = [f"{v['talle']} - {v['color']} (Stock: {v['stock']})" for v in vars_list]
                idx_var = st.selectbox("Variante", range(len(opts)), format_func=lambda i: opts[i])
            else:
                st.warning("Sin variantes.")

        cant = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("Guardar"):
            if pid_sel and idx_var >= 0:
                try:
                    info = datos_completos[pid_sel]
                    mis_vars = info.get('variantes', [])
                    mi_var = mis_vars[idx_var]
                    
                    total = info.get('precio_venta', 0) * cant
                    ganancia = (info.get('precio_venta', 0) - info.get('costo', 0)) * cant
                    
                    # Restar Stock en memoria
                    mis_vars[idx_var]['stock'] -= cant
                    
                    batch = db.batch()
                    # Actualizar Producto
                    batch.update(ref_productos.document(pid_sel), {"variantes": mis_vars})
                    
                    # Fecha con hora fija (usando datetime.time explícito)
                    hora_fija = datetime.time(12, 0, 0)
                    fecha_full = datetime.datetime.combine(fecha_elegida, hora_fija)
                    
                    desc = f"{info['modelo']} ({mi_var['talle']} {mi_var['color']})"
                    
                    # Guardar Movimiento
                    batch.add(ref_movimientos, {
                        "fecha": fecha_full,
                        "tipo": "Venta Retroactiva",
                        "productos": [desc],
                        "monto": total,
                        "ganancia": ganancia,
                        "vendedor": vendedor
                    })
                    
                    batch.commit()
                    st.success("Guardado.")
                    tm.sleep(1) # Pausa segura para ver el mensaje
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

# ==============================================================================
# TAB 2: BORRAR PRODUCTO
# ==============================================================================
with tab_producto:
    st.subheader("Borrar Producto")
    
    lista_borrar = {}
    for pid, d in datos_completos.items():
        n_vars = len(d.get('variantes', []))
        lbl = f"{d.get('modelo')} ({n_vars} vars)"
        lista_borrar[lbl] = pid
    
    sel_del = st.selectbox("Elegir producto", list(lista_borrar.keys()))
    
    if sel_del:
        id_del = lista_borrar[sel_del]
        if st.button("🔥 Eliminar Definitivamente", type="primary"):
            ref_productos.document(id_del).delete()
            st.toast("Producto eliminado")
            tm.sleep(1)
            st.rerun()

# ==============================================================================
# TAB 3: BORRAR VENTA
# ==============================================================================
with tab_ventas:
    st.subheader("Anular Venta")
    
    # Usamos la nueva referencia de movimientos
    docs_m = ref_movimientos.order_by("fecha", direction="DESCENDING").limit(50).stream()
    
    lista_m = []
    for doc in docs_m:
        d = doc.to_dict()
        if d.get('tipo') in ['Venta', 'Venta Retroactiva']:
            f_obj = d.get('fecha')
            f_str = f_obj.strftime('%d/%m %H:%M') if f_obj else "S/F"
            
            prods = d.get('productos', [])
            p_txt = ", ".join(prods) if isinstance(prods, list) else str(d.get('producto_modelo', 'Varios'))
            
            lbl = f"{f_str} | {p_txt} | ${d.get('monto', 0):,.0f}"
            lista_m.append((lbl, doc.id))

    if not lista_m:
        st.info("No hay ventas recientes.")
    else:
        opcion = st.selectbox("Selecciona venta", lista_m, format_func=lambda x: x[0])
        
        if opcion:
            lbl_sel, id_mov = opcion
            st.error(f"Vas a borrar: {lbl_sel}")
            st.caption("Nota: El stock NO se repone automáticamente.")
            
            if st.button("🗑️ Confirmar Borrado", type="primary"):
                ref_movimientos.document(id_mov).delete()
                st.toast("Venta eliminada") 
                tm.sleep(1)
                st.rerun()