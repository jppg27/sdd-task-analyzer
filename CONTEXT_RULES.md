# CONTEXT_RULES — Governança de Contexto e Regras para Agentes de IA

> Transposição da Seção 3 da "Especificação SDD TaskAnalyzer" (Fase 1, v2.0).
> Estas regras devem ser fornecidas **obrigatoriamente**, junto com
> [`specs/especificacao_taskanalyzer.md`](specs/especificacao_taskanalyzer.md),
> a qualquer assistente de IA que participe da geração de código,
> garantindo alinhamento, consistência e qualidade.

---

## 3.1 Diretrizes Arquiteturais (Obrigatórias)

- ✔ Python 3.12+ como versão mínima obrigatória.
- ✔ Utilizar type hints (anotações de tipo) em todas as funções e métodos.
- ✔ Implementar `RegistroTarefa` como dataclass imutável (`frozen=True`).
- ✔ Utilizar apenas bibliotecas da biblioteca padrão do Python (`statistics`, `datetime`, `math`, `dataclasses`) para os cálculos estatísticos; qualquer dependência externa deve ser justificada e listada em `requirements.txt`.
- ✔ Seguir o princípio Single Responsibility (SRP) e código limpo (PEP 8), separando claramente modelos de dados, lógica de cálculo e exceções em módulos distintos.
- ✔ Documentação formal no padrão Google style docstrings para módulos, classes, funções e parâmetros.
- ✔ Funções devem ser pequenas, coesas e com um único propósito.
- ✔ Tratamento de exceções específico, com classes próprias (`FormatoCodigoInvalidoError`, `PesoForaDoIntervaloError`, `CronologiaInvalidaError`).
- ✔ Logs estruturados em formato JSON, utilizando o módulo padrão `logging`.
- ✔ Cobertura mínima de 90% dos testes automatizados sobre o módulo de análise.

## 3.2 Proibições Explícitas (Regras Restritivas)

- ✘ Não utilizar bibliotecas externas que não estejam listadas em `requirements.txt`.
- ✘ Não alterar, remover ou adaptar os cenários de teste fornecidos.
- ✘ Não modificar a estrutura de pastas definida nesta especificação.
- ✘ Não persistir dados em arquivos ou bancos de dados.
- ✘ Não alterar a assinatura (nome e parâmetros) das funções públicas sem autorização.
- ✘ Não gerar código sem testes correspondentes para as novas funcionalidades.
- ✘ Não inserir código duplicado ou desnecessário.
- ✘ Não misturar lógica de cálculo estatístico com lógica de validação de entrada ou de apresentação de resultados.
- ✘ Não utilizar variáveis globais mutáveis para armazenar estado entre execuções.
- ✘ Não assumir comportamentos não especificados no contrato de negócio.

## 3.3 Regras de Interação com a IA

- Fornecer sempre o contexto completo (especificação, cenários e regras) antes de solicitar qualquer geração de código à IA.
- Validar se a IA compreendeu corretamente o contrato de negócio antes de aceitar o código gerado.
- Exigir que a IA explique, em linguagem simples, a fórmula ou o raciocínio estatístico usado em cada métrica antes de aceitar a implementação.
- Solicitar explicações adicionais sempre que houver dúvidas sobre a solução proposta pela IA.
- Revisar criticamente todo código gerado, nunca aceitá-lo automaticamente.
- Rejeitar e solicitar nova geração sempre que a resposta da IA violar as proibições ou o contrato definido.

---

## Estrutura de pastas protegida

Conforme a arquitetura do repositório definida na Fase 1 (apresentação complementar):

```text
taskanalyzer-sdd/
├── README.md
├── CONTEXT_RULES.md
├── requirements.txt
├── specs/
│   └── especificacao_taskanalyzer.md
├── tests/
│   ├── test_harness.py
│   └── fixtures_dados.py
└── src/
    ├── modelos.py
    ├── analisador.py
    └── excecoes.py
```
