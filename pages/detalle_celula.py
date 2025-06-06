import streamlit as st
import pandas as pd
import os
import plotly.express as px
import glob
from datetime import datetime

# Verificar que el usuario esté logueado
if "rol" not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión para continuar.")
    st.stop()

# Verificar que el usuario tenga un rol permitido
if st.session_state["rol"] not in ["admin", "usuario"]:
    st.error("🚫 No tienes permiso para ver esta página.")
    st.stop()

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"
ARCHIVO_PARAMETROS = "data/parametros_metricas.csv"
UPLOAD_DIR = "uploads"

def obtener_ultimo_archivo():
    archivos = glob.glob(os.path.join(UPLOAD_DIR, "metricas_*.xlsx"))
    if not archivos:
        return None
    archivos_ordenados = sorted(
        archivos,
        key=lambda x: datetime.strptime(os.path.basename(x).split("_")[1].replace(".xlsx", ""), "%Y-%m"),
        reverse=True
    )
    return archivos_ordenados[0]

@st.cache_data
def cargar_datos(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    df['coverage'] = pd.to_numeric(df['coverage'], errors='coerce').fillna(0)
    bug_cols = ['bugs', 'bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor', 'bugs_info']
    for col in bug_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

def cargar_todos_los_datos():
    archivos = glob.glob(os.path.join(UPLOAD_DIR, "metricas_*.xlsx"))
    dfs = []
    for archivo in archivos:
        df_temp = cargar_datos(archivo)
        mes = os.path.basename(archivo).split("_")[1].replace(".xlsx", "")
        df_temp['Mes'] = pd.to_datetime(mes, format="%Y-%m")
        dfs.append(df_temp)
    if dfs:
        return pd.concat(dfs)
    else:
        return pd.DataFrame()

def cargar_seleccion():
    if os.path.exists(ARCHIVO_SELECCION):
        df_sel = pd.read_csv(ARCHIVO_SELECCION)
        seleccion = {}
        for celula in df_sel['Celula'].unique():
            seleccion[celula] = df_sel[df_sel['Celula'] == celula]['NombreProyecto'].tolist()
        return seleccion
    else:
        return {}

def cargar_parametros():
    if os.path.exists(ARCHIVO_PARAMETROS):
        df_param = pd.read_csv(ARCHIVO_PARAMETROS)
        if not df_param.empty:
            fila = df_param.iloc[0]
            return {
                "security_rating": fila.get("security_rating", "A,B,C,D,E"),
                "reliability_rating": fila.get("reliability_rating", "A,B,C,D,E"),
                "sqale_rating": fila.get("sqale_rating", "A,B,C,D,E"),
                "coverage_min": float(fila.get("coverage_min", 0))
            }
    return {
        "security_rating": "A,B,C,D,E",
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E",
        "coverage_min": 0
    }

# Obtener el último archivo de métricas
ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

df_ultimo = cargar_datos(ultimo_archivo)
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()

st.title("🔎 Detalle de Métricas por Célula")

# Selección de célula
celulas = df_ultimo['Celula'].unique()
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas)

# Filtrar proyectos seleccionados para la célula
proyectos_filtrados = seleccion_proyectos.get(celula_seleccionada, [])
if not proyectos_filtrados:
    st.warning("⚠️ No hay proyectos seleccionados para esta célula. Ve a 'Seleccionar proyectos' para configurarlo.")
    st.stop()

df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_filtrados))].copy()

# Parámetros de cumplimiento
umbral_security = parametros["security_rating"].split(",") if isinstance(parametros["security_rating"], str) else parametros["security_rating"]
umbral_reliability = parametros["reliability_rating"].split(",") if isinstance(parametros["reliability_rating"], str) else parametros["reliability_rating"]
umbral_sqale = parametros["sqale_rating"].split(",") if isinstance(parametros["sqale_rating"], str) else parametros["sqale_rating"]
coverage_min = parametros["coverage_min"]

df_celula['cumple_security'] = df_celula['security_rating'].isin(umbral_security)
df_celula['cumple_reliability'] = df_celula['reliability_rating'].isin(umbral_reliability)
df_celula['cumple_maintainability'] = df_celula['sqale_rating'].isin(umbral_sqale)
df_celula['cumple_coverage'] = df_celula['coverage'] >= coverage_min

