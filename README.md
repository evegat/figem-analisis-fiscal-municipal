# Validación Empírica del FIGEM en Municipios Chilenos

[![Licencia](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Investigación Reproducible](https://img.shields.io/badge/Open%20Science-Reproducible-green.svg)](#)

[ 🇪🇸 Español ](README.md) · [ 🇬🇧 English version ](README.en.md)

Repositorio de **código abierto e investigación reproducible** correspondiente al estudio econométrico y multivariado sobre el **Fondo de Incentivo a la Gestión Municipal (FIGEM)** en Chile.

> 📄 **Referencia bibliográfica:**  
> Montecinos García, R. S., & Vega Toledo, E. (2025). *“Validación empírica del FIGEM en municipios chilenos: tipologías fiscales, clustering y evaluación de desempeño”*. Revista Políticas Públicas, 18(2), 3-21.

---

## 🎯 Resumen de la Investigación

El FIGEM es uno de los principales instrumentos de transferencia condicionada del Estado central hacia los gobiernos locales en Chile. Esta investigación evalúa empíricamente la efectividad, equidad distributiva y coherencia del fondo mediante:

1. **Reducción de dimensionalidad y análisis de componentes principales (PCA):** Identificación de los ejes estructurales de vulnerabilidad fiscal y capacidad de gestión local.
2. **Tipologías de conglomerados (Clustering):** Algoritmos K-Means, Ward Jerárquico y PAM (*Partitioning Around Medoids*) para caracterizar patrones municipales homogéneos.
3. **Modelos econométricos con efectos fijos:** Evaluación del impacto del incentivo sobre la recaudación de ingresos propios y la eficiencia del gasto municipal.

---

## 📁 Estructura del Repositorio

```text
├── data/
│   └── Tesis_final_base_municipal.csv    # Panel de datos consolidado a nivel comunal
├── src/
│   ├── tesis_clustering_final.py         # Pipeline de PCA, métodos de codo, silueta y clustering
│   └── generador_graficos_USACH.py       # Generación de gráficos y biplots de alta resolución
├── figuras/
│   ├── fig_pca_biplot.png                # Biplot de componentes principales
│   ├── fig_elbow_silhouette.png          # Validación de número óptimo de clusters
│   ├── fig_clusters_distribucion.png     # Distribución comunal de tipologías
│   ├── fig_boxplots_autonomia.png        # Autonomía fiscal por tipología
│   ├── fig_coeficientes_fe.png           # Coeficientes de modelos de efectos fijos
│   └── fig_confusion_heatmap.png         # Matriz de concordancia entre metodologías
├── requirements.txt                      # Dependencias de Python reproducibles
├── LICENSE                               # Licencia MIT
└── README.md
```

---

## 🛠️ Stack Tecnológico & Métodos

- **Lenguaje:** Python 3.10+
- **Bibliotecas:** `pandas`, `numpy`, `scikit-learn`, `scipy`, `matplotlib`, `seaborn`, `statsmodels`
- **Métodos Estadísticos:** PCA, K-Means, Clustering Jerárquico (Ward), PAM, Regresión de Panel con Efectos Fijos.

---

## 🚀 Reproducción de Resultados

```bash
# 1. Clonar el repositorio
git clone https://github.com/evegat/figem-analisis-fiscal-municipal.git
cd figem-analisis-fiscal-municipal

# 2. Configurar entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Instalar requerimientos
pip install -r requirements.txt

# 4. Ejecutar análisis y reproducir figuras
python src/tesis_clustering_final.py
python src/generador_graficos_USACH.py
```

---

## 📚 Cita Bibliográfica (BibTeX)

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

## 👥 Autores

* **Soledad Montecinos García** — Universidad de Santiago de Chile (USACH).
* **Eduardo Vega Toledo** — *Administrador Público · Magíster en Gobierno y Gerencia Pública (U. de Chile)* · Ex Jefe de Departamento de Inversión Municipal (SUBDERE) · Docente en FAGOB Universidad de Chile.
