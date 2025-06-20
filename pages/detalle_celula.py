import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
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
ARCHIVO_METRICAS_SELECCIONADAS = "data/metricas_seleccionadas.csv"
ARCHIVO_METAS = "data/metas_progreso.csv"  # Archivo de metas
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

    # Complexity es un rating (A, B, C, D, E), no un porcentaje
    if 'duplicated_lines_density' in df.columns:
        df['complexity'] = df['duplicated_lines_density'].astype(str).str.strip()
    elif 'complexity' in df.columns:
        df['complexity'] = df['complexity'].astype(str).str.strip()
    else:
        df['complexity'] = 'N/A'

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
                "complexity_rating": fila.get("complexity_rating", "A,B,C,D,E"),
                "coverage_min": float(fila.get("coverage_min", 0))
            }
    return {
        "security_rating": "A,B,C,D,E",
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E",
        "complexity_rating": "A,B,C,D,E",
        "coverage_min": 0
    }

def cargar_metas():
    """Cargar metas de progreso desde archivo CSV"""
    if os.path.exists(ARCHIVO_METAS):
        df_metas = pd.read_csv(ARCHIVO_METAS)
        if not df_metas.empty:
            fila = df_metas.iloc[0]
            return {
                "meta_security": float(fila.get("meta_security", 70)),
                "meta_reliability": float(fila.get("meta_reliability", 70)),
                "meta_maintainability": float(fila.get("meta_maintainability", 70)),
                "meta_coverage": float(fila.get("meta_coverage", 70)),
                "meta_duplications": float(fila.get("meta_duplications", 70))
            }
    return {
        "meta_security": 70.0,
        "meta_reliability": 70.0,
        "meta_maintainability": 70.0,
        "meta_coverage": 70.0,
        "meta_duplications": 70.0
    }

def cargar_metricas_seleccionadas():
    if os.path.exists(ARCHIVO_METRICAS_SELECCIONADAS):
        df_metricas = pd.read_csv(ARCHIVO_METRICAS_SELECCIONADAS)
        return df_metricas['metrica'].tolist()
    return ['security_rating', 'reliability_rating', 'sqale_rating', 'coverage', 'complexity']

def crear_barra_progreso(actual, meta, color="blue"):
    """Crear una barra de progreso usando Plotly"""
    progreso = min(actual / meta * 100, 100) if meta > 0 else 0
    
    fig = go.Figure(go.Bar(
        x=[progreso],
        y=[''],
        orientation='h',
        marker_color=color,
        text=f'{actual:.1f}% / {meta:.0f}%',
        textposition='inside',
        textfont=dict(color='white', size=14)
    ))
    
    fig.update_layout(
        xaxis=dict(range=[0, 100], showticklabels=False),
        yaxis=dict(showticklabels=False),
        height=40,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

df_ultimo = cargar_datos(ultimo_archivo)
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()
metas = cargar_metas()
metricas_seleccionadas = cargar_metricas_seleccionadas()

# Configuración de filtros
st.title("🔎 Detalle de Métricas por Célula")

col1, col2 = st.columns(2)
with col1:
    celulas = df_ultimo['Celula'].unique()
    celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas)

with col2:
    tipo_proyectos = st.radio(
        "Tipo de proyectos a mostrar:",
        options=["Seleccionados", "Todos"],
        help="Seleccionados: Solo proyectos configurados en 'Seleccionar proyectos'\nTodos: Todos los proyectos de la célula"
    )

# Filtrar proyectos según selección
if tipo_proyectos == "Seleccionados":
    proyectos_filtrados = seleccion_proyectos.get(celula_seleccionada, [])
    if not proyectos_filtrados:
        st.warning("⚠️ No hay proyectos seleccionados para esta célula. Ve a 'Seleccionar proyectos' para configurarlo.")
        st.stop()
    df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_filtrados))].copy()
else:
    df_celula = df_ultimo[df_ultimo['Celula'] == celula_seleccionada].copy()
    proyectos_filtrados = df_celula['NombreProyecto'].tolist()

# Aplicar parámetros
umbral_security = parametros["security_rating"].split(",")
umbral_reliability = parametros["reliability_rating"].split(",")
umbral_sqale = parametros["sqale_rating"].split(",")
umbral_complexity = parametros["complexity_rating"].split(",")
coverage_min = parametros["coverage_min"]

df_celula['cumple_security'] = df_celula['security_rating'].isin(umbral_security)
df_celula['cumple_reliability'] = df_celula['reliability_rating'].isin(umbral_reliability)
df_celula['cumple_maintainability'] = df_celula['sqale_rating'].isin(umbral_sqale)
df_celula['cumple_coverage'] = df_celula['coverage'] >= coverage_min
df_celula['cumple_duplications'] = df_celula['complexity'].isin(umbral_complexity)

