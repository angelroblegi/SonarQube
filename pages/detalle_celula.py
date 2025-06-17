import streamlit as st
import pandas as pd
import os
import plotly.express as px
import glob
from datetime import datetime

if "rol" not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión para continuar.")
    st.stop()

if st.session_state["rol"] not in ["admin", "usuario"]:
    st.error("🚫 No tienes permiso para ver esta página.")
    st.stop()

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"
ARCHIVO_PARAMETROS = "data/parametros_metricas.csv"
UPLOAD_DIR = "uploads"

def obtener_ultimo_archivo():
    archivos = glob.glob(os.path.join(UPLOAD_DIR, "metricas_*.xlsx"))
    if not archivos:import streamlit as st
import pandas as pd
import os
import plotly.express as px
import glob
from datetime import datetime

if "rol" not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión para continuar.")
    st.stop()

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

    if 'duplicated_lines_density' in df.columns:
        df['complexity'] = pd.to_numeric(df['duplicated_lines_density'], errors='coerce').fillna(0)
    else:
        df['complexity'] = pd.to_numeric(df['complexity'], errors='coerce').fillna(0)

    bug_cols = ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
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
    return pd.concat(dfs) if dfs else pd.DataFrame()

def cargar_seleccion():
    if os.path.exists(ARCHIVO_SELECCION):
        df_sel = pd.read_csv(ARCHIVO_SELECCION)
        seleccion = {}
        for celula in df_sel['Celula'].unique():
            seleccion[celula] = df_sel[df_sel['Celula'] == celula]['NombreProyecto'].tolist()
        return seleccion
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
                "coverage_min": float(fila.get("coverage_min", 0)),
                "duplications_max": float(fila.get("duplications_max", 10))
            }
    return {
        "security_rating": "A,B,C,D,E",
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E",
        "coverage_min": 0,
        "duplications_max": 10
    }

ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

df_ultimo = cargar_datos(ultimo_archivo)
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()

st.title("🔎 Detalle de Métricas por Célula")

celulas = df_ultimo['Celula'].unique()
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas)

proyectos_filtrados = seleccion_proyectos.get(celula_seleccionada, [])
if not proyectos_filtrados:
    st.warning("⚠️ No hay proyectos seleccionados para esta célula. Ve a 'Seleccionar proyectos' para configurarlo.")
    st.stop()

df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_filtrados))].copy()

umbral_security = parametros["security_rating"].split(",")
umbral_reliability = parametros["reliability_rating"].split(",")
umbral_sqale = parametros["sqale_rating"].split(",")
coverage_min = parametros["coverage_min"]
duplications_max = parametros["duplications_max"]

df_celula['cumple_security'] = df_celula['security_rating'].isin(umbral_security)
df_celula['cumple_reliability'] = df_celula['reliability_rating'].isin(umbral_reliability)
df_celula['cumple_maintainability'] = df_celula['sqale_rating'].isin(umbral_sqale)
df_celula['cumple_coverage'] = df_celula['coverage'] >= coverage_min
df_celula['cumple_duplications'] = df_celula['complexity'] <= duplications_max

# Proyectos a excluir para cálculo coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

df_celula['excluir_coverage'] = df_celula['NombreProyecto'].isin(proyectos_excluir_coverage)

df_filtrado_coverage = df_celula.loc[~df_celula['excluir_coverage']]

if not df_filtrado_coverage.empty:
    cumplimiento_coverage = (df_filtrado_coverage['cumple_coverage'].sum() / len(df_filtrado_coverage)) * 100
else:
    cumplimiento_coverage = 0

nombre_metricas_amigables = {
    'security_rating': 'Seguridad',
    'reliability_rating': 'Confiabilidad',
    'sqale_rating': 'Mantenibilidad',
    'coverage': 'Cobertura de pruebas unitarias',
    'complexity': 'Complejidad'
}

metricas_base = ['security_rating', 'reliability_rating', 'sqale_rating', 'coverage', 'complexity']

bug_cols = ['bugs_major', 'bugs_minor', 'bugs_blocker', 'bugs_critical']
nuevo_nombre_cols_bugs_tabla = {
    'bugs_major': 'Major',
    'bugs_minor': 'Minor',
    'bugs_blocker': 'Blocker',
    'bugs_critical': 'Critical'
}

