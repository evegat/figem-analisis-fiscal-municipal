#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generador_graficos_USACH.py
============================
Genera las 6 figuras de la tesis desde Output_USACH.xlsx.
Estilo uniforme, profesional, listo para defensa.

Figuras:
  1. fig_elbow_silhouette.png   — Evaluación de k (codo + silhouette)
  2. fig_clusters_distribucion.png — Distribución de municipios por tipología
  3. fig_pca_biplot.png          — Biplot PCA1 vs Autonomía Fiscal
  4. fig_confusion_heatmap.png   — Matriz de confusión FIGEM vs Clústeres
  5. fig_boxplots_autonomia.png  — Dispersión autonomía por grupo FIGEM
  6. fig_coeficientes_fe.png     — Coeficientes del modelo FE con IC 95%

EJECUCIÓN:
    python generador_graficos_USACH.py
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

# ─── Configuración global uniforme ────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

OUTPUT_FILE = 'Output_USACH.xlsx'
FIGURAS_DIR = 'figuras'

# Paleta consistente para los 4 clústeres
CLUSTER_COLORS = {
    'Autónomos Urbanos Estables': '#2166AC',   # azul
    'Dependientes Estructurales': '#D6604D',    # rojo
    'Mineras Volátiles': '#F4A742',             # amarillo/dorado
    'Rurales Estables': '#1B7837',              # verde
}

CLUSTER_ORDER = [
    'Autónomos Urbanos Estables',
    'Dependientes Estructurales',
    'Mineras Volátiles',
    'Rurales Estables',
]


