import streamlit as st
import pandas as pd
import io
import os
import glob
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import math

st.set_page_config(layout="wide", page_title="Dashboard SonarQube")

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.error("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"
ARCHIVO_PARAMETROS = "data/parametros_metricas.csv"
ARCHIVO_METAS = "data/metas_progreso.csv"
ARCHIVO_CONFIGURACION_METRICAS = "data/configuracion_metricas.csv"
ARCHIVO_CONFIGURACION_NA = "data/configuracion_na.csv"
UPLOAD_DIR = "uploads"

def redondear_hacia_arriba(valor):
    """Redondear hacia arriba cuando el decimal es .5 o mayor"""
    if pd.isna(valor):
        return valor
    # Para .5 exacto y valores mayores, redondear hacia arriba
    return int(valor + 0.5)

def crear_barra_progreso(actual, meta, color="blue"):
    """Crear una barra de progreso usando Plotly.
    Si el progreso es 0, mostrar una barra mínima visible y ubicar el texto por fuera para que no desaparezca.
    También mover el texto afuera cuando el porcentaje es muy bajo para mejorar la legibilidad.
    """
    progreso_real = min(actual / meta * 100, 100) if meta > 0 else 0
    progreso = progreso_real

    porcentaje_minimo_visible = 1  # Asegurar que no quede vacío visualmente
    mostrar_texto_fuera = False

    if progreso_real == 0:
        progreso = porcentaje_minimo_visible
        mostrar_texto_fuera = True
    elif progreso_real < 8:
        mostrar_texto_fuera = True

    posicion_texto = 'outside' if mostrar_texto_fuera else 'inside'
    color_texto = 'black' if mostrar_texto_fuera else 'white'

    fig = go.Figure(go.Bar(
        x=[progreso],
        y=[''],
        orientation='h',
        marker_color=color,
        text=f'{actual:.0f}% / {meta:.0f}%',
        textposition=posicion_texto,
        textfont=dict(color=color_texto, size=14)
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
    
    # Columnas numéricas
    numeric_cols = [
        'coverage', 'bugs', 'bugs_blocker', 'bugs_critical',
        'bugs_major', 'bugs_minor', 'bugs_info'
    ]
    
    # Convertir columnas numéricas, mantener NaN para valores faltantes (NO fillna(0))
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Manejar ratings como letras A-E, mantener NaN para valores faltantes
    rating_cols = ['security_rating', 'reliability_rating', 'sqale_rating', 'duplicated_lines_density']
    for col in rating_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            valid_ratings = ['A', 'B', 'C', 'D', 'E']
            # Convertir valores inválidos a NaN en lugar de 'E'
            df[col] = df[col].apply(lambda x: x if x in valid_ratings else None)
    
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
                "duplicated_lines_density": fila.get("duplicated_lines_density", "A,B,C,D,E"),
                "coverage_min": float(fila.get("coverage_min", 0))
            }
    return {
        "security_rating": "A,B,C,D,E", 
        "reliability_rating": "A,B,C,D,E",
        "sqale_rating": "A,B,C,D,E", 
        "duplicated_lines_density": "A,B,C,D,E",
        "coverage_min": 0
    }

def cargar_metas():
    """Cargar metas de progreso desde archivo CSV"""
    if os.path.exists(ARCHIVO_METAS):
        df_metas = pd.read_csv(ARCHIVO_METAS)
        if not df_metas.empty:
            fila = df_metas.iloc[0]
            return {
                "meta_seguridad": float(fila.get("meta_seguridad", 90)),
                "meta_confiabilidad": float(fila.get("meta_confiabilidad", 90)),
                "meta_mantenibilidad": float(fila.get("meta_mantenibilidad", 90)),
                "meta_cobertura": float(fila.get("meta_cobertura", 70)),  # Cambio: 70% por defecto
                "meta_complejidad": float(fila.get("meta_complejidad", 90))
            }
    return {
        "meta_seguridad": 90.0,  # Meta de progreso: 90%
        "meta_confiabilidad": 90.0,  # Meta de progreso: 90%
        "meta_mantenibilidad": 90.0,  # Meta de progreso: 90%
        "meta_cobertura": 70.0,  # Meta de cobertura: 70%
        "meta_complejidad": 90.0  # Meta de progreso: 90%
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

def cargar_configuracion_na():
    """Cargar configuración de componentes N/A (si incluirlos o excluirlos del cálculo)"""
    if os.path.exists(ARCHIVO_CONFIGURACION_NA):
        df_config = pd.read_csv(ARCHIVO_CONFIGURACION_NA)
        if not df_config.empty:
            fila = df_config.iloc[0]
            return {
                "incluir_na_seguridad": fila.get("incluir_na_seguridad", False),
                "incluir_na_confiabilidad": fila.get("incluir_na_confiabilidad", False),
                "incluir_na_mantenibilidad": fila.get("incluir_na_mantenibilidad", False),
                "incluir_na_cobertura": fila.get("incluir_na_cobertura", False),
                "incluir_na_complejidad": fila.get("incluir_na_complejidad", False)
            }
    return {
        "incluir_na_seguridad": False,
        "incluir_na_confiabilidad": False,
        "incluir_na_mantenibilidad": False,
        "incluir_na_cobertura": False,
        "incluir_na_complejidad": False
    }

def guardar_parametros(parametros):
    df = pd.DataFrame([parametros])
    df.to_csv(ARCHIVO_PARAMETROS, index=False)

def guardar_metas(metas):
    """Guardar metas de progreso en archivo CSV"""
    df = pd.DataFrame([metas])
    df.to_csv(ARCHIVO_METAS, index=False)

def guardar_configuracion_metricas(config):
    """Guardar configuración de métricas"""
    df = pd.DataFrame([config])
    df.to_csv(ARCHIVO_CONFIGURACION_METRICAS, index=False)

def guardar_configuracion_na(config):
    """Guardar configuración de componentes N/A"""
    df = pd.DataFrame([config])
    df.to_csv(ARCHIVO_CONFIGURACION_NA, index=False)

@st.cache_data
def convertir_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

proyectos_seleccionados = cargar_seleccion()
parametros = cargar_parametros()
metas = cargar_metas()
config_metricas = cargar_configuracion_metricas()
config_na = cargar_configuracion_na()

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
st.markdown(f"**📁 Archivo cargado:** {os.path.basename(archivo_mes_seleccionado)}")

df = cargar_datos(archivo_mes_seleccionado)

# Panel de parámetros
with st.expander("⚙️ Parámetros de calidad"):
    letras = ['A', 'B', 'C', 'D', 'E']
    col1, col2, col3, col4 = st.columns(4)
    umbral_seguridad = col1.multiselect("🔐 Seguridad", letras, default=parametros["security_rating"].split(","))
    umbral_confiabilidad = col2.multiselect("🛡️ Confiabilidad", letras, default=parametros["reliability_rating"].split(","))
    umbral_mantenibilidad = col3.multiselect("🧹 Mantenibilidad", letras, default=parametros["sqale_rating"].split(","))
    umbral_complejidad = col4.multiselect("🌀 Complejidad", letras, default=parametros["duplicated_lines_density"].split(","))

    col5, col6 = st.columns(2)
    cobertura_min = col5.slider("🧪 Cobertura mínima (%)", 0, 100, int(parametros["coverage_min"]))

    if st.button("💾 Guardar parámetros"):
        nuevos_parametros = {
            "security_rating": ",".join(umbral_seguridad),
            "reliability_rating": ",".join(umbral_confiabilidad),
            "sqale_rating": ",".join(umbral_mantenibilidad),
            "duplicated_lines_density": ",".join(umbral_complejidad),
            "coverage_min": cobertura_min
        }
        guardar_parametros(nuevos_parametros)
        st.success("✅ Parámetros guardados correctamente.")

# Panel de configuración de componentes N/A
with st.expander("🔧 Configuración de Componentes N/A"):
    st.markdown("**Selecciona si los componentes con valor 'N/A' deben ser incluidos o excluidos del cálculo:**")
    st.info("""
    **📋 Explicación:**
    - **Excluir N/A (recomendado)**: Solo cuenta proyectos que tienen datos válidos para la métrica
    - **Incluir N/A**: Cuenta todos los proyectos, considerando los N/A como "no cumplen"
    
    **Ejemplo**: Si hay 10 proyectos y 2 tienen N/A:
    - **Excluir N/A**: Cálculo sobre 8 proyectos
    - **Incluir N/A**: Cálculo sobre 10 proyectos (los 2 N/A cuentan como "no cumplen")
    """)
    
    col1, col2, col3 = st.columns(3)
    incluir_na_seguridad = col1.checkbox("🔐 Seguridad - Incluir N/A", value=config_na["incluir_na_seguridad"])
    incluir_na_confiabilidad = col2.checkbox("🛡️ Confiabilidad - Incluir N/A", value=config_na["incluir_na_confiabilidad"])
    incluir_na_mantenibilidad = col3.checkbox("🧹 Mantenibilidad - Incluir N/A", value=config_na["incluir_na_mantenibilidad"])
    
    col4, col5 = st.columns(2)
    incluir_na_cobertura = col4.checkbox("🧪 Cobertura - Incluir N/A", value=config_na["incluir_na_cobertura"])
    incluir_na_complejidad = col5.checkbox("🌀 Complejidad - Incluir N/A", value=config_na["incluir_na_complejidad"])
    
    if st.button("💾 Guardar configuración N/A"):
        nueva_config_na = {
            "incluir_na_seguridad": incluir_na_seguridad,
            "incluir_na_confiabilidad": incluir_na_confiabilidad,
            "incluir_na_mantenibilidad": incluir_na_mantenibilidad,
            "incluir_na_cobertura": incluir_na_cobertura,
            "incluir_na_complejidad": incluir_na_complejidad
        }
        guardar_configuracion_na(nueva_config_na)
        st.success("✅ Configuración de componentes N/A guardada correctamente.")
        st.rerun()

# Panel de configuración de métricas
with st.expander("📊 Configuración de Métricas por Tipo de Proyecto"):
    st.markdown("**Selecciona si cada métrica debe usar 'Proyectos Seleccionados' o 'Todos los Proyectos':**")
    
    col1, col2, col3 = st.columns(3)
    seguridad_seleccionados = col1.checkbox("🔐 Seguridad - Usar solo seleccionados", value=config_metricas["seguridad_usar_seleccionados"])
    confiabilidad_seleccionados = col2.checkbox("🛡️ Confiabilidad - Usar solo seleccionados", value=config_metricas["confiabilidad_usar_seleccionados"])
    mantenibilidad_seleccionados = col3.checkbox("🧹 Mantenibilidad - Usar solo seleccionados", value=config_metricas["mantenibilidad_usar_seleccionados"])
    
    col4, col5 = st.columns(2)
    cobertura_seleccionados = col4.checkbox("🧪 Cobertura - Usar solo seleccionados", value=config_metricas["cobertura_usar_seleccionados"])
    complejidad_seleccionados = col5.checkbox("🌀 Complejidad - Usar solo seleccionados", value=config_metricas["complejidad_usar_seleccionados"])
    
    if st.button("💾 Guardar configuración de métricas"):
        nueva_config = {
            "seguridad_usar_seleccionados": seguridad_seleccionados,
            "confiabilidad_usar_seleccionados": confiabilidad_seleccionados,
            "mantenibilidad_usar_seleccionados": mantenibilidad_seleccionados,
            "cobertura_usar_seleccionados": cobertura_seleccionados,
            "complejidad_usar_seleccionados": complejidad_seleccionados
        }
        guardar_configuracion_metricas(nueva_config)
        st.success("✅ Configuración de métricas guardada correctamente.")

# Panel de metas de progreso - CAMBIO EN LOS VALORES POR DEFECTO
with st.expander("🎯 Configurar Metas de Progreso"):
    st.markdown("**Define el % de proyectos que deben cumplir cada métrica:**")
    
    col1, col2, col3 = st.columns(3)
    meta_seguridad = col1.slider("🔐 Seguridad (%)", 0, 100, int(metas["meta_seguridad"]))
    meta_confiabilidad = col2.slider("🛡️ Calidad del Código (%)", 0, 100, int(metas["meta_confiabilidad"]))
    meta_mantenibilidad = col3.slider("🧹 Eficiencia de Mantenibilidad (%)", 0, 100, int(metas["meta_mantenibilidad"]))
    
    col4, col5 = st.columns(2)
    meta_cobertura = col4.slider("🧪 Cobertura de pruebas unitarias (%)", 0, 100, int(metas["meta_cobertura"]))
    meta_complejidad = col5.slider("🌀 Complejidad Reducida (%)", 0, 100, int(metas["meta_complejidad"]))
    
    if st.button("💾 Guardar metas"):
        nuevas_metas = {
            "meta_seguridad": meta_seguridad,
            "meta_confiabilidad": meta_confiabilidad,
            "meta_mantenibilidad": meta_mantenibilidad,
            "meta_cobertura": meta_cobertura,
            "meta_complejidad": meta_complejidad
        }
        guardar_metas(nuevas_metas)
        st.success("✅ Metas guardadas correctamente.")

# Función para filtrar datos según configuración de métrica
def filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, usar_seleccionados):
    if usar_seleccionados:
        # Usar solo proyectos seleccionados
        dfs_filtrados = []
        for celula, proyectos in proyectos_seleccionados.items():
            if proyectos and celula in celulas_seleccionadas:
                df_filtrado = df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos))]
                dfs_filtrados.append(df_filtrado)
        return pd.concat(dfs_filtrados, ignore_index=True) if dfs_filtrados else pd.DataFrame()
    else:
        # Usar todos los proyectos de las células seleccionadas
        return df[df['Celula'].isin(celulas_seleccionadas)].copy()

