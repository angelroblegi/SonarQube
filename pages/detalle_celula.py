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
ARCHIVO_METAS = "data/metas_progreso.csv"
ARCHIVO_CONFIGURACION_METRICAS = "data/configuracion_metricas.csv"  # Nuevo archivo
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

def cargar_configuracion_metricas():
    """Cargar configuración de métricas (si usar proyectos seleccionados o todos)"""
    if os.path.exists(ARCHIVO_CONFIGURACION_METRICAS):
        df_config = pd.read_csv(ARCHIVO_CONFIGURACION_METRICAS)
        if not df_config.empty:
            fila = df_config.iloc[0]
            return {
                "security_usar_seleccionados": fila.get("security_usar_seleccionados", False),
                "reliability_usar_seleccionados": fila.get("reliability_usar_seleccionados", False),
                "maintainability_usar_seleccionados": fila.get("maintainability_usar_seleccionados", False),
                "coverage_usar_seleccionados": fila.get("coverage_usar_seleccionados", True),
                "duplications_usar_seleccionados": fila.get("duplications_usar_seleccionados", False)
            }
    return {
        "security_usar_seleccionados": False,
        "reliability_usar_seleccionados": False,
        "maintainability_usar_seleccionados": False,
        "coverage_usar_seleccionados": True,
        "duplications_usar_seleccionados": False
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

def filtrar_datos_por_metrica(df, celula, proyectos_seleccionados, usar_seleccionados):
    """Filtrar datos según configuración de métrica específica"""
    if usar_seleccionados and celula in proyectos_seleccionados and proyectos_seleccionados[celula]:
        # Usar solo proyectos seleccionados para esta célula
        return df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos_seleccionados[celula]))]
    else:
        # Usar todos los proyectos de la célula
        return df[df['Celula'] == celula]

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
config_metricas = cargar_configuracion_metricas()
metas = cargar_metas()
metricas_seleccionadas = cargar_metricas_seleccionadas()

# Configuración de filtros
st.title("🔎 Detalle de Métricas por Célula")

celulas = df_ultimo['Celula'].unique()
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas)

# Filtrar datos según configuración para cada métrica
df_security = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["security_usar_seleccionados"])
df_reliability = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["reliability_usar_seleccionados"])
df_maintainability = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["maintainability_usar_seleccionados"])
df_coverage = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["coverage_usar_seleccionados"])
df_duplications = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["duplications_usar_seleccionados"])

# Proyectos a excluir para cálculo coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

# Verificar que hay datos para mostrar
proyectos_para_mostrar = set()
if 'security_rating' in metricas_seleccionadas and not df_security.empty:
    proyectos_para_mostrar.update(df_security['NombreProyecto'].tolist())
if 'reliability_rating' in metricas_seleccionadas and not df_reliability.empty:
    proyectos_para_mostrar.update(df_reliability['NombreProyecto'].tolist())
if 'sqale_rating' in metricas_seleccionadas and not df_maintainability.empty:
    proyectos_para_mostrar.update(df_maintainability['NombreProyecto'].tolist())
if 'coverage' in metricas_seleccionadas and not df_coverage.empty:
    proyectos_para_mostrar.update(df_coverage['NombreProyecto'].tolist())
if 'complexity' in metricas_seleccionadas and not df_duplications.empty:
    proyectos_para_mostrar.update(df_duplications['NombreProyecto'].tolist())

if not proyectos_para_mostrar:
    st.warning("⚠️ No hay proyectos disponibles para esta célula con la configuración actual.")
    st.stop()

# Crear dataframe combinado para mostrar
df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_para_mostrar))].copy()

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

df_celula['excluir_coverage'] = df_celula['NombreProyecto'].isin(proyectos_excluir_coverage)

# === NUEVA SECCIÓN: PROGRESO HACIA METAS ===
st.markdown("---")
st.header(f"🎯 Progreso hacia Metas - {celula_seleccionada}")



