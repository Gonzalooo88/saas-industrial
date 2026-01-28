import streamlit as st
import os
import sys
import time as tm
import itertools 
from datetime import datetime

# --- CONEXIÓN BASE DE DATOS ---
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
    st.error("🚫 Acceso denegado. Por favor inicia sesión.")
    st.stop()

cliente_id = st.session_state.carpeta_cliente

ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

st.set_page_config(page_title="Gestión de Stock", layout="wide", page_icon="📦")

# --- LÓGICA DE NEGOCIO ---
CATEGORIAS = {
    "Ropa": ["Talle", "Color"],
    "Anillo": ["Material", "Talle", "Color"],
    "Collar": ["Material", "Largo", "Color"],
    "Pulsera": ["Material", "Color"],
    "Aros": ["Material", "Color"],
    "Labial": ["Tono"],
    "Accesorio Pelo": ["Color"],
    "Mascarilla": [], 
    "Set/Conjunto": ["Talle"],
    "Otro": ["Detalle"]
}

# --- HELPER ---
def formatear_variante_texto(var_dict):
    parts = []
    ignorar = ['stock', 'sku']
    for k, v in var_dict.items():
        if k not in ignorar:
            parts.append(str(v))
    return " - ".join(parts) if parts else "Único"

# --- PESTAÑAS ---
tab_ver, tab_reponer, tab_nuevo = st.tabs(["👁️ Visualizar Stock", "🔄 Reposición / Ajuste", "➕ Crear Nuevo Modelo"])

# ==============================================================================
# 1. VISUALIZAR STOCK (VERSIÓN NATIVA SIN HTML RARO)
# ==============================================================================
with tab_ver:
    c1, c2 = st.columns([1, 2])
    filtro_cat = c1.selectbox("Filtrar Categoría", ["Todas"] + list(CATEGORIAS.keys()))
    busqueda = c2.text_input("Buscar por nombre o marca...", key="search_stock")
    
    docs = ref_productos.stream()
    encontrados = False
    
    for doc in docs:
        p = doc.to_dict()
        
        # Filtros
        if filtro_cat != "Todas" and p.get('categoria') != filtro_cat: continue
        texto_full = f"{p.get('modelo','')} {p.get('marca','')}".lower()
        if busqueda and busqueda.lower() not in texto_full: continue
        
        encontrados = True
        variantes = p.get('variantes', [])
        total_stock = sum(v.get('stock', 0) for v in variantes)
        
        # --- TARJETA NATIVA (USANDO st.container CON BORDE) ---
        # Esto crea el recuadro gris/blanco automáticamente
        with st.container(border=True):
            
            # Encabezado de la tarjeta
            col_head_1, col_head_2 = st.columns([3, 1])
            
            with col_head_1:
                # Título y detalles
                st.markdown(f"### {p.get('modelo')}")
                st.caption(f"🏷️ {p.get('categoria', 'Gral')} | Marca: {p.get('marca', 'Genérica')}")
            
            with col_head_2:
                # Precios alineados a la derecha (visualmente)
                st.markdown(f"### ${p.get('precio_venta', 0):,.0f}")
                st.caption(f"Stock Total: **{total_stock}**")

            st.divider() # Línea separadora fina
            
            # --- VARIANTES (GRILLA) ---
            if not variantes:
                st.warning("Sin variantes cargadas.")
            else:
                # Usamos columnas nativas para mostrar las variantes ordenadas
                # Creamos 4 columnas para que queden como una grilla
                cols_vars = st.columns(4)
                
                for i, v in enumerate(variantes):
                    desc = formatear_variante_texto(v)
                    qty = v.get('stock', 0)
                    
                    # Color condicional nativo de Streamlit
                    color_stock = "green" if qty > 2 else "red"
                    
                    # Escribimos en la columna correspondiente (ciclo 0,1,2,3)
                    with cols_vars[i % 4]:
                        # Usamos sintaxis de color de Streamlit: :color[texto]
                        st.markdown(f"**{desc}**")
                        st.markdown(f":{color_stock}[Stock: {qty} u.]")

    if not encontrados:
        st.info("No se encontraron productos con los filtros actuales.")

