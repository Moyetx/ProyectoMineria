"""
modules/preprocessing.py
------------------------
Modulo 3 de la especificacion: Preprocesamiento y Limpieza (el mas critico).

Cubre los REQUISITOS OBLIGATORIOS del proyecto:
  - Valores faltantes: mapa de calor de nulos + eliminar/imputar (media/mediana/moda).
  - Deteccion de duplicados: conteo + eliminacion.
  - Codificacion de categoricas: One-Hot o Label Encoding.
  - Deteccion de outliers: Boxplot interactivo + filtrado por rango IQR.
  - Escalamiento: StandardScaler / MinMaxScaler con vista previa.

Todas las transformaciones operan sobre `state.get_df()` y guardan el
resultado con `state.set_df()`, de modo que persisten al cambiar de pestana.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.preprocessing import (
    LabelEncoder,
    MinMaxScaler,
    StandardScaler,
)

from modules import state


# ---------------------------------------------------------------------------
# 3.1 Valores faltantes
# ---------------------------------------------------------------------------
def _seccion_nulos(df: pd.DataFrame) -> None:
    st.subheader("🕳️ Valores Faltantes (Nulos)")

    total_nulos = int(df.isna().sum().sum())
    st.write(f"Total de celdas nulas: **{total_nulos}**")

    if total_nulos == 0:
        st.success("No hay valores nulos en el dataset.")
        return

    # Mapa de calor de nulos (matriz booleana de faltantes)
    mapa = df.isna().astype(int)
    fig = px.imshow(
        mapa.T,
        aspect="auto",
        color_continuous_scale=["#e8f5e9", "#c62828"],
        labels=dict(x="Registros", y="Columnas", color="Nulo"),
        title="Mapa de calor de valores nulos",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # Conteo por columna
    nulos_col = df.isna().sum()
    st.dataframe(
        nulos_col[nulos_col > 0].rename("Nulos").to_frame(),
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Eliminar filas con nulos**")
        if st.button("🗑️ Eliminar filas con nulos"):
            antes = len(df)
            state.set_df(df.dropna().reset_index(drop=True))
            st.success(f"Eliminadas {antes - len(state.get_df())} filas.")
            st.rerun()

    with col2:
        st.markdown("**Imputar valores faltantes**")
        estrategia = st.selectbox(
            "Estrategia de imputación",
            ["Media", "Mediana", "Moda"],
            key="impute_strategy",
        )
        if st.button("Imputar nulos"):
            df_imp = df.copy()
            for col in df_imp.columns:
                if df_imp[col].isna().any():
                    if pd.api.types.is_numeric_dtype(df_imp[col]):
                        if estrategia == "Media":
                            valor = df_imp[col].mean()
                        elif estrategia == "Mediana":
                            valor = df_imp[col].median()
                        else:
                            valor = df_imp[col].mode().iloc[0]
                    else:
                        # columnas no numericas siempre se imputan con la moda
                        valor = df_imp[col].mode().iloc[0]
                    df_imp[col] = df_imp[col].fillna(valor)
            state.set_df(df_imp)
            st.success(f"Valores imputados con estrategia: {estrategia}.")
            st.rerun()


# ---------------------------------------------------------------------------
# 3.2 Duplicados
# ---------------------------------------------------------------------------
def _seccion_duplicados(df: pd.DataFrame) -> None:
    st.subheader("👥 Detección de Duplicados")
    n_dup = int(df.duplicated().sum())
    st.metric("Registros duplicados", n_dup)

    if n_dup == 0:
        st.success("No se detectaron registros duplicados.")
        return

    with st.expander("Ver registros duplicados"):
        st.dataframe(df[df.duplicated(keep=False)], use_container_width=True)

    if st.button("🗑️ Eliminar duplicados"):
        state.set_df(df.drop_duplicates().reset_index(drop=True))
        st.success(f"Eliminados {n_dup} registros duplicados.")
        st.rerun()


# ---------------------------------------------------------------------------
# 3.3 Codificacion de categoricas
# ---------------------------------------------------------------------------
def _seccion_codificacion(df: pd.DataFrame) -> None:
    st.subheader("🔤 Codificación de Variables Categóricas")

    cols_obj = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not cols_obj:
        st.info("No hay columnas categóricas (tipo object) para codificar.")
        return

    st.write("Columnas categóricas detectadas:", ", ".join(f"`{c}`" for c in cols_obj))

    cols_sel = st.multiselect(
        "Selecciona columnas a codificar",
        cols_obj,
        default=cols_obj,
        key="cols_encode",
    )
    metodo = st.radio(
        "Método de codificación",
        ["One-Hot Encoding", "Label Encoding"],
        horizontal=True,
        key="metodo_encode",
    )

    if st.button("Aplicar codificación") and cols_sel:
        df_enc = df.copy()
        if metodo == "One-Hot Encoding":
            df_enc = pd.get_dummies(df_enc, columns=cols_sel, dtype=int)
        else:  # Label Encoding
            for col in cols_sel:
                le = LabelEncoder()
                df_enc[col] = le.fit_transform(df_enc[col].astype(str))
        state.set_df(df_enc)
        st.success(f"Codificación aplicada ({metodo}).")
        st.rerun()


# ---------------------------------------------------------------------------
# 3.4 Outliers
# ---------------------------------------------------------------------------
def _seccion_outliers(df: pd.DataFrame) -> None:
    st.subheader("📦 Detección de Outliers (Valores Atípicos)")

    cols_num = df.select_dtypes(include="number").columns.tolist()
    if not cols_num:
        st.info("No hay columnas numéricas para analizar outliers.")
        return

    col = st.selectbox("Selecciona una variable", cols_num, key="outlier_col")

    serie = df[col].dropna()
    # Limites por rango intercuartilico (IQR)
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    n_outliers = int(((serie < lim_inf) | (serie > lim_sup)).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Outliers detectados", n_outliers)
    c2.metric("Límite inferior (IQR)", f"{lim_inf:,.2f}")
    c3.metric("Límite superior (IQR)", f"{lim_sup:,.2f}")

    # Boxplot interactivo
    fig = px.box(df, y=col, points="outliers", title=f"Boxplot de {col}")
    st.plotly_chart(fig, use_container_width=True)

    if n_outliers > 0 and st.button(f"🗑️ Eliminar outliers de '{col}' (rango IQR)"):
        mask = (df[col] >= lim_inf) & (df[col] <= lim_sup)
        # Conservamos tambien las filas con nulo en esa columna (no son outliers)
        mask = mask | df[col].isna()
        state.set_df(df[mask].reset_index(drop=True))
        st.success(f"Eliminados {n_outliers} outliers de '{col}'.")
        st.rerun()


# ---------------------------------------------------------------------------
# 3.5 Escalamiento
# ---------------------------------------------------------------------------
def _seccion_escalamiento(df: pd.DataFrame) -> None:
    st.subheader("⚖️ Escalamiento de Variables")
    st.caption(
        "El escalamiento es obligatorio para clustering basado en distancias "
        "(K-Means / jerárquico). Solo afecta a columnas numéricas."
    )

    cols_num = df.select_dtypes(include="number").columns.tolist()
    if not cols_num:
        st.info("No hay columnas numéricas para escalar.")
        return

    # Excluir posibles IDs del escalamiento
    cols_sel = st.multiselect(
        "Columnas numéricas a escalar",
        cols_num,
        default=[c for c in cols_num if "id" not in c.lower()],
        key="cols_scale",
    )
    metodo = st.radio(
        "Método de escalamiento",
        ["StandardScaler (media 0, desv 1)", "MinMaxScaler (rango 0-1)"],
        key="metodo_scale",
    )

    if st.button("Aplicar escalamiento") and cols_sel:
        scaler = StandardScaler() if metodo.startswith("Standard") else MinMaxScaler()
        df_scaled = df.copy()
        df_scaled[cols_sel] = scaler.fit_transform(df_scaled[cols_sel])
        state.set_df(df_scaled)
        st.session_state["escalado_aplicado"] = True
        st.success(f"Escalamiento aplicado ({metodo}).")
        st.rerun()

    if st.session_state.get("escalado_aplicado"):
        st.info("✅ Escalamiento aplicado. Vista previa del dataframe escalado:")
        st.dataframe(df.head(), use_container_width=True)


# ---------------------------------------------------------------------------
# Entrypoint del modulo
# ---------------------------------------------------------------------------
def render() -> None:
    st.header("2️⃣ Preprocesamiento y Limpieza")

    df = state.get_df()
    if df is None:
        st.warning("Primero carga un dataset en la sección 'Cargar Datos'.")
        return

    # Boton para revertir a los datos originales
    if st.button("↩️ Restaurar dataset original"):
        st.session_state["df"] = st.session_state["df_original"].copy()
        st.session_state["escalado_aplicado"] = False
        st.success("Dataset restaurado al original.")
        st.rerun()

    tabs = st.tabs(
        ["Nulos", "Duplicados", "Codificación", "Outliers", "Escalamiento"]
    )
    with tabs[0]:
        _seccion_nulos(state.get_df())
    with tabs[1]:
        _seccion_duplicados(state.get_df())
    with tabs[2]:
        _seccion_codificacion(state.get_df())
    with tabs[3]:
        _seccion_outliers(state.get_df())
    with tabs[4]:
        _seccion_escalamiento(state.get_df())