# Calcular cumplimiento usando los dataframes filtrados correspondientes
cumplimiento_data = []

if 'security_rating' in metricas_seleccionadas and not df_security.empty:
    df_security_calc = df_security.copy()
    df_security_calc['cumple_security'] = df_security_calc['security_rating'].isin(umbral_security)
    cumplimiento_security_pct = df_security_calc['cumple_security'].mean() * 100
    cumplimiento_data.append(('Seguridad', cumplimiento_security_pct, metas["meta_security"], '#1f77b4'))

if 'reliability_rating' in metricas_seleccionadas and not df_reliability.empty:
    df_reliability_calc = df_reliability.copy()
    df_reliability_calc['cumple_reliability'] = df_reliability_calc['reliability_rating'].isin(umbral_reliability)
    cumplimiento_reliability_pct = df_reliability_calc['cumple_reliability'].mean() * 100
    cumplimiento_data.append(('Confiabilidad', cumplimiento_reliability_pct, metas["meta_reliability"], '#ff7f0e'))

if 'sqale_rating' in metricas_seleccionadas and not df_maintainability.empty:
    df_maintainability_calc = df_maintainability.copy()
    df_maintainability_calc['cumple_maintainability'] = df_maintainability_calc['sqale_rating'].isin(umbral_sqale)
    cumplimiento_maintainability_pct = df_maintainability_calc['cumple_maintainability'].mean() * 100
    cumplimiento_data.append(('Mantenibilidad', cumplimiento_maintainability_pct, metas["meta_maintainability"], '#2ca02c'))

