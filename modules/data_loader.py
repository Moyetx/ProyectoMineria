"""
modules/data_loader.py
----------------------
Modulo 2 de la especificacion: Carga de Datos.

  - Subida de archivos CSV / XLSX (y opcion de usar el dataset incluido).
  - Vista previa con df.head().
  - Resumen tipo df.info() (registros, columnas, tipos, nulos, memoria).
"""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from modules import state

# Dataset de ejemplo incluido en el repo
DATASET_DEMO = Path(__file__).parent.parent / "data" / "clientes.csv"


def _resumen_info(df: pd.DataFrame) -> pd.DataFrame:
    """Construye una tabla equivalente a df.info() pero presentable en Streamlit."""
    resumen = pd.DataFrame(
        {
            "Columna": df.columns,
            "Tipo": [str(t) for t in df.dtypes],
            "No_Nulos": df.notna().sum().values,
            "Nulos": df.isna().sum().values,
            "% Nulos": (df.isna().mean().values * 100).round(2),
            "Valores_Unicos": [df[c].nunique() for c in df.columns],
        }
    )
    return resumen


def _cargar_archivo(archivo) -> pd.DataFrame | None:
    """Lee un archivo subido (CSV o XLSX) a un DataFrame."""
    nombre = archivo.name.lower()
    try:
        if nombre.endswith(".csv"):
            return pd.read_csv(archivo)
        if nombre.endswith((".xlsx", ".xls")):
            return pd.read_excel(archivo)
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo leer el archivo: {e}")
        return None
    st.error("Formato no soportado. Usa CSV o XLSX.")
    return None


def _almacenar(df: pd.DataFrame, nombre: str) -> None:
    """Guarda el DataFrame cargado en el estado del pipeline (resetea etapas)."""
    state.reset_pipeline()
    st.session_state["df_original"] = df.copy()
    st.session_state["df"] = df.copy()
    st.session_state["nombre_archivo"] = nombre
    st.success(f"✅ Datos cargados: **{nombre}** ({df.shape[0]:,} filas × {df.shape[1]} columnas)")


def render() -> None:
    st.header("1️⃣ Carga de Datos")

    col1, col2 = st.columns([3, 2])

    with col1:
        archivo = st.file_uploader(
            "Sube tu archivo de clientes (CSV o XLSX)",
            type=["csv", "xlsx", "xls"],
        )
        if archivo is not None and st.button("Cargar archivo", type="primary"):
            df = _cargar_archivo(archivo)
            if df is not None:
                _almacenar(df, archivo.name)

    with col2:
        st.markdown("**¿No tienes un archivo?**")
        st.caption("Usa el dataset de demostración incluido en el proyecto.")
        if DATASET_DEMO.exists() and st.button("Usar dataset de ejemplo"):
            df = pd.read_csv(DATASET_DEMO)
            _almacenar(df, "clientes.csv (demo)")

    # --- Vista previa y resumen ---
    df = state.get_df()
    if df is None:
        st.info("Carga un dataset para comenzar el pipeline.")
        return

    st.subheader("Vista previa (df.head)")
    st.dataframe(df.head(), use_container_width=True)

    st.subheader("Resumen del dataset (df.info)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{df.shape[0]:,}")
    c2.metric("Columnas", df.shape[1])
    c3.metric("Duplicados", int(df.duplicated().sum()))
    c4.metric("Celdas nulas", int(df.isna().sum().sum()))

    st.dataframe(_resumen_info(df), use_container_width=True)

    # Estadisticas descriptivas de las numericas
    num = df.select_dtypes(include="number")
    if not num.empty:
        st.subheader("Estadísticas descriptivas (numéricas)")
        st.dataframe(num.describe().T, use_container_width=True)
