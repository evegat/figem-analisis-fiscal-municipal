#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustering_USACH.py
===================
Pipeline de análisis cuantitativo — Tesis de Magíster USACH.
Autora tesis : Soledad Montecinos
Script       : pipeline completo, implementado sobre numpy + pandas

Tema: Validación empírica de la clasificación FIGEM de municipios chilenos
      mediante clustering K-means y modelo de panel con efectos fijos.

ARCHIVOS:
  Entrada : Input_USACH.xlsx   (debe estar en el mismo directorio)
  Salida  : Output_USACH.xlsx  (generado automáticamente)

HOJAS DE ENTRADA USADAS:
  - 01_Base_long_limpia          (panel longitudinal 2016-2024, N ≈ 3.085)
  - 02_Base_municipal_2016_2024  (promedios comunales, N = 345)
  - 04_FIGEM_2016_2024_long      (montos FIGEM oficiales por comuna-año)

PIPELINE:
   1. Carga y validación de datos
   2. Imputación de MONTO_FIGEM faltante (mediana grupo-año)
   3. Construcción de variables per cápita para el panel
   4. PCA sobre dimensión de desarrollo (DISPONIBILIDAD + IPPP)
   5. Estandarización Z-score de variables de clustering
   6. Evaluación K-means k=2..6 (inercia + silhouette)
   7. Clustering final k=4
   8. Caracterización de tipologías fiscales
   9. Matriz de confusión FIGEM vs clusters + Kappa de Cohen
  10. Modelo de panel con efectos fijos (within estimator, SE robustos HC3)
  11. Pruebas de robustez (10 semillas, estabilidad de asignación)
  12. Exportación a Output_USACH.xlsx (17 hojas trazables)

EJECUCIÓN:
    python -u Clustering_USACH.py

NOTA: Todos los algoritmos (K-means, silhouette, PCA, FE) están implementados
directamente sobre numpy/pandas para máxima reproducibilidad y trazabilidad,
sin dependencias externas adicionales.
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS Y CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_DIR / 'data' / 'Input_USACH.xlsx'
OUTPUT_FILE = PROJECT_DIR / 'data' / 'Output_USACH.xlsx'

SHEET_LONG  = '01_Base_long_limpia'
SHEET_MUNIC = '02_Base_municipal_2016_2024'
SHEET_FIGEM = '04_FIGEM_2016_2024_long'

# Variables de clustering (Avance 19.03.2026, Sección 3.4)
CLUSTER_VARS = [
    'PROM_AUTONOMIA_FISCAL',
    'PROM_DEPENDENCIA_FCM',
    'PROM_TRANSFERENCIAS_SOBRE_INGRESOS',
    'PROM_GASTO_CORRIENTE_SOBRE_GASTO_TOTAL',
    'PROM_SERV_COMUNITARIOS_SOBRE_GASTO_TOTAL',
    'PCA1_DESARROLLO',
]

# Tipologías fiscales (Avance 19.03.2026, Sección 4.2)
CLUSTER_NAMES = {
    1: 'Autónomos Urbanos Estables',
    2: 'Dependientes Estructurales',
    3: 'Mineras Volátiles',
    4: 'Rurales Estables',
}

RANDOM_SEED      = 42
K_MIN, K_MAX     = 2, 6
K_FINAL          = 4
N_INIT           = 20
MAX_ITER         = 500
ROBUSTNESS_SEEDS = list(range(10))


# ─────────────────────────────────────────────────────────────────────────────
# 1. CARGA Y VALIDACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input no encontrado: {INPUT_FILE}")
    print(f"[1/12] Cargando {INPUT_FILE.name} ...", flush=True)
    df_long  = pd.read_excel(INPUT_FILE, sheet_name=SHEET_LONG)
    df_munic = pd.read_excel(INPUT_FILE, sheet_name=SHEET_MUNIC)
    df_figem = pd.read_excel(INPUT_FILE, sheet_name=SHEET_FIGEM)
    print(f"       Base longitudinal  : {df_long.shape[0]:,} obs")
    print(f"       Base municipal     : {df_munic.shape[0]:,} comunas")
    print(f"       FIGEM longitudinal : {df_figem.shape[0]:,} obs")
    assert df_munic['CODIGO'].nunique() == df_munic.shape[0]
    return df_long, df_munic, df_figem


# ─────────────────────────────────────────────────────────────────────────────
# 2. IMPUTACIÓN DE MONTO_FIGEM
# ─────────────────────────────────────────────────────────────────────────────

def impute_figem(df_figem: pd.DataFrame):
    """
    Imputa MONTO_FIGEM faltante con mediana GRUPO_FIGEM × AÑO.

    Justificación: los municipios de un mismo grupo FIGEM compiten en el
    mismo pool de recursos; la mediana grupo-año es estimador robusto
    no paramétrico (Little & Rubin, 2019). Se evita la media por sensibilidad
    a valores extremos en grupos con n < 50.
    Estrategia escalonada: (1) mediana grupo×año → (2) mediana grupo →
    (3) mediana global, para garantizar imputación completa.
    """
    print("[2/12] Imputando MONTO_FIGEM ...", flush=True)
    df = df_figem.copy()
    n_total = df.shape[0]
    n_null  = df['MONTO_FIGEM'].isna().sum()

    med_ga = df.groupby(['GRUPO_FIGEM', 'AÑO'])['MONTO_FIGEM'].transform('median')
    med_g  = df.groupby('GRUPO_FIGEM')['MONTO_FIGEM'].transform('median')
    med_gl = df['MONTO_FIGEM'].median()

    df['MONTO_FIGEM_ORIG']  = df['MONTO_FIGEM'].copy()
    df['MONTO_FIGEM_IMPUT'] = df['MONTO_FIGEM'].fillna(med_ga).fillna(med_g).fillna(med_gl)
    df['FLAG_IMPUTADO']     = df['MONTO_FIGEM'].isna().astype(int)

    tasa = n_null / n_total * 100
    print(f"       Nulos imputados: {n_null}/{n_total} ({tasa:.1f}%)")

    resumen = pd.DataFrame({
        'Indicador': ['Total obs.', 'Nulos antes', 'Tasa imputación (%)',
                      'Método primario', 'Método secundario', 'Método terciario',
                      'Nulos post-imputación'],
        'Valor': [n_total, n_null, round(tasa, 2),
                  'Mediana GRUPO_FIGEM × AÑO',
                  'Mediana GRUPO_FIGEM (todos los años)',
                  'Mediana global',
                  int(df['MONTO_FIGEM_IMPUT'].isna().sum())]
    })
    return df, resumen, tasa


