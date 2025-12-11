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
ARCHIVO_CONFIGURACION_NA = "data/configuracion_na.csv"
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
    """Crear una barra de progreso usando Plotly.
    Si el progreso es 0, mostrar una barra mínima visible y ubicar el texto por fuera.
    También mover el texto afuera cuando el porcentaje es muy bajo para mejorar la legibilidad.
    """
    progreso_real = min(actual / meta * 100, 100) if meta > 0 else 0
    progreso = progreso_real

    porcentaje_minimo_visible = 1
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

ultimo_archivo = obtener_ultimo_archivo()
if ultimo_archivo is None:
    st.warning("⚠️ No se encontró ningún archivo de métricas en la carpeta uploads.")
    st.stop()

df_ultimo = cargar_datos(ultimo_archivo)
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()
config_metricas = cargar_configuracion_metricas()
config_na = cargar_configuracion_na()
metas = cargar_metas()
metricas_seleccionadas = cargar_metricas_seleccionadas()

# Configuración de filtros
st.title("🔎 Detalle de Métricas por Célula")

celulas = df_ultimo['Celula'].unique()
# Filtrar para ocultar 'nan' y 'obsoleta'
celulas_filtradas = [celula for celula in celulas if celula not in ['nan', 'obsoleta'] and pd.notna(celula)]
celula_seleccionada = st.selectbox("Selecciona la célula para mostrar sus proyectos", options=celulas_filtradas)
# === Selección de mes para ver datos históricos ===
meses_disponibles = sorted(df_historico[df_historico['Celula'] == celula_seleccionada]['Mes'].dt.strftime('%Y-%m').unique(), reverse=True)
mes_seleccionado = None  # Inicializar variable
if meses_disponibles:
    mes_seleccionado = st.selectbox("Selecciona el mes a visualizar", options=meses_disponibles)
    # Filtrar el dataframe del mes seleccionado
    df_mes_seleccionado = df_historico[
        (df_historico['Celula'] == celula_seleccionada) &
        (df_historico['Mes'].dt.strftime('%Y-%m') == mes_seleccionado)
    ].copy()
    # Si hay datos para el mes, usarlos en vez de df_ultimo
    if not df_mes_seleccionado.empty:
        df_ultimo = df_mes_seleccionado
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
    # Para cobertura usar la configuración: si está seleccionado, usar proyectos seleccionados; si no, usar todos
    if config_metricas["cobertura_usar_seleccionados"] and celula_seleccionada in seleccion_proyectos and seleccion_proyectos[celula_seleccionada]:
        # Usar proyectos seleccionados aunque no tengan datos de cobertura
        proyectos_para_mostrar.update(seleccion_proyectos[celula_seleccionada])
    else:
        # Usar todos los proyectos de la célula que tengan datos de cobertura
        df_todos_cobertura = df_ultimo[df_ultimo['Celula'] == celula_seleccionada]
        proyectos_para_mostrar.update(df_todos_cobertura.dropna(subset=['coverage'])['NombreProyecto'].tolist())
if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    # EXCLUIR proyectos con métricas vacías
    proyectos_para_mostrar.update(df_complejidad.dropna(subset=['complexity'])['NombreProyecto'].tolist())

# Si no hay proyectos con métricas, verificar si hay proyectos con bugs
if not proyectos_para_mostrar:
    # Obtener todos los proyectos de la célula que tengan datos de bugs
    df_todos_celula = df_ultimo[df_ultimo['Celula'] == celula_seleccionada]
    bug_cols = ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
    proyectos_con_bugs = set()
    
    for col in bug_cols:
        if col in df_todos_celula.columns:
            # Incluir proyectos que tengan bugs (valores > 0 o no NaN)
            proyectos_con_valores = df_todos_celula[
                (df_todos_celula[col].notna()) & (df_todos_celula[col] > 0)
            ]['NombreProyecto'].tolist()
            proyectos_con_bugs.update(proyectos_con_valores)
    
    if proyectos_con_bugs:
        proyectos_para_mostrar = proyectos_con_bugs
    else:
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

# === NUEVA SECCIÓN: OKR CUMPLIMIENTO ===
st.markdown("---")
st.header(f"📊 OKR Cumplimiento - {celula_seleccionada}")

