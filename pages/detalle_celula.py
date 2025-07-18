import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import glob
from datetime import datetime
import math

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
ARCHIVO_CONFIGURACION_METRICAS = "data/configuracion_metricas.csv"
UPLOAD_DIR = "uploads"

def redondear_hacia_arriba(valor):
    """Redondear hacia arriba cuando el decimal es .5 o mayor"""
    if pd.isna(valor):
        return valor
    # Para .5 exacto y valores mayores, redondear hacia arriba
    return int(valor + 0.5)

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
    # NO usar fillna(0) para mantener valores NaN
    df['coverage'] = pd.to_numeric(df['coverage'], errors='coerce')

    # Complexity es un rating (A, B, C, D, E), no un porcentaje - CORREGIR para usar duplicated_lines_density
    if 'duplicated_lines_density' in df.columns:
        df['complexity'] = df['duplicated_lines_density'].astype(str).str.strip().str.upper()
        # Convertir valores inválidos a NaN en lugar de N/A
        valid_ratings = ['A', 'B', 'C', 'D', 'E']
        df['complexity'] = df['complexity'].apply(lambda x: x if x in valid_ratings else None)
    elif 'complexity' in df.columns:
        df['complexity'] = df['complexity'].astype(str).str.strip().str.upper()
        valid_ratings = ['A', 'B', 'C', 'D', 'E']
        df['complexity'] = df['complexity'].apply(lambda x: x if x in valid_ratings else None)
    else:
        df['complexity'] = None

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
                "duplicated_lines_density": fila.get("duplicated_lines_density", "A,B,C,D,E"),  # CORREGIR nombre
                "coverage_min": float(fila.get("coverage_min", 0))
            }
    return {
        "security_rating": "A,B,C,D,E",
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E",
        "duplicated_lines_density": "A,B,C,D,E",  # CORREGIR nombre
        "coverage_min": 0
    }

def cargar_configuracion_metricas():
    """Cargar configuración de métricas (si usar proyectos seleccionados o todos)"""
    if os.path.exists(ARCHIVO_CONFIGURACION_METRICAS):
        df_config = pd.read_csv(ARCHIVO_CONFIGURACION_METRICAS)
        if not df_config.empty:
            fila = df_config.iloc[0]
            return {
                "seguridad_usar_seleccionados": fila.get("seguridad_usar_seleccionados", False),
                "confiabilidad_usar_seleccionados": fila.get("confiabilidad_usar_seleccionados", False),
                "mantenibilidad_usar_seleccionados": fila.get("mantenibilidad_usar_seleccionados", False),
                "cobertura_usar_seleccionados": fila.get("cobertura_usar_seleccionados", True),
                "complejidad_usar_seleccionados": fila.get("complejidad_usar_seleccionados", False)
            }
    return {
        "seguridad_usar_seleccionados": False,
        "confiabilidad_usar_seleccionados": False,
        "mantenibilidad_usar_seleccionados": False,
        "cobertura_usar_seleccionados": True,
        "complejidad_usar_seleccionados": False
    }

def cargar_metas():
    """Cargar metas de progreso desde archivo CSV - VALORES CORREGIDOS"""
    if os.path.exists(ARCHIVO_METAS):
        df_metas = pd.read_csv(ARCHIVO_METAS)
        if not df_metas.empty:
            fila = df_metas.iloc[0]
            return {
                "meta_seguridad": float(fila.get("meta_seguridad", 90)),
                "meta_confiabilidad": float(fila.get("meta_confiabilidad", 90)),
                "meta_mantenibilidad": float(fila.get("meta_mantenibilidad", 90)),
                "meta_cobertura": float(fila.get("meta_cobertura", 50)),  # 50% por defecto
                "meta_complejidad": float(fila.get("meta_complejidad", 90))
            }
    return {
        "meta_seguridad": 90.0,      # 90% por defecto
        "meta_confiabilidad": 90.0,  # 90% por defecto
        "meta_mantenibilidad": 90.0, # 90% por defecto
        "meta_cobertura": 50.0,      # 50% por defecto
        "meta_complejidad": 90.0     # 90% por defecto
    }

