"""Analisador estatístico de lotes de ``RegistroTarefa`` (TaskAnalyzer).

Ponto de entrada público: :func:`analyze_tasks`.

O módulo é organizado em três blocos independentes, para não misturar
validação de entrada com cálculo estatístico (CONTEXT_RULES, seção 3.2):

1. **Validação** do lote (código, peso e cronologia), que dispara as exceções
   específicas definidas em ``excecoes.py``.
2. **Cálculo** estatístico, composto apenas por funções puras sobre os
   registros já validados.
3. **Registro de eventos** em logs estruturados no formato JSON.

Fórmulas utilizadas (todas em minutos, apenas sobre registros concluídos):

* Tempo de execução = ``execucao_finalizada - execucao_iniciada``.
* Média aritmética, mediana e desvio padrão populacional (o lote analisado é
  tratado como a população completa, e não como amostra).
* Tarefa atípica: tempo de execução > média + 2 × desvio padrão (z-score > 2).
* Taxa de atraso: 100 × concluídas com ``execucao_finalizada > vencimento`` /
  concluídas com ``execucao_finalizada`` informada.
* Índice de acurácia: média de ``1 - |estimado - real| / estimado``, limitada
  ao intervalo [0, 1].
"""

import json
import logging
import re
from collections.abc import Iterable, Sequence
from statistics import fmean, median, pstdev

from excecoes import (
    CronologiaInvalidaError,
    FormatoCodigoInvalidoError,
    PesoForaDoIntervaloError,
    TaskValidationError,
)
from modelos import EstadoTarefa, MetricasSegmento, RegistroTarefa, ResultadoAnalise

logger = logging.getLogger("taskanalyzer")
logger.addHandler(logging.NullHandler())

PESOS_VALIDOS: tuple[int, ...] = (1, 2, 3)
LIMIAR_Z_SCORE: float = 2.0
CASAS_DECIMAIS: int = 2
_PADRAO_CODIGO: re.Pattern[str] = re.compile(r"TSK-[0-9]{4}")
_SEGUNDOS_POR_MINUTO: float = 60.0


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def analyze_tasks(registros: Iterable[RegistroTarefa]) -> ResultadoAnalise:
    """Calcula os indicadores estatísticos de um lote de tarefas.

    Args:
        registros: Lote de ``RegistroTarefa`` a ser analisado. Pode ser vazio.

    Returns:
        Dicionário ``ResultadoAnalise`` com as métricas gerais, os indicadores
        segmentados por peso (sempre com as chaves 1, 2 e 3) e por equipe
        (vazio se nenhum registro tiver equipe), o total de registros
        processados e a contagem de concluídos sem início de execução.
        Métricas sem dados são retornadas como ``0.0`` (ou ``0``), nunca
        ``None``.

    Raises:
        FormatoCodigoInvalidoError: Código fora do padrão ``TSK-####`` ou
            duplicado no lote.
        PesoForaDoIntervaloError: Peso que não é um inteiro entre 1 e 3.
        CronologiaInvalidaError: Datas de abertura, início e finalização em
            ordem inconsistente.
    """
    lote = tuple(registros)
    _registrar_evento(logging.INFO, "analise_iniciada", total_registros=len(lote))

    _validar_lote(lote)
    _sinalizar_registros_incompletos(lote)

    metricas_gerais = _calcular_metricas(lote)
    resultado: ResultadoAnalise = {
        **metricas_gerais,
        "indicadores_por_peso": _indicadores_por_peso(lote),
        "indicadores_por_equipe": _indicadores_por_equipe(lote),
        "total_registros_processados": len(lote),
        "registros_sem_inicio_execucao": _contar_sem_inicio_execucao(lote),
    }

    _registrar_evento(
        logging.INFO,
        "analise_concluida",
        total_registros=resultado["total_registros_processados"],
        tempo_medio_execucao_min=resultado["tempo_medio_execucao_min"],
        taxa_atraso=resultado["taxa_atraso"],
        tarefas_atipicas=resultado["tarefas_atipicas"],
    )
    return resultado


