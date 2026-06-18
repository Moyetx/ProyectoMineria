"""Modulo 6 (NiceGUI): Visualizacion (PCA, perfilado, radar) y Exportacion.

Permite descargar:
  - el CSV con la columna 'Cluster' asignada a cada cliente, y
  - un REPORTE HTML autocontenido con metricas, tablas y graficos.
"""

from datetime import datetime

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
    ui.label("La columna 'Tamaño' = cuántos clientes cumplen ese perfil.").classes(
        "text-sm text-gray-600")

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
    with ui.row().classes("gap-3"):
        csv = df.to_csv(index=False).encode("utf-8")
        ui.button("Descargar CSV (con columna 'Cluster')",
                  on_click=lambda: ui.download.content(csv, "clientes_segmentados.csv")
                  ).props("color=primary")

        ui.button("Descargar reporte (HTML)",
                  on_click=lambda: ui.download.content(
                      _generar_reporte(df, nombre, feats),
                      "reporte_segmentacion.html")
                  ).props("color=secondary outline")


# --------------------------------------------------------------------------- reporte
def _generar_reporte(df: pd.DataFrame, nombre: str, feats: list) -> bytes:
    """Construye un reporte HTML autocontenido con métricas, tablas y gráficos."""
    p = state.pipe()
    resultados = p.get("resultados", {})
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    n_filas, n_cols = df.shape
    escalado = "Sí" if p.get("escalado_aplicado") else "No"

    # --- Gráfico 1: distribución por clúster ---
    conteo = df["Cluster"].value_counts().sort_index()
    fig_dist = px.bar(x=conteo.index.astype(str), y=conteo.values,
                      labels={"x": "Clúster", "y": "Clientes"},
                      title="Distribución de clientes por clúster")

    # --- Gráfico 2: PCA 2D ---
    pca = PCA(n_components=2, random_state=42)
    comps = pca.fit_transform(df[feats].values)
    var = pca.explained_variance_ratio_.sum() * 100
    pdf = df.copy()
    pdf["Cluster"] = pdf["Cluster"].astype(str)
    pdf["PC1"], pdf["PC2"] = comps[:, 0], comps[:, 1]
    fig_pca = px.scatter(pdf, x="PC1", y="PC2", color="Cluster", opacity=0.75,
                         title=f"Proyección PCA 2D — varianza explicada {var:.1f}%")

    # --- Gráfico 3: radar de centroides ---
    cent = df.groupby("Cluster")[feats].mean()
    norm = pd.DataFrame(MinMaxScaler().fit_transform(cent), columns=feats, index=cent.index)
    fig_radar = go.Figure()
    for cl in norm.index:
        vals = norm.loc[cl].tolist()
        fig_radar.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=feats + [feats[0]],
                                            fill="toself", name=f"Clúster {cl}"))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                            title="Radar de centroides (normalizado)")

    # --- Tabla de perfilado ---
    perfil = df.groupby("Cluster")[feats].mean().round(2)
    perfil["Tamaño"] = df.groupby("Cluster").size()
    tabla_perfil = perfil.reset_index().to_html(index=False, border=0, classes="tbl")

    # --- Tabla de métricas ---
    if resultados:
        filas = [{
            "Modelo": "K-Means" if n == "kmeans" else "Jerárquico",
            "Clústers": i.get("k"),
            "Silhouette": i.get("silhouette"),
            "Davies-Bouldin": i.get("davies_bouldin"),
            "Calinski-Harabasz": i.get("calinski_harabasz"),
            "Muestras": i.get("n_muestras"),
        } for n, i in resultados.items()]
        tabla_metricas = pd.DataFrame(filas).to_html(index=False, border=0, classes="tbl")
    else:
        tabla_metricas = "<p>No hay métricas registradas.</p>"

    # --- Resumen textual por clúster ---
    items = []
    for cl in perfil.index:
        tam = int(perfil.loc[cl, "Tamaño"])
        destacada = norm.loc[cl].idxmax()  # variable más alta (normalizada)
        items.append(f"<li><b>Clúster {cl}</b>: {tam} clientes; "
                     f"destaca en <b>{destacada}</b>.</li>")
    resumen = "<ul>" + "".join(items) + "</ul>"

    # --- Figuras a HTML (plotly.js se carga una sola vez por CDN) ---
    div_dist = fig_dist.to_html(full_html=False, include_plotlyjs="cdn")
    div_pca = fig_pca.to_html(full_html=False, include_plotlyjs=False)
    div_radar = fig_radar.to_html(full_html=False, include_plotlyjs=False)

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Reporte de Segmentación de Clientes</title>
<style>
  body{{font-family:"Segoe UI",Arial,sans-serif;color:#1f2933;max-width:980px;
       margin:0 auto;padding:24px;line-height:1.55}}
  h1{{color:#0d47a1}} h2{{color:#1565c0;border-bottom:2px solid #e3f2fd;padding-bottom:4px;margin-top:28px}}
  .meta{{background:#f4f7fb;border:1px solid #e0e6ed;border-radius:10px;padding:14px 18px}}
  .meta b{{color:#0d47a1}}
  table.tbl{{border-collapse:collapse;width:100%;margin:10px 0;font-size:.95rem}}
  table.tbl th,table.tbl td{{border:1px solid #e0e6ed;padding:7px 10px;text-align:center}}
  table.tbl th{{background:#eef4fb;color:#0d47a1}}
  footer{{color:#90a4ae;font-size:.85rem;margin-top:30px;text-align:center}}
</style></head><body>
<h1>Reporte de Segmentación de Clientes</h1>
<div class="meta">
  <p><b>Fecha:</b> {fecha}</p>
  <p><b>Modelo activo:</b> {nombre}</p>
  <p><b>Clientes analizados:</b> {n_filas:,} &nbsp;|&nbsp; <b>Columnas:</b> {n_cols}</p>
  <p><b>Variables usadas:</b> {", ".join(feats)}</p>
  <p><b>Escalamiento aplicado:</b> {escalado}</p>
</div>

<h2>1. Métricas de evaluación</h2>
<p>Silhouette y Calinski-Harabasz: más alto es mejor. Davies-Bouldin: más bajo es mejor.</p>
{tabla_metricas}

<h2>2. Resumen de segmentos</h2>
{resumen}

<h2>3. Distribución de clientes por clúster</h2>
{div_dist}

<h2>4. Proyección PCA (2D)</h2>
{div_pca}

<h2>5. Perfilado de clústers</h2>
<p>Promedio de cada variable por grupo y tamaño (clientes que cumplen el perfil).</p>
{tabla_perfil}

<h2>6. Radar de centroides</h2>
{div_radar}

<footer>Generado por el Sistema de Segmentación Inteligente de Clientes</footer>
</body></html>"""
    return html.encode("utf-8")