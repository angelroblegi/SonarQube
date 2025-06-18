import streamlit as st
import pandas as pd
import io
import os
import glob
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide", page_title="Dashboard SonarQube")

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.error("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
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
    numeric_cols = [
        'coverage', 'duplicated_lines_density',
        'bugs', 'bugs_blocker', 'bugs_critical',
        'bugs_major', 'bugs_minor', 'bugs_info'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'Mes' in df.columns:
        df['Mes'] = pd.to_datetime(df['Mes'], format="%Y-%m", errors='coerce')
    else:
        try:
            fecha_str = os.path.basename(path).split("_")[1].replace(".xlsx", "")
            df['Mes'] = pd.to_datetime(fecha_str, format="%Y-%m")
        except:
            df['Mes'] = pd.NaT
    return df

def cargar_seleccion():
    if os.path.exists(ARCHIVO_SELECCION):
        df_sel = pd.read_csv(ARCHIVO_SELECCION)
        seleccion = {}
        for celula in df_sel['Celula'].unique():
            seleccion[celula] = df_sel.loc[df_sel['Celula'] == celula, 'NombreProyecto'].tolist()
        return seleccion
    return None

def cargar_parametros():
    if os.path.exists(ARCHIVO_PARAMETROS):
        df_param = pd.read_csv(ARCHIVO_PARAMETROS)
        if not df_param.empty:
            fila = df_param.iloc[0]
            return {
                "security_rating": fila.get("security_rating", "A,B,C,D,E"),
                "reliability_rating": fila.get("reliability_rating", "A,B,C,D,E"),
                "sqale_rating": fila.get("sqale_rating", "A,B,C,D,E"),
                "coverage_min": float(fila.get("coverage_min", 0)),
                "duplications_max": float(fila.get("duplications_max", 10))
            }
    return {"security_rating": "A,B,C,D,E", "reliability_rating": "A,B,C,D,E",
            "sqale_rating": "A,B,C,D,E", "coverage_min": 0, "duplications_max": 10}

def guardar_parametros(parametros):
    df = pd.DataFrame([parametros])
    df.to_csv(ARCHIVO_PARAMETROS, index=False)

@st.cache_data
def convertir_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

proyectos_seleccionados = cargar_seleccion()
parametros = cargar_parametros()

if proyectos_seleccionados is None or all(len(v) == 0 for v in proyectos_seleccionados.values()):
    st.warning("⚠️ No hay selección de proyectos guardada. Ve a la página 'Seleccionar proyectos' para elegir.")
    st.stop()

st.session_state["proyectos_seleccionados"] = proyectos_seleccionados

ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

archivos_todos = glob.glob(os.path.join(UPLOAD_DIR, "metricas_*.xlsx"))
meses_disponibles = sorted([
    os.path.basename(f).split("_")[1].replace(".xlsx", "")
    for f in archivos_todos
    if os.path.basename(f).startswith("metricas_")
], reverse=True)

mes_seleccionado = st.selectbox("📅 Selecciona el mes", meses_disponibles)
archivo_mes_seleccionado = os.path.join(UPLOAD_DIR, f"metricas_{mes_seleccionado}.xlsx")

st.title("📊 Dashboard de Métricas SonarQube por Célula")
st.markdown(f"**📁 Archivo cargado:** `{os.path.basename(archivo_mes_seleccionado)}`")

df = cargar_datos(archivo_mes_seleccionado)

# Panel de parámetros
with st.expander("⚙️ Parámetros de calidad"):
    letras = ['A', 'B', 'C', 'D', 'E']
    col1, col2, col3 = st.columns(3)
    umbral_security = col1.multiselect("🔐 Security Rating", letras, default=parametros["security_rating"].split(","))
    umbral_reliability = col2.multiselect("🛡️ Reliability Rating", letras, default=parametros["reliability_rating"].split(","))
    umbral_sqale = col3.multiselect("🧹 Maintainability Rating", letras, default=parametros["sqale_rating"].split(","))

    col4, col5 = st.columns(2)
    coverage_min = col4.slider("🧪 Cobertura mínima (%)", 0, 100, int(parametros["coverage_min"]))
    duplications_max = col5.slider("🌀 Complejidad máxima (%)", 0, 100, int(parametros["duplications_max"]))

    if st.button("💾 Guardar parámetros"):
        nuevos_parametros = {
            "security_rating": ",".join(umbral_security),
            "reliability_rating": ",".join(umbral_reliability),
            "sqale_rating": ",".join(umbral_sqale),
            "coverage_min": coverage_min,
            "duplications_max": duplications_max
        }
        guardar_parametros(nuevos_parametros)
        st.success("✅ Parámetros guardados correctamente.")

# Filtrado de datos
dfs_filtrados = []
for celula, proyectos in proyectos_seleccionados.items():
    if proyectos:
        df_filtrado = df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos))]
        dfs_filtrados.append(df_filtrado)

if not dfs_filtrados:
    st.warning("⚠️ No hay datos después del filtro.")
    st.stop()

df_filtrado_final = pd.concat(dfs_filtrados)

proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

df_filtrado_final['cumple_security'] = df_filtrado_final['security_rating'].isin(umbral_security)
df_filtrado_final['cumple_reliability'] = df_filtrado_final['reliability_rating'].isin(umbral_reliability)
df_filtrado_final['cumple_maintainability'] = df_filtrado_final['sqale_rating'].isin(umbral_sqale)
df_filtrado_final['cumple_duplications'] = df_filtrado_final['duplicated_lines_density'] <= duplications_max

