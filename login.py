import streamlit as st
import bcrypt
import json
import os

from auth_utils import celulas_desde_usuario, mostrar_navegacion_usuario

USUARIOS_FILE = "usuarios.json"

# ---------------------- Funciones ----------------------

def cargar_usuarios():
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r") as f:
            return json.load(f)
    return {}

def verificar_credenciales(username, password, usuarios):
    if username in usuarios:
        hashed = usuarios[username]["password"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), hashed):
            user = usuarios[username]
            return user.get("rol"), celulas_desde_usuario(user)
    return None, None

# ---------------------- Interfaz ----------------------

st.title("🔐 Login")

# Si ya está logueado:
if "rol" in st.session_state and "usuario" in st.session_state:
    mostrar_navegacion_usuario()
    mensaje = f"Ya estás logueado como **{st.session_state['usuario']}** ({st.session_state['rol']})"
    if st.session_state["rol"] == "usuario" and st.session_state.get("celulas"):
        celulas_txt = ", ".join(st.session_state["celulas"])
        mensaje += f" — Células: **{celulas_txt}**"
    st.success(mensaje)
    if st.button("🔓 Cerrar sesión"):
        for key in ["rol", "usuario", "celulas"]:
            st.session_state.pop(key, None)
        st.rerun()

else:
    st.subheader("Inicia sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        usuarios = cargar_usuarios()
        rol, celulas = verificar_credenciales(username, password, usuarios)

        if rol:
            st.session_state["usuario"] = username
            st.session_state["rol"] = rol
            st.session_state["celulas"] = celulas
            if rol == "usuario" and not celulas:
                st.warning("Inicio de sesión exitoso, pero tu usuario no tiene células asignadas. Contacta al administrador.")
            else:
                st.success("Inicio de sesión exitoso")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
