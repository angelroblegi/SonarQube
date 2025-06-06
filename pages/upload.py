import streamlit as st
import os
from datetime import datetime

UPLOAD_DIR = "uploads"

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

st.title("📤 Subir nuevo archivo de métricas")

uploaded_file = st.file_uploader("Selecciona archivo Excel de métricas", type=["xlsx"])

if uploaded_file is not None:
    # Aquí puedes pedir al usuario que seleccione el mes (opcional), si no se usa el mes actual
    fecha_str = st.text_input("Ingresa el mes del archivo (formato YYYY-MM)", datetime.now().strftime("%Y-%m"))

    if fecha_str:
        try:
            # Validar formato
            fecha = datetime.strptime(fecha_str, "%Y-%m")
            nombre_archivo = f"metricas_{fecha_str}.xlsx"

            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)

            archivo_path = os.path.join(UPLOAD_DIR, nombre_archivo)

            with open(archivo_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.success(f"Archivo guardado correctamente como {nombre_archivo}")

        except ValueError:
            st.error("Formato de fecha inválido. Usa YYYY-MM, por ejemplo: 2025-05")
