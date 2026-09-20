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

## 6. Geografia: residência e local de internação

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

### Achado: o deslocamento depende da condição

Na amostra exploratória (SP, MG, BA, DF · 1º trimestre de 2024):

| Condição | AIHs | fora da UF de residência |
|---|---:|---:|
| Atrofia Muscular Espinhal | 35 | **17,1%** |
| Esclerose Múltipla | 1.065 | 0,3% |
| Agregado | 1.300 | 0,7% |

O agregado de 0,7% é artefato de composição: a esclerose múltipla, com volume
muito maior e deslocamento mínimo, dilui o sinal.

**Por isso o fluxo interestadual é analisado por condição, nunca no agregado.**
Uma leitura agregada teria concluído que não há deslocamento relevante — o
oposto do que os dados mostram para as condições mais raras.

Esses percentuais vêm da amostra de 4 UFs e estão **superestimados**: um
residente de GO internado em GO não aparecia nela, enquanto um residente de GO
internado no DF aparecia. Os números definitivos serão recalculados sobre as 27
UFs.

---

## 7. O que o projeto não afirma

- **Não mede prevalência nem incidência.** Mede utilização hospitalar registrada.
- **Não mede acesso.** O indicador `admissionsPerService` é exploratório: nem
  toda internação exige centro especializado, e um serviço habilitado atende
  residentes de várias UFs.
- **Não estabelece causalidade** entre escassez de serviços e deslocamento de
  pacientes. Identifica padrões territoriais compatíveis com essa hipótese.
- **Não cobre atendimento ambulatorial.** Boa parte do cuidado dessas condições
  ocorre fora da internação e está no SIA/SUS, fora deste escopo.

---

## 8. Reprodutibilidade

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
