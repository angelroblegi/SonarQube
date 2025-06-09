import streamlit as st
import pandas as pd
import io
import os
import glob
import plotly.express as px
from datetime import datetime

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
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
        key=lambda x: datetime.strptime(os.path.basename(x).split("_")[1].replace(".xlsx",""), "%Y-%m"),
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
            fecha_str = os.path.basename(path).split("_")[1].replace(".xlsx","")
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
    else:
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
meses_disponibles = []
for archivo in archivos_todos:
    try:
        mes_str = os.path.basename(archivo).split("_")[1].replace(".xlsx","")
        meses_disponibles.append(mes_str)
    except:
        continue
meses_disponibles = sorted(meses_disponibles, reverse=True)

mes_seleccionado = st.selectbox("Selecciona el mes", meses_disponibles, index=0)
archivo_mes_seleccionado = os.path.join(UPLOAD_DIR, f"metricas_{mes_seleccionado}.xlsx")

st.title("📈 Dashboard de Métricas SonarQube por Célula")
st.markdown(f"**Archivo cargado:** {os.path.basename(archivo_mes_seleccionado)}")

df = cargar_datos(archivo_mes_seleccionado)

letras = ['A', 'B', 'C', 'D', 'E']
umbral_security = st.multiselect("Security Rating", letras, default=parametros["security_rating"].split(","))
umbral_reliability = st.multiselect("Reliability Rating", letras, default=parametros["reliability_rating"].split(","))
umbral_sqale = st.multiselect("Maintainability Rating", letras, default=parametros["sqale_rating"].split(","))

coverage_min = st.slider("Coverage mínimo (%)", 0, 100, int(parametros["coverage_min"]))
duplications_max = st.slider("Duplications máximo (%)", 0, 100, int(parametros.get("duplications_max", 10)))

if st.button("💾 Guardar parámetros"):
    nuevos_parametros = {
        "security_rating": ",".join(umbral_security),
        "reliability_rating": ",".join(umbral_reliability),
        "sqale_rating": ",".join(umbral_sqale),
        "coverage_min": coverage_min,
        "duplications_max": duplications_max
    }
    guardar_parametros(nuevos_parametros)
    st.success("✅ Parámetros guardados correctamente. Recarga la página Detalle Célula para ver reflejados los cambios.")

dfs_filtrados = []
for celula, proyectos in proyectos_seleccionados.items():
    if proyectos:
        df_filtrado = df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos))]
        dfs_filtrados.append(df_filtrado)

if not dfs_filtrados:
    st.warning("⚠️ No hay datos después de aplicar el filtro.")
    st.stop()

df_filtrado_final = pd.concat(dfs_filtrados)

df_filtrado_final['cumple_security'] = df_filtrado_final['security_rating'].isin(umbral_security)
df_filtrado_final['cumple_reliability'] = df_filtrado_final['reliability_rating'].isin(umbral_reliability)
df_filtrado_final['cumple_maintainability'] = df_filtrado_final['sqale_rating'].isin(umbral_sqale)
df_filtrado_final['cumple_coverage'] = df_filtrado_final['coverage'] >= coverage_min
df_filtrado_final['cumple_duplications'] = df_filtrado_final['duplicated_lines_density'] <= duplications_max

agrupado = df_filtrado_final.groupby('Celula').agg({
    'cumple_security': 'mean',
    'cumple_reliability': 'mean',
    'cumple_maintainability': 'mean',
    'cumple_coverage': 'mean',
    'cumple_duplications': 'mean',
    'bugs': 'sum',
    'bugs_blocker': 'sum',
    'bugs_critical': 'sum',
    'bugs_major': 'sum',
    'bugs_minor': 'sum',
    'bugs_info': 'sum'
})

agrupado[['cumple_security', 'cumple_reliability', 'cumple_maintainability', 'cumple_coverage', 'cumple_duplications']] *= 100
agrupado = agrupado.round(1).reset_index()

agrupado.columns = [
    'Célula', '% Security', '% Reliability', '% Maintainability',
    '% Coverage', '% Duplication', 'Bugs', 'Blocker',
    'Critical', 'Major', 'Minor', 'Info'
]

