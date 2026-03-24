import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

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


@st.cache_data(ttl=3600)
def fetch_copilot_metrics(org, token, since=None, until=None):
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


def safe_dict(value):
    """Retorna el valor si es dict, de lo contrario retorna None."""
    return value if isinstance(value, dict) else None


def safe_list(value):
    """Retorna el valor si es list, de lo contrario retorna lista vacía."""
    return value if isinstance(value, list) else []


# Sidebar
st.sidebar.header("⚙️ Configuración")
days_back = st.sidebar.slider("Días de historial", min_value=1, max_value=28, value=28)

until_date = datetime.now()
since_date = until_date - timedelta(days=days_back)
since_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
until_str = until_date.strftime("%Y-%m-%dT%H:%M:%SZ")

with st.spinner("Obteniendo métricas de GitHub Copilot..."):
    data, error = fetch_copilot_metrics(GITHUB_ORG, GITHUB_TOKEN, since_str, until_str)

if error:
    st.error(error)
    st.stop()

if not data or len(data) == 0:
    st.warning("⚠️ No hay datos disponibles para el período seleccionado.")
    st.stop()

# Procesar DataFrame base
df = pd.DataFrame(data)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# Asegurar columnas opcionales
for col in ['total_engaged_users', 'copilot_ide_code_completions',
            'copilot_ide_chat', 'copilot_dotcom_chat', 'copilot_dotcom_pull_requests']:
    if col not in df.columns:
        df[col] = None

if 'total_active_users' not in df.columns:
    df['total_active_users'] = 0

df['total_engaged_users'] = pd.to_numeric(df['total_engaged_users'], errors='coerce').fillna(0)
df['total_active_users'] = pd.to_numeric(df['total_active_users'], errors='coerce').fillna(0)


# ── SECCIÓN 1: RESUMEN GENERAL ──────────────────────────────────────────────
st.header("📈 Resumen General")

col1, col2, col3 = st.columns(3)
avg_active = df['total_active_users'].mean()
avg_engaged = df['total_engaged_users'].mean()

with col1:
    st.metric("👥 Usuarios Activos (Promedio)", f"{avg_active:.0f}")
with col2:
    st.metric("✅ Usuarios Comprometidos (Promedio)", f"{avg_engaged:.0f}")
with col3:
    if avg_active > 0:
        st.metric("📊 Tasa de Compromiso", f"{(avg_engaged / avg_active) * 100:.1f}%")
    else:
        st.metric("📊 Tasa de Compromiso", "N/A")


# ── SECCIÓN 2: TENDENCIA DE USUARIOS ────────────────────────────────────────
st.markdown("---")
st.header("📊 Tendencia de Usuarios")

fig_users = go.Figure()
fig_users.add_trace(go.Scatter(
    x=df['date'], y=df['total_active_users'],
    mode='lines+markers', name='Usuarios Activos',
    line=dict(color='#1f77b4', width=2), marker=dict(size=6)
))
fig_users.add_trace(go.Scatter(
    x=df['date'], y=df['total_engaged_users'],
    mode='lines+markers', name='Usuarios Comprometidos',
    line=dict(color='#ff7f0e', width=2), marker=dict(size=6)
))
fig_users.update_layout(
    title="Usuarios Activos vs Comprometidos",
    xaxis_title="Fecha", yaxis_title="Número de Usuarios",
    hovermode='x unified', height=400
)
st.plotly_chart(fig_users, use_container_width=True)


# ── SECCIÓN 3: CODE COMPLETIONS ──────────────────────────────────────────────
st.markdown("---")
st.header("💻 Métricas de Completado de Código")


