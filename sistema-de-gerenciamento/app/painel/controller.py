"""
Camada de Apresentacao, PainelController (APIRouter).

Rotas do Painel de Gestao interno da Bulbe. Todas exigem funcionario logado
(Depends(funcionario_logado)), exceto POST /v1/painel/login.
Os dados vem das consultas somente leitura de app.database.consultas.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from app.database import consultas
from app.painel.auth import criar_token, funcionario_logado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/painel", tags=["Painel"])

# Dependencia aplicada a todas as rotas protegidas.
PROTEGIDO = [Depends(funcionario_logado)]


class LoginRequisicao(BaseModel):
    """Credenciais do funcionario no login do painel."""
    email: str = Field(..., min_length=3, max_length=254, description="E-mail corporativo do funcionario")
    senha: str = Field(..., min_length=1, max_length=200, description="Senha do funcionario")


class FuncionarioPublico(BaseModel):
    """Dados do funcionario que a API devolve (sem senha)."""
    id: int
    nome: str
    email: str
    perfil: str


class LoginResposta(BaseModel):
    """Resposta do login: token Bearer e dados do funcionario."""
    token: str
    funcionario: FuncionarioPublico


def _erro(code: str, message: str, status_http: int) -> HTTPException:
    """HTTPException com o detail no formato padrao do projeto."""
    return HTTPException(
        status_code=status_http,
        detail={"error": {"code": code, "message": message, "status": status_http}},
    )


@router.post("/login", response_model=LoginResposta)
def login(dados: LoginRequisicao) -> dict:
    """Autentica o funcionario e devolve o token (valido por 8h)."""
    funcionario = consultas.autenticar_funcionario(dados.email.strip().lower(), dados.senha)
    if funcionario is None:
        # Mensagem generica: nao revela se o e-mail existe.
        raise _erro(
            "CREDENCIAIS_INVALIDAS",
            "E-mail ou senha incorretos.",
            status.HTTP_401_UNAUTHORIZED,
        )
    logger.info("Login no painel: funcionario %s", funcionario.get("id"))
    return {"token": criar_token(funcionario), "funcionario": funcionario}


@router.get("/me", response_model=FuncionarioPublico)
def me(funcionario: dict = Depends(funcionario_logado)) -> dict:
    """Retorna o funcionario logado (dados do token)."""
    return funcionario


@router.get("/metricas", dependencies=PROTEGIDO)
def metricas() -> dict:
    """Indicadores gerais para a tela Visao geral."""
    return consultas.metricas_gerais()


@router.get("/clientes", dependencies=PROTEGIDO)
def listar_clientes(
    termo: str | None = Query(None, max_length=100, description="Nome, e-mail, CPF, instalacao ou codigo de indicacao"),
    status_cliente: str | None = Query(None, alias="status", max_length=20, description="ativo, em_ativacao ou cancelado"),
    cidade: str | None = Query(None, max_length=80),
    limite: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Busca clientes com filtros opcionais."""
    return consultas.buscar_clientes(
        termo=(termo or "").strip() or None,
        status=status_cliente or None,
        cidade=(cidade or "").strip() or None,
        limite=limite,
    )


@router.get("/clientes/{cliente_id}")
def ficha_cliente(
    cliente_id: str = Path(..., min_length=1, max_length=64),
    funcionario: dict = Depends(funcionario_logado),
) -> dict:
    """Ficha completa do cliente, agregando todas as consultas. 404 se nao existir."""
    cliente = consultas.obter_cliente(cliente_id)
    if cliente is None:
        raise _erro(
            "CLIENTE_NAO_ENCONTRADO",
            f"Cliente com id {cliente_id} nao foi encontrado.",
            status.HTTP_404_NOT_FOUND,
        )
    # Trilha de auditoria (LGPD): quem abriu a ficha de quem.
    logger.info("Funcionario %s abriu a ficha do cliente %s", funcionario.get("id"), cliente_id)
    return {
        "cliente": cliente,
        "ativacao": consultas.obter_ativacao(cliente_id),
        "faturas": consultas.listar_faturas(cliente_id),
        "economia": consultas.resumo_economia_cliente(cliente_id),
        "indicacoes": consultas.listar_indicacoes(cliente_id),
        "clube": consultas.obter_clube(cliente_id),
        "cupons": consultas.listar_cupons(cliente_id),
        "notificacoes": consultas.listar_notificacoes(cliente_id),
        "atendimentos": consultas.listar_atendimentos(cliente_id=cliente_id),
    }


@router.get("/adesoes", dependencies=PROTEGIDO)
def listar_adesoes(
    situacao: str | None = Query(None, max_length=20, description="rascunho, enviada, aprovada ou recusada"),
    limite: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Lista as adesoes (pedidos de assinatura)."""
    return consultas.listar_adesoes(situacao=situacao or None, limite=limite)


@router.get("/atendimentos", dependencies=PROTEGIDO)
def listar_atendimentos(
    status_atendimento: str | None = Query(None, alias="status", max_length=20, description="aberto, em_andamento ou resolvido"),
    limite: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Lista os atendimentos de todos os clientes."""
    return consultas.listar_atendimentos(status=status_atendimento or None, limite=limite)


@router.get("/usinas", dependencies=PROTEGIDO)
def listar_usinas() -> list[dict]:
    """Lista as usinas da Bulbe."""
    return consultas.listar_usinas()


@router.get("/parceiros", dependencies=PROTEGIDO)
def listar_parceiros(apenas_ativos: bool = Query(True)) -> list[dict]:
    """Lista os parceiros do Clube Bulbe."""
    return consultas.listar_parceiros(apenas_ativos=apenas_ativos)


@router.get("/dicas", dependencies=PROTEGIDO)
def listar_dicas() -> list[dict]:
    """Lista as dicas de economia exibidas no app."""
    return consultas.listar_dicas()
