"""Agrega os parquets de data/raw para as tabelas do modelo e carrega no SQLite.

Fluxo:
    data/raw/*.parquet  ->  filtra os 5 CIDs  ->  agrega  ->  data/neuroraresus.db

Uso:
    python src/cleanData.py --year 2024
    python src/cleanData.py --year 2024 --dry-run   # nao grava, so mostra

As partes marcadas com TODO sao SUAS: sao decisoes analiticas, nao mecanica.
Cada uma tem a pergunta a responder e o que esta em jogo.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from classifyDiseases import add_uf_columns, classify
from config import DATA_PROCESSED, DATA_RAW, DB_PATH, ROOT, UFS

SQL_DIR = ROOT / "sql"


# ---------------------------------------------------------------------------
# Utilitarios (prontos)
# ---------------------------------------------------------------------------

def to_num(s: pd.Series) -> pd.Series:
    """SIH grava numeros como texto, as vezes com espacos. Vira numero ou NaN."""
    return pd.to_numeric(s.astype(str).str.strip(), errors="coerce")


def raw_files(year: int) -> list[Path]:
    return sorted(DATA_RAW.glob(f"sih_rd_*_{year}*.parquet"))


def parse_name(p: Path) -> tuple[str, int, int]:
    """sih_rd_SP_202403.parquet -> ('SP', 2024, 3)"""
    _, _, uf, ym = p.stem.split("_")
    return uf, int(ym[:4]), int(ym[4:])


# ---------------------------------------------------------------------------
# 1. Carga e filtro (pronto)
# ---------------------------------------------------------------------------

def load_scoped(year: int, verbose: bool = True) -> pd.DataFrame:
    """Le todos os parquets do ano e devolve SO as AIHs dos 5 CIDs.

    Filtra arquivo a arquivo: o bruto do Brasil inteiro nao cabe confortavel
    na memoria, mas o escopo filtrado e pequeno (milhares de linhas).
    """
    frames = []
    files = raw_files(year)
    if not files:
        print(f"Nenhum parquet de {year} em {DATA_RAW}. Rode src/loadData.py antes.")
        sys.exit(1)

    for i, p in enumerate(files, 1):
        uf, ano, mes = parse_name(p)
        df = pd.read_parquet(p)
        df = classify(df)                  # so DIAG_PRINC, por decisao
        if df.empty:
            continue
        df = add_uf_columns(df)
        df["fileUf"] = uf
        df["year"] = ano
        df["month"] = mes
        frames.append(df)
        if verbose and i % 50 == 0:
            print(f"  ... {i}/{len(files)} arquivos")

    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if verbose:
        print(f"{len(files)} arquivos lidos -> {len(out):,} AIHs no escopo")
    return out


# ---------------------------------------------------------------------------
# 2. Cobertura (pronto) - o que torna a lacuna dos 74 um dado, nao um vies
# ---------------------------------------------------------------------------

def build_coverage(year: int) -> pd.DataFrame:
    """Quantos meses de cada UF existem em data/raw.

    Sem isso, uma UF com 10 meses parece ter menos demanda que uma vizinha
    com 12, e o indicador demanda/servico mente. Com isso, o dashboard pode
    normalizar por mes disponivel e declarar a cobertura.
    """
    presentes = {}
    for p in raw_files(year):
        uf, _, mes = parse_name(p)
        presentes.setdefault(uf, set()).add(mes)

    linhas = []
    for uf in UFS:
        meses = sorted(presentes.get(uf, set()))
        faltando = [m for m in range(1, 13) if m not in meses]
        linhas.append({
            "year": year,
            "uf": uf,
            "monthsAvailable": len(meses),
            "monthsExpected": 12,
            "coverageRatio": round(len(meses) / 12, 4),
            "missingMonths": ",".join(str(m) for m in faltando),
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 3. Agregacao  <<< SUA PARTE >>>
# ---------------------------------------------------------------------------

def aggregate_admissions(scoped: pd.DataFrame) -> pd.DataFrame:
    """Agrega as AIHs para o grao de hospitalAdmissions.

    Grao (ver sql/createTables.sql):
        year, month, ufResidence, ufHospital,
        municipalityResidence, municipalityHospital,
        establishmentId, diseaseCode, diseaseName

    Metricas: admissions, deaths, hospitalDays, approvedValue

    Colunas disponiveis em `scoped`:
        year, month, ufResidence, ufHospital, MUNIC_RES, MUNIC_MOV, CNES,
        diseaseCode, diseaseName, diseaseShort, MORTE, DIAS_PERM, VAL_TOT,
        IDADE, COD_IDADE, SEXO, PROC_REA
    """
    df = scoped.copy()

    # Numeros vem como texto do SIH. (pronto)
    df["MORTE"] = to_num(df["MORTE"]).fillna(0)
    df["DIAS_PERM"] = to_num(df["DIAS_PERM"]).fillna(0)
    df["VAL_TOT"] = to_num(df["VAL_TOT"]).fillna(0)

    # TODO-1 (resolvido): em 2024 nao ha AIH sem UF - MUNIC_RES e MUNIC_MOV
    # vem sempre preenchidos com codigo IBGE valido (0 de 11.590 no escopo).
    # Opcao (a): manter as linhas, deixando o SQL lidar com NULL. Descartar
    # falsearia o total de internacoes registradas, que deve ser fiel ao SIH.
    # O aviso abaixo existe porque outro ano pode nao se comportar assim.
    sem_uf = df.ufResidence.isna() | df.ufHospital.isna()
    if sem_uf.any():
        print(f"  aviso: {sem_uf.sum():,} AIHs ({sem_uf.mean():.2%}) sem UF de "
              "residencia ou internacao. Mantidas nos totais; as analises de "
              "fluxo as ignoram, entao os numeros das paginas 1 e 4 divergem.")

    # TODO-2: a agregacao em si.
    #   Monte `out` com groupby nas colunas do grao e:
    #       admissions    = contagem de AIHs
    #       deaths        = soma de MORTE
    #       hospitalDays  = soma de DIAS_PERM
    #       approvedValue = soma de VAL_TOT
    #   Pergunta que muda o resultado: VAL_TOT soma ou tira media? Pense no
    #   que a pagina 1 mostra ("valor aprovado") e no que a pagina 2 mostra
    #   ("valor medio por internacao") - as duas saem da mesma coluna?
    #   Dica: df.groupby([...], dropna=False).agg(...).reset_index()
    out = (df.groupby(["year", "month",
                       "ufResidence", "ufHospital",
                       "MUNIC_RES", "MUNIC_MOV",
                       "CNES",
                       "diseaseCode", "diseaseName"], dropna=False)
              .agg(admissions=("MORTE", "size"),
                  shortStayAdmissions=("DIAS_PERM", lambda s: (s <= 1).sum()),
                  deaths=("MORTE", "sum"),
                  hospitalDays=("DIAS_PERM", "sum"),
                  approvedValue=("VAL_TOT", "sum"))
             .reset_index())

    # TODO-3: renomear para o schema.
    #   MUNIC_RES -> municipalityResidence
    #   MUNIC_MOV -> municipalityHospital
    #   CNES      -> establishmentId
    #   Confira ao final que out.columns bate EXATAMENTE com as colunas de
    #   hospitalAdmissions em sql/createTables.sql (menos o id).

    out = out.rename(columns={"MUNIC_RES": "municipalityResidence",
                              "MUNIC_MOV": "municipalityHospital",
                              "CNES": "establishmentId"})

    return out


# ---------------------------------------------------------------------------
# 4. Carga no SQLite (pronto)
# ---------------------------------------------------------------------------

COVERAGE_DDL = """
DROP TABLE IF EXISTS dataCoverage;
CREATE TABLE dataCoverage (
    year            INTEGER NOT NULL,
    uf              TEXT    NOT NULL,
    monthsAvailable INTEGER NOT NULL,
    monthsExpected  INTEGER NOT NULL,
    coverageRatio   REAL    NOT NULL,
    missingMonths   TEXT,
    PRIMARY KEY (year, uf)
);
"""


def load_to_sqlite(admissions: pd.DataFrame, coverage: pd.DataFrame) -> None:
    schema = (SQL_DIR / "createTables.sql").read_text()
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(schema)
        con.executescript(COVERAGE_DDL)
        admissions.to_sql("hospitalAdmissions", con,
                          if_exists="append", index=False)
        coverage.to_sql("dataCoverage", con, if_exists="append", index=False)

        n = con.execute("SELECT COUNT(*) FROM hospitalAdmissions").fetchone()[0]
        s = con.execute("SELECT SUM(admissions) FROM hospitalAdmissions").fetchone()[0]
    print(f"\nSQLite: {DB_PATH}")
    print(f"  hospitalAdmissions: {n:,} linhas, {s:,} internacoes")
    print(f"  dataCoverage: {len(coverage)} UFs")
    print("  rareDiseaseServices e population seguem vazias (passo seguinte)")


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print(f"=== cobertura {a.year} ===")
    coverage = build_coverage(a.year)
    completas = (coverage.monthsAvailable == 12).sum()
    print(f"{completas}/27 UFs completas; "
          f"cobertura media {coverage.coverageRatio.mean():.1%}")
    incompletas = coverage[coverage.monthsAvailable < 12]
    if len(incompletas):
        print(incompletas[["uf", "monthsAvailable", "missingMonths"]]
              .to_string(index=False))

    print(f"\n=== carga {a.year} ===")
    scoped = load_scoped(a.year)
    if scoped.empty:
        print("Nada no escopo. Confira os CIDs em config.py.")
        return 1

    print("\nAIHs por doenca:")
    print(scoped.groupby(["diseaseShort", "diseaseName"]).size()
          .rename("aihs").sort_values(ascending=False).to_string())

    scoped.to_parquet(DATA_PROCESSED / f"scoped_{a.year}.parquet", index=False)
    coverage.to_csv(DATA_PROCESSED / f"coverage_{a.year}.csv", index=False)

    print("\n=== agregacao ===")
    adm = aggregate_admissions(scoped)
    if adm.empty:
        print("aggregate_admissions() ainda devolve vazio - os TODOs 1-3 "
              "estao por fazer. A carga no SQLite foi pulada.")
        return 0

    print(f"{len(adm):,} linhas agregadas")
    if a.dry_run:
        print(adm.head(10).to_string(index=False))
        return 0

    load_to_sqlite(adm, coverage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