def extract_code_completion_metrics(row):
    metrics = {
        'date': row['date'],
        'total_suggestions': 0,
        'total_acceptances': 0,
        'total_lines_suggested': 0,
        'total_lines_accepted': 0
    }
    completions = safe_dict(row.get('copilot_ide_code_completions'))
    if completions:
        for editor in safe_list(completions.get('editors')):
            for model in safe_list(editor.get('models')):
                for lang in safe_list(model.get('languages')):
                    metrics['total_suggestions'] += lang.get('total_code_suggestions', 0)
                    metrics['total_acceptances'] += lang.get('total_code_acceptances', 0)
                    metrics['total_lines_suggested'] += lang.get('total_code_lines_suggested', 0)
                    metrics['total_lines_accepted'] += lang.get('total_code_lines_accepted', 0)
    return metrics


completion_metrics = [extract_code_completion_metrics(row) for _, row in df.iterrows()]
df_completions = pd.DataFrame(completion_metrics)
df_completions['acceptance_rate'] = (
    df_completions['total_acceptances'] / df_completions['total_suggestions'].replace(0, float('nan')) * 100
).fillna(0)

col1, col2, col3, col4 = st.columns(4)
total_suggestions = df_completions['total_suggestions'].sum()
total_acceptances = df_completions['total_acceptances'].sum()
total_lines_accepted = df_completions['total_lines_accepted'].sum()

with col1:
    st.metric("💡 Sugerencias Totales", f"{total_suggestions:,}")
with col2:
    st.metric("✅ Aceptaciones Totales", f"{total_acceptances:,}")
with col3:
    if total_suggestions > 0:
        st.metric("📊 Tasa de Aceptación", f"{(total_acceptances / total_suggestions) * 100:.1f}%")
    else:
        st.metric("📊 Tasa de Aceptación", "N/A")
with col4:
    st.metric("📝 Líneas Aceptadas", f"{total_lines_accepted:,}")

if total_suggestions > 0:
    fig_acceptance = go.Figure()
    fig_acceptance.add_trace(go.Scatter(
        x=df_completions['date'], y=df_completions['acceptance_rate'],
        mode='lines+markers', name='Tasa de Aceptación',
        line=dict(color='#2ca02c', width=2), marker=dict(size=6),
        fill='tozeroy', fillcolor='rgba(44, 160, 44, 0.1)'
    ))
    fig_acceptance.update_layout(
        title="Tasa de Aceptación de Sugerencias",
        xaxis_title="Fecha", yaxis_title="Tasa de Aceptación (%)",
        hovermode='x unified', height=400
    )
    st.plotly_chart(fig_acceptance, use_container_width=True)
else:
    st.info("ℹ️ No hay datos de completado de código en este período.")


# ── SECCIÓN 4: CHAT ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("💬 Métricas de Copilot Chat")


def extract_chat_metrics(row):
    metrics = {
        'date': row['date'],
        'ide_chat_users': 0,
        'ide_total_chats': 0,
        'dotcom_chat_users': 0,
        'dotcom_total_chats': 0
    }
    ide_chat = safe_dict(row.get('copilot_ide_chat'))
    if ide_chat:
        metrics['ide_chat_users'] = ide_chat.get('total_engaged_users', 0)
        for editor in safe_list(ide_chat.get('editors')):
            for model in safe_list(editor.get('models')):
                metrics['ide_total_chats'] += model.get('total_chats', 0)

    dotcom_chat = safe_dict(row.get('copilot_dotcom_chat'))
    if dotcom_chat:
        metrics['dotcom_chat_users'] = dotcom_chat.get('total_engaged_users', 0)
        for model in safe_list(dotcom_chat.get('models')):
            metrics['dotcom_total_chats'] += model.get('total_chats', 0)

    return metrics


chat_metrics = [extract_chat_metrics(row) for _, row in df.iterrows()]
df_chat = pd.DataFrame(chat_metrics)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("👥 Usuarios IDE Chat (Promedio)", f"{df_chat['ide_chat_users'].mean():.0f}")
with col2:
    st.metric("💬 Chats IDE Totales", f"{df_chat['ide_total_chats'].sum():,}")
