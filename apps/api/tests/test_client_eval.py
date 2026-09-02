"""Avaliação pública por token — PAR-03.

É a única superfície do sistema aberta na internet, e os testes aqui olham para as
propriedades que protegem isso: recusa indistinguível, idempotência do duplo clique,
sinalização de conteúdo negativo e mascaramento do WhatsApp.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.contexts.client_eval.models import (
    ClientEvalFormQuestion,
    ClientEvaluation,
    mascarar_whatsapp,
)
from app.contexts.client_eval.router import _motivacoes_ligadas
from app.contexts.client_eval.schemas import EvaluationOut, PublicSubmitIn
from app.contexts.client_eval.service import (
    NOTA_NEGATIVA_PADRAO,
    PoliticaDeSinalizacao,
    PublicEvaluationService,
)
from app.core.errors import NotFoundError, ValidationError


class FakeOutbox:
    def __init__(self) -> None:
        self.topicos: list[str] = []

    async def enqueue(self, *, topic: str, payload: dict, idempotency_key: str) -> bool:
        self.topicos.append(topic)
        return True


class FakePublicRepository:
    """Reproduz o UPDATE condicional atômico do banco.

    O ponto do dublê é justamente esse: `reivindicar_para_submissao` decide num passo só
    quem grava, e devolve `None` para quem chegou depois.
    """

    def __init__(
        self, avaliacao: ClientEvaluation | None, perguntas: list[ClientEvalFormQuestion]
    ) -> None:
        self.avaliacao = avaliacao
        self.perguntas = perguntas
        self.respostas: list[tuple[UUID, int | None, str | None]] = []
        self.adicionadas: list[ClientEvaluation] = []

    async def get_por_token(self, token: str) -> ClientEvaluation | None:
        if self.avaliacao is not None and self.avaliacao.token == token:
            return self.avaliacao
        return None

    async def marcar_em_andamento(self, token: str) -> int:
        if self.avaliacao is not None and self.avaliacao.status == "pending":
            self.avaliacao.status = "in_progress"
            return 1
        return 0

    async def reivindicar_para_submissao(self, token: str) -> ClientEvaluation | None:
        a = self.avaliacao
        if a is None or a.token != token:
            return None
        if a.status not in ("pending", "in_progress"):
            return None
        if a.token_expires_at is None or a.token_expires_at <= datetime.now(UTC):
            return None
        a.status = "submitted"
        a.submitted_at = datetime.now(UTC)
        return a

    async def perguntas_do_formulario(
        self, tenant_id: UUID, form_id: UUID
    ) -> list[ClientEvalFormQuestion]:
        return list(self.perguntas)

    def registrar_resposta(
        self, *, tenant_id: UUID, evaluation_id: UUID, question_id: UUID, rating_value, text_value
    ) -> None:
        self.respostas.append((question_id, rating_value, text_value))

    def adicionar(self, avaliacao: ClientEvaluation) -> ClientEvaluation:
        avaliacao.id = avaliacao.id or uuid4()
        self.adicionadas.append(avaliacao)
        return avaliacao

    async def flush(self) -> None: ...


def _pergunta(tipo: str = "textarea", obrigatoria: bool = True) -> ClientEvalFormQuestion:
    return ClientEvalFormQuestion(
        id=uuid4(),
        tenant_id=uuid4(),
        form_id=uuid4(),
        question_text="Como foi o atendimento?",
        question_type=tipo,
        is_required=obrigatoria,
        display_order=0,
    )


def _avaliacao(status: str = "pending", validade_em_dias: int = 10) -> ClientEvaluation:
    return ClientEvaluation(
        id=uuid4(),
        tenant_id=uuid4(),
        target_user_id=uuid4(),
        form_id=uuid4(),
        flow_type="requested",
        token="token-de-teste",
        token_expires_at=datetime.now(UTC) + timedelta(days=validade_em_dias),
        status=status,
    )


def _service(
    repo: FakePublicRepository,
    politica: PoliticaDeSinalizacao | None = None,
    outbox: FakeOutbox | None = None,
) -> PublicEvaluationService:
    fila = outbox or FakeOutbox()
    return PublicEvaluationService(
        repo,  # type: ignore[arg-type]
        lambda _tenant_id: fila,
        politica or PoliticaDeSinalizacao(),
    )


# ---------------------------------------------------------------- abertura


async def test_token_valido_abre_o_formulario_na_ordem() -> None:
    avaliacao = _avaliacao()
    perguntas = [_pergunta(), _pergunta(tipo="rating")]
    repo = FakePublicRepository(avaliacao, perguntas)

    _, devolvidas = await _service(repo).open_by_token("token-de-teste")

    assert [q.id for q in devolvidas] == [q.id for q in perguntas]
    assert avaliacao.status == "in_progress", "abrir registra que o cliente chegou"


@pytest.mark.parametrize(
    "cenario",
    ["inexistente", "expirado", "ja_respondido", "expirado_pelo_job"],
)
async def test_recusas_sao_indistinguiveis(cenario: str) -> None:
    """O link circula por WhatsApp: quem tem um token velho não descobre nada por aqui."""
    avaliacoes = {
        "inexistente": None,
        "expirado": _avaliacao(validade_em_dias=-1),
        "ja_respondido": _avaliacao(status="submitted"),
        "expirado_pelo_job": _avaliacao(status="expired"),
    }
    repo = FakePublicRepository(avaliacoes[cenario], [_pergunta()])

    with pytest.raises(NotFoundError) as exc:
        await _service(repo).open_by_token("token-de-teste")

    assert exc.value.message == "Link inválido ou expirado"


# ---------------------------------------------------------------- submissão


async def test_submissao_valida_persiste_e_confirma() -> None:
    avaliacao = _avaliacao()
    pergunta = _pergunta()
    repo = FakePublicRepository(avaliacao, [pergunta])
    outbox = FakeOutbox()

    resultado = await _service(repo, outbox=outbox).submit_by_token(
        "token-de-teste",
        respostas={pergunta.id: (None, "Excelente atendimento")},
        client_name="Cliente Teste",
        overall_rating=5,
    )

    assert resultado.ja_respondida is False
    assert avaliacao.status == "submitted"
    assert avaliacao.submitted_at is not None
    assert avaliacao.client_name == "Cliente Teste"
    assert repo.respostas == [(pergunta.id, None, "Excelente atendimento")]
    assert outbox.topicos == ["client_eval.submitted"]


async def test_segunda_submissao_devolve_a_mesma_confirmacao() -> None:
    """PAR-03 @idempotencia: o duplo clique do cliente não é erro dele."""
    avaliacao = _avaliacao()
    pergunta = _pergunta()
    repo = FakePublicRepository(avaliacao, [pergunta])
    outbox = FakeOutbox()
    service = _service(repo, outbox=outbox)

    primeira = await service.submit_by_token(
        "token-de-teste", respostas={pergunta.id: (None, "ótimo")}
    )
    segunda = await service.submit_by_token(
        "token-de-teste", respostas={pergunta.id: (None, "ótimo de novo")}
    )

    assert primeira.ja_respondida is False
    assert segunda.ja_respondida is True
    assert segunda.evaluation.id == avaliacao.id
    assert len(repo.respostas) == 1, "a segunda não grava nada"
    assert outbox.topicos == ["client_eval.submitted"], "nem enfileira de novo"


async def test_submissao_com_link_expirado_e_recusada() -> None:
    repo = FakePublicRepository(_avaliacao(validade_em_dias=-1), [_pergunta()])

    with pytest.raises(NotFoundError):
        await _service(repo).submit_by_token("token-de-teste", respostas={})


async def test_obrigatoria_em_branco_recusa() -> None:
    avaliacao = _avaliacao()
    obrigatoria, opcional = _pergunta(), _pergunta(obrigatoria=False)
    repo = FakePublicRepository(avaliacao, [obrigatoria, opcional])

    with pytest.raises(ValidationError) as exc:
        await _service(repo).submit_by_token(
            "token-de-teste", respostas={opcional.id: (None, "só a opcional")}
        )

    assert str(obrigatoria.id) in exc.value.details["question_ids"]


async def test_pergunta_de_outro_formulario_e_recusada() -> None:
    repo = FakePublicRepository(_avaliacao(), [_pergunta()])

    with pytest.raises(ValidationError):
        await _service(repo).submit_by_token("token-de-teste", respostas={uuid4(): (5, None)})


# ---------------------------------------------------------------- sinalização


async def test_nota_baixa_sinaliza() -> None:
    """BR-MIGRAR-021: alguém precisa ligar para esse cliente hoje."""
    avaliacao = _avaliacao()
    pergunta = _pergunta(tipo="rating")
    repo = FakePublicRepository(avaliacao, [pergunta])
    outbox = FakeOutbox()

    await _service(repo, PoliticaDeSinalizacao(nota_maxima=2), outbox).submit_by_token(
        "token-de-teste", respostas={pergunta.id: (1, None)}
    )

    assert avaliacao.has_negative is True
    assert outbox.topicos == ["client_eval.submitted", "client_eval.flagged_negative"]


async def test_nota_alta_nao_sinaliza() -> None:
    avaliacao = _avaliacao()
    pergunta = _pergunta(tipo="rating")
    repo = FakePublicRepository(avaliacao, [pergunta])
    outbox = FakeOutbox()

    await _service(repo, PoliticaDeSinalizacao(nota_maxima=2), outbox).submit_by_token(
        "token-de-teste", respostas={pergunta.id: (5, None)}
    )

    assert avaliacao.has_negative is False
    assert outbox.topicos == ["client_eval.submitted"]


async def test_palavra_negativa_sinaliza_sem_acento_e_sem_caixa() -> None:
    """"Péssimo" e "PESSIMO" são a mesma reclamação."""
    avaliacao = _avaliacao()
    pergunta = _pergunta()
    repo = FakePublicRepository(avaliacao, [pergunta])
    politica = PoliticaDeSinalizacao(nota_maxima=2, palavras=("péssimo", "demora"))

    await _service(repo, politica).submit_by_token(
        "token-de-teste", respostas={pergunta.id: (None, "Atendimento PESSIMO do começo ao fim")}
    )

    assert avaliacao.has_negative is True


async def test_politica_le_o_catalogo_de_settings() -> None:
    politica = PoliticaDeSinalizacao.de_settings(
        {
            "client_eval_negative_keywords": '["ruim", "demorado"]',
            "client_eval_negative_rating_max": "3",
        }
    )

    assert politica.nota_maxima == 3
    assert politica.sinaliza(notas=[3], textos=[])
    assert politica.sinaliza(notas=[5], textos=["achei demorado"])
    assert not politica.sinaliza(notas=[4], textos=["tudo certo"])


def test_configuracao_quebrada_nao_derruba_a_submissao() -> None:
    """O pior caso aceitável é deixar de sinalizar, nunca recusar a avaliação."""
    politica = PoliticaDeSinalizacao.de_settings(
        {
            "client_eval_negative_keywords": "{isto não é json",
            "client_eval_negative_rating_max": "x",
        }
    )

    assert politica.palavras == ()
    assert politica.nota_maxima == NOTA_NEGATIVA_PADRAO
    assert not politica.sinaliza(notas=[9], textos=["qualquer coisa"])


# ---------------------------------------------------------------- espontâneo


async def test_espontaneo_desligado_recusa() -> None:
    """AMB-002: endpoint que cria registro sem convite é superfície de spam."""
    repo = FakePublicRepository(None, [_pergunta()])

    with pytest.raises(ValidationError) as exc:
        await _service(repo).criar_espontanea(
            tenant_id=uuid4(),
            form_id=uuid4(),
            target_user_id=uuid4(),
            habilitado=False,
            respostas={},
        )

    assert exc.value.details["chave"] == "client_eval_spontaneous_enabled"
    assert repo.adicionadas == []


async def test_espontaneo_ligado_grava_direto_como_submitted() -> None:
    pergunta = _pergunta()
    repo = FakePublicRepository(None, [pergunta])
    outbox = FakeOutbox()

    avaliacao = await _service(repo, outbox=outbox).criar_espontanea(
        tenant_id=uuid4(),
        form_id=pergunta.form_id,
        target_user_id=uuid4(),
        habilitado=True,
        respostas={pergunta.id: (None, "passei para elogiar")},
    )

    assert avaliacao.flow_type == "spontaneous"
    assert avaliacao.status == "submitted"
    assert avaliacao.token is None, "sem convite não há token para reivindicar"
    assert outbox.topicos == ["client_eval.submitted"]


# ---------------------------------------------------------------- serialização


@pytest.mark.parametrize(
    "numero,esperado",
    [
        ("11987654321", "*******4321"),
        ("+55 (11) 98765-4321", "*********4321"),
        ("1234", "****"),
        ("", ""),
        (None, None),
    ],
)
def test_mascaramento_preserva_os_quatro_ultimos(numero, esperado) -> None:
    assert mascarar_whatsapp(numero) == esperado


def test_serializacao_mascara_por_padrao() -> None:
    """BR-MIGRAR-022: o número bruto não sai da API sem permissão explícita."""
    avaliacao = _avaliacao()
    avaliacao.client_whatsapp = "11987654321"
    avaliacao.created_at = datetime.now(UTC)
    # Objeto que nunca passou pelo banco: defaults de coluna só valem no INSERT.
    avaliacao.has_negative = False

    mascarada = EvaluationOut.de_modelo(avaliacao)
    completa = EvaluationOut.de_modelo(avaliacao, whatsapp_completo=True)

    assert mascarada.client_whatsapp == "*******4321"
    assert completa.client_whatsapp == "11987654321"


@pytest.mark.parametrize(
    "status,exibicao",
    [
        ("pending", "pendente"),
        ("in_progress", "pendente"),
        ("submitted", "respondido"),
        ("expired", "expirado"),
    ],
)
def test_mapa_de_status_para_exibicao(status: str, exibicao: str) -> None:
    """BR-MIGRAR-022: `in_progress` e `pending` são a mesma coisa para quem olha a lista."""
    avaliacao = _avaliacao(status=status)
    assert avaliacao.status_exibicao == exibicao


# ---------------------------------------------------------------- wizard público


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        (None, ["praise", "evaluate", "problem", "other"]),
        ("", ["praise", "evaluate", "problem", "other"]),
        ('{"praise":true,"evaluate":true,"problem":true,"other":true}',
         ["praise", "evaluate", "problem", "other"]),
        ('{"praise":false,"problem":true}', ["evaluate", "problem", "other"]),
        ('{"praise":false,"evaluate":false,"problem":false,"other":false}', []),
        ("{isto não é json", ["praise", "evaluate", "problem", "other"]),
        ('["praise"]', ["praise", "evaluate", "problem", "other"]),
    ],
)
def test_motivacoes_ligadas(bruto: str | None, esperado: list[str]) -> None:
    """Etapa 2 do wizard (SCR-0035): o tenant liga e desliga cada motivação.

    Config ausente ou torta libera as quatro — sumir com a etapa por causa de um JSON
    quebrado seria pior que mostrá-la. A ordem é sempre a do legado.
    """
    assert _motivacoes_ligadas({"client_feedback_motivations": bruto}) == esperado


def test_nota_geral_aceita_a_escala_de_zero_a_dez() -> None:
    """O wizard manda estrelas 0–10, a mesma escala que os relatórios exibem (DEV-A12)."""
    assert PublicSubmitIn(overall_rating=0).overall_rating == 0
    assert PublicSubmitIn(overall_rating=10).overall_rating == 10
    with pytest.raises(PydanticValidationError):
        PublicSubmitIn(overall_rating=11)
