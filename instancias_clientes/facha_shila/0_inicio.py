import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

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
    st.error("🚫 Acceso denegado. Inicia sesión.")
    st.stop()

cliente_id = st.session_state.carpeta_cliente
usuario_actual = st.session_state.get('usuario', 'Usuario')

# --- CONFIGURACIÓN DE CABECERA ---
c_head_1, c_head_2 = st.columns([3,1])
with c_head_1:
    st.header(f"🏠 Panel: {cliente_id.replace('_', ' ').title()}")
    st.caption(f"👋 Hola, **{usuario_actual}**")

with c_head_2:
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")

# --- BOTONES DE ACCIÓN RÁPIDA (RUTAS DINÁMICAS) ---
st.markdown("### ⚡ Acciones Rápidas")
col_a, col_b, col_c = st.columns(3)

# Definimos las rutas relativas a la carpeta del cliente
base_path = f"instancias_clientes/{cliente_id}"

with col_a:
    if st.button("🛒 **Nueva Venta**", use_container_width=True, type="primary"):
        st.switch_page(f"{base_path}/1_ventas.py")

with col_b:
    if st.button("🔄 **Reponer Stock**", use_container_width=True):
        st.switch_page(f"{base_path}/2_stock.py")

with col_c:
    # Nota: Antes llamabas al archivo "3_movimientos.py", ahora lo estandarizamos como "3_caja.py"
    if st.button("💵 **Ver Caja**", use_container_width=True):
        st.switch_page(f"{base_path}/3_caja.py")

st.divider()

# --- PROCESAMIENTO DE DATOS (NUEVA ESTRUCTURA) ---
# 1. Buscamos en la colección anidada
ref_movs = db.collection('instancias').document(cliente_id).collection('movimientos')

try:
    docs = ref_movs.stream()
    data = []
    
    for doc in docs:
        d = doc.to_dict()
        # Normalización de fechas para Pandas
        if d.get('fecha'):
            # Convertimos Timestamp de Firebase a datetime de Python sin zona horaria
            d['fecha_dt'] = d['fecha'].replace(tzinfo=None)
            data.append(d)

    # Variables de Fecha Actual
    hoy = datetime.now()
    mes_actual_str = hoy.strftime('%Y-%m')

    if not data:
        st.info("👋 ¡Bienvenido! Aún no hay movimientos registrados en la nueva base de datos.")
    else:
        df = pd.DataFrame(data)
        
        # 2. Preparar columna mes_anio
        df['mes_anio'] = df['fecha_dt'].dt.strftime('%Y-%m')
        
        # 3. FILTRAR: Solo datos de este mes y tipo 'Venta'
        # Nota: Usamos 'monto' en lugar de 'monto_total' porque así lo guarda 1_ventas.py ahora
        df_este_mes = df[(df['mes_anio'] == mes_actual_str) & (df['tipo'] == 'Venta')]

        # --- KPI: COMPETENCIA VENDEDORES ---
        st.subheader(f"🏆 Resumen de {hoy.strftime('%B')}") # Nombre del mes
        
        if df_este_mes.empty:
            st.warning("No hay ventas registradas en el mes actual.")
        else:
            # Métricas
            conteo_vendedores = df_este_mes['vendedor'].value_counts()
            
            # Ajustamos columnas dinámicamente según cantidad de vendedores
            cols_kpi = st.columns(len(conteo_vendedores) + 1)
            
            # Total Global
            total_mes = df_este_mes['monto'].sum()
            cols_kpi[0].metric(
                label="Total Facturado", 
                value=f"${total_mes:,.0f}",
                delta=f"{len(df_este_mes)} ventas"
            )
            
            # Por Vendedor
            idx = 1
            for vendedor, cantidad in conteo_vendedores.items():
                # Filtramos por vendedor y sumamos 'monto'
                monto_vend = df_este_mes[df_este_mes['vendedor'] == vendedor]['monto'].sum()
                
                if idx < len(cols_kpi):
                    cols_kpi[idx].metric(
                        label=vendedor, 
                        value=f"{cantidad} vts", 
                        delta=f"${monto_vend:,.0f}"
                    )
                    idx += 1

            st.markdown("---")

            # --- GRÁFICO: EVOLUCIÓN DIARIA ---
            st.subheader("📈 Ritmo de Ventas Diario")

            # A) Agrupamos ventas reales por fecha
            ventas_por_dia = df_este_mes.groupby(df_este_mes['fecha_dt'].dt.date)['monto'].sum()
            
            # B) Rellenar huecos (días sin ventas)
            inicio_mes = hoy.replace(day=1).date()
            fin_mes = hoy.date()
            
            if inicio_mes <= fin_mes:
                rango_fechas = pd.date_range(start=inicio_mes, end=fin_mes)
                ventas_completas = ventas_por_dia.reindex(rango_fechas.date, fill_value=0)
                
                st.line_chart(ventas_completas, color="#2980B9")
                st.caption("El gráfico muestra la facturación diaria desde el día 1 hasta hoy.")

except Exception as e:
    st.error(f"Error cargando el dashboard: {e}")