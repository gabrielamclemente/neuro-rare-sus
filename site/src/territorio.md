---
title: Território e deslocamento
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
const condicoes = Object.keys(cores);

const concentracao = await FileAttachment("data/vwConcentration.csv").csv({typed: true});
const deslocamento = await FileAttachment("data/vwTravelSummary.csv").csv({typed: true});
const porUf = await FileAttachment("data/vwByUf.csv").csv({typed: true});
const nomesMunicipios = await FileAttachment("data/municipios.json").json();

const nomeMunicipio = c => nomesMunicipios[String(c).padStart(6, "0")] ?? `código ${c}`;

// sigla -> codigo IBGE de 2 digitos, e o caminho inverso para rotular o mapa.
const codigoUf = new Map(Object.entries({
  RO: "11", AC: "12", AM: "13", RR: "14", PA: "15", AP: "16", TO: "17",
  MA: "21", PI: "22", CE: "23", RN: "24", PB: "25", PE: "26", AL: "27",
  SE: "28", BA: "29", MG: "31", ES: "32", RJ: "33", SP: "35",
  PR: "41", SC: "42", RS: "43", MS: "50", MT: "51", GO: "52", DF: "53"
}));
const siglaPorCodigo = new Map(Array.from(codigoUf, ([s, c]) => [c, s]));
```

```js
revelar();
```

<div class="hero">
  <h1>Metade das AIHs acontecem fora do município de residência</h1>
  <p>Mas quase nenhuma cruza fronteira estadual. A rede de referência se organiza
  dentro dos estados, e a concentração acompanha o tipo de cuidado, não a
  raridade da condição.</p>
</div>

<div class="stat-row reveal">
  <div class="stat">
    <div class="stat-value">~50%</div>
    <div class="stat-label">das AIHs ocorrem fora do município de residência</div>
  </div>
  <div class="stat">
    <div class="stat-value">0,8%</div>
    <div class="stat-label">cruzam fronteira estadual</div>
  </div>
  <div class="stat">
    <div class="stat-value">43%</div>
    <div class="stat-label">do atendimento nacional de AME está em Recife</div>
  </div>
  <div class="stat">
    <div class="stat-value">8</div>
    <div class="stat-label">municípios atendem polineuropatia amiloidótica no país</div>
  </div>
</div>

## A hipótese que os dados refutaram

Uma amostra exploratória de quatro estados sugeria que a atrofia muscular
espinhal teria **17% das AIHs fora da UF de residência**, contra 0,3% da
esclerose múltipla. Parecia deslocamento interestadual expressivo nas condições
mais raras.

Com as 27 UFs e o ano completo, esse número **cai para 2,8%**. O viés era
previsível: com só quatro estados baixados, um residente de Goiás internado em
Goiás não aparecia na amostra, enquanto um residente de Goiás internado no
Distrito Federal aparecia.

<div class="note">

No Brasil inteiro, em 2024, foram **97 deslocamentos interestaduais em 11.590
AIHs**. Não sustentam um diagrama de fluxo. O achado foi mantido como resultado
negativo documentado, em vez de ajustado para preservar a narrativa.

</div>

## A escala correta é municipal

```js
const ordemDeslocamento = ["Mesmo município", "Outro município, mesma UF", "Outra UF"];
const rotulos = {
  "Mesmo municipio": "Mesmo município",
  "Outro municipio, mesma UF": "Outro município, mesma UF",
  "Outra UF": "Outra UF"
};
const desloc = deslocamento.map(d => ({...d, tipo: rotulos[d.travelType] ?? d.travelType}));
const ordemPorFora = Array.from(new Set(
  desloc.filter(d => d.travelType !== "Mesmo municipio")
        .sort((a, b) => b.pct - a.pct)
        .map(d => d.diseaseName)
));
```

```js
comAnimacao(Plot.plot({
  marginLeft: 230,
  marginRight: 20,
  height: 260,
  x: {label: "% das AIHs da condição →", domain: [0, 100], grid: true},
  y: {label: null, domain: ordemPorFora},
  color: {
    domain: ordemDeslocamento,
    range: ["#c9c8c0", "#2a78d6", "#eb6834"],
    legend: true
  },
  marks: [
    Plot.barX(desloc, {
      x: "pct",
      y: "diseaseName",
      fill: "tipo",
      order: ordemDeslocamento,
      insetTop: 2,
      insetBottom: 2,
      title: d => `${d.diseaseName}\n${d.tipo}: ${d.pct.toFixed(1)}% das AIHs`,
      tip: {format: {x: false, y: false, fill: false}}
    }),
    Plot.ruleX([0])
  ]
}), "reveal animate-bars")
```

A faixa laranja é quase invisível, e esse é o ponto. Atravessar fronteira
estadual é exceção administrativa, não o caminho usual do paciente.

## Onde a demanda se origina

Este mapa mostra a UF de **residência** de quem foi atendido, não onde o
atendimento aconteceu. Demanda é de onde a pessoa é.

```js
const condicaoMapa = view(Inputs.select(
  ["Todas as condições", ...condicoes],
  {label: "Condição", value: "Todas as condições"}
));
```

```js
const brasil = await FileAttachment("data/brasilUf.json").json();
```

```js
// Nada de reconstruir feicoes: a projecao usa o objeto do IBGE como veio, e a
// cor sai de uma consulta por codigo na hora de pintar. Menos peca, menos
// lugar para quebrar.
const porUfFiltrado = condicaoMapa === "Todas as condições"
  ? porUf
  : porUf.filter(d => d.diseaseName === condicaoMapa);

