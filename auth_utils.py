import os

import pandas as pd
import streamlit as st

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"


def cargar_celulas_disponibles():
    if os.path.exists(ARCHIVO_SELECCION):
        df = pd.read_csv(ARCHIVO_SELECCION)
        return sorted(df["Celula"].dropna().unique().tolist())
    return []


def celulas_desde_usuario(user):
    """Obtiene la lista de células desde el registro del usuario (compatible con formato antiguo)."""
    if not user:
        return []
    if user.get("celulas"):
        raw = user["celulas"]
        return raw if isinstance(raw, list) else [raw]
    if user.get("celula"):
        raw = user["celula"]
        return raw if isinstance(raw, list) else [raw]
    return []


def es_admin():
    return st.session_state.get("rol") == "admin"


def es_usuario():
    return st.session_state.get("rol") == "usuario"


def obtener_celulas_usuario():
    raw = st.session_state.get("celulas")
    if not raw:
        return []
    return raw if isinstance(raw, list) else [raw]


def requiere_sesion():
    if "rol" not in st.session_state:
        st.warning("⚠️ Por favor inicia sesión para continuar.")
        st.stop()


def requiere_admin():
    requiere_sesion()
    if not es_admin():
        st.error("🚫 No tienes permiso para ver esta página. Solo administradores pueden acceder.")
        st.stop()


def requiere_admin_o_usuario():
    requiere_sesion()
    if st.session_state["rol"] not in ["admin", "usuario"]:
        st.error("🚫 No tienes permiso para ver esta página.")
        st.stop()


def requiere_celulas_asignadas():
    celulas = obtener_celulas_usuario()
    if not celulas:
        st.error("🚫 Tu usuario no tiene células asignadas. Contacta al administrador.")
        st.stop()
    return celulas


def filtrar_celulas_permitidas(celulas):
    celulas = [c for c in celulas if c not in ["nan", "obsoleta"] and pd.notna(c)]
    if es_admin():
        return celulas
    asignadas = requiere_celulas_asignadas()
    return [c for c in celulas if c in asignadas]


def mostrar_navegacion_usuario():
    if not es_usuario():
        return
    st.markdown(
        "<style>[data-testid='stSidebarNav'] {display: none;}</style>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown("### Navegación")
        st.page_link("login.py", label="🏠 Inicio")
        st.page_link("pages/descripcion_proyectos.py", label="📋 Descripción Proyectos")
        st.page_link("pages/detalle_celula.py", label="🔎 Detalle Célula")
        st.page_link("pages/resumen_anual.py", label="📅 Resumen Anual")
