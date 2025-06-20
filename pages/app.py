import streamlit as st
import pandas as pd
import io
import os
import glob
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="Dashboard SonarQube")

if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.error("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"
ARCHIVO_PARAMETROS = "data/parametros_metricas.csv"
ARCHIVO_METAS = "data/metas_progreso.csv"  # Nuevo archivo para metas
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
    
    # Columnas numéricas (excluyendo duplicated_lines_density que ahora es rating)
    numeric_cols = [
        'coverage', 'bugs', 'bugs_blocker', 'bugs_critical',
        'bugs_major', 'bugs_minor', 'bugs_info'
    ]
    
    # Convertir columnas numéricas
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Manejar duplicated_lines_density como rating (letras A-E)
    if 'duplicated_lines_density' in df.columns:
        # Convertir a string y limpiar espacios
        df['duplicated_lines_density'] = df['duplicated_lines_density'].astype(str).str.strip().str.upper()
        # Validar que solo contenga valores A-E, si no, asignar 'E' por defecto
        valid_ratings = ['A', 'B', 'C', 'D', 'E']
        df['duplicated_lines_density'] = df['duplicated_lines_density'].apply(
            lambda x: x if x in valid_ratings else 'E'
        )
    
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

def guardar_parametros(parametros):
    df = pd.DataFrame([parametros])
    df.to_csv(ARCHIVO_PARAMETROS, index=False)

def guardar_metas(metas):
    """Guardar metas de progreso en archivo CSV"""
    df = pd.DataFrame([metas])
    df.to_csv(ARCHIVO_METAS, index=False)

@st.cache_data
def convertir_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

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

proyectos_seleccionados = cargar_seleccion()
parametros = cargar_parametros()
metas = cargar_metas()

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
    umbral_security = col1.multiselect("🔐 Security Rating", letras, default=parametros["security_rating"].split(","))
    umbral_reliability = col2.multiselect("🛡️ Reliability Rating", letras, default=parametros["reliability_rating"].split(","))
    umbral_sqale = col3.multiselect("🧹 Maintainability Rating", letras, default=parametros["sqale_rating"].split(","))
    umbral_complexity = col4.multiselect("🌀 Complexity Rating", letras, default=parametros["duplicated_lines_density"].split(","))

    col5, col6 = st.columns(2)
    coverage_min = col5.slider("🧪 Cobertura mínima (%)", 0, 100, int(parametros["coverage_min"]))

    if st.button("💾 Guardar parámetros"):
        nuevos_parametros = {
            "security_rating": ",".join(umbral_security),
            "reliability_rating": ",".join(umbral_reliability),
            "sqale_rating": ",".join(umbral_sqale),
            "duplicated_lines_density": ",".join(umbral_complexity),
            "coverage_min": coverage_min
        }
        guardar_parametros(nuevos_parametros)
        st.success("✅ Parámetros guardados correctamente.")

# Panel de metas de progreso
with st.expander("🎯 Configurar Metas de Progreso"):
    st.markdown("**Define el % de proyectos que deben cumplir cada métrica:**")
    
    col1, col2, col3 = st.columns(3)
    meta_security = col1.slider("🔐 Meta Seguridad (%)", 0, 100, int(metas["meta_security"]))
    meta_reliability = col2.slider("🛡️ Meta Confiabilidad (%)", 0, 100, int(metas["meta_reliability"]))
    meta_maintainability = col3.slider("🧹 Meta Mantenibilidad (%)", 0, 100, int(metas["meta_maintainability"]))
    
    col4, col5 = st.columns(2)
    meta_coverage = col4.slider("🧪 Meta Cobertura (%)", 0, 100, int(metas["meta_coverage"]))
    meta_duplications = col5.slider("🌀 Meta Complejidad (%)", 0, 100, int(metas["meta_duplications"]))
    
    if st.button("💾 Guardar metas"):
        nuevas_metas = {
            "meta_security": meta_security,
            "meta_reliability": meta_reliability,
            "meta_maintainability": meta_maintainability,
            "meta_coverage": meta_coverage,
            "meta_duplications": meta_duplications
        }
        guardar_metas(nuevas_metas)
        st.success("✅ Metas guardadas correctamente.")

# Filtrado de datos
# Para coverage: usar solo proyectos seleccionados
dfs_filtrados_coverage = []
for celula, proyectos in proyectos_seleccionados.items():
    if proyectos:
        df_filtrado = df[(df['Celula'] == celula) & (df['NombreProyecto'].isin(proyectos))]
        dfs_filtrados_coverage.append(df_filtrado)

if not dfs_filtrados_coverage:
    st.warning("⚠️ No hay datos después del filtro.")
    st.stop()

df_filtrado_coverage = pd.concat(dfs_filtrados_coverage)

# Para las demás métricas: usar TODOS los proyectos de las células seleccionadas
celulas_seleccionadas = list(proyectos_seleccionados.keys())
df_todas_metricas = df[df['Celula'].isin(celulas_seleccionadas)].copy()

proyectos_excluir_coverage = [
    "AEL.DebidaDiligencia.FrontEnd:Quality",
    "AEL.NominaElectronica.FrontEnd:Quality"
]

# Calcular cumplimiento para TODAS las métricas excepto coverage (usando todos los proyectos por célula)
df_todas_metricas['cumple_security'] = df_todas_metricas['security_rating'].isin(umbral_security)
df_todas_metricas['cumple_reliability'] = df_todas_metricas['reliability_rating'].isin(umbral_reliability)
df_todas_metricas['cumple_maintainability'] = df_todas_metricas['sqale_rating'].isin(umbral_sqale)
df_todas_metricas['cumple_duplications'] = df_todas_metricas['duplicated_lines_density'].isin(umbral_complexity)

# Calcular cumplimiento para coverage (usando solo proyectos seleccionados)
df_coverage = df_filtrado_coverage[~df_filtrado_coverage['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()
df_coverage['cumple_coverage'] = df_coverage['coverage'] >= coverage_min

# Agrupar métricas generales (todos los proyectos por célula)
agrupado_otros = df_todas_metricas.groupby('Celula').agg({
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

# Agrupar coverage (solo proyectos seleccionados)
agrupado_coverage = df_coverage.groupby('Celula').agg({'cumple_coverage': 'mean'})

agrupado = agrupado_otros.join(agrupado_coverage)
agrupado[['cumple_security', 'cumple_reliability', 'cumple_maintainability',
          'cumple_coverage', 'cumple_duplications']] *= 100
agrupado = agrupado.round(1).reset_index()

agrupado.columns = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Complejidad', 'Bugs', 'Blocker',
    'Critical', 'Major', 'Minor', 'Cobertura de pruebas unitarias'
]

cols_reordenadas = [
    'Célula', 'Seguridad', 'Confiabilidad', 'Mantenibilidad',
    'Cobertura de pruebas unitarias', 'Complejidad',
    'Bugs', 'Blocker', 'Critical', 'Major', 'Minor'
]
agrupado = agrupado[cols_reordenadas]

# Nueva sección: Tabla de Progreso hacia Metas
st.markdown("---")
st.header("🎯 Progreso hacia Metas por Célula")

# Crear tabla de progreso
progreso_data = []
colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

for idx, (_, fila) in enumerate(agrupado.iterrows()):
    celula = fila['Célula']
    
    # Calcular progreso para cada métrica
    metricas_progreso = [
        ('Seguridad', fila['Seguridad'], meta_security, colores[0]),
        ('Confiabilidad', fila['Confiabilidad'], meta_reliability, colores[1]),
        ('Mantenibilidad', fila['Mantenibilidad'], meta_maintainability, colores[2]),
        ('Cobertura', fila['Cobertura de pruebas unitarias'], meta_coverage, colores[3]),
        ('Complejidad', fila['Complejidad'], meta_duplications, colores[4])
    ]
    
    progreso_data.append({
        'Célula': celula,
        'Métricas': metricas_progreso
    })

# Mostrar tabla de progreso
for celula_data in progreso_data:
    st.subheader(f"📊 {celula_data['Célula']}")
    
    # Crear columnas para cada métrica
    cols = st.columns(5)
    
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
                st.warning(f"⚠️ Falta {faltante:.1f}%")

# Resumen general de progreso
st.markdown("---")
st.subheader("📈 Resumen General de Progreso")

# Calcular promedio general por métrica
promedios = {
    'Seguridad': agrupado['Seguridad'].mean(),
    'Confiabilidad': agrupado['Confiabilidad'].mean(),
    'Mantenibilidad': agrupado['Mantenibilidad'].mean(),
    'Cobertura': agrupado['Cobertura de pruebas unitarias'].mean(),
    'Complejidad': agrupado['Complejidad'].mean()
}

metas_dict = {
    'Seguridad': meta_security,
    'Confiabilidad': meta_reliability,
    'Mantenibilidad': meta_maintainability,
    'Cobertura': meta_coverage,
    'Complejidad': meta_duplications
}

# Mostrar resumen en columnas
cols_resumen = st.columns(5)
for i, (metrica, promedio) in enumerate(promedios.items()):
    with cols_resumen[i]:
        meta_actual = metas_dict[metrica]
        progreso_pct = min(promedio / meta_actual * 100, 100) if meta_actual > 0 else 0
        
        st.metric(
            label=f"{metrica}",
            value=f"{promedio:.1f}%",
            delta=f"{promedio - meta_actual:.1f}%" if promedio >= meta_actual else f"-{meta_actual - promedio:.1f}%"
        )
        
        # Barra de progreso pequeña
        fig_small = crear_barra_progreso(promedio, meta_actual, colores[i])
        st.plotly_chart(fig_small, use_container_width=True, config={'displayModeBar': False},
                       key=f"resumen_{metrica}")

st.subheader("📋 Tabla de Cumplimiento por Célula")
st.dataframe(
    agrupado.style.background_gradient(
        cmap="BuGn",
        subset=['Seguridad', 'Confiabilidad', 'Mantenibilidad',
                'Cobertura de pruebas unitarias', 'Complejidad'],
        vmin=0, vmax=100
    ).format({
        'Seguridad': "{:.1f}%", 'Confiabilidad': "{:.1f}%", 'Mantenibilidad': "{:.1f}%",
        'Cobertura de pruebas unitarias': "{:.1f}%", 'Complejidad': "{:.1f}%",
        'Bugs': "{:.0f}", 'Blocker': "{:.0f}", 'Critical': "{:.0f}", 'Major': "{:.0f}", 'Minor': "{:.0f}"
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
        'Bugs', 'Blocker', 'Critical', 'Major', 'Minor'
    ], var_name='Tipo de Bug', value_name='Cantidad'),
    x='Célula', y='Cantidad', color='Tipo de Bug',
    barmode='group', title='Bugs por Célula'
)
st.plotly_chart(fig_bugs, use_container_width=True)

# 🔁 Tendencia mensual
st.markdown("---")
st.header("📈 Tendencia de Cumplimiento por Célula y Métrica")

lista_df = [cargar_datos(a) for a in archivos_todos]
df_todos = pd.concat(lista_df, ignore_index=True) if lista_df else pd.DataFrame()

if 'Mes' in df_todos.columns:
    df_todos['Mes'] = pd.to_datetime(df_todos['Mes'])
    
    # Para coverage: filtrar solo proyectos seleccionados
    df_todos_coverage_filtrado = df_todos[df_todos['NombreProyecto'].isin(
        sum(proyectos_seleccionados.values(), [])
    )].copy()
    
    # Para otras métricas: usar todas las células seleccionadas (todos los proyectos)
    df_todos_otras_metricas = df_todos[df_todos['Celula'].isin(celulas_seleccionadas)].copy()

    # Calcular cumplimiento para métricas generales (todos los proyectos por célula)
    df_todos_otras_metricas['cumple_security'] = df_todos_otras_metricas['security_rating'].isin(umbral_security)
    df_todos_otras_metricas['cumple_reliability'] = df_todos_otras_metricas['reliability_rating'].isin(umbral_reliability)
    df_todos_otras_metricas['cumple_maintainability'] = df_todos_otras_metricas['sqale_rating'].isin(umbral_sqale)
    df_todos_otras_metricas['cumple_duplications'] = df_todos_otras_metricas['duplicated_lines_density'].isin(umbral_complexity)

    # Calcular cumplimiento para coverage (solo proyectos seleccionados)
    df_todos_coverage_final = df_todos_coverage_filtrado[~df_todos_coverage_filtrado['NombreProyecto'].isin(proyectos_excluir_coverage)].copy()
    df_todos_coverage_final['cumple_coverage'] = df_todos_coverage_final['coverage'] >= coverage_min

    tendencias = [
        ("Seguridad", 'cumple_security', df_todos_otras_metricas),
        ("Confiabilidad", 'cumple_reliability', df_todos_otras_metricas),
        ("Mantenibilidad", 'cumple_maintainability', df_todos_otras_metricas),
        ("Cobertura", 'cumple_coverage', df_todos_coverage_final),
        ("Complejidad", 'cumple_duplications', df_todos_otras_metricas)
    ]

    for nombre, columna, df_tendencia in tendencias:
        df_trend = df_tendencia.groupby(['Mes', 'Celula'])[columna].mean().reset_index()
        df_trend[nombre] = df_trend[columna] * 100

        fig_trend = px.line(
            df_trend,
            x='Mes',
            y=nombre,
            color='Celula',
            markers=True,
            title=f"Tendencia mensual de {nombre}"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("⚠️ No se encontró columna 'Mes' para mostrar tendencia.")
