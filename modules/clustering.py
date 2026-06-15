"""
modules/clustering.py
---------------------
Modulo 5 de la especificacion: Modelos de Clustering.

  K-MEANS:
    - Slider para el rango de K.
    - Grafico del Metodo del Codo (inertia) interactivo.
    - Input para K definitivo y boton "Entrenar K-Means".

  CLUSTERING JERARQUICO:
    - Seleccion de linkage (ward, complete, average).
    - Dendrograma con scipy.
    - Corte del arbol (numero de clusters) y entrenamiento.
    - MUESTREO OBLIGATORIO: maximo 2,000 filas para el entrenamiento jerarquico
      y el dendrograma, para evitar MemoryError en datasets grandes.

Las etiquetas resultantes se guardan en `state` para evaluacion/visualizacion.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score

from modules import state

# Limite de filas para el clustering jerarquico (evita MemoryError)
MAX_FILAS_JERARQUICO = 2000


def _construir_X():
    """Devuelve la matriz numerica (features seleccionadas) sin nulos."""
    df = state.get_df()
    features = st.session_state.get("features", [])
    if df is None or len(features) < 2:
        return None
    X = df[features].dropna()
    return X


# ---------------------------------------------------------------------------
# K-MEANS
# ---------------------------------------------------------------------------
def _seccion_kmeans(X):
    st.subheader("🎯 K-Means")

    k_min, k_max = st.slider(
        "Rango de K a evaluar (Método del Codo)",
        min_value=2,
        max_value=15,
        value=(2, 10),
        key="rango_k",
    )

    if st.button("📈 Calcular Método del Codo (Inertia)"):
        ks = list(range(k_min, k_max + 1))
        inertias, silhouettes = [], []
        barra = st.progress(0.0)
        for i, k in enumerate(ks):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            inertias.append(km.inertia_)
            silhouettes.append(silhouette_score(X, labels))
            barra.progress((i + 1) / len(ks))
        barra.empty()
        # Guardamos para no recalcular al cambiar de pestana
        st.session_state["codo_ks"] = ks
        st.session_state["codo_inertias"] = inertias
        st.session_state["codo_silhouettes"] = silhouettes

    # Grafico del codo (si ya se calculo)
    if st.session_state.get("codo_ks"):
        ks = st.session_state["codo_ks"]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=ks, y=st.session_state["codo_inertias"],
                       mode="lines+markers", name="Inertia")
        )
        fig.update_layout(
            title="Método del Codo (Inertia vs K)",
            xaxis_title="Número de clústers (K)",
            yaxis_title="Inertia (WCSS)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tambien mostramos silhouette por K como ayuda a la decision
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(x=ks, y=st.session_state["codo_silhouettes"],
                       mode="lines+markers", name="Silhouette", line=dict(color="green"))
        )
        fig2.update_layout(
            title="Silhouette Score vs K",
            xaxis_title="Número de clústers (K)",
            yaxis_title="Silhouette Score",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Entrenamiento final
    k_def = st.number_input(
        "K definitivo para entrenar", min_value=2, max_value=20, value=4, key="k_def"
    )
    if st.button("🚀 Entrenar K-Means", type="primary"):
        km = KMeans(n_clusters=int(k_def), random_state=42, n_init=10)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)

        # Guardamos etiquetas alineadas al indice de X (que pudo perder filas por dropna)
        st.session_state["labels_kmeans"] = (X.index, labels)
        st.session_state["modelo_activo"] = "kmeans"
        st.session_state["resultados"]["kmeans"] = {
            "k": int(k_def),
            "silhouette": round(float(sil), 4),
            "n_muestras": len(X),
            "centroides": km.cluster_centers_,
        }
        st.success(f"✅ K-Means entrenado con K={int(k_def)} | Silhouette = {sil:.4f}")


# ---------------------------------------------------------------------------
# CLUSTERING JERARQUICO
# ---------------------------------------------------------------------------
def _seccion_jerarquico(X):
    st.subheader("🌳 Clustering Jerárquico")

    # MUESTREO OBLIGATORIO para evitar MemoryError
    if len(X) > MAX_FILAS_JERARQUICO:
        X_h = X.sample(MAX_FILAS_JERARQUICO, random_state=42)
        st.warning(
            f"El dataset tiene {len(X):,} filas. Se aplica un muestreo aleatorio de "
            f"{MAX_FILAS_JERARQUICO:,} filas para el dendrograma y el entrenamiento "
            "jerárquico (evita MemoryError)."
        )
    else:
        X_h = X

    linkage_metodo = st.selectbox(
        "Método de linkage", ["ward", "complete", "average"], key="linkage_metodo"
    )

    if st.button("🌲 Renderizar Dendrograma"):
        Z = linkage(X_h.values, method=linkage_metodo)
        st.session_state["dendro_Z"] = Z
        st.session_state["dendro_index"] = X_h.index

    if st.session_state.get("dendro_Z") is not None:
        Z = st.session_state["dendro_Z"]
        # Dendrograma con scipy -> lo dibujamos con matplotlib
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 4))
        dendrogram(Z, truncate_mode="lastp", p=30, ax=ax, no_labels=True)
        ax.set_title(f"Dendrograma (linkage={linkage_metodo})")
        ax.set_xlabel("Muestras (truncado)")
        ax.set_ylabel("Distancia")
        st.pyplot(fig)

    n_clusters = st.number_input(
        "Número de clústers (corte del árbol)",
        min_value=2, max_value=20, value=4, key="n_clusters_jerarquico",
    )
    if st.button("🚀 Entrenar Clustering Jerárquico", type="primary"):
        modelo = AgglomerativeClustering(
            n_clusters=int(n_clusters), linkage=linkage_metodo
        )
        labels = modelo.fit_predict(X_h)
        sil = silhouette_score(X_h, labels)

        st.session_state["labels_jerarquico"] = (X_h.index, labels)
        st.session_state["modelo_activo"] = "jerarquico"
        st.session_state["resultados"]["jerarquico"] = {
            "k": int(n_clusters),
            "linkage": linkage_metodo,
            "silhouette": round(float(sil), 4),
            "n_muestras": len(X_h),
        }
        st.success(
            f"✅ Jerárquico entrenado | clusters={int(n_clusters)} | "
            f"linkage={linkage_metodo} | Silhouette = {sil:.4f}"
        )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def render() -> None:
    st.header("4️⃣ Modelos de Clustering")

    X = _construir_X()
    if X is None:
        st.warning(
            "Selecciona al menos 2 features en la sección 'Selección de Variables' "
            "y asegúrate de haber escalado los datos."
        )
        return

    if not st.session_state.get("escalado_aplicado"):
        st.info(
            "💡 Recomendación: aplica escalamiento en Preprocesamiento antes de "
            "entrenar (el clustering por distancias lo requiere)."
        )

    st.caption(f"Matriz de entrenamiento: {X.shape[0]:,} filas × {X.shape[1]} features")

    tab_k, tab_h = st.tabs(["K-Means", "Clustering Jerárquico"])
    with tab_k:
        _seccion_kmeans(X)
    with tab_h:
        _seccion_jerarquico(X)
