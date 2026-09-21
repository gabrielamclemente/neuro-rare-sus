---
title: Panorama
---

```js
import {revelar, comAnimacao} from "./reveal.js";

const cores = {
  "Esclerose Multipla": "#2a78d6",
  "Esclerose Lateral Amiotrofica": "#eb6834",
  "Miastenia Gravis": "#1baf7a",
  "Atrofia Muscular Espinhal": "#eda100",
  "Polineuropatia Amiloidotica Familiar": "#e87ba4"
};

const overview = await FileAttachment("data/vwOverview.csv").csv({typed: true});

// Ordens calculadas explicitamente: mais previsivel que o sort do Plot.
const ordemVolume = overview.slice()
  .sort((a, b) => b.admissions - a.admissions).map(d => d.diseaseName);
const ordemRegime = overview.slice()
  .sort((a, b) => b.shortStayPct - a.shortStayPct).map(d => d.diseaseName);

const totalAihs = overview.reduce((s, d) => s + d.admissions, 0);
const totalObitos = overview.reduce((s, d) => s + d.deaths, 0);
```

```js
revelar();
```

<div class="hero">
  <h1>Onde acontece o cuidado das doenças neurológicas raras no Brasil</h1>
  <p>Uma análise das autorizações de internação hospitalar (AIH) registradas no SUS em
  2024, em cinco condições raras, e do quanto as pessoas precisam se deslocar
  para alcançar esse cuidado.</p>
</div>

<div class="stat-row reveal">
  <div class="stat">
    <div class="stat-value">${totalAihs.toLocaleString("pt-BR")}</div>
    <div class="stat-label">AIHs registradas em 2024</div>
  </div>
  <div class="stat">
    <div class="stat-value">5</div>
    <div class="stat-label">condições neurológicas raras analisadas</div>
  </div>
  <div class="stat">
    <div class="stat-value">99,4%</div>
    <div class="stat-label">de cobertura: 322 de 324 UF-meses</div>
  </div>
  <div class="stat">
    <div class="stat-value">${totalObitos.toLocaleString("pt-BR")}</div>
    <div class="stat-label">óbitos hospitalares no período</div>
  </div>
</div>

<div class="note">

**O SIH/SUS registra produção hospitalar aprovada, não o número de pessoas internadas.** Cada número
aqui é uma AIH, uma autorização de internação, nunca um paciente único. A
mesma pessoa internada três vezes no ano gera três AIHs. AM e PI não têm
fevereiro.

</div>

## O volume não é a história

Cinco condições, volumes muito diferentes. A esclerose múltipla responde por
quase três quartos das AIHs; a polineuropatia amiloidótica familiar, por 29
registros no país inteiro em um ano.

```js
comAnimacao(Plot.plot({
  marginLeft: 230,
  marginRight: 60,
  height: 230,
  x: {label: "AIHs registradas →", grid: true, nice: true},
  y: {label: null, domain: ordemVolume},
  marks: [
    Plot.barX(overview, {
      x: "admissions",
      y: "diseaseName",
      fill: d => cores[d.diseaseName] ?? "#888",
      rx: 2,
      tip: true,
      channels: {
        Condição: "diseaseName",
        AIHs: "admissions",
        "Permanência média": "avgLengthOfStay"
      }
    }),
    Plot.text(overview, {
      x: "admissions",
      y: "diseaseName",
      text: d => d.admissions.toLocaleString("pt-BR"),
      textAnchor: "start",
      dx: 6,
      fill: "currentColor",
      fontVariant: "tabular-nums"
    }),
    Plot.ruleX([0])
  ]
}), "reveal animate-bars")
```

Uma leitura apressada pararia aqui e concluiria que a esclerose múltipla é o
problema principal. O próximo gráfico mostra por que essa leitura estaria
errada.

## Duas naturezas de AIH dentro do mesmo escopo

Nem toda AIH é uma internação no sentido clínico. Algumas duram um dia, e são
episódios de tratamento, como a pulsoterapia para surto de esclerose múltipla.
Outras duram semanas.

```js
const regime = overview.flatMap(d => [
  {diseaseName: d.diseaseName, tipo: "Até 1 dia", pct: d.shortStayPct},
  {diseaseName: d.diseaseName, tipo: "Mais de 1 dia", pct: d.longStayPct}
]);
```

```js
comAnimacao(Plot.plot({
  marginLeft: 230,
  marginRight: 20,
  height: 250,
  x: {label: "% das AIHs da condição →", domain: [0, 100], grid: true},
  y: {label: null, domain: ordemRegime},
  color: {
    domain: ["Até 1 dia", "Mais de 1 dia"],
    range: ["#2a78d6", "#c9c8c0"],
    legend: true
  },
  marks: [
    Plot.barX(regime, {
      x: "pct",
      y: "diseaseName",
      fill: "tipo",
      order: ["Até 1 dia", "Mais de 1 dia"],
      insetTop: 2,
      insetBottom: 2,
      tip: true,
      channels: {Condição: "diseaseName", Regime: "tipo", "%": "pct"}
    }),
    Plot.ruleX([0])
  ]
}), "reveal animate-bars")
```

O corte não acompanha a raridade da condição, acompanha o **tipo de cuidado**.
Polineuropatia, esclerose múltipla e atrofia muscular espinhal são dominadas por
episódios de dia único. Miastenia gravis e esclerose lateral amiotrófica são
internações clínicas, de nove a vinte e um dias, com mortalidade hospitalar
relevante.

<div class="note">

Um total agregando as cinco condições como "internações" somaria coisas
incomparáveis. É por isso que este projeto nunca apresenta esse número.

</div>

## O perfil de cada condição

```js
const perfil = overview.slice().sort((a, b) => b.admissions - a.admissions);
```

<div class="tabela-limpa">

```js
Inputs.table(perfil, {
  columns: ["diseaseName", "careRegime", "admissions", "shortStayPct",
            "avgLengthOfStay", "inHospitalMortalityPct", "municipalitiesTreating"],
  header: {
    diseaseName: "Condição",
    careRegime: "Regime",
    admissions: "AIHs",
    shortStayPct: "% até 1 dia",
    avgLengthOfStay: "Permanência (dias)",
    inHospitalMortalityPct: "Mortalidade (%)",
    municipalitiesTreating: "Municípios"
  },
  format: {
    careRegime: r => r.startsWith("Tratamento") ? "Tratamento" : "Internação",
    admissions: v => v.toLocaleString("pt-BR"),
    shortStayPct: v => `${v.toFixed(1)}%`,
    avgLengthOfStay: v => v.toFixed(1),
    inHospitalMortalityPct: v => `${v.toFixed(2)}%`
  },
  align: {
    diseaseName: "left",
    careRegime: "left",
    admissions: "right",
    shortStayPct: "right",
    avgLengthOfStay: "right",
    inHospitalMortalityPct: "right",
    municipalitiesTreating: "right"
  },
  width: {diseaseName: 260, careRegime: 110},
  select: false,
  rows: 6,
  height: "auto"
})
```

</div>

<div class="note">

**Mortalidade hospitalar bruta não é indicador de qualidade assistencial.** Não
há ajuste por gravidade, e centros de referência tendem a receber os casos mais
graves. A comparação entre condições só faz sentido dentro do mesmo regime de
cuidado.

</div>

A próxima página mostra onde esse cuidado acontece no território, e é lá que
está o achado central do projeto.