import streamlit as st
import os
import sys
import time as tm
import itertools # Vital para combinar talles x colores x materiales
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

# Referencias a la nueva estructura anidada
ref_productos = db.collection('instancias').document(cliente_id).collection('productos')
ref_movimientos = db.collection('instancias').document(cliente_id).collection('movimientos')

st.set_page_config(page_title="Gestión de Stock", layout="wide", page_icon="📦")

# --- LÓGICA DE NEGOCIO (Esquemas Dinámicos) ---
# Aquí definimos qué pide cada categoría
CATEGORIAS = {
    "Ropa": ["Talle", "Color"],
    "Anillo": ["Material", "Talle", "Color"],
    "Collar": ["Material", "Largo", "Color"],
    "Pulsera": ["Material", "Color"],
    "Aros": ["Material", "Color"],
    "Labial": ["Tono"],
    "Accesorio Pelo": ["Color"],
    "Mascarilla": [], # Producto único sin variantes
    "Set/Conjunto": ["Talle"],
    "Otro": ["Detalle"]
}

# --- CSS MEJORADO ---
st.markdown("""
    <style>
    .stock-card { 
        background-color: white; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #e0e0e0; 
        margin-bottom: 15px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .badge-cat { 
        background-color: #e3f2fd; 
        color: #1565c0; 
        padding: 4px 8px; 
        border-radius: 12px; 
        font-size: 0.8rem; 
        font-weight: bold; 
        text-transform: uppercase;
    }
    .variant-row {
        font-size: 0.95rem;
        margin-top: 5px;
        padding: 4px;
        border-bottom: 1px dotted #eee;
    }
    .stock-high { color: #2e7d32; font-weight: bold; } /* Verde */
    .stock-low { color: #c62828; font-weight: bold; } /* Rojo */
    </style>
""", unsafe_allow_html=True)

# --- HELPER: Formatear variante para mostrar ---
def formatear_variante_texto(var_dict):
    parts = []
    # Ignoramos claves internas
    ignorar = ['stock', 'sku']
    for k, v in var_dict.items():
        if k not in ignorar:
            parts.append(str(v))
    return " - ".join(parts) if parts else "Único"

# --- PESTAÑAS PRINCIPALES ---
tab_ver, tab_reponer, tab_nuevo = st.tabs(["👁️ Visualizar Stock", "🔄 Reposición / Ajuste", "➕ Crear Nuevo Modelo"])

