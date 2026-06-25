import streamlit as st
import pandas as pd
import os
import io

from auth_utils import mostrar_navegacion_usuario, requiere_admin_o_usuario

st.set_page_config(layout="wide", page_title="Descripción de Proyectos")

# ── Auth ──────────────────────────────────────────────────────────────────────
requiere_admin_o_usuario()
mostrar_navegacion_usuario()

# ── Constantes ────────────────────────────────────────────────────────────────
ARCHIVO = "data/descripcion_proyectos.xlsx"

# ── Carga ─────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_proyectos(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    return df

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📋 Descripción de Proyectos")
st.caption("Catálogo de proyectos registrados en el sistema de métricas.")

if not os.path.exists(ARCHIVO):
    st.error(f"No se encontró el archivo `{ARCHIVO}`. Verifica que exista en la carpeta `data/`.")
    st.stop()

df = cargar_proyectos(ARCHIVO)

if df.empty:
    st.warning("El archivo está vacío.")
    st.stop()

# ── Métricas rápidas ──────────────────────────────────────────────────────────
total = len(df)
col1, col2, col3 = st.columns(3)
col1.metric("Total de proyectos", total)

# Si existe columna de célula/equipo, mostrar cuántas hay
celula_col = next((c for c in df.columns if "célula" in c.lower() or "celula" in c.lower() or "equipo" in c.lower() or "team" in c.lower()), None)
if celula_col:
    col2.metric("Células / Equipos", df[celula_col].nunique())

# Si existe columna de estado
estado_col = next((c for c in df.columns if "estado" in c.lower() or "status" in c.lower()), None)
if estado_col:
    col3.metric("Estados distintos", df[estado_col].nunique())

st.divider()

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros y búsqueda", expanded=True):
    search_col, filter_cols = st.columns([2, 3])

    with search_col:
        busqueda = st.text_input("Buscar en todas las columnas", placeholder="Escribe para filtrar…")

    # Detectar columnas categóricas con poca cardinalidad para filtros desplegables
    cols_filtro = [
        c for c in df.columns
        if df[c].dtype == object and 1 < df[c].nunique() <= 30
    ]

    filtros_activos = {}
    if cols_filtro:
        with filter_cols:
            num_filtros = min(len(cols_filtro), 3)
            fcols = st.columns(num_filtros)
            for i, col_name in enumerate(cols_filtro[:num_filtros]):
                opciones = sorted(df[col_name].dropna().unique().tolist())
                sel = fcols[i].multiselect(col_name, opciones, key=f"filtro_{col_name}")
                if sel:
                    filtros_activos[col_name] = sel

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df_filtrado = df.copy()

for col_name, valores in filtros_activos.items():
    df_filtrado = df_filtrado[df_filtrado[col_name].isin(valores)]

if busqueda:
    mask = df_filtrado.apply(
        lambda row: row.astype(str).str.contains(busqueda, case=False, na=False).any(),
        axis=1,
    )
    df_filtrado = df_filtrado[mask]

# ── Resultados ────────────────────────────────────────────────────────────────
st.markdown(f"**{len(df_filtrado)}** proyectos mostrados de **{total}** totales.")

# Formatear columnas numéricas con decimales
cols_numericas = df_filtrado.select_dtypes(include="number").columns.tolist()
format_map = {c: "{:,.2f}" for c in cols_numericas if df_filtrado[c].dtype == float}

st.dataframe(
    df_filtrado.reset_index(drop=True),
    use_container_width=True,
    height=500,
    column_config={
        c: st.column_config.NumberColumn(c, format="%.2f")
        for c in cols_numericas
        if df_filtrado[c].dtype == float
    },
)

# ── Descarga ──────────────────────────────────────────────────────────────────
st.divider()
dl_col1, dl_col2 = st.columns([3, 1])

with dl_col1:
    st.markdown("#### ⬇️ Descargar")
    fmt = st.radio(
        "Formato",
        ["Excel (.xlsx)", "CSV (.csv)"],
        horizontal=True,
        label_visibility="collapsed",
    )

with dl_col2:
    st.write("")  # spacer

if fmt == "Excel (.xlsx)":
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name="Proyectos")
    st.download_button(
        label="📥 Descargar Excel",
        data=buffer.getvalue(),
        file_name="descripcion_proyectos_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )
else:
    csv_data = df_filtrado.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 Descargar CSV",
        data=csv_data,
        file_name="descripcion_proyectos_filtrado.csv",
        mime="text/csv",
        use_container_width=False,
    )