if all(col in df_celula.columns for col in bug_cols):
    df_celula['Bugs Totales'] = df_celula[bug_cols].sum(axis=1)

columnas_mostrar = ['NombreProyecto'] + metricas_base + bug_cols + ['Bugs Totales']
df_mostrar = df_celula[columnas_mostrar].rename(columns=nombre_metricas_amigables)
df_mostrar.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

# Formateo
formatear_pct = lambda x: f"{float(x):.1f}%" if pd.notna(x) else x

df_mostrar['Cobertura de pruebas unitarias'] = df_mostrar['Cobertura de pruebas unitarias'].apply(formatear_pct)
df_mostrar['Complejidad'] = df_mostrar['Complejidad'].apply(formatear_pct)

# Resumen cumplimiento con coverage ajustado
fila_resumen = {
    'NombreProyecto': 'Cumplimiento (%)',
    'Seguridad': formatear_pct(df_celula['cumple_security'].mean() * 100),
    'Confiabilidad': formatear_pct(df_celula['cumple_reliability'].mean() * 100),
    'Mantenibilidad': formatear_pct(df_celula['cumple_maintainability'].mean() * 100),
    'Cobertura de pruebas unitarias': formatear_pct(cumplimiento_coverage),
    'Complejidad': formatear_pct(df_celula['cumple_duplications'].mean() * 100)
}

for col in nuevo_nombre_cols_bugs_tabla.values():
    if col in df_mostrar.columns:
        fila_resumen[col] = ""

if 'Bugs Totales' in df_mostrar.columns:
    fila_resumen['Bugs Totales'] = df_celula['Bugs Totales'].sum()

df_mostrar_final = pd.concat([df_mostrar, pd.DataFrame([fila_resumen])], ignore_index=True)

def resaltar_resumen(row):
    return ['background-color: #f0f0f0; font-weight: bold'] * len(row) if row['NombreProyecto'] == 'Cumplimiento (%)' else [''] * len(row)

df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Resumen bugs
resumen_bugs = df_celula[bug_cols].sum().astype(int).to_frame().T
resumen_bugs.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

if 'Bugs Totales' in df_celula:
    resumen_bugs['Bugs Totales'] = df_celula['Bugs Totales'].sum()

st.subheader("📊 Resumen total de bugs en la célula")
st.dataframe(resumen_bugs, hide_index=True)

fig = px.bar(
    resumen_bugs.melt(var_name='Tipo de Bug', value_name='Cantidad'),
    x='Tipo de Bug',
    y='Cantidad',
    title=f"Cantidad total de bugs por tipo en {celula_seleccionada}"
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

if not df_historico.empty and 'Mes' in df_historico.columns:
    df_historico_filtrado = df_historico[
        (df_historico['Celula'] == celula_seleccionada) &
        (df_historico['NombreProyecto'].isin(proyectos_filtrados))
    ].copy()

    df_historico_filtrado['Mes'] = pd.to_datetime(df_historico_filtrado['Mes']).dt.to_period('M').dt.to_timestamp()

    df_historico_filtrado['cumple_security'] = df_historico_filtrado['security_rating'].isin(umbral_security)
    df_historico_filtrado['cumple_reliability'] = df_historico_filtrado['reliability_rating'].isin(umbral_reliability)
    df_historico_filtrado['cumple_maintainability'] = df_historico_filtrado['sqale_rating'].isin(umbral_sqale)
    df_historico_filtrado['cumple_coverage'] = df_historico_filtrado['coverage'] >= coverage_min
    df_historico_filtrado['cumple_duplications'] = df_historico_filtrado['complexity'] <= duplications_max

    # Excluir proyectos para coverage en tendencia histórica
    df_historico_filtrado['excluir_coverage'] = df_historico_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)

    nombres_tendencias = {
        'cumple_security': 'Seguridad',
        'cumple_reliability': 'Confiabilidad',
        'cumple_maintainability': 'Mantenibilidad',
        'cumple_coverage': 'Cobertura de pruebas unitarias',
        'cumple_duplications': 'Complejidad'
    }

    for metrica, nombre_metrica in nombres_tendencias.items():
        if metrica == 'cumple_coverage':
            df_temp = df_historico_filtrado.loc[~df_historico_filtrado['excluir_coverage']]
            tendencia = df_temp.groupby('Mes')[metrica].mean().reset_index()
        else:
            tendencia = df_historico_filtrado.groupby('Mes')[metrica].mean().reset_index()

        if metrica.startswith("cumple_"):
            tendencia[metrica] = tendencia[metrica] * 100
            y_label = f"% Cumplimiento en {nombre_metrica}"
        else:
            tendencia[metrica] = tendencia[metrica].round(1)
            y_label = f"{nombre_metrica} Promedio"

        tendencia['Mes'] = tendencia['Mes'].dt.strftime('%Y-%m')

        fig = px.line(
            tendencia,
            x='Mes',
            y=metrica,
            markers=True,
            title=f"Tendencia de {nombre_metrica}",
            labels={metrica: y_label, 'Mes': 'Mes'}
        )
        st.plotly_chart(fig, use_container_width=True)

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

    if 'duplicated_lines_density' in df.columns:
        df['complexity'] = pd.to_numeric(df['duplicated_lines_density'], errors='coerce').fillna(0)
    else:
        df['complexity'] = pd.to_numeric(df['complexity'], errors='coerce').fillna(0)

    bug_cols = ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
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
    return pd.concat(dfs) if dfs else pd.DataFrame()

