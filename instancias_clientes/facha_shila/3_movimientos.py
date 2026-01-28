import streamlit as st
import pandas as pd
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

# --- SEGURIDAD: VERIFICAR SESIÓN ---
if 'carpeta_cliente' not in st.session_state:
    st.error("🚫 Acceso denegado. Debes iniciar sesión desde el menú principal.")
    st.stop()

# --- CONFIGURACIÓN DE RUTAS (NUEVA ESTRUCTURA) ---
cliente_id = st.session_state.carpeta_cliente # Obtenemos el ID del login (ej: facha_shila)

# Referencia a la SUB-COLECCIÓN ordenada: instancias/facha_shila/movimientos
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

# --- INTERFAZ ---
st.header(f"📋 Historial: {cliente_id.replace('_', ' ').title()}")

try:
    # Traemos los datos de la carpeta correcta
    docs = ref_movimientos.order_by('fecha', direction='DESCENDING').stream()
    data = []
    
    for doc in docs:
        d = doc.to_dict()
        # Procesamos la fecha para que se vea bien (sin zona horaria rara)
        if 'fecha' in d and d['fecha']:
            d['fecha_str'] = d['fecha'].strftime('%d/%m/%Y %H:%M')
        else:
            d['fecha_str'] = "S/F"
        data.append(d)

    if data:
        df = pd.DataFrame(data)
        
        # Formatear productos (Lista -> String legible)
        df['productos'] = df['productos'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        
        # Formatear números para tabla
        # (Opcional: puedes dejar los números crudos si quieres ordenar)
        
        # Mostrar Tabla
        # Seleccionamos columnas clave y renombramos para que se vea bonito
        st.dataframe(
            df[['fecha_str', 'tipo', 'productos', 'monto', 'ganancia', 'vendedor']], 
            column_config={
                "fecha_str": "Fecha",
                "tipo": "Movimiento",
                "productos": "Detalle",
                "monto": st.column_config.NumberColumn("Total", format="$%.2f"),
                "ganancia": st.column_config.NumberColumn("Ganancia", format="$%.2f"),
                "vendedor": "Usuario"
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Métricas Totales
        c1, c2, c3 = st.columns(3)
        total_caja = df['monto'].sum()
        total_ganancia = df['ganancia'].sum() if 'ganancia' in df.columns else 0
        
        c1.metric("💰 Caja Total", f"${total_caja:,.2f}")
        c2.metric("📈 Ganancia Total", f"${total_ganancia:,.2f}")
        c3.metric("🧾 Movimientos", len(df))
        
    else:
        st.info("No hay movimientos registrados en esta cuenta.")

except Exception as e:
    st.error(f"Error cargando movimientos: {e}")