# ---------------------------------------------------------------------------
# 1. Validação de entrada
# ---------------------------------------------------------------------------
def _validar_lote(lote: Sequence[RegistroTarefa]) -> None:
    """Valida todos os registros do lote, interrompendo no primeiro erro.

    Args:
        lote: Registros a validar.

    Raises:
        TaskValidationError: Subclasse específica da regra violada.
    """
    codigos_vistos: set[str] = set()
    for registro in lote:
        try:
            _validar_codigo(registro, codigos_vistos)
            _validar_peso(registro)
            _validar_cronologia(registro)
        except TaskValidationError as erro:
            _registrar_evento(
                logging.ERROR,
                "registro_invalido",
                codigo=erro.codigo,
                erro=type(erro).__name__,
                motivo=erro.motivo,
            )
            raise
        codigos_vistos.add(registro.codigo)


def _validar_codigo(registro: RegistroTarefa, codigos_vistos: set[str]) -> None:
    """Verifica o padrão ``TSK-####`` e a unicidade do código no lote.

    Args:
        registro: Registro a validar.
        codigos_vistos: Códigos já validados anteriormente no mesmo lote.

    Raises:
        FormatoCodigoInvalidoError: Formato inválido ou código duplicado.
    """
    codigo = registro.codigo
    if not isinstance(codigo, str) or _PADRAO_CODIGO.fullmatch(codigo) is None:
        raise FormatoCodigoInvalidoError(
            str(codigo), "código fora do padrão 'TSK-' seguido de 4 dígitos."
        )
    if codigo in codigos_vistos:
        raise FormatoCodigoInvalidoError(codigo, "código duplicado no lote.")


def _validar_peso(registro: RegistroTarefa) -> None:
    """Verifica se o peso é um inteiro entre 1 e 3.

    Args:
        registro: Registro a validar.

    Raises:
        PesoForaDoIntervaloError: Peso não inteiro ou fora do intervalo.
    """
    peso = registro.peso
    if isinstance(peso, bool) or not isinstance(peso, int) or peso not in PESOS_VALIDOS:
        raise PesoForaDoIntervaloError(
            registro.codigo, f"peso {peso!r} inválido; esperado inteiro entre 1 e 3."
        )


def _validar_cronologia(registro: RegistroTarefa) -> None:
    """Verifica a ordem ``abertura <= execucao_iniciada <= execucao_finalizada``.

    Args:
        registro: Registro a validar.

    Raises:
        CronologiaInvalidaError: Alguma data anterior à que deveria precedê-la.
    """
    abertura = registro.abertura
    inicio = registro.execucao_iniciada
    fim = registro.execucao_finalizada
    if inicio is not None and inicio < abertura:
        raise CronologiaInvalidaError(
            registro.codigo, "execucao_iniciada anterior à abertura."
        )
    if inicio is not None and fim is not None and fim < inicio:
        raise CronologiaInvalidaError(
            registro.codigo, "execucao_finalizada anterior à execucao_iniciada."
        )
    if fim is not None and fim < abertura:
        raise CronologiaInvalidaError(
            registro.codigo, "execucao_finalizada anterior à abertura."
        )


# ---------------------------------------------------------------------------
# 2. Cálculo estatístico (funções puras)
# ---------------------------------------------------------------------------
def _concluidos(registros: Iterable[RegistroTarefa]) -> list[RegistroTarefa]:
    """Filtra os registros com ``estado == "concluida"``.

    Args:
        registros: Registros de entrada.

    Returns:
        Lista apenas com os registros concluídos.
    """
    return [r for r in registros if r.estado is EstadoTarefa.CONCLUIDA]