def cargar_metricas_seleccionadas():
    if os.path.exists(ARCHIVO_METRICAS_SELECCIONADAS):
        df_metricas = pd.read_csv(ARCHIVO_METRICAS_SELECCIONADAS)
        return df_metricas['metrica'].tolist()
    # Comentar security_rating - no se necesita
    return ['reliability_rating', 'sqale_rating', 'coverage', 'complexity']

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
        text=f'{actual:.0f}% / {meta:.0f}%',  # CORREGIDO: formato sin decimales
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
# Filtrar para ocultar 'nan' y 'obsoleta'
celulas_filtradas = [celula for celula in celulas if celula not in ['nan', 'obsoleta'] and pd.notna(celula)]
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas_filtradas)

# Filtrar datos según configuración para cada métrica - CORREGIR nombres de las claves
df_seguridad = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["seguridad_usar_seleccionados"])
df_confiabilidad = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["confiabilidad_usar_seleccionados"])
df_mantenibilidad = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["mantenibilidad_usar_seleccionados"])
df_cobertura = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["cobertura_usar_seleccionados"])
df_complejidad = filtrar_datos_por_metrica(df_ultimo, celula_seleccionada, seleccion_proyectos, config_metricas["complejidad_usar_seleccionados"])

# Proyectos a excluir para cálculo coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

# Verificar que hay datos para mostrar - MODIFICAR para excluir proyectos sin métricas
proyectos_para_mostrar = set()
# COMENTADO: Seguridad no se necesita
# if 'security_rating' in metricas_seleccionadas and not df_seguridad.empty:
#     # EXCLUIR proyectos con métricas vacías
#     proyectos_para_mostrar.update(df_seguridad.dropna(subset=['security_rating'])['NombreProyecto'].tolist())
if 'reliability_rating' in metricas_seleccionadas and not df_confiabilidad.empty:
    # EXCLUIR proyectos con métricas vacías
    proyectos_para_mostrar.update(df_confiabilidad.dropna(subset=['reliability_rating'])['NombreProyecto'].tolist())
if 'sqale_rating' in metricas_seleccionadas and not df_mantenibilidad.empty:
    # EXCLUIR proyectos con métricas vacías
    proyectos_para_mostrar.update(df_mantenibilidad.dropna(subset=['sqale_rating'])['NombreProyecto'].tolist())
if 'coverage' in metricas_seleccionadas:
    # Para cobertura usar TODOS los proyectos de la célula (no filtrar por configuración)
    df_todos_cobertura = df_ultimo[df_ultimo['Celula'] == celula_seleccionada]
    proyectos_para_mostrar.update(df_todos_cobertura.dropna(subset=['coverage'])['NombreProyecto'].tolist())
if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    # EXCLUIR proyectos con métricas vacías
    proyectos_para_mostrar.update(df_complejidad.dropna(subset=['complexity'])['NombreProyecto'].tolist())

if not proyectos_para_mostrar:
    st.warning("⚠️ No hay proyectos disponibles para esta célula con la configuración actual.")
    st.stop()

# Crear dataframe combinado para mostrar
df_celula = df_ultimo[(df_ultimo['Celula'] == celula_seleccionada) & (df_ultimo['NombreProyecto'].isin(proyectos_para_mostrar))].copy()

# Para la tabla principal, también necesitamos TODOS los proyectos de cobertura de la célula
df_todos_celula_coverage = df_ultimo[df_ultimo['Celula'] == celula_seleccionada].dropna(subset=['coverage']).copy()

# Aplicar parámetros - CORREGIR nombre del parámetro
umbral_seguridad = parametros["security_rating"].split(",")
umbral_confiabilidad = parametros["reliability_rating"].split(",")
umbral_mantenibilidad = parametros["sqale_rating"].split(",")
umbral_complejidad = parametros["duplicated_lines_density"].split(",")  # CORREGIR nombre
cobertura_min = parametros["coverage_min"]

df_celula['cumple_security'] = df_celula['security_rating'].isin(umbral_seguridad)
df_celula['cumple_reliability'] = df_celula['reliability_rating'].isin(umbral_confiabilidad)
df_celula['cumple_maintainability'] = df_celula['sqale_rating'].isin(umbral_mantenibilidad)
df_celula['cumple_coverage'] = df_celula['coverage'] >= cobertura_min
df_celula['cumple_duplications'] = df_celula['complexity'].isin(umbral_complejidad)

