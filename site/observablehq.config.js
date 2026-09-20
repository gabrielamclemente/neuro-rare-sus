// O site e publicado em gabrielamclemente.github.io/neuro-rare-sus/, ou seja,
// dentro de um subcaminho. Sem "base" o Framework gera links absolutos (/style.css)
// que apontariam para a raiz do dominio e dariam 404 em producao — embora
// funcionassem no preview local, onde a raiz e o proprio site.
export default {
  root: "src",
  base: "/neuro-rare-sus/",
  title: "NeuroRare SUS",
  pages: [
    {name: "Panorama", path: "/"},
    {name: "Território e deslocamento", path: "/territorio"},
    {name: "Metodologia", path: "/metodologia"}
  ],
  style: "style.css",
  header: "",
  footer: `Dados: SIH/SUS 2024 (DATASUS) · malha territorial: IBGE · <a href="https://github.com/gabrielamclemente/neuro-rare-sus">código no GitHub</a>`,
  toc: true,
  search: false
};