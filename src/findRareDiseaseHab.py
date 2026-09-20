"""Identifica empiricamente o codigo de habilitacao da Rede de Doencas Raras.

A Rede de Atencao Especializada em Doencas Raras tinha, segundo o Ministerio,
cerca de 60 servicos habilitados em 15 estados. Isso e uma assinatura
procuravel: baixamos as habilitacoes (grupo HB do CNES) das 27 UFs e
procuramos o codigo SGRUPHAB que aparece em algumas dezenas de
estabelecimentos, espalhados por pouco mais de uma duzia de estados.

O cruzamento com os centros que concentram AME no nosso escopo confirma ou
descarta o candidato.

Uso:
    python src/findRareDiseaseHab.py --year 2024 --month 6
"""

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd

from config import DATA_PROCESSED, DATA_RAW, UFS

CACHE = DATA_RAW / "cnes_hb"


def baixar_hb(uf: str, ano: int, mes: int) -> pd.DataFrame | None:
    """Um UF-mes de habilitacoes, com cache em parquet."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"hb_{uf}_{ano}{mes:02d}.parquet"
    if out.exists():
        return pd.read_parquet(out)

    import pysus
    cnes = getattr(getattr(pysus, "ftp", pysus), "cnes", None) or pysus.cnes
    try:
        df = cnes(uf, ano, mes, group="HB", as_dataframe=True)
    except Exception as exc:
        print(f"  {uf}: {type(exc).__name__}")
        return None
    if df is None or len(df) == 0:
        print(f"  {uf}: vazio")
        return None

    df = pd.DataFrame(df)
    manter = [c for c in ["CNES", "CODUFMUN", "SGRUPHAB", "CMPT_INI", "CMPT_FIM"]
              if c in df.columns]
    df = df[manter].copy()
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    df["UF"] = uf
    df.to_parquet(out, index=False)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--month", type=int, default=6)
    ap.add_argument("--min-estab", type=int, default=20,
                    help="minimo de estabelecimentos para ser candidato")
    ap.add_argument("--max-estab", type=int, default=150,
                    help="maximo de estabelecimentos para ser candidato")
    a = ap.parse_args()

    print(f"Baixando habilitacoes (CNES-HB) de {a.year}-{a.month:02d}, 27 UFs\n")
    partes = []
    for i, uf in enumerate(UFS, 1):
        df = baixar_hb(uf, a.year, a.month)
        if df is not None:
            partes.append(df)
        if i % 9 == 0:
            print(f"  ... {i}/27")

    if not partes:
        print("Nada baixado.")
        return 1

    hb = pd.concat(partes, ignore_index=True)
    hb["CNES"] = hb.CNES.str.zfill(7)
    print(f"\n{len(hb):,} habilitacoes, {hb.CNES.nunique():,} estabelecimentos, "
          f"{hb.SGRUPHAB.nunique()} codigos distintos\n")

    # --- perfil de cada codigo -------------------------------------------
    perfil = (hb.groupby("SGRUPHAB")
                .agg(estabelecimentos=("CNES", "nunique"),
                     ufs=("UF", "nunique"),
                     municipios=("CODUFMUN", "nunique"))
                .reset_index())

    candidatos = perfil[
        perfil.estabelecimentos.between(a.min_estab, a.max_estab)
        & perfil.ufs.between(8, 22)
    ].sort_values("estabelecimentos")

    print("=== candidatos por assinatura (rede especializada: poucos servicos, "
          "muitos estados) ===")
    print(candidatos.to_string(index=False))

    # --- cruzamento com os centros de AME --------------------------------
    escopo_path = DATA_PROCESSED / "scoped_2024.parquet"
    if not escopo_path.exists():
        print(f"\n{escopo_path.name} nao encontrado; pulei o cruzamento.")
        return 0

    escopo = pd.read_parquet(escopo_path, columns=["CNES", "diseaseShort"])
    escopo["CNES"] = escopo.CNES.astype(str).str.strip().str.zfill(7)

    ame = (escopo[escopo.diseaseShort == "AME"]
           .groupby("CNES").size().rename("aihs")
           .sort_values(ascending=False))
    top_ame = set(ame.head(15).index)

    print(f"\n=== quais candidatos cobrem os 15 maiores centros de AME? ===")
    print(f"(esses 15 respondem por {ame.head(15).sum():,} das {ame.sum():,} AIHs de AME)\n")

    linhas = []
    for cod in candidatos.SGRUPHAB:
        com_hab = set(hb[hb.SGRUPHAB == cod].CNES)
        linhas.append({
            "SGRUPHAB": cod,
            "estabelecimentos": len(com_hab),
            "ufs": int(candidatos.loc[candidatos.SGRUPHAB == cod, "ufs"].iloc[0]),
            "dos_15_top_AME": len(top_ame & com_hab),
        })

    res = pd.DataFrame(linhas).sort_values("dos_15_top_AME", ascending=False)
    print(res.head(15).to_string(index=False))

    print("\n  O codigo da Rede de Doencas Raras deve combinar: poucas dezenas de")
    print("  estabelecimentos, presenca em ~15 UFs, e cobertura alta dos centros")
    print("  de AME. Confirme o vencedor na tabela de habilitacoes do CNES antes")
    print("  de tratar como certo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
