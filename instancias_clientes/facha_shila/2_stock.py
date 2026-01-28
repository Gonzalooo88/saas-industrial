import streamlit as st
import os
import sys
import time
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

# --- CONFIGURACIÓN ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"

st.set_page_config(page_title="Stock Matrix", layout="wide")
st.title("📦 Gestión de Stock (Matriz Talle/Color)")

# Estilos CSS para las tarjetas matriciales
st.markdown("""
    <style>
    .model-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 15px; background: white; }
    .model-title { font-size: 1.2em; font-weight: bold; color: #1f77b4; }
    .variant-group { margin-left: 15px; margin-top: 5px; font-size: 0.95em; }
    .variant-tag { background-color: #f0f2f6; padding: 2px 8px; border-radius: 4px; margin-right: 5px; border: 1px solid #ccc;}
    .stock-ok { color: green; font-weight: bold; }
    .stock-low { color: red; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- PESTAÑAS ---
tab_ver, tab_reponer, tab_nuevo = st.tabs(["👁️ Visualizar Stock", "🔄 Reposición / Ajuste Precios", "➕ Crear Nuevo Modelo"])

# ==============================================================================
# 1. PESTAÑA VISUALIZAR (TARJETAS DETALLADAS)
# ==============================================================================
with tab_ver:
    st.caption("Vista detallada por Modelo > Talle > Color")
    
    # Buscador
    query = st.text_input("Buscar modelo...", key="search_view")
    
    docs = db.collection(COLECCION_PRODUCTOS).stream()
    encontrados = False
    
    for doc in docs:
        p = doc.to_dict()
        if query and query.lower() not in p['modelo'].lower():
            continue
            
        encontrados = True
        variantes = p.get('variantes', []) # Lista de diccionarios: [{'talle': 'L', 'color': 'Negro', 'stock': 3}, ...]
        
        with st.container():
            st.markdown(f"""<div class="model-card">
            <div class="model-title">{p['modelo']} <span style="font-size:0.8em; color:gray">({p.get('marca','')})</span></div>
            <div style="margin-bottom:10px;">
                <b>Venta:</b> ${p['precio_venta']:,.2f} | 
                <b>Ganancia unit.:</b> ${p['ganancia']:,.2f}
            </div>
            """, unsafe_allow_html=True)
            
            if not variantes:
                st.warning("Este producto no tiene variantes cargadas (Sistema antiguo).")
            else:
                # LÓGICA DE AGRUPACIÓN: Queremos mostrar: L: (Negro) 3, (Azul) 2
                # Primero agrupamos por talle
                talles_unicos = sorted(list(set(v['talle'] for v in variantes)))
                
                for t in talles_unicos:
                    # Filtramos las variantes de este talle
                    vars_talle = [v for v in variantes if v['talle'] == t]
                    
                    # Construimos el string "(Negro) 3, (Azul) 2"
                    detalles_txt = ""
                    total_talle = 0
                    for v in vars_talle:
                        qty = v['stock']
                        total_talle += qty
                        color_style = "stock-low" if qty <= 2 else "stock-ok"
                        detalles_txt += f"({v['color']}) <span class='{color_style}'>{qty}</span> &nbsp; "
                    
                    st.markdown(f"""
                    <div class="variant-group">
                        <span class="variant-tag"><b>{t}</b></span> {detalles_txt}
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    if not encontrados:
        st.info("No hay productos que coincidan o el inventario está vacío.")

# ==============================================================================
# 2. PESTAÑA REPOSICIÓN Y PRECIOS (SEPARADA Y CON INVERSIÓN)
# ==============================================================================
with tab_reponer:
    st.header("🔄 Reposición de Mercadería")
    st.info("Selecciona el modelo, actualiza costos si cambiaron y añade el stock entrante.")
    
    # 1. Seleccionar Producto
    all_products = list(db.collection(COLECCION_PRODUCTOS).stream())
    opciones = {doc.id: f"{doc.to_dict()['modelo']}" for doc in all_products}
    
    sel_id = st.selectbox("Seleccionar Modelo a Reponer:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
    
    if sel_id:
        # Cargamos datos actuales de Firebase
        ref_p = db.collection(COLECCION_PRODUCTOS).document(sel_id)
        data_p = ref_p.get().to_dict()
        current_vars = data_p.get('variantes', [])
        
        st.divider()
        
        # 2. Actualización de Precios (Autocompletado con lo último)
        col_pre1, col_pre2, col_pre3 = st.columns(3)
        new_costo = col_pre1.number_input("Costo de Reposición ($)", value=float(data_p.get('costo', 0)), step=50.0)
        new_precio = col_pre2.number_input("Nuevo Precio Venta ($)", value=float(data_p.get('precio_venta', 0)), step=50.0)
        
        new_ganancia = new_precio - new_costo
        col_pre3.metric("Nueva Ganancia", f"${new_ganancia:,.2f}", delta=f"{new_ganancia - data_p.get('ganancia', 0):.2f}")
        
        st.divider()
        
        # 3. Selección de Variante a Reponer
        st.subheader("📦 ¿Qué está entrando?")
        
        # Creamos opciones basadas en lo que ya existe + opción de nueva variante
        c_var1, c_var2, c_var3 = st.columns(3)
        
        # Detectamos talles y colores existentes
        existentes_talles = sorted(list(set(v['talle'] for v in current_vars)))
        existentes_colores = sorted(list(set(v['color'] for v in current_vars)))
        
        talle_rep = c_var1.text_input("Talle (ej: L, 42, Único)", value=existentes_talles[0] if existentes_talles else "")
        color_rep = c_var2.text_input("Color (ej: Negro, Rojo)", value=existentes_colores[0] if existentes_colores else "")
        cantidad_rep = c_var3.number_input("Cantidad a Ingresar", min_value=1, step=1)
        
        if st.button("💾 CONFIRMAR REPOSICIÓN"):
            batch = db.batch()
            
            # A. Actualizar Precios Globales del Modelo
            update_data = {
                "costo": new_costo,
                "precio_venta": new_precio,
                "ganancia": new_ganancia
            }
            
            # B. Actualizar Array de Variantes
            found = False
            new_variantes_list = []
            
            # Recorremos para ver si sumamos a uno existente
            for v in current_vars:
                if v['talle'].lower() == talle_rep.lower() and v['color'].lower() == color_rep.lower():
                    v['stock'] += cantidad_rep
                    found = True
                new_variantes_list.append(v)
            
            # Si no existía esa combinación, la creamos
            if not found:
                new_variantes_list.append({
                    "talle": talle_rep.upper(),
                    "color": color_rep.title(),
                    "stock": cantidad_rep
                })
            
            update_data['variantes'] = new_variantes_list
            batch.update(ref_p, update_data)
            
            # C. Registrar Movimiento (Con inversión)
            inversion_total = new_costo * cantidad_rep
            mov_id = f"REP-{int(time.time())}"
            batch.set(db.collection(COLECCION_MOVIMIENTOS).document(mov_id), {
                "tipo": "Reposición",
                "monto": -inversion_total, # Negativo porque es gasto/inversión
                "costo_unitario": new_costo,
                "ganancia": 0,
                "productos": [f"{data_p['modelo']} {talle_rep}-{color_rep} (+{cantidad_rep})"],
                "fecha": datetime.now()
            })
            
            batch.commit()
            st.success(f"✅ Se ingresaron {cantidad_rep} unidades de {talle_rep}-{color_rep}.")
            st.toast(f"Inversión registrada: ${inversion_total}")
            time.sleep(1.5)
            st.rerun()

# ==============================================================================
# 3. PESTAÑA NUEVO MODELO (MATRIZ INICIAL)
# ==============================================================================
with tab_nuevo:
    st.subheader("Crear Nuevo Modelo (Matriz)")
    
    # ⚠️ TRUCO PARA TIEMPO REAL: NO USAR st.form PARA LOS PRECIOS
    # Usamos columnas directas para que al escribir, se calcule.
    col_main1, col_main2 = st.columns(2)
    new_mod_nombre = col_main1.text_input("Nombre del Modelo", key="n_mod")
    new_mod_marca = col_main2.text_input("Marca", key="n_mar")
    
    col_cost1, col_cost2, col_cost3 = st.columns(3)
    # Inputs FUERA de form
    n_costo = col_cost1.number_input("Costo ($)", min_value=0.0, key="n_cost")
    n_precio = col_cost2.number_input("Precio Venta ($)", min_value=0.0, key="n_prec")
    
    # Métrica reactiva
    n_ganancia = n_precio - n_costo
    col_cost3.metric("Ganancia Estimada", f"${n_ganancia:,.2f}", delta_color="normal")

    st.divider()
    
    st.write("📝 **Carga Inicial de Variantes**")
    st.caption("Define qué variantes (combinaciones) vas a crear inicialmente.")
    
    # Generador de variantes iniciales
    c_gen1, c_gen2 = st.columns(2)
    talles_input = c_gen1.text_input("Talles (separados por coma)", placeholder="S, M, L, XL")
    colores_input = c_gen2.text_input("Colores (separados por coma)", placeholder="Negro, Blanco, Rojo")
    stock_init = st.number_input("Stock inicial para CADA combinación", min_value=0, value=1)
    
    if st.button("💾 CREAR MODELO"):
        if new_mod_nombre and n_precio > 0:
            # Procesar variantes
            lista_talles = [t.strip().upper() for t in talles_input.split(",") if t.strip()]
            lista_colores = [c.strip().title() for c in colores_input.split(",") if c.strip()]
            
            variantes_generadas = []
            
            if not lista_talles or not lista_colores:
                # Caso simple sin variantes complejas
                variantes_generadas.append({"talle": "Único", "color": "Único", "stock": stock_init})
            else:
                # Crear matriz (Todos con Todos)
                for t in lista_talles:
                    for c in lista_colores:
                        variantes_generadas.append({
                            "talle": t,
                            "color": c,
                            "stock": stock_init
                        })
            
            # Guardar en DB
            p_id = f"PROD-{int(time.time())}"
            payload = {
                "modelo": new_mod_nombre,
                "marca": new_mod_marca,
                "costo": n_costo,
                "precio_venta": n_precio,
                "ganancia": n_ganancia,
                "categoria": "General", # Puedes agregar selectbox si quieres
                "variantes": variantes_generadas,
                "fecha_alta": datetime.now()
            }
            db.collection(COLECCION_PRODUCTOS).document(p_id).set(payload)
            
            st.success(f"✅ Modelo {new_mod_nombre} creado con {len(variantes_generadas)} variantes.")
            st.canvas = None # Limpiar
            time.sleep(1)
            st.rerun()
        else:
            st.error("Faltan datos obligatorios (Nombre o Precio).")