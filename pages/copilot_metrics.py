import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# Verificar autenticación
if "rol" not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión para continuar.")
    st.stop()

if st.session_state["rol"] not in ["admin", "usuario"]:
    st.error("🚫 No tienes permiso para ver esta página.")
    st.stop()

# Configuración
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_ORG = st.secrets["GITHUB_ORG"]

st.title("📊 Métricas de GitHub Copilot")
st.markdown(f"**Organización:** {GITHUB_ORG}")

@st.cache_data(ttl=3600)  # Cache por 1 hora
def fetch_copilot_metrics(org, token, since=None, until=None):
    """
    Obtener métricas de Copilot desde la API de GitHub
    """
    url = f"https://api.github.com/orgs/{org}/copilot/metrics"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    params = {}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return None, "❌ Acceso denegado. Verifica que el token tenga los permisos necesarios."
        elif e.response.status_code == 404:
            return None, "❌ Organización no encontrada o no tiene Copilot habilitado."
        elif e.response.status_code == 422:
            return None, "❌ Las métricas de Copilot están deshabilitadas en la organización."
        else:
            return None, f"❌ Error HTTP {e.response.status_code}: {str(e)}"
    except Exception as e:
        return None, f"❌ Error al obtener métricas: {str(e)}"

# Selector de rango de fechas
st.sidebar.header("⚙️ Configuración")
days_back = st.sidebar.slider("Días de historial", min_value=1, max_value=100, value=30)

# Calcular fechas
until_date = datetime.now()
since_date = until_date - timedelta(days=days_back)

since_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
until_str = until_date.strftime("%Y-%m-%dT%H:%M:%SZ")

# Obtener datos
with st.spinner("Obteniendo métricas de GitHub Copilot..."):
    data, error = fetch_copilot_metrics(GITHUB_ORG, GITHUB_TOKEN, since_str, until_str)

if error:
    st.error(error)
    st.stop()

if not data or len(data) == 0:
    st.warning("⚠️ No hay datos disponibles para el período seleccionado.")
    st.stop()

# Procesar datos
df = pd.DataFrame(data)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# === SECCIÓN 1: MÉTRICAS GENERALES ===
st.header("📈 Resumen General")

col1, col2, col3 = st.columns(3)

with col1:
    avg_active_users = df['total_active_users'].mean()
    st.metric("👥 Usuarios Activos (Promedio)", f"{avg_active_users:.0f}")

with col2:
    avg_engaged_users = df['total_engaged_users'].mean()
    st.metric("✅ Usuarios Comprometidos (Promedio)", f"{avg_engaged_users:.0f}")

with col3:
    if avg_active_users > 0:
        engagement_rate = (avg_engaged_users / avg_active_users) * 100
        st.metric("📊 Tasa de Compromiso", f"{engagement_rate:.1f}%")
    else:
        st.metric("📊 Tasa de Compromiso", "N/A")

# === SECCIÓN 2: TENDENCIA DE USUARIOS ===
st.markdown("---")
st.header("📊 Tendencia de Usuarios")

fig_users = go.Figure()
fig_users.add_trace(go.Scatter(
    x=df['date'],
    y=df['total_active_users'],
    mode='lines+markers',
    name='Usuarios Activos',
    line=dict(color='#1f77b4', width=2),
    marker=dict(size=6)
))
fig_users.add_trace(go.Scatter(
    x=df['date'],
    y=df['total_engaged_users'],
    mode='lines+markers',
    name='Usuarios Comprometidos',
    line=dict(color='#ff7f0e', width=2),
    marker=dict(size=6)
))

fig_users.update_layout(
    title="Usuarios Activos vs Comprometidos",
    xaxis_title="Fecha",
    yaxis_title="Número de Usuarios",
    hovermode='x unified',
    height=400
)

st.plotly_chart(fig_users, use_container_width=True)

# === SECCIÓN 3: MÉTRICAS DE CODE COMPLETIONS ===
st.markdown("---")
st.header("💻 Métricas de Completado de Código")

# Extraer métricas de code completions
def extract_code_completion_metrics(row):
    """Extraer métricas agregadas de code completions"""
    metrics = {
        'date': row['date'],
        'total_suggestions': 0,
        'total_acceptances': 0,
        'total_lines_suggested': 0,
        'total_lines_accepted': 0
    }
    
    if 'copilot_ide_code_completions' in row and row['copilot_ide_code_completions']:
        completions = row['copilot_ide_code_completions']
        if 'editors' in completions:
            for editor in completions['editors']:
                if 'models' in editor:
                    for model in editor['models']:
                        if 'languages' in model:
                            for lang in model['languages']:
                                metrics['total_suggestions'] += lang.get('total_code_suggestions', 0)
                                metrics['total_acceptances'] += lang.get('total_code_acceptances', 0)
                                metrics['total_lines_suggested'] += lang.get('total_code_lines_suggested', 0)
                                metrics['total_lines_accepted'] += lang.get('total_code_lines_accepted', 0)
    
    return metrics

