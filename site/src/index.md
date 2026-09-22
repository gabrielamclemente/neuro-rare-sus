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
  para receber tratamento.</p>
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

**O índice SIH/SUS registra produção hospitalar aprovada e não o número de pessoas internadas.** Cada número
Cada AIH corresponde a uma única autorização de internação, nunca um paciente único. Isso significa que se a mesma pessoa for internada três vezes no ano serão geradas três AIHs. O banco de dados não inclui dados do mês de fevereiro para os estados Amazonas e Piauí.

</div>

## Distribuição de AIHs Entre as 5 Condições Estudadas

As cinco condições neurolôgicas estudadas apresdentam volumes de AIHs registradas muito diferentes. Por exemplo, a esclerose múltipla responde por quase três quartos das AIHs de todo o Brasil. Já a polineuropatia amiloidótica familiar, por 29
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

Uma leitura apressada concluiria que a esclerose múltipla é o
problema principal. O próximo gráfico mostra por que essa leitura estaria
errada.

## Duas naturezas de AIH no mesmo escopo

Nem toda AIH é uma internação no sentido clínico. Algumas duram um dia e são
episódios de tratamento, como a pulsoterapia para surto de esclerose múltipla,
outras duram semanas.

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

A distribuição não acompanha a raridade da condição, mas sim o **tipo de cuidado**.
Polineuropatia, esclerose múltipla e atrofia muscular espinhal registram na maior parte dos casos episódios de dia único. Por outro lado, Miastenia gravis e esclerose lateral amiotrófica resultam em internação clínica, de nove a vinte e um dias, e apresntam um índice de mortalidade hospitalar significativo.

<div class="note">

A soma dos cinco tipos de internação resultaria em dados incomparáveis, e por isso que este projeto não apresenta esse dado. 

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
há padronização dos cuidados de acordo com a gravidade, até porque os centros de referência tendem a receber os casos mais graves. A comparação entre condições só faz sentido em um mesmo regime de cuidado.

</div>

Veja na próxima página a distribuição dos cuidados entre os diferentes estados do país.