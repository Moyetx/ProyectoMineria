"""
main.py
-------
Punto de entrada de la version NiceGUI del Sistema de Segmentación de Clientes.

Ejecutar con:
    python main.py
(NiceGUI levanta su propio servidor; abre http://localhost:8080)

FLUJO
=====
1. La pagina '/' es la COMPUERTA DE ACCESO: si el usuario no esta autenticado
   muestra login/registro/recuperacion; si lo esta, muestra la app completa.
2. `await client.connected()` es necesario antes de usar `app.storage.tab`
   (estado del pipeline en memoria, donde vive el DataFrame).
3. La sesion del usuario se guarda en `app.storage.user` (cookie), por eso
   `ui.run` requiere un `storage_secret`.
"""

from nicegui import app, ui

import database as db
from nicegui_app import state, theme
from nicegui_app.auth_ui import build_auth
from nicegui_app.shell import build_shell

# Inicializa la base de datos de usuarios (idempotente).
db.init_db()


@ui.page("/")
async def index(client):
    # Necesario para acceder a app.storage.tab (estado del pipeline en memoria).
    await client.connected()
    # Garantiza que el dict de estado del pipeline exista para esta pestana.
    state.pipe()

    if not app.storage.user.get("autenticado"):
        theme.aplicar_tema_guardado()  # respeta el tema tambien en el login
        build_auth()                   # compuerta de acceso (bloquea la app)
    else:
        build_shell()                  # app principal (navegacion + 6 secciones)


# storage_secret: clave para firmar la cookie de sesion de app.storage.user.
# En produccion, cargala desde una variable de entorno.
# El guard permite importar este modulo (p.ej. en tests) sin levantar el server.
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Segmentación de Clientes",
        storage_secret="cambia-esta-clave-secreta-en-produccion",
        reload=False,
        port=8080,
    )
