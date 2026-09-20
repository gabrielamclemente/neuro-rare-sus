"""Carrega a Rede de Doencas Raras (CNES) e responde a pergunta do projeto.

Os municipios que concentram o cuidado sao servicos habilitados da rede?

Habilitacoes do grupo 35 no CNES (fonte: instrutivo de habilitacao do
Ministerio da Saude):
    35.01-35.06, 35.13  Servico de Atencao Especializada em Doencas Raras
    35.07-35.12, 35.14  Servico de Referencia em Doencas Raras
    35.15               Servico de Aconselhamento Genetico

Usa os parquets ja baixados por src/findRareDiseaseHab.py em
data/raw/cnes_hb/. Se nao existirem, rode aquele script antes.

Uso:
    python src/loadCnes.py --year 2024 --month 6
"""

import argparse
import sqlite3
import sys

import pandas as pd

from config import DATA_PROCESSED, DATA_RAW, DB_PATH, ROOT, UF_BY_IBGE_PREFIX

CACHE = DATA_RAW / "cnes_hb"
SQL_DIR = ROOT / "sql"

SADR = {"3501", "3502", "3503", "3504", "3505", "3506", "3513"}
SRDR = {"3507", "3508", "3509", "3510", "3511", "3512", "3514"}
ACON = {"3515"}


def tipo_servico(cod: str) -> str:
    if cod in SRDR:
        return "referencia"
    if cod in SADR:
        return "atencao especializada"
    if cod in ACON:
        return "aconselhamento genetico"
    return "outro"


def carregar_hb(year: int, month: int) -> pd.DataFrame:
    arquivos = sorted(CACHE.glob(f"hb_*_{year}{month:02d}.parquet"))
    if not arquivos:
        print(f"Nenhum parquet em {CACHE}. Rode src/findRareDiseaseHab.py antes.")
        sys.exit(1)
    df = pd.concat([pd.read_parquet(p) for p in arquivos], ignore_index=True)
    df["CNES"] = df.CNES.astype(str).str.strip().str.zfill(7)
    df["SGRUPHAB"] = df.SGRUPHAB.astype(str).str.strip().str.zfill(4)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--month", type=int, default=6)
    a = ap.parse_args()

    hb = carregar_hb(a.year, a.month)
    print(f"{len(hb):,} habilitacoes lidas, {hb.CNES.nunique():,} estabelecimentos\n")

    # --- a rede ----------------------------------------------------------
    raras = hb[hb.SGRUPHAB.str.startswith("35")].copy()
    raras["serviceType"] = raras.SGRUPHAB.map(tipo_servico)
    raras["uf"] = raras.CODUFMUN.astype(str).str.zfill(6).str[:2].map(UF_BY_IBGE_PREFIX)

    print("=== Rede de Atencao Especializada em Doencas Raras ===")
    print(f"  estabelecimentos habilitados: {raras.CNES.nunique()}")
    print(f"  UFs com ao menos um servico : {raras.uf.nunique()}")
    print("\n  por tipo de servico:")
    print(raras.groupby("serviceType").CNES.nunique().to_string())
    print("\n  por UF:")
    print(raras.groupby("uf").CNES.nunique().sort_values(ascending=False).to_string())

    # Um estabelecimento pode ter varias habilitacoes; consolidamos em uma
    # linha por CNES, guardando o tipo mais alto da hierarquia.
    ordem = {"referencia": 0, "atencao especializada": 1,
             "aconselhamento genetico": 2, "outro": 3}
    servicos = (raras.sort_values("serviceType", key=lambda s: s.map(ordem))
                     .groupby("CNES")
                     .agg(uf=("uf", "first"),
                          municipality=("CODUFMUN", "first"),
                          serviceType=("serviceType", "first"))
                     .reset_index()
                     .rename(columns={"CNES": "establishmentId"}))
    servicos["establishmentName"] = None
    servicos["specializedDiseaseService"] = 1

    # --- a pergunta ------------------------------------------------------
    escopo_path = DATA_PROCESSED / f"scoped_{a.year}.parquet"
    if not escopo_path.exists():
        print(f"\n{escopo_path.name} nao encontrado; pulei o cruzamento.")
        return 0

    escopo = pd.read_parquet(escopo_path, columns=["CNES", "diseaseShort", "MUNIC_MOV"])
    escopo["CNES"] = escopo.CNES.astype(str).str.strip().str.zfill(7)
    habilitados = set(servicos.establishmentId)

    print("\n" + "=" * 68)
    print("A PERGUNTA: os centros que concentram o cuidado sao habilitados?")
    print("=" * 68)

    linhas = []
    for doenca, sub in escopo.groupby("diseaseShort"):
        por_estab = sub.groupby("CNES").size().sort_values(ascending=False)
        total = por_estab.sum()
        top5 = por_estab.head(5)
        linhas.append({
            "condicao": doenca,
            "aihs": int(total),
            "estabelecimentos": int(por_estab.size),
            "habilitados": int(sum(1 for c in por_estab.index if c in habilitados)),
            "aihs_em_habilitados": int(por_estab[[c in habilitados for c in por_estab.index]].sum()),
            "pct_aihs_habilitados": round(
                100.0 * por_estab[[c in habilitados for c in por_estab.index]].sum() / total, 1),
            "top5_habilitados": int(sum(1 for c in top5.index if c in habilitados)),
        })

    res = pd.DataFrame(linhas).sort_values("aihs", ascending=False)
    print(res.to_string(index=False))

    print("\n  pct_aihs_habilitados = fatia do atendimento que ocorre em servico")
    print("  habilitado da rede. top5_habilitados = quantos dos 5 maiores centros")
    print("  daquela condicao tem habilitacao.")

    # --- carga no banco --------------------------------------------------
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM rareDiseaseServices")
        servicos[["establishmentId", "establishmentName", "uf", "municipality",
                  "serviceType", "specializedDiseaseService"]].to_sql(
            "rareDiseaseServices", con, if_exists="append", index=False)
        n = con.execute("SELECT COUNT(*) FROM rareDiseaseServices").fetchone()[0]
    print(f"\nrareDiseaseServices: {n} linhas gravadas em {DB_PATH.name}")
    print("Agora sql/capacityAnalysis.sql roda com dados reais.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