# ─────────────────────────────────────────────────────────────────────────────
# 3. VARIABLES PER CÁPITA PARA PANEL
# ─────────────────────────────────────────────────────────────────────────────

def build_percapita(df_long: pd.DataFrame, df_figem_imp: pd.DataFrame) -> pd.DataFrame:
    """
    Población estimada: IADM01 (M$) / IADM10 (M$/hab) = nº habitantes.
    FIGEM per cápita: MONTO_FIGEM_IMPUT / Población.
    Variable dependiente FE: log1p(FIGEM_PER_CAP) — log1p para manejar ceros.
    """
    print("[3/12] Variables per cápita ...", flush=True)
    df = df_long.copy()
    c_ing  = 'IADM01 (M$) Ingresos Municipales (Ingreso Total Percibido)'
    c_disp = 'IADM10 (TAS) Disponibilidad Presupuestaria Municipal por Habitante (M$)'
    df['POBLACION_EST'] = np.where(df[c_disp] > 0, df[c_ing] / df[c_disp], np.nan)

    merge_cols = ['CODIGO', 'AÑO', 'MONTO_FIGEM_IMPUT', 'FLAG_IMPUTADO']
    df = df.merge(df_figem_imp[merge_cols], on=['CODIGO', 'AÑO'], how='left')
    df['FIGEM_PER_CAP'] = np.where(df['POBLACION_EST'] > 0,
                                    df['MONTO_FIGEM_IMPUT'] / df['POBLACION_EST'], np.nan)
    df['LOG_FIGEM_PC']  = np.log1p(df['FIGEM_PER_CAP'].clip(lower=0))

    df = df.rename(columns={
        'AUTONOMIA_FISCAL'                   : 'AUTFISCAL',
        'DEPENDENCIA_FCM'                    : 'DEPFCM',
        'TRANSFERENCIAS_SOBRE_INGRESOS'      : 'TRANSF_ING',
        'IMPUESTOS_SOBRE_INGRESOS'           : 'IMPUEST_ING',
        'GASTO_CORRIENTE_SOBRE_GASTO_TOTAL'  : 'GASTO_CORR',
        'SERV_COMUNITARIOS_SOBRE_GASTO_TOTAL': 'SERV_COM',
    })
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. PCA — DIMENSIÓN DE DESARROLLO
# ─────────────────────────────────────────────────────────────────────────────

def run_pca(df_munic: pd.DataFrame):
    """
    PCA sobre log(DISPONIBILIDAD_x_HAB) y log(IPPP).
    Implementado via SVD sobre matriz estandarizada (numpy).
    PC1 = 'Capacidad fiscal y de desarrollo municipal'.
    """
    print("[4/12] PCA dimensión de desarrollo ...", flush=True)
    df = df_munic.copy()
    df['LOG_DISP_X_HAB'] = np.log1p(df['PROM_DISPONIBILIDAD_PRESUP_X_HAB'].clip(lower=0))
    df['LOG_IPPP']       = np.log1p(df['PROM_IPPP'].clip(lower=0))

    X   = df[['LOG_DISP_X_HAB', 'LOG_IPPP']].values.astype(float)
    mu  = X.mean(axis=0); std = X.std(axis=0, ddof=1)
    std[std == 0] = 1.0
    Xz  = (X - mu) / std
    U, S, Vt = np.linalg.svd(Xz, full_matrices=False)
    scores   = Xz @ Vt.T
    var_exp  = (S**2 / (S**2).sum()) * 100

    df['PCA1_DESARROLLO'] = scores[:, 0]
    df['PCA2_DESARROLLO'] = scores[:, 1]

    print(f"       PCA1: {var_exp[0]:.1f}%  PCA2: {var_exp[1]:.1f}%")

    pca_info = pd.DataFrame({
        'Componente'       : ['PCA1_DESARROLLO', 'PCA2_DESARROLLO'],
        'Varianza_expl_%'  : [round(var_exp[0], 2), round(var_exp[1], 2)],
        'Var_acumulada_%'  : [round(var_exp[0], 2), round(float(var_exp[:2].sum()), 2)],
        'Loading_LOG_DISP' : [round(Vt[0, 0], 4), round(Vt[1, 0], 4)],
        'Loading_LOG_IPPP' : [round(Vt[0, 1], 4), round(Vt[1, 1], 4)],
        'Interpretación'   : ['Capacidad fiscal y desarrollo (+)', 'Contraste disp./ingresos propios'],
    })
    return df, pca_info, float(var_exp[0])


# ─────────────────────────────────────────────────────────────────────────────
# 5. ESTANDARIZACIÓN Z-SCORE
# ─────────────────────────────────────────────────────────────────────────────

def zscore_matrix(df, cols):
    X   = df[cols].values.astype(float)
    mu  = X.mean(axis=0); std = X.std(axis=0, ddof=1)
    std[std == 0] = 1.0
    return (X - mu) / std, mu, std


# ─────────────────────────────────────────────────────────────────────────────
# 6. K-MEANS Y SILHOUETTE (implementación numpy)
# ─────────────────────────────────────────────────────────────────────────────

