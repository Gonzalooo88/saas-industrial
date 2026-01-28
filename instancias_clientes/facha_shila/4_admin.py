import streamlit as st
import os
import sys
import time

# --- CONEXIÓN CON CONFIG.PY (RAÍZ) ---
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

try:
    from config import db
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- CONFIGURACIÓN DE PRIVACIDAD ---
cliente_id = os.path.basename(os.path.dirname(__file__))
COLECCION_PRODUCTOS = f"{cliente_id}_productos"
COLECCION_MOVIMIENTOS = f"{cliente_id}_movimientos"
COLECCION_VENTAS = f"{cliente_id}_ventas"

st.set_page_config(page_title="Panel Admin", layout="centered", page_icon="🔧")

st.title(f"🔧 Administración: {cliente_id.replace('_', ' ').title()}")
st.warning("⚠️ Zona de peligro: Las acciones aquí son irreversibles.")

tab_borrar_prod, tab_reset = st.tabs(["🗑️ Eliminar Productos", "🔥 Resetear Todo"])

# ==========================================
# TAB 1: ELIMINAR PRODUCTOS ESPECÍFICOS
# ==========================================
with tab_borrar_prod:
    st.subheader("Baja de Artículos")
    
    # Obtenemos todos los productos
    docs = db.collection(COLECCION_PRODUCTOS).stream()
    opciones = {}
    
    for doc in docs:
        d = doc.to_dict()
        p_id = doc.id
        
        # LÓGICA BLINDADA: Si falta algún dato, ponemos un texto genérico
        modelo = d.get('modelo', 'Sin Nombre')
        marca = d.get('marca', '')
        
        # Detectar si es formato nuevo (variantes) o viejo
        if 'variantes' in d:
            info_extra = f"({len(d['variantes'])} variantes)"
        elif 'detalles' in d:
            info_extra = "(Formato antiguo)"
        else:
            info_extra = "(Datos incompletos)"
            
        label = f"{modelo} {marca} - {info_extra}"
        opciones[label] = p_id

    if not opciones:
        st.info("No hay productos cargados en la base de datos.")
    else:
        seleccion = st.selectbox("Selecciona el producto a eliminar:", list(opciones.keys()))
        
        if st.button("🗑️ Eliminar Producto Seleccionado", type="primary"):
            id_a_borrar = opciones[seleccion]
            try:
                db.collection(COLECCION_PRODUCTOS).document(id_a_borrar).delete()
                st.success("✅ Producto eliminado correctamente.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar: {e}")

# ==========================================
# TAB 2: RESET TOTAL (ÚTIL PARA LIMPIAR PRUEBAS)
# ==========================================
with tab_reset:
    st.error("☢️ ZONA PELIGROSA: ESTO BORRARÁ TODO")
    st.write("Utiliza esto solo si quieres limpiar la base de datos completa para empezar de cero con el nuevo sistema.")
    
    check_seguridad = st.checkbox("Soy consciente de que perderé todo el stock y las ventas.")
    
    if st.button("🔥 BORRAR BASE DE DATOS COMPLETA") and check_seguridad:
        with st.status("Limpiando base de datos...", expanded=True) as status:
            batch = db.batch()
            count = 0
            
            # Borrar Productos
            docs_p = db.collection(COLECCION_PRODUCTOS).list_documents()
            for d in docs_p:
                d.delete()
                count += 1
            st.write(f"Eliminados {count} productos.")
            
            # Borrar Movimientos
            docs_m = db.collection(COLECCION_MOVIMIENTOS).list_documents()
            for d in docs_m:
                d.delete()
            st.write("Historial de movimientos eliminado.")
            
            status.update(label="¡Limpieza completada!", state="complete", expanded=False)
            
        st.success("El sistema ha quedado limpio como el día 1.")
        time.sleep(2)
        st.rerun()