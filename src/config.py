"""Configuracao central do projeto NeuroRare SUS."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "neuroraresus.db"

for _p in (DATA_RAW, DATA_PROCESSED):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Doencas neurologicas raras analisadas (CID-10).
# O SIH grava o diagnostico em DIAG_PRINC sem ponto: G120, G122, G35, G700, E851.
# Usamos prefixos para capturar subcategorias.
# ---------------------------------------------------------------------------
DISEASES = {
    "G120": {"name": "Atrofia Muscular Espinhal", "short": "AME"},
    "G122": {"name": "Esclerose Lateral Amiotrofica", "short": "ELA"},
    "G35": {"name": "Esclerose Multipla", "short": "EM"},
    "G700": {"name": "Miastenia Gravis", "short": "MG"},
    "E851": {"name": "Polineuropatia Amiloidotica Familiar", "short": "PAF"},
}

# Prefixos mais longos primeiro, para G120 ganhar de G12 se um dia for incluido.
DISEASE_PREFIXES = tuple(sorted(DISEASES, key=len, reverse=True))

# Colunas do SIH-RD (AIH reduzida) que realmente usamos.
SIH_COLUMNS = [
    "ANO_CMPT",     # ano de competencia
    "MES_CMPT",     # mes de competencia
    "UF_ZI",        # UF/gestor da internacao
    "MUNIC_RES",    # municipio de residencia (IBGE 6 digitos)
    "MUNIC_MOV",    # municipio de internacao
    "DIAG_PRINC",   # CID-10 principal
    "DIAG_SECUN",   # CID-10 secundario
    "IDADE",
    "COD_IDADE",    # 2=dias 3=meses 4=anos
    "SEXO",
    "DIAS_PERM",
    "MORTE",
    "VAL_TOT",
    "PROC_REA",     # procedimento realizado
    "CNES",         # estabelecimento -> chave de cruzamento com o CNES
]

# Amostra da Fase 0: poucos meses e UFs, para testar rapido.
SAMPLE_UFS = ["SP", "MG", "BA", "DF"]
SAMPLE_YEAR = 2024
SAMPLE_MONTHS = [1, 2, 3]

# Periodo completo (rodar so depois que a Fase 0 passar).
FULL_YEARS = list(range(2019, 2025))
UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

UF_BY_IBGE_PREFIX = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "41": "PR", "42": "SC", "43": "RS", "35": "SP", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}
