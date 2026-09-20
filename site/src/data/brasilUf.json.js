// Data loader: malha das UFs do Brasil, da API de malhas territoriais do IBGE.
//
// ---------------------------------------------------------------------------
// ORIENTACAO DOS ANEIS — a causa do mapa quebrado
//
// O d3-geo, que o Observable Plot usa por baixo, trabalha em geometria
// ESFERICA. Nela um poligono nao tem "dentro" definido pela forma: o dentro
// vem do sentido em que os vertices sao percorridos. Se o sentido estiver
// invertido, o d3-geo entende "todo o globo EXCETO esta area" e pinta o
// complemento — o mapa vira um retangulo preenchido com o Brasil recortado.
//
// Qual sentido? Verificado empiricamente, renderizando a malha com o Plot fora
// do navegador e contando os subcaminhos do SVG gerado:
//
//   anel externo anti-horario (area > 0) -> 2 subcaminhos: o estado + o quadro
//   anel externo horario     (area < 0) -> 1 subcaminho: so o estado   [correto]
//
// Ou seja: neste par de eixos (longitude em x, latitude em y), o d3-geo quer o
// anel externo HORARIO. Isso contraria a leitura ingenua da RFC 7946, e foi a
// origem de varias tentativas frustradas antes deste teste.
// ---------------------------------------------------------------------------

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

/** Area com sinal (formula do cadarco). Positiva = anti-horario. */
function areaAnel(anel) {
  let a = 0;
  for (let i = 0, m = anel.length, j = m - 1; i < m; j = i++) {
    a += anel[j][0] * anel[i][1] - anel[i][0] * anel[j][1];
  }
  return a / 2;
}

/** Anel externo horario (area negativa); buracos anti-horarios. */
function corrigirPoligono(poligono) {
  poligono.forEach((anel, i) => {
    const querNegativa = i === 0;
    if ((areaAnel(anel) > 0) === querNegativa) anel.reverse();
  });
  return poligono;
}

let reordenados = 0;

for (const f of geo.features) {
  f.properties = {...f.properties, codarea: String(f.properties.codarea).slice(0, 2)};

  const g = f.geometry;
  if (g.type === "Polygon") {
    if (areaAnel(g.coordinates[0]) > 0) reordenados++;
    corrigirPoligono(g.coordinates);
  } else if (g.type === "MultiPolygon") {
    let algum = false;
    for (const poly of g.coordinates) {
      if (areaAnel(poly[0]) > 0) algum = true;
      corrigirPoligono(poly);
    }
    if (algum) reordenados++;
  }
}

// Vai para o log do servidor de desenvolvimento, nao para o JSON.
process.stderr.write(
  `malha do IBGE: ${n} UFs, ${reordenados} com aneis reordenados para horario\n`
);

process.stdout.write(JSON.stringify(geo));