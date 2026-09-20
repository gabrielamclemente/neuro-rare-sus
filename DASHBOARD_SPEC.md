# Especificação do dashboard — NeuroRare SUS

Guia de construção no Power BI. Cada página lista a fonte de dados, os visuais,
os campos e o texto fixo. As escolhas de forma e cor estão justificadas — não
são preferência estética.

Fonte: os CSVs em `powerBi/data/`, gerados por `python src/exportForBI.py`.
No Power BI: **Obter Dados → Pasta** apontando para `powerBi/data/`, ou um CSV
por vez.

---

## Antes de começar: a paleta

O Power BI traz uma paleta padrão que não é segura para daltonismo. Substitua
por esta, que foi validada (separação CVD ΔE 9,1; visão normal ΔE 19,6):

| Ordem | Condição | Hex claro | Hex escuro |
|---|---|---|---|
| 1 | Esclerose Múltipla | `#2a78d6` | `#3987e5` |
| 2 | Esclerose Lateral Amiotrófica | `#eb6834` | `#d95926` |
| 3 | Miastenia Gravis | `#1baf7a` | `#199e70` |
| 4 | Atrofia Muscular Espinhal | `#eda100` | `#c98500` |
| 5 | Polineuropatia Amiloidótica Familiar | `#e87ba4` | `#d55181` |

**A cor segue a condição, sempre na mesma ordem, em todas as páginas.** Se um
filtro reduz de cinco para duas condições, as duas mantêm suas cores — não
repinte as sobreviventes. No Power BI isso se faz em *Formatar → Cores dos
dados*, fixando por valor, não por posição.

Três dessas cores ficam abaixo de 3:1 de contraste com fundo claro. A
consequência é obrigatória, não opcional: **todo visual colorido leva rótulo de
valor visível ou tem uma tabela equivalente na mesma página.** A cor nunca é a
única portadora de informação.

### Regras que valem para o dashboard inteiro

- **Nunca dois eixos y.** Duas medidas de escalas diferentes viram dois visuais.
- **Nada de pizza ou rosca.** Comparação de magnitude é barra.
- **Nada de 3D, sombra ou gradiente decorativo.**
- **Grade e eixos discretos**, cinza claro; o dado é que tem contraste.
- **Legenda sempre que houver duas ou mais séries**, com rótulo direto nas
  séries principais.

---

## O problema de escala, e como resolvê-lo

A esclerose múltipla tem 8.396 AIHs; a PAF tem 29. Num mesmo gráfico de barras,
a PAF vira um traço invisível.

**Não use escala logarítmica** — ela distorce a percepção de magnitude, que é
justamente o que a barra deveria comunicar.

Use uma destas, conforme a página:
- **Rótulo de valor em todas as barras.** O leitor lê "29" mesmo sem enxergar a
  barra. Resolve o caso simples.
- **Múltiplos pequenos**: um painel por condição, cada um com seu próprio eixo.
  É a solução certa para séries temporais.
- **Percentual dentro da condição** em vez de valor absoluto, quando a pergunta
  é sobre distribuição e não sobre volume.

---

## Página 1 — Panorama

**Fonte:** `vwOverview.csv`, `vwMonthly.csv`, `dataCoverage.csv`

### Cartões (linha superior)

| Rótulo | Medida | Observação |
|---|---|---|
| AIHs registradas | `SUM(admissions)` | **não** rotule como "pacientes" |
| Condições analisadas | 5 | fixo |
| Municípios que atendem | `DISTINCTCOUNT(municipalityHospital)` | |
| Óbitos hospitalares | `SUM(deaths)` | |
| Valor aprovado em AIH | `SUM(approvedValue)` | **não** rotule como "custo" |

O rótulo de cada cartão é parte do rigor do projeto. "Internações" sugere pessoas
internadas; "AIHs registradas" é o que o dado é.

### Faixa de ressalva (abaixo dos cartões, texto fixo, fonte menor)

> Dados: SIH/SUS 2024, 322 de 324 UF-meses (99,4%). AM e PI sem fevereiro.
> AIHs registram produção hospitalar aprovada, não pessoas únicas.

Deixar isso visível na primeira página, e não escondido numa página "sobre", é
uma decisão deliberada.

### Visual 1 — AIHs por condição

**Barras horizontais**, ordenadas por volume decrescente, rótulo de valor em
todas. Horizontal porque os nomes das condições são longos; ordenada porque a
comparação é de magnitude.

Campos: eixo `diseaseName`, valor `admissions`, cor por `diseaseName`.

### Visual 2 — Regime de cuidado

**Barras 100% empilhadas**, uma por condição, com duas séries: AIHs de até um
dia e AIHs mais longas.

Campos: eixo `diseaseName`, valores `shortStayAdmissions` e
`admissions - shortStayAdmissions`.

Aqui a cor **não** é por condição — as séries são os dois regimes. Use dois tons
neutros distintos (um escuro, um claro), com 2px de respiro entre os segmentos.