const aihsPorUf = new Map();
for (const d of porUfFiltrado) {
  const cod = codigoUf.get(d.uf);
  if (!cod) continue;
  aihsPorUf.set(cod, (aihsPorUf.get(cod) ?? 0) + d.admissions);
}

const valorDa = f => aihsPorUf.get(String(f.properties.codarea)) ?? 0;
const siglaDa = f => siglaPorCodigo.get(String(f.properties.codarea)) ?? "";
const maxAihsUf = Math.max(...brasil.features.map(valorDa), 1);
```

```js
comAnimacao(Plot.plot({
  width: 700,
  height: 620,
  projection: {type: "mercator", domain: brasil},
  color: {
    type: "quantize",
    n: 5,
    domain: [0, maxAihsUf],
    scheme: "blues",
    label: "AIHs registradas por UF de residência",
    legend: true,
    tickFormat: d => Math.round(d).toLocaleString("pt-BR")
  },
  marks: [
    Plot.geo(brasil.features, {
      fill: valorDa,
      stroke: "white",
      strokeWidth: 0.8,
      title: f => `${siglaDa(f)}\n${valorDa(f).toLocaleString("pt-BR")} AIHs`,
      tip: {format: {fill: false}}
    }),
    // A sigla no centro de cada estado: dispensa o leitor de saber geografia.
    Plot.text(brasil.features, Plot.centroid({
      text: siglaDa,
      fill: f => valorDa(f) > maxAihsUf * 0.6 ? "white" : "#333",
      fontSize: 10,
      fontWeight: 600,
      pointerEvents: "none"
    }))
  ]
}), "reveal")
```

<div class="mapa-legenda">

Escala linear em cinco faixas iguais, do branco ao azul. **Sem correção por
população**. São Paulo e Minas aparecem escuros em parte por serem os estados
mais populosos. A normalização por 100 mil habitantes depende da tabela do
IBGE, ainda pendente no pipeline, e sem ela o mapa mostra volume, não risco.

</div>

## Quanto do atendimento cabe nos primeiros municípios

Cada curva mostra o percentual acumulado conforme se somam os municípios, do
maior volume para o menor. Quanto mais rápido sobe, mais concentrado é o cuidado.

```js
const destaque = view(Inputs.select(
  ["Todas", ...condicoes],
  {label: "Destacar", value: "Todas"}
));
```

```js
const curva = concentracao.filter(d => d.rankInDisease <= 20);