with col3:
    st.metric("👥 Usuarios Web Chat (Promedio)", f"{df_chat['dotcom_chat_users'].mean():.0f}")
with col4:
    st.metric("💬 Chats Web Totales", f"{df_chat['dotcom_total_chats'].sum():,}")

# Eventos de chat IDE
st.subheader("📋 Eventos de Chat IDE")

total_insertions = 0
total_copies = 0
for row in data:
    ide_chat = safe_dict(row.get('copilot_ide_chat')) if isinstance(row, dict) else None
    if ide_chat:
        for editor in safe_list(ide_chat.get('editors')):
            for model in safe_list(editor.get('models')):
                total_insertions += model.get('total_chat_insertion_events', 0)
                total_copies += model.get('total_chat_copy_events', 0)

col1, col2 = st.columns(2)
with col1:
    st.metric("📥 Eventos de Inserción", f"{total_insertions:,}")
with col2:
    st.metric("📋 Eventos de Copia", f"{total_copies:,}")


# ── SECCIÓN 5: PULL REQUESTS ─────────────────────────────────────────────────
st.markdown("---")
st.header("🔀 Métricas de Pull Requests")


def extract_pr_metrics(data):
    pr_stats = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        pr_data = safe_dict(row.get('copilot_dotcom_pull_requests'))
        if pr_data:
            for repo in safe_list(pr_data.get('repositories')):
                repo_name = repo.get('name', 'unknown')
                if repo_name not in pr_stats:
                    pr_stats[repo_name] = {'total_pr_summaries': 0, 'total_engaged_users': 0}
                for model in safe_list(repo.get('models')):
                    pr_stats[repo_name]['total_pr_summaries'] += model.get('total_pr_summaries_created', 0)
                    pr_stats[repo_name]['total_engaged_users'] = max(
                        pr_stats[repo_name]['total_engaged_users'],
                        model.get('total_engaged_users', 0)
                    )
    return pr_stats


pr_stats = extract_pr_metrics(data)

if pr_stats:
    df_prs = pd.DataFrame.from_dict(pr_stats, orient='index').sort_values('total_pr_summaries', ascending=False)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📝 Resúmenes de PR Creados", f"{df_prs['total_pr_summaries'].sum():,}")
    with col2:
        st.metric("📦 Repositorios Activos", f"{len(df_prs)}")

    fig_prs = go.Figure()
    fig_prs.add_trace(go.Bar(
        x=df_prs.index, y=df_prs['total_pr_summaries'],
        name='Resúmenes de PR', marker_color='#9467bd'
    ))
    fig_prs.update_layout(
        title="Resúmenes de Pull Requests por Repositorio",
        xaxis_title="Repositorio", yaxis_title="Cantidad de Resúmenes", height=400
    )
    st.plotly_chart(fig_prs, use_container_width=True)

    st.subheader("📋 Detalle por Repositorio")
    st.dataframe(df_prs.rename(columns={
        'total_pr_summaries': 'Resúmenes Creados',
        'total_engaged_users': 'Usuarios Comprometidos'
    }), use_container_width=True)
else:
    st.info("ℹ️ No hay datos de Pull Requests disponibles.")


# ── SECCIÓN 6: POR EDITOR ────────────────────────────────────────────────────
st.markdown("---")
st.header("🖥️ Análisis por Editor")


def extract_editor_metrics(data):
    editor_stats = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        completions = safe_dict(row.get('copilot_ide_code_completions'))
        if completions:
            for editor in safe_list(completions.get('editors')):
                name = editor.get('name', 'unknown')
                if name not in editor_stats:
                    editor_stats[name] = {'engaged_users': 0, 'suggestions': 0, 'acceptances': 0}
                editor_stats[name]['engaged_users'] = max(
                    editor_stats[name]['engaged_users'],
                    editor.get('total_engaged_users', 0)
                )
                for model in safe_list(editor.get('models')):
                    for lang in safe_list(model.get('languages')):
                        editor_stats[name]['suggestions'] += lang.get('total_code_suggestions', 0)
                        editor_stats[name]['acceptances'] += lang.get('total_code_acceptances', 0)
    return editor_stats