# ==============================================================================
# 2. REPOSICIÓN
# ==============================================================================
with tab_reponer:
    st.header("🔄 Reposición de Mercadería")
    
    all_prods = list(ref_productos.stream())
    if not all_prods:
        st.warning("No hay productos cargados.")
    else:
        opciones_prod = {d.id: f"{d.to_dict().get('modelo')} ({d.to_dict().get('categoria')})" for d in all_prods}
        
        sel_id = st.selectbox("Buscar Producto a Reponer", options=list(opciones_prod.keys()), format_func=lambda x: opciones_prod[x])
        
        if sel_id:
            ref_doc = ref_productos.document(sel_id)
            data = ref_doc.get().to_dict()
            categoria_actual = data.get('categoria', 'Otro')
            campos_categoria = CATEGORIAS.get(categoria_actual, ["Detalle"])
            
            st.divider()
            
            # --- PRECIOS ---
            c_p1, c_p2, c_p3 = st.columns(3)
            n_costo = c_p1.number_input("Costo Unitario ($)", value=float(data.get('costo', 0)))
            n_precio = c_p2.number_input("Precio Venta ($)", value=float(data.get('precio_venta', 0)))
            n_ganancia = n_precio - n_costo
            c_p3.metric("Nueva Ganancia", f"${n_ganancia:,.0f}")
            
            st.divider()
            
            # --- STOCK ---
            st.subheader("📦 Ingresar Stock")
            st.info(f"Campos: {', '.join(campos_categoria)}")
            
            cols_input = st.columns(len(campos_categoria) + 1)
            inputs_repo = {}
            
            for i, campo in enumerate(campos_categoria):
                inputs_repo[campo] = cols_input[i].text_input(f"{campo}", key=f"repo_{campo}")
                
            cant_repo = cols_input[-1].number_input("Cantidad (+)", min_value=1, value=1)
            
            if st.button("💾 CONFIRMAR REPOSICIÓN", type="primary"):
                missing = [k for k, v in inputs_repo.items() if not v]
                if missing and categoria_actual != "Mascarilla":
                    st.error(f"Falta: {', '.join(missing)}")
                else:
                    batch = db.batch()
                    batch.update(ref_doc, {"costo": n_costo, "precio_venta": n_precio, "ganancia": n_ganancia})
                    
                    vars_actuales = data.get('variantes', [])
                    found = False
                    inputs_clean = {k: v.strip().title() for k, v in inputs_repo.items()}
                    new_vars_list = []
                    
                    for v in vars_actuales:
                        coincide = True
                        for campo in campos_categoria:
                            if str(v.get(campo.lower(), '')).lower() != inputs_clean[campo].lower():
                                coincide = False
                                break
                        if coincide:
                            v['stock'] += cant_repo
                            found = True
                        new_vars_list.append(v)
                    
                    if not found:
                        new_v = {k.lower(): v for k, v in inputs_clean.items()}
                        new_v['stock'] = cant_repo
                        new_vars_list.append(new_v)

                    batch.update(ref_doc, {"variantes": new_vars_list})
                    
                    mid = f"REP-{int(tm.time())}"
                    desc_texto = f"{data['modelo']} - {', '.join(inputs_clean.values())} (+{cant_repo})"
                    
                    batch.set(ref_movimientos.document(mid), {
                        "tipo": "Reposición",
                        "monto": -(n_costo * cant_repo),
                        "fecha": datetime.now(),
                        "productos": [desc_texto],
                        "vendedor": st.session_state.get('usuario', 'Sistema')
                    })
                    
                    batch.commit()
                    st.success("✅ Stock actualizado.")
                    tm.sleep(1.5)
                    st.rerun()

# ==============================================================================
# 3. CREAR NUEVO
# ==============================================================================
with tab_nuevo:
    st.header("✨ Nuevo Producto")
    
    c_base1, c_base2 = st.columns(2)
    cat_sel = c_base1.selectbox("Categoría", list(CATEGORIAS.keys()))
    marca = c_base2.text_input("Marca")
    modelo = st.text_input("Nombre del Modelo")
    
    c_num1, c_num2, c_num3 = st.columns(3)
    costo_ini = c_num1.number_input("Costo", 0.0)
    precio_ini = c_num2.number_input("Precio Venta", 0.0)
    c_num3.metric("Ganancia", f"${precio_ini - costo_ini:,.0f}")
    
    st.divider()
    
    campos = CATEGORIAS[cat_sel]
    inputs_generador = {}
    
    if not campos:
        st.info(f"Producto único (sin variantes).")
    else:
        st.write(f"📝 Variantes para {cat_sel}")
        cols_gen = st.columns(len(campos))
        for i, campo in enumerate(campos):
            val = cols_gen[i].text_input(f"{campo}(s) (sep. por coma)", key=f"gen_{campo}")
            if val.strip():
                inputs_generador[campo] = [x.strip().title() for x in val.split(",") if x.strip()]
    
    stock_ini = st.number_input("Stock inicial por variante", min_value=1, value=1)
    
    if st.button("🚀 CREAR PRODUCTO", type="primary"):
        if not modelo or precio_ini <= 0:
            st.error("Falta Nombre o Precio.")
        else:
            variantes_finales = []
            if not campos:
                variantes_finales.append({"nombre": "Único", "stock": stock_ini})
            else:
                if len(inputs_generador) < len(campos):
                    st.error("Completa todos los campos.")
                    st.stop()
                
                keys = list(inputs_generador.keys())
                values = list(inputs_generador.values())
                combinaciones = list(itertools.product(*values))
                
                for comb in combinaciones:
                    v_dict = {}
                    for i, k in enumerate(keys):
                        v_dict[k.lower()] = comb[i]
                    v_dict['stock'] = stock_ini
                    variantes_finales.append(v_dict)
            
            new_id = f"PROD-{int(tm.time())}"
            payload = {
                "modelo": modelo, "marca": marca, "categoria": cat_sel,
                "costo": costo_ini, "precio_venta": precio_ini,
                "ganancia": precio_ini - costo_ini, "variantes": variantes_finales,
                "fecha_alta": datetime.now()
            }
            ref_productos.document(new_id).set(payload)
            st.success(f"✅ Creado con {len(variantes_finales)} variantes.")
            tm.sleep(1.5)
            st.rerun()