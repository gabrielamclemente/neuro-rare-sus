// Revelacao ao rolar.
//
// Cada elemento se registra sozinho, porque no Observable Framework os
// graficos sao criados depois que a pagina carrega — uma varredura unica no
// inicio nao os alcanca, e eles ficariam invisiveis para sempre.

let observador;

function obterObservador() {
  if (observador) return observador;
  observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) {
      if (e.isIntersecting) {
        e.target.classList.add("is-visible");
        observador.unobserve(e.target);   // anima uma vez so
      }
    }
  }, {rootMargin: "0px 0px -8% 0px", threshold: 0.02});
  return observador;
}

function movimentoReduzido() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/** Registra um elemento para aparecer quando entrar na tela. */
export function observar(el) {
  if (!el) return el;

  // Sem suporte ou com movimento reduzido: mostra na hora.
  if (movimentoReduzido() || !("IntersectionObserver" in window)) {
    el.classList.add("is-visible");
    return el;
  }

  obterObservador().observe(el);

  // Rede de seguranca: se por qualquer motivo o observador nao disparar
  // (elemento fora de fluxo, navegador antigo, bug meu), o conteudo aparece
  // mesmo assim. Um grafico invisivel e pior que um grafico sem animacao.
  setTimeout(() => el.classList.add("is-visible"), 1500);

  return el;
}

/** Varre os elementos estaticos da pagina (blocos de HTML no Markdown). */
export function revelar(seletor = ".reveal") {
  document.querySelectorAll(seletor).forEach(observar);
}

/**
 * Envolve um no — tipicamente o SVG que o Plot devolve — num container com as
 * classes de animacao, e ja o registra.
 */
export function comAnimacao(no, classes = "reveal animate-bars") {
  const div = document.createElement("div");
  div.className = classes;
  div.appendChild(no);
  return observar(div);
}