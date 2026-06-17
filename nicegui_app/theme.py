"""
nicegui_app/theme.py
--------------------
Gestion de temas de la interfaz: Sistema, Claro, Oscuro, Azul y Amarillo.

  - "Sistema"  -> sigue la preferencia del sistema operativo (dark/light auto).
  - "Claro"    -> modo claro con el color primario por defecto.
  - "Oscuro"   -> modo oscuro.
  - "Azul"     -> modo claro con acento azul.
  - "Amarillo" -> modo claro con acento amarillo.

El tema elegido se guarda en `app.storage.user` (cookie), asi que persiste
entre recargas y entre sesiones del mismo navegador.
"""

from nicegui import app, ui

TEMAS = ["Sistema", "Claro", "Oscuro", "Azul", "Amarillo"]

# Color primario por defecto de NiceGUI/Quasar.
_PRIMARIO_DEFECTO = "#5898d4"
# (dark_mode, color_primario) por tema. dark_mode: True=oscuro, False=claro, None=auto.
_CONFIG = {
    "Sistema":  (None,  _PRIMARIO_DEFECTO),
    "Claro":    (False, _PRIMARIO_DEFECTO),
    "Oscuro":   (True,  _PRIMARIO_DEFECTO),
    "Azul":     (False, "#1e66f5"),
    "Amarillo": (False, "#f5b400"),
}


def _tema_guardado() -> str:
    return app.storage.user.get("tema", "Sistema")


def aplicar(nombre: str, dark: ui.dark_mode) -> None:
    """Aplica el tema: ajusta el modo oscuro y el color primario."""
    modo, color = _CONFIG.get(nombre, _CONFIG["Sistema"])
    dark.value = modo
    ui.colors(primary=color)


def aplicar_tema_guardado() -> ui.dark_mode:
    """Crea el control de modo oscuro y aplica el tema guardado. Devuelve el dark_mode."""
    dark = ui.dark_mode()
    aplicar(_tema_guardado(), dark)
    return dark


def selector(dark: ui.dark_mode):
    """Selector de tema (para el sidebar). Persiste la eleccion y la aplica."""
    def on_change(e):
        app.storage.user["tema"] = e.value
        aplicar(e.value, dark)

    return ui.select(TEMAS, value=_tema_guardado(), label="Tema",
                     on_change=on_change).classes("w-full")


def _icono_toggle(dark: ui.dark_mode) -> str:
    # En oscuro mostramos un sol (para pasar a claro); en claro, una luna.
    return "light_mode" if dark.value else "dark_mode"


def boton_toggle(dark: ui.dark_mode):
    """Boton compacto (para la cabecera) que alterna rapido entre Claro y Oscuro."""
    btn = ui.button(icon=_icono_toggle(dark)).props("flat round color=white")

    def toggle():
        nuevo = "Claro" if dark.value else "Oscuro"
        app.storage.user["tema"] = nuevo
        aplicar(nuevo, dark)
        btn.props(f"icon={_icono_toggle(dark)}")

    btn.on("click", toggle)
    btn.tooltip("Cambiar tema claro/oscuro")
    return btn