editor_stats = extract_editor_metrics(data)

if editor_stats:
    df_editors = pd.DataFrame.from_dict(editor_stats, orient='index')
    df_editors['acceptance_rate'] = (
        df_editors['acceptances'] / df_editors['suggestions'].replace(0, float('nan')) * 100
    ).fillna(0)
    df_editors = df_editors.sort_values('suggestions', ascending=False)

    fig_editors = go.Figure()
    fig_editors.add_trace(go.Bar(x=df_editors.index, y=df_editors['suggestions'],
                                  name='Sugerencias', marker_color='#1f77b4'))
    fig_editors.add_trace(go.Bar(x=df_editors.index, y=df_editors['acceptances'],
                                  name='Aceptaciones', marker_color='#2ca02c'))
    fig_editors.update_layout(
        title="Sugerencias y Aceptaciones por Editor",
        xaxis_title="Editor", yaxis_title="Cantidad", barmode='group', height=400
    )
    st.plotly_chart(fig_editors, use_container_width=True)

    st.subheader("📋 Detalle por Editor")
    df_ed_display = df_editors.copy()
    df_ed_display['acceptance_rate'] = df_ed_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_ed_display.rename(columns={
        'engaged_users': 'Usuarios Comprometidos',
        'suggestions': 'Sugerencias',
        'acceptances': 'Aceptaciones',
        'acceptance_rate': 'Tasa de Aceptación'
    }), use_container_width=True)
else:
    st.info("ℹ️ No hay datos de editores disponibles.")


# ── SECCIÓN 7: POR LENGUAJE ──────────────────────────────────────────────────
st.markdown("---")
st.header("🔤 Análisis por Lenguaje de Programación")


def extract_language_metrics(data):
    language_stats = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        completions = safe_dict(row.get('copilot_ide_code_completions'))
        if completions:
            for editor in safe_list(completions.get('editors')):
                for model in safe_list(editor.get('models')):
                    for lang in safe_list(model.get('languages')):
                        name = lang.get('name', 'unknown')
                        if name not in language_stats:
                            language_stats[name] = {
                                'suggestions': 0, 'acceptances': 0,
                                'lines_suggested': 0, 'lines_accepted': 0, 'engaged_users': 0
                            }
                        language_stats[name]['suggestions'] += lang.get('total_code_suggestions', 0)
                        language_stats[name]['acceptances'] += lang.get('total_code_acceptances', 0)
                        language_stats[name]['lines_suggested'] += lang.get('total_code_lines_suggested', 0)
                        language_stats[name]['lines_accepted'] += lang.get('total_code_lines_accepted', 0)
                        language_stats[name]['engaged_users'] = max(
                            language_stats[name]['engaged_users'],
                            lang.get('total_engaged_users', 0)
                        )
    return language_stats


language_stats = extract_language_metrics(data)

if language_stats:
    df_languages = pd.DataFrame.from_dict(language_stats, orient='index')
    df_languages['acceptance_rate'] = (
        df_languages['acceptances'] / df_languages['suggestions'].replace(0, float('nan')) * 100
    ).fillna(0)
    df_languages = df_languages.sort_values('suggestions', ascending=False)
    df_top = df_languages.head(10)

    fig_lang = go.Figure()
    fig_lang.add_trace(go.Bar(x=df_top.index, y=df_top['suggestions'],
                               name='Sugerencias', marker_color='#1f77b4'))
    fig_lang.add_trace(go.Bar(x=df_top.index, y=df_top['acceptances'],
                               name='Aceptaciones', marker_color='#2ca02c'))
    fig_lang.update_layout(
        title="Top 10 Lenguajes por Sugerencias y Aceptaciones",
        xaxis_title="Lenguaje", yaxis_title="Cantidad", barmode='group', height=400
    )
    st.plotly_chart(fig_lang, use_container_width=True)

    st.subheader("📋 Detalle por Lenguaje")
    df_lang_display = df_languages.copy()
    df_lang_display['acceptance_rate'] = df_lang_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_lang_display.rename(columns={
        'suggestions': 'Sugerencias', 'acceptances': 'Aceptaciones',
        'lines_suggested': 'Líneas Sugeridas', 'lines_accepted': 'Líneas Aceptadas',
        'acceptance_rate': 'Tasa de Aceptación', 'engaged_users': 'Usuarios Comprometidos'
    }), use_container_width=True)
