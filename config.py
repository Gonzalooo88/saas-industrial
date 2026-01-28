import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import json

# Función para obtener la base de datos de forma segura
def get_db():
    # CASO 1: Estamos en Streamlit Cloud (Producción)
    if "firebase" in st.secrets:
        # Convertimos la configuración de secretos a un diccionario de Python
        key_dict = json.loads(st.secrets["firebase"]["text_key"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        db = firestore.Client(credentials=creds, project=creds.project_id)
        return db

    # CASO 2: Estamos en Local (Tu PC)
    else:
        try:
            # Asegúrate que el nombre de tu archivo JSON sea correcto aquí
            creds = service_account.Credentials.from_service_account_file("serviceAccountKey.json")
            db = firestore.Client(credentials=creds)
            return db
        except Exception as e:
            st.error(f"Error cargando credenciales locales: {e}")
            return None

# Instancia global de la base de datos
db = get_db()