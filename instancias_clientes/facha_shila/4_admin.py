import streamlit as st
import pandas as pd
import datetime 
import time as tm
import os
import sys

# --- CONEXIÓN ---
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
    st.error("🚫 Acceso denegado.")
    st.stop()

cliente_id = st.session_state.carpeta_cliente
ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

st.header(f"⚙️ Admin: {cliente_id.replace('_', ' ').title()}")

bloqueo = st.toggle("🔓 Habilitar Edición", value=False)
if not bloqueo:
    st.info("Activa el interruptor para editar.")
    st.stop()

# --- HELPER INTELIGENTE ---
def formatear_variante_admin(var_dict):
    """Crea un texto legible de la variante sin importar qué atributos tenga"""
    partes = [] 
    ignorar = ['stock', 'sku']
    for k, v in var_dict.items():
        if k not in ignorar:
            partes.append(str(v))
    return " - ".join(partes) if partes else "Único"

tab_retro, tab_producto, tab_ventas = st.tabs([
    "📅 Cargar Venta Pasada", 
    "📦 Eliminar Producto", 
    "🗑️ Eliminar Movimiento (Venta/Repo)" # <-- Nombre actualizado
])

# ==============================================================================
# TAB 1: CARGA RETROACTIVA
# ==============================================================================
with tab_retro:
    st.subheader("Cargar venta pasada")
    
    docs = ref_productos.stream()
    opciones_productos = {}
    datos_completos = {} 
    
    for doc in docs:
        d = doc.to_dict()
        pid = doc.id
        modelo = d.get('modelo', 'Sin Nombre')
        datos_completos[pid] = d
        opciones_productos[pid] = f"{modelo} ({d.get('categoria', 'Gral')})"

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
                opts = []
                for v in vars_list:
                    desc = formatear_variante_admin(v)
                    stock = v.get('stock', 0)
                    opts.append(f"{desc} (Stock actual: {stock})")
                
                idx_var = st.selectbox("Variante vendida", range(len(opts)), format_func=lambda i: opts[i])
            else:
                st.warning("Este producto no tiene variantes configuradas.")

        cant = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.form_submit_button("Guardar Venta Histórica"):
            if pid_sel and idx_var >= 0:
                try:
                    info = datos_completos[pid_sel]
                    mis_vars = info.get('variantes', [])
                    mi_var = mis_vars[idx_var]
                    
                    # Cálculos
                    precio = info.get('precio_venta', 0)
                    costo = info.get('costo', 0)
                    total = precio * cant
                    ganancia = (precio - costo) * cant
                    
                    # Restar Stock
                    mis_vars[idx_var]['stock'] -= cant
                    
                    batch = db.batch()
                    batch.update(ref_productos.document(pid_sel), {"variantes": mis_vars})
                    
                    # Fecha con hora fija mediodía
                    hora_fija = datetime.time(12, 0, 0)
                    fecha_full = datetime.datetime.combine(fecha_elegida, hora_fija)
                    
                    desc_txt = f"{info['modelo']} ({formatear_variante_admin(mi_var)})"
                    
                    batch.add(ref_movimientos, {
                        "fecha": fecha_full,
                        "tipo": "Venta Retroactiva",
                        "productos": [desc_txt],
                        "monto": total,
                        "ganancia": ganancia,
                        "vendedor": vendedor
                    })
                    
                    batch.commit()
                    st.success("Guardado correctamente.")
                    tm.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ==============================================================================
# TAB 2: BORRAR PRODUCTO
# ==============================================================================
with tab_producto:
    st.subheader("Borrar Producto")
    
    lista_borrar = {}
    for pid, d in datos_completos.items():
        n_vars = len(d.get('variantes', []))
        lbl = f"{d.get('modelo')} - {d.get('categoria')} ({n_vars} vars)"
        lista_borrar[lbl] = pid
    
    if not lista_borrar:
        st.info("No hay productos.")
    else:
        sel_del = st.selectbox("Elegir producto a eliminar", list(lista_borrar.keys()))
        
        if sel_del:
            id_del = lista_borrar[sel_del]
            if st.button("🔥 Eliminar Definitivamente", type="primary"):
                ref_productos.document(id_del).delete()
                st.toast("Producto eliminado")
                tm.sleep(1)
                st.rerun()

# ==============================================================================
# TAB 3: BORRAR MOVIMIENTO (VENTA O REPOSICIÓN)
# ==============================================================================
with tab_ventas:
    st.subheader("Anular Movimiento (Venta o Reposición)")
    st.markdown("Aquí puedes eliminar tanto ventas mal cobradas como reposiciones de stock erróneas.")
    
    # Traemos los últimos 50 movimientos de CUALQUIER tipo
    docs_m = ref_movimientos.order_by("fecha", direction="DESCENDING").limit(50).stream()
    
    lista_m = []
    for doc in docs_m:
        d = doc.to_dict()
        tipo = d.get('tipo', 'Desconocido')
        
        # Filtramos solo lo que nos interesa borrar
        if tipo in ['Venta', 'Venta Retroactiva', 'Reposición']:
            f_obj = d.get('fecha')
            f_str = f_obj.strftime('%d/%m %H:%M') if f_obj else "S/F"
            
            prods = d.get('productos', [])
            p_txt = ", ".join(prods) if isinstance(prods, list) else str(d.get('producto_modelo', 'Varios'))
            monto = d.get('monto', 0)
            
            # Icono visual para distinguir rápido
            icono = "🟢" if monto > 0 else "🔴" # Verde ingreso, Rojo gasto
            
            lbl = f"{icono} {tipo} | {f_str} | {p_txt} | ${abs(monto):,.0f}"
            lista_m.append((lbl, doc.id, tipo))

    if not lista_m:
        st.info("No hay movimientos recientes.")
    else:
        opcion = st.selectbox("Selecciona movimiento a anular", lista_m, format_func=lambda x: x[0])
        
        if opcion:
            lbl_sel, id_mov, tipo_mov = opcion
            
            st.divider()
            st.error(f"Vas a eliminar: {lbl_sel}")
            
            if tipo_mov == 'Reposición':
                st.warning("⚠️ Al borrar una reposición, el dinero reinvertido desaparecerá del gráfico, PERO el stock agregado NO se descontará solo. Debes ajustarlo manualmente si es necesario.")
            else:
                st.warning("⚠️ Al borrar una venta, el dinero desaparecerá de la caja, PERO el stock NO se devuelve solo.")
            
            if st.button("🗑️ Confirmar Borrado", type="primary"):
                ref_movimientos.document(id_mov).delete()
                st.toast("Movimiento eliminado correctamente") 
                tm.sleep(1.5)
                st.rerun()