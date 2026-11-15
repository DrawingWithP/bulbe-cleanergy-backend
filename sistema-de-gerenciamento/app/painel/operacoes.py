"""
Camada de Apresentacao, rotas de operacao do painel sobre o app.

Tudo o que o funcionario altera no app passa por aqui e e enviado para a API
do app (app/integracao/api_app.py), que e a fonte da verdade. Depois de cada
alteracao o painel sincroniza na hora, para a tela ja mostrar o resultado.

Rotas (prefixo /v1/painel):
- relogio de demonstracao: GET /demonstracao/relogio, POST .../avancar e .../resetar (admin)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.integracao import api_app, sincronizacao
from app.painel.auth import exigir_admin, funcionario_logado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/painel", tags=["Painel: operacoes no app"])


def erro_http(erro: api_app.ErroApiApp) -> HTTPException:
    """ErroApiApp -> HTTPException no formato {"error": {...}} do painel."""
    return HTTPException(
        status_code=erro.status,
        detail={"error": {"code": erro.code, "message": erro.message, "status": erro.status}},
    )


def no_app(funcao, *args, sincronizar: bool = True, **kwargs):
    """Executa a operacao na API do app e, se der certo, sincroniza o painel."""
    try:
        resultado = funcao(*args, **kwargs)
    except api_app.ErroApiApp as erro:
        raise erro_http(erro) from erro
    if sincronizar:
        sincronizacao.sincronizar_sem_erro()
    return resultado


# ---------------------------------------------------------------------------
# Relogio de demonstracao
# ---------------------------------------------------------------------------
class AvancarRelogio(BaseModel):
    dias: int = Field(..., ge=1, le=60)


@router.get("/demonstracao/relogio", dependencies=[Depends(funcionario_logado)])
def relogio() -> dict:
    """Data que a API do app esta usando (com os dias adiantados)."""
    return no_app(api_app.relogio, sincronizar=False)


@router.post("/demonstracao/relogio/avancar")
def avancar_relogio(dados: AvancarRelogio, admin: dict = Depends(exigir_admin)) -> dict:
    """Adianta o relogio do app (somente admin e somente fora de producao)."""
    logger.info("Relogio de demonstracao +%s dia(s) por funcionario %s", dados.dias, admin.get("id"))
    return no_app(api_app.avancar_relogio, dados.dias)


@router.post("/demonstracao/relogio/resetar")
def resetar_relogio(admin: dict = Depends(exigir_admin)) -> dict:
    """Volta o relogio do app para a data real (somente admin)."""
    return no_app(api_app.resetar_relogio)


# ---------------------------------------------------------------------------
# Parceiros do Clube e catalogo de cupons (escrita: admin)
# ---------------------------------------------------------------------------
class ParceiroEntrada(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    categoria: str = Field(..., min_length=2, max_length=60)
    logo_url: str | None = Field(None, max_length=255)
    ativo: bool = True


class ModeloCupomEntrada(BaseModel):
    parceiro_id: str = Field(..., min_length=1, max_length=64)
    titulo: str = Field(..., min_length=3, max_length=120)
    descricao: str = Field(..., min_length=5, max_length=300)
    tag: str = Field("PARCERIA BULBE", min_length=3, max_length=60)
    prefixo_codigo: str = Field(..., pattern=r"^[A-Z0-9]{3,12}$")
    validade_dias: int = Field(14, ge=1, le=90)
    peso: int = Field(1, ge=1, le=10)
    ativo: bool = True


class ModeloCupomAlteracao(BaseModel):
    titulo: str | None = Field(None, min_length=3, max_length=120)
    descricao: str | None = Field(None, min_length=5, max_length=300)
    tag: str | None = Field(None, min_length=3, max_length=60)
    prefixo_codigo: str | None = Field(None, pattern=r"^[A-Z0-9]{3,12}$")
    validade_dias: int | None = Field(None, ge=1, le=90)
    peso: int | None = Field(None, ge=1, le=10)
    ativo: bool | None = None


def _id_app_parceiro(parceiro_id: str) -> str:
    """O painel usa o proprio id; a API do app precisa do id_app do parceiro."""
    from app.database.conexao import obter_sessao
    from app.database.modelos import Parceiro

    with obter_sessao() as sessao:
        parceiro = sessao.get(Parceiro, parceiro_id)
        if parceiro is None:
            raise HTTPException(404, detail={"error": {"code": "PARCEIRO_NAO_ENCONTRADO",
                                                        "message": "Parceiro nao encontrado.", "status": 404}})
        if not parceiro.id_app:
            raise HTTPException(409, detail={"error": {
                "code": "PARCEIRO_SEM_VINCULO_APP",
                "message": "Este parceiro existe so no banco ficticio do painel; cadastre-o pelo painel para ir ao app.",
                "status": 409}})
        return parceiro.id_app


@router.post("/parceiros", status_code=201)
def criar_parceiro(dados: ParceiroEntrada, admin: dict = Depends(exigir_admin)) -> dict:
    return no_app(api_app.criar_parceiro, dados.model_dump())


@router.put("/parceiros/{parceiro_id}")
def atualizar_parceiro(parceiro_id: str, dados: ParceiroEntrada, admin: dict = Depends(exigir_admin)) -> dict:
    return no_app(api_app.atualizar_parceiro, _id_app_parceiro(parceiro_id), dados.model_dump())


@router.delete("/parceiros/{parceiro_id}", status_code=204)
def remover_parceiro(parceiro_id: str, admin: dict = Depends(exigir_admin)) -> None:
    no_app(api_app.remover_parceiro, _id_app_parceiro(parceiro_id))


@router.get("/catalogo-cupons", dependencies=[Depends(funcionario_logado)])
def listar_catalogo(parceiro_id: str | None = None) -> list:
    """Catalogo de cupons do app (lido na hora da API, nao do banco do painel)."""
    alvo = _id_app_parceiro(parceiro_id) if parceiro_id else None
    return no_app(api_app.listar_catalogo, alvo, sincronizar=False)


@router.post("/catalogo-cupons", status_code=201)
def criar_modelo_cupom(dados: ModeloCupomEntrada, admin: dict = Depends(exigir_admin)) -> dict:
    corpo = {**dados.model_dump(), "parceiro_id": _id_app_parceiro(dados.parceiro_id)}
    return no_app(api_app.criar_modelo_cupom, corpo, sincronizar=False)


@router.patch("/catalogo-cupons/{modelo_id}")
def atualizar_modelo_cupom(modelo_id: str, dados: ModeloCupomAlteracao, admin: dict = Depends(exigir_admin)) -> dict:
    return no_app(api_app.atualizar_modelo_cupom, modelo_id, dados.model_dump(exclude_none=True), sincronizar=False)


@router.delete("/catalogo-cupons/{modelo_id}", status_code=204)
def remover_modelo_cupom(modelo_id: str, admin: dict = Depends(exigir_admin)) -> None:
    no_app(api_app.remover_modelo_cupom, modelo_id, sincronizar=False)


# ---------------------------------------------------------------------------
# Dicas do app: acervo, vitrine de 5 (o que aparece no app) e cadastro
# ---------------------------------------------------------------------------
ICONES_DICA = (
    "lampada_led", "lampada_apagada", "chuveiro", "maquina_lavar", "cofrinho", "geladeira",
    "ar_condicionado", "tomada", "televisao", "ferro_passar", "sol", "ventilador",
)
PADRAO_ICONE = "^(" + "|".join(ICONES_DICA) + ")$"


class DicaEntrada(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100)
    descricao: str = Field(..., min_length=3, max_length=250)
    economia: float = Field(..., gt=0, le=10_000)
    icone: str = Field("lampada_led", pattern=PADRAO_ICONE)


class VitrineEntrada(BaseModel):
    dicas: list[int] = Field(..., min_length=5, max_length=5)


@router.get("/app/dicas", dependencies=[Depends(funcionario_logado)])
def listar_dicas_app() -> dict:
    """Acervo de dicas do app, com a vitrine (em_exibicao/ordem) e os icones disponiveis."""
    return {"dicas": no_app(api_app.listar_dicas_app, sincronizar=False), "icones": list(ICONES_DICA)}


@router.put("/app/dicas/vitrine")
def definir_vitrine(dados: VitrineEntrada, admin: dict = Depends(exigir_admin)) -> list:
    """Confirma as 5 dicas do carrossel do app, na ordem (somente admin)."""
    return no_app(api_app.definir_vitrine_dicas, dados.dicas)


@router.post("/app/dicas", status_code=201)
def criar_dica(dados: DicaEntrada, admin: dict = Depends(exigir_admin)) -> dict:
    return no_app(api_app.criar_dica, dados.model_dump())


@router.put("/app/dicas/{dica_id}")
def atualizar_dica(dica_id: int, dados: DicaEntrada, admin: dict = Depends(exigir_admin)) -> dict:
    return no_app(api_app.atualizar_dica, dica_id, dados.model_dump())


@router.delete("/app/dicas/{dica_id}", status_code=204)
def remover_dica(dica_id: int, admin: dict = Depends(exigir_admin)) -> None:
    no_app(api_app.remover_dica, dica_id)


# ---------------------------------------------------------------------------
# Atendimento: chat com o cliente do app
# ---------------------------------------------------------------------------
class RespostaEntrada(BaseModel):
    texto: str = Field(..., min_length=1, max_length=1000)


def _atendimento(atendimento_id: int) -> dict:
    from app.database import consultas

    item = consultas.obter_atendimento(atendimento_id)
    if item is not None:
        return item
    raise HTTPException(404, detail={"error": {"code": "ATENDIMENTO_NAO_ENCONTRADO",
                                                "message": "Atendimento nao encontrado.", "status": 404}})


def _id_app_atendimento(atendimento: dict) -> str:
    if not atendimento.get("id_app"):
        raise HTTPException(409, detail={"error": {
            "code": "ATENDIMENTO_SEM_CHAT",
            "message": "Este atendimento e do historico ficticio do painel e nao tem conversa no app.",
            "status": 409}})
    return atendimento["id_app"]


@router.get("/atendimentos/{atendimento_id}/conversa", dependencies=[Depends(funcionario_logado)])
def conversa(atendimento_id: int, depois_de: int = 0) -> dict:
    """
    Atendimento do painel + mensagens do chat do app, lidas ao vivo na API
    (use depois_de com o id da ultima mensagem para buscar so as novas).
    """
    atendimento = _atendimento(atendimento_id)
    if not atendimento.get("id_app"):
        return {"atendimento": atendimento, "conversa": None}
    dados = no_app(api_app.conversa, atendimento["id_app"], max(depois_de, 0), sincronizar=False)
    return {"atendimento": atendimento, "conversa": dados}


@router.post("/atendimentos/{atendimento_id}/respostas", status_code=201)
def responder(atendimento_id: int, dados: RespostaEntrada,
              funcionario: dict = Depends(funcionario_logado)) -> dict:
    """Resposta do funcionario ao cliente; o nome dele aparece no app."""
    id_app = _id_app_atendimento(_atendimento(atendimento_id))
    nome = " ".join((funcionario.get("nome") or "Atendimento Bulbe").split())[:100]
    return no_app(api_app.responder_atendimento, id_app, dados.texto.strip(), nome)


@router.post("/atendimentos/{atendimento_id}/encerramento")
def encerrar(atendimento_id: int, funcionario: dict = Depends(funcionario_logado)) -> dict:
    """Encerra a conversa no app (o cliente ve 'Conversa encerrada')."""
    return no_app(api_app.encerrar_atendimento, _id_app_atendimento(_atendimento(atendimento_id)))


# ---------------------------------------------------------------------------
# Adesoes: aprovar (cria o cliente no app) ou recusar
# ---------------------------------------------------------------------------
def _id_app_adesao(adesao_id: str) -> str:
    from app.database.conexao import obter_sessao
    from app.database.modelos import Adesao

    with obter_sessao() as sessao:
        adesao = sessao.get(Adesao, adesao_id)
        if adesao is None:
            raise HTTPException(404, detail={"error": {"code": "ADESAO_NAO_ENCONTRADA",
                                                        "message": "Adesao nao encontrada.", "status": 404}})
        if not adesao.id_app:
            raise HTTPException(409, detail={"error": {
                "code": "ADESAO_SEM_VINCULO_APP",
                "message": "Esta adesao e do historico ficticio do painel; so as adesoes feitas pelo app podem ser analisadas.",
                "status": 409}})
        return adesao.id_app


@router.post("/adesoes/{adesao_id}/aprovacao")
def aprovar_adesao(adesao_id: str, funcionario: dict = Depends(funcionario_logado)) -> dict:
    """Aprova a adesao no app: cria o cliente, que comeca a jornada de ativacao."""
    return no_app(api_app.aprovar_adesao, _id_app_adesao(adesao_id))


@router.post("/adesoes/{adesao_id}/recusa")
def recusar_adesao(adesao_id: str, funcionario: dict = Depends(funcionario_logado)) -> dict:
    return no_app(api_app.recusar_adesao, _id_app_adesao(adesao_id))