def generar_graficos():
    os.makedirs(FIGURAS_DIR, exist_ok=True)
    print("[*] Leyendo datos desde Output_USACH.xlsx...")

    df_eval = pd.read_excel(OUTPUT_FILE, sheet_name='03_Evaluacion_k')
    df_mun  = pd.read_excel(OUTPUT_FILE, sheet_name='05_Base_municipal_final')
    df_conf_abs = pd.read_excel(OUTPUT_FILE, sheet_name='07_ConfMatrix_abs', index_col=0)
    df_fe   = pd.read_excel(OUTPUT_FILE, sheet_name='10_Panel_FE').dropna(subset=['Coef.'])

    # -----------------------------------------------------------------
    # 1. fig_elbow_silhouette.png
    # -----------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()
    ax2.spines['right'].set_visible(True)
    ax2.spines['top'].set_visible(False)

    k_vals = df_eval['k']
    ax1.plot(k_vals, df_eval['inercia'], 'o-', color='#2166AC', linewidth=2,
             markersize=8, label='Inercia (Codo)', zorder=3)
    ax2.plot(k_vals, df_eval['silhouette'], 's-', color='#D6604D', linewidth=2,
             markersize=8, label='Silhouette', zorder=3)

    # Marcar k=4 seleccionado
    k4_idx = df_eval[df_eval['k'] == 4].index[0]
    ax1.plot(4, df_eval.loc[k4_idx, 'inercia'], 'o', color='#2166AC',
             markersize=14, markerfacecolor='none', markeredgewidth=2.5, zorder=4)
    ax2.plot(4, df_eval.loc[k4_idx, 'silhouette'], 's', color='#D6604D',
             markersize=14, markerfacecolor='none', markeredgewidth=2.5, zorder=4)

    ax1.set_xlabel('k (número de clústeres)')
    ax1.set_ylabel('Inercia', color='#2166AC')
    ax2.set_ylabel('Coeficiente Silhouette', color='#D6604D')
    ax1.tick_params(axis='y', colors='#2166AC')
    ax2.tick_params(axis='y', colors='#D6604D')
    ax1.set_xticks(k_vals)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='center right')

    plt.title('Evaluación del número óptimo de clústeres (k=2..6)')
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_elbow_silhouette.png')
    plt.close()
    print("  [✓] fig_elbow_silhouette.png")

    # -----------------------------------------------------------------
    # 2. fig_clusters_distribucion.png
    # -----------------------------------------------------------------
    counts = df_mun['NOMBRE_CLUSTER'].value_counts()
    counts = counts.reindex(CLUSTER_ORDER)
    pcts = (counts / counts.sum() * 100).round(1)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(CLUSTER_ORDER)), pcts.values,
                   color=[CLUSTER_COLORS[c] for c in CLUSTER_ORDER],
                   edgecolor='white', linewidth=0.5, height=0.6)

    ax.set_yticks(range(len(CLUSTER_ORDER)))
    ax.set_yticklabels(CLUSTER_ORDER)
    ax.set_xlabel('Porcentaje del total')
    ax.set_title('Distribución de municipios por tipología de clúster')
    ax.invert_yaxis()

    for bar, pct, n in zip(bars, pcts.values, counts.values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{pct}%  (n={n})', va='center', fontweight='bold', fontsize=11)

    ax.set_xlim(0, max(pcts.values) + 8)
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_clusters_distribucion.png')
    plt.close()
    print("  [✓] fig_clusters_distribucion.png")

    # -----------------------------------------------------------------
    # 3. fig_pca_biplot.png
    # -----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 7))
    for cluster in CLUSTER_ORDER:
        mask = df_mun['NOMBRE_CLUSTER'] == cluster
        ax.scatter(df_mun.loc[mask, 'PCA1_DESARROLLO'],
                   df_mun.loc[mask, 'PROM_AUTONOMIA_FISCAL'],
                   color=CLUSTER_COLORS[cluster], label=cluster,
                   s=50, alpha=0.75, edgecolors='white', linewidth=0.3)

    ax.set_xlabel('PCA1 Desarrollo')
    ax.set_ylabel('Autonomía Fiscal')
    ax.set_title('Biplot: Desarrollo (PCA1) vs Autonomía Fiscal por Clúster')
    ax.legend(title='Tipología', loc='upper left', framealpha=0.9)
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_pca_biplot.png')
    plt.close()
    print("  [✓] fig_pca_biplot.png")

    # -----------------------------------------------------------------
    # 4. fig_confusion_heatmap.png  (CORREGIDO: 5 grupos FIGEM × 4 clústeres)
    # -----------------------------------------------------------------
    # df_conf_abs tiene índice FG (1-5) y columnas (1-4)
    cluster_names_short = {
        1: 'C1: Autónomos\nUrbanos',
        2: 'C2: Dependientes\nEstructurales',
        3: 'C3: Mineras\nVolátiles',
        4: 'C4: Rurales\nEstables',
    }
    figem_names = {i: f'FIGEM {i}' for i in range(1, 6)}

    # Renombrar para el gráfico
    cm = df_conf_abs.copy()
    cm.index = [figem_names.get(i, str(i)) for i in cm.index]
    cm.columns = [cluster_names_short.get(c, str(c)) for c in cm.columns]

    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(cm.values, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(range(len(cm.columns)))
    ax.set_xticklabels(cm.columns, fontsize=9)
    ax.set_yticks(range(len(cm.index)))
    ax.set_yticklabels(cm.index)
    ax.set_xlabel('Clústeres finales (tipología empírica)')
    ax.set_ylabel('Grupos FIGEM (clasificación normativa)')
    ax.set_title('Matriz de Confusión: Clustering vs FIGEM (valores absolutos)')

    # Anotar valores
    for i in range(len(cm.index)):
        for j in range(len(cm.columns)):
            val = int(cm.iloc[i, j])
            color = 'white' if val > cm.values.max() * 0.6 else 'black'
            ax.text(j, i, str(val), ha='center', va='center',
                    fontsize=14, fontweight='bold', color=color)

    fig.colorbar(im, ax=ax, label='Frecuencia', shrink=0.8)
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_confusion_heatmap.png')
    plt.close()
    print("  [✓] fig_confusion_heatmap.png")

    # -----------------------------------------------------------------
    # 5. fig_boxplots_autonomia.png
    # -----------------------------------------------------------------
    # Boxplots de autonomía fiscal por grupo FIGEM modal
    fig, ax = plt.subplots(figsize=(10, 6))
    figem_groups = sorted(df_mun['GRUPO_FIGEM_MODAL_2016_2024'].dropna().unique())
    group_colors = ['#4393C3', '#D6604D', '#F4A742', '#1B7837', '#9970AB']

    data_groups = [df_mun.loc[df_mun['GRUPO_FIGEM_MODAL_2016_2024'] == g, 'PROM_AUTONOMIA_FISCAL'].dropna()
                   for g in figem_groups]

    bp = ax.boxplot(data_groups, patch_artist=True, widths=0.5,
                    medianprops=dict(color='darkred', linewidth=2))

    for patch, color in zip(bp['boxes'], group_colors[:len(figem_groups)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xticklabels([f'Grupo {int(g)}' for g in figem_groups])
    ax.set_xlabel('Grupo FIGEM Modal 2016-2024')
    ax.set_ylabel('Autonomía Fiscal (Promedio)')
    ax.set_title('Distribución de Autonomía Fiscal por grupo FIGEM')
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_boxplots_autonomia.png')
    plt.close()
    print("  [✓] fig_boxplots_autonomia.png")

    # -----------------------------------------------------------------
    # 6. fig_coeficientes_fe.png
    # -----------------------------------------------------------------
    df_fe_plot = df_fe[~df_fe['Variable'].isin([
        'N observaciones', 'Efectos fijos', 'R² within', 'Errores estándar',
        '─── Estadísticos del modelo ───', '*** p<0.01  ** p<0.05  * p<0.10'
    ])].copy()

    df_fe_plot['Coef.'] = pd.to_numeric(df_fe_plot['Coef.'])
    df_fe_plot['SE HC3'] = pd.to_numeric(df_fe_plot['SE HC3'])

    # Nombres cortos para el gráfico
    short_names = {
        'Autonomía fiscal (IPP/IT)': 'Autonomía Fiscal',
        'Dependencia FCM': 'Dependencia FCM',
        'Transferencias / Ingresos': 'Transferencias',
        'Gasto corriente / Gasto total': 'Gasto Corriente',
    }
    df_fe_plot['Label'] = df_fe_plot['Variable'].map(short_names).fillna(df_fe_plot['Variable'])

    variables = df_fe_plot['Label'].values[::-1]
    coefs = df_fe_plot['Coef.'].values[::-1]
    errors = (df_fe_plot['SE HC3'].values * 1.96)[::-1]

    fig, ax = plt.subplots(figsize=(10, 5))
    y_pos = range(len(variables))

    # Barras horizontales con IC
    bars = ax.barh(y_pos, coefs, color='#5A7D9A', edgecolor='white',
                   height=0.5, alpha=0.85, zorder=2)

    # Error bars
    ax.errorbar(coefs, y_pos, xerr=errors, fmt='none', color='black',
                capsize=5, capthick=1.5, elinewidth=1.5, zorder=3)

    # Anotar valores
    for i, (c, e) in enumerate(zip(coefs, errors)):
        ax.text(c, i, f'{c:.2f}', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    ax.axvline(0, color='red', linestyle='--', alpha=0.6, linewidth=1, zorder=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(variables)
    ax.set_xlabel('Coeficiente (valor ± IC 95%)')
    ax.set_title('Coeficientes del Modelo de Panel FE con IC 95%')
    plt.tight_layout()
    plt.savefig(f'{FIGURAS_DIR}/fig_coeficientes_fe.png')
    plt.close()
    print("  [✓] fig_coeficientes_fe.png")

    print("\n[*] Generación completa. 6 figuras en figuras/")


if __name__ == "__main__":
    generar_graficos()
