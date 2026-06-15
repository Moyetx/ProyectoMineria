"""
modules/evaluation.py
---------------------
Modulo 6 de la especificacion: Evaluacion de Resultados.

  - Silhouette Score del modelo actual (mostrado de forma grafica).
  - Tabla comparativa cuando se han corrido ambos modelos (K-Means vs Jerarquico).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules import state


def _gauge_silhouette(valor: float, titulo: str) -> go.Figure:
    """Indicador tipo gauge para visualizar el Silhouette Score (-1 a 1)."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=valor,
            title={"text": titulo},
            gauge={
                "axis": {"range": [-1, 1]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [-1, 0.25], "color": "#ffcdd2"},
                    {"range": [0.25, 0.5], "color": "#fff9c4"},
                    {"range": [0.5, 1], "color": "#c8e6c9"},
                ],
            },
        )
    )
    fig.update_layout(height=300)
    return fig


def render() -> None:
    st.header("5️⃣ Evaluación de Resultados")

    resultados = st.session_state.get("resultados", {})
    if not resultados:
        st.warning("Entrena al menos un modelo en la sección 'Modelos de Clustering'.")
        return

    # --- Silhouette del modelo activo ---
    activo = st.session_state.get("modelo_activo")
    if activo and activo in resultados:
        st.subheader(f"Silhouette Score — modelo activo: {activo.upper()}")
        sil = resultados[activo]["silhouette"]
        col1, col2 = st.columns([2, 1])
        with col1:
            st.plotly_chart(
                _gauge_silhouette(sil, f"Silhouette ({activo})"),
                use_container_width=True,
            )
        with col2:
            st.metric("Silhouette Score", sil)
            st.metric("Número de clústers", resultados[activo]["k"])
            st.metric("Muestras evaluadas", resultados[activo]["n_muestras"])
            st.caption(
                "Interpretación: cercano a **1** = clústers bien separados; "
                "cercano a **0** = solapados; **negativo** = mala asignación."
            )

    # --- Tabla comparativa (si hay ambos modelos) ---
    st.subheader("📋 Tabla Comparativa de Modelos")
    filas = []
    for nombre, info in resultados.items():
        filas.append(
            {
                "Modelo": "K-Means" if nombre == "kmeans" else "Jerárquico",
                "Clústers (K)": info["k"],
                "Silhouette Score": info["silhouette"],
                "Muestras": info["n_muestras"],
                "Linkage": info.get("linkage", "—"),
            }
        )
    tabla = pd.DataFrame(filas)
    st.dataframe(tabla, use_container_width=True)

    if len(filas) >= 2:
        # Grafico de barras comparando silhouette
        fig = go.Figure(
            go.Bar(
                x=tabla["Modelo"],
                y=tabla["Silhouette Score"],
                marker_color=["#1f77b4", "#2ca02c"],
                text=tabla["Silhouette Score"],
                textposition="auto",
            )
        )
        fig.update_layout(
            title="Comparación de Silhouette Score",
            yaxis_title="Silhouette Score",
        )
        st.plotly_chart(fig, use_container_width=True)

        mejor = tabla.loc[tabla["Silhouette Score"].idxmax(), "Modelo"]
        st.success(f"🏆 Mejor modelo por Silhouette Score: **{mejor}**")
