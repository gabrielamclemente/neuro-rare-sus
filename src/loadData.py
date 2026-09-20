"""Download do SIH/SUS (grupo RD = AIH reduzida) via PySUS 2.x.

Uso:
    python src/loadData.py --sample          # amostra da Fase 0
    python src/loadData.py --uf SP --year 2024 --months 1 2 3
"""

import argparse
import sys

from pathlib import Path

import pandas as pd

from config import (DATA_RAW, SAMPLE_MONTHS, SAMPLE_UFS, SAMPLE_YEAR,
                    SIH_COLUMNS, UFS)


def _sih_fn():
    """Devolve a funcao de fetch do PySUS, lidando com as variacoes de API.

    Na 2.x o caminho recomendado e pysus.ftp.sih; pysus.sih ainda funciona mas
    emite DeprecationWarning. Versoes antigas (<2) usavam
    pysus.online_data.SIH.download, com assinatura diferente.
    """
    try:
        import pysus
    except ImportError:
        print("PySUS nao instalado. Rode: pip install -r requirements.txt")
        sys.exit(1)

    for path in ("ftp.sih", "sih"):
        obj = pysus
        for part in path.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                break
        if callable(obj):
            return obj

    print(f"PySUS {getattr(pysus, '__version__', '?')} instalado, mas nenhuma "
          "funcao 'sih' foi encontrada. Reporte a saida de: python -c "
          "'import pysus; print(dir(pysus))'")
    sys.exit(1)


def _parquet_path(uf: str, year: int, month: int):
    return DATA_RAW / f"sih_rd_{uf}_{year}{month:02d}.parquet"


# Fontes, em ordem de preferencia. O default do PySUS (catalog) e um espelho
# em Parquet, rapido mas INCOMPLETO: faltam particoes inteiras. O FTP e o
# servidor original do DATASUS: mais lento, porem canonico.
SOURCES = [
    ("catalog", {}),                                  # espelho rapido
    ("origin/FTP", {"source": "origin", "origin": "FTP"}),
    ("origin/Saude", {"source": "origin", "origin": "Saude"}),
]


def _resolver_no_cache(nome_ou_caminho: str):
    """O PySUS devolve nomes soltos; o arquivo fica no cache (~/pysus).

    Procura, nesta ordem: o caminho como veio, o cache declarado pela
    biblioteca, e por fim uma varredura recursiva do cache.
    """
    p = Path(nome_ou_caminho)
    if p.exists():
        return p

    candidatos = []
    try:
        import pysus
        cache = getattr(pysus, "CACHEPATH", None)
        if cache:
            candidatos.append(Path(cache))
    except Exception:
        pass
    candidatos.append(Path.home() / "pysus")

    nome = p.name
    for base in candidatos:
        if not base.exists():
            continue
        direto = base / nome
        if direto.exists():
            return direto
        achados = sorted(base.rglob(nome))
        if achados:
            return achados[0]
    return None


def _fetch_via_paths(sih, uf, year, month):
    """Plano C: pedir os CAMINHOS dos arquivos e ler o RD diretamente.

    Em ~23% das particoes de 2024 o catalogo do PySUS nao traz a marcacao de
    grupo, entao group="RD" devolve 0 linhas apesar de RD<UF><AA><MM>.parquet
    existir e baixar. Sem group vem ER+RJ+RD+SP empilhados, com esquemas
    diferentes - inutil. Pedindo os caminhos, escolhemos so o RD.
    """
    try:
        paths = sih(uf, year, month, as_dataframe=False)
    except Exception as exc:
        return None, f"paths: {type(exc).__name__}: {str(exc)[:110]}"
    if not paths:
        return None, "paths: nenhum arquivo"

    alvo = f"RD{uf.upper()}{year % 100:02d}{month:02d}"
    rd = [p for p in map(str, paths) if Path(p).name.upper().startswith(alvo)]
    if not rd:
        nomes = [Path(str(p)).name for p in paths][:6]
        return None, f"paths: sem {alvo}*. veio: {nomes}"

    alvo_path = _resolver_no_cache(rd[0])
    if alvo_path is None:
        return None, f"paths: {Path(rd[0]).name} nao encontrado no cache do PySUS"

    try:
        df = pd.read_parquet(alvo_path)
    except Exception as exc:
        return None, f"paths: leitura falhou: {type(exc).__name__}: {exc}"
    if df is None or len(df) == 0:
        return None, "paths: RD vazio"
    return df, ""


def _try_fetch(sih, uf, year, month, extra: dict, use_columns: bool):
    """Uma tentativa. Devolve (df, motivo). df=None quando nao veio nada."""
    kw = {"group": "RD", "as_dataframe": True, **extra}
    if use_columns:
        kw["columns"] = SIH_COLUMNS
    try:
        df = sih(uf, year, month, **kw)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:110]}"
    if df is None or len(df) == 0:
        return None, "0 linhas"
    return df, ""


