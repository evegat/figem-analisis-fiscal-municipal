# Empirical Validation of FIGEM in Chilean Municipalities

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Reproducible Research](https://img.shields.io/badge/Open%20Science-Reproducible-green.svg)](#)

[ 🇪🇸 Versión en Español ](README.md) · [ 🇬🇧 English version ](README.en.md)

Open-source and reproducible research repository for the econometric and multivariate study on the **Municipal Management Incentive Fund (FIGEM)** in Chile.

> 📄 **Academic Reference:**  
> Montecinos García, R. S., & Vega Toledo, E. (2025). *“Validación empírica del FIGEM en municipios chilenos: tipologías fiscales, clustering y evaluación de desempeño”*. Revista Políticas Públicas, 18(2), 3-21.

---

## 🎯 Research Abstract

FIGEM is one of the primary performance-based intergovernmental fiscal transfer mechanisms in Chile. This study provides an empirical assessment of its distributive equity, structural incentives, and policy impact through:

1. **Dimensionality Reduction & Principal Component Analysis (PCA):** Identifying latent dimensions of municipal fiscal vulnerability and institutional capacity.
2. **Cluster Typologies:** Applying K-Means, Hierarchical Ward, and PAM (*Partitioning Around Medoids*) to uncover homogeneous local governance archetypes.
3. **Panel Data Econometrics with Fixed Effects:** Measuring the causal effect of incentive transfers on own-source revenue mobilization and expenditure efficiency.

---

## 📁 Repository Structure

```text
├── data/
│   └── Tesis_final_base_municipal.csv    # Consolidated municipal-level panel dataset
├── src/
│   ├── tesis_clustering_final.py         # PCA, elbow method, silhouette, and clustering pipeline
│   └── generador_graficos_USACH.py       # High-resolution chart and biplot generator
├── figuras/
│   ├── fig_pca_biplot.png                # Principal Component Biplot
│   ├── fig_elbow_silhouette.png          # Optimal cluster number validation
│   ├── fig_clusters_distribucion.png     # Geographic cluster distribution
│   ├── fig_boxplots_autonomia.png        # Fiscal autonomy by cluster
│   ├── fig_coeficientes_fe.png           # Fixed-effects regression coefficients
│   └── fig_confusion_heatmap.png         # Methodological concordance matrix
├── requirements.txt                      # Reproducible Python dependencies
├── LICENSE                               # MIT License
└── README.md
```

---

## 🛠️ Tech Stack & Methods

- **Language:** Python 3.10+
- **Libraries:** `pandas`, `numpy`, `scikit-learn`, `scipy`, `matplotlib`, `seaborn`, `statsmodels`
- **Methods:** PCA, K-Means, Hierarchical Clustering (Ward), PAM, Fixed-Effects Panel Regression.

---

## 🚀 Quickstart & Reproduction

```bash
# 1. Clone the repository
git clone https://github.com/evegat/figem-analisis-fiscal-municipal.git
cd figem-analisis-fiscal-municipal

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Run analysis and generate figures
python src/tesis_clustering_final.py
python src/generador_graficos_USACH.py
```

---

## 📚 Citation (BibTeX)

```bibtex
@article{montecinos_vega_2025_figem,
  author    = {Montecinos Garc{\'i}a, Randy Soledad and Vega Toledo, Eduardo Isaack},
  title     = {Validaci{\'o}n emp{\'i}rica del FIGEM en municipios chilenos: tipolog{\'i}as fiscales, clustering y evaluaci{\'o}n de desempe{\~n}o},
  journal   = {Revista Pol{\'i}ticas P{\'u}blicas},
  year      = {2025},
  volume    = {18},
  number    = {2},
  pages     = {3--21}
}
```

---

## 👥 Authors

* **Soledad Montecinos García** — Universidad de Santiago de Chile (USACH).
* **Eduardo Vega Toledo** — *Public Administrator · Master in Government and Public Management (U. de Chile)* · Former Head of Municipal Investment Dept. (SUBDERE) · Lecturer at FAGOB Universidad de Chile.
