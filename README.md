# TaskAnalyzer — SDD

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![Testes](https://img.shields.io/badge/pytest-66%20passed-brightgreen?logo=pytest)
![Cobertura](https://img.shields.io/badge/cobertura-100%25-brightgreen)
![Lint](https://img.shields.io/badge/lint-ruff%20ok-brightgreen)
![Dependências](https://img.shields.io/badge/produ%C3%A7%C3%A3o-somente%20stdlib-blue)

Módulo de análise estatística de lotes de tarefas, construído com **Spec-Driven Development (SDD)**: o código em `src/` foi gerado por assistente de IA a partir do contrato em [`specs/especificacao_taskanalyzer.md`](specs/especificacao_taskanalyzer.md), sob as regras de [`CONTEXT_RULES.md`](CONTEXT_RULES.md), e homologado por revisão humana e pelo Test Harness em `tests/`.

**Bootcamp III — Desafio Cumulativo, Fase 2** · João Pedro Pinheiro Ghesti · Ciência de Dados e Machine Learning (Asa Norte)

---

## Status do build

| Verificação | Comando | Resultado |
|---|---|---|
| Test Harness | `pytest` | **66 passed** (100%) |
| Cobertura de `src/` | `pytest` (pytest-cov, meta ≥ 90%) | **100%** (linhas e ramos) |
| Lint, PEP 8, type hints e docstrings | `ruff check .` | **All checks passed** |
| Versões de Python verificadas | — | 3.12 e 3.13 |

> Na Fase 3 esta tabela será substituída pelo badge do pipeline de CI/CD (GitHub Actions).

---

## O que o TaskAnalyzer calcula

A partir de um lote de `RegistroTarefa`, a função pública `analyze_tasks` retorna:

| Saída | Descrição |
|---|---|
| `tempo_medio_execucao_min` | Média do tempo de execução (min) das tarefas concluídas |
| `tempo_mediano_execucao_min` | Mediana do tempo de execução (robusta a outliers) |
| `desvio_padrao_execucao_min` | Desvio padrão populacional do tempo de execução |
| `taxa_atraso` | % de concluídas com `execucao_finalizada > vencimento` |
| `tarefas_atipicas` | Concluídas com tempo > média + 2 × desvio padrão (z-score > 2) |
| `indice_acuracia_estimativa` | Média de `1 − \|estimado − real\| / estimado`, limitada a [0, 1] |
| `indicadores_por_peso` | As seis métricas acima para os pesos 1, 2 e 3 |
| `indicadores_por_equipe` | As seis métricas por equipe (vazio se nenhuma equipe for informada) |
| `total_registros_processados` | Total de registros do lote |
| `registros_sem_inicio_execucao` | Concluídos sem `execucao_iniciada` (excluídos do tempo) |

Entradas inválidas disparam exceções específicas, todas subclasses de `TaskValidationError`:

| Exceção | Quando |
|---|---|
| `FormatoCodigoInvalidoError` | `codigo` fora do padrão `TSK-####` ou duplicado no lote |
| `PesoForaDoIntervaloError` | `peso` que não é inteiro entre 1 e 3 |
| `CronologiaInvalidaError` | `execucao_iniciada < abertura`, `execucao_finalizada < execucao_iniciada` ou `execucao_finalizada < abertura` |

---

## Estrutura do repositório

Segue exatamente a arquitetura planejada na Fase 1 (apresentação "Arquitetura do Repositório para Git e GitHub"):

```text
taskanalyzer-sdd/
├── README.md                  # Documentação geral, execução e status do build
├── CONTEXT_RULES.md           # Regras de governança de IA (Seção 3 da especificação)
├── requirements.txt           # Dependências autorizadas (pytest, pytest-cov, ruff)
├── specs/
│   └── especificacao_taskanalyzer.md   # Contrato SDD (Seções 1 e 2 da especificação)
├── tests/
│   ├── test_harness.py        # Casos de teste (Cenários de Aceite 1 a 4)
│   └── fixtures_dados.py      # Geração dos lotes de RegistroTarefa usados nos testes
└── src/
    ├── modelos.py             # Dataclass imutável RegistroTarefa e tipos de saída
    ├── analisador.py          # Validação + cálculos estatísticos (analyze_tasks)
    └── excecoes.py            # TaskValidationError e as três exceções específicas
```

Arquivos de apoio na raiz: `.gitignore` (exigido pelo enunciado) e `pyproject.toml` (somente configuração de pytest, cobertura mínima de 90% e ruff — não empacota o projeto).

---

## Como executar

Pré-requisito: **Python 3.12+**.

```bash
git clone https://github.com/<seu-usuario>/taskanalyzer-sdd.git
cd taskanalyzer-sdd

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest                             # Test Harness + relatório de cobertura
ruff check .                       # Lint (PEP 8, type hints, docstrings)
```

Saída esperada (resumo):

```text
tests/test_harness.py::TestCenario1Sucesso::test_tempo_medio_mediano_e_desvio_padrao PASSED
...
Name                Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------
src/analisador.py     119      0     34      0   100%
src/excecoes.py         8      0      0      0   100%
src/modelos.py         56      0     14      0   100%
---------------------------------------------------------------
TOTAL                 183      0     48      0   100%
Required test coverage of 90.0% reached. Total coverage: 100.00%
============================== 66 passed in 0.30s ==============================
```

### Exemplo de uso

```bash
PYTHONPATH=src python    # Windows (PowerShell): $env:PYTHONPATH="src"; python
```

```python
from analisador import analyze_tasks
from modelos import RegistroTarefa

lote = [
    RegistroTarefa.de_dict({
        "codigo": "TSK-0001",
        "abertura": "2026-09-01T08:00:00Z",
        "execucao_iniciada": "2026-09-01T08:00:00Z",
        "execucao_finalizada": "2026-09-01T10:00:00Z",
        "vencimento": "2026-09-01T11:00:00Z",
        "peso": 3,
        "estado": "concluida",
        "equipe": "Dados",
        "esforco_estimado_min": 100,
    }),
    RegistroTarefa.de_dict({
        "codigo": "TSK-0002",
        "abertura": "2026-09-01T08:00:00Z",
        "vencimento": "2026-09-02T08:00:00Z",
        "peso": 1,
        "estado": "aberta",
    }),
]

resultado = analyze_tasks(lote)
resultado["tempo_medio_execucao_min"]     # 120.0
resultado["indice_acuracia_estimativa"]   # 0.8  (1 - |100 - 120| / 100)
resultado["total_registros_processados"]  # 2
```

Os logs são emitidos no logger `taskanalyzer`, com mensagens em JSON (ex.: `{"modulo": "taskanalyzer", "evento": "analise_concluida", ...}`). Para vê-los: `logging.basicConfig(level=logging.INFO)`.

---

## Rastreabilidade: Cenários de Aceite → Testes

| Cenário (especificação, seção 2.1) | Classe em `tests/test_harness.py` | Testes | Lote (`tests/fixtures_dados.py`) |
|---|---|---|---|
| 1 — Sucesso (estatísticas completas) | `TestCenario1Sucesso` | 11 | `lote_sucesso` |
| 2 — Exceção / Erro (entradas inválidas) | `TestCenario2Excecoes` | 30 | registros inválidos via `criar_registro` |
| 3 — Detecção de anomalia (outlier) | `TestCenario3Outlier` | 5 | `lote_com_outlier`, `lote_sem_outlier` |
| 4 — Borda (nenhum concluído / lote vazio) | `TestCenario4Borda` | 6 | `lote_sem_concluidos`, lote vazio |
| Regras complementares (seção 1.3.3) e CONTEXT_RULES | `TestContratoComplementar` | 14 | diversos |

Valores esperados do Cenário 1, conferidos manualmente: tempos de execução `[120, 60, 90, 30]` → média **75,00**, mediana **75,00**, desvio padrão **33,54**; atraso **40,00%** (2 de 5 concluídas); acurácia **0,85** (média de 0,80; 1,00; 0,75).
No Cenário 3, nove tarefas de 60 min e uma de 600 min → média 114, desvio 162, limite 438: **1 tarefa atípica**, mediana estável em **60**.

---

## Homologação humana

Plano definido na Fase 1 e aplicado a todo código gerado por IA antes do commit:

- [x] 1. Execução completa dos testes automatizados (`test_harness.py`) — 66/66 aprovados.
- [x] 2. Cobertura mínima de 90% e lint (`ruff`) sobre `modelos.py` e `analisador.py` — 100% e sem apontamentos.
- [x] 3. Revisão de conformidade com o contrato de negócio e com o `CONTEXT_RULES.md`.
- [x] 4. Conferência manual das fórmulas estatísticas (média, mediana, desvio padrão, outliers) — ver valores acima.
- [x] 5. Testes manuais complementares em casos de borda (lote vazio, estimativa zero, conclusão exatamente no vencimento).
- [x] 6. Somente após aprovação em todos os passos, o código foi commitado.

### Conformidade com o CONTEXT_RULES

| Regra | Como foi atendida |
|---|---|
| Python 3.12+ | `StrEnum`, `Self`, `datetime.UTC`; ruff com `target-version = "py312"` |
| Type hints em todas as funções | Regra `ANN` do ruff ativa; verificado também com `mypy --strict` |
| `RegistroTarefa` imutável | `@dataclass(frozen=True, kw_only=True, slots=True)` |
| Somente biblioteca padrão | `statistics`, `datetime`, `dataclasses`, `re`, `json`, `logging` |
| SRP: modelos, cálculo e exceções separados | `modelos.py`, `analisador.py`, `excecoes.py`; validação e cálculo em blocos distintos |
| Docstrings Google style | Regra `D` do ruff com `convention = "google"` |
| Exceções específicas | Três classes próprias + base `TaskValidationError` |
| Logs JSON com `logging` | Logger `taskanalyzer`; teste `test_logs_estruturados_em_json` |
| Prevenção de divisão por zero | Médias de listas vazias retornam `0.0`; estimativas `<= 0` ficam fora do índice |
| Sem persistência e sem estado global mutável | Funções puras; teste `test_execucao_nao_guarda_estado_entre_chamadas` |

### Decisões de interpretação (lacunas do contrato)

Pontos que a especificação não fixa explicitamente. Cada um foi resolvido da forma mais conservadora, documentado e coberto por teste, para validação humana:

| Ponto | Decisão adotada |
|---|---|
| Nome da função pública | `analyze_tasks(registros)`, nome definido no enunciado da Fase 2 |
| Desvio padrão amostral ou populacional | **Populacional** (`statistics.pstdev`): o lote analisado é a população inteira ("desvio padrão do lote") |
| Limite do índice de acurácia | Aplicado à **média** de (1 − erro relativo), como redigido no contrato |
| Raiz comum das exceções | `TaskValidationError` (nome do enunciado), que herda de `ValueError` |
| Cronologia sem `execucao_iniciada` | `execucao_finalizada < abertura` também é `CronologiaInvalidaError` |
| Concluída sem `execucao_finalizada` | Fora do tempo de execução e do denominador da taxa de atraso; registrada em log (nunca em silêncio) |
| `esforco_estimado_min <= 0` | Fora do índice de acurácia (evita divisão por zero); registrado em log |
| Sem estimativas avaliáveis | `indice_acuracia_estimativa = 0.0` (métrica numérica zerada, nunca `None`) |
| `indicadores_por_peso` | Sempre com as chaves 1, 2 e 3 (zeradas quando não há concluídas no peso) |
| Outliers dentro de um segmento | Critério z-score > 2 aplicado ao próprio segmento |
| Datas sem fuso horário | Interpretadas como UTC; datas com fuso são convertidas para UTC |
| `equipe` em branco | Tratada como não informada |
| Conclusão exatamente no vencimento | Não é atraso (exige `execucao_finalizada > vencimento`) |

---

## Uso de IA: prompts e controle de alucinações

O código de `src/` e os testes de `tests/` foram gerados com o assistente de IA **Claude** (Anthropic). Os commits gerados com IA trazem o trailer `Co-Authored-By`.

**Prompt utilizado.** O assistente recebeu como contexto completo a especificação SDD (Seções 1 e 2, hoje em `specs/`), as regras de governança (Seção 3, hoje em `CONTEXT_RULES.md`), a apresentação com a arquitetura do repositório e o enunciado da Fase 2, com a instrução de implementar o que o enunciado pede **obedecendo rigorosamente** ao planejado na especificação e seguindo a estrutura de pastas da apresentação.

**Como o CONTEXT_RULES evitou alucinações:**

- **"Não assumir comportamentos não especificados" + especificação como única fonte da verdade.** O enunciado genérico cita campos (`total_tarefas`, `total_concluidas`, `data_criacao`…) e um arquivo `task_analyzer.py` que **não existem** no contrato desta especificação. O assistente usou apenas os campos, regras e cenários do contrato SDD, e as lacunas reais foram listadas na tabela acima para decisão humana, em vez de serem preenchidas silenciosamente.
- **Somente biblioteca padrão.** Impediu o uso de `pandas`/`numpy` para média, mediana e desvio padrão (`statistics` foi suficiente).
- **Estrutura de pastas protegida.** Manteve a divisão `modelos.py` / `analisador.py` / `excecoes.py` e `test_harness.py` / `fixtures_dados.py` da Fase 1.
- **Não misturar validação com cálculo.** O analisador foi organizado em blocos separados: validação → cálculo (funções puras) → logs.
- **Exigir explicação das fórmulas.** Cada fórmula está descrita no docstring de `analisador.py` e conferida com valores calculados à mão nos testes.
- **Não alterar os cenários.** Os quatro Cenários de Aceite foram traduzidos literalmente em classes de teste, sem adaptação.

---

## Fluxo de versionamento (Git Flow simplificado)

| Branch | Conteúdo | Destino do PR |
|---|---|---|
| `main` | Versões homologadas (tag `v0.2.0` = Fase 2) | — |
| `develop` | Integração das funcionalidades | `main` |
| `feature/sdd-specification` | Especificação SDD e CONTEXT_RULES | `develop` |
| `feature/task-analyzer-impl` | Exceções, modelos e analisador gerados via IA | `develop` |
| `feature/test-harness` | Fixtures e Test Harness (Cenários 1 a 4) | `develop` |

Commits pequenos no padrão Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`), Pull Requests obrigatórios com revisão humana antes do merge e lint verificado antes de cada merge.

---

## Links

- Especificação SDD (Fase 1, Google Docs): *[inserir link]*
- Vídeo de apresentação técnica (Fase 2, YouTube): *[inserir link]*

## Próximos passos (Fase 3)

CI/CD com GitHub Actions (pytest + ruff a cada PR), containerização com Docker e relatório de governança/segurança.
