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
            return 'background-color: #d4edda; color: #155724'  # Verde para cumplir
        elif val >= 80:
            return 'background-color: #fff3cd; color: #856404'  # Amarillo para cercano
        else:
            return 'background-color: #f8d7da; color: #721c24'  # Rojo para no cumplir
    
    # Aplicar estilo
    df_styled = df_mostrar.style.applymap(resaltar_okr, subset=['Confiabilidad OKR (%)', 'Mantenibilidad OKR (%)', 'Cobertura OKR (%)', 'Complejidad OKR (%)'])
    
    st.dataframe(df_styled, use_container_width=True, hide_index=True)
    
    # Calcular promedios anuales
    st.markdown("---")
    st.subheader("📊 Promedios Anuales")
    
    promedios_anuales = {
        'Confiabilidad OKR (%)': df_okr_anual['Confiabilidad OKR (%)'].mean(),
        'Mantenibilidad OKR (%)': df_okr_anual['Mantenibilidad OKR (%)'].mean(),
        'Cobertura OKR (%)': df_okr_anual['Cobertura OKR (%)'].mean(),
        'Complejidad OKR (%)': df_okr_anual['Complejidad OKR (%)'].mean()
    }
    
    # Mostrar métricas
    cols = st.columns(4)
    colores = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, (metrica, promedio) in enumerate(promedios_anuales.items()):
        with cols[i]:
            st.metric(
                label=metrica.replace(' OKR (%)', ''),
                value=f"{promedio:.1f}%",
                delta=f"{promedio - 100:.1f}%" if promedio >= 100 else f"-{100 - promedio:.1f}%"
            )
    
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

