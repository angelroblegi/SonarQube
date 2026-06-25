import bcrypt
import json
import os

from auth_utils import cargar_celulas_disponibles

# Ruta del archivo JSON donde se almacenan los usuarios
USUARIOS_FILE = "usuarios.json"

# Función para cargar los usuarios desde el archivo JSON
def cargar_usuarios():
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r") as f:
            return json.load(f)
    return {}

# Función para guardar los usuarios en el archivo JSON
def guardar_usuarios(usuarios):
    with open(USUARIOS_FILE, "w") as f:
        json.dump(usuarios, f, indent=4)
    print("✔️ Usuario agregado y archivo actualizado.")

# Función para agregar un nuevo usuario
def agregar_usuario():
    usuarios = cargar_usuarios()

    # Solicitar datos del nuevo usuario
    nuevo_usuario = input("Nombre de usuario: ")
    if nuevo_usuario in usuarios:
        print("⚠️ El usuario ya existe.")
        return

    nueva_contraseña = input("Contraseña: ")
    rol = input("Rol (admin/usuario): ").lower()

    # Validar rol
    if rol not in ["admin", "usuario"]:
        print("⚠️ Rol inválido. Debes ingresar 'admin' o 'usuario'.")
        return

    celulas = []
    if rol == "usuario":
        celulas_disponibles = cargar_celulas_disponibles()
        if not celulas_disponibles:
            print("⚠️ No hay células disponibles en data/seleccion_proyectos.csv.")
            return
        print("Células disponibles:", ", ".join(celulas_disponibles))
        entrada = input("Células asignadas (separadas por coma): ").strip()
        celulas = [c.strip() for c in entrada.split(",") if c.strip()]
        invalidas = [c for c in celulas if c not in celulas_disponibles]
        if invalidas:
            print(f"⚠️ Células inválidas: {', '.join(invalidas)}")
            return
        if not celulas:
            print("⚠️ Debes ingresar al menos una célula.")
            return

    # Hashear la contraseña
    contraseña_hash = bcrypt.hashpw(nueva_contraseña.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Agregar el nuevo usuario al diccionario
    datos_usuario = {
        "password": contraseña_hash,
        "rol": rol,
    }
    if rol == "usuario":
        datos_usuario["celulas"] = celulas
    usuarios[nuevo_usuario] = datos_usuario

    # Guardar los cambios en el archivo JSON
    guardar_usuarios(usuarios)

# Ejecutar el script
if __name__ == "__main__":
    agregar_usuario()