def _kmeans_pp_init(X, k, rng):
    n = X.shape[0]
    idx = rng.integers(0, n)
    centers = [X[idx]]
    for _ in range(1, k):
        dists = np.array([min(np.sum((x - c)**2) for c in centers) for x in X])
        probs = dists / dists.sum()
        centers.append(X[rng.choice(n, p=probs)])
    return np.array(centers)


def kmeans(X, k, n_init=10, max_iter=300, seed=42):
    best_labels, best_centers, best_inertia = None, None, np.inf
    for run in range(n_init):
        rng     = np.random.default_rng(seed + run)
        centers = _kmeans_pp_init(X, k, rng)
        for _ in range(max_iter):
            dists  = np.linalg.norm(X[:, None] - centers[None, :], axis=2)
            labels = dists.argmin(axis=1)
            new_c  = np.array([
                X[labels == j].mean(axis=0) if (labels == j).any() else centers[j]
                for j in range(k)
            ])
            if np.allclose(new_c, centers, atol=1e-6):
                break
            centers = new_c
        inertia = sum(np.sum((X[labels == j] - centers[j])**2)
                      for j in range(k) if (labels == j).any())
        if inertia < best_inertia:
            best_inertia, best_labels, best_centers = inertia, labels.copy(), centers.copy()
    return best_labels, best_centers, best_inertia


def silhouette_score(X, labels):
    n = X.shape[0]; unique_k = np.unique(labels)
    if len(unique_k) < 2:
        return 0.0
    s = np.zeros(n)
    for i in range(n):
        same = X[labels == labels[i]]
        a_i  = np.mean(np.linalg.norm(same - X[i], axis=1)) if len(same) > 1 else 0.0
        b_i  = min(np.mean(np.linalg.norm(X[labels == k] - X[i], axis=1))
                   for k in unique_k if k != labels[i])
        m    = max(a_i, b_i)
        s[i] = (b_i - a_i) / m if m > 0 else 0.0
    return float(np.mean(s))


# ─────────────────────────────────────────────────────────────────────────────
# 7. EVALUACIÓN K Y CLUSTERING FINAL
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_k(X):
    print(f"[5/12] Evaluando K={K_MIN}..{K_MAX} (puede tardar 1-2 min) ...", flush=True)
    rows = []
    for k in range(K_MIN, K_MAX + 1):
        lbl, _, iner = kmeans(X, k, n_init=N_INIT, max_iter=MAX_ITER, seed=RANDOM_SEED)
        sil  = silhouette_score(X, lbl)
        cnts = [int((lbl == j).sum()) for j in range(k)]
        nota = 'Solución final: equilibrio técnico + interpretabilidad' if k == K_FINAL else ''
        rows.append({'k': k, 'inercia': round(iner, 4), 'silhouette': round(sil, 4),
                     'tamaños': ', '.join(map(str, cnts)), 'criterio': nota})
        print(f"       k={k}: inercia={iner:.1f}, sil={sil:.4f}, n={cnts}", flush=True)
    return pd.DataFrame(rows)


def assign_cluster_typology(centers):
    """
    Asigna etiquetas interpretativas estables a cada centroide.

    La asignación se hace sobre el perfil de los centroides y no sobre el
    identificador crudo de K-means, para que las etiquetas sean comparables
    entre semillas y corridas distintas.
    """
    cdf = pd.DataFrame(centers, columns=CLUSTER_VARS)
    available = set(range(len(cdf)))
    assigned = {}

    # T1: mayor autonomía + desarrollo
    c1 = int((cdf['PROM_AUTONOMIA_FISCAL'] + cdf['PCA1_DESARROLLO']).idxmax())
    assigned[c1] = 1
    available.discard(c1)

    # T2: mayor dependencia estructural del FCM
    c2 = int(cdf.loc[list(available), 'PROM_DEPENDENCIA_FCM'].idxmax())
    assigned[c2] = 2
    available.discard(c2)

    # T3: perfil con mayor autonomía entre los restantes
    c3 = int(cdf.loc[list(available), 'PROM_AUTONOMIA_FISCAL'].idxmax())
    assigned[c3] = 3
    available.discard(c3)

    # T4: centroide restante
    assigned[list(available)[0]] = 4
    return assigned, cdf


def fit_final_clustering(Xz, df_cl):
    print(f"[6/12] Clustering final k={K_FINAL} ...", flush=True)
    labels, centers, inertia = kmeans(Xz, K_FINAL, n_init=N_INIT, max_iter=MAX_ITER, seed=RANDOM_SEED)
    sil = silhouette_score(Xz, labels)

    # Etiquetas interpretativas estables sobre centroides.
    assigned, _ = assign_cluster_typology(centers)

    df_out = df_cl.copy()
    df_out['CLUSTER_FINAL']    = pd.Series(labels).map(assigned).values
    df_out['NOMBRE_CLUSTER']   = df_out['CLUSTER_FINAL'].map(CLUSTER_NAMES)

    mapped_centers = np.zeros_like(centers)
    for raw, tip in assigned.items():
        mapped_centers[tip - 1] = centers[raw]
    lbl1 = df_out['CLUSTER_FINAL'].values
    df_out['DISTANCIA_CENTROIDE'] = np.linalg.norm(Xz - mapped_centers[lbl1 - 1], axis=1)
    for i, v in enumerate(CLUSTER_VARS):
        df_out[f'Z_{v}'] = Xz[:, i]

    dist = {CLUSTER_NAMES[t]: int((df_out['CLUSTER_FINAL'] == t).sum()) for t in range(1, 5)}
    print(f"       Silhouette k=4: {sil:.4f}")
    print(f"       Distribución  : {dist}")
    return df_out, mapped_centers, inertia, sil