# ==============================================================================
# 1. VISUALIZAR STOCK
# ==============================================================================
with tab_ver:
    c1, c2 = st.columns([1, 2])
    filtro_cat = c1.selectbox("Filtrar Categoría", ["Todas"] + list(CATEGORIAS.keys()))
    busqueda = c2.text_input("Buscar por nombre o marca...", key="search_stock")
    
    # Traemos productos
    docs = ref_productos.stream()
    encontrados = False
    
    for doc in docs:
        p = doc.to_dict()
        p_id = doc.id
        
        # Filtros
        if filtro_cat != "Todas" and p.get('categoria') != filtro_cat: continue
        texto_full = f"{p.get('modelo','')} {p.get('marca','')}".lower()
        if busqueda and busqueda.lower() not in texto_full: continue
        
        encontrados = True
        variantes = p.get('variantes', [])
        total_stock = sum(v.get('stock', 0) for v in variantes)
        
        with st.container():
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="badge-cat">{p.get('categoria', 'Gral')}</span>
                        <h3 style="margin: 5px 0; color:#333;">{p.get('modelo')}</h3>
                        <span style="color:gray">Marca: {p.get('marca', 'Genérica')}</span>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.2rem; font-weight:bold;">${p.get('precio_venta', 0):,.0f}</div>
                        <div style="font-size:0.8rem; color:gray;">Costo: ${p.get('costo', 0):,.0f}</div>
                        <div style="font-size:0.8rem; color:green;">Stock Total: {total_stock}</div>
                    </div>
                </div>
                <hr style="margin:10px 0;">
            """, unsafe_allow_html=True)
            
            if not variantes:
                st.warning("⚠️ Producto sin variantes cargadas.")
            else:
                # Mostramos variantes en columnas para ahorrar espacio
                cols_vars = st.columns(3) # 3 columnas de variantes
                for i, v in enumerate(variantes):
                    col_idx = i % 3
                    desc = formatear_variante_texto(v)
                    qty = v.get('stock', 0)
                    clase_stock = "stock-high" if qty > 2 else "stock-low"
                    
                    cols_vars[col_idx].markdown(
                        f"<div class='variant-row'>{desc}: <span class='{clase_stock}'>{qty} u.</span></div>", 
                        unsafe_allow_html=True
                    )
            
            st.markdown("</div>", unsafe_allow_html=True)

    if not encontrados:
        st.info("No se encontraron productos con los filtros actuales.")

# ==============================================================================
# 2. REPOSICIÓN Y AJUSTE DE PRECIOS
# ==============================================================================
with tab_reponer:
    st.header("🔄 Reposición de Mercadería")
    st.caption("Selecciona un producto para agregar stock o cambiar sus precios.")
    
    # Selector de producto
    all_prods = list(ref_productos.stream())
    opciones_prod = {d.id: f"{d.to_dict().get('modelo')} ({d.to_dict().get('categoria')})" for d in all_prods}
    
    sel_id = st.selectbox("Buscar Producto a Reponer", options=list(opciones_prod.keys()), format_func=lambda x: opciones_prod[x])
    
    if sel_id:
        ref_doc = ref_productos.document(sel_id)
        data = ref_doc.get().to_dict()
        categoria_actual = data.get('categoria', 'Otro')
        campos_categoria = CATEGORIAS.get(categoria_actual, ["Detalle"])
        
        st.divider()
        
        # --- A. EDICIÓN DE PRECIOS ---
        c_p1, c_p2, c_p3 = st.columns(3)
        n_costo = c_p1.number_input("Costo Unitario ($)", value=float(data.get('costo', 0)))
        n_precio = c_p2.number_input("Precio Venta ($)", value=float(data.get('precio_venta', 0)))
        n_ganancia = n_precio - n_costo
        c_p3.metric("Nueva Ganancia", f"${n_ganancia:,.0f}")
        
        st.divider()
        
        # --- B. INGRESO DE STOCK ---
        st.subheader("📦 Ingresar Unidades")
        st.info(f"Campos requeridos para {categoria_actual}: {', '.join(campos_categoria)}")
        
        cols_input = st.columns(len(campos_categoria) + 1)
        inputs_repo = {}
        
        # Generamos inputs dinámicos según la categoría
        for i, campo in enumerate(campos_categoria):
            # Intentamos autocompletar con el valor más común si existe
            inputs_repo[campo] = cols_input[i].text_input(f"{campo}", key=f"repo_{campo}")
            
        cant_repo = cols_input[-1].number_input("Cantidad (+)", min_value=1, value=1)
        
        if st.button("💾 CONFIRMAR REPOSICIÓN", type="primary"):
            # 1. Validar inputs
            missing = [k for k, v in inputs_repo.items() if not v]
            if missing and categoria_actual != "Mascarilla": # Mascarilla no tiene campos
                st.error(f"Falta completar: {', '.join(missing)}")
            else:
                batch = db.batch()
                
                # Actualizar precios
                batch.update(ref_doc, {
                    "costo": n_costo,
                    "precio_venta": n_precio,
                    "ganancia": n_ganancia
                })
                
                # Actualizar variantes (Buscar si existe o crear nueva)
                vars_actuales = data.get('variantes', [])
                found = False
                desc_log = []
                
                # Normalizamos inputs para comparar
                inputs_clean = {k: v.strip().title() for k, v in inputs_repo.items()}
                
                # Buscamos coincidencia
                new_vars_list = []
                for v in vars_actuales:
                    # Comparamos solo las claves relevantes
                    coincide = True
                    for campo in campos_categoria:
                        if str(v.get(campo.lower(), '')).lower() != inputs_clean[campo].lower():
                            coincide = False
                            break
                    
                    if coincide:
                        v['stock'] += cant_repo
                        found = True
                        desc_log.append(f"{formatear_variante_texto(v)} (stock actualizado)")
                    
                    new_vars_list.append(v)
                
                # Si no existía, la agregamos
                if not found:
                    new_v = {k.lower(): v for k, v in inputs_clean.items()}
                    new_v['stock'] = cant_repo
                    new_vars_list.append(new_v)
                    desc_log.append("Nueva variante creada")

                batch.update(ref_doc, {"variantes": new_vars_list})
                
                # Registrar Movimiento (Gasto)
                gasto = n_costo * cant_repo
                mid = f"REP-{int(tm.time())}"
                
                # Texto descripción para el log
                desc_texto = f"{data['modelo']} - {', '.join(inputs_clean.values())} (+{cant_repo})"
                
                batch.set(ref_movimientos.document(mid), {
                    "tipo": "Reposición",
                    "monto": -gasto,
                    "fecha": datetime.now(),
                    "productos": [desc_texto],
                    "vendedor": st.session_state.get('usuario', 'Sistema')
                })
                
                batch.commit()
                st.success("✅ Stock actualizado correctamente.")
                tm.sleep(1.5)
                st.rerun()

# ==============================================================================
# 3. CREAR NUEVO MODELO (LÓGICA MATRIZ COMPLETA)
# ==============================================================================
with tab_nuevo:
    st.header("✨ Alta de Nuevo Producto")
    st.markdown("Define las características y el sistema generará todas las combinaciones.")
    
    # 1. Datos Básicos
    c_base1, c_base2 = st.columns(2)
    cat_sel = c_base1.selectbox("Tipo de Producto (Categoría)", list(CATEGORIAS.keys()))
    marca = c_base2.text_input("Marca")
    
    modelo = st.text_input("Nombre del Modelo (Ej: Argolla Cubana)")
    
    c_num1, c_num2, c_num3 = st.columns(3)
    costo_ini = c_num1.number_input("Costo Unitario", 0.0)
    precio_ini = c_num2.number_input("Precio Venta", 0.0)
    c_num3.metric("Ganancia Estimada", f"${precio_ini - costo_ini:,.0f}")
    
    st.divider()
    
    # 2. Generador de Variantes Dinámico
    campos = CATEGORIAS[cat_sel]
    inputs_generador = {}
    
    if not campos:
        st.info(f"El producto '{cat_sel}' se creará como ítem único (sin variantes).")
    else:
        st.write(f"📝 **Configuración de Variantes para {cat_sel}**")
        st.caption("Ingresa las opciones separadas por coma. Ej: Oro, Plata")
        
        cols_gen = st.columns(len(campos))
        for i, campo in enumerate(campos):
            val = cols_gen[i].text_input(f"{campo}(s)", placeholder="Ej: Rojo, Azul, Verde")
            if val.strip():
                # Convertimos "Rojo, Azul" en ["Rojo", "Azul"]
                inputs_generador[campo] = [x.strip().title() for x in val.split(",") if x.strip()]
    
    stock_ini = st.number_input("Stock inicial para CADA variante", min_value=1, value=1)
    
    if st.button("🚀 CREAR PRODUCTO", type="primary"):
        if not modelo or precio_ini <= 0:
            st.error("Falta el Nombre del Modelo o el Precio.")
        else:
            variantes_finales = []
            
            # CASO A: Producto Simple
            if not campos:
                variantes_finales.append({"nombre": "Único", "stock": stock_ini})
            
            # CASO B: Producto con Variantes (Matriz)
            else:
                # Validar que haya llenado todo
                if len(inputs_generador) < len(campos):
                    st.error(f"Debes completar todos los campos: {', '.join(campos)}")
                    st.stop()
                
                # Producto Cartesiano (Magia)
                keys = list(inputs_generador.keys()) # [Material, Largo]
                values = list(inputs_generador.values()) # [[Oro, Plata], [40, 50]]
                
                combinaciones = list(itertools.product(*values)) # [(Oro, 40), (Oro, 50), (Plata, 40)...]
                
                for comb in combinaciones:
                    v_dict = {}
                    for i, k in enumerate(keys):
                        v_dict[k.lower()] = comb[i]
                    v_dict['stock'] = stock_ini
                    variantes_finales.append(v_dict)
            
            # Guardado en DB
            new_id = f"PROD-{int(tm.time())}"
            payload = {
                "modelo": modelo,
                "marca": marca,
                "categoria": cat_sel,
                "costo": costo_ini,
                "precio_venta": precio_ini,
                "ganancia": precio_ini - costo_ini,
                "variantes": variantes_finales,
                "fecha_alta": datetime.now()
            }
            
            ref_productos.document(new_id).set(payload)
            
            st.success(f"✅ Producto creado con {len(variantes_finales)} combinaciones.")
            tm.sleep(2)
            st.rerun()