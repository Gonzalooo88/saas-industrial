import streamlit as st
import pandas as pd
import os
import sys

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

from config import db

cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

st.header("📋 Historial de Movimientos")

docs = db.collection(COLECCION_MOVIMIENTOS).order_by('fecha', direction='DESCENDING').stream()
data = [doc.to_dict() for doc in docs]

if data:
    df = pd.DataFrame(data)
    # Formatear productos para que se vean bien
    df['productos'] = df['productos'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    
    st.dataframe(df[['fecha', 'tipo', 'productos', 'monto', 'ganancia']], use_container_width=True)
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Caja Total", f"${df['monto'].sum():,.2f}")
    c2.metric("Ganancia Total", f"${df['ganancia'].sum():,.2f}")
else:
    st.info("Sin movimientos.")