// Data loader: nomes dos municipios brasileiros, direto do IBGE.
//
// O SIH grava o municipio com 6 digitos (sem o digito verificador); o IBGE
// usa 7. A chave aqui sao os 6 primeiros digitos, que e como o cruzamento
// funciona na pratica.
//
// Saida: { "355030": "São Paulo, SP", ... }

const url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios";

const res = await fetch(url);
if (!res.ok) {
  throw new Error(`IBGE respondeu ${res.status} ao buscar os municipios.`);
}

const municipios = await res.json();

const mapa = {};
for (const m of municipios) {
  const uf = m.microrregiao?.mesorregiao?.UF?.sigla
          ?? m["regiao-imediata"]?.["regiao-intermediaria"]?.UF?.sigla
          ?? "";
  const chave = String(m.id).slice(0, 6);
  mapa[chave] = uf ? `${m.nome}, ${uf}` : m.nome;
}

if (Object.keys(mapa).length < 5000) {
  throw new Error(
    `Esperava ~5570 municipios, recebi ${Object.keys(mapa).length}. ` +
    `A estrutura da API do IBGE pode ter mudado.`
  );
}

process.stdout.write(JSON.stringify(mapa));
