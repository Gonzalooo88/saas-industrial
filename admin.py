import streamlit as st
import pandas as pd
import datetime 
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

# --- CONFIGURACIÓN ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

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
    
    ref_stock = db.collection(COLECCION_PRODUCTOS)
    docs = ref_stock.stream()
    
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
                    
                    mis_vars[idx_var]['stock'] -= cant
                    
                    batch = db.batch()
                    batch.update(ref_stock.document(pid_sel), {"variantes": mis_vars})
                    
                    hora_fija = datetime.time(12, 0, 0)
                    fecha_full = datetime.datetime.combine(fecha_elegida, hora_fija)
                    
                    desc = f"{info['modelo']} ({mi_var['talle']} {mi_var['color']})"
                    
                    batch.add(db.collection(COLECCION_MOVIMIENTOS), {
                        "fecha": fecha_full,
                        "tipo": "Venta Retroactiva",
                        "productos": [desc],
                        "monto": total,
                        "ganancia": ganancia,
                        "vendedor": vendedor
                    })
                    
                    batch.commit()
                    st.success("Guardado.")
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
            db.collection(COLECCION_PRODUCTOS).document(id_del).delete()
            st.toast("Producto eliminado")
            st.rerun()

# ==============================================================================
# TAB 3: BORRAR VENTA
# ==============================================================================
with tab_ventas:
    st.subheader("Anular Venta")
    
    ref_movs = db.collection(COLECCION_MOVIMIENTOS)
    docs_m = ref_movs.order_by("fecha", direction="DESCENDING").limit(50).stream()
    
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
                ref_movs.document(id_mov).delete()
                st.toast("Venta eliminada") 
                st.rerun()