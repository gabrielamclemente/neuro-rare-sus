"""Download do SIH/SUS (arquivos RD = AIH reduzida) via PySUS.

Uso:
    python src/loadData.py --sample          # amostra da Fase 0
    python src/loadData.py --uf SP --year 2024 --months 1 2 3
"""

import argparse
import sys

import pandas as pd

from config import (DATA_RAW, SAMPLE_MONTHS, SAMPLE_UFS, SAMPLE_YEAR,
                    SIH_COLUMNS)


def _parquet_path(uf: str, year: int, month: int):
    return DATA_RAW / f"sih_rd_{uf}_{year}{month:02d}.parquet"


def download_month(uf: str, year: int, month: int, force: bool = False) -> pd.DataFrame | None:
    """Baixa um mes de SIH-RD e salva em parquet. Devolve o DataFrame."""
    out = _parquet_path(uf, year, month)
    if out.exists() and not force:
        print(f"[cache] {out.name}")
        return pd.read_parquet(out)

    try:
        from pysus.online_data.SIH import download
    except ImportError:
        print("PySUS nao instalado. Rode: pip install -r requirements.txt")
        sys.exit(1)

    print(f"[download] SIH-RD {uf} {year}-{month:02d} ...")
    try:
        res = download(uf, year, month)
    except Exception as exc:  # rede, arquivo inexistente, etc.
        print(f"  !! falhou: {exc}")
        return None

    df = res.to_dataframe() if hasattr(res, "to_dataframe") else pd.DataFrame(res)
    if df.empty:
        print("  !! vazio")
        return None

    # Guarda so as colunas de interesse que realmente existem no arquivo.
    keep = [c for c in SIH_COLUMNS if c in df.columns]
    missing = [c for c in SIH_COLUMNS if c not in df.columns]
    if missing:
        print(f"  (colunas ausentes neste mes: {missing})")
    df = df[keep].copy()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()

    df.to_parquet(out, index=False)
    print(f"  ok: {len(df):,} AIHs -> {out.name}")
    return df


def download_many(ufs, year, months, force=False) -> pd.DataFrame:
    frames = []
    for uf in ufs:
        for m in months:
            df = download_month(uf, year, m, force=force)
            if df is not None:
                df["UF_SIGLA"] = uf
                frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="usa a amostra da Fase 0")
    ap.add_argument("--uf", nargs="*", default=None)
    ap.add_argument("--year", type=int, default=SAMPLE_YEAR)
    ap.add_argument("--months", nargs="*", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    ufs = SAMPLE_UFS if (a.sample or not a.uf) else a.uf
    months = SAMPLE_MONTHS if (a.sample or not a.months) else a.months

    df = download_many(ufs, a.year, months, force=a.force)
    print(f"\nTotal baixado: {len(df):,} registros")