def download_month(uf: str, year: int, month: int, force: bool = False,
                   sources=None, verbose: bool = True) -> pd.DataFrame | None:
    """Baixa um mes de SIH-RD, tentando cada fonte ate uma responder.

    Nao ha backoff: a falha do espelho e deterministica (a particao nao
    existe), entao esperar nao muda nada. O que muda e trocar de fonte.
    """
    out = _parquet_path(uf, year, month)
    if out.exists() and not force:
        print(f"[cache] {out.name}")
        return pd.read_parquet(out)

    sih = _sih_fn()
    print(f"[download] SIH-RD {uf} {year}-{month:02d} ...")

    df, motivos = None, []
    for nome, extra in (sources or SOURCES):
        # Sempre tenta com corte de colunas primeiro; se nao vier nada,
        # repete sem o corte (nem toda fonte aceita columns=).
        df, motivo = _try_fetch(sih, uf, year, month, extra, use_columns=True)
        if df is None:
            df2, motivo2 = _try_fetch(sih, uf, year, month, extra,
                                      use_columns=False)
            if df2 is not None:
                df, motivo = df2, ""
            else:
                motivo = f"{motivo} / sem columns: {motivo2}"
        if df is not None:
            if nome != "catalog" and verbose:
                print(f"  (veio de {nome})")
            break
        motivos.append(f"{nome}: {motivo}")

    if df is None:
        # Plano C: o filtro group="RD" falha em algumas particoes; buscar o
        # arquivo RD pelo caminho contorna isso.
        df, motivo = _fetch_via_paths(sih, uf, year, month)
        if df is not None and verbose:
            print("  (veio por caminho de arquivo; group='RD' estava vazio)")
        else:
            motivos.append(motivo)

    if df is None:
        print(f"  !! sem dados. {' | '.join(motivos)}")
        return None

    df = pd.DataFrame(df)

    keep = [c for c in SIH_COLUMNS if c in df.columns]
    missing = [c for c in SIH_COLUMNS if c not in df.columns]
    if missing:
        print(f"  (colunas ausentes neste mes: {missing})")
    if not keep:
        print(f"  !! nenhuma coluna esperada encontrada. Veio: {list(df.columns)[:25]}")
        return None
    df = df[keep].copy()

    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()

    df.to_parquet(out, index=False)
    print(f"  ok: {len(df):,} AIHs -> {out.name}")
    return df


def missing_pairs(ufs, year, months) -> list[tuple[str, int]]:
    """UF-meses cujo parquet ainda nao existe em data/raw."""
    return [(uf, m) for uf in ufs for m in months
            if not _parquet_path(uf, year, m).exists()]


def download_pairs(pairs, year, force=False, concat=True) -> pd.DataFrame:
    """Baixa uma lista explicita de (uf, mes). Falhas nao interrompem o lote."""
    frames, failures = [], []
    total = len(pairs)
    for i, (uf, m) in enumerate(pairs, 1):
        print(f"--- [{i}/{total}] ---")
        try:
            df = download_month(uf, year, m, force=force)
        except Exception as exc:
            print(f"  !! erro inesperado: {type(exc).__name__}: {exc}")
            df = None
        if df is None:
            failures.append((uf, m))
            continue
        if concat:
            df["UF_SIGLA"] = uf
            frames.append(df)

    if failures:
        print(f"\n!! {len(failures)}/{total} UF-mes sem dados: "
              + ", ".join(f"{u}-{m:02d}" for u, m in failures))
    else:
        print(f"\nTodos os {total} vieram.")

    if not concat or not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def download_many(ufs, year, months, force=False, concat=True) -> pd.DataFrame:
    pairs = [(uf, m) for uf in ufs for m in months]
    return download_pairs(pairs, year, force=force, concat=concat)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="amostra da Fase 0")
    ap.add_argument("--all-ufs", action="store_true", help="as 27 UFs")
    ap.add_argument("--all-months", action="store_true", help="os 12 meses")
    ap.add_argument("--uf", nargs="*", default=None)
    ap.add_argument("--year", type=int, default=SAMPLE_YEAR)
    ap.add_argument("--months", nargs="*", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retry-missing", action="store_true",
                    help="baixa so os UF-meses que ainda faltam em data/raw")
    a = ap.parse_args()

    if a.all_ufs or a.retry_missing:
        ufs = UFS
    elif a.uf:
        ufs = [u.upper() for u in a.uf]
    else:
        ufs = SAMPLE_UFS

    if a.all_months or a.retry_missing:
        months = list(range(1, 13))
    elif a.months:
        months = a.months
    else:
        months = SAMPLE_MONTHS

    if a.retry_missing:
        pairs = missing_pairs(ufs, a.year, months)
        if not pairs:
            print(f"Nada faltando para {a.year}: os 324 arquivos estao em data/raw.")
            sys.exit(0)
        print(f"Faltando {len(pairs)} UF-mes em {a.year}. Retomando so esses.\n")
    else:
        pairs = [(uf, m) for uf in ufs for m in months]

    # Em lotes grandes nao acumulamos nada em RAM: os parquets ficam no disco.
    big = len(pairs) > 40
    df = download_pairs(pairs, a.year, force=a.force, concat=not big)

    n = len(list(DATA_RAW.glob(f"sih_rd_*_{a.year}*.parquet")))
    print(f"\ndata/raw agora tem {n}/324 arquivos de {a.year}.")
    if not big:
        print(f"Registros nesta rodada: {len(df):,}")
