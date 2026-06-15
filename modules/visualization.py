"""
modules/visualization.py
------------------------
Modulo 7 de la especificacion: Visualizacion y Exportacion.

  - Proyeccion espacial con PCA (2D o 3D) y scatter interactivo coloreado por cluster.
  - Perfilado de negocio: media de cada variable por cluster + Radar Chart de centroides.
  - Descarga del dataset final con la columna "Cluster".
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

from modules import state


def _obtener_labels():
    """Devuelve (indices, labels, nombre) del modelo activo, o None."""
    activo = st.session_state.get("modelo_activo")
    if activo == "kmeans" and st.session_state.get("labels_kmeans"):
        idx, labels = st.session_state["labels_kmeans"]
        return idx, labels, "K-Means"
    if activo == "jerarquico" and st.session_state.get("labels_jerarquico"):
        idx, labels = st.session_state["labels_jerarquico"]
        return idx, labels, "Jerárquico"
    return None


def _df_con_clusters():
    """DataFrame de trabajo + columna 'Cluster' alineada por indice."""
    res = _obtener_labels()
    if res is None:
        return None, None
    idx, labels, nombre = res
    df = state.get_df().copy()
    df = df.loc[idx]  # nos quedamos con las filas que recibieron etiqueta
    df["Cluster"] = labels
    return df, nombre


def _proyeccion_pca(df, features):
    st.subheader("🌐 Proyección Espacial (PCA)")
    dim = st.radio("Dimensiones de proyección", ["2D", "3D"], horizontal=True)
    n_comp = 2 if dim == "2D" else 3

    X = df[features].values
    pca = PCA(n_components=n_comp, random_state=42)
    comps = pca.fit_transform(X)
    var_exp = pca.explained_variance_ratio_.sum() * 100

    plot_df = df.copy()
    plot_df["PC1"], plot_df["PC2"] = comps[:, 0], comps[:, 1]
    plot_df["Cluster"] = plot_df["Cluster"].astype(str)

    if n_comp == 2:
        fig = px.scatter(
            plot_df, x="PC1", y="PC2", color="Cluster",
            title=f"Proyección PCA 2D — varianza explicada: {var_exp:.1f}%",
            opacity=0.75,
        )
    else:
        plot_df["PC3"] = comps[:, 2]
        fig = px.scatter_3d(
            plot_df, x="PC1", y="PC2", z="PC3", color="Cluster",
            title=f"Proyección PCA 3D — varianza explicada: {var_exp:.1f}%",
            opacity=0.75,
        )
    st.plotly_chart(fig, use_container_width=True)


def _perfilado(df, features):
    st.subheader("🧩 Perfilado de Clústers (Business Insights)")

    # Media de cada variable agrupada por cluster
    perfil = df.groupby("Cluster")[features].mean().round(2)
    perfil["Tamaño"] = df.groupby("Cluster").size()
    st.markdown("**Media de cada variable por clúster:**")
    st.dataframe(perfil, use_container_width=True)

    # Radar Chart de los centroides (normalizado 0-1 para comparar en una escala)
    st.markdown("**Radar Chart de centroides (valores normalizados 0-1):**")
    centroides = df.groupby("Cluster")[features].mean()
    norm = MinMaxScaler().fit_transform(centroides)
    norm = pd.DataFrame(norm, columns=features, index=centroides.index)

    fig = go.Figure()
    for cluster in norm.index:
        valores = norm.loc[cluster].tolist()
        fig.add_trace(
            go.Scatterpolar(
                r=valores + [valores[0]],          # cerrar el poligono
                theta=features + [features[0]],
                fill="toself",
                name=f"Clúster {cluster}",
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Perfil de centroides por clúster",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    st.header("6️⃣ Visualización y Exportación")

    resultado = _df_con_clusters()
    if resultado[0] is None:
        st.warning("Entrena un modelo de clustering para visualizar resultados.")
        return

    df, nombre = resultado
    features = st.session_state.get("features", [])
    features = [f for f in features if f in df.columns]
    if len(features) < 2:
        st.warning("Se requieren al menos 2 features para la visualización.")
        return

    st.caption(f"Visualizando resultados del modelo: **{nombre}**")

    # Distribucion de clusters
    conteo = df["Cluster"].value_counts().sort_index()
    fig_dist = px.bar(
        x=conteo.index.astype(str), y=conteo.values,
        labels={"x": "Clúster", "y": "Número de clientes"},
        title="Distribución de clientes por clúster",
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    _proyeccion_pca(df, features)
    _perfilado(df, features)

    # --- Descarga ---
    st.subheader("💾 Descargar Resultados")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar dataset con columna 'Cluster'",
        data=csv,
        file_name="clientes_segmentados.csv",
        mime="text/csv",
        type="primary",
    )