def _tempo_execucao_min(registro: RegistroTarefa) -> float | None:
    """Calcula o tempo de execução de um registro, em minutos.

    Args:
        registro: Registro concluído.

    Returns:
        ``execucao_finalizada - execucao_iniciada`` em minutos, ou ``None`` se
        alguma das duas datas não estiver informada.
    """
    if registro.execucao_iniciada is None or registro.execucao_finalizada is None:
        return None
    duracao = registro.execucao_finalizada - registro.execucao_iniciada
    return duracao.total_seconds() / _SEGUNDOS_POR_MINUTO


def _tempos_execucao(concluidos: Iterable[RegistroTarefa]) -> list[float]:
    """Lista os tempos de execução disponíveis dos registros concluídos.

    Args:
        concluidos: Registros concluídos.

    Returns:
        Tempos de execução em minutos (registros sem início são ignorados).
    """
    tempos = (_tempo_execucao_min(r) for r in concluidos)
    return [t for t in tempos if t is not None]


def _media(valores: Sequence[float]) -> float:
    """Média aritmética, ou ``0.0`` se não houver valores."""
    return fmean(valores) if valores else 0.0


def _mediana(valores: Sequence[float]) -> float:
    """Mediana, ou ``0.0`` se não houver valores."""
    return float(median(valores)) if valores else 0.0


def _desvio_padrao(valores: Sequence[float], media: float) -> float:
    """Desvio padrão populacional, ou ``0.0`` se não houver valores."""
    return pstdev(valores, mu=media) if valores else 0.0


def _contar_atipicas(valores: Sequence[float], media: float, desvio: float) -> int:
    """Conta os valores acima de ``media + LIMIAR_Z_SCORE * desvio``.

    Args:
        valores: Tempos de execução em minutos.
        media: Média dos tempos.
        desvio: Desvio padrão populacional dos tempos.

    Returns:
        Quantidade de tarefas atípicas (0 se não houver variabilidade).
    """
    if desvio == 0.0:
        return 0
    limite = media + LIMIAR_Z_SCORE * desvio
    return sum(1 for valor in valores if valor > limite)


def _taxa_atraso(concluidos: Sequence[RegistroTarefa]) -> float:
    """Percentual de concluídos finalizados após o vencimento.

    Args:
        concluidos: Registros concluídos.

    Returns:
        Percentual entre 0 e 100 calculado sobre os concluídos que possuem
        ``execucao_finalizada``; ``0.0`` se nenhum puder ser avaliado.
    """
    avaliaveis = [r for r in concluidos if r.execucao_finalizada is not None]
    if not avaliaveis:
        return 0.0
    atrasados = sum(
        1
        for r in avaliaveis
        if r.execucao_finalizada is not None and r.execucao_finalizada > r.vencimento
    )
    return 100.0 * atrasados / len(avaliaveis)


def _indice_acuracia(concluidos: Sequence[RegistroTarefa]) -> float:
    """Índice de acurácia das estimativas de esforço, de 0 a 1.

    Considera apenas registros com ``esforco_estimado_min > 0`` e tempo de
    execução disponível (a exigência de estimativa positiva evita divisão
    por zero no erro relativo).

    Args:
        concluidos: Registros concluídos.

    Returns:
        Média de ``1 - |estimado - real| / estimado`` limitada a [0, 1];
        ``0.0`` se nenhum registro puder ser avaliado.
    """
    termos: list[float] = []
    for registro in concluidos:
        estimado = registro.esforco_estimado_min
        real = _tempo_execucao_min(registro)
        if estimado is None or real is None or estimado <= 0:
            continue
        termos.append(1.0 - abs(estimado - real) / estimado)
    if not termos:
        return 0.0
    return min(max(fmean(termos), 0.0), 1.0)


def _arredondar(valor: float) -> float:
    """Arredonda para ``CASAS_DECIMAIS`` casas decimais."""
    return round(valor, CASAS_DECIMAIS)


