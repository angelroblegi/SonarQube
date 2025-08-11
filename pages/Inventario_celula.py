import streamlit as st
import pandas as pd
import os


if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

# ---------- Página principal ----------
st.title("🔎 Encuentra la asignacion de un proyecto con su celula")

@st.cache_data
def cargar_datos():
    archivo_path = os.path.join("data", "Proyectos_filtrados.xlsx")
    return pd.read_excel(archivo_path)

df = cargar_datos()

busqueda = st.text_input("Escribe parte del nombre del proyecto:")

if busqueda:
    opciones = df[df['NombreProyecto'].str.contains(busqueda, case=False, na=False)]['NombreProyecto'].tolist()

    if opciones:
        seleccion = st.selectbox("Sugerencias encontradas:", opciones)
        if seleccion:
            resultado = df[df["NombreProyecto"] == seleccion].iloc[0]
            st.markdown(f"### Resultado")
            st.write(f"📌 **Proyecto:** {seleccion}")
            st.write(f"👥 **Célula:** {resultado['Celula']}")
            # Mostrar Pipeline si existe en el archivo
            if 'Pipeline' in df.columns:
                valor_pipeline = resultado['Pipeline'] if 'Pipeline' in resultado else None
                if pd.notna(valor_pipeline):
                    st.write(f"🚀 **Pipeline:** {valor_pipeline}")
                else:
                    st.write("🚀 **Pipeline:** Sin dato")
    else:
        st.warning("No se encontraron proyectos.")
else:
    st.info("Comienza a escribir para obtener sugerencias.")
