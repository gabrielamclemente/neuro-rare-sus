# Metodologia — NeuroRare SUS

Este documento registra de onde vêm os dados, o que foi feito com eles, quais
decisões foram tomadas e o que o projeto **não** pode afirmar. Ele existe para
que qualquer pessoa possa auditar ou reproduzir o trabalho.

Última atualização: 2026-09-20 · Período analisado: 2024 · Escopo geográfico: 27 UFs

---

## 1. A limitação que define o projeto

O SIH/SUS registra **produção hospitalar aprovada** — Autorizações de Internação
Hospitalar (AIH) —, não pessoas. Não há identificador de paciente utilizável, e
a mesma pessoa internada três vezes no ano gera três AIHs.

Em consequência, **nenhum número aqui é contagem de pacientes.** Todas as
métricas são "internações registradas relacionadas à condição no período". O
modelo de dados reflete isso deliberadamente: não existe coluna `patients` em
lugar nenhum do schema.

Essa não é uma limitação contornável com técnica melhor. É uma propriedade do
sistema de informação, e o próprio Ministério da Saúde alerta que os sistemas
atuais não registram o número de pessoas únicas acompanhadas por condição.

---

## 2. Fontes

| Base | Papel | Acesso | Situação |
|---|---|---|---|
| SIH/SUS — arquivos RD (AIH Reduzida) | demanda hospitalar | `pysus` 2.11.2 | completo |
| CNES — habilitações em doenças raras | oferta especializada | a definir | pendente |
| IBGE — população por UF | denominador | a definir | pendente |

### Por que o grupo RD

O SIH publica quatro grupos de arquivo por UF-mês: `RD` (AIH reduzida), `SP`
(serviços profissionais), `ER` (rejeitadas) e `RJ`. Usamos exclusivamente o
`RD`, que tem **uma linha por internação** e carrega diagnóstico, município de
residência, município de internação, permanência, óbito, valor e CNES.

O `SP` tem uma linha por procedimento faturado, o que multiplicaria a mesma
internação em várias linhas e inflaria qualquer contagem direta. Ele volta a ser
relevante se o projeto avançar para análise de procedimentos específicos.

---

## 3. Extração

`src/loadData.py` baixa cada UF-mês e salva um parquet em `data/raw/`, com
cache: arquivo já baixado não é rebaixado.

### Problema encontrado: o filtro `group="RD"` falha em parte das partições

Na primeira execução completa de 2024, **74 dos 324 UF-meses (22,8%) voltaram
com zero linhas**. As falhas estavam espalhadas por todas as 27 UFs, sem
concentração em nenhum mês ou região.

A investigação passou por duas hipóteses erradas antes da correta:

1. **Limite de taxa** — descartada: três tentativas com espera crescente
   devolveram exatamente o mesmo resultado. Falha determinística, não transitória.
2. **Partição inexistente** — descartada: o arquivo `RD<UF><AA><MM>.parquet`
   existe e baixa normalmente.
3. **Causa real** — para essas partições o catálogo do PySUS não traz a marcação
   de grupo. Filtrar por `group="RD"` devolve zero linhas apesar de o arquivo
   estar lá e ser baixado.

**Solução adotada.** Quando o filtro por grupo devolve vazio, o código pede a
lista de *caminhos* de arquivo (`as_dataframe=False`), seleciona o que começa
com `RD<UF><AA><MM>` e o lê diretamente. A alternativa ingênua — omitir o
`group` — devolve `ER`+`RJ`+`RD`+`SP` empilhados num único DataFrame, com
esquemas diferentes, e é inutilizável.

Essa correção recuperou 71 dos 74 arquivos.

### Cobertura final

| | |
|---|---|
| UF-meses obtidos | **322 de 324 (99,4%)** |
| UFs com 12 meses completos | 25 de 27 |
| Ausentes | AM fevereiro/2024, PI fevereiro/2024 |

Os dois ausentes resistiram a todas as estratégias de recuperação. Como ambos
são o mesmo mês em estados diferentes, e os outros 71 foram recuperados pelo
mesmo caminho, a leitura mais provável é lacuna na publicação da fonte.