# Obtener células seleccionadas
celulas_seleccionadas = list(proyectos_seleccionados.keys())

# Filtrar datos según configuración para cada métrica
df_seguridad = filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, seguridad_seleccionados)
df_confiabilidad = filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, confiabilidad_seleccionados)
df_mantenibilidad = filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, mantenibilidad_seleccionados)
df_cobertura = filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, cobertura_seleccionados)
df_complejidad = filtrar_datos_por_metrica(df, celulas_seleccionadas, proyectos_seleccionados, complejidad_seleccionados)

# Proyectos a excluir para coverage
proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

# Calcular cumplimiento para cada métrica considerando configuración de N/A
def calcular_cumplimiento_con_na(df, columna_metrica, umbral, es_rating=True, incluir_na=False):
    """Calcular cumplimiento considerando configuración de componentes N/A"""
    if df.empty:
        return pd.Series(dtype=float)
    
    if incluir_na:
        # Incluir todos los proyectos, considerando N/A como "no cumplen"
        df_calc = df.copy()
        
        if es_rating:
            # Para ratings (A-E), N/A se considera como "no cumple"
            df_calc['cumple'] = df_calc[columna_metrica].isin(umbral)
            # Los valores NaN se consideran como False (no cumplen)
            df_calc['cumple'] = df_calc['cumple'].fillna(False)
        else:
            # Para valores numéricos (coverage), N/A se considera como "no cumple"
            df_calc['cumple'] = df_calc[columna_metrica] >= umbral
            # Los valores NaN se consideran como False (no cumplen)
            df_calc['cumple'] = df_calc['cumple'].fillna(False)
    else:
        # Excluir proyectos con valores nulos/vacíos en la métrica (comportamiento original)
        df_calc = df.dropna(subset=[columna_metrica]).copy()
        
        if df_calc.empty:
            return pd.Series(dtype=float)
        
        if es_rating:
            # Para ratings (A-E)
            df_calc['cumple'] = df_calc[columna_metrica].isin(umbral)
        else:
            # Para valores numéricos (coverage)
            df_calc['cumple'] = df_calc[columna_metrica] >= umbral
    
    return df_calc.groupby('Celula')['cumple'].mean()

