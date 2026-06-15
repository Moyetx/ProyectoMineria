"""
app.py
------
Punto de entrada del Sistema de Segmentación Inteligente de Clientes.

Orquesta:
  1. La COMPUERTA DE ACCESO (auth): toda la app principal esta bloqueada
     hasta que el usuario inicia sesion.
  2. El SIDEBAR con el perfil del usuario y el menu de navegacion del pipeline.
  3. El ROUTING entre los 6 modulos del pipeline de clustering.

CLAVE — Manejo de st.session_state
===================================
Streamlit re-ejecuta este script completo en CADA interaccion. Para que el
estado sobreviva entre re-ejecuciones y cambios de pestana, todo se guarda en
st.session_state:
  - Estado de AUTENTICACION  -> inicializado en auth.init_auth_state()
  - Estado del PIPELINE/datos -> inicializado en state.init_pipeline_state()
Asi, el dataset cargado y procesado NO se reinicia al navegar entre secciones.

Ejecutar con:
    streamlit run app.py
"""

import streamlit as st

import auth
import database as db
from modules import (
    clustering,
    data_loader,
    evaluation,
    feature_selection,
    preprocessing,
    state,
    visualization,
)

# --- Configuracion general de la pagina ---
st.set_page_config(
    page_title="Segmentación de Clientes",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Mapa de secciones del pipeline -> funcion render de cada modulo
PAGINAS = {
    "1. Cargar Datos": data_loader.render,
    "2. Preprocesamiento y Limpieza": preprocessing.render,
    "3. Selección y Exploración de Variables": feature_selection.render,
    "4. Modelos de Clustering": clustering.render,
    "5. Evaluación de Resultados": evaluation.render,
    "6. Visualización y Exportación": visualization.render,
}


def render_sidebar_navegacion() -> str:
    """Dibuja el menu de navegacion del pipeline y devuelve la seccion elegida."""
    with st.sidebar:
        st.title("🛍️ Sistema de Segmentación de Clientes")
        seccion = st.radio(
            "Etapas del pipeline",
            list(PAGINAS.keys()),
            key="navegacion",
        )
        st.divider()
        # Estado actual del dataset en memoria
        st.markdown("**📦 Estado del dataset**")
        st.info(state.estado_dataset_texto())
        if st.session_state.get("nombre_archivo"):
            st.caption(f"Archivo: {st.session_state['nombre_archivo']}")
    return seccion


def main() -> None:
    # Inicializacion (idempotente) de la base de datos y del estado de sesion
    db.init_db()
    auth.init_auth_state()
    state.init_pipeline_state()

    # ---------------- COMPUERTA DE ACCESO ----------------
    if not st.session_state.get("autenticado"):
        auth.render_compuerta_acceso()
        return  # bloquea toda la app principal hasta autenticarse

    # ---------------- APP PRINCIPAL (autenticado) ----------------
    # Perfil del usuario + boton de cerrar sesion en el sidebar
    auth.render_perfil_sidebar()

    # Menu de navegacion del pipeline
    seccion = render_sidebar_navegacion()

    # Render del modulo correspondiente
    PAGINAS[seccion]()


if __name__ == "__main__":
    main()
