"""Geração dos lotes de ``RegistroTarefa`` usados pelo Test Harness.

Este módulo separa os dados de teste (fixtures) dos casos de teste
(``test_harness.py``), conforme a arquitetura planejada na Fase 1. Cada lote
corresponde a um Cenário de Aceite da especificação SDD (seção 2.1).

Os fixtures são registrados no pytest por meio de
``pytest_plugins = ["fixtures_dados"]`` em ``test_harness.py``.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from modelos import EstadoTarefa, RegistroTarefa

T0: datetime = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
"""Instante de referência (UTC) a partir do qual as datas dos lotes são geradas."""


def em(minutos: float) -> datetime:
    """Retorna o instante ``T0 + minutos``.

    Args:
        minutos: Deslocamento em minutos a partir de ``T0``.

    Returns:
        Data/hora em UTC.
    """
    return T0 + timedelta(minutes=minutos)


def criar_registro(**alteracoes: Any) -> RegistroTarefa:  # noqa: ANN401
    """Cria um ``RegistroTarefa`` válido, sobrescrevendo os campos informados.

    Valores padrão: código ``TSK-0001``, aberto em ``T0``, vencimento em
    ``T0 + 10h``, peso 2 e estado ``aberta``.

    Args:
        **alteracoes: Campos do contrato a sobrescrever.

    Returns:
        Uma nova instância de ``RegistroTarefa``.
    """
    campos: dict[str, Any] = {
        "codigo": "TSK-0001",
        "abertura": T0,
        "vencimento": em(600),
        "peso": 2,
        "estado": EstadoTarefa.ABERTA,
    }
    campos.update(alteracoes)
    return RegistroTarefa(**campos)


def criar_concluido(
    codigo: str,
    inicio_min: float | None,
    fim_min: float,
    **alteracoes: Any,  # noqa: ANN401
) -> RegistroTarefa:
    """Cria um registro concluído com início e fim relativos a ``T0``.

    Args:
        codigo: Código ``TSK-####`` do registro.
        inicio_min: Minutos após ``T0`` do início da execução (``None`` para
            registro sem início informado).
        fim_min: Minutos após ``T0`` da finalização da execução.
        **alteracoes: Demais campos a sobrescrever.

    Returns:
        Uma nova instância concluída de ``RegistroTarefa``.
    """
    return criar_registro(
        codigo=codigo,
        estado=EstadoTarefa.CONCLUIDA,
        execucao_iniciada=None if inicio_min is None else em(inicio_min),
        execucao_finalizada=em(fim_min),
        **alteracoes,
    )


@pytest.fixture
def lote_sucesso() -> list[RegistroTarefa]:
    """Cenário 1: lote válido com estados, pesos, equipes e estimativas variados.

    Resumo dos concluídos (tempo de execução / situação / estimativa):

    * TSK-0001: 120 min, no prazo, estimado 100 (peso 3, Dados)
    * TSK-0002:  60 min, atrasado, estimado 60 (peso 3, Dados)
    * TSK-0003:  90 min, no prazo, sem estimativa (peso 2, Plataforma)
    * TSK-0004:  30 min, atrasado, estimado 40 (peso 1, sem equipe)
    * TSK-0005: sem início, no prazo, estimado 50 (peso 2, Plataforma)

    Não concluídos: TSK-0006 (em_andamento), TSK-0007 (aberta) e
    TSK-0008 (cancelada, finalizada após o vencimento - não conta atraso).

    Returns:
        Lista com 8 registros.
    """
    return [
        criar_concluido(
            "TSK-0001",
            0,
            120,
            vencimento=em(180),
            peso=3,
            equipe="Dados",
            esforco_estimado_min=100,
        ),
        criar_concluido(
            "TSK-0002",
            60,
            120,
            vencimento=em(90),
            peso=3,
            equipe="Dados",
            esforco_estimado_min=60,
        ),
        criar_concluido(
            "TSK-0003", 30, 120, vencimento=em(240), peso=2, equipe="Plataforma"
        ),
        criar_concluido(
            "TSK-0004", 10, 40, vencimento=em(20), peso=1, esforco_estimado_min=40
        ),
        criar_concluido(
            "TSK-0005",
            None,
            100,
            vencimento=em(240),
            peso=2,
            equipe="Plataforma",
            esforco_estimado_min=50,
        ),
        criar_registro(
            codigo="TSK-0006",
            estado=EstadoTarefa.EM_ANDAMENTO,
            execucao_iniciada=em(5),
            peso=1,
            equipe="Dados",
        ),
        criar_registro(codigo="TSK-0007", estado=EstadoTarefa.ABERTA, peso=2),
        criar_registro(
            codigo="TSK-0008",
            estado=EstadoTarefa.CANCELADA,
            execucao_iniciada=em(10),
            execucao_finalizada=em(700),
            vencimento=em(600),
            peso=3,
            equipe="Plataforma",
            esforco_estimado_min=30,
        ),
    ]


@pytest.fixture
def lote_sem_outlier() -> list[RegistroTarefa]:
    """Cenário 3 (base): nove concluídos com 60 min de execução cada.

    Returns:
        Lista com 9 registros concluídos (TSK-0001 a TSK-0009).
    """
    return [criar_concluido(f"TSK-{i:04d}", 0, 60) for i in range(1, 10)]


@pytest.fixture
def lote_com_outlier(lote_sem_outlier: list[RegistroTarefa]) -> list[RegistroTarefa]:
    """Cenário 3: lote sintético com uma tarefa de 600 min entre nove de 60 min.

    Média = 114, desvio padrão populacional = 162, limite = 114 + 2 × 162 = 438.
    Como 600 > 438, TSK-0010 deve ser contabilizada como atípica.

    Args:
        lote_sem_outlier: Nove registros de 60 min.

    Returns:
        Lista com 10 registros concluídos.
    """
    return [*lote_sem_outlier, criar_concluido("TSK-0010", 0, 600)]


@pytest.fixture
def lote_sem_concluidos() -> list[RegistroTarefa]:
    """Cenário 4: nenhum registro com ``estado = "concluida"``.

    Returns:
        Lista com 3 registros (aberta, em_andamento e cancelada).
    """
    return [
        criar_registro(
            codigo="TSK-0001",
            estado=EstadoTarefa.ABERTA,
            peso=1,
            equipe="Dados",
            esforco_estimado_min=30,
        ),
        criar_registro(
            codigo="TSK-0002",
            estado=EstadoTarefa.EM_ANDAMENTO,
            execucao_iniciada=em(15),
            peso=2,
            equipe="Dados",
        ),
        criar_registro(
            codigo="TSK-0003",
            estado=EstadoTarefa.CANCELADA,
            execucao_iniciada=em(5),
            execucao_finalizada=em(900),
            peso=3,
        ),
    ]
