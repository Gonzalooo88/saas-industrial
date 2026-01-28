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

# --- BOTONES DE ACCIÓN RÁPIDA ---
st.markdown("### ⚡ Acciones Rápidas")
col_a, col_b, col_c = st.columns(3)

base_path = f"instancias_clientes/{cliente_id}"

with col_a:
    if st.button("🛒 **Nueva Venta**", use_container_width=True, type="primary"):
        st.switch_page(f"{base_path}/1_ventas.py")

with col_b:
    if st.button("🔄 **Reponer Stock**", use_container_width=True):
        st.switch_page(f"{base_path}/2_stock.py")

with col_c:
    if st.button("💵 **Ver movimientos**", use_container_width=True):
        st.switch_page(f"{base_path}/3_movimientos.py")

st.divider()

# --- PROCESAMIENTO DE DATOS ---
ref_movs = db.collection('instancias').document(cliente_id).collection('movimientos')

try:
    docs = ref_movs.stream()
    data = []
    
    for doc in docs:
        d = doc.to_dict()
        if d.get('fecha'):
            # Convertimos Timestamp a datetime python
            d['fecha_dt'] = d['fecha'].replace(tzinfo=None)
            data.append(d)

    hoy = datetime.now()
    mes_actual_str = hoy.strftime('%Y-%m')

    # --- TRADUCCIÓN MANUAL DE MESES (SOLUCIÓN) ---
    nombres_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    nombre_mes_actual = nombres_meses[hoy.month]

    if not data:
        st.info("👋 ¡Bienvenido! Aún no hay movimientos registrados.")
    else:
        df = pd.DataFrame(data)
        df['mes_anio'] = df['fecha_dt'].dt.strftime('%Y-%m')
        
        # --- FILTROS DE ESTE MES ---
        # 1. Ventas
        df_ventas = df[(df['mes_anio'] == mes_actual_str) & (df['tipo'] == 'Venta')]
        
        # 2. Reposiciones (Inversión)
        df_repo = df[(df['mes_anio'] == mes_actual_str) & (df['tipo'] == 'Reposición')]

        # --- KPI: RESUMEN FINANCIERO DEL MES ---
        # Aquí usamos la variable traducida
        st.subheader(f"🏆 Resumen de {nombre_mes_actual}")
        
        # Cálculos Generales
        total_facturado = df_ventas['monto'].sum()
        total_reinvertido = df_repo['monto'].abs().sum() 
        
        # Métricas
        kpi1, kpi2 = st.columns(2)
        
        kpi1.metric(
            label="💰 Total Facturado (Ventas)",
            value=f"${total_facturado:,.0f}",
            delta=f"{len(df_ventas)} operaciones"
        )
        
        kpi2.metric(
            label="🔄 Total Reinvertido (Stock)",
            value=f"${total_reinvertido:,.0f}",
            delta=f"{len(df_repo)} reposiciones",
            delta_color="off" 
        )
        
        st.markdown("---")

        if df_ventas.empty:
            st.warning("No hay ventas registradas en el mes actual.")
        else:
            # --- COMPETENCIA VENDEDORES ---
            st.write("#### 🥇 Rendimiento por Vendedor")
            conteo_vendedores = df_ventas['vendedor'].value_counts()
            
            cols_vend = st.columns(len(conteo_vendedores))
            
            idx = 0
            for vendedor, cantidad in conteo_vendedores.items():
                monto_vend = df_ventas[df_ventas['vendedor'] == vendedor]['monto'].sum()
                if idx < len(cols_vend):
                    cols_vend[idx].metric(
                        label=vendedor, 
                        value=f"{cantidad} vts", 
                        delta=f"${monto_vend:,.0f}"
                    )
                    idx += 1

            st.markdown("---")

            # --- GRÁFICO: EVOLUCIÓN DIARIA ---
            st.subheader("📈 Ritmo de Ventas Diario")

            ventas_por_dia = df_ventas.groupby(df_ventas['fecha_dt'].dt.date)['monto'].sum()
            
            inicio_mes = hoy.replace(day=1).date()
            fin_mes = hoy.date()
            
            if inicio_mes <= fin_mes:
                rango_fechas = pd.date_range(start=inicio_mes, end=fin_mes)
                ventas_completas = ventas_por_dia.reindex(rango_fechas.date, fill_value=0)
                
                st.line_chart(ventas_completas, color="#2980B9")
                st.caption("Facturación diaria acumulada del mes en curso.")

except Exception as e:
    st.error(f"Error cargando el dashboard: {e}")