// Duas camadas em vez de opacidade calculada: assim nenhuma propriedade
// derivada vaza para o tooltip.
const apagadas = destaque === "Todas" ? [] : curva.filter(d => d.diseaseName !== destaque);
const ativas   = destaque === "Todas" ? curva : curva.filter(d => d.diseaseName === destaque);
```

```js
comAnimacao(Plot.plot({
  height: 420,
  marginRight: 30,
  x: {label: "Municípios, do maior volume para o menor →", domain: [1, 20], grid: true},
  y: {label: "↑ % acumulado do atendimento", domain: [0, 100], grid: true},
  color: {domain: condicoes, range: condicoes.map(c => cores[c]), legend: true},
  marks: [
    Plot.line(apagadas, {
      x: "rankInDisease", y: "cumulativePct", stroke: "diseaseName",
      strokeWidth: 1, strokeOpacity: 0.15, curve: "monotone-x"
    }),
    Plot.line(ativas, {
      x: "rankInDisease", y: "cumulativePct", stroke: "diseaseName",
      strokeWidth: 2.5, curve: "monotone-x"
    }),
    Plot.dot(ativas, {
      x: "rankInDisease",
      y: "cumulativePct",
      fill: "diseaseName",
      r: 4,
      title: d => [
        d.diseaseName,
        `${d.rankInDisease}º município: ${nomeMunicipio(d.municipalityHospital)}`,
        `${d.admissions.toLocaleString("pt-BR")} AIHs aqui`,
        `${d.cumulativePct.toFixed(1)}% do total acumulado até este ponto`
      ].join("\n"),
      tip: {format: {x: false, y: false, fill: false}}
    }),
    Plot.ruleY([0])
  ]
}), "reveal animate-lines")
```

Os nomes saíram do fim das linhas de propósito: com cinco curvas convergindo à
direita, os rótulos se sobrepunham. A identificação fica na legenda, no seletor
de destaque e no tooltip de cada ponto.

<div class="note">

**A concentração acompanha o regime de cuidado, não a raridade.** Episódios de
tratamento ocorrem em centros de referência, que são poucos. Internações
clínicas prolongadas ocorrem na rede hospitalar geral, que é ampla.

</div>

## Os centros

```js
const condicaoTabela = view(Inputs.select(
  condicoes,
  {label: "Condição", value: "Atrofia Muscular Espinhal"}
));
```

```js
const topN = view(Inputs.range([5, 25], {label: "Municípios", step: 5, value: 10}));
```

```js
const linhas = concentracao
  .filter(d => d.diseaseName === condicaoTabela && d.rankInDisease <= topN)
  .sort((a, b) => a.rankInDisease - b.rankInDisease)
  .map(d => ({
    posicao: d.rankInDisease,
    municipio: nomeMunicipio(d.municipalityHospital),
    aihs: d.admissions,
    pct: d.pctOfDisease,
    acumulado: d.cumulativePct
  }));

const maxAihs = Math.max(...linhas.map(d => d.aihs), 1);
const corAtual = cores[condicaoTabela] ?? "#2a78d6";

function celulaBarra(valor) {
  const wrap = document.createElement("div");
  wrap.className = "cell-bar-wrap";
  const num = document.createElement("span");
  num.className = "cell-num";
  num.textContent = valor.toLocaleString("pt-BR");
  const barra = document.createElement("span");
  barra.className = "cell-bar";
  barra.style.width = `${Math.max(2, (valor / maxAihs) * 130)}px`;
  barra.style.background = corAtual;
  wrap.append(num, barra);
  return wrap;
}
```

<div class="tabela-limpa">

```js
Inputs.table(linhas, {
  columns: ["posicao", "municipio", "aihs", "pct", "acumulado"],
  header: {
    posicao: "#",
    municipio: "Município",
    aihs: "AIHs",
    pct: "% da condição",
    acumulado: "% acumulado"
  },
  format: {
    aihs: celulaBarra,
    pct: v => `${v.toFixed(2)}%`,
    acumulado: v => `${v.toFixed(1)}%`
  },
  align: {
    posicao: "right",
    municipio: "left",
    aihs: "left",
    pct: "right",
    acumulado: "right"
  },
  width: {posicao: 40, municipio: 230, aihs: 210},
  select: false,
  rows: 26,
  height: "auto"
})
```

</div>

## O cuidado está na rede habilitada?

```js
const rede = await FileAttachment("data/vwNetworkCoverage.csv").csv({typed: true});
```

A Rede de Atenção Especializada em Doenças Raras existe desde 2014 e é o
instrumento da política nacional. Se a concentração que vimos acima for
deliberada, os centros que concentram cada condição devem ser serviços
habilitados dessa rede.

Em junho de 2024 a rede tinha **34 estabelecimentos em 13 estados**. Cruzando
com os hospitais que de fato registram AIHs no escopo:

```js
const ordemRede = rede.slice()
  .sort((a, b) => b.pctInNetwork - a.pctInNetwork)
  .map(d => d.diseaseName);
