"""FASE 0 - Viabilidade dos dados.

Roda as 7 perguntas antes de investir tempo em modelagem e Power BI:

  1. Consigo baixar o SIH/SUS?
  2. Consigo identificar os CIDs do escopo?
  3. Existem registros suficientes?
  4. Consigo separar residencia de local de internacao?
  5. Consigo identificar servicos de doencas raras no CNES?
  6. Consigo cruzar CNES entre as bases?
  7. Consigo obter populacao por UF?

Uso:
    python src/validateData.py
"""

import sys

import pandas as pd

from classifyDiseases import add_uf_columns, classify
from config import (DATA_PROCESSED, DISEASES, SAMPLE_MONTHS, SAMPLE_UFS,
                    SAMPLE_YEAR)
from loadData import download_many

MIN_RECORDS_PER_DISEASE = 30   # por doenca, na amostra -> escala p/ periodo cheio
MIN_RECORDS_TOTAL = 500

results: dict[str, tuple[bool, str]] = {}


def check(n: int, title: str, ok: bool, detail: str) -> None:
    results[f"{n}. {title}"] = (ok, detail)
    print(f"\n{'[OK]  ' if ok else '[FALHA]'} {n}. {title}\n      {detail}")


def main() -> int:
    print("=" * 70)
    print(f"FASE 0 - amostra: {SAMPLE_UFS} / {SAMPLE_YEAR} / meses {SAMPLE_MONTHS}")
    print("=" * 70)

    # --- 1. download -------------------------------------------------------
    raw = download_many(SAMPLE_UFS, SAMPLE_YEAR, SAMPLE_MONTHS)
    ok1 = not raw.empty
    check(1, "Download do SIH/SUS",
          ok1,
          f"{len(raw):,} AIHs baixadas, colunas: {list(raw.columns)}" if ok1
          else "Nenhum arquivo baixado - ver rede/PySUS ou trocar o periodo.")
    if not ok1:
        summary()
        return 1

    # --- 2. identificacao dos CIDs ----------------------------------------
    scoped = classify(raw)
    ok2 = not scoped.empty
    found = sorted(scoped["diseaseCode"].unique()) if ok2 else []
    check(2, "Identificacao dos CIDs",
          ok2,
          f"CIDs encontrados na amostra: {found}" if ok2
          else "Nenhum CID do escopo bateu - conferir o formato de DIAG_PRINC.")

    # --- 3. volume --------------------------------------------------------
    counts = (scoped.groupby(["diseaseCode", "diseaseName"]).size()
              .rename("aihs").reset_index().sort_values("aihs", ascending=False))
    print("\n      Contagem por doenca (amostra):")
    for _, r in counts.iterrows():
        print(f"        {r.diseaseCode:<5} {r.diseaseName:<40} {r.aihs:>7,}")
    weak = [c for c in DISEASES
            if int(counts.loc[counts.diseaseCode == c, "aihs"].sum()) < MIN_RECORDS_PER_DISEASE]
    ok3 = len(scoped) >= MIN_RECORDS_TOTAL
    check(3, "Volume de registros",
          ok3,
          f"{len(scoped):,} AIHs no escopo. "
          + (f"Doencas com volume baixo na amostra: {weak} (avaliar agregar por grupo "
             f"ou ampliar o periodo)." if weak else "Todas as doencas com volume utilizavel."))

    # --- 4. residencia x internacao ---------------------------------------
    scoped = add_uf_columns(scoped)
    has_both = {"ufResidence", "ufHospital"} <= set(scoped.columns)
    if has_both:
        valid = scoped[["ufResidence", "ufHospital"]].notna().all(axis=1)
        out_of_state = (scoped.loc[valid, "ufResidence"] != scoped.loc[valid, "ufHospital"]).mean()
        ok4 = valid.mean() > 0.95
        detail = (f"{valid.mean():.1%} das AIHs com as duas UFs preenchidas; "
                  f"{out_of_state:.1%} internadas fora da UF de residencia "
                  f"-> a pagina de Patient Flow tem material.")
    else:
        ok4, detail = False, "MUNIC_RES/MUNIC_MOV ausentes - fluxo interestadual inviavel."
    check(4, "Residencia x local de internacao", ok4, detail)

    # --- 5 e 6. CNES ------------------------------------------------------
    has_cnes = "CNES" in scoped.columns and scoped["CNES"].notna().any()
    n_estab = scoped["CNES"].nunique() if has_cnes else 0
    check(5, "Habilitacao de doencas raras no CNES",
          has_cnes,
          f"{n_estab:,} estabelecimentos distintos na amostra. "
          "A lista de habilitados (cod. 25.xx / Rede de Doencas Raras) precisa vir do "
          "CNES-ST/DATASUS ou do painel oficial - passo manual, ver README."
          if has_cnes else "Coluna CNES ausente no SIH - cruzamento de oferta inviavel.")
    check(6, "Cruzamento por CNES entre as bases",
          has_cnes,
          "Chave CNES presente no SIH; o join com o cadastro de estabelecimentos "
          "e possivel assim que o arquivo do CNES for baixado."
          if has_cnes else "Sem chave comum entre demanda e oferta.")

    # --- 7. populacao -----------------------------------------------------
    pop_file = DATA_PROCESSED / "population_uf.csv"
    ok7 = pop_file.exists()
    check(7, "Populacao por UF",
          ok7,
          f"{pop_file.name} encontrado." if ok7 else
          f"Baixar as estimativas do IBGE (SIDRA tabela 6579) e salvar em {pop_file}. "
          "Nao bloqueia o MVP: so afeta os indicadores por 100 mil habitantes.")

    # --- saidas -----------------------------------------------------------
    out = DATA_PROCESSED / "phase0_sample_scoped.parquet"
    scoped.to_parquet(out, index=False)
    counts.to_csv(DATA_PROCESSED / "phase0_counts_by_disease.csv", index=False)
    print(f"\nAmostra classificada salva em: {out}")

    return summary()


def summary() -> int:
    print("\n" + "=" * 70)
    print("RESUMO DA FASE 0")
    print("=" * 70)
    for k, (ok, _) in results.items():
        print(f"  {'OK    ' if ok else 'FALHA '} {k}")
    blockers = [k for k, (ok, _) in results.items()
                if not ok and k.startswith(("1.", "2.", "3.", "4."))]
    if blockers:
        print("\n>> Bloqueadores (adaptar o projeto antes de seguir):")
        for b in blockers:
            print(f"   - {b}")
        print("   Plano B: focar so em AME (projeto 'AME 5q: From Diagnosis to Care').")
        return 1
    print("\n>> Viabilidade confirmada. Proximo passo: montar as tabelas agregadas e o SQL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
