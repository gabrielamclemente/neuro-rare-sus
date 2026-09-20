"""Diagnostico pos-Fase 0. Nao baixa nada: le o que ja esta em data/.

Responde:
  A. O que aconteceu com os meses faltantes (quais parquets existem).
  B. MUNIC_MOV mede mesmo o local de internacao? (compara com UF_ZI e CNES)
  C. Qual o fluxo interestadual real, por doenca e por UF.
  D. Volume por doenca extrapolado para o periodo completo.

Uso:
    python src/inspectPhase0.py
"""

import pandas as pd

from classifyDiseases import add_uf_columns, classify
from config import (DATA_PROCESSED, DATA_RAW, SAMPLE_MONTHS, SAMPLE_UFS,
                    SAMPLE_YEAR, UF_BY_IBGE_PREFIX)

pd.set_option("display.width", 120)


def sec(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


# --- A. cobertura dos arquivos --------------------------------------------
sec("A. Arquivos baixados")
rows = []
for uf in SAMPLE_UFS:
    for m in SAMPLE_MONTHS:
        p = DATA_RAW / f"sih_rd_{uf}_{SAMPLE_YEAR}{m:02d}.parquet"
        n = len(pd.read_parquet(p, columns=["ANO_CMPT"])) if p.exists() else 0
        rows.append({"uf": uf, "mes": m, "existe": p.exists(), "aihs": n})
cov = pd.DataFrame(rows)
print(cov.pivot(index="uf", columns="mes", values="aihs").fillna(0).astype(int))
faltando = cov[~cov.existe]
if len(faltando):
    print("\nFALTANDO:")
    print(faltando[["uf", "mes"]].to_string(index=False))
    print("\n  -> relancar so esses:  python src/loadData.py --uf <UF> "
          f"--year {SAMPLE_YEAR} --months <M> --force")

# --- carrega o escopo ------------------------------------------------------
scoped = pd.read_parquet(DATA_PROCESSED / "phase0_sample_scoped.parquet")

# --- B. MUNIC_MOV mede o que? ---------------------------------------------
sec("B. MUNIC_MOV mede o local de internacao?")
s = scoped.copy()
s["ufFromMunicMov"] = s["MUNIC_MOV"].astype(str).str.zfill(6).str[:2].map(UF_BY_IBGE_PREFIX)
s["ufFromUfZi"] = s["UF_ZI"].astype(str).str.zfill(6).str[:2].map(UF_BY_IBGE_PREFIX)
s["ufFromFile"] = s["UF_SIGLA"]

print("Concordancia entre as tres fontes de 'UF de internacao':")
print(f"  MUNIC_MOV == UF_ZI       : {(s.ufFromMunicMov == s.ufFromUfZi).mean():.1%}")
print(f"  MUNIC_MOV == arquivo/UF  : {(s.ufFromMunicMov == s.ufFromFile).mean():.1%}")
print(f"  UF_ZI     == arquivo/UF  : {(s.ufFromUfZi == s.ufFromFile).mean():.1%}")
print("\n  Se as tres concordam ~100%, as tres medem a mesma coisa (o gestor),")
print("  e o local real de atendimento vem do municipio do CNES, nao daqui.")

print(f"\nMUNIC_MOV distintos: {s.MUNIC_MOV.nunique():,}")
print(f"MUNIC_RES distintos: {s.MUNIC_RES.nunique():,}")
print(f"CNES distintos     : {s.CNES.nunique():,}")
print("\n  MUNIC_MOV com poucos valores distintos = e o gestor, nao o hospital.")
print("\nTop 10 MUNIC_MOV:")
print(s.MUNIC_MOV.value_counts().head(10).to_string())

# --- C. fluxo interestadual ------------------------------------------------
sec("C. Fluxo interestadual (residencia -> internacao)")
s = add_uf_columns(s)
valid = s[s.ufResidence.notna() & s.ufHospital.notna()].copy()
valid["foraDaUF"] = valid.ufResidence != valid.ufHospital

print(f"AIHs no escopo com as duas UFs: {len(valid):,}")
print(f"Fora da UF de residencia      : {valid.foraDaUF.sum():,} ({valid.foraDaUF.mean():.2%})")

print("\nPor UF de residencia:")
print(valid.groupby("ufResidence").agg(
    aihs=("foraDaUF", "size"), fora=("foraDaUF", "sum"),
    pct=("foraDaUF", "mean")).sort_values("aihs", ascending=False).to_string())

print("\nPor doenca:")
print(valid.groupby("diseaseShort").agg(
    aihs=("foraDaUF", "size"), fora=("foraDaUF", "sum"),
    pct=("foraDaUF", "mean")).sort_values("aihs", ascending=False).to_string())

if valid.foraDaUF.any():
    print("\nPares origem->destino observados:")
    print(valid[valid.foraDaUF].groupby(["ufResidence", "ufHospital"])
          .size().rename("aihs").sort_values(ascending=False).to_string())

print("\n  ATENCAO: so baixamos 4 UFs. Um residente de GO internado em GO nao")
print("  esta na amostra; um residente de GO internado em DF esta. Isso")
print("  SUPERESTIMA o fluxo. O numero so fecha com as 27 UFs baixadas.")

# --- D. extrapolacao -------------------------------------------------------
sec("D. Volume por doenca: amostra -> periodo completo")
n_meses_ok = int(cov.existe.sum())
by = scoped.groupby(["diseaseShort", "diseaseName"]).size().rename("amostra").reset_index()
# 12 UF-meses previstos; escala para 27 UFs x 12 meses x 6 anos
fator = (27 / len(SAMPLE_UFS)) * (12 / len(SAMPLE_MONTHS)) * 6
by["proj_2019_2024"] = (by.amostra * fator * (12 / max(n_meses_ok, 1))).round().astype(int)
print(by.sort_values("amostra", ascending=False).to_string(index=False))
print(f"\n  ({n_meses_ok}/12 arquivos presentes; fator de escala {fator:.0f}x)")
print("  Projecao grosseira: assume distribuicao uniforme entre UFs, o que e falso.")
print("  Serve so para decidir o que fica no escopo, nao como estimativa.")
