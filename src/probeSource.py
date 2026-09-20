"""Sonda cada fonte do PySUS e imprime o erro COMPLETO."""
import re, sys, warnings
warnings.filterwarnings("ignore")
import pysus
from config import SIH_COLUMNS

uf  = sys.argv[1] if len(sys.argv) > 1 else "AC"
ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
mes = int(sys.argv[3]) if len(sys.argv) > 3 else 4
print(f"PySUS {getattr(pysus,'__version__','?')} | alvo: {uf} {ano}-{mes:02d}\n")

TENTATIVAS = [
    ("catalog (default)",  {}),
    ("catalog + columns",  {"columns": SIH_COLUMNS}),
    ("origin=FTP",         {"source": "origin", "origin": "FTP"}),
    ("origin=SAUDE",       {"source": "origin", "origin": "SAUDE"}),
    ("origin=DADOSGOV",    {"source": "origin", "origin": "DADOSGOV"}),
    ("FTP, download=False",{"source": "origin", "origin": "FTP", "download": False}),
    ("sem group",          {"source": "origin", "origin": "FTP", "_nogroup": True}),
]

def limpa(e):
    t = re.sub(r"[║╔╗╚╝═╠╣]", " ", str(e))
    return re.sub(r"\s+", " ", t).strip()

for nome, kw in TENTATIVAS:
    kw = dict(kw)
    nogroup = kw.pop("_nogroup", False)
    base = {"as_dataframe": True}
    if not nogroup:
        base["group"] = "RD"
    if kw.get("download") is False:
        base.pop("as_dataframe", None)
    try:
        r = pysus.sih(uf, ano, mes, **base, **kw)
        n = len(r) if r is not None else 0
        print(f"[{nome}]\n    OK -> {type(r).__name__}, {n} itens")
        if n and hasattr(r, "columns"):
            print(f"    colunas: {list(r.columns)[:8]} ...")
        elif n:
            print(f"    {list(r)[:3]}")
    except Exception as e:
        print(f"[{nome}]\n    {type(e).__name__}: {limpa(e)[:700]}")
    print()
