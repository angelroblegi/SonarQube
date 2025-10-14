import streamlit as st
import pandas as pd
import os
import glob
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import math

st.set_page_config(layout="wide", page_title="Resumen Anual - Dashboard SonarQube")

if "rol" not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión para continuar.")
    st.stop()

if st.session_state["rol"] != "admin":
    st.error("🚫 No tienes permiso para ver esta página. Solo administradores pueden acceder.")
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
    return int(valor + 0.5)

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
    """Cargar metas de progreso desde archivo CSV"""
    if os.path.exists(ARCHIVO_METAS):
        df_metas = pd.read_csv(ARCHIVO_METAS)
        if not df_metas.empty:
            fila = df_metas.iloc[0]
            return {
                "meta_seguridad": float(fila.get("meta_seguridad", 90)),
                "meta_confiabilidad": float(fila.get("meta_confiabilidad", 90)),
                "meta_mantenibilidad": float(fila.get("meta_mantenibilidad", 90)),
                "meta_cobertura": float(fila.get("meta_cobertura", 50)),
                "meta_complejidad": float(fila.get("meta_complejidad", 90))
            }
    return {
        "meta_seguridad": 90.0,
        "meta_confiabilidad": 90.0,
        "meta_mantenibilidad": 90.0,
        "meta_cobertura": 50.0,
        "meta_complejidad": 90.0
    }

def filtrar_datos_por_metrica(df, celula, proyectos_seleccionados, usar_seleccionados):
    """Filtrar datos según configuración de métrica específica"""
    if usar_seleccionados and celula in proyectos_seleccionados and proyectos_seleccionados[celula]:
        return df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos_seleccionados[celula]))]
    else:
        return df[df['Celula'] == celula]

def calcular_bugs_mensual(df_historico, celula_seleccionada):
    """Calcular tendencia de bugs por mes para una célula"""
    df_celula = df_historico[df_historico['Celula'] == celula_seleccionada].copy()
    
    if df_celula.empty:
        return pd.DataFrame()
    
    # Agrupar por mes y sumar bugs
    bugs_por_mes = df_celula.groupby('Mes').agg({
        'bugs_blocker': 'sum',
        'bugs_critical': 'sum',
        'bugs_major': 'sum',
        'bugs_minor': 'sum'
    }).reset_index()
    
    # Calcular total de bugs
    bugs_por_mes['Total Bugs'] = (
        bugs_por_mes['bugs_blocker'] + 
        bugs_por_mes['bugs_critical'] + 
        bugs_por_mes['bugs_major'] + 
        bugs_por_mes['bugs_minor']
    )
    
    bugs_por_mes = bugs_por_mes.sort_values('Mes')
    
    return bugs_por_mes