# Procesar métricas de code completions
completion_metrics = []
for _, row in df.iterrows():
    completion_metrics.append(extract_code_completion_metrics(row))

df_completions = pd.DataFrame(completion_metrics)

# Calcular tasa de aceptación
df_completions['acceptance_rate'] = (
    df_completions['total_acceptances'] / df_completions['total_suggestions'] * 100
).fillna(0)

# Mostrar métricas agregadas
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_suggestions = df_completions['total_suggestions'].sum()
    st.metric("💡 Sugerencias Totales", f"{total_suggestions:,}")

with col2:
    total_acceptances = df_completions['total_acceptances'].sum()
    st.metric("✅ Aceptaciones Totales", f"{total_acceptances:,}")

with col3:
    if total_suggestions > 0:
        overall_acceptance = (total_acceptances / total_suggestions) * 100
        st.metric("📊 Tasa de Aceptación", f"{overall_acceptance:.1f}%")
    else:
        st.metric("📊 Tasa de Aceptación", "N/A")

with col4:
    total_lines_accepted = df_completions['total_lines_accepted'].sum()
    st.metric("📝 Líneas Aceptadas", f"{total_lines_accepted:,}")

# Gráfico de tasa de aceptación en el tiempo
fig_acceptance = go.Figure()
fig_acceptance.add_trace(go.Scatter(
    x=df_completions['date'],
    y=df_completions['acceptance_rate'],
    mode='lines+markers',
    name='Tasa de Aceptación',
    line=dict(color='#2ca02c', width=2),
    marker=dict(size=6),
    fill='tozeroy',
    fillcolor='rgba(44, 160, 44, 0.1)'
))

fig_acceptance.update_layout(
    title="Tasa de Aceptación de Sugerencias",
    xaxis_title="Fecha",
    yaxis_title="Tasa de Aceptación (%)",
    hovermode='x unified',
    height=400
)

st.plotly_chart(fig_acceptance, use_container_width=True)

# === SECCIÓN 4: MÉTRICAS DE CHAT ===
st.markdown("---")
st.header("💬 Métricas de Copilot Chat")

def extract_chat_metrics(row):
    """Extraer métricas de chat"""
    metrics = {
        'date': row['date'],
        'ide_chat_users': 0,
        'ide_total_chats': 0,
        'dotcom_chat_users': 0,
        'dotcom_total_chats': 0
    }
    
    # IDE Chat
    if 'copilot_ide_chat' in row and row['copilot_ide_chat']:
        ide_chat = row['copilot_ide_chat']
        metrics['ide_chat_users'] = ide_chat.get('total_engaged_users', 0)
        
        if 'editors' in ide_chat:
            for editor in ide_chat['editors']:
                if 'models' in editor:
                    for model in editor['models']:
                        metrics['ide_total_chats'] += model.get('total_chats', 0)
    
    # Dotcom Chat
    if 'copilot_dotcom_chat' in row and row['copilot_dotcom_chat']:
        dotcom_chat = row['copilot_dotcom_chat']
        metrics['dotcom_chat_users'] = dotcom_chat.get('total_engaged_users', 0)
        
        if 'models' in dotcom_chat:
            for model in dotcom_chat['models']:
                metrics['dotcom_total_chats'] += model.get('total_chats', 0)
    
    return metrics

# Procesar métricas de chat
chat_metrics = []
for _, row in df.iterrows():
    chat_metrics.append(extract_chat_metrics(row))

df_chat = pd.DataFrame(chat_metrics)

# Mostrar métricas de chat
col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_ide_users = df_chat['ide_chat_users'].mean()
    st.metric("👥 Usuarios IDE Chat (Promedio)", f"{avg_ide_users:.0f}")

with col2:
    total_ide_chats = df_chat['ide_total_chats'].sum()
    st.metric("💬 Chats IDE Totales", f"{total_ide_chats:,}")

with col3:
    avg_dotcom_users = df_chat['dotcom_chat_users'].mean()
    st.metric("👥 Usuarios Web Chat (Promedio)", f"{avg_dotcom_users:.0f}")

