"""Pipeline reproducible para construir la base municipal final y el clustering.

Entradas esperadas en /mnt/data:
- Tesis_input_base_integrada.xlsx

Salidas:
- Tesis_final_base_resultados.xlsx
- Tesis_final_base_municipal.csv

Este script replica la lógica usada en el archivo final de tesis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path('/mnt/data')
INPUT_XLSX = BASE_DIR / 'Tesis_input_base_integrada.xlsx'
OUTPUT_CSV = BASE_DIR / 'Tesis_final_base_municipal.csv'

FEATURE_COLS = [
    'PROM_DEPENDENCIA_FCM',
    'PROM_TRANSFERENCIAS_SOBRE_INGRESOS',
    'PROM_GASTO_CORRIENTE_SOBRE_GASTO_TOTAL',
    'PROM_SERV_COMUNITARIOS_SOBRE_GASTO_TOTAL',
    'LOG_PROM_DISPONIBILIDAD_PRESUP_X_HAB',
    'LOG_PROM_IPPP',
]

NAME_MAP = {
    1: 'Dependencia fiscal intermedia y operación corriente alta',
    2: 'Mayor holgura fiscal y capacidad propia',
    3: 'Alta disponibilidad por habitante y baja escala relativa',
    4: 'Alta transferencia y orientación a servicios comunitarios',
}


def load_base(path: Path) -> pd.DataFrame:
    """Carga la base municipal consolidada."""
    df = pd.read_excel(path, sheet_name='02_Base_municipal_2016_2024')
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica transformaciones previas al clustering."""
    out = df.copy()
    out['LOG_PROM_DISPONIBILIDAD_PRESUP_X_HAB'] = np.log1p(
        out['PROM_DISPONIBILIDAD_PRESUP_X_HAB'].clip(lower=0)
    )
    out['LOG_PROM_IPPP'] = np.log1p(out['PROM_IPPP'].clip(lower=0))
    return out


def evaluate_k(df: pd.DataFrame, k_values=range(2, 7)) -> pd.DataFrame:
    """Calcula métricas comparativas para distintos valores de k."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURE_COLS])

    rows = []
    for k in k_values:
        model = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=300)
        labels = model.fit_predict(X)
        rows.append(
            {
                'k': k,
                'silhouette': float(silhouette_score(X, labels)),
                'inertia': float(model.inertia_),
                'cluster_sizes': pd.Series(labels).value_counts().sort_index().tolist(),
            }
        )
    return pd.DataFrame(rows)


def fit_final_model(df: pd.DataFrame, k: int = 4) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ajusta el modelo final y devuelve base enriquecida y centroides."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURE_COLS])

    model = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=300)
    labels = model.fit_predict(X)

    out = df.copy()
    out['CLUSTER_FINAL'] = labels + 1
    out['DISTANCIA_CENTROIDE'] = np.linalg.norm(X - model.cluster_centers_[labels], axis=1)
    out['NOMBRE_CLUSTER'] = out['CLUSTER_FINAL'].map(NAME_MAP)

    zscores = pd.DataFrame(X, columns=[f'Z_{c}' for c in FEATURE_COLS])
    out = pd.concat([out.reset_index(drop=True), zscores], axis=1)

    centroids = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=FEATURE_COLS
    )
    centroids['CLUSTER_FINAL'] = range(1, k + 1)
    centroids['N'] = out['CLUSTER_FINAL'].value_counts().sort_index().values
    centroids['NOMBRE_CLUSTER'] = centroids['CLUSTER_FINAL'].map(NAME_MAP)

    return out, centroids


def main() -> None:
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f'No se encontró el archivo de entrada: {INPUT_XLSX}')

    df = load_base(INPUT_XLSX)
    df = prepare_features(df)

    # Evaluación de k. Se mantiene k=4 por equilibrio entre métricas y utilidad sustantiva.
    comparison = evaluate_k(df)
    print('Evaluación de k:')
    print(comparison.to_string(index=False))

    final_df, centroids = fit_final_model(df, k=4)
    final_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    print('\nResumen del modelo final:')
    print(f'Municipios: {len(final_df)}')
    print(f'Clusters asignados sin nulos: {final_df["CLUSTER_FINAL"].notna().sum()}')
    print(f'Tamaño por cluster: {final_df["CLUSTER_FINAL"].value_counts().sort_index().to_dict()}')
    print('\nCentroides (escala original):')
    print(centroids.round(4).to_string(index=False))
    print(f'\nCSV exportado en: {OUTPUT_CSV}')


if __name__ == '__main__':
    main()
