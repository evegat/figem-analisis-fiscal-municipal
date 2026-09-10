"""Check the published-paper headline results in the generated workbook."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "Output_USACH.xlsx"


def value(sheet: pd.DataFrame, indicator: str):
    return sheet.loc[sheet["Indicador"].eq(indicator), "Valor"].iloc[0]


def main() -> None:
    if not OUTPUT.exists():
        raise FileNotFoundError(f"Missing generated output: {OUTPUT}")
    sheets = pd.ExcelFile(OUTPUT).sheet_names
    assert len(sheets) == 17, sheets

    evaluation = pd.read_excel(OUTPUT, sheet_name="03_Evaluacion_k")
    k4 = evaluation.loc[evaluation["k"].eq(4)].iloc[0]
    assert abs(float(k4["silhouette"]) - 0.2376) < 1e-4

    summary = pd.read_excel(OUTPUT, sheet_name="14_Resumen_tesis")
    assert int(value(summary, "N municipios")) == 345
    assert abs(float(value(summary, "PCA1 varianza explicada (%)")) - 81.0) < 1e-6
    assert abs(float(value(summary, "Kappa de Cohen")) - (-0.0095)) < 1e-4
    assert abs(float(value(summary, "Discrepancia FIGEM vs Clusters (%)")) - 48.7) < 1e-6
    assert abs(float(value(summary, "R² within (FE)")) - 0.1495) < 1e-4
    assert int(value(summary, "N obs. modelo FE")) == 3085
    print("Reproduction checks: PASS")


if __name__ == "__main__":
    main()