with col4:
    total_dotcom_chats = df_chat['dotcom_total_chats'].sum()
    st.metric("💬 Chats Web Totales", f"{total_dotcom_chats:,}")

# === NUEVA SECCIÓN: EVENTOS DE CHAT (INSERCIÓN Y COPIA) ===
st.subheader("📋 Eventos de Chat IDE")

def extract_chat_events(data):
    """Extraer eventos de inserción y copia del chat"""
    events = {
        'total_insertion_events': 0,
        'total_copy_events': 0
    }
    
    for row in data:
        if 'copilot_ide_chat' in row and row['copilot_ide_chat']:
            ide_chat = row['copilot_ide_chat']
            if 'editors' in ide_chat:
                for editor in ide_chat['editors']:
                    if 'models' in editor:
                        for model in editor['models']:
                            events['total_insertion_events'] += model.get('total_chat_insertion_events', 0)
                            events['total_copy_events'] += model.get('total_chat_copy_events', 0)
    
    return events

chat_events = extract_chat_events(data)

col1, col2 = st.columns(2)
with col1:
    st.metric("📥 Eventos de Inserción", f"{chat_events['total_insertion_events']:,}")
with col2:
    st.metric("📋 Eventos de Copia", f"{chat_events['total_copy_events']:,}")

# === SECCIÓN 5: PULL REQUESTS ===
st.markdown("---")
st.header("🔀 Métricas de Pull Requests")

def extract_pr_metrics(data):
    """Extraer métricas de pull requests"""
    pr_stats = {}
    
    for row in data:
        if 'copilot_dotcom_pull_requests' in row and row['copilot_dotcom_pull_requests']:
            pr_data = row['copilot_dotcom_pull_requests']
            if 'repositories' in pr_data:
                for repo in pr_data['repositories']:
                    repo_name = repo.get('name', 'unknown')
                    if repo_name not in pr_stats:
                        pr_stats[repo_name] = {
                            'total_pr_summaries': 0,
                            'total_engaged_users': 0
                        }
                    
                    if 'models' in repo:
                        for model in repo['models']:
                            pr_stats[repo_name]['total_pr_summaries'] += model.get('total_pr_summaries_created', 0)
                            pr_stats[repo_name]['total_engaged_users'] = max(
                                pr_stats[repo_name]['total_engaged_users'],
                                model.get('total_engaged_users', 0)
                            )
    
    return pr_stats

pr_stats = extract_pr_metrics(data)

if pr_stats:
    df_prs = pd.DataFrame.from_dict(pr_stats, orient='index')
    df_prs = df_prs.sort_values('total_pr_summaries', ascending=False)
    
    # Métricas generales de PRs
    col1, col2 = st.columns(2)
    with col1:
        total_pr_summaries = df_prs['total_pr_summaries'].sum()
        st.metric("📝 Resúmenes de PR Creados", f"{total_pr_summaries:,}")
    with col2:
        total_repos = len(df_prs)
        st.metric("📦 Repositorios Activos", f"{total_repos}")
    
    # Gráfico de PRs por repositorio
    fig_prs = go.Figure()
    fig_prs.add_trace(go.Bar(
        x=df_prs.index,
        y=df_prs['total_pr_summaries'],
        name='Resúmenes de PR',
        marker_color='#9467bd'
    ))
    
    fig_prs.update_layout(
        title="Resúmenes de Pull Requests por Repositorio",
        xaxis_title="Repositorio",
        yaxis_title="Cantidad de Resúmenes",
        height=400
    )
    
    st.plotly_chart(fig_prs, use_container_width=True)
    
    # Tabla de detalles por repositorio
    st.subheader("📋 Detalle por Repositorio")
    df_prs_display = df_prs.copy()
    df_prs_display = df_prs_display.rename(columns={
        'total_pr_summaries': 'Resúmenes Creados',
        'total_engaged_users': 'Usuarios Comprometidos'
    })
    st.dataframe(df_prs_display, use_container_width=True)
else:
    st.info("ℹ️ No hay datos de Pull Requests disponibles.")

# === SECCIÓN 6: ANÁLISIS POR EDITOR ===
st.markdown("---")
st.header("🖥️ Análisis por Editor")

