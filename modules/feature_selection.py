"""
modules/feature_selection.py
----------------------------
Modulo 4 de la especificacion: Seleccion y Exploracion de Variables.

  - Multi-select para elegir las features finales que entran al modelo.
  - Matriz de correlacion (heatmap interactivo) para detectar multicolinealidad.

El conjunto de features elegido se guarda en `state` (clave 'features') y se
usa para construir la matriz `X_modelo` que alimentara al clustering.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from modules import state


def render() -> None:
    st.header("3️⃣ Selección y Exploración de Variables")

    df = state.get_df()
    if df is None:
        st.warning("Primero carga y limpia un dataset.")
        return

    cols_num = df.select_dtypes(include="number").columns.tolist()
    if len(cols_num) < 2:
        st.warning(
            "Se necesitan al menos 2 columnas numéricas. "
            "Codifica las categóricas en la sección de Preprocesamiento."
        )
        return

    # --- Matriz de correlacion ---
    st.subheader("📊 Matriz de Correlación")
    st.caption("Evita incluir variables muy correlacionadas (multicolinealidad).")
    corr = df[cols_num].corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlación entre variables numéricas",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Aviso de pares altamente correlacionados
    pares_altos = []
    for i in range(len(cols_num)):
        for j in range(i + 1, len(cols_num)):
            valor = corr.iloc[i, j]
            if abs(valor) >= 0.85:
                pares_altos.append((cols_num[i], cols_num[j], valor))
    if pares_altos:
        st.warning("⚠️ Pares con correlación alta (|r| ≥ 0.85):")
        st.table(
            pd.DataFrame(pares_altos, columns=["Variable A", "Variable B", "Correlación"])
        )

    # --- Seleccion de features ---
    st.subheader("✅ Selección de Features para el Modelo")
    # Sugerencia: excluir columnas tipo ID por defecto
    default = st.session_state.get("features") or [
        c for c in cols_num if "id" not in c.lower()
    ]
    features = st.multiselect(
        "Variables que entrarán al modelo de clustering",
        cols_num,
        default=[f for f in default if f in cols_num],
        key="features",  # se persiste automaticamente en session_state
    )

    if len(features) < 2:
        st.info("Selecciona al menos 2 variables para poder entrenar el clustering.")
    else:
        st.success(f"{len(features)} variables seleccionadas: {', '.join(features)}")
        st.dataframe(df[features].describe().T, use_container_width=True)