def calcular_okr_cumplimiento(df_celula, df_cobertura, config_metricas, config_na, metas, parametros, proyectos_excluir_coverage):
    """Calcular el cumplimiento OKR para cada métrica considerando metas configuradas y configuración N/A"""
    okr_data = []
    
    # Conteo de componentes totales por métrica
    total_componentes = {}
    componentes_cumplen = {}
    
    # Confiabilidad
    if 'reliability_rating' in df_celula.columns:
        if config_na.get("incluir_na_confiabilidad", False):
            # Incluir todos los proyectos, considerando N/A como "no cumplen"
            df_confiabilidad = df_celula.copy()
            umbral_confiabilidad = parametros["reliability_rating"].split(",")
            df_confiabilidad['cumple'] = df_confiabilidad['reliability_rating'].isin(umbral_confiabilidad)
            df_confiabilidad['cumple'] = df_confiabilidad['cumple'].fillna(False)
        else:
            # Excluir proyectos con N/A
            df_confiabilidad = df_celula.dropna(subset=['reliability_rating'])
            umbral_confiabilidad = parametros["reliability_rating"].split(",")
            df_confiabilidad['cumple'] = df_confiabilidad['reliability_rating'].isin(umbral_confiabilidad)
        
        if not df_confiabilidad.empty:
            total_componentes['Confiabilidad'] = len(df_confiabilidad)
            componentes_cumplen['Confiabilidad'] = len(df_confiabilidad[df_confiabilidad['cumple']])
    
    # Mantenibilidad
    if 'sqale_rating' in df_celula.columns:
        if config_na.get("incluir_na_mantenibilidad", False):
            # Incluir todos los proyectos, considerando N/A como "no cumplen"
            df_mantenibilidad = df_celula.copy()
            umbral_mantenibilidad = parametros["sqale_rating"].split(",")
            df_mantenibilidad['cumple'] = df_mantenibilidad['sqale_rating'].isin(umbral_mantenibilidad)
            df_mantenibilidad['cumple'] = df_mantenibilidad['cumple'].fillna(False)
        else:
            # Excluir proyectos con N/A
            df_mantenibilidad = df_celula.dropna(subset=['sqale_rating'])
            umbral_mantenibilidad = parametros["sqale_rating"].split(",")
            df_mantenibilidad['cumple'] = df_mantenibilidad['sqale_rating'].isin(umbral_mantenibilidad)
        
        if not df_mantenibilidad.empty:
            total_componentes['Mantenibilidad'] = len(df_mantenibilidad)
            componentes_cumplen['Mantenibilidad'] = len(df_mantenibilidad[df_mantenibilidad['cumple']])
    
    # Complejidad
    if 'complexity' in df_celula.columns:
        if config_na.get("incluir_na_complejidad", False):
            # Incluir todos los proyectos, considerando N/A como "no cumplen"
            df_complejidad = df_celula.copy()
            umbral_complejidad = parametros["duplicated_lines_density"].split(",")
            df_complejidad['cumple'] = df_complejidad['complexity'].isin(umbral_complejidad)
            df_complejidad['cumple'] = df_complejidad['cumple'].fillna(False)
        else:
            # Excluir proyectos con N/A
            df_complejidad = df_celula.dropna(subset=['complexity'])
            umbral_complejidad = parametros["duplicated_lines_density"].split(",")
            df_complejidad['cumple'] = df_complejidad['complexity'].isin(umbral_complejidad)
        
        if not df_complejidad.empty:
            total_componentes['Complejidad'] = len(df_complejidad)
            componentes_cumplen['Complejidad'] = len(df_complejidad[df_complejidad['cumple']])
    
    # Cobertura - usar configuración específica
    if 'coverage' in df_celula.columns:
        if config_metricas.get("cobertura_usar_seleccionados", False):
            # Usar proyectos seleccionados para cobertura
            df_cobertura_calc = df_cobertura.copy()
        else:
            # Usar todos los proyectos
            df_cobertura_calc = df_celula.copy()
        
        # Excluir proyectos específicos
        df_cobertura_calc = df_cobertura_calc[~df_cobertura_calc['NombreProyecto'].isin(proyectos_excluir_coverage)]
        
        if config_na.get("incluir_na_cobertura", False):
            # Incluir todos los proyectos, considerando N/A como "no cumplen"
            df_cobertura_calc['cumple'] = df_cobertura_calc['coverage'] >= parametros["coverage_min"]
            df_cobertura_calc['cumple'] = df_cobertura_calc['cumple'].fillna(False)
        else:
            # Excluir proyectos con N/A
            df_cobertura_calc = df_cobertura_calc.dropna(subset=['coverage'])
            df_cobertura_calc['cumple'] = df_cobertura_calc['coverage'] >= parametros["coverage_min"]
        
        if not df_cobertura_calc.empty:
            total_componentes['Cobertura'] = len(df_cobertura_calc)
            componentes_cumplen['Cobertura'] = len(df_cobertura_calc[df_cobertura_calc['cumple']])
    
    # Calcular porcentajes de cumplimiento OKR
    for metrica in ['Confiabilidad', 'Mantenibilidad', 'Complejidad', 'Cobertura']:
        if metrica in total_componentes and metrica in componentes_cumplen:
            total = total_componentes[metrica]
            cumplen = componentes_cumplen[metrica]
            
            # Obtener meta configurada
            meta_key = f"meta_{metrica.lower()}"
            meta_configurada = metas.get(meta_key, 90)
            
            # Calcular componentes objetivo según meta
            componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
            
            # Calcular cumplimiento OKR (porcentaje respecto a la meta)
            if componentes_objetivo > 0:
                cumplimiento_okr = (cumplen / componentes_objetivo) * 100
            else:
                cumplimiento_okr = 100 if cumplen == 0 else 0
            
            # Redondear hacia arriba
            cumplimiento_okr = redondear_hacia_arriba(cumplimiento_okr)
            
            okr_data.append({
                'Métrica': metrica,
                'Total Componentes': total,
                'Meta Configurada (%)': meta_configurada,
                'Componentes Objetivo': componentes_objetivo,
                'Componentes Cumplen': cumplen,
                'Cumplimiento OKR (%)': cumplimiento_okr,
                'Estado': '✅ Cumple' if cumplimiento_okr >= 100 else '⚠️ No cumple'
            })
    
    return okr_data

# Calcular OKR para la célula seleccionada
okr_data = calcular_okr_cumplimiento(df_celula, df_cobertura, config_metricas, config_na, metas, parametros, proyectos_excluir_coverage)

if okr_data:
    # Crear DataFrame para mostrar
    df_okr = pd.DataFrame(okr_data)
    
    # Mostrar tabla OKR
    st.subheader("📈 Tabla de Cumplimiento OKR")
    
    # Formatear la tabla
    df_okr_display = df_okr.copy()
    df_okr_display['Meta Configurada (%)'] = df_okr_display['Meta Configurada (%)'].apply(lambda x: f"{x:.0f}%")
    df_okr_display['Cumplimiento OKR (%)'] = df_okr_display['Cumplimiento OKR (%)'].apply(lambda x: f"{x:.0f}%")
    
    # Función para resaltar filas según estado
    def resaltar_okr(row):
        if row['Estado'] == '✅ Cumple':
            return ['background-color: #d4edda; color: #155724'] * len(row)
        else:
            return ['background-color: #f8d7da; color: #721c24'] * len(row)
    
    df_okr_styled = df_okr_display.style.apply(resaltar_okr, axis=1)
    st.dataframe(df_okr_styled, use_container_width=True, hide_index=True)
    
    # Explicación del cálculo
    st.info("""
    **📋 Explicación del cálculo OKR:**
    
    - **Total Componentes**: Número total de proyectos que miden esta métrica
    - **Meta Configurada**: Porcentaje objetivo configurado para esta métrica
    - **Componentes Objetivo**: Número de componentes que deben cumplir (Total × Meta%)
    - **Componentes Cumplen**: Número de componentes que realmente cumplen
    - **Cumplimiento OKR**: Porcentaje de cumplimiento respecto a la meta (Cumplen/Objetivo × 100)
    
    **Ejemplo**: Si hay 10 componentes y la meta es 90%, el objetivo es 9 componentes. 
    Si cumplen 9, el OKR es 100%. Si cumplen 4.5 (imposible pero para cálculo), el OKR sería 50%.
    """)
else:
    st.warning("⚠️ No hay datos suficientes para calcular OKR de cumplimiento.")

# === NUEVA SECCIÓN: PROGRESO HACIA METAS ===
st.markdown("---")
st.header(f"🎯 Progreso hacia Metas - {celula_seleccionada}")

# Calcular cumplimiento usando los dataframes filtrados correspondientes considerando configuración N/A
cumplimiento_data = []

