"""Modelos de dados do TaskAnalyzer.

Contém apenas estruturas de dados (sem lógica de cálculo nem de validação de
regras de negócio), conforme o princípio Single Responsibility exigido pelo
CONTEXT_RULES:

* ``EstadoTarefa``: enumeração dos estados aceitos pelo contrato (seção 1.3.1).
* ``RegistroTarefa``: entidade de entrada, implementada como dataclass imutável.
* ``MetricasSegmento`` e ``ResultadoAnalise``: formato tipado da saída
  (seção 1.3.2).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self, TypedDict

_CAMPOS_DATA: tuple[str, ...] = (
    "abertura",
    "execucao_iniciada",
    "execucao_finalizada",
    "vencimento",
)


class EstadoTarefa(StrEnum):
    """Estados aceitos para um ``RegistroTarefa``.

    Por herdar de ``str``, cada membro é igual ao seu valor textual
    (ex.: ``EstadoTarefa.CONCLUIDA == "concluida"``).
    """

    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


def _para_utc(nome_campo: str, valor: datetime) -> datetime:
    """Converte uma data/hora para UTC.

    Datas sem fuso horário (naive) são interpretadas como UTC, pois o contrato
    determina que todas as datas sejam tratadas em UTC.

    Args:
        nome_campo: Nome do campo, usado na mensagem de erro.
        valor: Data/hora a ser normalizada.

    Returns:
        A mesma data/hora expressa em UTC.

    Raises:
        TypeError: Se ``valor`` não for um ``datetime``.
    """
    if not isinstance(valor, datetime):
        raise TypeError(
            f"Campo '{nome_campo}' deve ser datetime, recebido {type(valor).__name__}."
        )
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)


@dataclass(frozen=True, kw_only=True, slots=True)
class RegistroTarefa:
    """Tarefa individual dentro do lote analisado (contrato, seção 1.3.1).

    A instância é imutável. Na criação, as datas são normalizadas para UTC,
    ``estado`` é convertido para ``EstadoTarefa`` e ``equipe`` em branco é
    tratada como não informada. As regras de negócio (padrão do código,
    intervalo do peso e cronologia) são verificadas pelo analisador, no
    momento da execução sobre o lote.

    Attributes:
        codigo: Identificador único no padrão ``TSK-####``.
        abertura: Data/hora de abertura do registro (UTC).
        vencimento: Data/hora limite acordada para a conclusão (UTC).
        peso: Importância da tarefa, de 1 (baixo) a 3 (crítico).
        estado: Estado da tarefa.
        execucao_iniciada: Data/hora de início da execução (opcional).
        execucao_finalizada: Data/hora de finalização da execução (opcional).
        equipe: Equipe ou responsável (opcional).
        esforco_estimado_min: Estimativa de esforço em minutos (opcional).
    """

    codigo: str
    abertura: datetime
    execucao_iniciada: datetime | None = None
    execucao_finalizada: datetime | None = None
    vencimento: datetime
    peso: int
    estado: EstadoTarefa
    equipe: str | None = None
    esforco_estimado_min: int | None = None

    def __post_init__(self) -> None:
        """Normaliza datas para UTC, o estado para enum e a equipe em branco.

        Raises:
            TypeError: Se algum campo de data não for ``datetime``.
            ValueError: Se ``estado`` não for um dos valores aceitos.
        """
        for nome in _CAMPOS_DATA:
            valor = getattr(self, nome)
            if valor is not None:
                object.__setattr__(self, nome, _para_utc(nome, valor))
        object.__setattr__(self, "estado", EstadoTarefa(self.estado))
        if self.equipe is not None and not self.equipe.strip():
            object.__setattr__(self, "equipe", None)

    @classmethod
    def de_dict(cls, dados: Mapping[str, Any]) -> Self:
        """Cria um registro a partir de um dicionário com datas em ISO 8601.

        Args:
            dados: Mapeamento com os campos do contrato. Campos de data podem
                ser ``datetime`` ou texto ISO 8601 (ex.: ``"2026-09-01T08:00:00Z"``).

        Returns:
            Uma nova instância de ``RegistroTarefa``.
        """
        campos = dict(dados)
        for nome in _CAMPOS_DATA:
            valor = campos.get(nome)
            if isinstance(valor, str):
                campos[nome] = datetime.fromisoformat(valor)
        return cls(**campos)


class MetricasSegmento(TypedDict):
    """Métricas estatísticas calculadas para um conjunto de registros."""

    tempo_medio_execucao_min: float
    tempo_mediano_execucao_min: float
    desvio_padrao_execucao_min: float
    taxa_atraso: float
    tarefas_atipicas: int
    indice_acuracia_estimativa: float


class ResultadoAnalise(MetricasSegmento):
    """Saída completa do TaskAnalyzer (contrato, seção 1.3.2)."""

    indicadores_por_peso: dict[int, MetricasSegmento]
    indicadores_por_equipe: dict[str, MetricasSegmento]
    total_registros_processados: int
    registros_sem_inicio_execucao: int