else:
    st.info("ℹ️ No hay datos de lenguajes disponibles.")


# ── SECCIÓN 8: POR MODELO ────────────────────────────────────────────────────
st.markdown("---")
st.header("🤖 Análisis por Modelo")


def extract_model_metrics(data):
    model_stats = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        completions = safe_dict(row.get('copilot_ide_code_completions'))
        if completions:
            for editor in safe_list(completions.get('editors')):
                for model in safe_list(editor.get('models')):
                    model_name = model.get('name', 'unknown')
                    is_custom = model.get('is_custom_model', False)
                    key = f"{model_name} ({'Custom' if is_custom else 'Default'})"
                    if key not in model_stats:
                        model_stats[key] = {'suggestions': 0, 'acceptances': 0,
                                            'engaged_users': 0, 'is_custom': is_custom}
                    model_stats[key]['engaged_users'] = max(
                        model_stats[key]['engaged_users'],
                        model.get('total_engaged_users', 0)
                    )
                    for lang in safe_list(model.get('languages')):
                        model_stats[key]['suggestions'] += lang.get('total_code_suggestions', 0)
                        model_stats[key]['acceptances'] += lang.get('total_code_acceptances', 0)
    return model_stats


model_stats = extract_model_metrics(data)

if model_stats:
    df_models = pd.DataFrame.from_dict(model_stats, orient='index')
    df_models['acceptance_rate'] = (
        df_models['acceptances'] / df_models['suggestions'].replace(0, float('nan')) * 100
    ).fillna(0)
    df_models = df_models.sort_values('suggestions', ascending=False)

    fig_models = go.Figure()
    fig_models.add_trace(go.Bar(x=df_models.index, y=df_models['suggestions'],
                                 name='Sugerencias', marker_color='#d62728'))
    fig_models.add_trace(go.Bar(x=df_models.index, y=df_models['acceptances'],
                                 name='Aceptaciones', marker_color='#2ca02c'))
    fig_models.update_layout(
        title="Sugerencias y Aceptaciones por Modelo",
        xaxis_title="Modelo", yaxis_title="Cantidad", barmode='group', height=400
    )
    st.plotly_chart(fig_models, use_container_width=True)

    st.subheader("📋 Detalle por Modelo")
    df_mod_display = df_models.copy()
    df_mod_display['acceptance_rate'] = df_mod_display['acceptance_rate'].apply(lambda x: f"{x:.1f}%")
    df_mod_display['is_custom'] = df_mod_display['is_custom'].apply(lambda x: '✅ Sí' if x else '❌ No')
    st.dataframe(df_mod_display.rename(columns={
        'suggestions': 'Sugerencias', 'acceptances': 'Aceptaciones',
        'acceptance_rate': 'Tasa de Aceptación', 'engaged_users': 'Usuarios Comprometidos',
        'is_custom': 'Modelo Personalizado'
    }), use_container_width=True)
else:
    st.info("ℹ️ No hay datos de modelos disponibles.")


# ── SECCIÓN 9: DATOS CRUDOS ──────────────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Ver Datos Crudos (JSON)"):
    st.json(data)