def cargar_seleccion():
    if os.path.exists(ARCHIVO_SELECCION):
        df_sel = pd.read_csv(ARCHIVO_SELECCION)
        seleccion = {}
        for celula in df_sel['Celula'].unique():
            seleccion[celula] = df_sel[df_sel['Celula'] == celula]['NombreProyecto'].tolist()
        return seleccion
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
                "coverage_min": float(fila.get("coverage_min", 0)),
                "duplications_max": float(fila.get("duplications_max", 10))
            }
    return {
        "security_rating": "A,B,C,D,E",
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E",
        "coverage_min": 0,
        "duplications_max": 10
    }

ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

df_ultimo = cargar_datos(ultimo_archivo)
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()

st.title("🔎 Detalle de Métricas por Célula")

celulas = df_ultimo['Celula'].unique()
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas)

proyectos_filtrados = seleccion_proyectos.get(celula_seleccionada, [])
if not proyectos_filtrados:
    st.warning("⚠️ No hay proyectos seleccionados para esta célula. Ve a 'Seleccionar proyectos' para configurarlo.")
    st.stop()

df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_filtrados))].copy()

umbral_security = parametros["security_rating"].split(",")
umbral_reliability = parametros["reliability_rating"].split(",")
umbral_sqale = parametros["sqale_rating"].split(",")
coverage_min = parametros["coverage_min"]
duplications_max = parametros["duplications_max"]

df_celula['cumple_security'] = df_celula['security_rating'].isin(umbral_security)
df_celula['cumple_reliability'] = df_celula['reliability_rating'].isin(umbral_reliability)
df_celula['cumple_maintainability'] = df_celula['sqale_rating'].isin(umbral_sqale)
df_celula['cumple_coverage'] = df_celula['coverage'] >= coverage_min
df_celula['cumple_duplications'] = df_celula['complexity'] <= duplications_max

nombre_metricas_amigables = {
    'security_rating': 'Seguridad',
    'reliability_rating': 'Confiabilidad',
    'sqale_rating': 'Mantenibilidad',
    'coverage': 'Cobertura de pruebas unitarias',
    'complexity': 'Complejidad'
}

metricas_base = ['security_rating', 'reliability_rating', 'sqale_rating', 'coverage', 'complexity']

bug_cols = ['bugs_major', 'bugs_minor', 'bugs_blocker', 'bugs_critical']
nuevo_nombre_cols_bugs_tabla = {
    'bugs_major': 'Major',
    'bugs_minor': 'Minor',
    'bugs_blocker': 'Blocker',
    'bugs_critical': 'Critical'
}

if all(col in df_celula.columns for col in bug_cols):
    df_celula['Bugs Totales'] = df_celula[bug_cols].sum(axis=1)

columnas_mostrar = ['NombreProyecto'] + metricas_base + bug_cols + ['Bugs Totales']
df_mostrar = df_celula[columnas_mostrar].rename(columns=nombre_metricas_amigables)
df_mostrar.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

# Formateo
formatear_pct = lambda x: f"{float(x):.1f}%" if pd.notna(x) else x

