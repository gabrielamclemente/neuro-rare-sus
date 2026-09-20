"""Exporta as views do dashboard para CSV, prontas para o Power BI.

Uso:
    python src/exportForBI.py

Saida: powerBi/data/*.csv  (UTF-8 com BOM, para o Power BI ler acentos certo)
"""

import sqlite3
import sys

import pandas as pd

from config import DB_PATH, ROOT

SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "powerBi" / "data"

VIEWS = [
    "vwDiseaseRegime",
    "vwOverview",
    "vwMonthly",
    "vwByUf",
    "vwConcentration",
    "vwFlow",
    "vwTravelSummary",
    "dataCoverage",
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"{DB_PATH} nao existe. Rode src/cleanData.py --year 2024 antes.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as con:
        con.executescript((SQL_DIR / "dashboardViews.sql").read_text())
        print("views criadas\n")

        for v in VIEWS:
            df = pd.read_sql_query(f"SELECT * FROM {v}", con)
            # utf-8-sig: sem o BOM o Power BI le "Esclerose Multipla" com
            # acentos quebrados ao importar CSV.
            out = OUT_DIR / f"{v}.csv"
            df.to_csv(out, index=False, encoding="utf-8-sig")
            print(f"  {v:<20} {len(df):>7,} linhas -> {out.name}")

    print(f"\nCSVs em: {OUT_DIR}")
    print("No Power BI: Obter Dados > Pasta > aponte para essa pasta,")
    print("ou importe um CSV de cada vez.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