**Tratamento.** A tabela `dataCoverage` registra, por UF, quantos meses estão
disponíveis, quais faltam e a razão de cobertura. AM e PI aparecem com
`monthsAvailable = 11` e `coverageRatio = 0.9167`. Comparações entre UFs devem
normalizar por meses disponíveis; o dashboard declara a cobertura em vez de
apresentar o ano como completo.

---

## 4. Classificação das condições

Cinco condições neurológicas raras da lista oficial do Ministério da Saúde:

| Condição | CID-10 | Código no SIH |
|---|---|---|
| Esclerose Múltipla | G35 | `G35` |
| Esclerose Lateral Amiotrófica | G12.2 | `G122` |
| Miastenia Gravis | G70.0 | `G700` |
| Atrofia Muscular Espinhal | G12.0 | `G120` |
| Polineuropatia Amiloidótica Familiar | E85.1 | `E851` |

O SIH grava CID sem ponto em `DIAG_PRINC`. O match é por prefixo, normalizado
para maiúsculas e com pontos removidos, então `G12.0`, `g120` e `G120 ` caem
todos em `G120`.

### Decisão: apenas diagnóstico principal

A classificação usa **somente `DIAG_PRINC`**, não `DIAG_SECUN`.

Justificativa: com o diagnóstico principal, cada AIH conta uma única vez e a
internação foi de fato motivada pela condição. Incluir o secundário misturaria
"internada por causa da doença" com "internada tendo a doença" — uma pessoa com
esclerose múltipla internada por fratura entraria na contagem de demanda por
atenção à esclerose múltipla.

O secundário permanece disponível como análise de sensibilidade
(`classify(df, use_secondary=True)`), não como número principal.

---

## 5. Distribuição observada — 2024

11.590 AIHs no escopo, em 322 UF-meses.

| Condição | AIHs | % do escopo |
|---|---:|---:|
| Esclerose Múltipla | 8.396 | 72,4% |
| Esclerose Lateral Amiotrófica | 1.309 | 11,3% |
| Miastenia Gravis | 1.136 | 9,8% |
| Atrofia Muscular Espinhal | 720 | 6,2% |
| Polineuropatia Amiloidótica Familiar | 29 | 0,3% |

### Consequências para a análise

**A esclerose múltipla domina o volume.** Com 72% do escopo, ela achata qualquer
gráfico agregado e abafa as demais. É também a menos rara do grupo. Decisão:
mantida no escopo, com tratamento visual separado (eixo próprio ou recorte
dedicado), nunca somada às outras num único total apresentado como "doenças
raras".

**A PAF é ultrarrara mesmo em dados nacionais.** 29 AIHs no Brasil inteiro em um
ano não sustenta análise territorial — qualquer razão por UF seria construída
sobre uma ou duas internações. Decisão: mantida nas contagens, **excluída** dos
indicadores territoriais e do fluxo interestadual, e usada como ilustração do
limite do SIH para condições ultrarraras.

---

## 6. A natureza das AIHs: dois regimes distintos

Uma AIH de esclerose múltipla e uma AIH de ELA **não são a mesma coisa**, e
somá-las num total de "internações por doenças neurológicas raras" mistura
eventos clínicos incomparáveis.

### Permanência hospitalar por condição

| Condição | AIHs | permanência média | mediana | % com ≤1 dia |
|---|---:|---:|---:|---:|
| Polineuropatia Amiloidótica Familiar | 29 | 1,2 d | 0 | 86,2% |
| Esclerose Múltipla | 8.396 | 2,3 d | 0 | 73,4% |
| Atrofia Muscular Espinhal | 720 | 9,5 d | 0 | 68,9% |
| Miastenia Gravis | 1.136 | 7,9 d | 5 | 15,8% |
| Esclerose Lateral Amiotrófica | 1.309 | 15,1 d | 9 | 9,4% |

### Procedimentos predominantes

**Esclerose Múltipla** — um único procedimento responde por 88% das AIHs:

| Código | Procedimento | AIHs | % |
|---|---|---:|---:|
| `03.03.04.028-9` | Tratamento de surto de esclerose múltipla | 7.362 | 87,7% |

Trata-se do **evento agudo** da doença, tipicamente pulsoterapia, resolvido em
um ou dois dias. É demanda clínica legítima — um surto é um episódio real —,
mas não é internação prolongada.

**Atrofia Muscular Espinhal** — dividida entre dois perfis:

| Código | Procedimento | AIHs | permanência | valor médio |
|---|---|---:|---:|---:|
| `03.03.03.004-6` | Tratamento de distúrbios metabólicos | 292 | 0,0 d | R$ 139 |
| `03.03.04.020-3` | — | 254 | 19,8 d | R$ 6.464 |
| `03.03.04.019-0` | — | 90 | 18,5 d | R$ 8.280 |

**Polineuropatia Amiloidótica Familiar** — 28 das 29 AIHs usam o mesmo
`03.03.03.004-6`, com permanência 1,2 dia e valor médio de R$ 393.

**ELA e Miastenia Gravis** — dominadas por códigos de internação com
permanência de 9 a 21 dias. São hospitalizações no sentido clínico.

### Consequências para a análise

1. **Nenhum total agregando as cinco condições é apresentado como
   "internações".** O termo usado é "AIHs registradas", e os gráficos
   estratificam por condição.

2. **`approvedValue` não é custo do cuidado.** Para AME e PAF, as AIHs de
   valor baixo (R$ 139, R$ 393) e dia único sugerem que a medicação de alto
   custo é financiada fora da AIH. A métrica é rotulada como "valor aprovado
   em AIH", nunca como custo do tratamento.

3. **Permanência média e mortalidade só se comparam dentro do mesmo regime.**
   Comparar os 15,1 dias da ELA com os 2,3 da EM não diz nada sobre gravidade
   — diz que são tipos de episódio diferentes.

4. **O deslocamento interestadual da AME precisa ser reinterpretado.** Se parte
   das AIHs são episódios de dia único, o deslocamento pode medir viagem para
   receber tratamento, não para ser internado. Isso não enfraquece o achado:
   acesso a terapia especializada é precisamente o que a Rede de Doenças Raras
   existe para organizar. Mas muda o que o indicador significa, e a página de
   fluxo declara isso.

### Em aberto

A hipótese de que a medicação de alto custo da AME é financiada fora da AIH
**não foi verificada** — exige checar as regras de financiamento no PCDT da
condição, não os dados do SIH. Até lá, permanece como interpretação provável,
não como fato estabelecido.

Os nomes dos procedimentos `03.03.04.020-3` e `03.03.04.019-0` também seguem
por confirmar na tabela SIGTAP.

---

## 7. Geografia: residência e local de internação

`ufResidence` e `ufHospital` são derivadas do prefixo de dois dígitos dos
códigos IBGE em `MUNIC_RES` e `MUNIC_MOV`.

### Validação de que `MUNIC_MOV` mede o local de internação

Havia uma dúvida legítima: `MUNIC_MOV` poderia registrar o gestor da AIH, não o
hospital. Dois testes resolveram:

- **106 municípios distintos em `MUNIC_MOV`** na amostra de 4 UFs. Se fosse
  gestor estadual, seriam 4.
- **Residentes de GO, CE e SC aparecem internados em DF, SP e BA.** Se a coluna
  medisse o gestor do arquivo de origem, isso seria impossível.

A concordância de 100% entre `MUNIC_MOV`, `UF_ZI` e a UF do arquivo é esperada
por construção — o arquivo RD de SP contém as AIHs geridas em SP — e não indica
defeito.

### Hipótese inicial e sua refutação parcial

Uma amostra exploratória de 4 UFs (SP, MG, BA, DF · 1º trimestre de 2024)
sugeriu que a AME teria **17,1%** de AIHs fora da UF de residência, contra 0,3%
da esclerose múltipla — indicando deslocamento interestadual expressivo nas
condições mais raras.

**Com as 27 UFs e o ano completo, esse número cai para 2,8%.**