# Calcular cumplimiento para cada métrica usando configuración de N/A
agrupado_seguridad = calcular_cumplimiento_con_na(df_seguridad, 'security_rating', umbral_seguridad, True, config_na["incluir_na_seguridad"])
agrupado_confiabilidad = calcular_cumplimiento_con_na(df_confiabilidad, 'reliability_rating', umbral_confiabilidad, True, config_na["incluir_na_confiabilidad"])
agrupado_mantenibilidad = calcular_cumplimiento_con_na(df_mantenibilidad, 'sqale_rating', umbral_mantenibilidad, True, config_na["incluir_na_mantenibilidad"])

# Para cobertura, excluir proyectos específicos además de considerar configuración N/A
if not df_cobertura.empty:
    df_cobertura_filtrado = df_cobertura[~df_cobertura['NombreProyecto'].isin(proyectos_excluir_coverage)]
    agrupado_cobertura = calcular_cumplimiento_con_na(df_cobertura_filtrado, 'coverage', cobertura_min, False, config_na["incluir_na_cobertura"])
else:
    agrupado_cobertura = pd.Series(dtype=float)

agrupado_complejidad = calcular_cumplimiento_con_na(df_complejidad, 'duplicated_lines_density', umbral_complejidad, True, config_na["incluir_na_complejidad"])

