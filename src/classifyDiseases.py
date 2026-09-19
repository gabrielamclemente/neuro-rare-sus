"""Classificacao das AIHs nas doencas neurologicas raras do escopo."""

import pandas as pd

from config import DISEASE_PREFIXES, DISEASES, UF_BY_IBGE_PREFIX


def _match(cid: str) -> str | None:
    if not isinstance(cid, str):
        return None
    cid = cid.strip().upper().replace(".", "")
    for pref in DISEASE_PREFIXES:
        if cid.startswith(pref):
            return pref
    return None


def classify(df: pd.DataFrame, use_secondary: bool = False) -> pd.DataFrame:
    """Adiciona diseaseCode / diseaseName / diseaseShort e filtra o escopo.

    use_secondary=False (padrao) usa so DIAG_PRINC: cada AIH conta uma vez e a
    internacao foi de fato motivada pela condicao. O secundario serve para uma
    analise de sensibilidade, nao para o numero principal.
    """
    out = df.copy()
    out["diseaseCode"] = out["DIAG_PRINC"].map(_match)

    if use_secondary and "DIAG_SECUN" in out.columns:
        sec = out["DIAG_SECUN"].map(_match)
        out["diseaseCode"] = out["diseaseCode"].fillna(sec)

    out = out[out["diseaseCode"].notna()].copy()
    out["diseaseName"] = out["diseaseCode"].map(lambda c: DISEASES[c]["name"])
    out["diseaseShort"] = out["diseaseCode"].map(lambda c: DISEASES[c]["short"])
    return out


def add_uf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva UF de residencia e UF de internacao a partir do codigo IBGE."""
    out = df.copy()
    for src, dest in (("MUNIC_RES", "ufResidence"), ("MUNIC_MOV", "ufHospital")):
        if src in out.columns:
            out[dest] = (
                out[src].astype(str).str.zfill(6).str[:2].map(UF_BY_IBGE_PREFIX)
            )
    if "ufHospital" not in out.columns and "UF_ZI" in out.columns:
        out["ufHospital"] = (
            out["UF_ZI"].astype(str).str.zfill(6).str[:2].map(UF_BY_IBGE_PREFIX)
        )
    return out
