"""
Generador de dataset sintetico de clientes para el Sistema de Segmentacion.

Crea un dataset realista con clientes provenientes de ~4 grupos latentes
(perfiles de comportamiento) e introduce a proposito:
  - valores nulos
  - registros duplicados
  - outliers

...para que el modulo de Preprocesamiento y Limpieza de la app tenga trabajo
real que mostrar (deteccion de duplicados / outliers / imputacion).

Uso:
    python scripts/generate_dataset.py
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N = 1200  # numero base de clientes


def _perfil(n, edad, ingreso, gasto, freq, web):
    """Genera n clientes alrededor de un centroide de comportamiento."""
    return pd.DataFrame(
        {
            "Edad": RNG.normal(edad, 6, n).clip(18, 90),
            "Ingreso_Anual_kUSD": RNG.normal(ingreso, 12, n).clip(8, None),
            "Puntaje_Gasto": RNG.normal(gasto, 10, n).clip(1, 100),
            "Frecuencia_Compra_Mes": RNG.normal(freq, 2, n).clip(0, None),
            "Visitas_Web_Mes": RNG.normal(web, 8, n).clip(0, None),
        }
    )


def main():
    # 4 perfiles latentes de clientes
    grupos = [
        _perfil(int(N * 0.30), edad=27, ingreso=35, gasto=78, freq=9, web=42),   # jovenes gastadores
        _perfil(int(N * 0.25), edad=45, ingreso=95, gasto=30, freq=3, web=10),   # altos ingresos / ahorradores
        _perfil(int(N * 0.25), edad=55, ingreso=60, gasto=55, freq=5, web=18),   # familiares estables
        _perfil(int(N * 0.20), edad=22, ingreso=18, gasto=25, freq=2, web=30),   # estudiantes
    ]
    df = pd.concat(grupos, ignore_index=True)

    # Variables categoricas (para probar codificacion)
    df["Genero"] = RNG.choice(["Masculino", "Femenino"], size=len(df))
    df["Ciudad"] = RNG.choice(
        ["CDMX", "Guadalajara", "Monterrey", "Puebla"], size=len(df)
    )
    df["Membresia"] = RNG.choice(
        ["Bronce", "Plata", "Oro"], size=len(df), p=[0.5, 0.35, 0.15]
    )

    # ID de cliente
    df.insert(0, "ID_Cliente", np.arange(1, len(df) + 1))

    # --- Suciedad intencional para el pipeline de limpieza ---

    # 1) Outliers extremos en ingreso y gasto
    idx_out = RNG.choice(df.index, size=15, replace=False)
    df.loc[idx_out, "Ingreso_Anual_kUSD"] *= RNG.uniform(4, 7, size=15)

    # 2) Valores nulos dispersos
    for col, frac in [("Ingreso_Anual_kUSD", 0.04), ("Puntaje_Gasto", 0.03),
                      ("Visitas_Web_Mes", 0.02), ("Ciudad", 0.02)]:
        idx_na = RNG.choice(df.index, size=int(len(df) * frac), replace=False)
        df.loc[idx_na, col] = np.nan

    # 3) Registros duplicados
    dup = df.sample(25, random_state=1).copy()
    df = pd.concat([df, dup], ignore_index=True)

    # Redondeo cosmetico
    df = df.round(
        {
            "Edad": 0,
            "Ingreso_Anual_kUSD": 1,
            "Puntaje_Gasto": 0,
            "Frecuencia_Compra_Mes": 0,
            "Visitas_Web_Mes": 0,
        }
    )

    # Mezclar filas
    df = df.sample(frac=1, random_state=7).reset_index(drop=True)

    df.to_csv("data/clientes.csv", index=False)
    print(f"Dataset generado: data/clientes.csv  -> {df.shape[0]} filas, {df.shape[1]} columnas")
    print(f"Duplicados: {df.duplicated().sum()}  |  Nulos totales: {df.isna().sum().sum()}")


if __name__ == "__main__":
    main()