if 'coverage' in metricas_seleccionadas and not df_coverage.empty:
    df_coverage_calc = df_coverage.copy()
    df_coverage_calc['cumple_coverage'] = df_coverage_calc['coverage'] >= coverage_min
    df_coverage_calc['excluir_coverage'] = df_coverage_calc['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_coverage_filtrado = df_coverage_calc[~df_coverage_calc['excluir_coverage']]
    if not df_coverage_filtrado.empty:
        cumplimiento_coverage_pct = df_coverage_filtrado['cumple_coverage'].mean() * 100
        cumplimiento_data.append(('Cobertura', cumplimiento_coverage_pct, metas["meta_coverage"], '#d62728'))

if 'complexity' in metricas_seleccionadas and not df_duplications.empty:
    df_duplications_calc = df_duplications.copy()
    df_duplications_calc['cumple_duplications'] = df_duplications_calc['complexity'].isin(umbral_complexity)
    cumplimiento_duplications_pct = df_duplications_calc['cumple_duplications'].mean() * 100
    cumplimiento_data.append(('Complejidad', cumplimiento_duplications_pct, metas["meta_duplications"], '#9467bd'))

# Mostrar barras de progreso
if cumplimiento_data:
    cols = st.columns(len(cumplimiento_data))
    
    for i, (nombre, actual, meta, color) in enumerate(cumplimiento_data):
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

bug_cols = ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']  # Nuevo orden
nuevo_nombre_cols_bugs_tabla = {
    'bugs_blocker': 'Crítica',
    'bugs_critical': 'Alta', 
    'bugs_major': 'Media',
    'bugs_minor': 'Baja'
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

# Crear fila de resumen usando los datos filtrados por métrica
fila_resumen = {'NombreProyecto': 'Cumplimiento (%)'}

if 'security_rating' in metricas_seleccionadas and not df_security.empty:
    df_temp = df_security.copy()
    df_temp['cumple_security'] = df_temp['security_rating'].isin(umbral_security)
    fila_resumen['Seguridad'] = formatear_pct(df_temp['cumple_security'].mean() * 100)

if 'reliability_rating' in metricas_seleccionadas and not df_reliability.empty:
    df_temp = df_reliability.copy()
    df_temp['cumple_reliability'] = df_temp['reliability_rating'].isin(umbral_reliability)
    fila_resumen['Confiabilidad'] = formatear_pct(df_temp['cumple_reliability'].mean() * 100)

if 'sqale_rating' in metricas_seleccionadas and not df_maintainability.empty:
    df_temp = df_maintainability.copy()
    df_temp['cumple_maintainability'] = df_temp['sqale_rating'].isin(umbral_sqale)
    fila_resumen['Mantenibilidad'] = formatear_pct(df_temp['cumple_maintainability'].mean() * 100)

if 'coverage' in metricas_seleccionadas and not df_coverage.empty:
    df_temp = df_coverage.copy()
    df_temp['cumple_coverage'] = df_temp['coverage'] >= coverage_min
    df_temp['excluir_coverage'] = df_temp['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_temp_filtrado = df_temp[~df_temp['excluir_coverage']]
    if not df_temp_filtrado.empty:
        fila_resumen['Cobertura de pruebas unitarias'] = formatear_pct(df_temp_filtrado['cumple_coverage'].mean() * 100)

if 'complexity' in metricas_seleccionadas and not df_duplications.empty:
    df_temp = df_duplications.copy()
    df_temp['cumple_duplications'] = df_temp['complexity'].isin(umbral_complexity)
    fila_resumen['Complejidad'] = formatear_pct(df_temp['cumple_duplications'].mean() * 100)

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

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Separar tablas de cobertura si está seleccionada
if 'coverage' in metricas_seleccionadas and not df_coverage.empty:
    st.markdown("---")
    st.title("📊 Detalle de Cobertura de Pruebas Unitarias")
    
    # Tabla 1: Proyectos considerados para cobertura
    proyectos_coverage = df_coverage.copy()
    proyectos_coverage['cumple_coverage'] = proyectos_coverage['coverage'] >= coverage_min
    proyectos_coverage['excluir_coverage'] = proyectos_coverage['NombreProyecto'].isin(proyectos_excluir_coverage)
    
    proyectos_coverage_incluidos = proyectos_coverage[~proyectos_coverage['excluir_coverage']][['NombreProyecto', 'coverage', 'cumple_coverage']].copy()
    
    if not proyectos_coverage_incluidos.empty:
        proyectos_coverage_incluidos['coverage'] = proyectos_coverage_incluidos['coverage'].apply(formatear_pct)
        proyectos_coverage_incluidos['cumple_coverage'] = proyectos_coverage_incluidos['cumple_coverage'].map({True: '✅', False: '❌'})
        proyectos_coverage_incluidos.rename(columns={
            'NombreProyecto': 'Proyecto',
            'coverage': 'Cobertura',
            'cumple_coverage': 'Cumple'
        }, inplace=True)
        
        st.subheader("🎯 Proyectos incluidos en el cálculo de cobertura")
        
        # Calcular porcentaje de cumplimiento para agregar a la tabla
        proyectos_que_cumplen = len(proyectos_coverage_incluidos[proyectos_coverage_incluidos['Cumple'] == '✅'])
        total_proyectos_coverage = len(proyectos_coverage_incluidos)
        
        if total_proyectos_coverage > 0:
            porcentaje_cumplimiento = (proyectos_que_cumplen / total_proyectos_coverage) * 100
            
            # Agregar fila de cumplimiento a la tabla
            fila_cumplimiento = {
                'Proyecto': 'Cumplimiento (%)',
                'Cobertura': f"{porcentaje_cumplimiento:.1f}%",
                'Cumple': f"{proyectos_que_cumplen}/{total_proyectos_coverage}"
            }
            
            # Concatenar la fila de cumplimiento
            proyectos_coverage_final = pd.concat([proyectos_coverage_incluidos, pd.DataFrame([fila_cumplimiento])], ignore_index=True)
            
            # Función para resaltar la fila de cumplimiento
            def resaltar_cumplimiento(row):
                return ['background-color: #e8f4fd; font-weight: bold'] * len(row) if row['Proyecto'] == 'Cumplimiento (%)' else [''] * len(row)
            
            proyectos_coverage_styled = proyectos_coverage_final.style.apply(resaltar_cumplimiento, axis=1)
            st.dataframe(proyectos_coverage_styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(proyectos_coverage_incluidos, use_container_width=True, hide_index=True)
    
    # Tabla 2: Proyectos excluidos de cobertura
    proyectos_excluidos = proyectos_coverage[proyectos_coverage['excluir_coverage']][['NombreProyecto', 'coverage']].copy()
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
    # Mantener el orden específico: Crítica, Alta, Media, Baja
    resumen_bugs = df_celula[bug_cols].sum().astype(int).to_frame().T
    resumen_bugs.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)
    
    # Reordenar las columnas para mantener el orden deseado
    orden_columnas = ['Crítica', 'Alta', 'Media', 'Baja']
    columnas_disponibles = [col for col in orden_columnas if col in resumen_bugs.columns]
    if 'Bugs Totales' in resumen_bugs.columns:
        columnas_disponibles.append('Bugs Totales')
    resumen_bugs = resumen_bugs[columnas_disponibles]

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
    # Aplicar filtros históricos según configuración de métricas
    nombres_tendencias = {
        'security_rating': 'Seguridad',
        'reliability_rating': 'Confiabilidad',
        'sqale_rating': 'Mantenibilidad',
        'coverage': 'Cobertura',
        'complexity': 'Complejidad'
    }

    for metrica in metricas_seleccionadas:
        if metrica not in df_historico.columns:
            continue

        usar_seleccionados = config_metricas.get(f"{metrica.split('_')[0]}_usar_seleccionados", False)

        cumplimiento_por_mes = []

        for mes in sorted(df_historico['Mes'].unique()):
            df_mes = df_historico[df_historico['Mes'] == mes]
            df_filtrado = filtrar_datos_por_metrica(df_mes, celula_seleccionada, seleccion_proyectos, usar_seleccionados)

            if df_filtrado.empty:
                continue

            if metrica == 'coverage':
                df_filtrado = df_filtrado[~df_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)]
                if df_filtrado.empty:
                    continue
                valor = (df_filtrado['coverage'] >= coverage_min).mean() * 100

            elif metrica == 'complexity':
                valor = df_filtrado['complexity'].isin(umbral_complexity).mean() * 100

            elif metrica == 'security_rating':
                valor = df_filtrado['security_rating'].isin(umbral_security).mean() * 100

            elif metrica == 'reliability_rating':
                valor = df_filtrado['reliability_rating'].isin(umbral_reliability).mean() * 100

            elif metrica == 'sqale_rating':
                valor = df_filtrado['sqale_rating'].isin(umbral_sqale).mean() * 100

            cumplimiento_por_mes.append({
                'Mes': mes,
                'Cumplimiento (%)': valor
            })

        if cumplimiento_por_mes:
            df_trend = pd.DataFrame(cumplimiento_por_mes)
            df_trend.sort_values(by='Mes', inplace=True)

            fig_trend = px.line(
                df_trend,
                x='Mes',
                y='Cumplimiento (%)',
                title=f"Tendencia histórica de cumplimiento - {nombres_tendencias.get(metrica, metrica)}",
                markers=True
            )

            meta = metas.get(f"meta_{metrica.split('_')[0]}", None)
            if meta:
                fig_trend.add_shape(
                    type="line",
                    x0=df_trend['Mes'].min(),
                    x1=df_trend['Mes'].max(),
                    y0=meta,
                    y1=meta,
                    line=dict(color="red", width=2, dash="dash"),
                    name="Meta"
                )
                fig_trend.add_annotation(
                    x=df_trend['Mes'].max(),
                    y=meta,
                    text="Meta",
                    showarrow=False,
                    yshift=10,
                    font=dict(color="red")
                )

            fig_trend.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info(f"No hay datos históricos suficientes para mostrar tendencia de **{nombres_tendencias.get(metrica, metrica)}**.")
else:
    st.info("No hay datos históricos disponibles.")

