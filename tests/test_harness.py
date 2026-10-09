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

import pytest

from analisador import analyze_tasks
from excecoes import (
    CronologiaInvalidaError,
    FormatoCodigoInvalidoError,
    PesoForaDoIntervaloError,
    TaskValidationError,
)
from fixtures_dados import criar_concluido, criar_registro, em
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