# ─────────────────────────────────────────────────────────────────────────────
# 8. DESCRIPTIVOS POR GRUPO FIGEM (Tabla 4.1)
# ─────────────────────────────────────────────────────────────────────────────

def descriptivos_figem(df):
    print("[7/12] Descriptivos por grupo FIGEM ...", flush=True)
    vars_d = ['PROM_AUTONOMIA_FISCAL', 'PROM_DEPENDENCIA_FCM',
              'PROM_TRANSFERENCIAS_SOBRE_INGRESOS', 'PROM_GASTO_CORRIENTE_SOBRE_GASTO_TOTAL',
              'PROM_SERV_COMUNITARIOS_SOBRE_GASTO_TOTAL',
              'PROM_DISPONIBILIDAD_PRESUP_X_HAB', 'PROM_IPPP']
    rows = []
    for grp in sorted(df['GRUPO_FIGEM_MODAL_2016_2024'].dropna().unique()):
        sub = df[df['GRUPO_FIGEM_MODAL_2016_2024'] == grp]
        row = {'GRUPO_FIGEM': int(grp), 'N': len(sub)}
        for v in vars_d:
            s = sub[v].dropna()
            row[f'{v}_media'] = round(float(s.mean()), 4)
            row[f'{v}_sd']    = round(float(s.std(ddof=1)), 4)
            row[f'{v}_cv']    = round(float(s.std(ddof=1)/s.mean()) if s.mean() != 0 else np.nan, 4)
        rows.append(row)
    # Fila global
    row = {'GRUPO_FIGEM': 'GLOBAL', 'N': len(df)}
    for v in vars_d:
        s = df[v].dropna()
        row[f'{v}_media'] = round(float(s.mean()), 4)
        row[f'{v}_sd']    = round(float(s.std(ddof=1)), 4)
        row[f'{v}_cv']    = round(float(s.std(ddof=1)/s.mean()) if s.mean() != 0 else np.nan, 4)
    rows.append(row)
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 9. MATRIZ DE CONFUSIÓN + KAPPA DE COHEN (Tabla 4.3)
# ─────────────────────────────────────────────────────────────────────────────

def confusion_and_kappa(df):
    """
    Resume el desalineamiento entre la clasificación FIGEM y las tipologías
    empíricas mediante:
      1. Matriz de confusión y discrepancia mínima de reclasificación.
      2. Kappa de Cohen como indicador complementario de concordancia.

    Nota: Kappa se interpreta con cautela porque aquí se comparan 5 grupos
    normativos con 4 tipologías empíricas; el hallazgo principal descansa en
    la matriz de confusión y la heterogeneidad intra-grupo.
    """
    print("[8/12] Matriz de confusión FIGEM vs clusters ...", flush=True)
    sub = df.dropna(subset=['GRUPO_FIGEM_MODAL_2016_2024', 'CLUSTER_FINAL']).copy()
    sub['FG'] = sub['GRUPO_FIGEM_MODAL_2016_2024'].astype(int)
    sub['CL'] = sub['CLUSTER_FINAL'].astype(int)

    ct_abs = pd.crosstab(sub['FG'], sub['CL'])
    ct_pct = pd.crosstab(sub['FG'], sub['CL'], normalize='index').round(4)

    # Kappa
    all_vals = sorted(set(sub['FG'].unique()) | set(sub['CL'].unique()))
    v2i = {v: i for i, v in enumerate(all_vals)}
    nc  = len(all_vals); n = len(sub)
    C   = np.zeros((nc, nc), dtype=int)
    for _, row in sub.iterrows():
        C[v2i[row['FG']], v2i[row['CL']]] += 1
    po = np.trace(C) / n
    pe = (C.sum(axis=1) @ C.sum(axis=0)) / n**2
    kappa = (po - pe) / (1 - pe) if (1 - pe) != 0 else 0.0

    # Concordancia máxima (asignación óptima fila → cluster)
    total_match = 0
    for fg in sub['FG'].unique():
        row_s = ct_abs.loc[fg] if fg in ct_abs.index else pd.Series()
        total_match += int(row_s.max()) if len(row_s) > 0 else 0
    conc  = total_match / n * 100
    disc  = 100 - conc

    if kappa >= 0.6:
        interp = 'Sustancial'
    elif kappa >= 0.4:
        interp = 'Moderada'
    elif kappa >= 0.0:
        interp = 'Débil'
    else:
        interp = 'Nula o menor al azar (complementario)'
    kappa_res = pd.DataFrame({
        'Indicador': ['N municipios', 'Po (concordancia observada)',
                      'Pe (concordancia esperada azar)', 'Kappa de Cohen',
                      'Interpretación', 'Concordancia máxima (%)', 'Discrepancia (%)',
                      'Nota metodológica'],
        'Valor': [n, round(po, 4), round(pe, 4), round(kappa, 4),
                  interp, round(conc, 1), round(disc, 1),
                  'Kappa se reporta como complemento; la evidencia principal es la matriz de confusión']
    })
    print(f"       Kappa={kappa:.4f} ({interp}), Discrepancia={disc:.1f}%")
    return ct_abs, ct_pct, kappa_res, kappa, disc


# ─────────────────────────────────────────────────────────────────────────────
# 10. MODELO PANEL EFECTOS FIJOS — Within Estimator (Tabla 4.4)
# ─────────────────────────────────────────────────────────────────────────────