| Condição | AIHs | fora da UF de residência |
|---|---:|---:|
| Polineuropatia Amiloidótica Familiar | 29 | 17,2% (5 eventos — ruído) |
| Atrofia Muscular Espinhal | 720 | 2,8% |
| Miastenia Gravis | 1.136 | 1,3% |
| Esclerose Lateral Amiotrófica | 1.309 | 0,7% |
| Esclerose Múltipla | 8.396 | 0,6% |
| **Agregado** | **11.590** | **0,8%** |

A superestimativa da amostra era previsível e estava anotada: com apenas 4 UFs
baixadas, um residente de GO internado em GO não aparecia, enquanto um
residente de GO internado no DF aparecia. O viés inflava o percentual por um
fator de aproximadamente seis.

Os 17,2% da PAF são ruído — cinco deslocamentos em 29 AIHs.

**O que sobrevive é a ordenação, não a magnitude.** AME > Miastenia > ELA > EM
é consistente com "condição mais rara, oferta mais concentrada, mais
deslocamento". Mas 97 deslocamentos interestaduais em todo o país e em todo o
ano não sustentam um diagrama de fluxo.

### A escala correta é municipal

O recorte por UF torna invisível, por construção, o deslocamento que de fato
ocorre: do interior para os centros de referência dentro do próprio estado.

| Condição | AIHs | em outro município | municípios de origem | municípios que atendem | razão |
|---|---:|---:|---:|---:|---:|
| Atrofia Muscular Espinhal | 720 | **49,7%** | 157 | 58 | 2,7× |
| Esclerose Múltipla | 8.396 | 48,5% | 960 | 380 | 2,5× |
| Miastenia Gravis | 1.136 | 46,1% | 451 | 261 | 1,7× |
| Polineuropatia Amiloidótica Familiar | 29 | 44,8% | 10 | 8 | — |
| Esclerose Lateral Amiotrófica | 1.309 | 42,7% | 504 | 262 | 1,9× |

Cerca de metade das AIHs envolvem atendimento fora do município de residência,
e a razão entre municípios de origem e municípios que atendem é maior
justamente na AME — a condição mais rara com volume analisável.

**Decisão.** A análise de fluxo é feita no nível municipal. O recorte
interestadual permanece no projeto como resultado negativo documentado: a
travessia de fronteira estadual é exceção administrativa, não o caminho usual
do paciente, e a rede de referência se organiza dentro dos estados.

Esta seção registra uma hipótese que a ampliação dos dados refutou em
magnitude. O achado não foi ajustado para preservar a narrativa original.

---

## 8. O que o projeto não afirma

- **Não mede prevalência nem incidência.** Mede utilização hospitalar registrada.
- **Não mede acesso.** O indicador `admissionsPerService` é exploratório: nem
  toda internação exige centro especializado, e um serviço habilitado atende
  residentes de várias UFs.
- **Não estabelece causalidade** entre escassez de serviços e deslocamento de
  pacientes. Identifica padrões territoriais compatíveis com essa hipótese.
- **Não cobre atendimento ambulatorial.** Boa parte do cuidado dessas condições
  ocorre fora da internação e está no SIA/SUS, fora deste escopo.

---

## 9. Reprodutibilidade

`data/raw/` e `data/processed/` não são versionados: são alguns GB de dado
público reconstruível. O repositório versiona a receita.

```bash
pip install -r requirements.txt
python src/validateData.py                        # Fase 0 — viabilidade
python src/loadData.py --all-ufs --all-months --year 2024
python src/loadData.py --retry-missing --year 2024
python src/cleanData.py --year 2024               # agrega e carrega no SQLite
```

Ambiente de referência: Python 3.13, `pysus` 2.11.2, macOS.

**Ressalva de reprodutibilidade.** O comportamento do filtro `group="RD"`
depende do catálogo do PySUS, que é mantido por terceiros e pode mudar. Uma
execução futura pode não precisar do caminho alternativo descrito na seção 3 —
ou precisar dele em outras partições. O log de cada execução registra quais
arquivos vieram por qual caminho.