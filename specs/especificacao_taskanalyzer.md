# Especificação SDD — TaskAnalyzer

**João Pedro Pinheiro Ghesti**

*Bootcamp III — Desafio Cumulativo: Entrega Inicial (Fase 1) — Spec-Driven Development & AI Harness*

> Transposição fiel do documento "Especificação SDD TaskAnalyzer" (Fase 1, v2.0).
> Este arquivo é a **única fonte da verdade** para a geração do código.
> A Seção 3 (Governança de Contexto) está publicada em [`CONTEXT_RULES.md`](../CONTEXT_RULES.md).

---

## 1. Visão Geral e Contrato de Negócio (SDD)

### 1.1 Identificação

| Campo | Valor |
|---|---|
| **Nome completo** | João Pedro Pinheiro Ghesti |
| **Curso** | Ciência de Dados e Machine Learning |
| **Polo / Turma** | Asa Norte |
| **E-mail institucional** | jppghesti@sempreceub.com |
| **Data de elaboração** | 11/09/2026 |
| **Versão da especificação** | v2.0 |

### 1.2 Propósito do Módulo TaskAnalyzer

O enunciado do Bootcamp III define o TaskAnalyzer, no mínimo, como um módulo que calcula o tempo médio de conclusão das tarefas, a taxa de atraso e indicadores segmentados por prioridade. A partir desse requisito genérico, optei por ir além do mínimo pedido, aproveitando minha formação em Ciência de Dados para tratar o problema com uma lente estatística: em vez de apenas médias e contagens, o módulo também caracteriza a variabilidade dos tempos de execução, identifica tarefas com comportamento atípico (outliers) e mede o quão precisas foram as estimativas de esforço feitas no planejamento. Especificamente, o TaskAnalyzer deverá:

- Calcular o tempo médio e o tempo mediano de execução das tarefas concluídas (a mediana reduz a sensibilidade a valores extremos, algo relevante quando poucas tarefas muito longas distorceriam a média);
- Calcular o desvio padrão do tempo de execução, como medida da variabilidade do lote;
- Calcular a taxa de atraso em relação à data de vencimento acordada;
- Gerar indicadores segmentados por nível de peso (prioridade) e, quando disponível, por equipe responsável;
- Identificar tarefas atípicas (outliers), cujo tempo de execução foge significativamente do padrão do restante do lote;
- Medir a acurácia das estimativas de esforço informadas no planejamento, comparando-as ao tempo real de execução;
- Fornecer métricas confiáveis mesmo em lotes vazios, sem tarefas concluídas ou sem estimativas informadas.

Este módulo será construído por um agente de IA a partir desta especificação (Fase 2). Por isso, o contrato definido a seguir deve ser preciso, completo e livre de ambiguidades — ele é a única fonte da verdade para a geração do código.

### 1.3 Contrato Executável de Interface

*A entidade de entrada é chamada `RegistroTarefa` e representa uma tarefa individual dentro do lote analisado.*

#### 1.3.1 Entradas (Inputs)

| Campo | Tipo | Obrigatório | Descrição / Restrições |
|---|---|---|---|
| `codigo` | str | Sim | Identificador alfanumérico único, no padrão `"TSK-####"` (ex.: TSK-0007). |
| `abertura` | datetime | Sim | Data/hora de abertura do registro, em ISO 8601 (UTC). |
| `execucao_iniciada` | datetime | Não | Data/hora de início da execução. |
| `execucao_finalizada` | datetime | Não | Data/hora de finalização da execução. |
| `vencimento` | datetime | Sim | Data/hora limite acordada para a conclusão. |
| `peso` | int | Sim | Escala de 1 (baixo) a 3 (crítico) indicando a importância da tarefa. |
| `estado` | str (enum) | Sim | Valores aceitos: `"aberta"`, `"em_andamento"`, `"concluida"`, `"cancelada"`. |
| `equipe` | str | Não | Nome da equipe ou responsável, usado para indicadores segmentados. |
| `esforco_estimado_min` | int | Não | Estimativa de esforço em minutos, feita no planejamento da tarefa. |

#### 1.3.2 Saídas (Outputs)

| Campo | Tipo | Descrição |
|---|---|---|
| `tempo_medio_execucao_min` | float | Tempo médio de execução, em minutos, das tarefas concluídas. |
| `tempo_mediano_execucao_min` | float | Tempo mediano de execução, em minutos (robusto a valores extremos). |
| `desvio_padrao_execucao_min` | float | Desvio padrão do tempo de execução, como medida de variabilidade. |
| `taxa_atraso` | float | Percentual de tarefas concluídas após o vencimento. |
| `tarefas_atipicas` | int | Quantidade de tarefas cujo tempo de execução ultrapassa média + 2×desvio padrão do lote. |
| `indice_acuracia_estimativa` | float | Índice de 0 a 1 que mede a proximidade entre a estimativa de esforço e o tempo real (1 = estimativas perfeitas). |
| `indicadores_por_peso` | dict | Métricas acima segmentadas por peso (1, 2, 3). |
| `indicadores_por_equipe` | dict | Métricas acima segmentadas por equipe (presente apenas se ao menos um registro tiver equipe informada). |
| `total_registros_processados` | int | Total de registros processados no lote. |
| `registros_sem_inicio_execucao` | int | Registros concluídos sem `execucao_iniciada` preenchido (excluídos do tempo de execução). |

#### 1.3.3 Regras de Negócio e Restrições

