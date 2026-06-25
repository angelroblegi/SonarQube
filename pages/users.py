import streamlit as st
import bcrypt
import json
import os

from auth_utils import cargar_celulas_disponibles

USUARIOS_FILE = "usuarios.json"

# Control de acceso
if "rol" not in st.session_state or st.session_state["rol"] != "admin":
    st.warning("🚫 No tienes permiso para ver esta página. Por favor inicia sesión como admin.")
    st.stop()

def cargar_usuarios():
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r") as f:
            return json.load(f)
    return {}

def guardar_usuarios(usuarios):
    with open(USUARIOS_FILE, "w") as f:
        json.dump(usuarios, f, indent=4)
    st.success("✔️ Usuario agregado y archivo actualizado.")

def agregar_usuario_streamlit():
    st.header("Agregar nuevo usuario")

    usuarios = cargar_usuarios()
    celulas_disponibles = cargar_celulas_disponibles()

    nuevo_usuario = st.text_input("Nombre de usuario")
    nueva_contraseña = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["admin", "usuario"])

    celulas = []
    if rol == "usuario":
        if not celulas_disponibles:
            st.error("No hay células disponibles en data/seleccion_proyectos.csv.")
            return
        celulas = st.multiselect(
            "Células asignadas (puedes elegir una o varias)",
            celulas_disponibles,
        )

    if st.button("Agregar usuario"):
        if not nuevo_usuario or not nueva_contraseña:
            st.error("Por favor ingresa usuario y contraseña.")
            return

        if nuevo_usuario in usuarios:
            st.error("⚠️ El usuario ya existe.")
            return

        if rol == "usuario" and not celulas:
            st.error("Debes seleccionar al menos una célula para usuarios de tipo usuario.")
            return

        contraseña_hash = bcrypt.hashpw(nueva_contraseña.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        datos_usuario = {"password": contraseña_hash, "rol": rol}
        if rol == "usuario":
            datos_usuario["celulas"] = celulas
        usuarios[nuevo_usuario] = datos_usuario
        guardar_usuarios(usuarios)

if __name__ == "__main__":
    agregar_usuario_streamlit()
