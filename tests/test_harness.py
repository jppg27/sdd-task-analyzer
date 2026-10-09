"""Test Harness do TaskAnalyzer (pytest).

Traduz diretamente os Cenários de Aceite da especificação SDD (seção 2.1) em
testes automatizados. Rastreabilidade:

* ``TestCenario1Sucesso``   -> Cenário 1 (estatísticas completas)
* ``TestCenario2Excecoes``  -> Cenário 2 (entradas inválidas)
* ``TestCenario3Outlier``   -> Cenário 3 (detecção de anomalia)
* ``TestCenario4Borda``     -> Cenário 4 (nenhum concluído / lote vazio)
* ``TestContratoComplementar`` -> demais regras de negócio da seção 1.3.3

Os valores esperados foram calculados manualmente (e conferidos por revisão
humana) a partir dos lotes definidos em ``fixtures_dados.py``.
"""

import json
import logging
from datetime import UTC, datetime, timedelta, timezone

import pytest

from analisador import analyze_tasks
from excecoes import (
    CronologiaInvalidaError,
    FormatoCodigoInvalidoError,
    PesoForaDoIntervaloError,
    TaskValidationError,
)
from fixtures_dados import T0, criar_concluido, criar_registro, em
from modelos import EstadoTarefa, MetricasSegmento, RegistroTarefa

# Registra os fixtures de fixtures_dados.py (lotes dos cenários) neste módulo.
pytest_plugins = ["fixtures_dados"]

METRICAS_ZERADAS: MetricasSegmento = {
    "tempo_medio_execucao_min": 0.0,
    "tempo_mediano_execucao_min": 0.0,
    "desvio_padrao_execucao_min": 0.0,
    "taxa_atraso": 0.0,
    "tarefas_atipicas": 0,
    "indice_acuracia_estimativa": 0.0,
}

CAMPOS_SAIDA: set[str] = {
    *METRICAS_ZERADAS,
    "indicadores_por_peso",
    "indicadores_por_equipe",
    "total_registros_processados",
    "registros_sem_inicio_execucao",
}