```

```js
comAnimacao(Plot.plot({
  marginLeft: 230,
  marginRight: 60,
  height: 260,
  x: {label: "% das AIHs em serviço habilitado da rede →", domain: [0, 100], grid: true},
  y: {label: null, domain: ordemRede},
  marks: [
    Plot.barX(rede, {
      x: "pctInNetwork",
      y: "diseaseName",
      fill: d => cores[d.diseaseName] ?? "#888",
      rx: 2,
      title: d => [
        d.diseaseName,
        `${d.pctInNetwork}% das AIHs em serviço habilitado`,
        `${d.admissionsInNetwork.toLocaleString("pt-BR")} de ${d.admissions.toLocaleString("pt-BR")} AIHs`,
        `${d.establishmentsInNetwork} de ${d.establishments} estabelecimentos habilitados`
      ].join("\n"),
      tip: {format: {x: false, y: false, fill: false}}
    }),
    Plot.text(rede, {
      x: "pctInNetwork",
      y: "diseaseName",
      text: d => `${d.pctInNetwork.toFixed(1)}%`,
      textAnchor: "start",
      dx: 6,
      fill: "currentColor",
      fontVariant: "tabular-nums"
    }),
    Plot.ruleX([0])
  ]
}), "reveal animate-bars")
```

<div class="stat-row reveal">
  <div class="stat">
    <div class="stat-value">34</div>
    <div class="stat-label">estabelecimentos habilitados na rede, em 13 estados</div>
  </div>
  <div class="stat">
    <div class="stat-value">95%</div>
    <div class="stat-label">do atendimento de esclerose múltipla ocorre fora da rede</div>
  </div>
  <div class="stat">
    <div class="stat-value">0 de 5</div>
    <div class="stat-label">maiores centros de esclerose múltipla têm habilitação</div>
  </div>
  <div class="stat">
    <div class="stat-value">58%</div>
    <div class="stat-label">do atendimento de AME ocorre dentro da rede</div>
  </div>
</div>

A rede captura o cuidado hospitalar das condições **genéticas e ultrarraras**,
atrofia muscular espinhal e polineuropatia amiloidótica, e praticamente não
captura as demais. A esclerose múltipla, que responde por 72% do volume do
escopo, tem 95% do seu atendimento fora da rede habilitada, e nenhum dos seus
cinco maiores centros é habilitado.

É o mesmo corte entre condições que apareceu nos regimes de AIH, mas por um eixo
diferente: lá era a duração do episódio, aqui é a natureza da condição.

## O que isso não prova

Concentração não é, por si, um problema. Condições raras exigem volume para que
uma equipe desenvolva e mantenha expertise, e a política nacional de doenças
raras organiza a rede justamente assim.

<div class="note">

**Isto não é evidência de falha da rede.** A política organiza diagnóstico e
acompanhamento, boa parte deles ambulatoriais e fora do SIH. Um surto de
esclerose múltipla tratado com pulsoterapia no hospital geral mais próximo pode
ser exatamente o desenho pretendido. Além disso, a competência analisada é junho
de 2024, houve expansão da rede depois disso, e a habilitação é do
estabelecimento, não do atendimento específico.

</div>

O cruzamento com o CNES respondeu **onde** o cuidado acontece em relação à rede
formal. Não responde **por quê**, e não mede acesso: nada aqui informa quanto
tempo alguém esperou, quanto se deslocou ou se chegou a ser atendido. Explicar o
padrão exige o SIA/SUS, onde mora o cuidado ambulatorial dessas condições, e
isso está fora deste escopo.

Os dados levantam a pergunta com precisão. Respondê-la é trabalho de outra
natureza.