# COMENTADO: Seguridad no se necesita
# if 'security_rating' in metricas_seleccionadas and not df_seguridad.empty:
#     if config_na.get("incluir_na_seguridad", False):
#         df_security_calc = df_seguridad.copy()
#         df_security_calc['cumple_security'] = df_security_calc['security_rating'].isin(umbral_seguridad)
#         df_security_calc['cumple_security'] = df_security_calc['cumple_security'].fillna(False)
#     else:
#         df_security_calc = df_seguridad.dropna(subset=['security_rating']).copy()
#         df_security_calc['cumple_security'] = df_security_calc['security_rating'].isin(umbral_seguridad)
#     
#     if not df_security_calc.empty:
#         cumplimiento_security_pct = df_security_calc['cumple_security'].mean() * 100
#         cumplimiento_data.append(('Seguridad', cumplimiento_security_pct, metas["meta_seguridad"], '#1f77b4'))

if 'reliability_rating' in metricas_seleccionadas and not df_confiabilidad.empty:
    if config_na.get("incluir_na_confiabilidad", False):
        df_reliability_calc = df_confiabilidad.copy()
        df_reliability_calc['cumple_reliability'] = df_reliability_calc['reliability_rating'].isin(umbral_confiabilidad)
        df_reliability_calc['cumple_reliability'] = df_reliability_calc['cumple_reliability'].fillna(False)
    else:
        df_reliability_calc = df_confiabilidad.dropna(subset=['reliability_rating']).copy()
        df_reliability_calc['cumple_reliability'] = df_reliability_calc['reliability_rating'].isin(umbral_confiabilidad)
    
    if not df_reliability_calc.empty:
        # Calcular OKR para confiabilidad
        total = len(df_reliability_calc)
        cumplen = len(df_reliability_calc[df_reliability_calc['cumple_reliability']])
        meta_configurada = metas.get("meta_confiabilidad", 90)
        componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
        
        if componentes_objetivo > 0:
            okr_reliability = (cumplen / componentes_objetivo) * 100
        else:
            okr_reliability = 100 if cumplen == 0 else 0
        
        okr_reliability = redondear_hacia_arriba(okr_reliability)
        cumplimiento_data.append(('Confiabilidad', okr_reliability, 100, '#ff7f0e'))  # Meta OKR es 100%

if 'sqale_rating' in metricas_seleccionadas and not df_mantenibilidad.empty:
    if config_na.get("incluir_na_mantenibilidad", False):
        df_maintainability_calc = df_mantenibilidad.copy()
        df_maintainability_calc['cumple_maintainability'] = df_maintainability_calc['sqale_rating'].isin(umbral_mantenibilidad)
        df_maintainability_calc['cumple_maintainability'] = df_maintainability_calc['cumple_maintainability'].fillna(False)
    else:
        df_maintainability_calc = df_mantenibilidad.dropna(subset=['sqale_rating']).copy()
        df_maintainability_calc['cumple_maintainability'] = df_maintainability_calc['sqale_rating'].isin(umbral_mantenibilidad)
    
    if not df_maintainability_calc.empty:
        # Calcular OKR para mantenibilidad
        total = len(df_maintainability_calc)
        cumplen = len(df_maintainability_calc[df_maintainability_calc['cumple_maintainability']])
        meta_configurada = metas.get("meta_mantenibilidad", 90)
        componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
        
        if componentes_objetivo > 0:
            okr_maintainability = (cumplen / componentes_objetivo) * 100
        else:
            okr_maintainability = 100 if cumplen == 0 else 0
        
        okr_maintainability = redondear_hacia_arriba(okr_maintainability)
        cumplimiento_data.append(('Mantenibilidad', okr_maintainability, 100, '#2ca02c'))  # Meta OKR es 100%

