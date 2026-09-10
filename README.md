# Validación empírica del FIGEM en municipios chilenos

[Español](README.md) · [English](README.en.md) · [Português](README.pt-BR.md)

Repositorio reproducible asociado a:

> Montecinos García, R. S., & Vega Toledo, E. (2025). *Validación empírica
> del FIGEM en municipios chilenos: tipologías fiscales y evaluación
> cuantitativa*. Revista Políticas Públicas, 18(2), 3–21.

El artículo evalúa si los grupos normativos del Fondo de Incentivo al
Mejoramiento de la Gestión Municipal (FIGEM) agrupan municipios fiscalmente
comparables. El análisis utiliza datos SINIM y registros FIGEM para 345
municipios durante 2016–2024.

## Qué reproduce

El pipeline completo reproduce:

1. imputación documentada de montos FIGEM faltantes;
2. construcción de variables per cápita;
3. PCA de desarrollo fiscal relativo;
4. evaluación de K-Means para `k=2..6` y solución final `k=4`;
5. tipologías fiscales con etiquetas semánticas estables;
6. matriz FIGEM-clusters y Kappa de Cohen como indicador complementario;
7. modelo de panel con efectos fijos municipales y anuales, con errores HC3;
8. pruebas de robustez con diez semillas;
9. las tablas y figuras de respaldo del artículo.

La solución `k=4` se conserva por equilibrio entre desempeño estadístico,
interpretabilidad y utilidad evaluativa. `k=3` obtiene la mayor silhouette,
por lo que la selección de `k=4` es una decisión sustantiva explícita y no
una maximización automática de esa métrica.

## Estructura

```text
data/
  Input_USACH.xlsx       # insumo consolidado SINIM + FIGEM
  Output_USACH.xlsx      # salida reproducida, 17 hojas trazables
src/
  Clustering_USACH.py    # pipeline completo
  generador_graficos_USACH.py
scripts/
  verify_reproduction.py # controles de cifras publicadas
figuras/                 # seis figuras reproducibles
docs/
  Cuaderno_Metodologico_FIGEM.docx
requirements.txt
```

## Reproducción

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python src/Clustering_USACH.py
python src/generador_graficos_USACH.py
```

El pipeline usa rutas relativas a la raíz del repositorio y sobrescribe
`data/Output_USACH.xlsx` con una salida nueva. La ejecución esperada reporta:

```text
345 municipios
PCA1: 81.0%
Silhouette k=4: 0.2376
Kappa: -0.0095
Discrepancia modal: 48.7%
R² within: 0.1495
```

La discrepancia de 48,7% corresponde a la discrepancia bajo asignación modal
por grupo FIGEM: se suma el máximo de cada fila de la matriz de confusión y se
resta de 100%. No representa una equivalencia uno-a-uno entre cinco grupos
normativos y cuatro clusters.

## Datos, alcance y limitaciones

Los datos son administrativos y públicos, integrados desde SINIM y registros
FIGEM. El estudio es evaluativo y no causal. El modelo de efectos fijos
identifica asociaciones intra-municipales, no efectos causales. La imputación
de montos FIGEM está documentada en la hoja `01_Imputacion_FIGEM` y no
reemplaza observaciones originales.

La propuesta de rediseño híbrido del artículo es una hipótesis de política
pública, no una regla implementable sin simulación distributiva, análisis de
ganadores y perdedores y transición gradual.

La licencia del código es MIT. Los datos base provienen de información pública
SINIM/FIGEM descargada manualmente y consolidada por los autores. La
procedencia y atribución están documentadas en
`docs/DATA-AND-LICENSE.md`.

GitHub Actions ejecuta automáticamente la compilación de los scripts y una
verificación de las cifras principales reportadas en el artículo.

## Licencia y cita

El código se distribuye bajo MIT. Para citar el análisis, use la referencia
del artículo indicada al inicio de este README.