# Usar df completo para bugs (todos los proyectos de células seleccionadas)
df_todas_metricas = df[df['Celula'].isin(celulas_seleccionadas)].copy()
agrupado_bugs = df_todas_metricas.groupby('Celula').agg({
    'bugs': 'sum',
    'bugs_blocker': 'sum',
    'bugs_critical': 'sum',
    'bugs_major': 'sum',
    'bugs_minor': 'sum'
}).fillna(0)

# Combinar todos los agrupados
todas_las_celulas = set(celulas_seleccionadas)
agrupado_final = pd.DataFrame(index=sorted(todas_las_celulas))

# Agregar métricas una por una
for serie, nombre in [
    (agrupado_seguridad, 'cumple_seguridad'),
    (agrupado_confiabilidad, 'cumple_confiabilidad'),
    (agrupado_mantenibilidad, 'cumple_mantenibilidad'),
    (agrupado_cobertura, 'cumple_cobertura'),
    (agrupado_complejidad, 'cumple_complejidad')
]:
    if not serie.empty:
        agrupado_final = agrupado_final.join(serie.rename(nombre), how='left')
    else:
        agrupado_final[nombre] = 0

# Agregar bugs
agrupado_final = agrupado_final.join(agrupado_bugs, how='left')

# Llenar valores NaN con 0
agrupado_final = agrupado_final.fillna(0)