def _calcular_metricas(registros: Sequence[RegistroTarefa]) -> MetricasSegmento:
    """Calcula as métricas estatísticas de um conjunto de registros.

    Args:
        registros: Registros (de qualquer estado) do lote ou de um segmento.

    Returns:
        Métricas arredondadas a 2 casas decimais; zeradas quando não há
        registros concluídos.
    """
    concluidos = _concluidos(registros)
    tempos = _tempos_execucao(concluidos)
    media = _media(tempos)
    desvio = _desvio_padrao(tempos, media)
    return {
        "tempo_medio_execucao_min": _arredondar(media),
        "tempo_mediano_execucao_min": _arredondar(_mediana(tempos)),
        "desvio_padrao_execucao_min": _arredondar(desvio),
        "taxa_atraso": _arredondar(_taxa_atraso(concluidos)),
        "tarefas_atipicas": _contar_atipicas(tempos, media, desvio),
        "indice_acuracia_estimativa": _arredondar(_indice_acuracia(concluidos)),
    }


def _indicadores_por_peso(
    lote: Sequence[RegistroTarefa],
) -> dict[int, MetricasSegmento]:
    """Calcula as métricas segmentadas por peso (chaves 1, 2 e 3).

    Args:
        lote: Registros validados.

    Returns:
        Dicionário ``peso -> métricas``, sempre com os três pesos.
    """
    return {
        peso: _calcular_metricas([r for r in lote if r.peso == peso])
        for peso in PESOS_VALIDOS
    }


def _indicadores_por_equipe(
    lote: Sequence[RegistroTarefa],
) -> dict[str, MetricasSegmento]:
    """Calcula as métricas segmentadas por equipe informada.

    Args:
        lote: Registros validados.

    Returns:
        Dicionário ``equipe -> métricas`` em ordem alfabética; vazio se nenhum
        registro tiver equipe. Registros sem equipe não entram em nenhum
        segmento.
    """
    equipes = sorted({r.equipe for r in lote if r.equipe is not None})
    return {
        equipe: _calcular_metricas([r for r in lote if r.equipe == equipe])
        for equipe in equipes
    }


def _contar_sem_inicio_execucao(lote: Sequence[RegistroTarefa]) -> int:
    """Conta os concluídos sem ``execucao_iniciada`` preenchida.

    Args:
        lote: Registros validados.

    Returns:
        Quantidade de registros concluídos excluídos do tempo de execução.
    """
    return sum(1 for r in _concluidos(lote) if r.execucao_iniciada is None)


# ---------------------------------------------------------------------------
# 3. Logs estruturados (JSON)
# ---------------------------------------------------------------------------
def _registrar_evento(nivel: int, evento: str, **campos: object) -> None:
    """Emite um evento de log cuja mensagem é um objeto JSON.

    Args:
        nivel: Nível do ``logging`` (ex.: ``logging.INFO``).
        evento: Nome curto do evento.
        **campos: Dados adicionais serializados no JSON.
    """
    payload = {"modulo": "taskanalyzer", "evento": evento, **campos}
    logger.log(nivel, json.dumps(payload, ensure_ascii=False, default=str))


def _sinalizar_registros_incompletos(lote: Sequence[RegistroTarefa]) -> None:
    """Registra em log os concluídos excluídos de alguma métrica.

    Garante que nenhum registro seja descartado em silêncio (contrato,
    seção 1.3.3).

    Args:
        lote: Registros validados.
    """
    for registro in _concluidos(lote):
        if registro.execucao_iniciada is None:
            _registrar_evento(
                logging.WARNING,
                "concluido_sem_inicio_execucao",
                codigo=registro.codigo,
                efeito="excluido do tempo de execucao",
            )
        if registro.execucao_finalizada is None:
            _registrar_evento(
                logging.WARNING,
                "concluido_sem_finalizacao",
                codigo=registro.codigo,
                efeito="excluido do tempo de execucao e da taxa de atraso",
            )
        estimado = registro.esforco_estimado_min
        if estimado is not None and estimado <= 0:
            _registrar_evento(
                logging.WARNING,
                "estimativa_nao_positiva",
                codigo=registro.codigo,
                efeito="excluido do indice de acuracia",
            )
