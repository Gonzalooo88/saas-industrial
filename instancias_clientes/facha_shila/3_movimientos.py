import streamlit as st
import pandas as pd
from config import db 

st.header("📋 Historial de Movimientos")

# Filtros
c1, c2 = st.columns(2)
filtro_vendedor = c1.multiselect("Filtrar Vendedor", ["Bianca", "Luciano", "Empleado"])
# Aquí podrías agregar filtro de fecha

ref_movs = db.collection('facha_shila_movimientos')
# Ordenamos por fecha descendente
docs = ref_movs.order_by('fecha', direction='DESCENDING').limit(50).stream()

data = [doc.to_dict() for doc in docs]

if data:
    df = pd.DataFrame(data)
    
    # Aplicar filtros
    if filtro_vendedor:
        df = df[df['vendedor'].isin(filtro_vendedor)]
    
    st.dataframe(
        df[['fecha', 'producto_modelo', 'cantidad', 'monto_total', 'vendedor']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No hay movimientos registrados.")