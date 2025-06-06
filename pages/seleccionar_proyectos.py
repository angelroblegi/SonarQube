import streamlit as st
import pandas as pd
import os

# Verificación de rol
if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

ARCHIVO_SELECCION = "data/seleccion_proyectos.csv"
CARPETA_METRICAS = "uploads"

# Cargar todos los archivos metricas_*.xlsx de la carpeta uploads
@st.cache_data
def cargar_datos():
    archivos = sorted([
        f for f in os.listdir(CARPETA_METRICAS)
        if f.startswith("metricas_") and f.endswith(".xlsx")
    ])

    if not archivos:
        return pd.DataFrame(columns=["Celula", "NombreProyecto"])

    dfs = []
    for archivo in archivos:
        df = pd.read_excel(os.path.join(CARPETA_METRICAS, archivo))
        df.columns = df.columns.str.strip()
        dfs.append(df)

    df_total = pd.concat(dfs, ignore_index=True)
    return df_total

# Cargar selección guardada
def cargar_seleccion():
    if os.path.exists(ARCHIVO_SELECCION):
        df_sel = pd.read_csv(ARCHIVO_SELECCION)
        return df_sel
    else:
        return pd.DataFrame(columns=['Celula', 'NombreProyecto'])

# Guardar selección a archivo CSV
def guardar_seleccion(df_seleccion):
    df_seleccion.to_csv(ARCHIVO_SELECCION, index=False)

# Carga de datos
df = cargar_datos()
df_seleccion = cargar_seleccion()

st.title("Selección de proyectos por célula")

todas_las_celulas = sorted(df['Celula'].dropna().unique())

proyectos_seleccionados = {}

# Interfaz por cada célula
for celula in todas_las_celulas:
    st.markdown(f"### 🧬 Célula: `{celula}`")

    proyectos_celula = sorted(df.loc[df['Celula'] == celula, 'NombreProyecto'].dropna().unique())
    precargados = df_seleccion.loc[df_seleccion['Celula'] == celula, 'NombreProyecto'].tolist()

    key_multi = f"multi_{celula}"
    seleccion_actual = st.session_state.get(key_multi, precargados)

    # Buscador limitado a los proyectos de la célula actual
    proyecto_elegido = st.selectbox(
        f"Buscar proyecto para agregar a {celula}",
        options=[p for p in proyectos_celula if p not in seleccion_actual],
        index=None,
        placeholder="Escribe para buscar...",
        key=f"search_{celula}"
    )

    if proyecto_elegido:
        if proyecto_elegido not in seleccion_actual:
            seleccion_actual.append(proyecto_elegido)
            st.session_state[key_multi] = seleccion_actual
            st.success(f"✅ Proyecto '{proyecto_elegido}' agregado a '{celula}'")

    # Lista de proyectos seleccionados para la célula
    seleccion = st.multiselect(
        f"Proyectos seleccionados para {celula}",
        options=sorted(set(proyectos_celula + seleccion_actual)),
        default=seleccion_actual,
        key=key_multi
    )

    proyectos_seleccionados[celula] = seleccion
    st.divider()

# Guardar selección
if st.button("💾 Guardar selección"):
    filas = []
    for cel, proys in proyectos_seleccionados.items():
        for p in proys:
            filas.append({"Celula": cel, "NombreProyecto": p})
    df_guardar = pd.DataFrame(filas)
    guardar_seleccion(df_guardar)
    st.success("✅ Selección guardada.")

# Actualizar session_state global
st.session_state["proyectos_seleccionados"] = proyectos_seleccionados
