# Empirical validation of FIGEM in Chilean municipalities

Reproducible repository associated with Montecinos García, R. S., & Vega
Toledo, E. (2025), *Validación empírica del FIGEM en municipios chilenos:
tipologías fiscales y evaluación cuantitativa*, Revista Políticas Públicas,
18(2), 3–21.

The repository evaluates whether the normative FIGEM groups municipalities
with comparable fiscal profiles using SINIM and FIGEM records for 345
municipalities over 2016–2024.

## Reproducible pipeline

`src/Clustering_USACH.py` reproduces missing-value imputation, per-capita
variables, PCA, standardized K-Means for `k=2..6`, the selected `k=4`
typology, confusion matrix, complementary Cohen's kappa, a municipality and
year fixed-effects model with HC3 standard errors, and ten-seed robustness
checks. `src/generador_graficos_USACH.py` regenerates the six article figures.

The `k=4` solution is retained for substantive interpretability and policy
usefulness even though `k=3` has the highest silhouette. This is an explicit
analytical decision, not automatic metric maximization.

## Reproduction

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/Clustering_USACH.py
python src/generador_graficos_USACH.py
```

The pipeline reads `data/Input_USACH.xlsx` and writes the traceable
17-sheet result to `data/Output_USACH.xlsx`.

## Scope and limitations

The study is evaluative, not causal. Fixed effects identify within-municipality
associations. The reported 48.7% discrepancy is the complement of modal
row-wise agreement in the five-by-four FIGEM/cluster table; it is not a strict
one-to-one classification accuracy measure.