if 'coverage' in metricas_seleccionadas and not df_cobertura.empty:
    # Para las BARRAS DE PROGRESO usar la configuración filtrada (df_cobertura)
    if config_na.get("incluir_na_cobertura", False):
        df_coverage_calc = df_cobertura.copy()
        df_coverage_calc['cumple_coverage'] = df_coverage_calc['coverage'] >= cobertura_min
        df_coverage_calc['cumple_coverage'] = df_coverage_calc['cumple_coverage'].fillna(False)
    else:
        df_coverage_calc = df_cobertura.dropna(subset=['coverage']).copy()
        df_coverage_calc['cumple_coverage'] = df_coverage_calc['coverage'] >= cobertura_min
    
    df_coverage_calc['excluir_coverage'] = df_coverage_calc['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_coverage_filtrado = df_coverage_calc[~df_coverage_calc['excluir_coverage']]
    if not df_coverage_filtrado.empty:
        # Calcular OKR para cobertura
        total = len(df_coverage_filtrado)
        cumplen = len(df_coverage_filtrado[df_coverage_filtrado['cumple_coverage']])
        meta_configurada = metas.get("meta_cobertura", 50)
        componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
        
        if componentes_objetivo > 0:
            okr_coverage = (cumplen / componentes_objetivo) * 100
        else:
            okr_coverage = 100 if cumplen == 0 else 0
        
        okr_coverage = redondear_hacia_arriba(okr_coverage)
        cumplimiento_data.append(('Cobertura', okr_coverage, 100, '#d62728'))  # Meta OKR es 100%

if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    if config_na.get("incluir_na_complejidad", False):
        df_duplications_calc = df_complejidad.copy()
        df_duplications_calc['cumple_duplications'] = df_duplications_calc['complexity'].isin(umbral_complejidad)
        df_duplications_calc['cumple_duplications'] = df_duplications_calc['cumple_duplications'].fillna(False)
    else:
        df_duplications_calc = df_complejidad.dropna(subset=['complexity']).copy()
        df_duplications_calc['cumple_duplications'] = df_duplications_calc['complexity'].isin(umbral_complejidad)
    
    if not df_duplications_calc.empty:
        # Calcular OKR para complejidad
        total = len(df_duplications_calc)
        cumplen = len(df_duplications_calc[df_duplications_calc['cumple_duplications']])
        meta_configurada = metas.get("meta_complejidad", 90)
        componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
        
        if componentes_objetivo > 0:
            okr_complexity = (cumplen / componentes_objetivo) * 100
        else:
            okr_complexity = 100 if cumplen == 0 else 0
        
        okr_complexity = redondear_hacia_arriba(okr_complexity)
        cumplimiento_data.append(('Complejidad', okr_complexity, 100, '#9467bd'))  # Meta OKR es 100%

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
                st.success(f"✅ OKR cumplido")
            else:
                faltante = meta - actual
                st.warning(f"⚠️ OKR no cumplido - Falta {faltante:.0f}%")  # CORREGIDO: formato sin decimales

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

# Calcular Total Bugs con las columnas de bugs disponibles
bug_cols_disponibles = [col for col in bug_cols if col in df_celula.columns]
if bug_cols_disponibles:
    df_celula['Total Bugs'] = df_celula[bug_cols_disponibles].sum(axis=1)

# Función para formatear porcentajes - APLICAR REDONDEO
formatear_pct = lambda x: f"{redondear_hacia_arriba(float(x)):.0f}%" if pd.notna(x) else "N/A"

# Preparar columnas para mostrar basadas en métricas seleccionadas
columnas_mostrar = ['NombreProyecto']
for metrica in metricas_seleccionadas:
    if metrica in df_celula.columns:
        columnas_mostrar.append(metrica)

# Agregar columnas de bugs si existen
columnas_mostrar.extend([col for col in bug_cols_disponibles if col in df_celula.columns])
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

# Crear fila de resumen usando los datos filtrados por métrica considerando configuración N/A
fila_resumen = {'NombreProyecto': 'Cumplimiento (%)'}

# COMENTADO: Seguridad no se necesita
# if 'security_rating' in metricas_seleccionadas and not df_seguridad.empty:
#     if config_na.get("incluir_na_seguridad", False):
#         df_temp = df_seguridad.copy()
#         df_temp['cumple_security'] = df_temp['security_rating'].isin(umbral_seguridad)
#         df_temp['cumple_security'] = df_temp['cumple_security'].fillna(False)
#     else:
#         df_temp = df_seguridad.dropna(subset=['security_rating']).copy()
#         df_temp['cumple_security'] = df_temp['security_rating'].isin(umbral_seguridad)
#     
#     if not df_temp.empty:
#         fila_resumen['Seguridad'] = formatear_pct(df_temp['cumple_security'].mean() * 100)
#     else:
#         fila_resumen['Seguridad'] = "N/A"

if 'reliability_rating' in metricas_seleccionadas and not df_confiabilidad.empty:
    if config_na.get("incluir_na_confiabilidad", False):
        df_temp = df_confiabilidad.copy()
        df_temp['cumple_reliability'] = df_temp['reliability_rating'].isin(umbral_confiabilidad)
        df_temp['cumple_reliability'] = df_temp['cumple_reliability'].fillna(False)
    else:
        df_temp = df_confiabilidad.dropna(subset=['reliability_rating']).copy()
        df_temp['cumple_reliability'] = df_temp['reliability_rating'].isin(umbral_confiabilidad)
    
    if not df_temp.empty:
        fila_resumen['Confiabilidad'] = formatear_pct(df_temp['cumple_reliability'].mean() * 100)
    else:
        fila_resumen['Confiabilidad'] = "N/A"

if 'sqale_rating' in metricas_seleccionadas and not df_mantenibilidad.empty:
    if config_na.get("incluir_na_mantenibilidad", False):
        df_temp = df_mantenibilidad.copy()
        df_temp['cumple_maintainability'] = df_temp['sqale_rating'].isin(umbral_mantenibilidad)
        df_temp['cumple_maintainability'] = df_temp['cumple_maintainability'].fillna(False)
    else:
        df_temp = df_mantenibilidad.dropna(subset=['sqale_rating']).copy()
        df_temp['cumple_maintainability'] = df_temp['sqale_rating'].isin(umbral_mantenibilidad)
    
    if not df_temp.empty:
        fila_resumen['Mantenibilidad'] = formatear_pct(df_temp['cumple_maintainability'].mean() * 100)
    else:
        fila_resumen['Mantenibilidad'] = "N/A"

if 'coverage' in metricas_seleccionadas:
    # Para cobertura en la TABLA PRINCIPAL usar TODOS los proyectos de la célula (NO los filtrados por configuración)
    df_temp = df_todos_celula_coverage.copy()
    
    if config_na.get("incluir_na_cobertura", False):
        # Incluir todos los proyectos, considerando N/A como "no cumplen"
        df_temp['cumple_coverage'] = df_temp['coverage'] >= cobertura_min
        df_temp['cumple_coverage'] = df_temp['cumple_coverage'].fillna(False)
    else:
        # Solo proyectos con datos válidos
        df_temp = df_temp.dropna(subset=['coverage'])
        df_temp['cumple_coverage'] = df_temp['coverage'] >= cobertura_min
    
    df_temp['excluir_coverage'] = df_temp['NombreProyecto'].isin(proyectos_excluir_coverage)
    df_temp_filtrado = df_temp[~df_temp['excluir_coverage']]
    if not df_temp_filtrado.empty:
        fila_resumen['Cobertura de pruebas unitarias'] = formatear_pct(df_temp_filtrado['cumple_coverage'].mean() * 100)
    else:
        fila_resumen['Cobertura de pruebas unitarias'] = "N/A"

if 'complexity' in metricas_seleccionadas and not df_complejidad.empty:
    if config_na.get("incluir_na_complejidad", False):
        df_temp = df_complejidad.copy()
        df_temp['cumple_duplications'] = df_temp['complexity'].isin(umbral_complejidad)
        df_temp['cumple_duplications'] = df_temp['cumple_duplications'].fillna(False)
    else:
        df_temp = df_complejidad.dropna(subset=['complexity']).copy()
        df_temp['cumple_duplications'] = df_temp['complexity'].isin(umbral_complejidad)
    
    if not df_temp.empty:
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
    if row['NombreProyecto'] == 'Cumplimiento (%)':
        return ['background-color: #f0f0f0; font-weight: bold'] * len(row)
    else:
        return [''] * len(row)

def resaltar_cumplimiento(val):
    """Aplicar colores según el cumplimiento en las columnas de métricas"""
    if isinstance(val, str) and '%' in val and val != 'N/A':
        try:
            # Extraer el número del porcentaje
            porcentaje = float(val.replace('%', ''))
            if porcentaje >= 100:
                return 'background-color: #d4edda; color: #155724'  # Verde para cumplir
            else:
                return 'background-color: #f8d7da; color: #721c24'  # Rojo para no cumplir
        except:
            return ''
    return ''

# Aplicar estilos
df_mostrar_final_styled = df_mostrar_final.style.apply(resaltar_resumen, axis=1)
# Aplicar colores a las columnas de métricas
metricas_cols = ['Confiabilidad', 'Mantenibilidad', 'Cobertura de pruebas unitarias', 'Complejidad']
for col in metricas_cols:
    if col in df_mostrar_final.columns:
        df_mostrar_final_styled = df_mostrar_final_styled.applymap(resaltar_cumplimiento, subset=[col])

st.subheader(f"Proyectos y métricas para la célula: {celula_seleccionada}")
st.dataframe(df_mostrar_final_styled, use_container_width=True, hide_index=True)

# Separar tablas de cobertura si está seleccionada
if 'coverage' in metricas_seleccionadas:
    st.markdown("---")
    st.title("📊 Detalle de Cobertura de Pruebas Unitarias")
    
    # Tabla 1: Proyectos considerados para cobertura - USAR configuración filtrada
    if config_metricas["cobertura_usar_seleccionados"] and celula_seleccionada in seleccion_proyectos and seleccion_proyectos[celula_seleccionada]:
        # Usar proyectos seleccionados aunque no tengan datos de cobertura
        proyectos_coverage = df_ultimo[df_ultimo['Celula'] == celula_seleccionada].copy()
        # Agregar columna de cobertura con NaN para proyectos sin datos
        proyectos_coverage['coverage'] = proyectos_coverage['coverage'].fillna('N/A')
        # Solo incluir proyectos seleccionados
        proyectos_coverage = proyectos_coverage[proyectos_coverage['NombreProyecto'].isin(seleccion_proyectos[celula_seleccionada])]
    else:
        # Usar configuración original (solo proyectos con datos de cobertura)
        proyectos_coverage = df_cobertura.dropna(subset=['coverage']).copy()
    
    proyectos_coverage['cumple_coverage'] = proyectos_coverage['coverage'].apply(lambda x: x >= cobertura_min if pd.notna(x) and x != 'N/A' else 'N/A')
    proyectos_coverage['excluir_coverage'] = proyectos_coverage['NombreProyecto'].isin(proyectos_excluir_coverage)
    
    proyectos_coverage_incluidos = proyectos_coverage[~proyectos_coverage['excluir_coverage']][['NombreProyecto', 'coverage', 'cumple_coverage']].copy()
    
    if not proyectos_coverage_incluidos.empty:
        # Calcular promedio de cobertura (excluyendo proyectos sin datos)
        proyectos_con_datos = proyectos_coverage_incluidos[proyectos_coverage_incluidos['coverage'] != 'N/A']
        if not proyectos_con_datos.empty:
            promedio_cobertura = proyectos_con_datos['coverage'].mean()
            promedio_cobertura = redondear_hacia_arriba(promedio_cobertura)
        else:
            promedio_cobertura = 0
        
        # Formatear cobertura (mantener N/A para proyectos sin datos)
        proyectos_coverage_incluidos['coverage'] = proyectos_coverage_incluidos['coverage'].apply(
            lambda x: formatear_pct(x) if x != 'N/A' else 'N/A'
        )
        proyectos_coverage_incluidos['cumple_coverage'] = proyectos_coverage_incluidos['cumple_coverage'].map({True: '✅', False: '❌', 'N/A': 'N/A'})
        proyectos_coverage_incluidos.rename(columns={
            'NombreProyecto': 'Proyecto',
            'coverage': 'Cobertura',
            'cumple_coverage': 'Cumple'
        }, inplace=True)
        
        st.subheader("🎯 Proyectos incluidos en el cálculo de cobertura")
        
        # Calcular porcentaje de cumplimiento para agregar a la tabla (solo proyectos con datos)
        proyectos_con_datos = proyectos_coverage_incluidos[proyectos_coverage_incluidos['Cumple'] != 'N/A']
        proyectos_que_cumplen = len(proyectos_con_datos[proyectos_con_datos['Cumple'] == '✅'])
        total_proyectos_con_datos = len(proyectos_con_datos)
        total_proyectos_coverage = len(proyectos_coverage_incluidos)
        
        if total_proyectos_con_datos > 0:
            porcentaje_cumplimiento = (proyectos_que_cumplen / total_proyectos_con_datos) * 100
            porcentaje_cumplimiento = redondear_hacia_arriba(porcentaje_cumplimiento)  # APLICAR REDONDEO
            
            # Agregar fila de cumplimiento a la tabla
            fila_cumplimiento = {
                'Proyecto': 'Cumplimiento (%)',
                'Cobertura': f"{porcentaje_cumplimiento:.0f}%",  # FORMATO SIN DECIMALES
                'Cumple': f"{proyectos_que_cumplen}/{total_proyectos_con_datos} (de {total_proyectos_coverage} total)"
            }
            
            # Agregar fila de promedio de cobertura
            fila_promedio = {
                'Proyecto': 'Promedio Cobertura',
                'Cobertura': f"{promedio_cobertura:.0f}%",  # FORMATO SIN DECIMALES
                'Cumple': ''
            }
            
            # Concatenar las filas de resumen
            proyectos_coverage_final = pd.concat([proyectos_coverage_incluidos, pd.DataFrame([fila_cumplimiento, fila_promedio])], ignore_index=True)
            
            # Función para resaltar las filas de resumen
            def resaltar_resumen_coverage(row):
                if row['Proyecto'] == 'Cumplimiento (%)':
                    return ['background-color: #e8f4fd; font-weight: bold'] * len(row)
                elif row['Proyecto'] == 'Promedio Cobertura':
                    return ['background-color: #f0f8ff; font-weight: bold'] * len(row)
                else:
                    return [''] * len(row)
            
            def resaltar_cumplimiento_coverage(val):
                """Aplicar colores según el cumplimiento en la columna de cobertura"""
                if isinstance(val, str) and '%' in val and val != 'N/A':
                    try:
                        # Extraer el número del porcentaje
                        porcentaje = float(val.replace('%', ''))
                        if porcentaje >= 100:
                            return 'background-color: #d4edda; color: #155724'  # Verde para cumplir
                        else:
                            return 'background-color: #f8d7da; color: #721c24'  # Rojo para no cumplir
                    except:
                        return ''
                return ''
            
            proyectos_coverage_styled = proyectos_coverage_final.style.apply(resaltar_resumen_coverage, axis=1)
            # Aplicar colores a la columna de cobertura
            proyectos_coverage_styled = proyectos_coverage_styled.applymap(resaltar_cumplimiento_coverage, subset=['Cobertura'])
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
        # Aplicar colores a la columna de cobertura en proyectos excluidos también
        proyectos_excluidos_styled = proyectos_excluidos.style.applymap(resaltar_cumplimiento_coverage, subset=['Cobertura'])
        st.dataframe(proyectos_excluidos_styled, use_container_width=True, hide_index=True)

# Resumen bugs
if any(col in df_celula.columns for col in bug_cols):
    st.markdown("---")
    st.subheader("🐛 Resumen total de bugs en la célula")
    
    # Tabla resumen actual - usar solo las columnas de bugs disponibles
    resumen_bugs_actual = df_celula[bug_cols_disponibles].sum().astype(int).to_frame().T
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
    
    # Gráfico de barras simple
    fig = px.bar(
        resumen_bugs_actual.melt(var_name='Tipo de Bug', value_name='Cantidad'),
        x='Tipo de Bug',
        y='Cantidad',
        title=f"Cantidad total de bugs por tipo en {celula_seleccionada}"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Métricas históricas de bugs por célula: factor de crecimiento y % eliminación del backlog de deuda técnica
    if not df_historico.empty and 'Mes' in df_historico.columns:
        df_bugs_hist = df_historico[df_historico['Celula'] == celula_seleccionada].copy()
        df_bugs_hist['Mes'] = pd.to_datetime(df_bugs_hist['Mes'], errors='coerce')
        df_bugs_hist = df_bugs_hist.dropna(subset=['Mes'])

        # Solo considerar bugs Crítica, Alta, Media y Baja (ignorar otros niveles como "info")
        bug_cols_hist = [col for col in ['bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor'] if col in df_bugs_hist.columns]
        if bug_cols_hist:
            # Agrupar por mes (periodo mensual) y sumar bugs de la célula
            df_bugs_mes = (
                df_bugs_hist
                .groupby(df_bugs_hist['Mes'].dt.to_period('M'))[bug_cols_hist]
                .sum()
                .reset_index()
            )
            df_bugs_mes['Mes'] = df_bugs_mes['Mes'].dt.to_timestamp()
            df_bugs_mes = df_bugs_mes.sort_values('Mes').reset_index(drop=True)

            # Calcular total de bugs por mes con las columnas seleccionadas
            df_bugs_mes['Total Bugs'] = df_bugs_mes[bug_cols_hist].sum(axis=1)

            # Identificar mes de enero como línea base (tomar el primer enero disponible)
            df_enero = df_bugs_mes[df_bugs_mes['Mes'].dt.month == 1]
            if not df_enero.empty:
                idx_enero_base = df_enero.index[0]
                total_bugs_base = df_bugs_mes.loc[idx_enero_base, 'Total Bugs']

                # Inicializar columnas de métricas
                df_bugs_mes['Factor crecimiento bugs'] = None
                df_bugs_mes['% eliminación backlog deuda técnica'] = None

                for i in range(len(df_bugs_mes)):
                    total_actual = df_bugs_mes.loc[i, 'Total Bugs']

                    # Factor de crecimiento de bugs: diferencia absoluta respecto al mes anterior (puede ser positiva o negativa)
                    if i > 0:
                        total_prev = df_bugs_mes.loc[i - 1, 'Total Bugs']
                        if not pd.isna(total_prev):
                            factor = total_actual - total_prev
                            df_bugs_mes.at[i, 'Factor crecimiento bugs'] = int(factor)

                    # % eliminación del backlog de deuda técnica: respecto a la línea base de enero
                    if i >= idx_enero_base and total_bugs_base and not pd.isna(total_bugs_base) and total_bugs_base != 0:
                        if i == idx_enero_base:
                            # Enero es la línea base, no se muestra porcentaje
                            df_bugs_mes.at[i, '% eliminación backlog deuda técnica'] = None
                        else:
                            eliminacion = ((total_bugs_base - total_actual) / total_bugs_base) * 100
                            # Puede ser negativo si hay más bugs que en enero
                            df_bugs_mes.at[i, '% eliminación backlog deuda técnica'] = redondear_hacia_arriba(eliminacion)

                # Preparar tabla para mostrar
                df_bugs_mostrar = df_bugs_mes[['Mes', 'Total Bugs', 'Factor crecimiento bugs', '% eliminación backlog deuda técnica']].copy()

                # Formatear porcentaje de eliminación
                def formatear_porcentaje(valor):
                    if pd.isna(valor) or valor is None:
                        return "N/A"
                    try:
                        v = float(valor)
                        return f"{v:.0f}%"
                    except Exception:
                        return "N/A"

                # Formatear factor de crecimiento como número con signo
                def formatear_factor(valor):
                    if pd.isna(valor) or valor is None:
                        return "N/A"
                    try:
                        v = int(valor)
                        signo = "+" if v > 0 else ""
                        return f"{signo}{v}"
                    except Exception:
                        return "N/A"

                df_bugs_mostrar['Factor crecimiento bugs'] = df_bugs_mostrar['Factor crecimiento bugs'].apply(formatear_factor)
                df_bugs_mostrar['% eliminación backlog deuda técnica'] = df_bugs_mostrar['% eliminación backlog deuda técnica'].apply(formatear_porcentaje)
                df_bugs_mostrar['Mes'] = df_bugs_mostrar['Mes'].dt.strftime('%Y-%m')

                st.subheader("📉 Tendencia de bugs y eliminación de backlog (base: enero)")
                st.dataframe(df_bugs_mostrar, hide_index=True, use_container_width=True)

# === SECCIÓN: COMPONENTES QUE DEJARON DE CUMPLIR ===
# Solo mostrar si hay datos históricos y se puede comparar con mes anterior
if meses_disponibles and len(meses_disponibles) > 1 and mes_seleccionado:
    # Obtener el mes anterior si existe
    # Nota: meses_disponibles está ordenado de forma descendente (más reciente primero)
    # Para comparar, necesitamos ordenar de forma ascendente
    meses_ordenados = sorted(meses_disponibles)
    
    if mes_seleccionado in meses_ordenados:
        indice_mes_actual = meses_ordenados.index(mes_seleccionado)
        
        if indice_mes_actual > 0:  # Hay mes anterior
            mes_anterior = meses_ordenados[indice_mes_actual - 1]
            
            st.markdown("---")
            st.header(f"⚠️ Componentes que Dejaron de Cumplir - Comparación {mes_anterior} vs {mes_seleccionado}")
            st.markdown(f"Comparando el mes **{mes_anterior}** (anterior) con **{mes_seleccionado}** (actual)")
            
            # Función para calcular componentes degradados entre dos meses
            def calcular_degradados_mes_a_mes(df_historico, celula_seleccionada, mes_anterior, mes_actual, 
                                               proyectos_seleccionados, config_metricas, config_na, parametros):
                """Calcular componentes que pasaron de cumplir a no cumplir entre dos meses"""
                
                # Obtener datos del mes anterior
                df_mes_anterior = df_historico[
                    (df_historico['Celula'] == celula_seleccionada) &
                    (df_historico['Mes'].dt.strftime('%Y-%m') == mes_anterior)
                ].copy()
                
                # Obtener datos del mes actual
                df_mes_actual = df_historico[
                    (df_historico['Celula'] == celula_seleccionada) &
                    (df_historico['Mes'].dt.strftime('%Y-%m') == mes_actual)
                ].copy()
                
                if df_mes_anterior.empty or df_mes_actual.empty:
                    return {}
                
                # Aplicar parámetros
                umbral_confiabilidad = parametros["reliability_rating"].split(",")
                umbral_mantenibilidad = parametros["sqale_rating"].split(",")
                umbral_complejidad = parametros["duplicated_lines_density"].split(",")
                
                resultados = {
                    'Confiabilidad': [],
                    'Mantenibilidad': [],
                    'Complejidad': []
                }
                
                # Definir métricas a analizar (sin cobertura)
                metricas_config = [
                    {
                        'nombre': 'Confiabilidad',
                        'columna': 'reliability_rating',
                        'umbral': umbral_confiabilidad,
                        'usar_seleccionados': config_metricas["confiabilidad_usar_seleccionados"],
                        'incluir_na': config_na.get("incluir_na_confiabilidad", False),
                        'es_rating': True
                    },
                    {
                        'nombre': 'Mantenibilidad',
                        'columna': 'sqale_rating',
                        'umbral': umbral_mantenibilidad,
                        'usar_seleccionados': config_metricas["mantenibilidad_usar_seleccionados"],
                        'incluir_na': config_na.get("incluir_na_mantenibilidad", False),
                        'es_rating': True
                    },
                    {
                        'nombre': 'Complejidad',
                        'columna': 'complexity',
                        'umbral': umbral_complejidad,
                        'usar_seleccionados': config_metricas["complejidad_usar_seleccionados"],
                        'incluir_na': config_na.get("incluir_na_complejidad", False),
                        'es_rating': True
                    }
                ]
                
                for metrica_config in metricas_config:
                    nombre_metrica = metrica_config['nombre']
                    columna = metrica_config['columna']
                    umbral = metrica_config['umbral']
                    usar_seleccionados = metrica_config['usar_seleccionados']
                    incluir_na = metrica_config['incluir_na']
                    
                    # Filtrar datos según configuración para mes anterior
                    if usar_seleccionados and celula_seleccionada in proyectos_seleccionados and proyectos_seleccionados[celula_seleccionada]:
                        df_anterior = df_mes_anterior[df_mes_anterior['NombreProyecto'].isin(proyectos_seleccionados[celula_seleccionada])].copy()
                        df_actual = df_mes_actual[df_mes_actual['NombreProyecto'].isin(proyectos_seleccionados[celula_seleccionada])].copy()
                    else:
                        df_anterior = df_mes_anterior.copy()
                        df_actual = df_mes_actual.copy()
                    
                    if df_anterior.empty or df_actual.empty or columna not in df_anterior.columns or columna not in df_actual.columns:
                        continue
                    
                    # Determinar cumplimiento para mes anterior
                    if incluir_na:
                        df_anterior['cumple'] = df_anterior[columna].isin(umbral)
                        df_anterior['cumple'] = df_anterior['cumple'].fillna(False)
                    else:
                        df_anterior = df_anterior.dropna(subset=[columna]).copy()
                        if df_anterior.empty:
                            continue
                        df_anterior['cumple'] = df_anterior[columna].isin(umbral)
                    
                    # Determinar cumplimiento para mes actual
                    if incluir_na:
                        df_actual['cumple'] = df_actual[columna].isin(umbral)
                        df_actual['cumple'] = df_actual['cumple'].fillna(False)
                    else:
                        df_actual = df_actual.dropna(subset=[columna]).copy()
                        if df_actual.empty:
                            continue
                        df_actual['cumple'] = df_actual[columna].isin(umbral)
                    
                    # Crear diccionarios para búsqueda rápida
                    anterior_dict = df_anterior.set_index('NombreProyecto')[['cumple', columna]].to_dict('index')
                    actual_dict = df_actual.set_index('NombreProyecto')[['cumple', columna]].to_dict('index')
                    
                    # Encontrar componentes que cumplían antes y no cumplen ahora
                    for proyecto in anterior_dict.keys():
                        if proyecto in actual_dict:
                            cumple_anterior = anterior_dict[proyecto]['cumple']
                            cumple_actual = actual_dict[proyecto]['cumple']
                            valor_anterior = anterior_dict[proyecto][columna]
                            valor_actual = actual_dict[proyecto][columna]
                            
                            if cumple_anterior == True and cumple_actual == False:
                                # Formatear valores
                                valor_anterior_str = 'N/A' if pd.isna(valor_anterior) else str(valor_anterior)
                                valor_actual_str = 'N/A' if pd.isna(valor_actual) else str(valor_actual)
                                
                                resultados[nombre_metrica].append({
                                    'Componente': proyecto,
                                    'Valor Anterior': valor_anterior_str,
                                    'Valor Actual': valor_actual_str,
                                    'Estado Anterior': '✅ Cumplía',
                                    'Estado Actual': '❌ No Cumple'
                                })
                
                return resultados
            
            # Calcular componentes degradados
            degradados = calcular_degradados_mes_a_mes(
                df_historico, celula_seleccionada, mes_anterior, mes_seleccionado,
                seleccion_proyectos, config_metricas, config_na, parametros
            )
            
            # Mostrar 3 tablas separadas
            metricas_tablas = ['Confiabilidad', 'Mantenibilidad', 'Complejidad']
            colores_tablas = {
                'Confiabilidad': '#fff3cd',
                'Mantenibilidad': '#f8d7da',
                'Complejidad': '#d1ecf1'
            }
            
            for metrica in metricas_tablas:
                st.markdown("---")
                st.subheader(f"📊 {metrica}")
                
                if degradados.get(metrica):
                    df_tabla = pd.DataFrame(degradados[metrica])
                    
                    # Función para resaltar filas
                    def resaltar_fila(row):
                        return ['background-color: ' + colores_tablas[metrica]] * len(row)
                    
                    df_tabla_styled = df_tabla.style.apply(resaltar_fila, axis=1)
                    st.dataframe(df_tabla_styled, use_container_width=True, hide_index=True)
                    
                    # Mostrar métrica resumen
                    st.info(f"**{len(df_tabla)} componente(s)** dejaron de cumplir la métrica de **{metrica}** entre {mes_anterior} y {mes_seleccionado}")
                else:
                    st.success(f"✅ No hay componentes que hayan dejado de cumplir la métrica de **{metrica}** entre {mes_anterior} y {mes_seleccionado}")

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

        # Mapear nombres de métricas a nombres de configuración
        if metrica == 'coverage':
            usar_seleccionados = config_metricas.get("cobertura_usar_seleccionados", False)
        elif metrica == 'complexity':
            usar_seleccionados = config_metricas.get("complejidad_usar_seleccionados", False)
        else:
            usar_seleccionados = config_metricas.get(f"{metrica.split('_')[0]}_usar_seleccionados", False)

        # Información de depuración desactivada
        # if metrica == 'coverage':
        #     st.info(f"🔍 **Depuración Cobertura:** Usando proyectos seleccionados: {usar_seleccionados}")
        #     if usar_seleccionados and celula_seleccionada in seleccion_proyectos:
        #         proyectos_celula = seleccion_proyectos[celula_seleccionada]
        #         if proyectos_celula:
        #             st.info(f"📋 **Proyectos seleccionados para cobertura en {celula_seleccionada}:** {', '.join(proyectos_celula[:5])}{'...' if len(proyectos_celula) > 5 else ''}")

        cumplimiento_por_mes = []

        # Procesar cada mes disponible
        for mes_fecha in sorted(df_historico['Mes'].dt.to_period('M').unique()):
            df_mes = df_historico[df_historico['Mes'].dt.to_period('M') == mes_fecha]
            df_filtrado = filtrar_datos_por_metrica(df_mes, celula_seleccionada, seleccion_proyectos, usar_seleccionados)

            if df_filtrado.empty:
                continue

            # Aplicar configuración de componentes N/A
            config_na_key = f"incluir_na_{metrica.split('_')[0]}"
            if metrica == 'complexity':
                config_na_key = "incluir_na_complejidad"
            elif metrica == 'coverage':
                config_na_key = "incluir_na_cobertura"
            
            incluir_na = config_na.get(config_na_key, False)
            
            if incluir_na:
                # Incluir todos los proyectos, considerando N/A como "no cumplen"
                if metrica == 'coverage':
                    df_filtrado = df_filtrado[~df_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)]
                    if df_filtrado.empty:
                        continue
                    df_filtrado['cumple'] = df_filtrado['coverage'] >= cobertura_min
                    df_filtrado['cumple'] = df_filtrado['cumple'].fillna(False)
                    valor = df_filtrado['cumple'].mean() * 100
                elif metrica == 'complexity':
                    df_filtrado['cumple'] = df_filtrado['duplicated_lines_density'].isin(umbral_complejidad)
                    df_filtrado['cumple'] = df_filtrado['cumple'].fillna(False)
                    valor = df_filtrado['cumple'].mean() * 100
                elif metrica == 'reliability_rating':
                    df_filtrado['cumple'] = df_filtrado['reliability_rating'].isin(umbral_confiabilidad)
                    df_filtrado['cumple'] = df_filtrado['cumple'].fillna(False)
                    valor = df_filtrado['cumple'].mean() * 100
                elif metrica == 'sqale_rating':
                    df_filtrado['cumple'] = df_filtrado['sqale_rating'].isin(umbral_mantenibilidad)
                    df_filtrado['cumple'] = df_filtrado['cumple'].fillna(False)
                    valor = df_filtrado['cumple'].mean() * 100
            else:
                # Excluir proyectos con métricas vacías (comportamiento original)
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

                elif metrica == 'reliability_rating':
                    valor = df_filtrado['reliability_rating'].isin(umbral_confiabilidad).mean() * 100

                elif metrica == 'sqale_rating':
                    valor = df_filtrado['sqale_rating'].isin(umbral_mantenibilidad).mean() * 100

            # Calcular cumplimiento OKR para tendencias
            # Obtener meta configurada para la métrica
            if metrica == 'coverage':
                meta_key = "meta_cobertura"
            elif metrica == 'complexity':
                meta_key = "meta_complejidad"
            elif metrica == 'reliability_rating':
                meta_key = "meta_confiabilidad"
            elif metrica == 'sqale_rating':
                meta_key = "meta_mantenibilidad"
            else:
                meta_key = "meta_seguridad"
            
            meta_configurada = metas.get(meta_key, 90)
            
            # Calcular componentes objetivo según meta
            total_proyectos = len(df_filtrado)
            componentes_objetivo = redondear_hacia_arriba(total_proyectos * (meta_configurada / 100))
            
            # Calcular cumplimiento OKR (porcentaje respecto a la meta)
            if componentes_objetivo > 0:
                cumplimiento_okr = (valor / 100 * total_proyectos / componentes_objetivo) * 100
            else:
                cumplimiento_okr = 100 if valor == 0 else 0
            
            # APLICAR REDONDEO A TENDENCIAS OKR
            cumplimiento_okr = redondear_hacia_arriba(cumplimiento_okr)

            cumplimiento_por_mes.append({
                'Mes': mes_fecha.to_timestamp(),
                'Cumplimiento OKR (%)': cumplimiento_okr
            })

        if cumplimiento_por_mes:
            df_trend = pd.DataFrame(cumplimiento_por_mes)
            df_trend.sort_values(by='Mes', inplace=True)

            fig_trend = px.line(
                df_trend,
                x='Mes',
                y='Cumplimiento OKR (%)',
                title=f"Tendencia histórica de cumplimiento OKR - {nombres_tendencias.get(metrica, metrica)}",
                markers=True
            )

            # Línea de meta para OKR (100% es el objetivo)
            fig_trend.add_hline(
                y=100, 
                line_dash="dash", 
                line_color="red",
                annotation_text="Meta OKR: 100%"
            )

            # Configurar rango Y de 0 a 100
            fig_trend.update_layout(yaxis=dict(range=[0, 100]))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info(f"No hay datos históricos suficientes para mostrar tendencia de **{nombres_tendencias.get(metrica, metrica)}**.")
else:
    st.info("No hay datos históricos disponibles.")
