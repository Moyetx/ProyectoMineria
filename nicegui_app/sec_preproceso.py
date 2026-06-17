"""
Modulo 2 (NiceGUI): Preprocesamiento y Limpieza.
Nulos (estrategia POR COLUMNA), duplicados, codificacion, outliers
(IQR o Z-Score, con cuartiles y listado de valores) y escalamiento.
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

    # Mapa de calor de nulos: gris claro = presente, rojo OSCURO = nulo (alto contraste)
    fig = px.imshow(
        df.isna().astype(int).T, aspect="auto",
        color_continuous_scale=[(0.0, "#eceff1"), (1.0, "#7f0000")],
        labels=dict(x="Registros", y="Columnas", color="Nulo"),
        title="Mapa de calor de nulos (rojo oscuro = nulo)",
    )
    fig.update_coloraxes(showscale=False)
    ui.plotly(fig).classes("w-full")

    # --- Estrategia POR COLUMNA ---
    cols_con_nulos = [c for c in df.columns if df[c].isna().any()]
    ui.label("Estrategia de imputación por columna").classes("font-semibold mt-2")
    ui.label(
        "Elige qué hacer con cada columna. 'Eliminar filas' quita las filas con "
        "nulos en esa columna; 'No tocar' la deja igual."
    ).classes("text-xs text-gray-500")

    selecciones: dict = {}
    with ui.column().classes("gap-1 w-full"):
        for c in cols_con_nulos:
            es_num = pd.api.types.is_numeric_dtype(df[c])
            opciones = (["Mediana", "Media", "Moda", "Eliminar filas", "No tocar"]
                        if es_num else ["Moda", "Eliminar filas", "No tocar"])
            with ui.row().classes("items-center gap-3 w-full"):
                ui.label(c).classes("w-48 font-medium")
                ui.label(f"{int(df[c].isna().sum())} nulos").classes(
                    "text-xs text-gray-500 w-20")
                ui.label("numérica" if es_num else "categórica").classes(
                    "text-xs text-gray-400 w-24")
                selecciones[c] = ui.select(opciones, value=opciones[0]).props(
                    "dense outlined").classes("w-44")

    def aplicar():
        d = state.get_df().copy()
        cols_eliminar = []
        for c, sel in selecciones.items():
            if c not in d.columns:
                continue
            metodo = sel.value
            if metodo == "No tocar":
                continue
            if metodo == "Eliminar filas":
                cols_eliminar.append(c)
            elif metodo == "Media":
                d[c] = d[c].fillna(d[c].mean())
            elif metodo == "Mediana":
                d[c] = d[c].fillna(d[c].median())
            elif metodo == "Moda":
                d[c] = d[c].fillna(d[c].mode().iloc[0])
        filas_antes = len(d)
        if cols_eliminar:
            d = d.dropna(subset=cols_eliminar)
        d = d.reset_index(drop=True)
        state.set_df(d)
        quitadas = filas_antes - len(d)
        msg = "Imputación por columna aplicada."
        if quitadas:
            msg += f" Se eliminaron {quitadas} filas."
        ui.notify(msg, type="positive")
        refresh.refresh()

    ui.button("Aplicar imputación por columna", on_click=aplicar).props("color=primary")


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
    cols_obj = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
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

    with ui.row().classes("items-center gap-4"):
        col = ui.select(cols, value=cols[0], label="Variable").classes("w-64")
        metodo = ui.radio(["IQR", "Z-Score"], value="IQR").props("inline")

    @ui.refreshable
    def panel():
        d = state.get_df()
        c = col.value
        s = d[c].dropna()
        q1, q2, q3 = s.quantile(0.25), s.quantile(0.5), s.quantile(0.75)
        iqr = q3 - q1

        if metodo.value == "IQR":
            li, ls = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask_out = (d[c] < li) | (d[c] > ls)
            desc = f"Límites IQR: [{li:,.2f}, {ls:,.2f}]  (Q1-1.5·IQR, Q3+1.5·IQR)"
        else:  # Z-Score
            mu, sigma = s.mean(), s.std()
            umbral = 3.0
            if sigma == 0 or pd.isna(sigma):
                mask_out = pd.Series(False, index=d.index)
                desc = "Desviación estándar = 0; no se pueden calcular Z-Scores."
            else:
                z = (d[c] - mu) / sigma
                mask_out = z.abs() > umbral
                li, ls = mu - umbral * sigma, mu + umbral * sigma
                desc = (f"Media={mu:,.2f}  Desv={sigma:,.2f}  |Z|>{umbral:.0f}  "
                        f"→ fuera de [{li:,.2f}, {ls:,.2f}]")

        mask_out = mask_out.fillna(False)
        n_out = int(mask_out.sum())

        # Estadisticos / cuartiles
        with ui.row().classes("gap-3 flex-wrap"):
            for et, v in [("Q1 (25%)", q1), ("Q2 (mediana)", q2), ("Q3 (75%)", q3),
                          ("IQR", iqr), ("Mín", s.min()), ("Máx", s.max())]:
                with ui.card().classes("items-center p-2"):
                    ui.label(f"{v:,.2f}").classes("font-bold")
                    ui.label(et).classes("text-xs text-gray-500")

        ui.label(f"Outliers detectados ({metodo.value}): {n_out}").classes("font-semibold mt-2")
        ui.label(desc).classes("text-xs text-gray-500")

        ui.plotly(px.box(d, y=c, points="outliers", title=f"Boxplot de {c}")).classes("w-full")

        # Listado de valores outliers
        if n_out > 0:
            out = d.loc[mask_out, [c]].copy()
            if metodo.value == "Z-Score" and s.std() not in (0, None) and not pd.isna(s.std()):
                out["Z"] = ((d.loc[mask_out, c] - s.mean()) / s.std()).round(2)
            out = out.reset_index().rename(columns={"index": "Fila"})
            ui.label("Valores outliers (primeros 50)").classes("text-sm font-semibold mt-2")
            ui.table.from_pandas(out.head(50)).classes("w-full")

            def eliminar():
                state.set_df(d.loc[~mask_out].reset_index(drop=True))
                ui.notify(f"Eliminados {n_out} outliers de {c} ({metodo.value}).",
                          type="positive")
                panel.refresh()

            ui.button(f"Eliminar outliers de {c} ({metodo.value})", on_click=eliminar)

    col.on_value_change(lambda: panel.refresh())
    metodo.on_value_change(lambda: panel.refresh())
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