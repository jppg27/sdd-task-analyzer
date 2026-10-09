"""Exceções específicas do TaskAnalyzer.

Este módulo concentra apenas as classes de erro do domínio, conforme a
separação de responsabilidades exigida pelo CONTEXT_RULES (seção 3.1).

Hierarquia:
    TaskValidationError
    ├── FormatoCodigoInvalidoError
    ├── PesoForaDoIntervaloError
    └── CronologiaInvalidaError

A classe base ``TaskValidationError`` (nome exigido pelo enunciado da Fase 2)
permite capturar qualquer falha de validação do lote com um único ``except``,
enquanto as subclasses preservam a especificidade definida no contrato SDD.
"""


class TaskValidationError(ValueError):
    """Erro base para qualquer registro inválido recebido pelo TaskAnalyzer.

    Attributes:
        codigo: Código do registro que originou o erro (pode ser inválido).
        motivo: Descrição objetiva da regra de negócio violada.
    """

    def __init__(self, codigo: str, motivo: str) -> None:
        """Inicializa o erro com o código do registro e o motivo.

        Args:
            codigo: Código do registro que originou o erro.
            motivo: Descrição objetiva da regra de negócio violada.
        """
        self.codigo: str = codigo
        self.motivo: str = motivo
        super().__init__(f"Registro '{codigo}': {motivo}")


class FormatoCodigoInvalidoError(TaskValidationError):
    """O ``codigo`` não segue o padrão ``TSK-####`` ou está duplicado no lote."""


class PesoForaDoIntervaloError(TaskValidationError):
    """O ``peso`` não é um inteiro entre 1 e 3."""


class CronologiaInvalidaError(TaskValidationError):
    """As datas de abertura, início e finalização estão em ordem inconsistente."""