# Proyectos a excluir para cálculo coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

df_celula['excluir_coverage'] = df_celula['NombreProyecto'].isin(proyectos_excluir_coverage)

# === NUEVA SECCIÓN: PROGRESO HACIA METAS ===
st.markdown("---")
st.header(f"🎯 Progreso hacia Metas - {celula_seleccionada}")

# Calcular cumplimiento para coverage excluyendo proyectos específicos
df_filtrado_coverage = df_celula.loc[~df_celula['excluir_coverage']]
if not df_filtrado_coverage.empty:
    cumplimiento_coverage_pct = (df_filtrado_coverage['cumple_coverage'].sum() / len(df_filtrado_coverage)) * 100
else:
    cumplimiento_coverage_pct = 0

# Calcular cumplimiento para otras métricas
cumplimiento_security_pct = df_celula['cumple_security'].mean() * 100
cumplimiento_reliability_pct = df_celula['cumple_reliability'].mean() * 100
cumplimiento_maintainability_pct = df_celula['cumple_maintainability'].mean() * 100
cumplimiento_duplications_pct = df_celula['cumple_duplications'].mean() * 100

# Colores para cada métrica
colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

# Preparar datos de progreso
metricas_progreso = [
    ('Seguridad', cumplimiento_security_pct, metas["meta_security"], colores[0]),
    ('Confiabilidad', cumplimiento_reliability_pct, metas["meta_reliability"], colores[1]),
    ('Mantenibilidad', cumplimiento_maintainability_pct, metas["meta_maintainability"], colores[2]),
    ('Cobertura', cumplimiento_coverage_pct, metas["meta_coverage"], colores[3]),
    ('Complejidad', cumplimiento_duplications_pct, metas["meta_duplications"], colores[4])
]

# Mostrar barras de progreso
cols = st.columns(5)

for i, (nombre, actual, meta, color) in enumerate(metricas_progreso):
    with cols[i]:
        st.markdown(f"**{nombre}**")
        
        # Crear barra de progreso
        fig_progress = crear_barra_progreso(actual, meta, color)
        st.plotly_chart(fig_progress, use_container_width=True, config={'displayModeBar': False}, 
                      key=f"progress_{celula_seleccionada}_{nombre}")
        
        # Mostrar estado
        if actual >= meta:
            st.success(f"✅ Meta alcanzada")
        else:
            faltante = meta - actual
            st.warning(f"⚠️ Falta {faltante:.1f}%")

# === CONTINUACIÓN DEL CÓDIGO ORIGINAL ===

# Nombres amigables para métricas
nombre_metricas_amigables = {
    'security_rating': 'Seguridad',
    'reliability_rating': 'Confiabilidad',
    'sqale_rating': 'Mantenibilidad',
    'coverage': 'Cobertura de pruebas unitarias',
    'complexity': 'Complejidad'
}

bug_cols = ['bugs_major', 'bugs_minor', 'bugs_blocker', 'bugs_critical']
nuevo_nombre_cols_bugs_tabla = {
    'bugs_major': 'Major',
    'bugs_minor': 'Minor',
    'bugs_blocker': 'Blocker',
    'bugs_critical': 'Critical'
}

if all(col in df_celula.columns for col in bug_cols):
    df_celula['Bugs Totales'] = df_celula[bug_cols].sum(axis=1)

# Función para formatear porcentajes
formatear_pct = lambda x: f"{float(x):.1f}%" if pd.notna(x) else x

# Preparar columnas para mostrar basadas en métricas seleccionadas
columnas_mostrar = ['NombreProyecto']
for metrica in metricas_seleccionadas:
    if metrica in df_celula.columns:
        columnas_mostrar.append(metrica)

# Agregar columnas de bugs si existen
columnas_mostrar.extend([col for col in bug_cols if col in df_celula.columns])
if 'Bugs Totales' in df_celula.columns:
    columnas_mostrar.append('Bugs Totales')

# Crear tabla principal
df_mostrar = df_celula[columnas_mostrar].copy()
df_mostrar.rename(columns=nombre_metricas_amigables, inplace=True)
df_mostrar.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

# Aplicar formato a métricas de porcentaje
if 'Cobertura de pruebas unitarias' in df_mostrar.columns:
    df_mostrar['Cobertura de pruebas unitarias'] = df_mostrar['Cobertura de pruebas unitarias'].apply(formatear_pct)