def extract_editor_metrics(data):
    """Extraer métricas por editor"""
    editor_stats = {}
    
    for row in data:
        if 'copilot_ide_code_completions' in row and row['copilot_ide_code_completions']:
            completions = row['copilot_ide_code_completions']
            if 'editors' in completions:
                for editor in completions['editors']:
                    editor_name = editor.get('name', 'unknown')
                    if editor_name not in editor_stats:
                        editor_stats[editor_name] = {
                            'engaged_users': 0,
                            'suggestions': 0,
                            'acceptances': 0
                        }
                    
                    editor_stats[editor_name]['engaged_users'] = max(
                        editor_stats[editor_name]['engaged_users'],
                        editor.get('total_engaged_users', 0)
                    )
                    
                    if 'models' in editor:
                        for model in editor['models']:
                            if 'languages' in model:
                                for lang in model['languages']:
                                    editor_stats[editor_name]['suggestions'] += lang.get('total_code_suggestions', 0)
                                    editor_stats[editor_name]['acceptances'] += lang.get('total_code_acceptances', 0)
    
    return editor_stats

editor_stats = extract_editor_metrics(data)

if editor_stats:
    df_editors = pd.DataFrame.from_dict(editor_stats, orient='index')
    df_editors['acceptance_rate'] = (df_editors['acceptances'] / df_editors['suggestions'] * 100).fillna(0)
    df_editors = df_editors.sort_values('suggestions', ascending=False)
    
    # Gráfico de editores
    fig_editors = go.Figure()
    fig_editors.add_trace(go.Bar(
        x=df_editors.index,
        y=df_editors['suggestions'],
        name='Sugerencias',
        marker_color='#1f77b4'
    ))
    fig_editors.add_trace(go.Bar(
        x=df_editors.index,
        y=df_editors['acceptances'],
        name='Aceptaciones',
        marker_color='#2ca02c'
    ))
    
    fig_editors.update_layout(
        title="Sugerencias y Aceptaciones por Editor",
        xaxis_title="Editor",
        yaxis_title="Cantidad",
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig_editors, use_container_width=True)
    
    # Tabla de detalles por editor
    st.subheader("📋 Detalle por Editor")
    df_editors_display = df_editors.copy()
    df_editors_display['acceptance_rate'] = df_editors_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    df_editors_display = df_editors_display.rename(columns={
        'engaged_users': 'Usuarios Comprometidos',
        'suggestions': 'Sugerencias',
        'acceptances': 'Aceptaciones',
        'acceptance_rate': 'Tasa de Aceptación'
    })
    st.dataframe(df_editors_display, use_container_width=True)
else:
    st.info("ℹ️ No hay datos de editores disponibles.")

# === SECCIÓN 7: ANÁLISIS POR LENGUAJE ===
st.markdown("---")
st.header("🔤 Análisis por Lenguaje de Programación")

def extract_language_metrics(data):
    """Extraer métricas por lenguaje"""
    language_stats = {}
    
    for row in data:
        if 'copilot_ide_code_completions' in row and row['copilot_ide_code_completions']:
            completions = row['copilot_ide_code_completions']
            if 'editors' in completions:
                for editor in completions['editors']:
                    if 'models' in editor:
                        for model in editor['models']:
                            if 'languages' in model:
                                for lang in model['languages']:
                                    lang_name = lang.get('name', 'unknown')
                                    if lang_name not in language_stats:
                                        language_stats[lang_name] = {
                                            'suggestions': 0,
                                            'acceptances': 0,
                                            'lines_suggested': 0,
                                            'lines_accepted': 0,
                                            'engaged_users': 0
                                        }
                                    
                                    language_stats[lang_name]['suggestions'] += lang.get('total_code_suggestions', 0)
                                    language_stats[lang_name]['acceptances'] += lang.get('total_code_acceptances', 0)
                                    language_stats[lang_name]['lines_suggested'] += lang.get('total_code_lines_suggested', 0)
                                    language_stats[lang_name]['lines_accepted'] += lang.get('total_code_lines_accepted', 0)
                                    language_stats[lang_name]['engaged_users'] = max(
                                        language_stats[lang_name]['engaged_users'],
                                        lang.get('total_engaged_users', 0)
                                    )
    
    return language_stats

language_stats = extract_language_metrics(data)

