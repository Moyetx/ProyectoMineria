# 🛍️ Sistema de Segmentación Inteligente de Clientes

Aplicación web (Streamlit) que implementa un **pipeline completo de clustering**
para descubrir segmentos de clientes orientados a estrategias de marketing.

> **Propuesta 2 — Minería de Datos.** Cubre: detección de outliers, detección de
> duplicados, escalamiento, selección de variables, **K-Means** y **Clustering
> Jerárquico**, métricas de evaluación (**Método del Codo** y **Silhouette
> Score**) e **interfaz gráfica** con autenticación de usuarios.

---

## 🚀 Instalación y ejecución

El proyecto incluye **dos interfaces equivalentes**: **NiceGUI** (recomendada,
pura Python con look de aplicación) y **Streamlit** (alternativa clásica).

```bash
# 1. (opcional) crear entorno virtual
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. instalar dependencias
pip install -r requirements.txt

# 3. (opcional) regenerar el dataset de ejemplo
python scripts/generate_dataset.py

# 4a. ejecutar la app NiceGUI (recomendada)  ->  http://localhost:8080
python main.py

# 4b. o ejecutar la app Streamlit (alternativa)  ->  http://localhost:8501
streamlit run app.py
```

### Tests (NiceGUI)

```bash
pytest -q          # smoke tests: login + recorrido de las 6 secciones
```

---

## 🔐 Acceso

La aplicación está **bloqueada tras una compuerta de autenticación**. Debes:

1. **Crear una cuenta** (nombre, correo, contraseña, foto de perfil).
2. **Verificar el correo** con el código de 6 dígitos (mostrado en pantalla —
   simulación del envío por email).
3. **Iniciar sesión**.

También hay flujo de **recuperación de contraseña** mediante token.

> Las contraseñas se guardan **encriptadas** con PBKDF2-HMAC-SHA256 + salt único
> por usuario en una base de datos local SQLite (`usuarios.db`). Nunca se
> almacenan en texto plano.

---

## 🧭 Pipeline (secciones de la app)

| # | Sección | Qué hace |
|---|---------|----------|
| 1 | **Cargar Datos** | Sube CSV/XLSX o usa el dataset demo. `df.head()` + `df.info()`. |
| 2 | **Preprocesamiento** | Nulos (mapa de calor + imputación), **duplicados**, codificación categórica (One-Hot/Label), **outliers** (boxplot + IQR), **escalamiento** (Standard/MinMax). |
| 3 | **Selección de Variables** | Multi-select de features + matriz de correlación. |
| 4 | **Modelos de Clustering** | **K-Means** (método del codo + entrenamiento) y **Jerárquico** (dendrograma + corte). |
| 5 | **Evaluación** | **Silhouette Score** + tabla comparativa de modelos. |
| 6 | **Visualización y Exportación** | Proyección **PCA** 2D/3D, perfilado por clúster, **Radar Chart** de centroides y descarga del CSV con la columna `Cluster`. |

> ⚠️ El clustering jerárquico aplica **muestreo automático de máx. 2,000 filas**
> para el dendrograma y el entrenamiento, evitando `MemoryError` en datasets
> grandes (requisito de la especificación).

---

## 🗂️ Estructura del proyecto

```
ProyectoMineria/
├── main.py                 # ★ Entrada NiceGUI (recomendada)
├── app.py                  # Entrada Streamlit (alternativa)
├── security.py             # Hashing PBKDF2 + validaciones (compartido)
├── database.py             # Capa SQLite de usuarios (CRUD) — compartido
├── auth.py                 # Auth UI (Streamlit)
├── conftest.py / pytest.ini / test_nicegui_app.py   # tests NiceGUI
├── requirements.txt
├── README.md
├── data/
│   └── clientes.csv        # Dataset de ejemplo (nulos, duplicados, outliers)
├── scripts/
│   └── generate_dataset.py # Generador del dataset sintético
├── nicegui_app/            # ★ Interfaz NiceGUI
│   ├── state.py            # Estado del pipeline (app.storage.tab)
│   ├── auth_ui.py          # Compuerta de acceso (app.storage.user)
│   ├── shell.py            # Cabecera + drawer + navegación
│   ├── sec_carga.py        # Módulo 1
│   ├── sec_preproceso.py   # Módulo 2
│   ├── sec_variables.py    # Módulo 3
│   ├── sec_modelos.py      # Módulo 4 (K-Means + jerárquico)
│   ├── sec_evaluacion.py   # Módulo 5
│   └── sec_visualizacion.py# Módulo 6
└── modules/                # Interfaz Streamlit (mismo pipeline)
    ├── state.py · data_loader.py · preprocessing.py
    ├── feature_selection.py · clustering.py
    └── evaluation.py · visualization.py
```

---

## 🧠 Manejo de estado (que el dataset no se reinicie)

- **NiceGUI** (`nicegui_app/state.py`): el estado del pipeline vive en
  `app.storage.tab` (memoria del servidor, por pestaña), que **puede guardar el
  DataFrame directamente**; la sesión del usuario va en `app.storage.user`
  (cookie). NiceGUI no re-ejecuta el script, así que el estado persiste de forma
  natural entre secciones.
- **Streamlit** (`modules/state.py`): Streamlit re-ejecuta el script en cada
  interacción, por eso todo se centraliza en `st.session_state`. Cada
  transformación lee con `state.get_df()` y escribe con `state.set_df()`.

## ☁️ Despliegue

- **NiceGUI** → Hugging Face Spaces (Docker), Render, Railway o cualquier VPS.
  Define `storage_secret` desde una variable de entorno y expón el puerto 8080.
- **Streamlit** → Streamlit Community Cloud (conecta el repo y apunta a
  `app.py`) o Hugging Face Spaces (SDK Streamlit).
