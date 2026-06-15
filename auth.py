"""
auth.py
-------
Modulo de Autenticacion y Perfil de Usuario (la "compuerta de acceso").

Implementa la seccion 0 de la especificacion:
  - Login (correo + contrasena)
  - Registro (nombre, correo, contrasena, confirmacion, foto de perfil)
  - Verificacion de correo mediante codigo (simulada: el codigo se muestra
    en pantalla y se valida; en produccion se enviaria por email)
  - Recuperacion de contrasena mediante token/codigo
  - Manejo de sesion via st.session_state + render del perfil en el sidebar

Seguridad de contrasenas:
  - Se usa PBKDF2-HMAC-SHA256 (libreria estandar `hashlib`) con un salt
    aleatorio por usuario. NUNCA se guarda la contrasena en texto plano.
"""

import streamlit as st

import database as db
# La logica de encriptacion/validacion vive en security.py (compartida con la
# version NiceGUI) para no duplicarla.
from security import (  # noqa: F401
    crear_hash,
    email_valido,
    generar_codigo,
    verificar_password,
)


# ---------------------------------------------------------------------------
# Estado de sesion de autenticacion
# ---------------------------------------------------------------------------

def init_auth_state() -> None:
    """Inicializa las llaves de sesion relacionadas con autenticacion."""
    st.session_state.setdefault("autenticado", False)
    st.session_state.setdefault("usuario", None)          # dict del usuario logueado
    st.session_state.setdefault("vista_auth", "login")    # login | registro | recuperar
    st.session_state.setdefault("codigo_pendiente", None) # codigo de verificacion
    st.session_state.setdefault("datos_pendientes", None) # datos del registro a confirmar


def usuario_actual() -> dict | None:
    return st.session_state.get("usuario")


def cerrar_sesion() -> None:
    """Cierra la sesion del usuario y limpia su informacion."""
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = None
    st.session_state["vista_auth"] = "login"
    st.rerun()


# ---------------------------------------------------------------------------
# Vistas de la compuerta de acceso
# ---------------------------------------------------------------------------

