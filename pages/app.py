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
duplications_max = st.slider("Complejidad (%)", 0, 100, int(parametros.get("duplications_max", 10)))

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

# Proyectos a excluir solo en coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

# Calcular métricas de cumplimiento para todas las filas (normal para todo excepto coverage)
df_filtrado_final['cumple_security'] = df_filtrado_final['security_rating'].isin(umbral_security)
df_filtrado_final['cumple_reliability'] = df_filtrado_final['reliability_rating'].isin(umbral_reliability)
df_filtrado_final['cumple_maintainability'] = df_filtrado_final['sqale_rating'].isin(umbral_sqale)
df_filtrado_final['cumple_duplications'] = df_filtrado_final['duplicated_lines_density'] <= duplications_max

# Coverage: calcular solo para filas que NO estén en los proyectos excluidos
df_coverage = df_filtrado_final[~df_filtrado_final['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()
df_coverage['cumple_coverage'] = df_coverage['coverage'] >= coverage_min

# Ahora agrupamos

# Para métricas que sí incluyen todos los proyectos
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

# Para coverage excluyendo los proyectos indicados
agrupado_coverage = df_coverage.groupby('Celula').agg({
    'cumple_coverage': 'mean'
})

# Combinar resultados
agrupado = agrupado_otros.join(agrupado_coverage)

# Multiplicar por 100 y redondear
agrupado[['cumple_security', 'cumple_reliability', 'cumple_maintainability', 'cumple_coverage', 'cumple_duplications']] *= 100
agrupado = agrupado.round(1).reset_index()

agrupado.columns = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Complejidad', 'Bugs', 'Blocker',
    'Critical', 'Major', 'Minor', 'Cobertura de pruebas unitarias'
]

# Reordenar columnas para que "Cobertura de pruebas unitarias" esté en el lugar correcto
cols_reordenadas = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Cobertura de pruebas unitarias', 'Complejidad',
    'Bugs', 'Blocker', 'Critical', 'Major', 'Minor'
]
agrupado = agrupado[cols_reordenadas]

st.subheader("📊 Cumplimiento por célula")
st.dataframe(
    agrupado.style
        .background_gradient(
            cmap="Greens",
            subset=[
                'Seguridad', 'Confiabilidad',
                'Mantenibilidad', 'Cobertura de pruebas unitarias', 'Complejidad'
            ],
            vmin=0,
            vmax=100
        )
        .format({
            'Seguridad': "{:.1f}%",
            'Confiabilidad': "{:.1f}%",
            'Mantenibilidad': "{:.1f}%",
            'Cobertura de pruebas unitarias': "{:.1f}%",
            'Complejidad': "{:.1f}%",
            'Bugs': "{:.0f}",
            'Blocker': "{:.0f}",
            'Critical': "{:.0f}",
            'Major': "{:.0f}",
            'Minor': "{:.0f}"
        }),
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
metricas_cumplimiento = agrupado[['Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad', 'Cobertura de pruebas unitarias', 'Complejidad']]

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
bugs_cols = ['Célula', 'Bugs', 'Blocker', 'Critical', 'Major', 'Minor']  # sin 'Info'

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

    # **Aquí también excluyo esos proyectos de coverage para la tendencia**
    df_todos_coverage = df_todos[~df_todos['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()

    df_todos['Mes'] = pd.to_datetime(df_todos['Mes'])
    df_todos_filtrado = df_todos[df_todos['Mes'] <= mes_sel_dt]
    df_todos_coverage_filtrado = df_todos_coverage[df_todos_coverage['Mes'] <= mes_sel_dt]

    tendencias = [
        ("Seguridad", 'cumple_security', df_todos_filtrado),
        ("Mantenibilidad", 'cumple_maintainability', df_todos_filtrado),
        ("Cobertura", 'cumple_coverage', df_todos_coverage_filtrado),
    ]

    fig_tendencias = px.line(title="Tendencias de Cumplimiento por Célula y Métrica")
    for nombre, columna, df_tend in tendencias:
        trend = df_tend.groupby(['Mes', 'Celula'])[columna].mean().reset_index()
        trend[nombre] = trend[columna] * 100
        fig_tendencias.add_scatter(x=trend['Mes'], y=trend[nombre], mode='lines+markers', name=nombre)
    st.plotly_chart(fig_tendencias, use_container_width=True)

else:
    st.warning("⚠️ No se encontró columna 'Mes' para mostrar tendencia.")

