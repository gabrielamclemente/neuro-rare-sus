"""Sonda o CNES para achar a habilitacao em doencas raras.

Nao sabemos de antemao qual codigo identifica a habilitacao da Rede de Atencao
Especializada em Doencas Raras. Este script baixa um mes do CNES, lista os
grupos e codigos disponiveis, e cruza com os estabelecimentos que aparecem no
nosso escopo do SIH — para ver quais deles tem alguma habilitacao e qual.

Uso:
    python src/probeCnes.py              # PE 2024-06 (Recife concentra AME)
    python src/probeCnes.py SP 2024 6
"""

import re
import sys
import warnings

warnings.filterwarnings("ignore")

import pandas as pd

from config import DATA_PROCESSED

uf = sys.argv[1] if len(sys.argv) > 1 else "PE"
ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
mes = int(sys.argv[3]) if len(sys.argv) > 3 else 6


def limpa(e) -> str:
    t = re.sub(r"[║╔╗╚╝═╠╣]", " ", str(e))
    return re.sub(r"\s+", " ", t).strip()


def tentar(fn, uf, ano, mes, **kw):
    """Repete a estrategia que funcionou no SIH: se o filtro de grupo vier
    vazio, pede os caminhos e le o arquivo certo direto."""
    try:
        df = fn(uf, ano, mes, as_dataframe=True, **kw)
        if df is not None and len(df):
            return pd.DataFrame(df), None
        return None, "0 linhas"
    except Exception as e:
        return None, f"{type(e).__name__}: {limpa(e)[:200]}"


def main() -> int:
    try:
        import pysus
    except ImportError:
        print("PySUS nao instalado.")
        return 1

    cnes = getattr(getattr(pysus, "ftp", pysus), "cnes", None) or pysus.cnes
    print(f"PySUS {getattr(pysus, '__version__', '?')} | alvo: CNES {uf} {ano}-{mes:02d}\n")

    # ------------------------------------------------------------------ HB --
    # HB = habilitacoes. E o grupo que deve conter a habilitacao de doencas
    # raras, se ela existir como habilitacao formal.
    print("=== grupo HB (habilitacoes) ===")
    hb, erro = tentar(cnes, uf, ano, mes, group="HB")
    if hb is None:
        print(f"  falhou: {erro}")
        print("  tentando sem group, pelos caminhos de arquivo...")
        try:
            paths = cnes(uf, ano, mes, as_dataframe=False)
            nomes = [str(p).split("/")[-1] for p in (paths or [])]
            print(f"  arquivos disponiveis: {nomes}")
        except Exception as e:
            print(f"  tambem falhou: {limpa(e)[:200]}")
        return 1

    print(f"  {len(hb):,} linhas, {len(hb.columns)} colunas")
    print(f"  colunas: {list(hb.columns)}\n")

    # Procura a coluna de codigo de habilitacao sem assumir o nome.
    candidatas = [c for c in hb.columns
                  if re.search(r"(SGRUPHAB|COD|HAB)", c, re.I)]
    print(f"  colunas candidatas a codigo de habilitacao: {candidatas}\n")

    for c in candidatas[:4]:
        vc = hb[c].astype(str).str.strip().value_counts().head(15)
        print(f"  --- {c} (15 mais frequentes) ---")
        print(vc.to_string())
        print()

    # ------------------------------------------- cruzamento com o nosso SIH --
    print("=== cruzamento com os estabelecimentos do escopo ===")
    escopo_path = DATA_PROCESSED / "scoped_2024.parquet"
    if not escopo_path.exists():
        print(f"  {escopo_path.name} nao encontrado. Rode src/cleanData.py antes.")
        return 0

    escopo = pd.read_parquet(escopo_path, columns=["CNES", "diseaseShort", "MUNIC_MOV"])
    nossos = set(escopo.CNES.astype(str).str.strip().str.zfill(7))

    col_cnes = next((c for c in hb.columns if re.fullmatch(r"CNES", c, re.I)), None)
    if col_cnes is None:
        print(f"  nao achei coluna CNES em HB. Colunas: {list(hb.columns)}")
        return 0

    hb["_cnes"] = hb[col_cnes].astype(str).str.strip().str.zfill(7)
    cruzados = hb[hb._cnes.isin(nossos)]

    print(f"  estabelecimentos no nosso escopo (nacional): {len(nossos):,}")
    print(f"  deles, com habilitacao em {uf}: {cruzados._cnes.nunique():,}")

    if len(cruzados) and candidatas:
        col = candidatas[0]
        print(f"\n  habilitacoes mais comuns entre os nossos ({col}):")
        print(cruzados[col].astype(str).str.strip().value_counts().head(20).to_string())

    print("\n  Proximo passo: identificar, na tabela de habilitacoes do SIGTAP/CNES,")
    print("  qual desses codigos corresponde a Rede de Atencao Especializada em")
    print("  Doencas Raras. So depois disso o cruzamento vira analise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
