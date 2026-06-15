"""
Modulo 2 (NiceGUI): Preprocesamiento y Limpieza.
Nulos, duplicados, codificacion, outliers y escalamiento.
"""

import pandas as pd
import plotly.express as px
from nicegui import ui
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from nicegui_app import state


def render() -> None:
    ui.label("2. Preprocesamiento y Limpieza").classes("text-2xl font-bold")

    df = state.get_df()
    if df is None:
        ui.label("Primero carga un dataset.").classes("text-gray-500")
        return

    def restaurar():
        p = state.pipe()
        p["df"] = p["df_original"].copy()
        p["escalado_aplicado"] = False
        ui.notify("Dataset restaurado al original.", type="info")
        _todo.refresh()

    ui.button("Restaurar original", on_click=restaurar).props("flat")

    with ui.tabs().classes("w-full") as tabs:
        t_nulos = ui.tab("Nulos")
        t_dup = ui.tab("Duplicados")
        t_cod = ui.tab("Codificación")
        t_out = ui.tab("Outliers")
        t_esc = ui.tab("Escalamiento")

    @ui.refreshable
    def _todo():
        with ui.tab_panels(tabs, value=t_nulos).classes("w-full"):
            with ui.tab_panel(t_nulos):
                _seccion_nulos(_todo)
            with ui.tab_panel(t_dup):
                _seccion_duplicados(_todo)
            with ui.tab_panel(t_cod):
                _seccion_codificacion(_todo)
            with ui.tab_panel(t_out):
                _seccion_outliers()
            with ui.tab_panel(t_esc):
                _seccion_escalamiento(_todo)

    _todo()


# --------------------------------------------------------------------------- nulos
def _seccion_nulos(refresh):
    df = state.get_df()
    total = int(df.isna().sum().sum())
    ui.label(f"Total de celdas nulas: {total}").classes("font-semibold")
    if total == 0:
        ui.label("No hay valores nulos.").classes("text-green-600"); return

    # Mapa de calor de nulos
    fig = px.imshow(df.isna().astype(int).T, aspect="auto",
                    color_continuous_scale=["#e8f5e9", "#c62828"],
                    labels=dict(x="Registros", y="Columnas"),
                    title="Mapa de calor de nulos")
    fig.update_coloraxes(showscale=False)
    ui.plotly(fig).classes("w-full")

    def eliminar():
        antes = len(df)
        state.set_df(df.dropna().reset_index(drop=True))
        ui.notify(f"Eliminadas {antes - len(state.get_df())} filas.", type="positive")
        refresh.refresh()

    estrategia = ui.select(["Media", "Mediana", "Moda"], value="Mediana",
                          label="Estrategia de imputación").classes("w-48")

    def imputar():
        d = state.get_df().copy()
        for col in d.columns:
            if d[col].isna().any():
                if pd.api.types.is_numeric_dtype(d[col]):
                    val = {"Media": d[col].mean(), "Mediana": d[col].median()}.get(
                        estrategia.value, d[col].mode().iloc[0])
                else:
                    val = d[col].mode().iloc[0]
                d[col] = d[col].fillna(val)
        state.set_df(d)
        ui.notify(f"Imputado con {estrategia.value}.", type="positive")
        refresh.refresh()

    with ui.row():
        ui.button("Eliminar filas con nulos", on_click=eliminar)
        ui.button("Imputar nulos", on_click=imputar)


# --------------------------------------------------------------------------- duplicados
def _seccion_duplicados(refresh):
    df = state.get_df()
    n = int(df.duplicated().sum())
    ui.label(f"Registros duplicados: {n}").classes("font-semibold")
    if n == 0:
        ui.label("No hay duplicados.").classes("text-green-600"); return

    def eliminar():
        state.set_df(df.drop_duplicates().reset_index(drop=True))
        ui.notify(f"Eliminados {n} duplicados.", type="positive")
        refresh.refresh()

    ui.button("Eliminar duplicados", on_click=eliminar)


# --------------------------------------------------------------------------- codificacion
def _seccion_codificacion(refresh):
    df = state.get_df()
    cols_obj = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not cols_obj:
        ui.label("No hay columnas categóricas.").classes("text-gray-500"); return

    sel = ui.select(cols_obj, value=cols_obj, multiple=True,
                   label="Columnas a codificar").classes("w-full").props("use-chips")
    metodo = ui.radio(["One-Hot Encoding", "Label Encoding"],
                     value="One-Hot Encoding").props("inline")

    def aplicar():
        if not sel.value:
            ui.notify("Selecciona columnas.", type="warning"); return
        d = df.copy()
        if metodo.value == "One-Hot Encoding":
            d = pd.get_dummies(d, columns=list(sel.value), dtype=int)
        else:
            for c in sel.value:
                d[c] = LabelEncoder().fit_transform(d[c].astype(str))
        state.set_df(d)
        ui.notify(f"Codificación aplicada ({metodo.value}).", type="positive")
        refresh.refresh()

    ui.button("Aplicar codificación", on_click=aplicar)


# --------------------------------------------------------------------------- outliers
def _seccion_outliers():
    df = state.get_df()
    cols = df.select_dtypes(include="number").columns.tolist()
    if not cols:
        ui.label("No hay columnas numéricas.").classes("text-gray-500"); return

    col = ui.select(cols, value=cols[0], label="Variable").classes("w-64")

    @ui.refreshable
    def panel():
        d = state.get_df()
        c = col.value
        s = d[c].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        li, ls = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((s < li) | (s > ls)).sum())
        ui.label(f"Outliers: {n_out}  |  IQR: [{li:,.2f}, {ls:,.2f}]").classes("font-semibold")
        ui.plotly(px.box(d, y=c, points="outliers", title=f"Boxplot de {c}")).classes("w-full")

        def eliminar():
            mask = ((d[c] >= li) & (d[c] <= ls)) | d[c].isna()
            state.set_df(d[mask].reset_index(drop=True))
            ui.notify(f"Eliminados {n_out} outliers de {c}.", type="positive")
            panel.refresh()

        if n_out > 0:
            ui.button(f"Eliminar outliers de {c} (IQR)", on_click=eliminar)

    col.on_value_change(lambda: panel.refresh())
    panel()


# --------------------------------------------------------------------------- escalamiento
def _seccion_escalamiento(refresh):
    df = state.get_df()
    cols = df.select_dtypes(include="number").columns.tolist()
    if not cols:
        ui.label("No hay columnas numéricas.").classes("text-gray-500"); return

    default = [c for c in cols if "id" not in c.lower()]
    sel = ui.select(cols, value=default, multiple=True,
                   label="Columnas a escalar").classes("w-full").props("use-chips")
    metodo = ui.radio(["StandardScaler", "MinMaxScaler"], value="StandardScaler").props("inline")

    def aplicar():
        if not sel.value:
            ui.notify("Selecciona columnas.", type="warning"); return
        scaler = StandardScaler() if metodo.value == "StandardScaler" else MinMaxScaler()
        d = df.copy()
        d[list(sel.value)] = scaler.fit_transform(d[list(sel.value)])
        state.set_df(d)
        state.pipe()["escalado_aplicado"] = True
        ui.notify(f"Escalamiento aplicado ({metodo.value}).", type="positive")
        refresh.refresh()

    ui.button("Aplicar escalamiento", on_click=aplicar)
    if state.pipe().get("escalado_aplicado"):
        ui.label("Escalamiento aplicado. Vista previa:").classes("text-green-600 mt-2")
        ui.table.from_pandas(state.get_df().head(8)).classes("w-full")
