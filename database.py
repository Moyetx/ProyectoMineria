"""
database.py
-----------
Capa de acceso a datos (SQLite) para usuarios del sistema.

Responsabilidades:
  - Crear la base de datos / tabla de usuarios si no existe.
  - Insertar, consultar y actualizar usuarios.
  - Guardar la foto de perfil como BLOB (bytes) directamente en la tabla.

NO contiene logica de negocio de autenticacion (eso vive en auth.py); aqui
solo hay operaciones CRUD puras sobre SQLite.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
import os

# La base de datos se crea junto al proyecto.
DB_PATH = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent))) / "usuarios.db"


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexion SQLite con filas accesibles por nombre de columna."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acceder a las columnas por nombre
    return conn


def init_db() -> None:
    """Crea la tabla de usuarios si todavia no existe."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre        TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,   -- contrasena encriptada (PBKDF2)
                salt          TEXT    NOT NULL,   -- salt aleatorio por usuario
                foto          BLOB,               -- imagen de perfil en bytes
                verificado    INTEGER NOT NULL DEFAULT 0,  -- 0 = pendiente, 1 = activo
                creado_en     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def crear_usuario(
    nombre: str,
    email: str,
    password_hash: str,
    salt: str,
    foto: Optional[bytes] = None,
    verificado: int = 0,
) -> bool:
    """Inserta un nuevo usuario. Devuelve False si el email ya existe."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO usuarios (nombre, email, password_hash, salt, foto, verificado)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (nombre, email.lower().strip(), password_hash, salt, foto, verificado),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Violacion de UNIQUE -> el correo ya esta registrado
        return False


def obtener_usuario(email: str) -> Optional[Dict[str, Any]]:
    """Devuelve el usuario como dict o None si no existe."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def existe_email(email: str) -> bool:
    """True si el correo ya esta registrado."""
    return obtener_usuario(email) is not None


def marcar_verificado(email: str) -> None:
    """Activa la cuenta (verificacion de correo completada)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET verificado = 1 WHERE email = ?",
            (email.lower().strip(),),
        )
        conn.commit()


def actualizar_password(email: str, password_hash: str, salt: str) -> None:
    """Reemplaza la contrasena (usado en recuperacion de contrasena)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ?, salt = ? WHERE email = ?",
            (password_hash, salt, email.lower().strip()),
        )
        conn.commit()
