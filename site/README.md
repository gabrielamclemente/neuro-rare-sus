# Site — NeuroRare SUS

Data storytelling em [Observable Framework](https://observablehq.com/framework/):
páginas em Markdown com blocos de JavaScript, servidor de desenvolvimento com
recarregamento automático, e build estático.

## Rodar localmente

```bash
cd site
npm install          # so na primeira vez
npm run data         # copia os CSVs de ../powerBi/data para src/data
npm run dev          # http://localhost:3000
```

O `npm run data` precisa rodar sempre que o pipeline gerar CSVs novos
(`python src/exportForBI.py` na raiz do projeto).

## Publicar

```bash
npm run build        # gera dist/
```

O `dist/` e estatico: serve em GitHub Pages, Netlify, Vercel ou qualquer
hospedagem de arquivos.

## Estrutura

```
site/
├── observablehq.config.js   titulo, paginas do menu, tema
├── src/
│   ├── index.md             Panorama — as duas naturezas de AIH
│   ├── territorio.md        Territorio e deslocamento (em construcao)
│   ├── metodologia.md       aponta para docs/METHODOLOGY.md
│   └── data/                CSVs copiados pelo `npm run data` (nao versionados)
└── package.json
```

## Paleta

Definida em `src/index.md` e reutilizada nas demais paginas. As cores seguem a
mesma atribuicao do dashboard do Tableau, validada para daltonismo:

| Condicao | Hex |
|---|---|
| Esclerose Multipla | `#2a78d6` |
| Esclerose Lateral Amiotrofica | `#eb6834` |
| Miastenia Gravis | `#1baf7a` |
| Atrofia Muscular Espinhal | `#eda100` |
| Polineuropatia Amiloidotica Familiar | `#e87ba4` |