df_celula['excluir_coverage'] = df_celula['NombreProyecto'].isin(proyectos_excluir_coverage)

# === NUEVA SECCIÓN: PROGRESO HACIA METAS ===
st.markdown("---")
st.header(f"🎯 Progreso hacia Metas - {celula_seleccionada}")

# Calcular cumplimiento usando los dataframes filtrados correspondientes - EXCLUIR métricas vacías
cumplimiento_data = []

# COMENTADO: Seguridad no se necesita
# if 'security_rating' in metricas_seleccionadas and not df_seguridad.empty:
#     df_security_calc = df_seguridad.dropna(subset=['security_rating']).copy()  # EXCLUIR vacías
#     if not df_security_calc.empty:
#         df_security_calc['cumple_security'] = df_security_calc['security_rating'].isin(umbral_seguridad)
#         cumplimiento_security_pct = df_security_calc['cumple_security'].mean() * 100
#         cumplimiento_data.append(('Seguridad', cumplimiento_security_pct, metas["meta_seguridad"], '#1f77b4'))

if 'reliability_rating' in metricas_seleccionadas and not df_confiabilidad.empty:
    df_reliability_calc = df_confiabilidad.dropna(subset=['reliability_rating']).copy()  # EXCLUIR vacías
    if not df_reliability_calc.empty:
        df_reliability_calc['cumple_reliability'] = df_reliability_calc['reliability_rating'].isin(umbral_confiabilidad)
        cumplimiento_reliability_pct = df_reliability_calc['cumple_reliability'].mean() * 100
        cumplimiento_reliability_pct = redondear_hacia_arriba(cumplimiento_reliability_pct)  # APLICAR REDONDEO
        cumplimiento_data.append(('Confiabilidad', cumplimiento_reliability_pct, metas["meta_confiabilidad"], '#ff7f0e'))

if 'sqale_rating' in metricas_seleccionadas and not df_mantenibilidad.empty:
    df_maintainability_calc = df_mantenibilidad.dropna(subset=['sqale_rating']).copy()  # EXCLUIR vacías
    if not df_maintainability_calc.empty:
        df_maintainability_calc['cumple_maintainability'] = df_maintainability_calc['sqale_rating'].isin(umbral_mantenibilidad)
        cumplimiento_maintainability_pct = df_maintainability_calc['cumple_maintainability'].mean() * 100
        cumplimiento_maintainability_pct = redondear_hacia_arriba(cumplimiento_maintainability_pct)  # APLICAR REDONDEO
        cumplimiento_data.append(('Mantenibilidad', cumplimiento_maintainability_pct, metas["meta_mantenibilidad"], '#2ca02c'))