st.subheader("📊 Cumplimiento por célula")
st.dataframe(
    agrupado.style
        .format({
            '% Security': "{:.1f}%",
            '% Reliability': "{:.1f}%",
            '% Maintainability': "{:.1f}%",
            '% Coverage': "{:.1f}%",
            '% Duplication': "{:.1f}%",
            'Bugs': "{:.0f}",
            'Blocker': "{:.0f}",
            'Critical': "{:.0f}",
            'Major': "{:.0f}",
            'Minor': "{:.0f}",
            'Info': "{:.0f}",
        })
        .background_gradient(cmap="Greens", subset=['% Security', '% Reliability', '% Maintainability', '% Coverage', '% Duplication']),
    use_container_width=True
)

st.markdown("### 📥 Descargar reporte en Excel")
excel_data = convertir_excel(agrupado)
st.download_button(
    label="📊 Descargar Excel",
    data=excel_data,
    file_name=f"cumplimiento_celulas_{mes_seleccionado}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Gráfico solo para métricas de cumplimiento
metricas_cumplimiento = agrupado[['Célula', '% Security', '% Reliability', '% Maintainability', '% Coverage', '% Duplication']]
fig_cumplimiento = px.bar(
    metricas_cumplimiento.melt(id_vars='Célula', var_name='Métrica', value_name='Porcentaje'),
    x='Célula',
    y='Porcentaje',
    color='Métrica',
    barmode='group',
    title='Cumplimiento por Célula'
)
st.plotly_chart(fig_cumplimiento, use_container_width=True)

# Gráfico separado para Bugs
st.subheader("🐞 Distribución de Bugs por Célula")
bugs_cols = ['Célula', 'Bugs', 'Blocker', 'Critical', 'Major', 'Minor', 'Info']
fig_bugs = px.bar(
    agrupado[bugs_cols].melt(id_vars='Célula', var_name='Tipo de Bug', value_name='Cantidad'),
    x='Célula',
    y='Cantidad',
    color='Tipo de Bug',
    barmode='group',
    title='Cantidad de Bugs por Célula'
)
st.plotly_chart(fig_bugs, use_container_width=True)

# Tendencia mensual
st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

lista_df = [cargar_datos(a) for a in archivos_todos]
df_todos = pd.concat(lista_df, ignore_index=True) if lista_df else pd.DataFrame()

if 'Mes' in df_todos.columns:
    mes_sel_dt = datetime.strptime(mes_seleccionado, "%Y-%m")
    for metr in ['cumple_security', 'cumple_reliability', 'cumple_maintainability', 'cumple_coverage']:
        df_todos[metr] = df_todos.apply(
            lambda x: x['security_rating'] in umbral_security if metr == 'cumple_security' else
                      (x['reliability_rating'] in umbral_reliability if metr == 'cumple_reliability' else
                       (x['sqale_rating'] in umbral_sqale if metr == 'cumple_maintainability' else
                        x['coverage'] >= coverage_min)),
            axis=1
        )
    df_todos['cumple_duplications'] = df_todos['duplicated_lines_density'] <= duplications_max

    df_todos['Mes'] = pd.to_datetime(df_todos['Mes'])
    df_todos_filtrado = df_todos[df_todos['Mes'] <= mes_sel_dt]

    for metrica in ['cumple_security', 'cumple_reliability', 'cumple_maintainability', 'cumple_coverage', 'cumple_duplications']:
        st.subheader(metrica.replace('cumple_', '').capitalize())
        tendencia = df_todos_filtrado.groupby(['Celula', 'Mes'])[metrica].mean().reset_index()
        tendencia[metrica] *= 100
        fig = px.line(
            tendencia,
            x='Mes',
            y=metrica,
            color='Celula',
            markers=True,
            title=f"Tendencia mensual de {metrica.replace('cumple_', '').capitalize()} (%)"
        )
        fig.update_layout(yaxis_title="Porcentaje (%)", xaxis_title="Mes", height=400)
        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("ℹ️ No se pudo identificar la columna 'Mes' para mostrar la tendencia.")
