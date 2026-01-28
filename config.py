import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

def get_db():
    # Verificamos si ya está inicializado para no dar error
    if not firebase_admin._apps:
        try:
            # 1. INTENTO NUBE: Buscamos en los Secretos de Streamlit
            # Esto funcionará cuando la app esté online
            key_dict = json.loads(st.secrets["firebase"]["text_key"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            # print("Conectado vía Streamlit Secrets (Nube)")
            
        except Exception:
            # 2. INTENTO LOCAL: Si falla lo de arriba (porque estás en tu PC)
            # Buscamos el archivo físico serviceAccountKey.json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            key_path = os.path.join(current_dir, "serviceAccountKey.json")
            
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                # print("Conectado vía archivo local JSON (PC)")
            else:
                st.error("❌ ERROR CRÍTICO: No se encontró la llave de Firebase.")
                st.warning("Si estás en local, asegúrate de tener 'serviceAccountKey.json'. Si estás en la nube, revisa los Secrets.")
                st.stop()

    return firestore.client()

db = get_db()