def panel_fixed_effects(df_panel: pd.DataFrame):
    """
    Within Estimator (efectos fijos por municipio + dummies de año).
    Especificación:
        log(FIGEM_pc_it) = α_i + β1·AUTFISCAL + β2·DEPFCM
                         + β3·TRANSF_ING + β4·GASTO_CORR + γ_t + ε_it
    SE robustos HC3 (Long & Ervin, 2000) para corregir heteroscedasticidad.
    Elección EF sobre EA justificada: efectos municipales correlacionados
    con regresores (Wooldridge, 2010, §10.5).
    """
    print("[9/12] Modelo panel efectos fijos ...", flush=True)

    dep  = 'LOG_FIGEM_PC'
    indv = ['AUTFISCAL', 'DEPFCM', 'TRANSF_ING', 'GASTO_CORR']
    id_v = 'CODIGO'; yr_v = 'AÑO'

    cols_need = [id_v, yr_v, dep] + indv
    df_fe = df_panel[cols_need].dropna().copy()
    df_fe[yr_v] = df_fe[yr_v].astype(int)

    years     = sorted(df_fe[yr_v].unique())
    yr_dums   = []
    for yr in years[1:]:
        col = f'D_{yr}'; df_fe[col] = (df_fe[yr_v] == yr).astype(float); yr_dums.append(col)

    all_x = indv + yr_dums

    # Within transform: X_it - mean_i(X) + mean(X)
    gm = df_fe.groupby(id_v)[all_x + [dep]].transform('mean')
    glo = df_fe[all_x + [dep]].mean()
    W = pd.DataFrame()
    for v in all_x + [dep]:
        W[f'W_{v}'] = df_fe[v] - gm[v] + glo[v]

    Wy = W[f'W_{dep}'].values
    WX = W[[f'W_{v}' for v in all_x]].values

    betas, _, _, _ = np.linalg.lstsq(WX.T @ WX, WX.T @ Wy, rcond=None)
    resid = Wy - WX @ betas
    n_obs = len(Wy); k = WX.shape[1]

    # HC3 SE
    H    = WX @ np.linalg.pinv(WX.T @ WX) @ WX.T
    h    = np.clip(np.diag(H), 0, 1 - 1e-8)
    e3   = resid / (1 - h)
    meat = sum((e3[i]**2) * np.outer(WX[i], WX[i]) for i in range(n_obs))
    V    = np.linalg.pinv(WX.T @ WX) @ meat @ np.linalg.pinv(WX.T @ WX)
    se   = np.sqrt(np.diag(V))
    t_s  = betas / np.where(se > 0, se, 1e-10)

    # p-valores aproximados (normal estándar, válido para n>1000)
    p_vals = [float(2 * (1 - _norm_cdf(abs(t)))) for t in t_s]

    ss_res = float(resid @ resid)
    ss_tot = float(np.sum((Wy - Wy.mean())**2))
    r2w    = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    labels_fe = {
        'AUTFISCAL' : 'Autonomía fiscal (IPP/IT)',
        'DEPFCM'    : 'Dependencia FCM',
        'TRANSF_ING': 'Transferencias / Ingresos',
        'GASTO_CORR': 'Gasto corriente / Gasto total',
    }
    rows = []
    for i, v in enumerate(all_x):
        if v not in indv: continue
        pv = p_vals[i]
        sig = '***' if pv<0.01 else ('**' if pv<0.05 else ('*' if pv<0.10 else ''))
        rows.append({'Variable': labels_fe.get(v, v),
                     'Coef.': round(float(betas[i]), 4),
                     'SE HC3': round(float(se[i]), 4),
                     't': round(float(t_s[i]), 3),
                     'p (aprox)': round(pv, 4), 'Sig.': sig})
    rows += [
        {'Variable': '─── Estadísticos del modelo ───', 'Coef.': '', 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
        {'Variable': 'N observaciones', 'Coef.': n_obs, 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
        {'Variable': 'Efectos fijos', 'Coef.': 'Municipio + Año', 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
        {'Variable': 'R² within', 'Coef.': round(r2w, 4), 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
        {'Variable': 'Errores estándar', 'Coef.': 'Robustos HC3', 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
        {'Variable': '*** p<0.01  ** p<0.05  * p<0.10', 'Coef.': '', 'SE HC3': '', 't': '', 'p (aprox)': '', 'Sig.': ''},
    ]

    df_res = pd.DataFrame(rows)
    for r in rows[:len(indv)]:
        print(f"       β {r['Variable'][:25]:<25} = {r['Coef.']:>7}  p≈{r['p (aprox)']}{r['Sig.']}")
    print(f"       R² within = {r2w:.4f}  |  N = {n_obs:,}")
    return df_res, r2w, n_obs


def _norm_cdf(z):
    """CDF N(0,1) aproximada (Abramowitz & Stegun 26.2.17)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
           + t * (-1.821255978 + t * 1.330274429))))
    p = 1.0 - (1.0 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * z**2) * poly
    return p if z >= 0 else 1.0 - p


# ─────────────────────────────────────────────────────────────────────────────
# 11. PRUEBAS DE ROBUSTEZ
# ─────────────────────────────────────────────────────────────────────────────

def robustness_tests(Xz, df_final, base_inertia, base_silhouette, base_seed=RANDOM_SEED):
    print("[10/12] Robustez (10 semillas) ...", flush=True)
    rows   = []
    labels_all = []
    ref_lbl = df_final['CLUSTER_FINAL'].values
    for seed in ROBUSTNESS_SEEDS:
        lbl_raw, centers, iner = kmeans(Xz, K_FINAL, n_init=N_INIT, max_iter=MAX_ITER, seed=seed)
        assigned, _ = assign_cluster_typology(centers)
        lbl = pd.Series(lbl_raw).map(assigned).values
        sil = silhouette_score(Xz, lbl_raw)
        rows.append({'semilla': seed, 'inercia': round(iner, 4), 'silhouette': round(sil, 4)})
        labels_all.append(lbl)

    df_seed = pd.DataFrame(rows)
    labels_all = np.array(labels_all)
    stab = np.mean([Counter(labels_all[:, i]).most_common(1)[0][1] / len(ROBUSTNESS_SEEDS)
                    for i in range(Xz.shape[0])])
    base_agreement = float(np.mean([np.mean(lbl == ref_lbl) for lbl in labels_all]))

    rob_sum = pd.DataFrame({
        'Indicador': ['Corrida principal (seed)',
                      'Inercia corrida principal',
                      'Silhouette corrida principal',
                      'Semillas robustez',
                      'Semillas evaluadas',
                      'Inercia mín',
                      'Inercia máx',
                      'Silhouette mín',
                      'Silhouette máx',
                      'Estabilidad media de asignación (%)',
                      'Acuerdo medio con corrida base (%)',
                      'Nota metodológica'],
        'Valor': [base_seed,
                  round(float(base_inertia), 4),
                  round(float(base_silhouette), 4),
                  '0-9',
                  len(ROBUSTNESS_SEEDS),
                  round(df_seed['inercia'].min(), 4),
                  round(df_seed['inercia'].max(), 4),
                  round(df_seed['silhouette'].min(), 4),
                  round(df_seed['silhouette'].max(), 4),
                  f'{stab*100:.1f}%',
                  f'{base_agreement*100:.1f}%',
                  'La corrida principal usa seed=42; las semillas 0-9 evalúan sensibilidad y pueden diferir marginalmente en inercia/silhouette.']
    })
    print(f"       Estabilidad: {stab*100:.1f}% | acuerdo base: {base_agreement*100:.1f}%")
    return df_seed, rob_sum


# ─────────────────────────────────────────────────────────────────────────────
# 12. TABLAS AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def build_centroids_table(df_final, mu, std):
    rows = []
    for t in range(1, K_FINAL + 1):
        sub = df_final[df_final['CLUSTER_FINAL'] == t]
        row = {'CLUSTER': t, 'NOMBRE': CLUSTER_NAMES[t],
               'N': len(sub), 'PCT%': round(len(sub)/len(df_final)*100, 1)}
        for i, v in enumerate(CLUSTER_VARS):
            vals = sub[v].dropna()
            row[f'{v}_media'] = round(float(vals.mean()), 4)
            row[f'{v}_sd']    = round(float(vals.std(ddof=1)), 4)
            row[f'Z_{v}']     = round(float((vals.mean()-mu[i])/std[i]), 4) if std[i] > 0 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def build_emblematic(df_final):
    parts = []
    for t in range(1, K_FINAL + 1):
        sub = df_final[df_final['CLUSTER_FINAL'] == t].nsmallest(8, 'DISTANCIA_CENTROIDE').copy()
        sub['RANK'] = range(1, len(sub) + 1)
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# 13. CONSTRUCCIÓN OUTPUT EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def build_output(df_final, df_eval_k, df_desc,
                 ct_abs, ct_pct, kappa_res, kappa, disc,
                 df_fe, r2w, n_fe,
                 df_seed, rob_sum,
                 cent_df, embl_df,
                 pca_info, imp_res, mu_z, std_z):

    sil4 = df_eval_k.loc[df_eval_k['k'] == K_FINAL, 'silhouette'].iloc[0]
    n    = len(df_final)
    dist_n = {CLUSTER_NAMES[t]: int((df_final['CLUSTER_FINAL']==t).sum()) for t in range(1,5)}
    dist_p = {k: round(v/n*100,1) for k,v in dist_n.items()}

    leeme = pd.DataFrame({
        'Hoja': ['00_Leeme','01_Imputacion_FIGEM','02_PCA_desarrollo','03_Evaluacion_k',
                 '04_Centroides_k4','05_Base_municipal_final','06_Descriptivos_FIGEM',
                 '07_ConfMatrix_abs','08_ConfMatrix_pct','09_Kappa_Cohen',
                 '10_Panel_FE','11_Casos_emblematicos','12_Robustez_semillas',
                 '13_Robustez_resumen','14_Resumen_tesis','15_Diccionario','16_Fuentes_APA'],
        'Descripcion': [
            'Índice y trazabilidad del Output',
            'Diagnóstico imputación MONTO_FIGEM (Sección 3.2)',
            'PCA dimensión de desarrollo — Tabla 3.1',
            'Evaluación K-means k=2..6 — método codo + silhouette',
            'Centroides k=4 escala original + Z-score — Tabla 4.2',
            'Base municipal final con cluster asignado (N=345)',
            'Descriptivos por grupo FIGEM — Tabla 4.1',
            'Matriz de confusión FIGEM vs cluster (valores absolutos)',
            'Matriz de confusión FIGEM vs cluster (proporciones fila)',
            'Kappa de Cohen y métricas de concordancia — Tabla 4.3',
            'Modelo panel efectos fijos (within+HC3) — Tabla 4.4',
            'Casos emblemáticos top-8 por tipología',
            'Robustez: 10 semillas — inercia y silhouette',
            'Resumen robustez + estabilidad de asignación',
            'Resumen operativo para redacción del Word',
            'Diccionario de variables',
            'Fuentes bibliográficas APA 7',
        ]
    })

    tasa_imp = imp_res.loc[imp_res['Indicador']=='Tasa imputación (%)','Valor'].iloc[0]
    pc1_var  = pca_info.loc[pca_info['Componente']=='PCA1_DESARROLLO','Varianza_expl_%'].iloc[0]

    resumen = pd.DataFrame({
        'Indicador': [
            'Input utilizado', 'Período', 'Unidad analítica', 'N municipios',
            'Método clustering', 'Seed corrida principal', 'K final', f'Silhouette K={K_FINAL}',
            'Kappa de Cohen', 'Discrepancia FIGEM vs Clusters (%)',
            f'T1 – {CLUSTER_NAMES[1]}', f'T2 – {CLUSTER_NAMES[2]}',
            f'T3 – {CLUSTER_NAMES[3]}', f'T4 – {CLUSTER_NAMES[4]}',
            'R² within (FE)', 'N obs. modelo FE',
            'Tasa imputación FIGEM (%)', 'PCA1 varianza explicada (%)',
        ],
        'Valor': [
            INPUT_FILE.name, '2016–2024', 'Municipio (promedios 2016-2024)', n,
            f'K-means (K-means++, n_init={N_INIT}, seed={RANDOM_SEED})',
            RANDOM_SEED, K_FINAL, round(float(sil4), 4),
            round(kappa, 4), round(disc, 1),
            f'{dist_n[CLUSTER_NAMES[1]]} comunas ({dist_p[CLUSTER_NAMES[1]]}%)',
            f'{dist_n[CLUSTER_NAMES[2]]} comunas ({dist_p[CLUSTER_NAMES[2]]}%)',
            f'{dist_n[CLUSTER_NAMES[3]]} comunas ({dist_p[CLUSTER_NAMES[3]]}%)',
            f'{dist_n[CLUSTER_NAMES[4]]} comunas ({dist_p[CLUSTER_NAMES[4]]}%)',
            round(r2w, 4), n_fe, round(float(tasa_imp), 1), round(float(pc1_var), 1),
        ]
    })

    dic = pd.DataFrame([
        ('PROM_AUTONOMIA_FISCAL','Autonomía fiscal','IPP/IT promedio 2016-2024','Ratio'),
        ('PROM_DEPENDENCIA_FCM','Dep. FCM','FCM/IT promedio 2016-2024','Ratio'),
        ('PROM_TRANSFERENCIAS_SOBRE_INGRESOS','Transf./IT','Transferencias/IT 2016-2024','Ratio'),
        ('PROM_GASTO_CORRIENTE_SOBRE_GASTO_TOTAL','Gasto corr./GT','Gasto corriente/GT 2016-2024','Ratio'),
        ('PROM_SERV_COMUNITARIOS_SOBRE_GASTO_TOTAL','Serv.com./GT','Serv. comunitarios/GT 2016-2024','Ratio'),
        ('PCA1_DESARROLLO','PCA1 desarrollo','PC1 de log(Disp.x hab)+log(IPPP)','PCA'),
        ('CLUSTER_FINAL','Tipología','Cluster K-means (1–4)','Categórica'),
        ('DISTANCIA_CENTROIDE','Dist. centroide','Norma L2 espacio Z-score','Adimensional'),
        ('MONTO_FIGEM_IMPUT','FIGEM imputado','Monto FIGEM + imput. mediana grupo-año','M$ CLP'),
        ('LOG_FIGEM_PC','log(FIGEM pc)','log1p(FIGEM_IMPUT/Pob_est)','ln(M$)'),
        ('AUTFISCAL','Autonomía panel','IPP/IT obs. anuales (panel)','Ratio'),
        ('DEPFCM','Dep. FCM panel','FCM/IT obs. anuales (panel)','Ratio'),
    ], columns=['Variable','Nombre_corto','Definición','Transformación'])

    fuentes = pd.DataFrame([
        ('Arthur, D., & Vassilvitskii, S.','2007','K-means++: The advantages of careful seeding',
         'Proc. 18th SODA, 1027–1035','https://dl.acm.org/doi/10.5555/1283383.1283494'),
        ('Bahl, R., & Linn, J.','1992','Urban public finance in developing countries',
         'Oxford University Press','ISBN: 9780195207477'),
        ('Biblioteca del Congreso Nacional de Chile','2020','Fondo Común Municipal: ingresos y distribución',
         'Asesoría Técnica Parlamentaria','https://obtienearchivo.bcn.cl/obtienearchivo?id=repositorio/10221/28638/1/BCN_FCM_ingresos_y_distribucion_GD_def.pdf'),
        ('Bravo, J.','2014','Fondo Común Municipal y su desincentivo a la recaudación en Chile',
         'Centro de Políticas Públicas UC, Serie N°68','https://politicaspublicas.uc.cl/publicacion/serie-n-68-fondo-comun-municipal-y-su-desincentivo-a-la-recaudacion-en-chile/'),
        ('CEPAL','2019','Descentralización fiscal: los ingresos municipales y regionales en Chile',
         'Naciones Unidas','https://repositorio.cepal.org/handle/11362/7397'),
        ('Cohen, J.','1960','A coefficient of agreement for nominal scales',
         'Educational and Psychological Measurement, 20(1), 37–46','https://doi.org/10.1177/001316446002000104'),
        ('Denzin, N. K.','1970','The research act: A theoretical introduction to sociological methods',
         'Aldine Publishing Company','OCLC: 109440'),
        ('DIPRES','2013','Eficiencia de los gobiernos locales y sus determinantes',
         'Documentos DIPRES','https://www.dipres.gob.cl/598/articles-114713_doc_pdf.pdf'),
        ('Henríquez, M., & Fuenzalida, C.','2011','Compensando la desigualdad de ingresos locales: el FCM en Chile',
         'Revista Iberoamericana de Estudios Municipales, 4, 73–104','https://doi.org/10.32457/riem.vi4.421'),
        ('Hernández Sampieri, R., Fernández, C., & Baptista, P.','2014','Metodología de la investigación (6ª ed.)',
         'McGraw-Hill Education','ISBN: 9781456223960'),
        ('Holmstrom, B.','1979','Moral hazard and observability',
         'Bell Journal of Economics, 10(1), 74–91','https://doi.org/10.2307/3003319'),
        ('Hood, C.','1991','A public management for all seasons?',
         'Public Administration, 69(1), 3–19','https://doi.org/10.1111/j.1467-9299.1991.tb00779.x'),
        ('Jain, A. K.','2010','Data clustering: 50 years beyond K-means',
         'Pattern Recognition Letters, 31(8), 651–666','https://doi.org/10.1016/j.patrec.2009.09.011'),
        ('Little, R. J. A., & Rubin, D. B.','2019','Statistical analysis with missing data (3rd ed.)',
         'Wiley','https://doi.org/10.1002/9781119013563'),
        ('Long, J. S., & Ervin, L. H.','2000','Using heteroscedasticity consistent standard errors in the linear regression model',
         'The American Statistician, 54(3), 217–224','https://doi.org/10.1080/00031305.2000.10474549'),
        ('MacQueen, J.','1967','Some methods for classification and analysis of multivariate observations',
         'Proc. 5th Berkeley Symp. Math. Stat. Prob., 1, 281–297','https://projecteuclid.org/euclid.bsmsp/1200512992'),
        ('Martínez, J., Salazar, C., & Améstica-Rivas, L.','2020','¿Son los gobiernos locales más eficientes cuando su coalición política está en el Gobierno central?',
         'Estudios de Economía, 47(1), 49–75','https://doi.org/10.4067/s0718-52862020000100049'),
        ('OECD','2017','Making decentralisation work in Chile: Towards stronger municipalities',
         'OECD Multi-level Governance Studies','https://doi.org/10.1787/9789264279049-en'),
        ('Rousseeuw, P. J.','1987','Silhouettes: A graphical aid to the interpretation and validation of cluster analysis',
         'Journal of Computational and Applied Mathematics, 20, 53–65','https://doi.org/10.1016/0377-0427(87)90125-7'),
        ('SUBDERE','2025','Fondo de Incentivo a la Gestión Municipal (FIGEM)',
         'Ministerio del Interior y Seguridad Pública','https://www.subdere.gov.cl/programas/figem'),
        ('SUBDERE','2025','Sistema Nacional de Información Municipal (SINIM)',
         'Ministerio del Interior y Seguridad Pública','https://www.sinim.gov.cl/'),
        ('Wooldridge, J. M.','2010','Econometric analysis of cross section and panel data (2nd ed.)',
         'MIT Press','ISBN: 9780262232586'),
        ('González-Gómez, F., & Guardiola, J.','2010','Descentralización fiscal en América Latina: impacto social y determinantes',
         'Investigación Económica, 69(273), 73–91','https://doi.org/10.22201/fe.01851667p.2010.273.23891'),
    ], columns=['Autor(es)','Año','Título','Fuente/Revista','DOI/URL'])

    return {
        '00_Leeme'             : leeme,
        '01_Imputacion_FIGEM'  : imp_res,
        '02_PCA_desarrollo'    : pca_info,
        '03_Evaluacion_k'      : df_eval_k,
        '04_Centroides_k4'     : cent_df,
        '05_Base_municipal_final': df_final,
        '06_Descriptivos_FIGEM': df_desc,
        '07_ConfMatrix_abs'    : ct_abs.reset_index(),
        '08_ConfMatrix_pct'    : ct_pct.reset_index(),
        '09_Kappa_Cohen'       : kappa_res,
        '10_Panel_FE'          : df_fe,
        '11_Casos_emblematicos': embl_df,
        '12_Robustez_semillas' : df_seed,
        '13_Robustez_resumen'  : rob_sum,
        '14_Resumen_tesis'     : resumen,
        '15_Diccionario'       : dic,
        '16_Fuentes_APA'       : fuentes,
    }


def write_output(sheets):
    print(f"[11/12] Escribiendo {OUTPUT_FILE.name} ...", flush=True)
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    print(f"        → {OUTPUT_FILE}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  Clustering_USACH.py  —  Pipeline tesis USACH")
    print(f"  Input  : {INPUT_FILE.name}")
    print(f"  Output : {OUTPUT_FILE.name}")
    print("=" * 65)

    df_long, df_munic, df_figem = load_data()
    df_fig_imp, imp_res, tasa_imp = impute_figem(df_figem)
    df_panel   = build_percapita(df_long, df_fig_imp)
    df_munic2, pca_info, pc1v = run_pca(df_munic)

    missing = [c for c in CLUSTER_VARS if c not in df_munic2.columns]
    if missing:
        raise ValueError(f"Columnas faltantes: {missing}")

    df_cl = df_munic2.dropna(subset=CLUSTER_VARS).copy()
    print(f"       Municipios para clustering: {len(df_cl)}")
    Xz, mu_z, std_z = zscore_matrix(df_cl, CLUSTER_VARS)

    df_eval   = evaluate_k(Xz)
    df_final, mapped_c, iner4, sil4 = fit_final_clustering(Xz, df_cl)
    df_desc   = descriptivos_figem(df_final)
    ct_abs, ct_pct, kappa_res, kappa, disc = confusion_and_kappa(df_final)
    df_fe, r2w, n_fe = panel_fixed_effects(df_panel)
    df_seed, rob_sum = robustness_tests(Xz, df_final, iner4, sil4)

    cent_df  = build_centroids_table(df_final, mu_z, std_z)
    embl_df  = build_emblematic(df_final)

    print("[11/12] Construyendo output ...", flush=True)
    sheets = build_output(df_final, df_eval, df_desc,
                          ct_abs, ct_pct, kappa_res, kappa, disc,
                          df_fe, r2w, n_fe,
                          df_seed, rob_sum,
                          cent_df, embl_df,
                          pca_info, imp_res, mu_z, std_z)
    write_output(sheets)

    print("[12/12] QA ...", flush=True)
    import openpyxl
    wb = openpyxl.load_workbook(OUTPUT_FILE)
    print(f"        Hojas: {wb.sheetnames}")
    print()
    print("✓ Pipeline completado.")
    print(f"  Silhouette K=4 : {sil4:.4f}")
    print(f"  Kappa Cohen    : {kappa:.4f}")
    print(f"  Discrepancia   : {disc:.1f}%")
    print(f"  R² within FE   : {r2w:.4f}")
    print("=" * 65)


if __name__ == '__main__':
    main()
