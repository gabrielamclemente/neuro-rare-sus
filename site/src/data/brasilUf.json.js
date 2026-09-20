// Data loader: malha das UFs do Brasil, da API de malhas territoriais do IBGE.
//
// O Framework executa este arquivo uma vez e guarda a saida em cache
// (src/.observablehq/cache/data/brasilUf.json).
//
// Se a malha vier com menos de 27 feicoes, algo mudou na API e o mapa nao faz
// sentido — melhor falhar aqui, com mensagem clara, do que desenhar um
// retangulo azul na pagina.

const url =
  "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR" +
  "?intrarregiao=UF&formato=application/vnd.geo+json";

const res = await fetch(url);
if (!res.ok) {
  throw new Error(`IBGE respondeu ${res.status} ao buscar a malha das UFs.`);
}

const geo = await res.json();
const n = geo?.features?.length ?? 0;

if (n !== 27) {
  throw new Error(
    `Esperava 27 UFs na malha, recebi ${n}. ` +
    `Conferir o parametro intrarregiao na API de malhas do IBGE.`
  );
}

// Normaliza a chave: a API ja devolve properties.codarea, mas garantimos que
// seja string de 2 digitos, que e como cruzamos com a sigla da UF.
for (const f of geo.features) {
  f.properties = {...f.properties, codarea: String(f.properties.codarea).slice(0, 2)};
}

process.stdout.write(JSON.stringify(geo));