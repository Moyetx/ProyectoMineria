"""Modulo 1 (NiceGUI): Carga de Datos.

Tres orígenes de datos:
  - Subir mi archivo (CSV / XLSX)
  - Generar un dataset de prueba sintético (con nulos y outliers intencionales)
  - Usar el dataset incluido en el proyecto (data/clientes.csv)
"""

import io
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from nicegui import ui

from nicegui_app import state

DATASET_DEMO = Path(__file__).parent.parent / "data" / "clientes.csv"


def _resumen_info(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Columna": df.columns,
            "Tipo": [str(t) for t in df.dtypes],
            "No_Nulos": df.notna().sum().values,
            "Nulos": df.isna().sum().values,
            "Unicos": [df[c].nunique() for c in df.columns],
        }
    )


def _almacenar(df: pd.DataFrame, nombre: str, vista) -> None:
    """Guarda el DataFrame en el estado del pipeline (resetea etapas previas)."""
    state.reset_pipeline()
    p = state.pipe()
    p["df_original"], p["df"], p["nombre_archivo"] = df.copy(), df.copy(), nombre
    ui.notify(f"Cargado: {nombre} ({df.shape[0]:,}x{df.shape[1]})", type="positive")
    vista.refresh()


def _generar_dataset() -> pd.DataFrame:
    """Genera 1,000 clientes sintéticos con nulos y un outlier intencionales."""
    rng = np.random.default_rng(42)
    n = 1000
    df = pd.DataFrame(
        {
            "Edad": rng.normal(40, 12, n).astype(int).clip(18, 90),
            "Ingreso_Anual_k": rng.normal(60, 25, n).round(1),
            "Puntaje_Gasto": rng.integers(1, 100, n),
            "Frecuencia_Compra_Mes": rng.normal(5, 2, n).round().clip(0, None),
            "Genero": rng.choice(["M", "F"], n),
            "Categoria_Favorita": rng.choice(["Electronica", "Ropa", "Hogar"], n),
        }
    )
    # Suciedad intencional para practicar la limpieza
    df.loc[10:25, "Ingreso_Anual_k"] = np.nan        # nulos
    df.loc[5, "Puntaje_Gasto"] = 500                 # outlier
    df.loc[7, "Ingreso_Anual_k"] = 900               # outlier
    return df


def _leer_csv_robusto(contenido: bytes) -> pd.DataFrame:
    """Lee un CSV detectando separador (, ; tab) y probando varios encodings."""
    ultimo_error = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            # sep=None + engine='python' auto-detecta el separador
            return pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding=enc)
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
    # Ultimo intento: lectura estandar con coma
    try:
        return pd.read_csv(io.BytesIO(contenido))
    except Exception as e:  # noqa: BLE001
        raise ultimo_error or e


def _cargar_bytes(nombre: str, contenido: bytes, vista) -> None:
    """Convierte los bytes subidos en DataFrame y lo almacena (siempre avisa)."""
    if not contenido:
        ui.notify("El archivo llegó vacío. Vuelve a intentarlo.", type="negative")
        return
    try:
        low = nombre.lower()
        if low.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contenido))
        else:  # cualquier otro caso lo tratamos como CSV/texto
            df = _leer_csv_robusto(contenido)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()  # detalle completo en la terminal
        ui.notify(f"Error al leer '{nombre}': {e}", type="negative")
        return

    if df is None or df.empty:
        ui.notify("El archivo no contiene datos legibles.", type="negative")
        return

    _almacenar(df, nombre, vista)


def _manejar_upload(e, vista) -> None:
    """Lee el contenido del archivo subido de forma segura y lo carga."""
    try:
        contenido = e.content.read()
    except Exception as ex:  # noqa: BLE001
        traceback.print_exc()
        ui.notify(f"No se pudo leer el archivo subido: {ex}", type="negative")
        return
    _cargar_bytes(e.name, contenido, vista)


def render() -> None:
    ui.label("1. Carga de Datos").classes("text-2xl font-bold")
    ui.label("Sube tu propio dataset, genera uno de prueba o usa el incluido.").classes(
        "text-sm text-gray-500"
    )

    @ui.refreshable
    def vista():
        df = state.get_df()
        if df is None:
            ui.label("Carga un dataset para comenzar el pipeline.").classes("text-gray-500")
            return

        with ui.row().classes("gap-4 w-full"):
            for etiqueta, valor in [
                ("Registros", f"{df.shape[0]:,}"),
                ("Columnas", df.shape[1]),
                ("Duplicados", int(df.duplicated().sum())),
                ("Celdas nulas", int(df.isna().sum().sum())),
            ]:
                with ui.card().classes("items-center"):
                    ui.label(str(valor)).classes("text-xl font-bold")
                    ui.label(etiqueta).classes("text-xs text-gray-500")

        ui.label("Vista previa (head)").classes("text-lg font-semibold mt-2")
        ui.table.from_pandas(df.head(10)).classes("w-full")

        ui.label("Resumen (info)").classes("text-lg font-semibold mt-2")
        ui.table.from_pandas(_resumen_info(df)).classes("w-full")

    # --- Selector de origen de datos ---
    origen = ui.radio(
        ["Subir mi archivo", "Generar dataset de prueba", "Usar dataset incluido"],
        value="Subir mi archivo",
    ).props("inline")

    @ui.refreshable
    def panel_origen():
        with ui.card().classes("w-full gap-2"):
            if origen.value == "Subir mi archivo":
                ui.label("Sube tu archivo (CSV o XLSX)").classes("font-semibold")
                ui.upload(
                    on_upload=lambda e: _manejar_upload(e, vista),
                    auto_upload=True,
                    max_file_size=200 * 1024 * 1024,  # hasta 200 MB
                ).props('accept=".csv,.xlsx,.xls"').classes("w-full")

            elif origen.value == "Generar dataset de prueba":
                ui.label("1,000 clientes sintéticos (con nulos y outliers).").classes(
                    "font-semibold"
                )
                ui.button(
                    "Generar dataset",
                    on_click=lambda: _almacenar(_generar_dataset(), "dataset_prueba", vista),
                ).props("color=primary")

            else:  # Usar dataset incluido
                if DATASET_DEMO.exists():
                    ui.label("Dataset de ejemplo incluido en el proyecto.").classes(
                        "font-semibold"
                    )
                    ui.button(
                        "Cargar dataset incluido",
                        on_click=lambda: _almacenar(
                            pd.read_csv(DATASET_DEMO), "clientes.csv (incluido)", vista
                        ),
                    ).props("color=primary")
                else:
                    ui.label("No se encontró data/clientes.csv.").classes("text-orange-600")

    origen.on_value_change(lambda: panel_origen.refresh())
    panel_origen()
    vista()