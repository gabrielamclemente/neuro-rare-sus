# NeuroRare SUS

**Demanda, capacidade e acesso** — onde acontece o cuidado hospitalar de doenças
neurológicas raras no Brasil, e quanto as pessoas se deslocam para alcançá-lo.

Dados abertos do SIH/SUS · 27 UFs · 2024 · Python, SQL, Tableau/Power BI

> **Nota metodológica.** O SIH/SUS registra produção hospitalar aprovada (AIHs),
> não pessoas únicas. Nenhum número aqui é contagem de pacientes.

Documentação completa de proveniência, decisões e limites:
**[docs/METHODOLOGY.md](docs/METHODOLOGY.md)** ·
Especificação do dashboard: **[docs/DASHBOARD_SPEC.md](docs/DASHBOARD_SPEC.md)**

---

## A pergunta

Existe correspondência entre onde está a demanda por atendimento de pessoas com
doenças neurológicas raras e onde está a capacidade especializada do SUS?

Cinco condições da lista oficial do Ministério da Saúde: esclerose múltipla
(G35), esclerose lateral amiotrófica (G12.2), miastenia gravis (G70.0), atrofia
muscular espinhal (G12.0) e polineuropatia amiloidótica familiar (E85.1).

## O que os dados mostraram

**Existem dois regimes de cuidado dentro do mesmo escopo.** Episódios de
tratamento — surto de esclerose múltipla, administração de medicação — duram um
dia e concentram-se em poucos municípios. Internações clínicas — ELA, miastenia
— duram de 9 a 21 dias e distribuem-se pela rede hospitalar geral.

| Condição | AIHs | % com ≤1 dia | % em 5 municípios |
|---|---:|---:|---:|
| Esclerose Múltipla | 8.396 | 73,4% | 74,0% |
| Esclerose Lateral Amiotrófica | 1.309 | 9,4% | 27,1% |
| Miastenia Gravis | 1.136 | 15,8% | 26,4% |
| Atrofia Muscular Espinhal | 720 | 68,9% | 62,2% |
| Polineuropatia Amiloidótica Familiar | 29 | 86,2% | 89,7% |

As duas últimas colunas se espelham: **a concentração geográfica acompanha o
tipo de episódio, não a raridade da condição.**

**O deslocamento é intraestadual.** Cerca de metade das AIHs ocorrem fora do
município de residência; apenas 0,8% cruzam fronteira estadual. Recife concentra
43% do atendimento nacional de atrofia muscular espinhal.

**Uma hipótese inicial foi refutada.** Uma amostra de 4 UFs sugeria 17% de
deslocamento interestadual na AME; com as 27 UFs, o número é 2,8%. O achado não
foi ajustado para preservar a narrativa — a refutação está documentada na
[metodologia](docs/METHODOLOGY.md#7-geografia-residência-e-local-de-internação).

## O que o projeto não afirma

Não mede prevalência, não mede acesso, não mede qualidade assistencial e não
estabelece causalidade. Mortalidade hospitalar bruta não é indicador de
qualidade sem ajuste por risco. A maior parte do cuidado dessas condições é
ambulatorial (SIA/SUS) e está fora deste escopo.

## Como reproduzir

```bash
pip install -r requirements.txt

python src/validateData.py                                  # Fase 0 — viabilidade
python src/loadData.py --all-ufs --all-months --year 2024   # extração
python src/loadData.py --retry-missing --year 2024          # recupera lacunas
python src/cleanData.py --year 2024                         # agrega -> SQLite
python src/exportForBI.py                                   # CSVs p/ o dashboard
```

`data/` não é versionado: são alguns GB de dado público reconstruível. O
repositório versiona a receita.

**Cobertura obtida:** 322 de 324 UF-meses (99,4%). AM e PI sem fevereiro/2024.
A tabela `dataCoverage` registra isso por UF, e as comparações normalizam por
meses disponíveis.

## Estrutura

```
├── src/
│   config.py            constantes: CIDs, colunas do SIH, mapa IBGE→UF
│   loadData.py          download do SIH-RD com cache e fontes alternativas
│   classifyDiseases.py  match de CID-10 e derivação das UFs
│   validateData.py      Fase 0 — as 7 checagens de viabilidade
│   inspectPhase0.py     diagnóstico de cobertura e fluxo
│   probeSource.py       sonda as fontes do PySUS
│   cleanData.py         agregação e carga no SQLite
│   exportForBI.py       exporta as views para CSV
├── sql/
│   createTables.sql     modelo de dados
│   dashboardViews.sql   views que alimentam o dashboard
│   demandAnalysis.sql   demanda, evolução, per capita, fluxo
│   capacityAnalysis.sql oferta e cruzamento demanda × capacidade
├── docs/
│   METHODOLOGY.md       proveniência, decisões, limites
│   DASHBOARD_SPEC.md    especificação visual (Power BI e Tableau)
└── powerBi/             dashboard e CSVs gerados
```

## Estado atual

Concluído: extração, classificação, agregação, modelo de dados, views do
dashboard, documentação metodológica.

Em andamento: construção do dashboard.

Pendente: habilitações da Rede de Doenças Raras (CNES) e população por UF
(IBGE) — destravam a análise de demanda × capacidade.

### A pergunta em aberto

Os municípios que concentram cada condição são serviços habilitados da Rede de
Atenção Especializada em Doenças Raras? Se sim, a rede funciona como desenhada e
a questão passa a ser a equidade do acesso geográfico a ela. Se não, o cuidado
está se concentrando fora da rede formal — o que seria um achado de gestão com
peso próprio.