import streamlit as st
import pandas as pd
import os
import sys

# --- CONEXIÓN CON CONFIG.PY (RAÍZ) ---
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except ImportError:
    st.error("❌ Error de conexión con la base de datos central.")
    st.stop()

# --- CONFIGURACIÓN DE PRIVACIDAD ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

st.header(f"📋 Historial: {cliente_id.replace('_', ' ').title()}")

# --- LÓGICA DE DATOS ---
try:
    ref_movs = db.collection(COLECCION_MOVIMIENTOS)
    # Traemos los últimos 100 movimientos
    docs = ref_movs.order_by('fecha', direction='DESCENDING').limit(100).stream()

    data = []
    for doc in docs:
        d = doc.to_dict()
        # Formateamos la fecha para que sea legible en la tabla
        if 'fecha' in d and d['fecha']:
            d['fecha'] = d['fecha'].strftime("%Y-%m-%d %H:%M")
        
        # Convertimos la lista de productos en un texto separado por comas para la tabla
        if 'productos' in d and isinstance(d['productos'], list):
            d['productos'] = ", ".join(d['productos'])
            
        data.append(d)

    if data:
        df = pd.DataFrame(data)

        # Filtros en la interfaz
        st.subheader("Filtros")
        c1, c2 = st.columns(2)
        
        # Filtro por tipo (Venta, Reposición, etc.)
        tipos_disponibles = df['tipo'].unique().tolist() if 'tipo' in df.columns else []
        filtro_tipo = c1.multiselect("Tipo de Movimiento", tipos_disponibles)
        
        if filtro_tipo:
            df = df[df['tipo'].isin(filtro_tipo)]

        # --- TABLA FINAL ---
        # Definimos las columnas que queremos mostrar según lo que guardamos en Ventas
        columnas_visibles = ['fecha', 'tipo', 'productos', 'monto', 'ganancia']
        
        # Solo mostramos las columnas que realmente existan en el DataFrame
        existentes = [col for col in columnas_visibles if col in df.columns]
        
        st.dataframe(
            df[existentes],
            use_container_width=True,
            hide_index=True
        )
        
        # --- RESUMEN DE CAJA ---
        st.divider()
        col_res1, col_res2 = st.columns(2)
        total_caja = df['monto'].sum() if 'monto' in df.columns else 0
        total_ganancia = df['ganancia'].sum() if 'ganancia' in df.columns else 0
        
        col_res1.metric("Total en Caja (Filtro)", f"${total_caja:,.2f}")
        col_res2.metric("Ganancia Total (Filtro)", f"${total_ganancia:,.2f}")

    else:
        st.info("Aún no hay movimientos registrados para este cliente.")

except Exception as e:
    st.error(f"Error al cargar movimientos: {e}")