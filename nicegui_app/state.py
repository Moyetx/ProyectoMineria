"""
nicegui_app/state.py
--------------------
Gestion de estado para la version NiceGUI.

DIFERENCIA CLAVE CON STREAMLIT
==============================
NiceGUI NO re-ejecuta el script en cada interaccion (es orientado a eventos),
asi que los objetos Python "viven" de forma natural. Pero necesitamos que el
estado sea POR USUARIO / POR PESTANA y que sobreviva a la navegacion entre
secciones. Para eso NiceGUI ofrece dos almacenes:

  - `app.storage.user` : asociado al navegador via cookie. Debe ser
    JSON-serializable. Lo usamos para la SESION/AUTENTICACION.
  - `app.storage.tab`  : en memoria del servidor, unico por pestana. Puede
    guardar OBJETOS ARBITRARIOS (incluido un DataFrame de pandas). Lo usamos
    para el ESTADO DEL PIPELINE -> asi el dataset procesado NO se reinicia al
    cambiar de seccion.

`app.storage.tab` requiere `await client.connected()` antes de accederse, lo
cual garantizamos construyendo la UI dentro del page builder ya conectado.
"""

from nicegui import app

# Estado inicial del pipeline (mismas llaves que la version Streamlit).
_DEFAULTS = {
    "seccion": "carga",       # seccion activa del menu
    "df_original": None,
    "df": None,
    "nombre_archivo": None,
    "features": [],
    "escalado_aplicado": False,
    "labels_kmeans": None,    # tupla (indices, labels)
    "labels_jerarquico": None,
    "modelo_activo": None,    # 'kmeans' | 'jerarquico'
    "resultados": {},         # {'kmeans': {...}, 'jerarquico': {...}}
    # caches de calculos para no repetirlos al refrescar
    "codo": None,             # {'ks':..., 'inertias':..., 'silhouettes':...}
    "dendro": None,           # {'Z':..., 'index':..., 'linkage':...}
}


def pipe() -> dict:
    """Devuelve (creando si hace falta) el dict de estado del pipeline de la pestana."""
    tab = app.storage.tab
    if "pipe" not in tab:
        tab["pipe"] = {
            k: (v.copy() if isinstance(v, (list, dict)) else v)
            for k, v in _DEFAULTS.items()
        }
    return tab["pipe"]


def reset_pipeline() -> None:
    """Reinicia el pipeline (al cargar un nuevo dataset)."""
    app.storage.tab["pipe"] = {
        k: (v.copy() if isinstance(v, (list, dict)) else v)
        for k, v in _DEFAULTS.items()
    }


def hay_datos() -> bool:
    return pipe().get("df") is not None


def get_df():
    return pipe().get("df")


def set_df(df) -> None:
    pipe()["df"] = df


def estado_dataset_texto() -> str:
    df = get_df()
    if df is None:
        return "Sin datos cargados"
    return f"{df.shape[0]:,} filas x {df.shape[1]} columnas"
