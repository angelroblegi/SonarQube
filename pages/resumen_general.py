import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

st.set_page_config(layout="wide", page_title="Resumen General")

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.error("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

# Archivos de configuración
ARCHIVO_PARAMETROS = "data/parametros_metricas.csv"
ARCHIVO_CONFIGURACION_NA = "data/configuracion_na.csv"
UPLOAD_DIR = "uploads"

@st.cache_data
def cargar_datos(path):
    """Cargar datos de métricas desde archivo Excel"""
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    
    # Columnas numéricas
    numeric_cols = ['coverage', 'bugs', 'bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor', 'bugs_info']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ratings como letras A-E
    rating_cols = ['security_rating', 'reliability_rating', 'sqale_rating', 'duplicated_lines_density']
    for col in rating_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            valid_ratings = ['A', 'B', 'C', 'D', 'E']
            df[col] = df[col].apply(lambda x: x if x in valid_ratings else None)
    
    return df

def obtener_ultimo_archivo():
    """Obtener el archivo de métricas más reciente"""
    archivos = glob.glob(os.path.join(UPLOAD_DIR, "metricas_*.xlsx"))
    if not archivos:
        return None
    archivos_ordenados = sorted(
        archivos,
        key=lambda x: datetime.strptime(os.path.basename(x).split("_")[1].replace(".xlsx", ""), "%Y-%m"),
        reverse=True
    )
    return archivos_ordenados[0]

def cargar_parametros():
    """Cargar parámetros de calidad"""
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

def cargar_configuracion_na():
    """Cargar configuración de componentes N/A"""
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

def calcular_cumplimiento(df, columna_metrica, umbral, es_rating=True, incluir_na=False):
    """Calcular cumplimiento de una métrica"""
    if df.empty:
        return 0, 0, 0.0
    
    if incluir_na:
        # Incluir todos los proyectos
        df_calc = df.copy()
        if es_rating:
            df_calc['cumple'] = df_calc[columna_metrica].isin(umbral)
            df_calc['cumple'] = df_calc['cumple'].fillna(False)
        else:
            df_calc['cumple'] = df_calc[columna_metrica] >= umbral
            df_calc['cumple'] = df_calc['cumple'].fillna(False)
    else:
        # Excluir proyectos con valores nulos
        df_calc = df.dropna(subset=[columna_metrica]).copy()
        if df_calc.empty:
            return 0, 0, 0.0
        
        if es_rating:
            df_calc['cumple'] = df_calc[columna_metrica].isin(umbral)
        else:
            df_calc['cumple'] = df_calc[columna_metrica] >= umbral
    
    total = len(df_calc)
    cumplen = df_calc['cumple'].sum()
    porcentaje = (cumplen / total * 100) if total > 0 else 0.0
    
    return int(cumplen), total, porcentaje

# ---------- Página principal ----------
st.title("📊 Resumen General de Cumplimiento")

# Cargar último archivo
ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

st.markdown(f"**📁 Archivo cargado:** {os.path.basename(ultimo_archivo)}")

# Cargar datos y configuración
df = cargar_datos(ultimo_archivo)
parametros = cargar_parametros()
config_na = cargar_configuracion_na()

# Filtrar para excluir célula "obsoleta" (case-insensitive)
df_filtrado = df[df['Celula'].str.lower() != 'obsoleta'].copy()

total_proyectos = len(df_filtrado)
st.info(f"📋 **Total de proyectos considerados (excluyendo 'Obsoleta'):** {total_proyectos}")

# Convertir parámetros a listas
umbral_seguridad = parametros["security_rating"].split(",")
umbral_confiabilidad = parametros["reliability_rating"].split(",")
umbral_mantenibilidad = parametros["sqale_rating"].split(",")
umbral_complejidad = parametros["duplicated_lines_density"].split(",")
cobertura_min = parametros["coverage_min"]

# Para cobertura, usar TODOS los proyectos (sin exclusiones)
df_cobertura = df_filtrado.copy()

# ---------- Calcular cumplimiento para cada métrica ----------
st.markdown("---")
st.header("🎯 Estadísticas de Cumplimiento por Métrica")

metricas = [
    ("🔐 Seguridad", "security_rating", umbral_seguridad, True, config_na["incluir_na_seguridad"], df_filtrado),
    ("🛡️ Confiabilidad", "reliability_rating", umbral_confiabilidad, True, config_na["incluir_na_confiabilidad"], df_filtrado),
    ("🧹 Mantenibilidad", "sqale_rating", umbral_mantenibilidad, True, config_na["incluir_na_mantenibilidad"], df_filtrado),
    ("🌀 Complejidad", "duplicated_lines_density", umbral_complejidad, True, config_na["incluir_na_complejidad"], df_filtrado),
    ("🧪 Cobertura de Pruebas Unitarias", "coverage", cobertura_min, False, config_na["incluir_na_cobertura"], df_cobertura)
]

# Mostrar en columnas
cols = st.columns(3)
for idx, (nombre, columna, umbral, es_rating, incluir_na, df_metrica) in enumerate(metricas):
    cumplen, total, porcentaje = calcular_cumplimiento(df_metrica, columna, umbral, es_rating, incluir_na)
    
    with cols[idx % 3]:
        st.metric(
            label=nombre,
            value=f"{cumplen} de {total}",
            delta=f"{porcentaje:.1f}%"
        )
        
        # Mostrar umbral
        if es_rating:
            umbral_str = ", ".join(umbral) if isinstance(umbral, list) else str(umbral)
            st.caption(f"Umbral: {umbral_str}")
        else:
            st.caption(f"Umbral: ≥ {umbral}%")

# ---------- Tabla de proyectos ----------
st.markdown("---")
st.header("📋 Lista de Proyectos Considerados")

# Preparar tabla para mostrar
df_mostrar = df_filtrado[['Celula', 'NombreProyecto', 'security_rating', 'reliability_rating', 
                          'sqale_rating', 'duplicated_lines_density', 'coverage']].copy()

# Renombrar columnas
df_mostrar.columns = ['Célula', 'Proyecto', 'Seguridad', 'Confiabilidad', 
                      'Mantenibilidad', 'Complejidad', 'Cobertura (%)']

# Ordenar por célula y proyecto
df_mostrar = df_mostrar.sort_values(['Célula', 'Proyecto'])

# Mostrar tabla
st.dataframe(
    df_mostrar.style.format({
        'Cobertura (%)': lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    }),
    use_container_width=True,
    height=400
)

# Resumen por célula
st.markdown("---")
st.header("📊 Resumen por Célula")

resumen_celulas = df_filtrado.groupby('Celula').agg({
    'NombreProyecto': 'count'
}).rename(columns={'NombreProyecto': 'Total Proyectos'})

st.dataframe(resumen_celulas, use_container_width=True)