# Complexity ya viene como rating, no necesita formato de porcentaje

# Crear fila de resumen
fila_resumen = {'NombreProyecto': 'Cumplimiento (%)'}

if 'security_rating' in metricas_seleccionadas:
    fila_resumen['Seguridad'] = formatear_pct(df_celula['cumple_security'].mean() * 100)
if 'reliability_rating' in metricas_seleccionadas:
    fila_resumen['Confiabilidad'] = formatear_pct(df_celula['cumple_reliability'].mean() * 100)
if 'sqale_rating' in metricas_seleccionadas:
    fila_resumen['Mantenibilidad'] = formatear_pct(df_celula['cumple_maintainability'].mean() * 100)
if 'coverage' in metricas_seleccionadas:
    fila_resumen['Cobertura de pruebas unitarias'] = formatear_pct(cumplimiento_coverage_pct)
if 'complexity' in metricas_seleccionadas:
    fila_resumen['Complejidad'] = formatear_pct(df_celula['cumple_duplications'].mean() * 100)

# Completar fila de resumen con columnas de bugs
for col in nuevo_nombre_cols_bugs_tabla.values():
    if col in df_mostrar.columns:
        fila_resumen[col] = ""

if 'Bugs Totales' in df_mostrar.columns:
    fila_resumen['Bugs Totales'] = df_celula['Bugs Totales'].sum()

df_mostrar_final = pd.concat([df_mostrar, pd.DataFrame([fila_resumen])], ignore_index=True)

def resaltar_resumen(row):
    return ['background-color: #f0f0f0; font-weight: bold'] * len(row) if row['NombreProyecto'] == 'Cumplimiento (%)' else [''] * len(row)

