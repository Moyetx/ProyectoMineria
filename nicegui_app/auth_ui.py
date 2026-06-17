"""
nicegui_app/auth_ui.py
---------------------
Compuerta de acceso (seccion 0 de la especificacion) en NiceGUI.

  - Login (correo + contrasena)
  - Registro (nombre, correo, contrasena, confirmacion, foto de perfil)
  - Verificacion de correo por codigo (simulada)
  - Recuperacion de contrasena por token

SESION
======
El usuario autenticado se guarda en `app.storage.user` (persistente via cookie
y JSON-serializable). La foto se guarda como Data-URI base64 para poder
mostrarla con `ui.image`.
"""

import base64

from nicegui import app, ui

import database as db
import security


# ---------------------------------------------------------------------------
# Helpers de sesion
# ---------------------------------------------------------------------------
def _foto_a_datauri(foto_bytes: bytes | None) -> str | None:
    """Convierte bytes de imagen a Data-URI base64 para <img>."""
    if not foto_bytes:
        return None
    b64 = base64.b64encode(foto_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def login_usuario(user_row: dict) -> None:
    """Marca al usuario como autenticado y recarga para entrar a la app."""
    app.storage.user.update(
        {
            "autenticado": True,
            "nombre": user_row["nombre"],
            "email": user_row["email"],
            "foto": _foto_a_datauri(user_row.get("foto")),
        }
    )
    ui.navigate.reload()


def logout_usuario() -> None:
    app.storage.user.clear()
    ui.navigate.reload()


# Estado temporal del flujo de auth (vista actual + datos de registro pendientes)
def _auth_state() -> dict:
    return app.storage.tab.setdefault(
        "auth", {"vista": "login", "codigo": None, "datos": None}
    )


# ---------------------------------------------------------------------------
# UI principal de la compuerta
# ---------------------------------------------------------------------------
def build_auth() -> None:
    """Construye la pantalla de autenticacion centrada."""
    ast = _auth_state()

    with ui.column().classes("absolute-center items-center w-96 gap-4"):
        ui.label("Segmentación Inteligente de Clientes").classes(
            "text-2xl font-bold text-center"
        )
        ui.label("Accede o crea una cuenta para usar el sistema.").classes(
            "text-sm text-gray-500"
        )

        @ui.refreshable
        def formulario():
            vista = ast["vista"]
            if vista == "registro":
                _form_registro(ast, formulario)
            elif vista == "recuperar":
                _form_recuperar(ast, formulario)
            else:
                _form_login(ast, formulario)

        formulario()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def _form_login(ast, refresh):
    with ui.card().classes("w-full gap-3"):
        ui.label("Iniciar Sesión").classes("text-lg font-semibold")
        email = ui.input("Correo electrónico").classes("w-full").mark("login-email")
        password = ui.input("Contraseña", password=True,
                            password_toggle_button=True).classes("w-full").mark("login-password")

        def entrar():
            user = db.obtener_usuario(email.value)
            if not user:
                ui.notify("No existe una cuenta con ese correo.", type="negative")
            elif not user["verificado"]:
                ui.notify("Cuenta no verificada.", type="warning")
            elif security.verificar_password(password.value, user["salt"], user["password_hash"]):
                ui.notify(f"¡Bienvenido, {user['nombre']}!", type="positive")
                login_usuario(user)
            else:
                ui.notify("Contraseña incorrecta.", type="negative")

        ui.button("Entrar", on_click=entrar).classes("w-full")
        with ui.row().classes("w-full justify-between"):
            ui.button("Crear cuenta", on_click=lambda: (ast.update(vista="registro"), refresh.refresh())).props("flat")
            ui.button("¿Olvidaste tu contraseña?",
                     on_click=lambda: (ast.update(vista="recuperar"), refresh.refresh())).props("flat")


# ---------------------------------------------------------------------------
# Registro + verificacion
# ---------------------------------------------------------------------------
def _form_registro(ast, refresh):
    # Paso 2: verificacion de correo
    if ast.get("codigo"):
        _form_verificacion(ast, refresh)
        return

    with ui.card().classes("w-full gap-3"):
        ui.label("Crear Cuenta").classes("text-lg font-semibold")
        nombre = ui.input("Nombre completo").classes("w-full")
        email = ui.input("Correo electrónico").classes("w-full")
        password = ui.input("Contraseña", password=True,
                            password_toggle_button=True).classes("w-full")
        confirmar = ui.input("Confirmar contraseña", password=True,
                            password_toggle_button=True).classes("w-full")

        foto_holder = {"bytes": None}
        ui.label("Foto de perfil (png/jpg)").classes("text-sm")

        async def on_upload(e):
            # Compatible con NiceGUI 3.x (e.file + read async) y 2.x (e.content).
            if hasattr(e, "file"):
                foto_holder["bytes"] = await e.file.read()
                nombre_archivo = e.file.name
            else:
                foto_holder["bytes"] = e.content.read()
                nombre_archivo = e.name
            ui.notify(f"Foto cargada: {nombre_archivo}", type="positive")

        ui.upload(on_upload=on_upload, auto_upload=True).props(
            'accept=".png,.jpg,.jpeg"'
        ).classes("w-full")

        def registrar():
            if not nombre.value or not email.value or not password.value:
                ui.notify("Completa los campos obligatorios.", type="negative"); return
            if not security.email_valido(email.value):
                ui.notify("Correo inválido.", type="negative"); return
            if db.existe_email(email.value):
                ui.notify("Ese correo ya está registrado.", type="negative"); return
            if password.value != confirmar.value:
                ui.notify("Las contraseñas no coinciden.", type="negative"); return
            if len(password.value) < 6:
                ui.notify("La contraseña debe tener al menos 6 caracteres.", type="negative"); return
            # Guardamos datos pendientes hasta verificar el correo
            ast["datos"] = {
                "nombre": nombre.value,
                "email": email.value,
                "password": password.value,
                "foto": foto_holder["bytes"],
            }
            ast["codigo"] = security.generar_codigo()
            refresh.refresh()

        ui.button("Registrarme", on_click=registrar).classes("w-full")
        ui.button("Volver", on_click=lambda: (ast.update(vista="login"), refresh.refresh())).props("flat")


def _form_verificacion(ast, refresh):
    with ui.card().classes("w-full gap-3"):
        ui.label("Verificación de correo").classes("text-lg font-semibold")
        # SIMULACION: en produccion el codigo se enviaria por email.
        ui.label(f"Código (simulado): {ast['codigo']}").classes(
            "font-mono bg-gray-100 p-2 rounded"
        )
        codigo = ui.input("Ingresa el código de 6 dígitos").classes("w-full")

        def verificar():
            if codigo.value.strip() != ast["codigo"]:
                ui.notify("Código incorrecto.", type="negative"); return
            d = ast["datos"]
            salt, pwd_hash = security.crear_hash(d["password"])
            ok = db.crear_usuario(d["nombre"], d["email"], pwd_hash, salt,
                                  foto=d["foto"], verificado=1)
            if ok:
                ui.notify("¡Cuenta creada y verificada! Inicia sesión.", type="positive")
                ast.update(vista="login", codigo=None, datos=None)
                refresh.refresh()
            else:
                ui.notify("No se pudo crear (correo duplicado).", type="negative")

        ui.button("Verificar y activar", on_click=verificar).classes("w-full")
        ui.button("Cancelar",
                 on_click=lambda: (ast.update(vista="login", codigo=None, datos=None), refresh.refresh())).props("flat")


# ---------------------------------------------------------------------------
# Recuperacion de contrasena
# ---------------------------------------------------------------------------
def _form_recuperar(ast, refresh):
    # Paso 2: ya hay token -> restablecer
    if ast.get("codigo") and ast.get("datos"):
        with ui.card().classes("w-full gap-3"):
            ui.label("Restablecer contraseña").classes("text-lg font-semibold")
            ui.label(f"Token (simulado): {ast['codigo']}").classes(
                "font-mono bg-gray-100 p-2 rounded"
            )
            codigo = ui.input("Código de recuperación").classes("w-full")
            nueva = ui.input("Nueva contraseña", password=True,
                            password_toggle_button=True).classes("w-full")
            confirmar = ui.input("Confirmar contraseña", password=True,
                                password_toggle_button=True).classes("w-full")

            def reset():
                if codigo.value.strip() != ast["codigo"]:
                    ui.notify("Código incorrecto.", type="negative"); return
                if nueva.value != confirmar.value:
                    ui.notify("No coinciden.", type="negative"); return
                if len(nueva.value) < 6:
                    ui.notify("Mínimo 6 caracteres.", type="negative"); return
                salt, pwd_hash = security.crear_hash(nueva.value)
                db.actualizar_password(ast["datos"]["email"], pwd_hash, salt)
                ui.notify("Contraseña actualizada. Inicia sesión.", type="positive")
                ast.update(vista="login", codigo=None, datos=None)
                refresh.refresh()

            ui.button("Restablecer", on_click=reset).classes("w-full")
        return

    # Paso 1: pedir correo
    with ui.card().classes("w-full gap-3"):
        ui.label("Recuperar contraseña").classes("text-lg font-semibold")
        email = ui.input("Correo de la cuenta").classes("w-full")

        def enviar():
            if db.existe_email(email.value):
                ast["codigo"] = security.generar_codigo()
                ast["datos"] = {"email": email.value}
                refresh.refresh()
            else:
                ui.notify("No existe una cuenta con ese correo.", type="negative")

        ui.button("Enviar código", on_click=enviar).classes("w-full")
        ui.button("Volver", on_click=lambda: (ast.update(vista="login"), refresh.refresh())).props("flat")
