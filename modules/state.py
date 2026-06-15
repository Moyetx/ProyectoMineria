"""
modules/state.py
----------------
Gestion centralizada de `st.session_state` para el PIPELINE de datos.

POR QUE ESTE MODULO EXISTE
==========================
Streamlit re-ejecuta TODO el script en cada interaccion (cada clic, cada
cambio de pestana en el menu lateral). Si guardaramos el DataFrame en una
variable local, se perderia en cada re-ejecucion.

La solucion es persistir todo el estado del pipeline en `st.session_state`,
que sobrevive a las re-ejecuciones mientras dure la sesion del navegador.
Asi, cuando el usuario:
  - carga datos en la pestana 1,
  - los limpia en la pestana 2,
  - y se mueve a la pestana 4,
...el DataFrame procesado NO se reinicia.

Convencion de llaves del pipeline (todas con prefijo claro):
  df_original   -> DataFrame tal cual se cargo (no se modifica)
  df            -> DataFrame "de trabajo" (se va transformando en cada etapa)
  features      -> lista de columnas seleccionadas para el modelo
  X_modelo      -> matriz numerica final (escalada + features) lista para clustering
  labels_kmeans / labels_jerarquico -> etiquetas de cluster por modelo
  resultados    -> dict con metricas (silhouette, k, etc.) para comparacion
"""

import streamlit as st

# Valores por defecto de TODO el estado del pipeline.
_DEFAULTS = {
    "df_original": None,     # DataFrame original sin tocar
    "df": None,             # DataFrame de trabajo (se transforma etapa a etapa)
    "nombre_archivo": None,  # nombre del archivo cargado
    "features": [],          # features seleccionadas para el modelo
    "escalado_aplicado": False,
    "X_modelo": None,        # matriz numerica final para clustering (np.ndarray / df)
    "labels_kmeans": None,   # etiquetas resultantes de K-Means
    "labels_jerarquico": None,  # etiquetas del clustering jerarquico
    "modelo_activo": None,   # 'kmeans' | 'jerarquico' -> cual se usa en eval/viz
    "resultados": {},        # metricas por modelo: {'kmeans': {...}, 'jerarquico': {...}}
}


def init_pipeline_state() -> None:
    """Inicializa (una sola vez) las llaves del pipeline en session_state."""
    for key, default in _DEFAULTS.items():
        st.session_state.setdefault(key, default)


def reset_pipeline() -> None:
    """Reinicia el pipeline (util al cargar un nuevo dataset)."""
    for key, default in _DEFAULTS.items():
        # copiamos para no compartir referencias mutables (listas/dicts)
        st.session_state[key] = default.copy() if isinstance(default, (list, dict)) else default


def hay_datos() -> bool:
    """True si ya se cargo un dataset en memoria."""
    return st.session_state.get("df") is not None


def get_df():
    """DataFrame de trabajo actual."""
    return st.session_state.get("df")


def set_df(df) -> None:
    """Actualiza el DataFrame de trabajo (tras una transformacion)."""
    st.session_state["df"] = df


def estado_dataset_texto() -> str:
    """Texto corto con la dimension del dataset en memoria (para el sidebar)."""
    df = get_df()
    if df is None:
        return "Sin datos cargados"
    return f"{df.shape[0]:,} filas × {df.shape[1]} columnas"
