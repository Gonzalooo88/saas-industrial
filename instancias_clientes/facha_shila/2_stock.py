import streamlit as st
import pandas as pd
from config import db 

st.header("📦 Gestión de Inventario")

ref_stock = db.collection('facha_shila_productos')

# Tabs principales
tab_lista, tab_reponer, tab_nuevo = st.tabs(["🔎 Buscador Avanzado", "🔄 Reponer Stock", "✨ Crear Nuevo Modelo"])

# ==============================================================================
# TAB 1: BUSCADOR CON FILTROS (LA NOVEDAD)
# ==============================================================================
with tab_lista:
    # 1. Traer datos
    docs = ref_stock.stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        data.append(d)
        
    if data:
        df = pd.DataFrame(data)
        
        # --- ZONA DE FILTROS ---
        with st.expander("🎛️ Filtros de Búsqueda", expanded=True):
            c1, c2, c3 = st.columns(3)
            
            # Sacamos listas únicas ordenadas para los selectores
            lista_modelos = sorted(df['modelo'].unique())
            lista_colores = sorted(df['color'].unique())
            lista_talles = sorted(df['talle'].unique())
            
            # Multiselect permite elegir varios (Ej: "Negro" y "Azul" al mismo tiempo)
            filtro_modelo = c1.multiselect("Modelo", lista_modelos)
            filtro_color = c2.multiselect("Color", lista_colores)
            filtro_talle = c3.multiselect("Talle", lista_talles)
        
        # --- APLICACIÓN DE FILTROS ---
        df_filtrado = df.copy()
        
        if filtro_modelo:
            df_filtrado = df_filtrado[df_filtrado['modelo'].isin(filtro_modelo)]
            
        if filtro_color:
            df_filtrado = df_filtrado[df_filtrado['color'].isin(filtro_color)]
            
        if filtro_talle:
            df_filtrado = df_filtrado[df_filtrado['talle'].isin(filtro_talle)]
            
        # --- RESULTADOS ---
        st.markdown(f"### Resultados: **{len(df_filtrado)}** productos encontrados")
        
        # Tabla Principal
        st.dataframe(
            df_filtrado[['modelo', 'color', 'talle', 'stock_actual', 'precio_venta']],
            use_container_width=True,
            hide_index=True
        )
        
        # --- MÉTRICAS DEL FILTRO (Valor Agregado) ---
        # Esto le sirve al dueño para saber "Cuánta plata tengo en Jeans"
        st.divider()
        total_unidades = df_filtrado['stock_actual'].sum()
        valor_estimado = (df_filtrado['stock_actual'] * df_filtrado['precio_venta']).sum()
        
        m1, m2 = st.columns(2)
        m1.metric("Stock Visible", f"{total_unidades} u.")
        m2.metric("Valor de Venta Estimado", f"${valor_estimado:,.0f}")
        
    else:
        st.info("El inventario está vacío. Ve a la pestaña 'Crear Nuevo Modelo'.")

# ==============================================================================
# TAB 2: REPONER (Lógica anterior mejorada)
# ==============================================================================
with tab_reponer:
    st.write("Usa esto cuando llegue mercadería de algo que YA existe.")
    
    if data:
        # Selector inteligente: Modelo + Color + Talle
        # Ordenamos la lista para que sea fácil buscar
        opciones_raw = [(f"{d['modelo']} | {d['color']} {d['talle']}", d['id']) for d in data]
        opciones_raw.sort() # Orden alfabético
        
        etiquetas = [x[0] for x in opciones_raw]
        ids = [x[1] for x in opciones_raw]
        
        seleccion_idx = st.selectbox("Buscar Prenda a Reponer", range(len(etiquetas)), format_func=lambda x: etiquetas[x])
        
        if seleccion_idx is not None:
            id_prod = ids[seleccion_idx]
            prod_actual = next((item for item in data if item["id"] == id_prod), None)
            
            st.info(f"Stock actual: **{prod_actual['stock_actual']}** unidades")
            
            c_cant, c_btn = st.columns([1, 2])
            cantidad_sumar = c_cant.number_input("Ingreso (+)", min_value=1, value=5)
            
            if c_btn.button("📥 Sumar al Stock", use_container_width=True):
                nuevo_total = prod_actual['stock_actual'] + cantidad_sumar
                ref_stock.document(id_prod).update({"stock_actual": nuevo_total})
                st.success(f"¡Listo! Ahora hay {nuevo_total} unidades.")
                st.rerun()
    else:
        st.warning("No hay productos para reponer.")

# ==============================================================================
# TAB 3: ALTA NUEVO (Igual que antes)
# ==============================================================================
with tab_nuevo:
    st.caption("Solo para modelos/colores que NO existen en el sistema.")
    with st.form("alta_producto"):
        c1, c2 = st.columns(2)
        modelo = c1.text_input("Nombre Modelo (Ej: Remera Basic)")
        color = c2.text_input("Color (Ej: Rojo)") 
        # Cambié Color a text_input para dar más libertad, o puedes dejar el selectbox si prefieres
        
        c3, c4 = st.columns(2)
        talle = c3.selectbox("Talle", ["XS", "S", "M", "L", "XL", "XXL", "Único", "38", "40", "42", "44"])
        stock = c4.number_input("Stock Inicial", min_value=1)
        
        precio = st.number_input("Precio Venta ($)", min_value=0.0)
        
        if st.form_submit_button("💾 Guardar Nuevo Producto"):
            if modelo and color:
                ref_stock.add({
                    "modelo": modelo,
                    "color": color,
                    "talle": talle,
                    "stock_actual": stock,
                    "precio_venta": precio,
                    "descripcion": ""
                })
                st.success("✅ Producto creado exitosamente.")
                st.rerun()
            else:
                st.error("Falta el modelo o el color.")