# Convertir a porcentajes las métricas de cumplimiento
agrupado_final[['cumple_seguridad', 'cumple_confiabilidad', 'cumple_mantenibilidad',
                'cumple_cobertura', 'cumple_complejidad']] *= 100

# Aplicar redondeo hacia arriba para .5 o mayor
for col in ['cumple_seguridad', 'cumple_confiabilidad', 'cumple_mantenibilidad',
            'cumple_cobertura', 'cumple_complejidad']:
    agrupado_final[col] = agrupado_final[col].apply(redondear_hacia_arriba)

agrupado_final = agrupado_final.reset_index()

# Renombrar columnas - CAMBIO: 'Bugs' por 'Total Bugs'
agrupado_final.columns = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Cobertura de pruebas unitarias', 'Complejidad', 'Total Bugs', 'Crítica',
    'Alta', 'Media', 'Baja'
]

# Reordenar columnas
cols_reordenadas = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Cobertura de pruebas unitarias', 'Complejidad',
    'Total Bugs', 'Crítica', 'Alta', 'Media', 'Baja'
]
agrupado = agrupado_final[cols_reordenadas]

# Nueva sección: Tabla de Progreso hacia Metas
st.markdown("---")
st.header("🎯 Progreso hacia Metas por Célula")

# Crear tabla de progreso
progreso_data = []
colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

for idx, (_, fila) in enumerate(agrupado.iterrows()):
    celula = fila['Célula']
    
    # Calcular progreso para cada métrica (incluir todas las 5)
    metricas_progreso = [
        #('Seguridad', fila['Seguridad'], meta_seguridad, colores[0]),
        ('Confiabilidad', fila['Confiabilidad'], meta_confiabilidad, colores[1]),
        ('Mantenibilidad', fila['Mantenibilidad'], meta_mantenibilidad, colores[2]),
        ('Cobertura', fila['Cobertura de pruebas unitarias'], meta_cobertura, colores[3]),
        ('Complejidad', fila['Complejidad'], meta_complejidad, colores[4])
    ]
    
    progreso_data.append({
        'Célula': celula,
        'Métricas': metricas_progreso
    })

# Mostrar tabla de progreso
for celula_data in progreso_data:
    st.subheader(f"📊 {celula_data['Célula']}")
    
    # Crear columnas para cada métrica
    cols = st.columns(4)  # Cambio: 4 columnas porque quitamos Seguridad
    
    for i, (nombre, actual, meta, color) in enumerate(celula_data['Métricas']):
        with cols[i]:
            st.markdown(f"**{nombre}**")
            
            # Crear barra de progreso
            fig_progress = crear_barra_progreso(actual, meta, color)
            st.plotly_chart(fig_progress, use_container_width=True, config={'displayModeBar': False}, 
                          key=f"progress_{celula_data['Célula']}_{nombre}")
            
            # Mostrar estado
            if actual >= meta:
                st.success(f"✅ Meta alcanzada")
            else:
                faltante = meta - actual
                st.warning(f"⚠️ Falta {faltante:.0f}%")