if language_stats:
    df_languages = pd.DataFrame.from_dict(language_stats, orient='index')
    df_languages['acceptance_rate'] = (df_languages['acceptances'] / df_languages['suggestions'] * 100).fillna(0)
    df_languages = df_languages.sort_values('suggestions', ascending=False)
    
    # Top 10 lenguajes por sugerencias
    df_top_languages = df_languages.head(10)
    
    fig_languages = go.Figure()
    fig_languages.add_trace(go.Bar(
        x=df_top_languages.index,
        y=df_top_languages['suggestions'],
        name='Sugerencias',
        marker_color='#1f77b4'
    ))
    fig_languages.add_trace(go.Bar(
        x=df_top_languages.index,
        y=df_top_languages['acceptances'],
        name='Aceptaciones',
        marker_color='#2ca02c'
    ))
    
    fig_languages.update_layout(
        title="Top 10 Lenguajes por Sugerencias y Aceptaciones",
        xaxis_title="Lenguaje",
        yaxis_title="Cantidad",
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig_languages, use_container_width=True)
    
    # Tabla de detalles por lenguaje
    st.subheader("📋 Detalle por Lenguaje")
    df_languages_display = df_languages.copy()
    df_languages_display['acceptance_rate'] = df_languages_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    df_languages_display = df_languages_display.rename(columns={
        'suggestions': 'Sugerencias',
        'acceptances': 'Aceptaciones',
        'lines_suggested': 'Líneas Sugeridas',
        'lines_accepted': 'Líneas Aceptadas',
        'acceptance_rate': 'Tasa de Aceptación',
        'engaged_users': 'Usuarios Comprometidos'
    })
    st.dataframe(df_languages_display, use_container_width=True)
else:
    st.info("ℹ️ No hay datos de lenguajes disponibles.")

# === SECCIÓN 8: ANÁLISIS POR MODELO ===
st.markdown("---")
st.header("🤖 Análisis por Modelo")

def extract_model_metrics(data):
    """Extraer métricas por modelo (default vs custom)"""
    model_stats = {}
    
    for row in data:
        if 'copilot_ide_code_completions' in row and row['copilot_ide_code_completions']:
            completions = row['copilot_ide_code_completions']
            if 'editors' in completions:
                for editor in completions['editors']:
                    if 'models' in editor:
                        for model in editor['models']:
                            model_name = model.get('name', 'unknown')
                            is_custom = model.get('is_custom_model', False)
                            model_key = f"{model_name} ({'Custom' if is_custom else 'Default'})"
                            
                            if model_key not in model_stats:
                                model_stats[model_key] = {
                                    'suggestions': 0,
                                    'acceptances': 0,
                                    'engaged_users': 0,
                                    'is_custom': is_custom
                                }
                            
                            model_stats[model_key]['engaged_users'] = max(
                                model_stats[model_key]['engaged_users'],
                                model.get('total_engaged_users', 0)
                            )
                            
                            if 'languages' in model:
                                for lang in model['languages']:
                                    model_stats[model_key]['suggestions'] += lang.get('total_code_suggestions', 0)
                                    model_stats[model_key]['acceptances'] += lang.get('total_code_acceptances', 0)
    
    return model_stats

model_stats = extract_model_metrics(data)

if model_stats:
    df_models = pd.DataFrame.from_dict(model_stats, orient='index')
    df_models['acceptance_rate'] = (df_models['acceptances'] / df_models['suggestions'] * 100).fillna(0)
    df_models = df_models.sort_values('suggestions', ascending=False)
    
    # Gráfico de modelos
    fig_models = go.Figure()
    fig_models.add_trace(go.Bar(
        x=df_models.index,
        y=df_models['suggestions'],
        name='Sugerencias',
        marker_color='#d62728'
    ))
    fig_models.add_trace(go.Bar(
        x=df_models.index,
        y=df_models['acceptances'],
        name='Aceptaciones',
        marker_color='#2ca02c'
    ))
    
    fig_models.update_layout(
        title="Sugerencias y Aceptaciones por Modelo",
        xaxis_title="Modelo",
        yaxis_title="Cantidad",
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig_models, use_container_width=True)
    
    # Tabla de detalles por modelo
    st.subheader("📋 Detalle por Modelo")
    df_models_display = df_models.copy()
    df_models_display['acceptance_rate'] = df_models_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    df_models_display['is_custom'] = df_models_display['is_custom'].apply(lambda x: '✅ Sí' if x else '❌ No')
    df_models_display = df_models_display.rename(columns={
        'suggestions': 'Sugerencias',
        'acceptances': 'Aceptaciones',
        'acceptance_rate': 'Tasa de Aceptación',
        'engaged_users': 'Usuarios Comprometidos',
        'is_custom': 'Modelo Personalizado'
    })
    st.dataframe(df_models_display, use_container_width=True)
else:
    st.info("ℹ️ No hay datos de modelos disponibles.")

# === SECCIÓN 9: DATOS RAW (OPCIONAL) ===
st.markdown("---")
with st.expander("🔍 Ver Datos Crudos (JSON)"):
    st.json(data)
