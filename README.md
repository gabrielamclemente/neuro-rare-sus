# NeuroRare SUS

**Demand, Capacity & Access** — mapeamento da demanda hospitalar e capacidade especializada do SUS para doenças neurológicas raras no Brasil.

> **Nota metodológica.** O SIH/SUS registra **produção aprovada** (AIHs), não pessoas únicas. Todo número aqui é "internações registradas relacionadas à condição no período", nunca "pacientes com a doença". 

## Escopo

| Doença | CID-10 | Código no SIH |
|---|---|---|
| Atrofia Muscular Espinhal | G12.0 | `G120` |
| Esclerose Lateral Amiotrófica | G12.2 | `G122` |
| Esclerose Múltipla | G35 | `G35` |
| Miastenia Gravis | G70.0 | `G700` |
| Polineuropatia Amiloidótica Familiar | E85.1 | `E851` |

## Perguntas

1. **Demanda** — como evoluiu a utilização do SUS relacionada a essas condições?
2. **Capacidade** — onde estão os serviços habilitados em doenças raras?
3. **Desalinhamento** — quais regiões têm mais demanda registrada por serviço disponível?

## Como rodar

```bash
pip install -r requirements.txt

# Fase 0 — viabilidade (SEMPRE antes de qualquer outra coisa)
python src/validateData.py
```

A Fase 0 baixa uma amostra pequena (SP/MG/BA/DF, 1º trimestre de 2024) e responde às 7 perguntas de viabilidade. Se os itens 1–4 falharem, o projeto muda de forma antes de você investir tempo — o plano B é focar só em AME ("AME 5q: From Diagnosis to Care").

## Estrutura

```
neuroRareSUS/
├── data/raw/          # parquet do SIH, um arquivo por UF/mês (não versionar)
├── data/processed/    # tabelas agregadas + saídas da Fase 0
├── src/
│   ├── config.py           # CIDs, colunas do SIH, amostra, mapa IBGE→UF
│   ├── loadData.py         # download do SIH-RD via PySUS, com cache
│   ├── classifyDiseases.py # match de CID + derivação das UFs
│   └── validateData.py     # FASE 0 — as 7 checagens
├── sql/
│   ├── createTables.sql    # modelo: hospitalAdmissions / rareDiseaseServices / population
│   ├── demandAnalysis.sql  # demanda, evolução, per capita, fluxo interestadual
│   └── capacityAnalysis.sql# oferta, demanda×capacidade, concentração
└── powerBi/
```

## Dados que ainda precisam de passo manual

| Base | Onde | Observação |
|---|---|---|
| SIH-RD | automático (PySUS) | já coberto por `loadData.py` |
| Habilitações CNES em doenças raras | painel oficial da Rede de Doenças Raras / CNES-ST | baixar e salvar em `data/processed/rare_disease_services.csv` com colunas `establishmentId,establishmentName,uf,municipality,serviceType` |
| População por UF | IBGE/SIDRA tabela 6579 | salvar em `data/processed/population_uf.csv` (`year,uf,population`) |

## Roadmap

- **MVP (~2 semanas):** Fase 0 → tabelas agregadas → SQLite → Power BI páginas 1–2.
- **v2 (4–6 semanas):** fluxo residência→internação (página 4), indicador demanda/serviço (página 3), documentação metodológica.
- **v3 (opcional):** aprofundar AME — PCDT, procedimentos, terapia gênica.

## Limites do indicador `admissionsPerService`

É um **indicador exploratório** da relação entre demanda hospitalar registrada e oferta especializada. Não mede acesso real: nem toda internação exige centro especializado, e um serviço habilitado atende residentes de várias UFs.