Título: *"Duas naturezas de AIH dentro do mesmo escopo"*.

### Visual 3 — Evolução mensal

**Múltiplos pequenos**: cinco painéis de linha, um por condição, cada um com seu
eixo. Linha de 2px, marcadores de 8px, sem rótulo em cada ponto.

Campos: eixo `yearMonth`, valor `admissions`, painel por `diseaseName`.

Um único gráfico com as cinco séries faria a EM achatar as outras quatro.

---

## Página 2 — Perfil das condições

**Fonte:** `vwOverview.csv`, `vwByUf.csv`

Segmentação (slicer) por `diseaseName` no topo, em linha única.

### Visual 1 — Tabela comparativa

Matriz com uma linha por condição:

| Coluna | Campo |
|---|---|
| Condição | `diseaseName` |
| Regime | `careRegime` |
| AIHs | `admissions` |
| % até 1 dia | `shortStayAdmissions / admissions` |
| Permanência média (dias) | `avgLengthOfStay` |
| Mortalidade hospitalar | `inHospitalMortalityPct` |
| Municípios que atendem | `municipalitiesTreating` |

Esta tabela é também a "tabela equivalente" que o aviso de contraste da paleta
exige.

### Visual 2 — Permanência × concentração

**Dispersão.** Eixo x: % de AIHs com até um dia. Eixo y: % do atendimento nos
cinco maiores municípios. Um ponto por condição, rotulado com o nome.

É o achado central do projeto num único visual: os pontos se alinham numa
diagonal. Marcadores de pelo menos 12px, rótulo direto em todos os cinco —
com cinco pontos, legenda separada é desnecessária.

Título: *"A concentração do cuidado acompanha o tipo de episódio, não a raridade"*.

### Visual 3 — Ressalva sobre mortalidade

Caixa de texto ao lado da tabela:

> Mortalidade hospitalar bruta não é indicador de qualidade assistencial. Não há
> ajuste por gravidade, e centros de referência tendem a receber os casos mais
> graves.

---

## Página 3 — Demanda × capacidade

**Depende do CNES e do IBGE — construir por último.**

Estrutura prevista: mapa coroplético do Brasil por UF (AIHs por 100 mil
habitantes, usando `admissionsAnnualized` para corrigir a cobertura de AM e PI),
tabela UF × serviços habilitados × razão demanda/serviço, com as UFs sem serviço
marcadas em vez de exibirem divisão por zero.

O indicador é estratificado por condição. Um número agregado único misturaria os
dois regimes e não teria significado clínico.

---

## Página 4 — Território e deslocamento

**Fonte:** `vwConcentration.csv`, `vwTravelSummary.csv`, `vwFlow.csv`

É a página mais forte do projeto. Construa-a antes da 3.

### Visual 1 — Curva de concentração

**Linhas**, uma por condição. Eixo x: posição do município no ranking (1 a 20).
Eixo y: percentual acumulado do atendimento.

Campos: eixo `rankInDisease` (filtrado para ≤20), valor `cumulativePct`,
série `diseaseName`.

Cinco curvas que sobem em velocidades diferentes. A da PAF quase encosta no
topo imediatamente; a da ELA sobe devagar. Rótulo direto no fim de cada linha.

Título: *"Quanto do atendimento cabe nos primeiros municípios"*.

### Visual 2 — Tipo de deslocamento

**Barras 100% empilhadas** por condição, três séries: mesmo município, outro
município da mesma UF, outra UF.

Campos: eixo `diseaseName`, valor `pct`, série `travelType` (de
`vwTravelSummary`).

A faixa "outra UF" será quase invisível — e isso é o ponto. Mostra que o
deslocamento é intraestadual.

### Visual 3 — Principais municípios

Tabela dos dez maiores por condição: município, AIHs, % da condição, %
acumulado. Filtrada pela segmentação de condição.

### Visual 4 — Texto de leitura

> Cerca de metade das AIHs ocorrem fora do município de residência, enquanto
> apenas 0,8% cruzam fronteira estadual. A rede de referência se organiza dentro
> dos estados. Recife concentra 43% do atendimento nacional de Atrofia Muscular
> Espinhal.
>
> Concentração não é, por si, um problema: condições raras exigem volume para
> manter expertise. A questão que este painel levanta é se o acesso geográfico a
> esses centros é equitativo.

Esse parágrafo evita a leitura preguiçosa de que concentração equivale a
desigualdade.

---

## Ordem de construção sugerida

1. Página 1 — estabelece a paleta e as medidas base.
2. Página 4 — o achado principal.
3. Página 2 — perfis.
4. Página 3 — depois do CNES e do IBGE.

---

## O que nunca aparece no dashboard

- A palavra "pacientes" para se referir a contagens de AIH.
- "Custo do tratamento" para `approvedValue`.
- Total agregado das cinco condições apresentado como "internações".
- Mortalidade comparada entre condições sem a ressalva de ajuste de risco.
- Qualquer afirmação de causalidade entre escassez de serviços e deslocamento.