if 'coverage' in metricas_seleccionadas and not df_cobertura.empty:
    # Para las BARRAS DE PROGRESO usar la configuración filtrada (df_cobertura)
    df_coverage_calc = df_cobertura.dropna(subset=['coverage']).copy()
    df_coverage_calc['cumple_coverage'] = df_coverage_calc['coverage'] >= cobertura_min
    df_coverage_calc['excluir_coverage'] = df_coverage_calc['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_coverage_filtrado = df_coverage_calc[~df_coverage_calc['excluir_coverage']]
    if not df_coverage_filtrado.empty:
        cumplimiento_coverage_pct = df_coverage_filtrado['cumple_coverage'].mean() * 100
        cumplimiento_coverage_pct = redondear_hacia_arriba(cumplimiento_coverage_pct)  # APLICAR REDONDEO
        cumplimiento_data.append(('Cobertura', cumplimiento_coverage_pct, metas["meta_cobertura"], '#d62728'))

if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    df_duplications_calc = df_complejidad.dropna(subset=['complexity']).copy()  # EXCLUIR vacías
    if not df_duplications_calc.empty:
        df_duplications_calc['cumple_duplications'] = df_duplications_calc['complexity'].isin(umbral_complejidad)
        cumplimiento_duplications_pct = df_duplications_calc['cumple_duplications'].mean() * 100
        cumplimiento_duplications_pct = redondear_hacia_arriba(cumplimiento_duplications_pct)  # APLICAR REDONDEO
        cumplimiento_data.append(('Complejidad', cumplimiento_duplications_pct, metas["meta_complejidad"], '#9467bd'))

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
                st.warning(f"⚠️ Falta {faltante:.0f}%")  # CORREGIDO: formato sin decimales

# === CONTINUACIÓN DEL CÓDIGO ORIGINAL ===

# Nombres amigables para métricas
nombre_metricas_amigables = {
    # 'security_rating': 'Seguridad',  # COMENTADO: No se necesita
    'reliability_rating': 'Confiabilidad',
    'sqale_rating': 'Mantenibilidad',
    'coverage': 'Cobertura de pruebas unitarias',
    'complexity': 'Complejidad'
}

bug_cols = ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
nuevo_nombre_cols_bugs_tabla = {
    'bugs_blocker': 'Crítica',
    'bugs_critical': 'Alta', 
    'bugs_major': 'Media',
    'bugs_minor': 'Baja'
}

if all(col in df_celula.columns for col in bug_cols):
    df_celula['Total Bugs'] = df_celula[bug_cols].sum(axis=1)  # CORREGIDO: cambié nombre

# Función para formatear porcentajes - APLICAR REDONDEO
formatear_pct = lambda x: f"{redondear_hacia_arriba(float(x)):.0f}%" if pd.notna(x) else "N/A"

# Preparar columnas para mostrar basadas en métricas seleccionadas
columnas_mostrar = ['NombreProyecto']
for metrica in metricas_seleccionadas:
    if metrica in df_celula.columns:
        columnas_mostrar.append(metrica)

# Agregar columnas de bugs si existen
columnas_mostrar.extend([col for col in bug_cols if col in df_celula.columns])
if 'Total Bugs' in df_celula.columns:  # CORREGIDO: cambié nombre
    columnas_mostrar.append('Total Bugs')

# Crear tabla principal
df_mostrar = df_celula[columnas_mostrar].copy()
df_mostrar.rename(columns=nombre_metricas_amigables, inplace=True)
df_mostrar.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)

# Aplicar formato a métricas de porcentaje
if 'Cobertura de pruebas unitarias' in df_mostrar.columns:
    df_mostrar['Cobertura de pruebas unitarias'] = df_mostrar['Cobertura de pruebas unitarias'].apply(formatear_pct)

# Aplicar formato N/A a métricas de rating que pueden tener None
columnas_rating = ['Confiabilidad', 'Mantenibilidad', 'Complejidad']  # Removido 'Seguridad'
for col in columnas_rating:
    if col in df_mostrar.columns:
        df_mostrar[col] = df_mostrar[col].apply(lambda x: "N/A" if pd.isna(x) or x is None or str(x).lower() == 'none' else x)

# Crear fila de resumen usando los datos filtrados por métrica - CORREGIR para excluir métricas vacías
fila_resumen = {'NombreProyecto': 'Cumplimiento (%)'}

# COMENTADO: Seguridad no se necesita
# if 'security_rating' in metricas_seleccionadas and not df_seguridad.empty:
#     df_temp = df_seguridad.dropna(subset=['security_rating']).copy()  # EXCLUIR vacías
#     if not df_temp.empty:
#         df_temp['cumple_security'] = df_temp['security_rating'].isin(umbral_seguridad)
#         fila_resumen['Seguridad'] = formatear_pct(df_temp['cumple_security'].mean() * 100)
#     else:
#         fila_resumen['Seguridad'] = "N/A"

if 'reliability_rating' in metricas_seleccionadas and not df_confiabilidad.empty:
    df_temp = df_confiabilidad.dropna(subset=['reliability_rating']).copy()  # EXCLUIR vacías
    if not df_temp.empty:
        df_temp['cumple_reliability'] = df_temp['reliability_rating'].isin(umbral_confiabilidad)
        fila_resumen['Confiabilidad'] = formatear_pct(df_temp['cumple_reliability'].mean() * 100)
    else:
        fila_resumen['Confiabilidad'] = "N/A"

if 'sqale_rating' in metricas_seleccionadas and not df_mantenibilidad.empty:
    df_temp = df_mantenibilidad.dropna(subset=['sqale_rating']).copy()  # EXCLUIR vacías
    if not df_temp.empty:
        df_temp['cumple_maintainability'] = df_temp['sqale_rating'].isin(umbral_mantenibilidad)
        fila_resumen['Mantenibilidad'] = formatear_pct(df_temp['cumple_maintainability'].mean() * 100)
    else:
        fila_resumen['Mantenibilidad'] = "N/A"

