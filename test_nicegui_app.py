"""
Smoke tests de la version NiceGUI: simulan un usuario real con el framework de
testing de NiceGUI para verificar que la compuerta de acceso y las 6 secciones
del pipeline se renderizan sin excepciones.
"""

import pandas as pd
import pytest
from nicegui import app
from nicegui.testing import User

import database as db
import main  # registra la pagina '/' (ui.run esta protegido por guard)
import security
from nicegui_app import sec_carga, state


@pytest.fixture(autouse=True)
def _db_limpia(tmp_path, monkeypatch):
    """Usa una base de datos temporal para no tocar la real."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_usuarios.db")
    db.init_db()
    # usuario de prueba ya verificado
    salt, h = security.crear_hash("secreta123")
    db.crear_usuario("Ana Test", "ana@test.com", h, salt, foto=None, verificado=1)


async def test_compuerta_login_visible(user: User):
    await user.open("/")
    await user.should_see("Iniciar Sesión")


async def test_login_y_recorrido_secciones(user: User):
    # --- Login ---
    await user.open("/")
    await user.should_see("Iniciar Sesión")  # espera a que renderice el form
    user.find(marker="login-email").type("ana@test.com")
    user.find(marker="login-password").type("secreta123")
    user.find("Entrar").click()
    await user.should_see("Sistema de Segmentación de Clientes")

    # Prepara dataset + features + un modelo entrenado dentro del contexto del
    # cliente (el render de las secciones lee este mismo estado). Esto ejercita
    # las rutas pesadas: correlacion, PCA y radar de centroides.
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    with user._client:
        state.reset_pipeline()
        df = pd.read_csv(sec_carga.DATASET_DEMO).drop_duplicates().reset_index(drop=True)
        for c in df.select_dtypes("number"):
            df[c] = df[c].fillna(df[c].median())
        feats = ["Edad", "Ingreso_Anual_kUSD", "Puntaje_Gasto",
                 "Frecuencia_Compra_Mes", "Visitas_Web_Mes"]
        df[feats] = StandardScaler().fit_transform(df[feats])
        km = KMeans(n_clusters=4, n_init=10, random_state=42).fit(df[feats])
        p = state.pipe()
        p.update(df=df, df_original=df.copy(), features=feats,
                 escalado_aplicado=True, modelo_activo="kmeans")
        p["labels_kmeans"] = (df.index, km.labels_)
        p["resultados"]["kmeans"] = {"k": 4, "silhouette": 0.42, "n_muestras": len(df)}

    # --- Navega por cada seccion y verifica que renderiza sin excepcion ---
    for etiqueta, esperado in [
        ("2. Preprocesamiento", "Preprocesamiento y Limpieza"),
        ("3. Selección de Variables", "Matriz de Correlación"),
        ("4. Modelos de Clustering", "Modelos de Clustering"),
        ("5. Evaluación", "Comparativa de Modelos"),
        ("6. Visualización y Exportación", "Proyección Espacial"),
    ]:
        user.find(etiqueta).click()
        await user.should_see(esperado)
