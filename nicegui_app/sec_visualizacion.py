"""Modulo 6 (NiceGUI): Visualizacion (PCA, perfilado, radar) y Exportacion."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nicegui import ui
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

from nicegui_app import state


def _df_con_clusters():
    p = state.pipe()
    activo = p.get("modelo_activo")
    if activo == "kmeans" and p.get("labels_kmeans"):
        idx, labels, nombre = *p["labels_kmeans"], "K-Means"
    elif activo == "jerarquico" and p.get("labels_jerarquico"):
        idx, labels, nombre = *p["labels_jerarquico"], "Jerárquico"
    else:
        return None, None
    df = state.get_df().loc[idx].copy()
    df["Cluster"] = labels
    return df, nombre


def render() -> None:
    ui.label("6. Visualización y Exportación").classes("text-2xl font-bold")

    df, nombre = _df_con_clusters()
    if df is None:
        ui.label("Entrena un modelo para visualizar resultados.").classes("text-orange-600")
        return

    feats = [f for f in state.pipe().get("features", []) if f in df.columns]
    if len(feats) < 2:
        ui.label("Se requieren ≥2 features.").classes("text-orange-600"); return

    ui.label(f"Modelo: {nombre}").classes("text-sm text-gray-500")

    # Distribucion por cluster
    conteo = df["Cluster"].value_counts().sort_index()
    ui.plotly(px.bar(x=conteo.index.astype(str), y=conteo.values,
                     labels={"x": "Clúster", "y": "Clientes"},
                     title="Distribución de clientes por clúster")).classes("w-full")

    # --- PCA ---
    ui.label("Proyección Espacial (PCA)").classes("text-lg font-semibold")
    dim = ui.radio(["2D", "3D"], value="2D").props("inline")

    @ui.refreshable
    def proyeccion():
        n = 2 if dim.value == "2D" else 3
        pca = PCA(n_components=n, random_state=42)
        comps = pca.fit_transform(df[feats].values)
        var = pca.explained_variance_ratio_.sum() * 100
        pdf = df.copy()
        pdf["Cluster"] = pdf["Cluster"].astype(str)
        pdf["PC1"], pdf["PC2"] = comps[:, 0], comps[:, 1]
        if n == 2:
            fig = px.scatter(pdf, x="PC1", y="PC2", color="Cluster", opacity=0.75,
                             title=f"PCA 2D — varianza explicada {var:.1f}%")
        else:
            pdf["PC3"] = comps[:, 2]
            fig = px.scatter_3d(pdf, x="PC1", y="PC2", z="PC3", color="Cluster",
                                opacity=0.75, title=f"PCA 3D — varianza {var:.1f}%")
        ui.plotly(fig).classes("w-full")

    dim.on_value_change(lambda: proyeccion.refresh())
    proyeccion()

    # --- Perfilado ---
    ui.label("Perfilado de Clústers").classes("text-lg font-semibold mt-2")
    perfil = df.groupby("Cluster")[feats].mean().round(2)
    perfil["Tamaño"] = df.groupby("Cluster").size()
    ui.table.from_pandas(perfil.reset_index()).classes("w-full")

    # Radar de centroides (normalizado 0-1)
    cent = df.groupby("Cluster")[feats].mean()
    norm = pd.DataFrame(MinMaxScaler().fit_transform(cent), columns=feats, index=cent.index)
    radar = go.Figure()
    for cl in norm.index:
        vals = norm.loc[cl].tolist()
        radar.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=feats + [feats[0]],
                                        fill="toself", name=f"Clúster {cl}"))
    radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                        title="Radar de centroides (normalizado)", showlegend=True)
    ui.plotly(radar).classes("w-full")

    # --- Descarga ---
    ui.label("Descargar").classes("text-lg font-semibold mt-2")
    csv = df.to_csv(index=False).encode("utf-8")
    ui.button("Descargar CSV con columna 'Cluster'",
              on_click=lambda: ui.download.content(csv, "clientes_segmentados.csv")
              ).props("color=primary")