def _vista_login():
    st.subheader("🔐 Iniciar Sesión")
    with st.form("form_login"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        enviado = st.form_submit_button("Entrar", use_container_width=True)

    if enviado:
        user = db.obtener_usuario(email)
        if not user:
            st.error("No existe una cuenta con ese correo.")
        elif not user["verificado"]:
            st.warning("Tu cuenta aún no ha sido verificada. Revisa tu correo / código.")
        elif verificar_password(password, user["salt"], user["password_hash"]):
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = user
            st.success(f"¡Bienvenido, {user['nombre']}!")
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    col1, col2 = st.columns(2)
    if col1.button("Crear cuenta nueva", use_container_width=True):
        st.session_state["vista_auth"] = "registro"
        st.rerun()
    if col2.button("¿Olvidaste tu contraseña?", use_container_width=True):
        st.session_state["vista_auth"] = "recuperar"
        st.rerun()


def _vista_registro():
    st.subheader("📝 Crear Cuenta")

    # Paso 2: si ya hay un codigo pendiente, pedimos la verificacion del correo
    if st.session_state.get("codigo_pendiente"):
        _vista_verificacion()
        return

    with st.form("form_registro"):
        nombre = st.text_input("Nombre completo")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        confirmar = st.text_input("Confirmar contraseña", type="password")
        foto = st.file_uploader("Foto de perfil (png/jpg)", type=["png", "jpg", "jpeg"])
        enviado = st.form_submit_button("Registrarme", use_container_width=True)

    if enviado:
        # Validaciones de formulario
        if not nombre or not email or not password:
            st.error("Completa todos los campos obligatorios.")
        elif not email_valido(email):
            st.error("El correo no tiene un formato válido.")
        elif db.existe_email(email):
            st.error("Ya existe una cuenta con ese correo.")
        elif password != confirmar:
            st.error("Las contraseñas no coinciden.")
        elif len(password) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        else:
            # Guardamos los datos del registro en sesion hasta verificar el correo
            foto_bytes = foto.read() if foto is not None else None
            codigo = generar_codigo()
            st.session_state["datos_pendientes"] = {
                "nombre": nombre,
                "email": email,
                "password": password,
                "foto": foto_bytes,
            }
            st.session_state["codigo_pendiente"] = codigo
            st.rerun()

    if st.button("⬅ Volver a inicio de sesión"):
        st.session_state["vista_auth"] = "login"
        st.rerun()


def _vista_verificacion():
    """Verificacion de correo: el usuario ingresa el codigo recibido."""
    st.info("📧 **Verificación de correo**")
    # SIMULACION: en produccion el codigo se enviaria por email.
    st.code(f"Código de verificación (simulado): {st.session_state['codigo_pendiente']}")

    with st.form("form_verificacion"):
        codigo = st.text_input("Ingresa el código de 6 dígitos")
        enviado = st.form_submit_button("Verificar y activar cuenta", use_container_width=True)

    if enviado:
        if codigo.strip() == st.session_state["codigo_pendiente"]:
            datos = st.session_state["datos_pendientes"]
            salt, pwd_hash = crear_hash(datos["password"])
            ok = db.crear_usuario(
                nombre=datos["nombre"],
                email=datos["email"],
                password_hash=pwd_hash,
                salt=salt,
                foto=datos["foto"],
                verificado=1,  # cuenta activada tras verificar
            )
            if ok:
                st.success("¡Cuenta verificada y creada! Ya puedes iniciar sesión.")
                # Limpieza del flujo de registro
                st.session_state["codigo_pendiente"] = None
                st.session_state["datos_pendientes"] = None
                st.session_state["vista_auth"] = "login"
                st.rerun()
            else:
                st.error("No se pudo crear la cuenta (correo duplicado).")
        else:
            st.error("Código incorrecto. Intenta de nuevo.")

    if st.button("Cancelar registro"):
        st.session_state["codigo_pendiente"] = None
        st.session_state["datos_pendientes"] = None
        st.session_state["vista_auth"] = "login"
        st.rerun()


def _vista_recuperar():
    st.subheader("🔑 Recuperar Contraseña")

    # Paso 2: ya se genero un token -> permitir restablecer
    if st.session_state.get("codigo_pendiente") and st.session_state.get("datos_pendientes"):
        st.info("Ingresa el código enviado y tu nueva contraseña.")
        st.code(f"Token de recuperación (simulado): {st.session_state['codigo_pendiente']}")
        with st.form("form_reset"):
            codigo = st.text_input("Código de recuperación")
            nueva = st.text_input("Nueva contraseña", type="password")
            confirmar = st.text_input("Confirmar nueva contraseña", type="password")
            enviado = st.form_submit_button("Restablecer contraseña", use_container_width=True)

        if enviado:
            if codigo.strip() != st.session_state["codigo_pendiente"]:
                st.error("Código incorrecto.")
            elif nueva != confirmar:
                st.error("Las contraseñas no coinciden.")
            elif len(nueva) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres.")
            else:
                email = st.session_state["datos_pendientes"]["email"]
                salt, pwd_hash = crear_hash(nueva)
                db.actualizar_password(email, pwd_hash, salt)
                st.success("Contraseña actualizada. Ya puedes iniciar sesión.")
                st.session_state["codigo_pendiente"] = None
                st.session_state["datos_pendientes"] = None
                st.session_state["vista_auth"] = "login"
                st.rerun()
        return

    # Paso 1: pedir el correo
    with st.form("form_recuperar"):
        email = st.text_input("Correo de la cuenta")
        enviado = st.form_submit_button("Enviar código de recuperación", use_container_width=True)

    if enviado:
        if db.existe_email(email):
            st.session_state["codigo_pendiente"] = generar_codigo()
            st.session_state["datos_pendientes"] = {"email": email}
            st.rerun()
        else:
            st.error("No existe una cuenta con ese correo.")

    if st.button("⬅ Volver a inicio de sesión"):
        st.session_state["codigo_pendiente"] = None
        st.session_state["datos_pendientes"] = None
        st.session_state["vista_auth"] = "login"
        st.rerun()


def render_compuerta_acceso() -> None:
    """
    Renderiza la pantalla de autenticacion (login/registro/recuperacion).
    Debe llamarse cuando el usuario NO esta autenticado.
    """
    st.title("🛍️ Sistema de Segmentación Inteligente de Clientes")
    st.caption("Accede o crea una cuenta para utilizar el sistema.")

    vista = st.session_state.get("vista_auth", "login")
    if vista == "registro":
        _vista_registro()
    elif vista == "recuperar":
        _vista_recuperar()
    else:
        _vista_login()


def render_perfil_sidebar() -> None:
    """Muestra foto, nombre y boton de cerrar sesion en el sidebar."""
    user = usuario_actual()
    if not user:
        return
    with st.sidebar:
        if user.get("foto"):
            st.image(user["foto"], width=110)
        st.markdown(f"### 👋 {user['nombre']}")
        st.caption(user["email"])
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()
        st.divider()