# Resumen general de progreso
st.markdown("---")
st.subheader("📈 Resumen General de Progreso")

# Calcular promedio general por métrica
promedios = {
    'Seguridad': redondear_hacia_arriba(agrupado['Seguridad'].mean()),
    'Confiabilidad': redondear_hacia_arriba(agrupado['Confiabilidad'].mean()),
    'Mantenibilidad': redondear_hacia_arriba(agrupado['Mantenibilidad'].mean()),
    'Cobertura': redondear_hacia_arriba(agrupado['Cobertura de pruebas unitarias'].mean()),
    'Complejidad': redondear_hacia_arriba(agrupado['Complejidad'].mean())
}

# Calcular promedio general de cobertura considerando configuración de N/A
def calcular_promedio_cobertura_general():
    """Calcular el promedio de cobertura considerando configuración de componentes N/A"""
    # Usar df completo para obtener todos los proyectos
    df_todos_proyectos = df[df['Celula'].isin(celulas_seleccionadas)].copy()
    
    # Excluir proyectos específicos de cobertura
    df_todos_proyectos = df_todos_proyectos[~df_todos_proyectos['NombreProyecto'].isin(proyectos_excluir_coverage)]
    
    if config_na["incluir_na_cobertura"]:
        # Incluir todos los proyectos, considerando N/A como 0%
        df_cobertura_calc = df_todos_proyectos.copy()
        df_cobertura_calc['coverage'] = df_cobertura_calc['coverage'].fillna(0)
    else:
        # Excluir proyectos sin datos de cobertura (comportamiento original)
        df_cobertura_calc = df_todos_proyectos.dropna(subset=['coverage'])
    
    if not df_cobertura_calc.empty:
        promedio_cobertura_general = df_cobertura_calc['coverage'].mean()
        return redondear_hacia_arriba(promedio_cobertura_general)
    else:
        return 0

promedio_cobertura_general = calcular_promedio_cobertura_general()

metas_dict = {
    'Seguridad': meta_seguridad,
    'Confiabilidad': meta_confiabilidad,
    'Mantenibilidad': meta_mantenibilidad,
    'Cobertura': meta_cobertura,
    'Complejidad': meta_complejidad
}

# Mostrar resumen en columnas
cols_resumen = st.columns(5)
for i, (metrica, promedio) in enumerate(promedios.items()):
    with cols_resumen[i]:
        meta_actual = metas_dict[metrica]
        
        st.metric(
            label=f"{metrica}",
            value=f"{promedio:.0f}%",
            delta=f"{promedio - meta_actual:.0f}%" if promedio >= meta_actual else f"-{meta_actual - promedio:.0f}%"
        )
        
        # Barra de progreso pequeña
        fig_small = crear_barra_progreso(promedio, meta_actual, colores[i])
        st.plotly_chart(fig_small, use_container_width=True, config={'displayModeBar': False},
                       key=f"resumen_{metrica}")

# Mostrar promedio general de cobertura
st.markdown("---")
st.subheader("📊 Promedio General de Cobertura de Pruebas Unitarias")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Promedio General de Cobertura",
        value=f"{promedio_cobertura_general:.0f}%",
        delta=""
    )

with col2:
    # Mostrar cantidad de proyectos considerados según configuración N/A
    df_todos_proyectos = df[df['Celula'].isin(celulas_seleccionadas)].copy()
    df_todos_proyectos = df_todos_proyectos[~df_todos_proyectos['NombreProyecto'].isin(proyectos_excluir_coverage)]
    
    if config_na["incluir_na_cobertura"]:
        # Incluir todos los proyectos
        total_proyectos_cobertura = len(df_todos_proyectos)
        label_cobertura = "Proyectos considerados (incluyendo N/A)"
    else:
        # Solo proyectos con datos válidos
        df_cobertura_valida = df_todos_proyectos.dropna(subset=['coverage'])
        total_proyectos_cobertura = len(df_cobertura_valida)
        label_cobertura = "Proyectos con datos de cobertura"
    
    st.metric(
        label=label_cobertura,
        value=f"{total_proyectos_cobertura}",
        delta=""
    )