# Nombre amigable para las métricas
nombre_metricas_amigables = {
    'security_rating': 'Security',
    'reliability_rating': 'Reliability',
    'sqale_rating': 'Maintainability',
    'coverage': 'Coverage'
}

metricas_base = ['security_rating', 'reliability_rating', 'sqale_rating', 'coverage']
bug_cols = ['bugs', 'bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor', 'bugs_info']

# Seleccionar columnas para mostrar
columnas_mostrar = ['NombreProyecto'] + metricas_base + [col for col in bug_cols if col in df_celula.columns]
df_mostrar = df_celula[columnas_mostrar].rename(columns=nombre_metricas_amigables)

# Fila de resumen
fila_resumen = {
    'NombreProyecto': 'Cumplimiento (%)',
    'Security': f"{df_celula['cumple_security'].mean() * 100:.1f}%",
    'Reliability': f"{df_celula['cumple_reliability'].mean() * 100:.1f}%",
    'Maintainability': f"{df_celula['cumple_maintainability'].mean() * 100:.1f}%",
    'Coverage': f"{df_celula['cumple_coverage'].mean() * 100:.1f}%"
}

for col in bug_cols:
    if col in df_mostrar.columns:
        fila_resumen[col] = ""

df_mostrar_final = pd.concat([df_mostrar, pd.DataFrame([fila_resumen])], ignore_index=True)

# Formatear la cobertura como porcentaje
def formatear_coverage(x):
    try:
        val = float(x)
        return f"{val:.1f}%"
    except:
        return str(x)

df_mostrar_final.loc[df_mostrar_final['NombreProyecto'] != 'Cumplimiento (%)', 'Coverage'] = df_mostrar_final.loc[df_mostrar_final['NombreProyecto'] != 'Cumplimiento (%)', 'Coverage'].apply(formatear_coverage)

# Resaltar la fila de resumen
def resaltar_resumen(row):
    if row['NombreProyecto'] == 'Cumplimiento (%)':
        return ['background-color: #f0f0f0; font-weight: bold'] * len(row)
    return [''] * len(row)

df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)

# Mostrar la tabla de métricas
st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Resumen de bugs
resumen_bugs = df_celula[bug_cols].sum().astype(int).to_frame().T
nuevo_nombre_cols_bugs = {
    'bugs': 'Total Bugs',
    'bugs_blocker': 'Blocker',
    'bugs_critical': 'Critical',
    'bugs_major': 'Major',
    'bugs_minor': 'Minor',
    'bugs_info': 'Info'
}
resumen_bugs.rename(columns=nuevo_nombre_cols_bugs, inplace=True)

st.subheader("📊 Resumen total de bugs en la célula")
st.dataframe(resumen_bugs, hide_index=True)

# Gráfico de bugs
fig = px.bar(
    resumen_bugs.melt(var_name='Tipo de Bug', value_name='Cantidad'),
    x='Tipo de Bug',
    y='Cantidad',
    title=f"Cantidad total de bugs por tipo en {celula_seleccionada}"
)
st.plotly_chart(fig, use_container_width=True)

# Tendencia de cumplimiento
st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

if not df_historico.empty and 'Mes' in df_historico.columns:
    df_historico_filtrado = df_historico[
        (df_historico['Celula'] == celula_seleccionada) & 
        (df_historico['NombreProyecto'].isin(proyectos_filtrados))
    ].copy()

    df_historico_filtrado['cumple_security'] = df_historico_filtrado['security_rating'].isin(umbral_security)
    df_historico_filtrado['cumple_reliability'] = df_historico_filtrado['reliability_rating'].isin(umbral_reliability)
    df_historico_filtrado['cumple_maintainability'] = df_historico_filtrado['sqale_rating'].isin(umbral_sqale)
    df_historico_filtrado['cumple_coverage'] = df_historico_filtrado['coverage'] >= coverage_min

    metricas_cumplimiento = ['cumple_security', 'cumple_reliability', 'cumple_maintainability', 'cumple_coverage']

    for metrica in metricas_cumplimiento:
        st.subheader(metrica.replace('cumple_', '').capitalize())

        tendencia = df_historico_filtrado.groupby(['Mes'])[metrica].mean().reset_index()
        tendencia[metrica] = tendencia[metrica] * 100

        fig = px.line(
            tendencia,
            x='Mes',
            y=metrica,
            markers=True,
            title=f"Tendencia de cumplimiento en {metrica.replace('cumple_', '')}"
        )
        st.plotly_chart(fig, use_container_width=True)