# ---------------------------------------------------------------------------
# Cenário 1 - Sucesso (estatísticas completas)
# ---------------------------------------------------------------------------
class TestCenario1Sucesso:
    """Dado um lote válido variado, o TaskAnalyzer retorna todas as métricas."""

    def test_retorna_exatamente_os_campos_do_contrato(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """A saída contém todos (e apenas) os campos da seção 1.3.2."""
        assert set(analyze_tasks(lote_sucesso)) == CAMPOS_SAIDA

    def test_tempo_medio_mediano_e_desvio_padrao(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """Tempos [120, 60, 90, 30]: média 75, mediana 75, desvio 33,54."""
        resultado = analyze_tasks(lote_sucesso)
        assert resultado["tempo_medio_execucao_min"] == 75.0
        assert resultado["tempo_mediano_execucao_min"] == 75.0
        assert resultado["desvio_padrao_execucao_min"] == 33.54

    def test_taxa_atraso_considera_apenas_concluidos(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """2 atrasados (TSK-0002, TSK-0004) em 5 concluídos = 40%.

        TSK-0008 (cancelada) terminou após o vencimento, mas não é contada.
        """
        assert analyze_tasks(lote_sucesso)["taxa_atraso"] == 40.0

    def test_indice_acuracia_apenas_com_estimativa(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """Média de (0,80; 1,00; 0,75) = 0,85; TSK-0003 e TSK-0005 ficam fora."""
        assert analyze_tasks(lote_sucesso)["indice_acuracia_estimativa"] == 0.85

    def test_sem_tarefas_atipicas_no_lote_regular(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """Nenhum tempo ultrapassa 75 + 2 × 33,54 = 142,08 min."""
        assert analyze_tasks(lote_sucesso)["tarefas_atipicas"] == 0

    def test_totais_de_registros(self, lote_sucesso: list[RegistroTarefa]) -> None:
        """8 registros processados; 1 concluído sem início (TSK-0005)."""
        resultado = analyze_tasks(lote_sucesso)
        assert resultado["total_registros_processados"] == 8
        assert resultado["registros_sem_inicio_execucao"] == 1

    def test_indicadores_por_peso(self, lote_sucesso: list[RegistroTarefa]) -> None:
        """Métricas segmentadas pelos pesos 1, 2 e 3."""
        esperado: dict[int, MetricasSegmento] = {
            1: {
                "tempo_medio_execucao_min": 30.0,
                "tempo_mediano_execucao_min": 30.0,
                "desvio_padrao_execucao_min": 0.0,
                "taxa_atraso": 100.0,
                "tarefas_atipicas": 0,
                "indice_acuracia_estimativa": 0.75,
            },
            2: {
                "tempo_medio_execucao_min": 90.0,
                "tempo_mediano_execucao_min": 90.0,
                "desvio_padrao_execucao_min": 0.0,
                "taxa_atraso": 0.0,
                "tarefas_atipicas": 0,
                "indice_acuracia_estimativa": 0.0,
            },
            3: {
                "tempo_medio_execucao_min": 90.0,
                "tempo_mediano_execucao_min": 90.0,
                "desvio_padrao_execucao_min": 30.0,
                "taxa_atraso": 50.0,
                "tarefas_atipicas": 0,
                "indice_acuracia_estimativa": 0.9,
            },
        }
        assert analyze_tasks(lote_sucesso)["indicadores_por_peso"] == esperado

    def test_indicadores_por_equipe(self, lote_sucesso: list[RegistroTarefa]) -> None:
        """Segmentação apenas das equipes informadas (TSK-0004 não tem equipe)."""
        esperado: dict[str, MetricasSegmento] = {
            "Dados": {
                "tempo_medio_execucao_min": 90.0,
                "tempo_mediano_execucao_min": 90.0,
                "desvio_padrao_execucao_min": 30.0,
                "taxa_atraso": 50.0,
                "tarefas_atipicas": 0,
                "indice_acuracia_estimativa": 0.9,
            },
            "Plataforma": {
                "tempo_medio_execucao_min": 90.0,
                "tempo_mediano_execucao_min": 90.0,
                "desvio_padrao_execucao_min": 0.0,
                "taxa_atraso": 0.0,
                "tarefas_atipicas": 0,
                "indice_acuracia_estimativa": 0.0,
            },
        }
        assert analyze_tasks(lote_sucesso)["indicadores_por_equipe"] == esperado

    def test_tipos_da_saida(self, lote_sucesso: list[RegistroTarefa]) -> None:
        """Métricas de tempo, taxa e índice são float; contagens são int."""
        resultado: dict[str, object] = dict(analyze_tasks(lote_sucesso))
        for campo in (
            "tempo_medio_execucao_min",
            "tempo_mediano_execucao_min",
            "desvio_padrao_execucao_min",
            "taxa_atraso",
            "indice_acuracia_estimativa",
        ):
            assert type(resultado[campo]) is float
        for campo in (
            "tarefas_atipicas",
            "total_registros_processados",
            "registros_sem_inicio_execucao",
        ):
            assert type(resultado[campo]) is int

    def test_aceita_qualquer_iteravel(self, lote_sucesso: list[RegistroTarefa]) -> None:
        """Um gerador produz o mesmo resultado que a lista."""
        assert analyze_tasks(r for r in lote_sucesso) == analyze_tasks(lote_sucesso)

    def test_ordem_do_lote_nao_altera_resultado(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """O resultado independe da ordem dos registros."""
        assert analyze_tasks(reversed(lote_sucesso)) == analyze_tasks(lote_sucesso)


# ---------------------------------------------------------------------------
# Cenário 2 - Exceção / Erro (entradas inválidas)
# ---------------------------------------------------------------------------
class TestCenario2Excecoes:
    """Dado um registro inválido, o TaskAnalyzer dispara a exceção específica."""

    @pytest.mark.parametrize(
        "codigo",
        [
            "TSK-12",
            "TSK-00012",
            "tsk-0001",
            "TASK-0001",
            "TSK_0001",
            " TSK-0001",
            "TSK-0001 ",
            "TSK-00A1",
            "",
            "TSK-٠١٢٣",
        ],
    )
    def test_codigo_fora_do_padrao(self, codigo: str) -> None:
        """Código que não é exatamente 'TSK-' + 4 dígitos ASCII é rejeitado."""
        lote = [criar_registro(codigo=codigo)]
        with pytest.raises(FormatoCodigoInvalidoError, match="padrão"):
            analyze_tasks(lote)

    def test_codigo_nao_textual(self) -> None:
        """Código de tipo diferente de str é rejeitado."""
        with pytest.raises(FormatoCodigoInvalidoError):
            analyze_tasks([criar_registro(codigo=1234)])

    def test_codigo_duplicado_no_lote(self) -> None:
        """Dois registros com o mesmo código geram erro de formato."""
        lote = [criar_registro(codigo="TSK-0001"), criar_registro(codigo="TSK-0001")]
        with pytest.raises(FormatoCodigoInvalidoError, match="duplicado"):
            analyze_tasks(lote)

    @pytest.mark.parametrize("peso", [0, 4, -1, 10, 2.0, 2.5, "2", None, True])
    def test_peso_fora_do_intervalo(self, peso: object) -> None:
        """Peso que não é inteiro entre 1 e 3 gera PesoForaDoIntervaloError."""
        with pytest.raises(PesoForaDoIntervaloError, match="peso"):
            analyze_tasks([criar_registro(peso=peso)])

    def test_finalizacao_anterior_ao_inicio(self) -> None:
        """execucao_finalizada < execucao_iniciada é cronologia inválida."""
        registro = criar_concluido("TSK-0001", 60, 30)
        with pytest.raises(
            CronologiaInvalidaError, match="anterior à execucao_iniciada"
        ):
            analyze_tasks([registro])

    def test_inicio_anterior_a_abertura(self) -> None:
        """execucao_iniciada < abertura é cronologia inválida."""
        registro = criar_concluido("TSK-0001", -10, 30)
        with pytest.raises(CronologiaInvalidaError, match="anterior à abertura"):
            analyze_tasks([registro])

    def test_conclusao_anterior_a_abertura_sem_inicio(self) -> None:
        """Data de conclusão anterior à data de criação (abertura) é inválida."""
        registro = criar_concluido("TSK-0001", None, -5)
        with pytest.raises(
            CronologiaInvalidaError, match="finalizada anterior à abertura"
        ):
            analyze_tasks([registro])

    def test_registro_invalido_no_meio_do_lote(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """Um único registro inválido em qualquer posição interrompe a análise."""
        lote = [
            *lote_sucesso[:4],
            criar_registro(codigo="TSK-0099", peso=7),
            *lote_sucesso[4:],
        ]
        with pytest.raises(PesoForaDoIntervaloError):
            analyze_tasks(lote)

    def test_validacao_vale_para_registros_nao_concluidos(self) -> None:
        """Registros abertos também são validados (nunca falha silenciosa)."""
        registro = criar_registro(estado=EstadoTarefa.ABERTA, execucao_iniciada=em(-1))
        with pytest.raises(CronologiaInvalidaError):
            analyze_tasks([registro])

    @pytest.mark.parametrize(
        ("registro", "classe"),
        [
            (criar_registro(codigo="X"), FormatoCodigoInvalidoError),
            (criar_registro(peso=9), PesoForaDoIntervaloError),
            (criar_concluido("TSK-0001", 10, 5), CronologiaInvalidaError),
        ],
    )
    def test_excecoes_herdam_de_task_validation_error(
        self, registro: RegistroTarefa, classe: type[TaskValidationError]
    ) -> None:
        """Todas as exceções podem ser capturadas pela base TaskValidationError."""
        with pytest.raises(TaskValidationError) as info:
            analyze_tasks([registro])
        assert type(info.value) is classe
        assert isinstance(info.value, ValueError)

    def test_mensagem_clara_com_codigo_e_motivo(self) -> None:
        """A mensagem identifica o registro e a regra violada."""
        with pytest.raises(PesoForaDoIntervaloError) as info:
            analyze_tasks([criar_registro(codigo="TSK-0042", peso=5)])
        assert info.value.codigo == "TSK-0042"
        assert str(info.value) == (
            "Registro 'TSK-0042': peso 5 inválido; esperado inteiro entre 1 e 3."
        )


# ---------------------------------------------------------------------------
# Cenário 3 - Detecção de anomalia (outlier)
# ---------------------------------------------------------------------------
class TestCenario3Outlier:
    """Dado um tempo muito acima dos demais, ele é contado como atípico."""

    def test_outlier_contabilizado(
        self, lote_com_outlier: list[RegistroTarefa]
    ) -> None:
        """600 min > 114 + 2 × 162 = 438 min, logo 1 tarefa atípica."""
        resultado = analyze_tasks(lote_com_outlier)
        assert resultado["tempo_medio_execucao_min"] == 114.0
        assert resultado["desvio_padrao_execucao_min"] == 162.0
        assert resultado["tarefas_atipicas"] == 1

    def test_mediana_permanece_estavel(
        self,
        lote_sem_outlier: list[RegistroTarefa],
        lote_com_outlier: list[RegistroTarefa],
    ) -> None:
        """A mediana (60 min) não é distorcida pelo outlier."""
        sem = analyze_tasks(lote_sem_outlier)
        com = analyze_tasks(lote_com_outlier)
        assert sem["tempo_mediano_execucao_min"] == 60.0
        assert com["tempo_mediano_execucao_min"] == 60.0

    def test_lote_homogeneo_nao_tem_outlier(
        self, lote_sem_outlier: list[RegistroTarefa]
    ) -> None:
        """Sem variabilidade (desvio 0) não há tarefas atípicas."""
        resultado = analyze_tasks(lote_sem_outlier)
        assert resultado["desvio_padrao_execucao_min"] == 0.0
        assert resultado["tarefas_atipicas"] == 0

    def test_outlier_aparece_no_segmento_correspondente(
        self, lote_com_outlier: list[RegistroTarefa]
    ) -> None:
        """Todos têm peso 2, então o outlier aparece no segmento do peso 2."""
        por_peso = analyze_tasks(lote_com_outlier)["indicadores_por_peso"]
        assert por_peso[2]["tarefas_atipicas"] == 1
        assert por_peso[1] == METRICAS_ZERADAS
        assert por_peso[3] == METRICAS_ZERADAS

    def test_valor_no_limite_nao_e_atipico(self) -> None:
        """Somente valores estritamente acima de média + 2σ são atípicos.

        Tempos [0, 0, 0, 0, 10]: média 2, σ 4, limite 10 - o valor 10 não
        ultrapassa o limite.
        """
        lote = [criar_concluido(f"TSK-{i:04d}", 0, 0) for i in range(1, 5)]
        lote.append(criar_concluido("TSK-0005", 0, 10))
        resultado = analyze_tasks(lote)
        assert resultado["tempo_medio_execucao_min"] == 2.0
        assert resultado["desvio_padrao_execucao_min"] == 4.0
        assert resultado["tarefas_atipicas"] == 0


# ---------------------------------------------------------------------------
# Cenário 4 - Borda (nenhum registro concluído / lote vazio)
# ---------------------------------------------------------------------------
class TestCenario4Borda:
    """Sem concluídos, todas as métricas numéricas são zeradas, sem exceção."""

    def test_apenas_pendentes_retorna_metricas_zeradas(
        self, lote_sem_concluidos: list[RegistroTarefa]
    ) -> None:
        """Aberta, em andamento e cancelada: métricas zeradas e total = 3."""
        resultado: dict[str, object] = dict(analyze_tasks(lote_sem_concluidos))
        for campo, valor in METRICAS_ZERADAS.items():
            assert resultado[campo] == valor
            assert type(resultado[campo]) is type(valor)
        assert resultado["total_registros_processados"] == 3
        assert resultado["registros_sem_inicio_execucao"] == 0

    def test_apenas_pendentes_segmentos_zerados(
        self, lote_sem_concluidos: list[RegistroTarefa]
    ) -> None:
        """Indicadores por peso e por equipe também são zerados."""
        resultado = analyze_tasks(lote_sem_concluidos)
        assert resultado["indicadores_por_peso"] == {
            1: METRICAS_ZERADAS,
            2: METRICAS_ZERADAS,
            3: METRICAS_ZERADAS,
        }
        assert resultado["indicadores_por_equipe"] == {"Dados": METRICAS_ZERADAS}

    def test_lote_vazio(self) -> None:
        """Lote vazio: métricas zeradas, total 0 e nenhuma equipe."""
        resultado = analyze_tasks([])
        saida: dict[str, object] = dict(resultado)
        for campo, valor in METRICAS_ZERADAS.items():
            assert saida[campo] == valor
        assert resultado["total_registros_processados"] == 0
        assert resultado["registros_sem_inicio_execucao"] == 0
        assert resultado["indicadores_por_equipe"] == {}
        assert set(resultado["indicadores_por_peso"]) == {1, 2, 3}

    def test_concluidos_todos_sem_inicio(self) -> None:
        """Concluídos sem início: sem tempo de execução, mas contados."""
        lote = [
            criar_concluido("TSK-0001", None, 30, vencimento=em(10)),
            criar_concluido("TSK-0002", None, 30, vencimento=em(60)),
        ]
        resultado = analyze_tasks(lote)
        assert resultado["tempo_medio_execucao_min"] == 0.0
        assert resultado["registros_sem_inicio_execucao"] == 2
        assert resultado["taxa_atraso"] == 50.0

    def test_estimativa_zero_nao_divide_por_zero(self) -> None:
        """esforco_estimado_min = 0 é ignorado no índice (sem ZeroDivisionError)."""
        lote = [criar_concluido("TSK-0001", 0, 30, esforco_estimado_min=0)]
        assert analyze_tasks(lote)["indice_acuracia_estimativa"] == 0.0

    def test_concluido_sem_finalizacao(self) -> None:
        """Concluído sem execucao_finalizada fica fora do tempo e do atraso."""
        lote = [
            criar_registro(
                codigo="TSK-0001",
                estado=EstadoTarefa.CONCLUIDA,
                execucao_iniciada=em(0),
            ),
            criar_concluido("TSK-0002", 0, 30, vencimento=em(20)),
        ]
        resultado = analyze_tasks(lote)
        assert resultado["tempo_medio_execucao_min"] == 30.0
        assert resultado["taxa_atraso"] == 100.0
        assert resultado["registros_sem_inicio_execucao"] == 0


# ---------------------------------------------------------------------------
# Regras complementares do contrato (seção 1.3.3) e governança
# ---------------------------------------------------------------------------
class TestContratoComplementar:
    """Regras de negócio adicionais e requisitos do CONTEXT_RULES."""

    def test_indice_acuracia_limitado_a_zero(self) -> None:
        """Estimativas muito distantes do real não geram índice negativo."""
        lote = [criar_concluido("TSK-0001", 0, 300, esforco_estimado_min=10)]
        assert analyze_tasks(lote)["indice_acuracia_estimativa"] == 0.0

    def test_indice_acuracia_perfeito(self) -> None:
        """Estimativa igual ao tempo real resulta em índice 1."""
        lote = [criar_concluido("TSK-0001", 0, 45, esforco_estimado_min=45)]
        assert analyze_tasks(lote)["indice_acuracia_estimativa"] == 1.0

    def test_arredondamento_duas_casas(self) -> None:
        """Tempos [10, 20, 20] têm média 16,666... arredondada para 16,67."""
        lote = [
            criar_concluido("TSK-0001", 0, 10),
            criar_concluido("TSK-0002", 0, 20),
            criar_concluido("TSK-0003", 0, 20),
        ]
        resultado = analyze_tasks(lote)
        assert resultado["tempo_medio_execucao_min"] == 16.67
        assert resultado["desvio_padrao_execucao_min"] == 4.71

    def test_conclusao_exatamente_no_vencimento_nao_e_atraso(self) -> None:
        """Atraso exige execucao_finalizada estritamente maior que vencimento."""
        lote = [criar_concluido("TSK-0001", 0, 60, vencimento=em(60))]
        assert analyze_tasks(lote)["taxa_atraso"] == 0.0

    def test_sem_equipe_retorna_dicionario_vazio(
        self, lote_com_outlier: list[RegistroTarefa]
    ) -> None:
        """indicadores_por_equipe é vazio quando nenhuma equipe é informada."""
        assert analyze_tasks(lote_com_outlier)["indicadores_por_equipe"] == {}

    def test_equipe_em_branco_e_tratada_como_ausente(self) -> None:
        """Equipe vazia ou só com espaços não é considerada preenchida."""
        registro = criar_registro(equipe="   ")
        assert registro.equipe is None
        assert analyze_tasks([registro])["indicadores_por_equipe"] == {}

    def test_datas_normalizadas_para_utc(self) -> None:
        """Datas sem fuso são tratadas como UTC; com fuso, convertidas para UTC."""
        brasilia = timezone(timedelta(hours=-3))
        registro = criar_registro(
            abertura=datetime(2026, 9, 1, 8, 0),
            vencimento=datetime(2026, 9, 1, 10, 0, tzinfo=brasilia),
        )
        assert registro.abertura == T0
        assert registro.abertura.tzinfo is UTC
        assert registro.vencimento == datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
        assert registro.vencimento.tzinfo is UTC

    def test_data_com_tipo_invalido(self) -> None:
        """Campos de data devem ser datetime."""
        with pytest.raises(TypeError, match="abertura"):
            criar_registro(abertura="2026-09-01")

    def test_de_dict_com_datas_iso_8601(self) -> None:
        """Registros podem ser criados a partir de texto ISO 8601 (UTC)."""
        registro = RegistroTarefa.de_dict(
            {
                "codigo": "TSK-0001",
                "abertura": "2026-09-01T08:00:00Z",
                "execucao_iniciada": T0,
                "execucao_finalizada": "2026-09-01T06:30:00-03:00",
                "vencimento": "2026-09-01T12:00:00Z",
                "peso": 2,
                "estado": "concluida",
            }
        )
        assert registro.estado is EstadoTarefa.CONCLUIDA
        assert registro.execucao_finalizada == em(90)
        assert analyze_tasks([registro])["tempo_medio_execucao_min"] == 90.0

    def test_estado_invalido(self) -> None:
        """Estado fora do enum é rejeitado na criação do registro."""
        with pytest.raises(ValueError, match="finalizada"):
            criar_registro(estado="finalizada")

    def test_registro_e_imutavel(self) -> None:
        """RegistroTarefa é uma dataclass congelada (frozen=True)."""
        registro = criar_registro()
        with pytest.raises(AttributeError):
            registro.peso = 3  # type: ignore[misc]

    def test_logs_estruturados_em_json(
        self, lote_sucesso: list[RegistroTarefa], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Toda mensagem de log é um objeto JSON com o campo 'evento'."""
        caplog.set_level(logging.INFO, logger="taskanalyzer")
        lote = [
            *lote_sucesso,
            criar_registro(
                codigo="TSK-0100",
                estado=EstadoTarefa.CONCLUIDA,
                execucao_iniciada=em(0),
            ),
            criar_concluido("TSK-0101", 0, 10, esforco_estimado_min=0),
        ]
        analyze_tasks(lote)
        eventos = [json.loads(r.getMessage()) for r in caplog.records]
        nomes = [e["evento"] for e in eventos]
        assert nomes[0] == "analise_iniciada"
        assert nomes[-1] == "analise_concluida"
        assert {
            "concluido_sem_inicio_execucao",
            "concluido_sem_finalizacao",
            "estimativa_nao_positiva",
        } <= set(nomes)
        assert all(e["modulo"] == "taskanalyzer" for e in eventos)

    def test_log_de_erro_de_validacao(self, caplog: pytest.LogCaptureFixture) -> None:
        """Erros de validação são registrados em JSON antes de propagar."""
        caplog.set_level(logging.ERROR, logger="taskanalyzer")
        with pytest.raises(FormatoCodigoInvalidoError):
            analyze_tasks([criar_registro(codigo="ABC")])
        evento = json.loads(caplog.records[-1].getMessage())
        assert evento == {
            "modulo": "taskanalyzer",
            "evento": "registro_invalido",
            "codigo": "ABC",
            "erro": "FormatoCodigoInvalidoError",
            "motivo": "código fora do padrão 'TSK-' seguido de 4 dígitos.",
        }

    def test_execucao_nao_guarda_estado_entre_chamadas(
        self, lote_sucesso: list[RegistroTarefa]
    ) -> None:
        """Chamadas repetidas (inclusive após erro) produzem o mesmo resultado."""
        primeiro = analyze_tasks(lote_sucesso)
        with pytest.raises(TaskValidationError):
            analyze_tasks(
                [criar_registro(codigo="TSK-0001"), criar_registro(codigo="TSK-0001")]
            )
        assert analyze_tasks(lote_sucesso) == primeiro