with col3:
    # Mostrar cantidad total de proyectos
    total_proyectos = len(df[df['Celula'].isin(celulas_seleccionadas)])
    st.metric(
        label="Total de proyectos",
        value=f"{total_proyectos}",
        delta=""
    )

# Crear barra de progreso para el promedio general de cobertura
fig_promedio_cobertura = crear_barra_progreso(promedio_cobertura_general, 100, '#d62728')
st.plotly_chart(fig_promedio_cobertura, use_container_width=True, config={'displayModeBar': False},
               key="promedio_cobertura_general")

st.subheader("📋 Tabla de Cumplimiento por Célula")
st.dataframe(
    agrupado.style.background_gradient(
        cmap="BuGn",
        subset=['Seguridad', 'Confiabilidad', 'Mantenibilidad',
                'Cobertura de pruebas unitarias', 'Complejidad'],
        vmin=0, vmax=100
    ).format({
        'Seguridad': "{:.0f}%", 'Confiabilidad': "{:.0f}%", 'Mantenibilidad': "{:.0f}%",
        'Cobertura de pruebas unitarias': "{:.0f}%", 'Complejidad': "{:.0f}%",
        'Total Bugs': "{:.0f}", 'Crítica': "{:.0f}", 'Alta': "{:.0f}", 'Media': "{:.0f}", 'Baja': "{:.0f}"
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
        'Total Bugs', 'Crítica', 'Alta', 'Media', 'Baja'  # CORREGIDO: cambié 'Bugs' por 'Total Bugs'
    ], var_name='Tipo de Bug', value_name='Cantidad'),
    x='Célula', y='Cantidad', color='Tipo de Bug',
    category_orders={'Tipo de Bug': ['Crítica', 'Alta', 'Media', 'Baja', 'Total Bugs']},
    barmode='group', title='Bugs por Célula'
)
st.plotly_chart(fig_bugs, use_container_width=True)

# Tendencia mensual - CORREGIDO para mejor consistencia
st.markdown("---")
st.header("📈 Tendencia de Cumplimiento por Célula y Métrica")

# Cargar todos los meses
lista_df = []
archivos_todos_ordenados = sorted(archivos_todos, 
    key=lambda x: datetime.strptime(os.path.basename(x).split("_")[1].replace(".xlsx", ""), "%Y-%m"))

for archivo in archivos_todos_ordenados:
    try:
        df_mes = cargar_datos(archivo)
        if not df_mes.empty:
            lista_df.append(df_mes)
    except Exception as e:
        st.warning(f"Error cargando {archivo}: {e}")
        continue

