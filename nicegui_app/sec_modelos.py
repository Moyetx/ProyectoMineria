"""
Modulo 4 (NiceGUI): Modelos de Clustering.
K-Means (metodo del codo) y Clustering Jerarquico (dendrograma + muestreo).

Al entrenar cada modelo se calculan TRES metricas de evaluacion:
  - Silhouette Score      (mas alto es mejor)
  - Davies-Bouldin Index  (mas bajo es mejor)
  - Calinski-Harabasz     (mas alto es mejor)
Se guardan en el estado para mostrarse en la seccion de Evaluacion.
"""

import plotly.graph_objects as go
from nicegui import ui
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

from nicegui_app import state

MAX_FILAS_JERARQUICO = 2000  # muestreo obligatorio para evitar MemoryError


def _construir_X():
    p = state.pipe()
    df, feats = p.get("df"), p.get("features", [])
    if df is None or len(feats) < 2:
        return None
    return df[feats].dropna()


def _metricas(X, labels) -> dict:
    """Calcula las tres metricas internas de clustering."""
    n = len(set(labels))
    if n < 2:
        return {"silhouette": float("nan"), "davies_bouldin": float("nan"),
                "calinski_harabasz": float("nan")}
    return {
        "silhouette": round(float(silhouette_score(X, labels)), 4),
        "davies_bouldin": round(float(davies_bouldin_score(X, labels)), 4),
        "calinski_harabasz": round(float(calinski_harabasz_score(X, labels)), 1),
    }


def render() -> None:
    ui.label("4. Modelos de Clustering").classes("text-2xl font-bold")

    X = _construir_X()
    if X is None:
        ui.label("Selecciona ≥2 features en 'Selección de Variables'.").classes("text-orange-600")
        return
    if not state.pipe().get("escalado_aplicado"):
        ui.label("Recomendado: aplica escalamiento antes de entrenar.").classes("text-blue-600")
    ui.label(f"Matriz: {X.shape[0]:,} filas × {X.shape[1]} features").classes("text-sm text-gray-500")

    with ui.tabs().classes("w-full") as tabs:
        t_k = ui.tab("K-Means")
        t_h = ui.tab("Jerárquico")
    with ui.tab_panels(tabs, value=t_k).classes("w-full"):
        with ui.tab_panel(t_k):
            _kmeans(X)
        with ui.tab_panel(t_h):
            _jerarquico(X)


# --------------------------------------------------------------------------- K-Means
def _kmeans(X):
    rango = {"min": 2, "max": 10}
    ui.label("Rango de K para el Método del Codo").classes("font-semibold")
    with ui.row().classes("items-center gap-4"):
        ui.number("K min", value=2, min=2, max=14,
                 on_change=lambda e: rango.update(min=int(e.value))).classes("w-24")
        ui.number("K max", value=10, min=3, max=15,
                 on_change=lambda e: rango.update(max=int(e.value))).classes("w-24")

    @ui.refreshable
    def graficos_codo():
        codo = state.pipe().get("codo")
        if not codo:
            return
        ks = codo["ks"]
        f1 = go.Figure(go.Scatter(x=ks, y=codo["inertias"], mode="lines+markers"))
        f1.update_layout(title="Método del Codo (Inertia vs K)",
                         xaxis_title="K", yaxis_title="Inertia (WCSS)")
        ui.plotly(f1).classes("w-full")
        f2 = go.Figure(go.Scatter(x=ks, y=codo["silhouettes"], mode="lines+markers",
                                  line=dict(color="green")))
        f2.update_layout(title="Silhouette vs K", xaxis_title="K", yaxis_title="Silhouette")
        ui.plotly(f2).classes("w-full")

    def calcular_codo():
        ks = list(range(rango["min"], rango["max"] + 1))
        inertias, sils = [], []
        for k in ks:
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
            inertias.append(km.inertia_)
            sils.append(silhouette_score(X, km.labels_))
        state.pipe()["codo"] = {"ks": ks, "inertias": inertias, "silhouettes": sils}
        graficos_codo.refresh()
        ui.notify("Método del codo calculado.", type="positive")

    ui.button("Calcular Método del Codo", on_click=calcular_codo)
    graficos_codo()

    ui.separator()
    k_def = ui.number("K definitivo", value=4, min=2, max=20).classes("w-32")

    def entrenar():
        km = KMeans(n_clusters=int(k_def.value), random_state=42, n_init=10).fit(X)
        m = _metricas(X, km.labels_)
        p = state.pipe()
        p["labels_kmeans"] = (X.index, km.labels_)
        p["modelo_activo"] = "kmeans"
        p["resultados"]["kmeans"] = {"k": int(k_def.value), "n_muestras": len(X), **m}
        ui.notify(
            f"K-Means entrenado | K={int(k_def.value)} | Silhouette={m['silhouette']} | "
            f"DB={m['davies_bouldin']} | CH={m['calinski_harabasz']}",
            type="positive",
        )

    ui.button("Entrenar K-Means", on_click=entrenar).props("color=primary")


# --------------------------------------------------------------------------- Jerarquico
def _jerarquico(X):
    if len(X) > MAX_FILAS_JERARQUICO:
        X_h = X.sample(MAX_FILAS_JERARQUICO, random_state=42)
        ui.label(
            f"{len(X):,} filas  se usa muestreo de {MAX_FILAS_JERARQUICO:,} "
            "para dendrograma y entrenamiento (evita MemoryError)."
        ).classes("text-orange-600")
    else:
        X_h = X

    metodo = ui.select(["ward", "complete", "average"], value="ward",
                      label="Método de linkage").classes("w-48")

    @ui.refreshable
    def dendro_panel():
        dd = state.pipe().get("dendro")
        if not dd:
            return
        # Dendrograma con scipy renderizado en matplotlib
        with ui.pyplot(figsize=(10, 4)):
            dendrogram(dd["Z"], truncate_mode="lastp", p=30, no_labels=True)
            import matplotlib.pyplot as plt
            plt.title(f"Dendrograma (linkage={dd['linkage']})")
            plt.xlabel("Muestras (truncado)"); plt.ylabel("Distancia")

    def render_dendro():
        Z = linkage(X_h.values, method=metodo.value)
        state.pipe()["dendro"] = {"Z": Z, "linkage": metodo.value}
        dendro_panel.refresh()

    ui.button("Renderizar Dendrograma", on_click=render_dendro)
    dendro_panel()

    ui.separator()
    n_clusters = ui.number("Número de clústers (corte)", value=4, min=2, max=20).classes("w-40")

    def entrenar():
        modelo = AgglomerativeClustering(n_clusters=int(n_clusters.value), linkage=metodo.value)
        labels = modelo.fit_predict(X_h)
        m = _metricas(X_h, labels)
        p = state.pipe()
        p["labels_jerarquico"] = (X_h.index, labels)
        p["modelo_activo"] = "jerarquico"
        p["resultados"]["jerarquico"] = {
            "k": int(n_clusters.value), "linkage": metodo.value,
            "n_muestras": len(X_h), **m,
        }
        ui.notify(
            f"Jerárquico entrenado | clusters={int(n_clusters.value)} | "
            f"Silhouette={m['silhouette']} | DB={m['davies_bouldin']} | "
            f"CH={m['calinski_harabasz']}",
            type="positive",
        )

    ui.button("Entrenar Clustering Jerárquico", on_click=entrenar).props("color=primary")