if 'coverage' in metricas_seleccionadas:
    # Para cobertura en la TABLA PRINCIPAL usar TODOS los proyectos de la célula (NO los filtrados por configuración)
    df_temp = df_todos_celula_coverage.copy()
    df_temp['cumple_coverage'] = df_temp['coverage'] >= cobertura_min
    df_temp['excluir_coverage'] = df_temp['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_temp_filtrado = df_temp[~df_temp['excluir_coverage']]
    if not df_temp_filtrado.empty:
        fila_resumen['Cobertura de pruebas unitarias'] = formatear_pct(df_temp_filtrado['cumple_coverage'].mean() * 100)
    else:
        fila_resumen['Cobertura de pruebas unitarias'] = "N/A"

if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    df_temp = df_complejidad.dropna(subset=['complexity']).copy()  # EXCLUIR vacías
    if not df_temp.empty:
        df_temp['cumple_duplications'] = df_temp['complexity'].isin(umbral_complejidad)
        fila_resumen['Complejidad'] = formatear_pct(df_temp['cumple_duplications'].mean() * 100)
    else:
        fila_resumen['Complejidad'] = "N/A"

# Completar fila de resumen con columnas de bugs
for col in nuevo_nombre_cols_bugs_tabla.values():
    if col in df_mostrar.columns:
        fila_resumen[col] = ""

if 'Total Bugs' in df_mostrar.columns:  # CORREGIDO: cambié nombre
    fila_resumen['Total Bugs'] = df_celula['Total Bugs'].sum()

df_mostrar_final = pd.concat([df_mostrar, pd.DataFrame([fila_resumen])], ignore_index=True)

def resaltar_resumen(row):
    return ['background-color: #f0f0f0; font-weight: bold'] * len(row) if row['NombreProyecto'] == 'Cumplimiento (%)' else [''] * len(row)

df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Separar tablas de cobertura si está seleccionada
if 'coverage' in metricas_seleccionadas:
    st.markdown("---")
    st.title("📊 Detalle de Cobertura de Pruebas Unitarias")
    
    # Tabla 1: Proyectos considerados para cobertura - USAR configuración filtrada
    proyectos_coverage = df_cobertura.dropna(subset=['coverage']).copy()
    proyectos_coverage['cumple_coverage'] = proyectos_coverage['coverage'] >= cobertura_min
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
            porcentaje_cumplimiento = redondear_hacia_arriba(porcentaje_cumplimiento)  # APLICAR REDONDEO
            
            # Agregar fila de cumplimiento a la tabla
            fila_cumplimiento = {
                'Proyecto': 'Cumplimiento (%)',
                'Cobertura': f"{porcentaje_cumplimiento:.0f}%",  # FORMATO SIN DECIMALES
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

# Resumen bugs y tendencia histórica
if any(col in df_celula.columns for col in bug_cols):
    st.markdown("---")
    st.subheader("🐛 Resumen actual de bugs en la célula")
    
    # Tabla resumen actual (mantener la tabla)
    resumen_bugs_actual = df_celula[bug_cols].sum().astype(int).to_frame().T
    resumen_bugs_actual.rename(columns=nuevo_nombre_cols_bugs_tabla, inplace=True)
    
    # Agregar Total Bugs si existe en df_celula
    if 'Total Bugs' in df_celula.columns:
        resumen_bugs_actual['Total Bugs'] = df_celula['Total Bugs'].sum()
    
    # Reordenar las columnas para mantener el orden deseado
    orden_columnas = ['Crítica', 'Alta', 'Media', 'Baja']
    columnas_disponibles = [col for col in orden_columnas if col in resumen_bugs_actual.columns]
    
    if 'Total Bugs' in resumen_bugs_actual.columns:
        columnas_disponibles.append('Total Bugs')
    
    resumen_bugs_actual = resumen_bugs_actual[columnas_disponibles]
    st.dataframe(resumen_bugs_actual, hide_index=True)
    
    # NUEVA SECCIÓN: Tendencia histórica de bugs
    st.subheader("📈 Tendencia histórica de bugs")
    
    if not df_historico.empty and 'Mes' in df_historico.columns:
        # Asegurar formato de fecha consistente
        df_historico_bugs = df_historico.copy()
        df_historico_bugs['Mes'] = pd.to_datetime(df_historico_bugs['Mes'], errors='coerce')
        df_historico_bugs = df_historico_bugs.dropna(subset=['Mes'])
        
        bugs_por_mes = []
        
        # Verificar qué columnas de bugs existen realmente en los datos históricos
        bug_cols_disponibles = {
            'bugs_blocker': 'Crítica',
            'bugs_critical': 'Alta', 
            'bugs_major': 'Media',
            'bugs_minor': 'Baja'
        }
        
        # Solo usar columnas que existen en el DataFrame histórico
        bug_cols_existentes = {col: nombre for col, nombre in bug_cols_disponibles.items() 
                              if col in df_historico_bugs.columns}
        
        if not bug_cols_existentes:
            st.warning("No se encontraron columnas de bugs en los datos históricos.")
        else:
            # Procesar cada mes disponible
            for mes_fecha in sorted(df_historico_bugs['Mes'].dt.to_period('M').unique()):
                df_mes = df_historico_bugs[df_historico_bugs['Mes'].dt.to_period('M') == mes_fecha]
                
                # Filtrar por célula seleccionada
                df_celula_mes = df_mes[df_mes['Celula'] == celula_seleccionada]
                
                if df_celula_mes.empty:
                    continue
                
                # Inicializar bugs_mes con valores por defecto
                bugs_mes = {'Mes': mes_fecha.to_timestamp()}
                
                # Sumar bugs por tipo para ese mes - solo columnas que existen
                total_bugs = 0
                for col_original, nombre_friendly in bug_cols_existentes.items():
                    if col_original in df_celula_mes.columns:
                        valor = df_celula_mes[col_original].fillna(0).astype(int).sum()
                        bugs_mes[nombre_friendly] = valor
                        total_bugs += valor
                    else:
                        bugs_mes[nombre_friendly] = 0
                
                # Calcular total bugs
                bugs_mes['Total Bugs'] = total_bugs
                
                bugs_por_mes.append(bugs_mes)
            
            if bugs_por_mes:
                df_bugs_trend = pd.DataFrame(bugs_por_mes)
                df_bugs_trend.sort_values(by='Mes', inplace=True)
                
                # Verificar qué columnas tenemos realmente para el gráfico
                columnas_disponibles_grafico = ['Total Bugs']
                for nombre_friendly in bug_cols_disponibles.values():
                    if nombre_friendly in df_bugs_trend.columns:
                        columnas_disponibles_grafico.append(nombre_friendly)
                
                # Crear gráfico de tendencia con múltiples líneas - solo columnas disponibles
                df_bugs_melted = df_bugs_trend.melt(
                    id_vars=['Mes'], 
                    value_vars=columnas_disponibles_grafico,
                    var_name='Tipo de Bug', 
                    value_name='Cantidad'
                )
                
                # Definir colores específicos para cada tipo
                color_map = {
                    'Total Bugs': '#2E86AB',    # Azul oscuro para total
                    'Crítica': '#A23B72',       # Rojo oscuro para crítica
                    'Alta': '#F18F01',          # Naranja para alta
                    'Media': '#C73E1D',         # Rojo medio para media
                    'Baja': '#592E83'           # Morado para baja
                }
                
                fig_bugs_trend = px.line(
                    df_bugs_melted,
                    x='Mes',
                    y='Cantidad',
                    color='Tipo de Bug',
                    markers=True,
                    title=f"Tendencia histórica de bugs - {celula_seleccionada}",
                    color_discrete_map=color_map
                )
                
                # Personalizar el gráfico
                fig_bugs_trend.update_layout(
                    yaxis_title="Cantidad de Bugs",
                    xaxis_title="Mes",
                    legend_title="Tipo de Bug",
                    hovermode='x unified'
                )
                
                # Hacer la línea de Total Bugs más gruesa
                for trace in fig_bugs_trend.data:
                    if trace.name == 'Total Bugs':
                        trace.update(line=dict(width=4))
                    else:
                        trace.update(line=dict(width=2))
                
                st.plotly_chart(fig_bugs_trend, use_container_width=True)
                
                # Mostrar tabla de datos de la tendencia
                with st.expander("📊 Ver datos de la tendencia"):
                    # Formatear fechas para mejor visualización
                    df_bugs_display = df_bugs_trend.copy()
                    df_bugs_display['Mes'] = df_bugs_display['Mes'].dt.strftime('%Y-%m')
                    
                    st.dataframe(df_bugs_display, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos históricos suficientes para mostrar la tendencia de bugs.")
    else:
        st.info("No hay datos históricos disponibles para mostrar la tendencia de bugs.")

# Tendencias históricas - CORREGIDAS PARA MEJOR CONSISTENCIA
st.markdown("---")
st.title("📈 Tendencia de cumplimiento por célula y mes")

if not df_historico.empty and 'Mes' in df_historico.columns:
    # Asegurar formato de fecha consistente
    df_historico['Mes'] = pd.to_datetime(df_historico['Mes'], errors='coerce')
    df_historico = df_historico.dropna(subset=['Mes'])
    
    # Aplicar filtros históricos según configuración de métricas
    nombres_tendencias = {
        # 'security_rating': 'Seguridad',  # COMENTADO: No se necesita
        'reliability_rating': 'Confiabilidad',
        'sqale_rating': 'Mantenibilidad',
        'coverage': 'Cobertura',
        'complexity': 'Complejidad'
    }

    for metrica in metricas_seleccionadas:
        # Para complexity, usar duplicated_lines_density
        if metrica == 'complexity':
            if 'duplicated_lines_density' not in df_historico.columns:
                continue
            col_metrica = 'duplicated_lines_density'
        else:
            if metrica not in df_historico.columns:
                continue
            col_metrica = metrica

        usar_seleccionados = config_metricas.get(f"{metrica.split('_')[0]}_usar_seleccionados", False)
        if metrica == 'complexity':
            usar_seleccionados = config_metricas.get("complejidad_usar_seleccionados", False)

        cumplimiento_por_mes = []

        # Procesar cada mes disponible
        for mes_fecha in sorted(df_historico['Mes'].dt.to_period('M').unique()):
            df_mes = df_historico[df_historico['Mes'].dt.to_period('M') == mes_fecha]
            df_filtrado = filtrar_datos_por_metrica(df_mes, celula_seleccionada, seleccion_proyectos, usar_seleccionados)

            if df_filtrado.empty:
                continue

            # EXCLUIR proyectos con métricas vacías (MANTENER EXCEPCIONES)
            df_filtrado = df_filtrado.dropna(subset=[col_metrica])
            if df_filtrado.empty:
                continue

            if metrica == 'coverage':
                # Para tendencias usar configuración filtrada (NO todos los proyectos)
                df_filtrado = df_filtrado[~df_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)]
                if df_filtrado.empty:
                    continue
                valor = (df_filtrado['coverage'] >= cobertura_min).mean() * 100

            elif metrica == 'complexity':
                valor = df_filtrado['duplicated_lines_density'].isin(umbral_complejidad).mean() * 100

            # elif metrica == 'security_rating':  # COMENTADO: No se necesita
            #     valor = df_filtrado['security_rating'].isin(umbral_seguridad).mean() * 100

            elif metrica == 'reliability_rating':
                valor = df_filtrado['reliability_rating'].isin(umbral_confiabilidad).mean() * 100

            elif metrica == 'sqale_rating':
                valor = df_filtrado['sqale_rating'].isin(umbral_mantenibilidad).mean() * 100

            # APLICAR REDONDEO A TENDENCIAS
            valor = redondear_hacia_arriba(valor)

            cumplimiento_por_mes.append({
                'Mes': mes_fecha.to_timestamp(),
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

            # CORREGIR nombres de las metas
            meta_key = f"meta_{metrica.split('_')[0]}" if metrica != 'complexity' else "meta_complejidad"
            meta = metas.get(meta_key, None)
            if meta:
                fig_trend.add_hline(
                    y=meta, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"Meta: {meta}%"
                )

            # Configurar rango Y de 0 a 100
            fig_trend.update_layout(yaxis=dict(range=[0, 100]))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info(f"No hay datos históricos suficientes para mostrar tendencia de **{nombres_tendencias.get(metrica, metrica)}**.")
else:
    st.info("No hay datos históricos disponibles.")