df_mostrar['Cobertura de pruebas unitarias'] = df_mostrar['Cobertura de pruebas unitarias'].apply(formatear_pct)
df_mostrar['Complejidad'] = df_mostrar['Complejidad'].apply(formatear_pct)

# Resumen cumplimiento
fila_resumen = {
    'NombreProyecto': 'Cumplimiento (%)',
    'Seguridad': formatear_pct(df_celula['cumple_security'].mean() * 100),
    'Confiabilidad': formatear_pct(df_celula['cumple_reliability'].mean() * 100),
    'Mantenibilidad': formatear_pct(df_celula['cumple_maintainability'].mean() * 100),
    'Cobertura de pruebas unitarias': formatear_pct(df_celula['cumple_coverage'].mean() * 100),
    'Complejidad': formatear_pct(df_celula['cumple_duplications'].mean() * 100)
}

for col in nuevo_nombre_cols_bugs_tabla.values():
    if col in df_mostrar.columns:
        fila_resumen[col] = ""

if 'Bugs Totales' in df_mostrar.columns:
    fila_resumen['Bugs Totales'] = df_celula['Bugs Totales'].sum()

df_mostrar_final = pd.concat([df_mostrar, pd.DataFrame([fila_resumen])], ignore_index=True)

def resaltar_resumen(row):
    return ['background-color: #f0f0f0; font-weight: bold'] * len(row) if row['NombreProyecto'] == 'Cumplimiento (%)' else [''] * len(row)

df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Resumen bugs
resumen_bugs = df_celula[bug_cols].sum().astype(int).to_frame().T
resumen_bugs.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

if 'Bugs Totales' in df_celula:
    resumen_bugs['Bugs Totales'] = df_celula['Bugs Totales'].sum()

st.subheader("📊 Resumen total de bugs en la célula")
st.dataframe(resumen_bugs, hide_index=True)

fig = px.bar(
    resumen_bugs.melt(var_name='Tipo de Bug', value_name='Cantidad'),
    x='Tipo de Bug',
    y='Cantidad',
    title=f"Cantidad total de bugs por tipo en {celula_seleccionada}"
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

if not df_historico.empty and 'Mes' in df_historico.columns:
    df_historico_filtrado = df_historico[
        (df_historico['Celula'] == celula_seleccionada) &
        (df_historico['NombreProyecto'].isin(proyectos_filtrados))
    ].copy()

    df_historico_filtrado['Mes'] = pd.to_datetime(df_historico_filtrado['Mes']).dt.to_period('M').dt.to_timestamp()

    df_historico_filtrado['cumple_security'] = df_historico_filtrado['security_rating'].isin(umbral_security)
    df_historico_filtrado['cumple_reliability'] = df_historico_filtrado['reliability_rating'].isin(umbral_reliability)
    df_historico_filtrado['cumple_maintainability'] = df_historico_filtrado['sqale_rating'].isin(umbral_sqale)
    df_historico_filtrado['cumple_coverage'] = df_historico_filtrado['coverage'] >= coverage_min
    df_historico_filtrado['cumple_duplications'] = df_historico_filtrado['complexity'] <= duplications_max

    nombres_tendencias = {
        'cumple_security': 'Seguridad',
        'cumple_reliability': 'Confiabilidad',
        'cumple_maintainability': 'Mantenibilidad',
        'cumple_coverage': 'Cobertura de pruebas unitarias',
        'cumple_duplications': 'Complejidad'
    }

    for metrica, nombre_metrica in nombres_tendencias.items():
        tendencia = df_historico_filtrado.groupby('Mes')[metrica].mean().reset_index()

        if metrica.startswith("cumple_"):
            tendencia[metrica] = tendencia[metrica] * 100
            y_label = f"% Cumplimiento en {nombre_metrica}"
        else:
            tendencia[metrica] = tendencia[metrica].round(1)
            y_label = f"{nombre_metrica} Promedio"

        tendencia['Mes'] = tendencia['Mes'].dt.strftime('%Y-%m')

        fig = px.line(
            tendencia,
            x='Mes',
            y=metrica,
            markers=True,
            title=f"Tendencia de {nombre_metrica}",
            labels={metrica: y_label, 'Mes': 'Mes'}
        )
        st.plotly_chart(fig, use_container_width=True)
