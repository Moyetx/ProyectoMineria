"""
Modulo 5 (NiceGUI): Evaluacion de Resultados.

Muestra TRES metricas internas de clustering para el modelo activo y una tabla
comparativa entre modelos:
  - Silhouette Score      (rango -1 a 1, mas alto es mejor)
  - Davies-Bouldin Index  (>= 0, mas bajo es mejor)
  - Calinski-Harabasz     (>= 0, mas alto es mejor)
"""

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from nicegui_app import state


def _gauge(valor: float, titulo: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor, title={"text": titulo},
        gauge={"axis": {"range": [-1, 1]}, "bar": {"color": "#1f77b4"},
               "steps": [{"range": [-1, 0.25], "color": "#ffcdd2"},
                         {"range": [0.25, 0.5], "color": "#fff9c4"},
                         {"range": [0.5, 1], "color": "#c8e6c9"}]}))
    fig.update_layout(height=300)
    return fig


def render() -> None:
    ui.label("5. Evaluación de Resultados").classes("text-2xl font-bold")

    resultados = state.pipe().get("resultados", {})
    if not resultados:
        ui.label("Entrena al menos un modelo.").classes("text-orange-600"); return

    ui.label(
        "Silhouette y Calinski-Harabasz: más alto es mejor.  "
        "Davies-Bouldin: más bajo es mejor."
    ).classes("text-sm text-gray-500")

    # --- Metricas del modelo activo ---
    activo = state.pipe().get("modelo_activo")
    if activo in resultados:
        info = resultados[activo]
        ui.label(f"Modelo activo: {activo.upper()}").classes("text-lg font-semibold")
        with ui.row().classes("items-center gap-6 w-full"):
            ui.plotly(_gauge(info.get("silhouette", 0), f"Silhouette ({activo})")).classes("w-96")
            with ui.column().classes("gap-1"):
                ui.label(f"Silhouette: {info.get('silhouette')}").classes("text-lg")
                ui.label(f"Davies-Bouldin: {info.get('davies_bouldin')}")
                ui.label(f"Calinski-Harabasz: {info.get('calinski_harabasz')}")
                ui.label(f"Clústers: {info.get('k')}  |  Muestras: {info.get('n_muestras')}")

    # --- Tabla comparativa ---
    ui.label("Comparativa de Modelos").classes("text-lg font-semibold mt-2")
    filas = [{
        "Modelo": "K-Means" if n == "kmeans" else "Jerárquico",
        "Clústers": i.get("k"),
        "Silhouette": i.get("silhouette"),
        "Davies-Bouldin": i.get("davies_bouldin"),
        "Calinski-Harabasz": i.get("calinski_harabasz"),
        "Muestras": i.get("n_muestras"),
        "Linkage": i.get("linkage", "—"),
    } for n, i in resultados.items()]
    tabla = pd.DataFrame(filas)
    ui.table.from_pandas(tabla).classes("w-full")

    if len(filas) >= 2:
        # Barras comparativas de Silhouette
        fig = go.Figure(go.Bar(x=tabla["Modelo"], y=tabla["Silhouette"],
                              marker_color=["#1f77b4", "#2ca02c"],
                              text=tabla["Silhouette"], textposition="auto"))
        fig.update_layout(title="Comparación de Silhouette Score", yaxis_title="Silhouette")
        ui.plotly(fig).classes("w-full")
        mejor = tabla.loc[tabla["Silhouette"].idxmax(), "Modelo"]
        ui.label(f"Mejor por Silhouette: {mejor}").classes("text-green-600 font-semibold")
