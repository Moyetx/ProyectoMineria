"""
security.py
-----------
Utilidades de seguridad y validacion INDEPENDIENTES del framework de UI.

Se comparten entre la version Streamlit (auth.py) y la version NiceGUI
(nicegui_app/auth_ui.py) para no duplicar la logica de encriptacion.

  - Hashing de contrasenas con PBKDF2-HMAC-SHA256 + salt unico por usuario.
  - Validacion de correo.
  - Generacion de codigos de verificacion (simulacion de envio por email).
"""

import hashlib
import random
import re
import secrets

_PBKDF2_ITERATIONS = 200_000  # coste computacional del hashing


def _hash_password(password: str, salt: str) -> str:
    """Deriva el hash PBKDF2-HMAC-SHA256 de la contrasena con el salt dado."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _PBKDF2_ITERATIONS,
    )
    return dk.hex()


def crear_hash(password: str) -> tuple[str, str]:
    """Genera (salt, hash) nuevos para una contrasena en texto plano."""
    salt = secrets.token_hex(16)
    return salt, _hash_password(password, salt)


def verificar_password(password: str, salt: str, password_hash: str) -> bool:
    """Compara de forma segura la contrasena ingresada contra el hash guardado."""
    candidato = _hash_password(password, salt)
    # comparacion en tiempo constante para evitar timing attacks
    return secrets.compare_digest(candidato, password_hash)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_valido(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def generar_codigo() -> str:
    """Codigo de verificacion de 6 digitos (simulacion de envio por correo)."""
    return f"{random.randint(0, 999999):06d}"
