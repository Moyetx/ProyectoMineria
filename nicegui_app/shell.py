"""
nicegui_app/shell.py
-------------------
Estructura principal tras iniciar sesion: cabecera, drawer lateral con el
perfil del usuario + menu de navegacion, y area de contenido que cambia entre
las 6 secciones SIN recargar la pagina (gracias a @ui.refreshable).
"""

from nicegui import app, ui

from nicegui_app import (
    auth_ui,
    sec_carga,
    sec_evaluacion,
    sec_modelos,
    sec_preproceso,
    sec_variables,
    sec_visualizacion,
    state,
    theme,
)

# clave de seccion -> (etiqueta, funcion render)
SECCIONES = {
    "carga": ("1. Cargar Datos", sec_carga.render),
    "preproceso": ("2. Preprocesamiento", sec_preproceso.render),
    "variables": ("3. Selección de Variables", sec_variables.render),
    "modelos": ("4. Modelos de Clustering", sec_modelos.render),
    "evaluacion": ("5. Evaluación", sec_evaluacion.render),
    "visualizacion": ("6. Visualización y Exportación", sec_visualizacion.render),
}


def build_shell() -> None:
    user = app.storage.user

    # Aplica el tema guardado y obtiene el control de modo oscuro.
    dark = theme.aplicar_tema_guardado()

    with ui.header().classes("items-center justify-between"):
        ui.label("Sistema de Segmentación de Clientes").classes("text-lg font-bold")
        with ui.row().classes("items-center gap-3"):
            # Estado del dataset (se mantiene actualizado con un timer)
            lbl_estado_top = ui.label()
            # Boton rapido de tema claro/oscuro (arriba a la derecha)
            theme.boton_toggle(dark)

    with ui.left_drawer().classes("gap-2") :
        # Perfil del usuario
        if user.get("foto"):
            ui.image(user["foto"]).classes("w-24 h-24 rounded-full mx-auto object-cover")
        ui.label(f"{user.get('nombre', '')}").classes("text-lg font-semibold text-center")
        ui.label(user.get("email", "")).classes("text-xs text-gray-500 text-center")
        ui.button("Cerrar Sesión", on_click=auth_ui.logout_usuario).props("flat").classes("w-full")

        # Selector de tema (Sistema / Claro / Oscuro / Azul / Amarillo)
        theme.selector(dark)
        ui.separator()

        # Navegacion entre secciones
        def ir_a(clave):
            state.pipe()["seccion"] = clave
            contenido.refresh()

        for clave, (etiqueta, _) in SECCIONES.items():
            ui.button(etiqueta, on_click=lambda c=clave: ir_a(c)).props("flat align=left").classes("w-full")

        ui.separator()
        ui.label("Estado").classes("text-xs font-semibold")
        lbl_estado_drawer = ui.label().classes("text-xs text-gray-600")

    # Mantiene vivos los dos indicadores de estado (cabecera y drawer).
    # Los labels eran estaticos: por eso seguian diciendo "Sin datos cargados".
    def _refrescar_estado():
        txt = state.estado_dataset_texto()
        lbl_estado_top.set_text(txt)
        lbl_estado_drawer.set_text(txt)

    _refrescar_estado()
    ui.timer(1.0, _refrescar_estado)

    @ui.refreshable
    def contenido():
        clave = state.pipe().get("seccion", "carga")
        with ui.column().classes("w-full gap-3 p-2"):
            SECCIONES[clave][1]()

    contenido()