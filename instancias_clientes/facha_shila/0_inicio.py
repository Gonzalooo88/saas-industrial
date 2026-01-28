import streamlit as st
import pandas as pd
from config import db 
from datetime import datetime, date

# --- CONFIGURACIÓN DE CABECERA ---
datos_usuario = st.session_state.get('user_session', {})
nombre_usuario = datos_usuario.get('nombre', 'Socio')

c_head_1, c_head_2 = st.columns([3,1])
c_head_1.header(f"🏠 Panel Principal: {nombre_usuario}")
c_head_2.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")

# --- BOTONES DE ACCIÓN RÁPIDA ---
st.markdown("### ⚡ Acciones Rápidas")
col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("🛒 **Nueva Venta**", use_container_width=True, type="primary"):
        st.switch_page("instancias_clientes/facha_shila/1_ventas.py")

with col_b:
    if st.button("🔄 **Reponer Stock**", use_container_width=True):
        st.switch_page("instancias_clientes/facha_shila/2_stock.py")

with col_c:
    if st.button("📋 **Ver Detalles**", use_container_width=True):
        st.switch_page("instancias_clientes/facha_shila/3_movimientos.py")

st.divider()

# --- PROCESAMIENTO DE DATOS ---
ref_movs = db.collection('facha_shila_movimientos')
docs = ref_movs.stream()
data = [d.to_dict() for d in docs]

# Variables de Fecha Actual
hoy = datetime.now()
mes_actual_str = hoy.strftime('%Y-%m')

if not data:
    st.info("👋 ¡Bienvenido! Aún no hay ventas registradas.")
else:
    df = pd.DataFrame(data)
    
    # 1. Limpieza de Fechas
    df['fecha_dt'] = pd.to_datetime(df['fecha']).dt.tz_localize(None)
    df['mes_anio'] = df['fecha_dt'].dt.strftime('%Y-%m')
    
    # 2. FILTRAR: Solo datos de este mes y Ventas
    df_este_mes = df[(df['mes_anio'] == mes_actual_str) & (df['tipo'] == 'Venta')]

    # --- KPI: COMPETENCIA VENDEDORES ---
    st.subheader(f"🏆 Resumen de {hoy.strftime('%B')}") # Nombre del mes
    
    if df_este_mes.empty:
        st.warning("No hay ventas registradas en el mes actual.")
    else:
        # Métricas
        conteo_vendedores = df_este_mes['vendedor'].value_counts()
        cols_kpi = st.columns(len(conteo_vendedores) + 1)
        
        # Total Global
        cols_kpi[0].metric(
            label="Total Facturado", 
            value=f"${df_este_mes['monto_total'].sum():,.0f}",
            delta=f"{len(df_este_mes)} ventas"
        )
        
        # Por Vendedor
        idx = 1
        for vendedor, cantidad in conteo_vendedores.items():
            monto = df_este_mes[df_este_mes['vendedor'] == vendedor]['monto_total'].sum()
            if idx < len(cols_kpi):
                cols_kpi[idx].metric(label=vendedor, value=cantidad, delta=f"${monto:,.0f}")
                idx += 1

        st.markdown("---")

        # --- GRÁFICO: EVOLUCIÓN DIARIA (MEJORADO) ---
        st.subheader("📈 Ritmo de Ventas Diario")

        # A) Agrupamos ventas reales por fecha (solo la parte de la fecha, sin hora)
        ventas_por_dia = df_este_mes.groupby(df_este_mes['fecha_dt'].dt.date)['monto_total'].sum()
        
        # B) TRUCO DE INGENIERÍA: Rellenar los huecos (Gap Filling)
        # Creamos un rango desde el día 1 del mes hasta HOY
        inicio_mes = hoy.replace(day=1).date()
        fin_mes = hoy.date()
        
        # Generamos todas las fechas intermedias (1, 2, 3... 27)
        rango_fechas = pd.date_range(start=inicio_mes, end=fin_mes)
        
        # Reindexamos: Esto pone $0 en los días que no hubo ventas
        ventas_completas = ventas_por_dia.reindex(rango_fechas.date, fill_value=0)
        
        # Graficamos la serie completa
        st.line_chart(ventas_completas, color="#2980B9")
        st.caption("El gráfico muestra desde el día 1 del mes hasta hoy.")