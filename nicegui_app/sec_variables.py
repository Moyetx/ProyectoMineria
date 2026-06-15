"""Modulo 3 (NiceGUI): Seleccion y Exploracion de Variables."""

import pandas as pd
import plotly.express as px
from nicegui import ui

from nicegui_app import state


def render() -> None:
    ui.label("3. Selección y Exploración de Variables").classes("text-2xl font-bold")

    df = state.get_df()
    if df is None:
        ui.label("Primero carga y limpia un dataset.").classes("text-gray-500"); return

    cols = df.select_dtypes(include="number").columns.tolist()
    if len(cols) < 2:
        ui.label("Se necesitan ≥2 columnas numéricas (codifica las categóricas).").classes(
            "text-orange-600"); return

    # Matriz de correlacion
    ui.label("Matriz de Correlación").classes("text-lg font-semibold")
    corr = df[cols].corr().round(2)
    fig = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1, title="Correlación entre variables")
    ui.plotly(fig).classes("w-full")

    # Pares altamente correlacionados
    pares = [(cols[i], cols[j], corr.iloc[i, j])
             for i in range(len(cols)) for j in range(i + 1, len(cols))
             if abs(corr.iloc[i, j]) >= 0.85]
    if pares:
        ui.label("Pares con |r| ≥ 0.85:").classes("text-orange-600")
        ui.table.from_pandas(
            pd.DataFrame(pares, columns=["Var A", "Var B", "r"])
        ).classes("w-full")

    # Seleccion de features (se persiste en el estado del pipeline)
    ui.label("Features para el Modelo").classes("text-lg font-semibold mt-2")
    p = state.pipe()
    actuales = [f for f in (p.get("features") or
                            [c for c in cols if "id" not in c.lower()]) if f in cols]

    sel = ui.select(cols, value=actuales, multiple=True,
                   label="Variables que entran al clustering").classes("w-full").props("use-chips")

    info = ui.label().classes("text-sm")

    def guardar():
        p["features"] = list(sel.value)
        if len(p["features"]) < 2:
            info.set_text("Selecciona al menos 2 variables.")
            info.classes(replace="text-orange-600 text-sm")
        else:
            info.set_text(f"{len(p['features'])} variables guardadas: {', '.join(p['features'])}")
            info.classes(replace="text-green-600 text-sm")

    sel.on_value_change(lambda: guardar())
    guardar()