- Somente registros com `estado = "concluida"` entram no cálculo de tempo de execução, mediana, desvio padrão, detecção de outliers e acurácia de estimativa.
- Tempo de execução = `execucao_finalizada − execucao_iniciada` (expresso em minutos).
- Registros concluídos sem `execucao_iniciada` preenchido não entram no tempo de execução; são contados em `registros_sem_inicio_execucao`, nunca descartados em silêncio.
- Um registro é considerado atrasado quando `execucao_finalizada > vencimento`.
- `peso` deve ser um inteiro entre 1 e 3; qualquer outro valor gera erro de validação (`PesoForaDoIntervaloError`).
- `codigo` deve seguir o padrão `"TSK-"` seguido de 4 dígitos e ser único dentro do lote; formato inválido ou código duplicado gera erro (`FormatoCodigoInvalidoError`).
- Registros com cronologia inconsistente (ex.: `execucao_finalizada` anterior a `execucao_iniciada`, ou `execucao_iniciada` anterior a `abertura`) geram um erro específico (`CronologiaInvalidaError`) e são excluídos do cálculo.
- Um registro concluído é considerado atípico (outlier) quando seu tempo de execução ultrapassa a média do lote somada a duas vezes o desvio padrão (critério estatístico de z-score > 2).
- Quando `esforco_estimado_min` e o tempo de execução estiverem disponíveis, calcula-se o erro relativo da estimativa = `|esforco_estimado_min − tempo_execucao| / esforco_estimado_min`; o índice de acurácia é a média de (1 − erro relativo), limitada ao intervalo [0, 1].
- `indicadores_por_equipe` só deve ser calculado e retornado quando pelo menos um registro do lote tiver o campo `equipe` preenchido; caso contrário, retorna-se um dicionário vazio.
- Quando não houver nenhum registro com `estado = "concluida"` no lote, todas as métricas numéricas devem ser retornadas zeradas (nunca `None` ou exceção), com `total_registros_processados` informado corretamente.
- Todas as datas devem ser tratadas em UTC, no formato ISO 8601; arredondamento de 2 casas decimais para métricas de tempo, percentuais e índices.

---

## 2. Especificação de Cenários de Aceite e Test Harness

### 2.1 Cenários de Aceite (Dado – Quando – Então)

#### Cenário 1 — Sucesso (Estatísticas completas)

**Dado:** um lote de registros válidos, alguns concluídos e outros em diferentes estados, com pesos e equipes variados, e parte deles com `esforco_estimado_min` informado.
**Quando:** o TaskAnalyzer for executado sobre esse lote.
**Então:** o sistema deve retornar corretamente:

- ✔ o tempo médio, o tempo mediano e o desvio padrão de execução;
- ✔ a taxa de atraso, os indicadores por peso e, quando aplicável, por equipe;
- ✔ o índice de acurácia de estimativa, calculado apenas sobre os registros com esforço estimado informado.

#### Cenário 2 — Exceção / Erro (Entradas inválidas)

**Dado:** um lote com pelo menos um registro com `codigo` fora do padrão `"TSK-####"`, `peso` fora do intervalo de 1 a 3, ou cronologia inconsistente entre `abertura`, `execucao_iniciada` e `execucao_finalizada`.
**Quando:** o TaskAnalyzer for executado sobre esse lote.
**Então:** o sistema deve disparar a exceção específica correspondente (`FormatoCodigoInvalidoError`, `PesoForaDoIntervaloError` ou `CronologiaInvalidaError`), com mensagem clara e objetiva — nunca uma falha silenciosa ou um valor incorreto.

#### Cenário 3 — Detecção de Anomalia (Outlier)

**Dado:** um lote de registros concluídos em que um deles apresenta tempo de execução muito acima dos demais (acima da média mais duas vezes o desvio padrão do lote).
**Quando:** o TaskAnalyzer for executado sobre esse lote.
**Então:** esse registro deve ser contabilizado em `tarefas_atipicas`, sem distorcer incorretamente as demais métricas do lote (a mediana, em particular, deve permanecer estável).

#### Cenário 4 — Borda (Nenhum registro concluído)

**Dado:** um lote em que nenhum registro possui `estado = "concluida"` (todos abertos, em andamento ou cancelados).
**Quando:** o TaskAnalyzer for executado sobre esse lote.
**Então:** o sistema deve retornar todas as métricas numéricas zeradas, sem lançar exceção, informando corretamente o `total_registros_processados`.

### 2.2 Planejamento do Test Harness

Os quatro cenários acima serão transformados em testes automatizados na Fase 2, seguindo o fluxo abaixo:

1. **Cenários de Aceite** (esta especificação): descrevem o comportamento esperado do sistema — incluindo sucesso, exceção, detecção de anomalia e o caso de borda — e servem como referência única para os testes.
2. **Casos de Teste** (derivados dos cenários): decompõem cada cenário em casos específicos, definindo os lotes de `RegistroTarefa` de entrada e os resultados esperados — inclusive o lote sintético usado para provocar um outlier no Cenário 3.
3. **Testes Automatizados** (pytest): implementam os casos de teste em pytest, com fixtures dedicadas para gerar os lotes de `RegistroTarefa` e validar outputs, tipos e exceções (`FormatoCodigoInvalidoError`, `PesoForaDoIntervaloError`, `CronologiaInvalidaError`).
4. **Execução e Validação** (contínua): os testes são executados automaticamente a cada geração de código; qualquer falha bloqueia o avanço da solução.
5. **Relatórios e Evidências**: geração de relatórios de cobertura e resultados, garantindo rastreabilidade entre cada cenário e seu respectivo teste, com meta mínima de 90% de cobertura.

**Objetivo: garantir que todo código gerado por IA esteja correto e em conformidade com o contrato de negócio e os quatro cenários de aceite definidos nesta especificação.**

---

## 3. Governança de Contexto e Regras para Agentes de IA

Publicada integralmente em [`CONTEXT_RULES.md`](../CONTEXT_RULES.md), que deve ser fornecido obrigatoriamente a qualquer assistente de IA que participe da geração de código.
