import io
import os

import pandas as pd
import streamlit as st

ARCHIVO_QG_CANDIDATOS = [
    "data/sonar_metricas_qg 2.xlsx",
    "data/sonar_metricas_qg_2.xlsx",
]


if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("No tienes permiso para ver esta pagina. Inicia sesion como admin.")
    st.stop()


@st.cache_data
def resolver_archivo_qg():
    for ruta in ARCHIVO_QG_CANDIDATOS:
        if os.path.exists(ruta):
            return ruta
    return None


@st.cache_data
def cargar_asignacion_qg(ruta_archivo):
    df = pd.read_excel(ruta_archivo)
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data
def convertir_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


st.title("Asignacion de Quality Gates")
st.caption("Vista administrativa del archivo de asignacion de Quality Gates")

ruta_qg = resolver_archivo_qg()
if ruta_qg is None:
    st.error("No se encontro el archivo de asignacion en data.")
    st.info("Se esperaba uno de estos archivos: sonar_metricas_qg 2.xlsx o sonar_metricas_qg_2.xlsx")
    st.stop()

st.success(f"Archivo cargado: {os.path.basename(ruta_qg)}")

df_qg = cargar_asignacion_qg(ruta_qg)

if df_qg.empty:
    st.warning("El archivo existe, pero no contiene filas.")
    st.stop()

st.write(f"Registros: {len(df_qg)} | Columnas: {len(df_qg.columns)}")

busqueda = st.text_input("Buscar en tabla", placeholder="Escribe texto para filtrar...").strip()

if busqueda:
    mascara = df_qg.astype(str).apply(
        lambda fila: fila.str.contains(busqueda, case=False, na=False).any(),
        axis=1,
    )
    df_mostrado = df_qg[mascara].copy()
else:
    df_mostrado = df_qg.copy()

st.dataframe(df_mostrado, use_container_width=True, height=620)

excel_bytes = convertir_excel(df_mostrado)
st.download_button(
    "Descargar vista filtrada (Excel)",
    data=excel_bytes,
    file_name="asignacion_quality_gates_filtrada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