def calcular_top_variacion_bugs(df_historico, celula_seleccionada, top_n=5):
    """Calcular top aplicaciones con mayor incremento/decremento de bugs de forma inteligente"""
    df_celula = df_historico[df_historico['Celula'] == celula_seleccionada].copy()
    
    if df_celula.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    
    # Calcular total de bugs por aplicación y mes (asegurar enteros)
    df_celula['Total_Bugs'] = (
        df_celula['bugs_blocker'].astype(int) + 
        df_celula['bugs_critical'].astype(int) + 
        df_celula['bugs_major'].astype(int) + 
        df_celula['bugs_minor'].astype(int)
    )
    
    # Ordenar por proyecto y mes
    df_celula = df_celula.sort_values(['NombreProyecto', 'Mes'])
    
    # Calcular diferencia de bugs mes a mes por proyecto
    df_celula['Bugs_Mes_Anterior'] = df_celula.groupby('NombreProyecto')['Total_Bugs'].shift(1)
    df_celula['Variacion_Bugs'] = df_celula['Total_Bugs'] - df_celula['Bugs_Mes_Anterior']
    
    # Filtrar solo registros con mes anterior (excluir primer mes de cada proyecto)
    df_variacion = df_celula[df_celula['Bugs_Mes_Anterior'].notna()].copy()
    
    if df_variacion.empty:
        return pd.DataFrame(), pd.DataFrame(), {'sin_datos': True}
    
    # Obtener el último mes disponible
    ultimo_mes = df_variacion['Mes'].max()
    penultimo_mes = df_variacion[df_variacion['Mes'] < ultimo_mes]['Mes'].max() if len(df_variacion[df_variacion['Mes'] < ultimo_mes]) > 0 else None
    
    df_ultimo_mes = df_variacion[df_variacion['Mes'] == ultimo_mes].copy()
    
    # Estadísticas generales
    estadisticas = {
        'total_aplicaciones': len(df_ultimo_mes),
        'aplicaciones_incrementaron': len(df_ultimo_mes[df_ultimo_mes['Variacion_Bugs'] > 0]),
        'aplicaciones_redujeron': len(df_ultimo_mes[df_ultimo_mes['Variacion_Bugs'] < 0]),
        'aplicaciones_sin_cambio': len(df_ultimo_mes[df_ultimo_mes['Variacion_Bugs'] == 0]),
        'total_bugs_actuales': int(df_ultimo_mes['Total_Bugs'].sum()),
        'total_bugs_anteriores': int(df_ultimo_mes['Bugs_Mes_Anterior'].sum()),
        'variacion_total': int(df_ultimo_mes['Variacion_Bugs'].sum()),
        'mes_actual': ultimo_mes.strftime('%Y-%m'),
        'mes_anterior': penultimo_mes.strftime('%Y-%m') if penultimo_mes else 'N/A'
    }
    
    # Top incrementos (solo si hay variación positiva)
    incrementos = df_ultimo_mes[df_ultimo_mes['Variacion_Bugs'] > 0].copy()
    if not incrementos.empty:
        top_incrementos = incrementos.nlargest(min(top_n, len(incrementos)), 'Variacion_Bugs')[
            ['NombreProyecto', 'Total_Bugs', 'Bugs_Mes_Anterior', 'Variacion_Bugs', 'Mes',
             'bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
        ].copy()
        top_incrementos['Mes_Formateado'] = top_incrementos['Mes'].dt.strftime('%Y-%m')
        # Asegurar que todos los valores son enteros
        top_incrementos['Total_Bugs'] = top_incrementos['Total_Bugs'].astype(int)
        top_incrementos['Bugs_Mes_Anterior'] = top_incrementos['Bugs_Mes_Anterior'].astype(int)
        top_incrementos['Variacion_Bugs'] = top_incrementos['Variacion_Bugs'].astype(int)
        top_incrementos['bugs_blocker'] = top_incrementos['bugs_blocker'].astype(int)
        top_incrementos['bugs_critical'] = top_incrementos['bugs_critical'].astype(int)
        top_incrementos['bugs_major'] = top_incrementos['bugs_major'].astype(int)
        top_incrementos['bugs_minor'] = top_incrementos['bugs_minor'].astype(int)
    else:
        top_incrementos = pd.DataFrame()
    
    # Top decrementos (solo si hay variación negativa)
    decrementos = df_ultimo_mes[df_ultimo_mes['Variacion_Bugs'] < 0].copy()
    if not decrementos.empty:
        top_decrementos = decrementos.nsmallest(min(top_n, len(decrementos)), 'Variacion_Bugs')[
            ['NombreProyecto', 'Total_Bugs', 'Bugs_Mes_Anterior', 'Variacion_Bugs', 'Mes',
             'bugs_blocker', 'bugs_critical', 'bugs_major', 'bugs_minor']
        ].copy()
        top_decrementos['Mes_Formateado'] = top_decrementos['Mes'].dt.strftime('%Y-%m')
        # Asegurar que todos los valores son enteros
        top_decrementos['Total_Bugs'] = top_decrementos['Total_Bugs'].astype(int)
        top_decrementos['Bugs_Mes_Anterior'] = top_decrementos['Bugs_Mes_Anterior'].astype(int)
        top_decrementos['Variacion_Bugs'] = top_decrementos['Variacion_Bugs'].astype(int)
        top_decrementos['bugs_blocker'] = top_decrementos['bugs_blocker'].astype(int)
        top_decrementos['bugs_critical'] = top_decrementos['bugs_critical'].astype(int)
        top_decrementos['bugs_major'] = top_decrementos['bugs_major'].astype(int)
        top_decrementos['bugs_minor'] = top_decrementos['bugs_minor'].astype(int)
    else:
        top_decrementos = pd.DataFrame()
    
    return top_incrementos, top_decrementos, estadisticas

def calcular_okr_anual(df_historico, celula_seleccionada, proyectos_seleccionados, config_metricas, config_na, metas, parametros, proyectos_excluir_coverage):
    """Calcular OKR anual para una célula específica"""
    
    # Proyectos a excluir para coverage
    proyectos_excluir_coverage = [
        "AEL.DebidaDiligencia.FrontEnd:Quality",
        "AEL.NominaElectronica.FrontEnd:Quality"
    ]
    
    # Filtrar datos de la célula seleccionada
    df_celula_historico = df_historico[df_historico['Celula'] == celula_seleccionada].copy()
    
    if df_celula_historico.empty:
        return []
    
    # Aplicar parámetros
    umbral_seguridad = parametros["security_rating"].split(",")
    umbral_confiabilidad = parametros["reliability_rating"].split(",")
    umbral_mantenibilidad = parametros["sqale_rating"].split(",")
    umbral_complejidad = parametros["duplicated_lines_density"].split(",")
    cobertura_min = parametros["coverage_min"]
    
    # Calcular OKR por mes
    okr_mensual = []
    
    for mes in sorted(df_celula_historico['Mes'].dt.to_period('M').unique()):
        df_mes = df_celula_historico[df_celula_historico['Mes'].dt.to_period('M') == mes].copy()
        
        # Filtrar datos según configuración para cada métrica
        df_seguridad = filtrar_datos_por_metrica(df_mes, celula_seleccionada, proyectos_seleccionados, config_metricas["seguridad_usar_seleccionados"])
        df_confiabilidad = filtrar_datos_por_metrica(df_mes, celula_seleccionada, proyectos_seleccionados, config_metricas["confiabilidad_usar_seleccionados"])
        df_mantenibilidad = filtrar_datos_por_metrica(df_mes, celula_seleccionada, proyectos_seleccionados, config_metricas["mantenibilidad_usar_seleccionados"])
        df_cobertura = filtrar_datos_por_metrica(df_mes, celula_seleccionada, proyectos_seleccionados, config_metricas["cobertura_usar_seleccionados"])
        df_complejidad = filtrar_datos_por_metrica(df_mes, celula_seleccionada, proyectos_seleccionados, config_metricas["complejidad_usar_seleccionados"])
        
        # Calcular OKR para cada métrica
        okr_mes = {'Mes': mes.to_timestamp()}
        
        # Confiabilidad
        if not df_confiabilidad.empty:
            if config_na.get("incluir_na_confiabilidad", False):
                df_confiabilidad_calc = df_confiabilidad.copy()
                df_confiabilidad_calc['cumple'] = df_confiabilidad_calc['reliability_rating'].isin(umbral_confiabilidad)
                df_confiabilidad_calc['cumple'] = df_confiabilidad_calc['cumple'].fillna(False)
            else:
                df_confiabilidad_calc = df_confiabilidad.dropna(subset=['reliability_rating'])
                df_confiabilidad_calc['cumple'] = df_confiabilidad_calc['reliability_rating'].isin(umbral_confiabilidad)
            
            if not df_confiabilidad_calc.empty:
                total = len(df_confiabilidad_calc)
                cumplen = len(df_confiabilidad_calc[df_confiabilidad_calc['cumple']])
                meta_configurada = metas.get("meta_confiabilidad", 90)
                componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
                
                if componentes_objetivo > 0:
                    cumplimiento_okr = (cumplen / componentes_objetivo) * 100
                else:
                    cumplimiento_okr = 100 if cumplen == 0 else 0
                
                okr_mes['Confiabilidad OKR (%)'] = redondear_hacia_arriba(cumplimiento_okr)
            else:
                okr_mes['Confiabilidad OKR (%)'] = 0
        else:
            okr_mes['Confiabilidad OKR (%)'] = 0
        
        # Mantenibilidad
        if not df_mantenibilidad.empty:
            if config_na.get("incluir_na_mantenibilidad", False):
                df_mantenibilidad_calc = df_mantenibilidad.copy()
                df_mantenibilidad_calc['cumple'] = df_mantenibilidad_calc['sqale_rating'].isin(umbral_mantenibilidad)
                df_mantenibilidad_calc['cumple'] = df_mantenibilidad_calc['cumple'].fillna(False)
            else:
                df_mantenibilidad_calc = df_mantenibilidad.dropna(subset=['sqale_rating'])
                df_mantenibilidad_calc['cumple'] = df_mantenibilidad_calc['sqale_rating'].isin(umbral_mantenibilidad)
            
            if not df_mantenibilidad_calc.empty:
                total = len(df_mantenibilidad_calc)
                cumplen = len(df_mantenibilidad_calc[df_mantenibilidad_calc['cumple']])
                meta_configurada = metas.get("meta_mantenibilidad", 90)
                componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
                
                if componentes_objetivo > 0:
                    cumplimiento_okr = (cumplen / componentes_objetivo) * 100
                else:
                    cumplimiento_okr = 100 if cumplen == 0 else 0
                
                okr_mes['Mantenibilidad OKR (%)'] = redondear_hacia_arriba(cumplimiento_okr)
            else:
                okr_mes['Mantenibilidad OKR (%)'] = 0
        else:
            okr_mes['Mantenibilidad OKR (%)'] = 0
        
        # Complejidad
        if not df_complejidad.empty:
            if config_na.get("incluir_na_complejidad", False):
                df_complejidad_calc = df_complejidad.copy()
                df_complejidad_calc['cumple'] = df_complejidad_calc['complexity'].isin(umbral_complejidad)
                df_complejidad_calc['cumple'] = df_complejidad_calc['cumple'].fillna(False)
            else:
                df_complejidad_calc = df_complejidad.dropna(subset=['complexity'])
                df_complejidad_calc['cumple'] = df_complejidad_calc['complexity'].isin(umbral_complejidad)
            
            if not df_complejidad_calc.empty:
                total = len(df_complejidad_calc)
                cumplen = len(df_complejidad_calc[df_complejidad_calc['cumple']])
                meta_configurada = metas.get("meta_complejidad", 90)
                componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
                
                if componentes_objetivo > 0:
                    cumplimiento_okr = (cumplen / componentes_objetivo) * 100
                else:
                    cumplimiento_okr = 100 if cumplen == 0 else 0
                
                okr_mes['Complejidad OKR (%)'] = redondear_hacia_arriba(cumplimiento_okr)
            else:
                okr_mes['Complejidad OKR (%)'] = 0
        else:
            okr_mes['Complejidad OKR (%)'] = 0
        
        # Cobertura
        if not df_cobertura.empty:
            # Excluir proyectos específicos
            df_cobertura_calc = df_cobertura[~df_cobertura['NombreProyecto'].isin(proyectos_excluir_coverage)]
            
            if config_na.get("incluir_na_cobertura", False):
                df_cobertura_calc['cumple'] = df_cobertura_calc['coverage'] >= cobertura_min
                df_cobertura_calc['cumple'] = df_cobertura_calc['cumple'].fillna(False)
            else:
                df_cobertura_calc = df_cobertura_calc.dropna(subset=['coverage'])
                df_cobertura_calc['cumple'] = df_cobertura_calc['coverage'] >= cobertura_min
            
            if not df_cobertura_calc.empty:
                total = len(df_cobertura_calc)
                cumplen = len(df_cobertura_calc[df_cobertura_calc['cumple']])
                meta_configurada = metas.get("meta_cobertura", 50)
                componentes_objetivo = redondear_hacia_arriba(total * (meta_configurada / 100))
                
                if componentes_objetivo > 0:
                    cumplimiento_okr = (cumplen / componentes_objetivo) * 100
                else:
                    cumplimiento_okr = 100 if cumplen == 0 else 0
                
                okr_mes['Cobertura OKR (%)'] = redondear_hacia_arriba(cumplimiento_okr)
            else:
                okr_mes['Cobertura OKR (%)'] = 0
        else:
            okr_mes['Cobertura OKR (%)'] = 0
        
        okr_mensual.append(okr_mes)
    
    return okr_mensual

# Cargar datos
df_historico = cargar_todos_los_datos()
seleccion_proyectos = cargar_seleccion()
parametros = cargar_parametros()
config_metricas = cargar_configuracion_metricas()
config_na = cargar_configuracion_na()
metas = cargar_metas()

st.title("📊 Resumen Anual de OKR por Célula")

if df_historico.empty:
    st.warning("⚠️ No se encontraron datos históricos.")
    st.stop()

# Obtener células disponibles
celulas = df_historico['Celula'].unique()
celulas_filtradas = [celula for celula in celulas if celula not in ['nan', 'obsoleta'] and pd.notna(celula)]

if not celulas_filtradas:
    st.warning("⚠️ No hay células válidas para mostrar.")
    st.stop()

# Selector de célula
celula_seleccionada = st.selectbox(
    "Selecciona la célula para ver su resumen anual",
    options=celulas_filtradas
)

st.markdown("---")

# Calcular OKR anual para la célula seleccionada
okr_anual = calcular_okr_anual(
    df_historico, celula_seleccionada, seleccion_proyectos, 
    config_metricas, config_na, metas, parametros, []
)

if okr_anual:
    # Crear DataFrame
    df_okr_anual = pd.DataFrame(okr_anual)
    df_okr_anual['Mes'] = pd.to_datetime(df_okr_anual['Mes'])
    df_okr_anual = df_okr_anual.sort_values('Mes')
    
    # Formatear fecha para mostrar
    df_okr_anual['Mes_Formateado'] = df_okr_anual['Mes'].dt.strftime('%Y-%m')
    
    st.subheader(f"📈 OKR Anual - {celula_seleccionada}")
    
    # Mostrar tabla
    columnas_mostrar = ['Mes_Formateado', 'Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)']
    df_mostrar = df_okr_anual[columnas_mostrar].copy()
    df_mostrar.columns = ['Mes', 'Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)']
    
    # Función para resaltar valores según cumplimiento
    def resaltar_okr(val):
        if val >= 100:
            return 'background-color: #d4edda; color: #155724'
        elif val >= 80:
            return 'background-color: #fff3cd; color: #856404'
        else:
            return 'background-color: #f8d7da; color: #721c24'
    
    # Aplicar estilo
    df_styled = df_mostrar.style.applymap(resaltar_okr, subset=['Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)'])
    
    st.dataframe(df_styled, use_container_width=True, hide_index=True)
    
    # Gráfico de tendencia
    st.markdown("---")
    st.subheader("📈 Tendencia OKR Anual")
    
    # Preparar datos para el gráfico
    df_grafico = df_okr_anual.melt(
        id_vars='Mes', 
        value_vars=['Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)'],
        var_name='Métrica', 
        value_name='OKR (%)'
    )
    
    # Limpiar nombres para el gráfico
    df_grafico['Métrica'] = df_grafico['Métrica'].str.replace(' OKR (%)', '')
    
    fig = px.line(
        df_grafico,
        x='Mes',
        y='OKR (%)',
        color='Métrica',
        title=f"Tendencia OKR Anual - {celula_seleccionada}",
        markers=True
    )
    
    # Agregar línea de meta
    fig.add_hline(
        y=100, 
        line_dash="dash", 
        line_color="red",
        annotation_text="Meta OKR: 100%"
    )
    
    fig.update_layout(yaxis=dict(range=[0, 120]))
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumen de cumplimiento
    st.markdown("---")
    st.subheader("🎯 Resumen de Cumplimiento")
    
    cumplimiento_resumen = []
    for metrica in ['Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)']:
        valores = df_okr_anual[metrica]
        meses_cumple = len(valores[valores >= 100])
        total_meses = len(valores)
        porcentaje_cumple = (meses_cumple / total_meses) * 100 if total_meses > 0 else 0
        
        cumplimiento_resumen.append({
            'Métrica': metrica.replace(' OKR (%)', ''),
            'Meses que Cumplen': meses_cumple,
            'Total de Meses': total_meses,
            '% Meses Cumplidos': f"{porcentaje_cumple:.1f}%"
        })
    
    df_resumen = pd.DataFrame(cumplimiento_resumen)
    
    # Función para resaltar según cumplimiento
    def resaltar_cumplimiento(val):
        if isinstance(val, str) and '%' in val:
            porcentaje = float(val.replace('%', ''))
            if porcentaje >= 80:
                return 'background-color: #d4edda; color: #155724'
            elif porcentaje >= 50:
                return 'background-color: #fff3cd; color: #856404'
            else:
                return 'background-color: #f8d7da; color: #721c24'
        return ''
    
    df_resumen_styled = df_resumen.style.applymap(resaltar_cumplimiento, subset=['% Meses Cumplidos'])
    st.dataframe(df_resumen_styled, use_container_width=True, hide_index=True)

else:
    st.warning(f"⚠️ No hay datos suficientes para calcular OKR anual de {celula_seleccionada}.")

# ============================================
# SECCIÓN DE ANÁLISIS DE BUGS
# ============================================

st.markdown("---")
st.markdown("---")
st.title("🐛 Análisis de Bugs")

# Calcular tendencia de bugs
bugs_mensuales = calcular_bugs_mensual(df_historico, celula_seleccionada)

if not bugs_mensuales.empty:
    # Gráfico de tendencia de bugs
    st.subheader(f"📈 Tendencia de Bugs - {celula_seleccionada}")
    
    # Crear gráfico con plotly
    fig_bugs = go.Figure()
    
    # Agregar línea de bugs totales
    fig_bugs.add_trace(go.Scatter(
        x=bugs_mensuales['Mes'],
        y=bugs_mensuales['Total Bugs'],
        mode='lines+markers',
        name='Total Bugs',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    
    # Agregar líneas por tipo de bug
    fig_bugs.add_trace(go.Scatter(
        x=bugs_mensuales['Mes'],
        y=bugs_mensuales['bugs_blocker'],
        mode='lines+markers',
        name='Blocker',
        line=dict(color='#d62728', width=2, dash='dot'),
        marker=dict(size=6)
    ))
    
    fig_bugs.add_trace(go.Scatter(
        x=bugs_mensuales['Mes'],
        y=bugs_mensuales['bugs_critical'],
        mode='lines+markers',
        name='Critical',
        line=dict(color='#ff7f0e', width=2, dash='dot'),
        marker=dict(size=6)
    ))
    
    fig_bugs.add_trace(go.Scatter(
        x=bugs_mensuales['Mes'],
        y=bugs_mensuales['bugs_major'],
        mode='lines+markers',
        name='Major',
        line=dict(color='#bcbd22', width=2, dash='dot'),
        marker=dict(size=6)
    ))
    
    fig_bugs.add_trace(go.Scatter(
        x=bugs_mensuales['Mes'],
        y=bugs_mensuales['bugs_minor'],
        mode='lines+markers',
        name='Minor',
        line=dict(color='#17becf', width=2, dash='dot'),
        marker=dict(size=6)
    ))
    
    fig_bugs.update_layout(
        title=f"Evolución de Bugs por Tipo - {celula_seleccionada}",
        xaxis_title="Mes",
        yaxis_title="Cantidad de Bugs",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_bugs, use_container_width=True)
    
    # Mostrar tabla de bugs mensuales
    st.markdown("---")
    st.subheader("📋 Detalle Mensual de Bugs")
    
    bugs_mensuales_mostrar = bugs_mensuales.copy()
    bugs_mensuales_mostrar['Mes'] = bugs_mensuales_mostrar['Mes'].dt.strftime('%Y-%m')
    bugs_mensuales_mostrar = bugs_mensuales_mostrar.rename(columns={
        'bugs_blocker': 'Blocker',
        'bugs_critical': 'Critical',
        'bugs_major': 'Major',
        'bugs_minor': 'Minor'
    })
    
    st.dataframe(bugs_mensuales_mostrar, use_container_width=True, hide_index=True)
    
    # TOP 5 Aplicaciones
    st.markdown("---")
    st.subheader("🔝 Top 5 Aplicaciones por Variación de Bugs")
    
    top_incrementos, top_decrementos, estadisticas = calcular_top_variacion_bugs(df_historico, celula_seleccionada, top_n=5)
    
    if not top_incrementos.empty or not top_decrementos.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 **Top 5 - Mayor Incremento de Bugs**")
            if not top_incrementos.empty:
                # Preparar datos para mostrar
                top_inc_mostrar = top_incrementos[['NombreProyecto', 'Bugs_Mes_Anterior', 'Total_Bugs', 'Variacion_Bugs', 'Mes_Formateado']].copy()
                top_inc_mostrar.columns = ['Aplicación', 'Bugs Mes Anterior', 'Bugs Actuales', 'Variación', 'Período']
                top_inc_mostrar['Variación'] = top_inc_mostrar['Variación'].astype(int)
                
                # Función para resaltar incrementos
                def resaltar_incremento(row):
                    return ['background-color: #f8d7da' if col == 'Variación' else '' for col in row.index]
                
                st.dataframe(
                    top_inc_mostrar.style.apply(resaltar_incremento, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Gráfico de barras
                fig_inc = px.bar(
                    top_inc_mostrar,
                    x='Aplicación',
                    y='Variación',
                    title='Incremento de Bugs',
                    color='Variación',
                    color_continuous_scale=['yellow', 'red']
                )
                fig_inc.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_inc, use_container_width=True)
            else:
                st.info("No hay datos de incremento disponibles.")
        
        with col2:
            st.markdown("#### 📉 **Top 5 - Mayor Reducción de Bugs**")
            if not top_decrementos.empty:
                # Preparar datos para mostrar
                top_dec_mostrar = top_decrementos[['NombreProyecto', 'Bugs_Mes_Anterior', 'Total_Bugs', 'Variacion_Bugs', 'Mes_Formateado']].copy()
                top_dec_mostrar.columns = ['Aplicación', 'Bugs Mes Anterior', 'Bugs Actuales', 'Variación', 'Período']
                top_dec_mostrar['Variación'] = top_dec_mostrar['Variación'].astype(int)
                
                # Función para resaltar decrementos
                def resaltar_decremento(row):
                    return ['background-color: #d4edda' if col == 'Variación' else '' for col in row.index]
                
                st.dataframe(
                    top_dec_mostrar.style.apply(resaltar_decremento, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Gráfico de barras
                
    else:
        st.warning("⚠️ No hay suficientes datos para calcular variaciones de bugs (se requieren al menos 2 meses).")

else:
    st.warning(f"⚠️ No hay datos de bugs disponibles para la célula {celula_seleccionada}.")

# ============================================
# MÉTRICAS RESUMEN DE BUGS
# ============================================

if not bugs_mensuales.empty:
    st.markdown("---")
    st.subheader("📊 Métricas Resumen de Bugs")
    
    # Calcular métricas
    total_bugs_actual = bugs_mensuales['Total Bugs'].iloc[-1] if len(bugs_mensuales) > 0 else 0
    total_bugs_inicial = bugs_mensuales['Total Bugs'].iloc[0] if len(bugs_mensuales) > 0 else 0
    variacion_total = total_bugs_actual - total_bugs_inicial
    promedio_bugs = bugs_mensuales['Total Bugs'].mean()
    max_bugs = bugs_mensuales['Total Bugs'].max()
    min_bugs = bugs_mensuales['Total Bugs'].min()
    
    # Mostrar métricas en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Bugs Actuales",
            value=int(total_bugs_actual),
            delta=int(variacion_total) if variacion_total != 0 else None,
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            label="Promedio Anual",
            value=f"{promedio_bugs:.0f}",
            help="Promedio de bugs totales en el año"
        )
    
    with col3:
        st.metric(
            label="Máximo Registrado",
            value=int(max_bugs),
            help="Mayor cantidad de bugs en un mes"
        )
    
    with col4:
        st.metric(
            label="Mínimo Registrado",
            value=int(min_bugs),
            help="Menor cantidad de bugs en un mes"
        )
    
    # Distribución de bugs por tipo (último mes)
    st.markdown("---")
    st.subheader("🥧 Distribución de Bugs por Tipo (Último Mes)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ultimo_mes_bugs = bugs_mensuales.iloc[-1]
        
        # Preparar datos para gráfico de pastel
        tipos_bugs = ['Blocker', 'Critical', 'Major', 'Minor']
        valores_bugs = [
            ultimo_mes_bugs['bugs_blocker'],
            ultimo_mes_bugs['bugs_critical'],
            ultimo_mes_bugs['bugs_major'],
            ultimo_mes_bugs['bugs_minor']
        ]
        
        fig_pie = px.pie(
            values=valores_bugs,
            names=tipos_bugs,
            title=f"Distribución de Bugs - {ultimo_mes_bugs['Mes'].strftime('%Y-%m')}",
            color=tipos_bugs,
            color_discrete_map={
                'Blocker': '#d62728',
                'Critical': '#ff7f0e',
                'Major': '#bcbd22',
                'Minor': '#17becf'
            }
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Detalle")
        detalle_bugs = pd.DataFrame({
            'Tipo': tipos_bugs,
            'Cantidad': valores_bugs,
            'Porcentaje': [f"{(v/sum(valores_bugs)*100):.1f}%" if sum(valores_bugs) > 0 else "0%" for v in valores_bugs]
        })
        
        # Función para colorear filas según tipo
        def colorear_tipo(row):
            colores = {
                'Blocker': 'background-color: #f8d7da',
                'Critical': 'background-color: #fff3cd',
                'Major': 'background-color: #fff9e6',
                'Minor': 'background-color: #d1ecf1'
            }
            return [colores.get(row['Tipo'], '')] * len(row)
        
        st.dataframe(
            detalle_bugs.style.apply(colorear_tipo, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        st.metric(
            label="Total Bugs",
            value=int(sum(valores_bugs))
        )


st.markdown("---")