if lista_df:
    df_todos = pd.concat(lista_df, ignore_index=True)
    
    # Asegurar formato de fecha consistente
    if 'Mes' in df_todos.columns:
        df_todos['Mes'] = pd.to_datetime(df_todos['Mes'], errors='coerce')
        
        # Eliminar filas con fechas inválidas
        df_todos = df_todos.dropna(subset=['Mes'])
        
        # Definir tendencias con parámetros actuales
        tendencias = [
            ("Seguridad", "cumple_seguridad", 'security_rating', umbral_seguridad, seguridad_seleccionados, True),
            ("Confiabilidad", "cumple_confiabilidad", 'reliability_rating', umbral_confiabilidad, confiabilidad_seleccionados, True),
            ("Mantenibilidad", "cumple_mantenibilidad", 'sqale_rating', umbral_mantenibilidad, mantenibilidad_seleccionados, True),
            ("Cobertura", "cumple_cobertura", 'coverage', cobertura_min, cobertura_seleccionados, False),
            ("Complejidad", "cumple_complejidad", 'duplicated_lines_density', umbral_complejidad, complejidad_seleccionados, True)
        ]

        for nombre, col_cumple, col_metrica, umbral, usar_sel, es_rating in tendencias:
            st.subheader(f"📊 {nombre}")
            
            # Información de depuración desactivada
            # if nombre == "Cobertura":
            #     st.info(f"🔍 **Depuración Cobertura:** Usando proyectos seleccionados: {usar_sel}")
            #     if usar_sel:
            #         proyectos_cobertura = []
            #         for celula, proyectos in proyectos_seleccionados.items():
            #             if proyectos and celula in celulas_seleccionadas:
            #                 proyectos_cobertura.extend([f"{celula}: {p}" for p in proyectos])
            #         if proyectos_cobertura:
            #             st.info(f"📋 **Proyectos seleccionados para cobertura:** {', '.join(proyectos_cobertura[:5])}{'...' if len(proyectos_cobertura) > 5 else ''}")
            
            # Lista para almacenar datos de tendencia
            datos_tendencia = []
            
            # Procesar cada mes disponible
            for mes_fecha in sorted(df_todos['Mes'].dt.to_period('M').unique()):
                # Filtrar datos del mes específico
                df_mes = df_todos[df_todos['Mes'].dt.to_period('M') == mes_fecha].copy()
                
                if df_mes.empty:
                    continue
                
                # Aplicar filtrado según configuración de métrica
                df_fil = filtrar_datos_por_metrica(df_mes, celulas_seleccionadas, proyectos_seleccionados, usar_sel)
                
                # Aplicar exclusiones específicas para cobertura
                if nombre == "Cobertura" and not df_fil.empty:
                    df_fil = df_fil[~df_fil['NombreProyecto'].isin(proyectos_excluir_coverage)]
                
                # Aplicar configuración de componentes N/A
                config_na_key = f"incluir_na_{nombre.lower()}"
                incluir_na = config_na.get(config_na_key, False)
                
                if incluir_na:
                    # Incluir todos los proyectos, considerando N/A como "no cumplen"
                    if es_rating:
                        df_fil[col_cumple] = df_fil[col_metrica].isin(umbral)
                        df_fil[col_cumple] = df_fil[col_cumple].fillna(False)
                    else:
                        df_fil[col_cumple] = df_fil[col_metrica] >= umbral
                        df_fil[col_cumple] = df_fil[col_cumple].fillna(False)
                else:
                    # Excluir proyectos con métricas vacías (comportamiento original)
                    if col_metrica in df_fil.columns:
                        df_fil = df_fil.dropna(subset=[col_metrica])
                    
                    if df_fil.empty:
                        continue
                    
                    # Calcular cumplimiento
                    if es_rating:
                        df_fil[col_cumple] = df_fil[col_metrica].isin(umbral)
                    else:
                        df_fil[col_cumple] = df_fil[col_metrica] >= umbral
                
                # Agrupar por célula
                cumplimiento_mes = df_fil.groupby('Celula')[col_cumple].mean().reset_index()
                cumplimiento_mes['Mes'] = mes_fecha.to_timestamp()
                cumplimiento_mes[nombre] = cumplimiento_mes[col_cumple] * 100
                # Aplicar redondeo hacia arriba en tendencias también
                cumplimiento_mes[nombre] = cumplimiento_mes[nombre].apply(redondear_hacia_arriba)
                cumplimiento_mes = cumplimiento_mes[['Mes', 'Celula', nombre]]
                
                datos_tendencia.append(cumplimiento_mes)
            
            # Crear gráfico de tendencia si hay datos
            if datos_tendencia:
                df_trend = pd.concat(datos_tendencia, ignore_index=True)
                
                # Asegurar que todas las células estén representadas en todos los meses
                meses_unicos = df_trend['Mes'].unique()
                celulas_unicas = df_trend['Celula'].unique()
                
                # Crear combinaciones completas de mes-célula
                from itertools import product
                combinaciones = list(product(meses_unicos, celulas_unicas))
                df_completo = pd.DataFrame(combinaciones, columns=['Mes', 'Celula'])
                
                # Merge con datos reales
                df_trend_final = df_completo.merge(df_trend, on=['Mes', 'Celula'], how='left')
                
                # Crear gráfico
                fig_trend = px.line(
                    df_trend_final,
                    x='Mes', y=nombre, color='Celula',
                    markers=True,
                    title=f"Tendencia mensual de {nombre} (%)",
                    labels={nombre: f"{nombre} (%)"}
                )
                
                # Agregar línea de meta
                meta_actual = metas_dict.get(nombre, 70)
                fig_trend.add_hline(
                    y=meta_actual, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"Meta: {meta_actual}%"
                )
                
                # Configurar rango Y de 0 a 100
                fig_trend.update_layout(yaxis=dict(range=[0, 100]))
                
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info(f"No hay datos suficientes para mostrar la tendencia de {nombre}")

else:
    st.warning("⚠️ No se encontraron archivos válidos para mostrar tendencias.")
