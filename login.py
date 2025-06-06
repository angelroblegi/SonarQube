import streamlit as st
import bcrypt
import json
import os

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
            return usuarios[username]["rol"]
    return None

# ---------------------- Interfaz ----------------------

st.title("🔐 Login")

# Si ya está logueado:
if "rol" in st.session_state and "usuario" in st.session_state:
    st.success(f"Ya estás logueado como **{st.session_state['usuario']}** ({st.session_state['rol']})")
    if st.button("🔓 Cerrar sesión"):
        for key in ["rol", "usuario"]:
            st.session_state.pop(key, None)
        st.rerun()

else:
    st.subheader("Inicia sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        usuarios = cargar_usuarios()
        rol = verificar_credenciales(username, password, usuarios)

        if rol:
            st.session_state["usuario"] = username
            st.session_state["rol"] = rol
            st.success("Inicio de sesión exitoso")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