df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada} ({tipo_proyectos.lower()})")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Separar tablas de cobertura si está seleccionada
if 'coverage' in metricas_seleccionadas:
    st.markdown("---")
    st.title("📊 Detalle de Cobertura de Pruebas Unitarias")
    
    # Tabla 1: Proyectos seleccionados para cobertura
    proyectos_coverage = df_celula.loc[~df_celula['excluir_coverage']][['NombreProyecto', 'coverage', 'cumple_coverage']].copy()
    proyectos_coverage['coverage'] = proyectos_coverage['coverage'].apply(formatear_pct)
    proyectos_coverage['cumple_coverage'] = proyectos_coverage['cumple_coverage'].map({True: '✅', False: '❌'})
    proyectos_coverage.rename(columns={
        'NombreProyecto': 'Proyecto',
        'coverage': 'Cobertura',
        'cumple_coverage': 'Cumple'
    }, inplace=True)
    
    st.subheader("🎯 Proyectos incluidos en el cálculo de cobertura")
    
    # Calcular porcentaje de cumplimiento para agregar a la tabla
    proyectos_que_cumplen = len(proyectos_coverage[proyectos_coverage['Cumple'] == '✅'])
    total_proyectos_coverage = len(proyectos_coverage)
    
    if total_proyectos_coverage > 0:
        porcentaje_cumplimiento = (proyectos_que_cumplen / total_proyectos_coverage) * 100
        
        # Agregar fila de cumplimiento a la tabla
        fila_cumplimiento = {
            'Proyecto': 'Cumplimiento (%)',
            'Cobertura': f"{porcentaje_cumplimiento:.1f}%",
            'Cumple': f"{proyectos_que_cumplen}/{total_proyectos_coverage}"
        }
        
        # Concatenar la fila de cumplimiento
        proyectos_coverage_final = pd.concat([proyectos_coverage, pd.DataFrame([fila_cumplimiento])], ignore_index=True)
        
        # Función para resaltar la fila de cumplimiento
        def resaltar_cumplimiento(row):
            return ['background-color: #e8f4fd; font-weight: bold'] * len(row) if row['Proyecto'] == 'Cumplimiento (%)' else [''] * len(row)
        
        proyectos_coverage_styled = proyectos_coverage_final.style.apply(resaltar_cumplimiento, axis=1)
        st.dataframe(proyectos_coverage_styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(proyectos_coverage, use_container_width=True, hide_index=True)
    
    # Tabla 2: Proyectos excluidos de cobertura
    proyectos_excluidos = df_celula.loc[df_celula['excluir_coverage']][['NombreProyecto', 'coverage']].copy()
    if not proyectos_excluidos.empty:
        proyectos_excluidos['coverage'] = proyectos_excluidos['coverage'].apply(formatear_pct)
        proyectos_excluidos['Motivo'] = 'Excluido del cálculo'
        proyectos_excluidos.rename(columns={
            'NombreProyecto': 'Proyecto',
            'coverage': 'Cobertura'
        }, inplace=True)
        
        st.subheader("⚠️ Proyectos excluidos del cálculo de cobertura")
        st.dataframe(proyectos_excluidos, use_container_width=True, hide_index=True)

# Resumen bugs
if any(col in df_celula.columns for col in bug_cols):
    st.markdown("---")
    resumen_bugs = df_celula[bug_cols].sum().astype(int).to_frame().T
    resumen_bugs.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

    if 'Bugs Totales' in df_celula:
        resumen_bugs['Bugs Totales'] = df_celula['Bugs Totales'].sum()

    st.subheader("🐛 Resumen total de bugs en la célula")
    st.dataframe(resumen_bugs, hide_index=True)

    fig = px.bar(
        resumen_bugs.melt(var_name='Tipo de Bug', value_name='Cantidad'),
        x='Tipo de Bug',
        y='Cantidad',
        title=f"Cantidad total de bugs por tipo en {celula_seleccionada}"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tendencias históricas
st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

if not df_historico.empty and 'Mes' in df_historico.columns:
    # Filtrar datos históricos según tipo de proyectos seleccionado
    if tipo_proyectos == "Seleccionados":
        proyectos_para_tendencia = seleccion_proyectos.get(celula_seleccionada, [])
    else:
        proyectos_para_tendencia = df_historico[df_historico['Celula'] == celula_seleccionada]['NombreProyecto'].unique().tolist()
    
    df_historico_filtrado = df_historico[
        (df_historico['Celula'] == celula_seleccionada) &
        (df_historico['NombreProyecto'].isin(proyectos_para_tendencia))
    ].copy()

    df_historico_filtrado['Mes'] = pd.to_datetime(df_historico_filtrado['Mes']).dt.to_period('M').dt.to_timestamp()

    df_historico_filtrado['cumple_security'] = df_historico_filtrado['security_rating'].isin(umbral_security)
    df_historico_filtrado['cumple_reliability'] = df_historico_filtrado['reliability_rating'].isin(umbral_reliability)
    df_historico_filtrado['cumple_maintainability'] = df_historico_filtrado['sqale_rating'].isin(umbral_sqale)
    df_historico_filtrado['cumple_coverage'] = df_historico_filtrado['coverage'] >= coverage_min
    df_historico_filtrado['cumple_duplications'] = df_historico_filtrado['complexity'].isin(umbral_complexity)

    # Excluir proyectos para coverage en tendencia histórica
    df_historico_filtrado['excluir_coverage'] = df_historico_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)

    nombres_tendencias = {
        'cumple_security': 'Seguridad',
        'cumple_reliability': 'Confiabilidad',
        'cumple_maintainability': 'Mantenibilidad',
        'cumple_coverage': 'Cobertura de pruebas unitarias',
        'cumple_duplications': 'Complejidad'
    }

    # Mostrar solo tendencias de métricas seleccionadas
    metricas_cumplimiento = []
    for metrica in metricas_seleccionadas:
        if metrica == 'security_rating':
            metricas_cumplimiento.append('cumple_security')
        elif metrica == 'reliability_rating':
            metricas_cumplimiento.append('cumple_reliability')
        elif metrica == 'sqale_rating':
            metricas_cumplimiento.append('cumple_maintainability')
        elif metrica == 'coverage':
            metricas_cumplimiento.append('cumple_coverage')
        elif metrica == 'complexity':
            metricas_cumplimiento.append('cumple_duplications')

    for metrica in metricas_cumplimiento:
        nombre_metrica = nombres_tendencias[metrica]
        
        if metrica == 'cumple_coverage':
            df_temp = df_historico_filtrado.loc[~df_historico_filtrado['excluir_coverage']]
            if df_temp.empty:
                continue
            tendencia = df_temp.groupby('Mes')[metrica].mean().reset_index()
        else:
            tendencia = df_historico_filtrado.groupby('Mes')[metrica].mean().reset_index()

        if tendencia.empty:
            continue

        tendencia[metrica] = tendencia[metrica] * 100
        y_label = f"% Cumplimiento en {nombre_metrica}"

        tendencia['Mes'] = tendencia['Mes'].dt.strftime('%Y-%m')

        fig = px.line(
            tendencia,
            x='Mes',
            y=metrica,
            markers=True,
            title=f"Tendencia de {nombre_metrica} - {tipo_proyectos}",
            labels={metrica: y_label, 'Mes': 'Mes'}
        )
        fig.update_layout(yaxis=dict(tickformat='.1f', ticksuffix='%'))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📊 No hay datos históricos disponibles para mostrar tendencias.")