df_coverage = df_filtrado_final[~df_filtrado_final['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()
df_coverage['cumple_coverage'] = df_coverage['coverage'] >= coverage_min

agrupado_otros = df_filtrado_final.groupby('Celula').agg({
    'cumple_security': 'mean',
    'cumple_reliability': 'mean',
    'cumple_maintainability': 'mean',
    'cumple_duplications': 'mean',
    'bugs': 'sum',
    'bugs_blocker': 'sum',
    'bugs_critical': 'sum',
    'bugs_major': 'sum',
    'bugs_minor': 'sum'
})

agrupado_coverage = df_coverage.groupby('Celula').agg({'cumple_coverage': 'mean'})

agrupado = agrupado_otros.join(agrupado_coverage)
agrupado[['cumple_security', 'cumple_reliability', 'cumple_maintainability',
          'cumple_coverage', 'cumple_duplications']] *= 100
agrupado = agrupado.round(1).reset_index()

agrupado.columns = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Complejidad', 'Bugs', 'Blocker',
    'Critical', 'Major', 'Minor', 'Cobertura de pruebas unitarias'
]

cols_reordenadas = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Cobertura de pruebas unitarias', 'Complejidad',
    'Bugs', 'Blocker', 'Critical', 'Major', 'Minor'
]
agrupado = agrupado[cols_reordenadas]

st.subheader("📋 Tabla de Cumplimiento por Célula")
st.dataframe(
    agrupado.style.background_gradient(
        cmap="BuGn",
        subset=['Seguridad', 'Confiabilidad', 'Mantenibilidad',
                'Cobertura de pruebas unitarias', 'Complejidad'],
        vmin=0, vmax=100
    ).format({
        'Seguridad': "{:.1f}%", 'Confiabilidad': "{:.1f}%", 'Mantenibilidad': "{:.1f}%",
        'Cobertura de pruebas unitarias': "{:.1f}%", 'Complejidad': "{:.1f}%",
        'Bugs': "{:.0f}", 'Blocker': "{:.0f}", 'Critical': "{:.0f}", 'Major': "{:.0f}", 'Minor': "{:.0f}"
    }),
    use_container_width=True
)

st.markdown("### 📥 Descargar Excel")
st.download_button(
    label="⬇️ Descargar Reporte",
    data=convertir_excel(agrupado),
    file_name=f"cumplimiento_celulas_{mes_seleccionado}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.subheader("📊 Gráfico de Cumplimiento por Célula")
fig_cumplimiento = px.bar(
    agrupado.melt(id_vars='Célula', value_vars=[
        'Seguridad', 'Confiabilidad', 'Mantenibilidad',
        'Cobertura de pruebas unitarias', 'Complejidad'
    ], var_name='Métrica', value_name='Porcentaje'),
    x='Célula', y='Porcentaje', color='Métrica',
    barmode='group', title='Cumplimiento por Métrica y Célula'
)
st.plotly_chart(fig_cumplimiento, use_container_width=True)

st.subheader("🐞 Distribución de Bugs")
fig_bugs = px.bar(
    agrupado.melt(id_vars='Célula', value_vars=[
        'Bugs', 'Blocker', 'Critical', 'Major', 'Minor'
    ], var_name='Tipo de Bug', value_name='Cantidad'),
    x='Célula', y='Cantidad', color='Tipo de Bug',
    barmode='group', title='Bugs por Célula'
)
st.plotly_chart(fig_bugs, use_container_width=True)

# 🔁 Tendencia mensual
st.markdown("---")
st.header("📈 Tendencia de Cumplimiento por Célula y Métrica")

lista_df = [cargar_datos(a) for a in archivos_todos]
df_todos = pd.concat(lista_df, ignore_index=True) if lista_df else pd.DataFrame()

if 'Mes' in df_todos.columns:
    df_todos['Mes'] = pd.to_datetime(df_todos['Mes'])
    df_todos = df_todos[df_todos['NombreProyecto'].isin(
        sum(proyectos_seleccionados.values(), [])
    )]

    df_todos['cumple_security'] = df_todos['security_rating'].isin(umbral_security)
    df_todos['cumple_reliability'] = df_todos['reliability_rating'].isin(umbral_reliability)
    df_todos['cumple_maintainability'] = df_todos['sqale_rating'].isin(umbral_sqale)
    df_todos['cumple_duplications'] = df_todos['duplicated_lines_density'] <= duplications_max

    df_todos_coverage = df_todos[~df_todos['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()
    df_todos_coverage['cumple_coverage'] = df_todos_coverage['coverage'] >= coverage_min

    tendencias = [
        ("Seguridad", 'cumple_security', df_todos),
        ("Confiabilidad", 'cumple_reliability', df_todos),
        ("Mantenibilidad", 'cumple_maintainability', df_todos),
        ("Cobertura", 'cumple_coverage', df_todos_coverage),
        ("Complejidad", 'cumple_duplications', df_todos)
    ]

    for nombre, columna, df_tendencia in tendencias:
        df_trend = df_tendencia.groupby(['Mes', 'Celula'])[columna].mean().reset_index()
        df_trend[nombre] = df_trend[columna] * 100

        fig_trend = px.line(
            df_trend,
            x='Mes',
            y=nombre,
            color='Celula',
            markers=True,
            title=f"Tendencia mensual de {nombre}"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("⚠️ No se encontró columna 'Mes' para mostrar tendencia.")
