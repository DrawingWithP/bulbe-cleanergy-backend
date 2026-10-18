"""
Camada de Apresentacao, PainelController (APIRouter).

Rotas do Painel de Gestao interno da Bulbe. Todas exigem funcionario logado
(Depends(funcionario_logado)), exceto POST /v1/painel/login; as rotas de gestao
(auditoria, uso do chatbot e expurgo) exigem perfil admin (Depends(exigir_admin)).
Os dados vem de app.database.consultas.

Seguranca do login (v2): bloqueio 429 LOGIN_BLOQUEADO depois de LOGIN_BLOQUEIO_APOS_FALHAS
falhas do mesmo e-mail em LOGIN_JANELA_MINUTOS, alerta por e-mail em segundo plano
(app.painel.alertas) e trilha de auditoria (login_ok, login_falha, login_bloqueado,
ver_ficha, ver_auditoria, expurgo) com o IP da requisicao.
"""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.database import consultas
from app.painel import alertas
from app.painel.auth import criar_token, exigir_admin, funcionario_logado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/painel", tags=["Painel"])

# Dependencia aplicada a todas as rotas protegidas.
PROTEGIDO = [Depends(funcionario_logado)]

PADRAO_CHAT_RETENCAO_DIAS = 180
PADRAO_AUDITORIA_RETENCAO_DIAS = 730
ACOES_AUDITORIA = ("login_ok", "login_falha", "login_bloqueado", "alerta_email", "ver_ficha", "ver_auditoria", "expurgo")


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


def _corpo_erro(code: str, message: str, status_http: int) -> dict:
    return {"error": {"code": code, "message": message, "status": status_http}}


def _erro(code: str, message: str, status_http: int, headers: dict | None = None) -> HTTPException:
    """HTTPException com o detail no formato padrao do projeto."""
    return HTTPException(status_code=status_http, detail=_corpo_erro(code, message, status_http), headers=headers)


def _ip(request: Request) -> str | None:
    """IP de quem fez a requisicao (o do socket; cabecalhos X-Forwarded-For nao sao confiaveis aqui)."""
    return request.client.host if request.client else None


def _auditar(acao: str, **campos: object) -> None:
    """Grava na auditoria sem derrubar a requisicao se o banco falhar (o erro vai para o log)."""
    try:
        consultas.registrar_auditoria(acao, **campos)
    except Exception:  # noqa: BLE001
        logger.exception("Nao foi possivel gravar a acao %s na auditoria.", acao)


def _limpar(texto: str | None) -> str | None:
    return (texto or "").strip() or None


def _funcionario_id_por_email(email: str) -> int | None:
    """
    Id do funcionario dono do e-mail (para o login_falha de e-mail existente), ou None.
    O contrato nao tem essa consulta em app.database.consultas: usa-a se existir
    (obter_funcionario_por_email) e, senao, faz uma leitura simples pela sessao do banco.
    """
    consulta = getattr(consultas, "obter_funcionario_por_email", None)
    try:
        if callable(consulta):
            funcionario = consulta(email)
            return funcionario.get("id") if isinstance(funcionario, dict) else None
        from sqlalchemy import func, select

        from app.database.conexao import obter_sessao
        from app.database.modelos import Funcionario

        with obter_sessao() as sessao:
            return sessao.scalar(select(Funcionario.id).where(func.lower(Funcionario.email) == email.lower()).limit(1))
    except Exception:  # noqa: BLE001 - so enriquece a auditoria; nunca derruba o login
        logger.exception("Nao foi possivel identificar o funcionario pelo e-mail informado.")
        return None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=LoginResposta,
    responses={401: {"description": "CREDENCIAIS_INVALIDAS"}, 429: {"description": "LOGIN_BLOQUEADO (com Retry-After)"}},
)
def login(dados: LoginRequisicao, request: Request, tarefas: BackgroundTasks):
    """
    Autentica o funcionario e devolve o token (valido por 8h).
    Depois de LOGIN_BLOQUEIO_APOS_FALHAS falhas do mesmo e-mail na janela, responde 429 ate a janela passar
    (mesmo com a senha certa). Quando as falhas passam de LOGIN_ALERTA_APOS_FALHAS, envia um alerta por e-mail.
    """
    email = dados.email.strip().lower()
    ip = _ip(request)
    janela = alertas.janela_minutos()

    falhas = consultas.contar_falhas_login(email, minutos=janela)
    if falhas >= alertas.limite_bloqueio():
        _auditar("login_bloqueado", funcionario_id=_funcionario_id_por_email(email), email_informado=email, ip=ip,
                 detalhe=f"{falhas} falhas nos ultimos {janela} minutos")
        logger.warning("Login bloqueado por excesso de tentativas (%s falhas).", falhas)
        raise _erro(
            "LOGIN_BLOQUEADO",
            f"Muitas tentativas. Tente de novo em {janela} minutos.",
            status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(janela * 60)},
        )

    funcionario = consultas.autenticar_funcionario(email, dados.senha)
    if funcionario is None:
        _auditar("login_falha", funcionario_id=_funcionario_id_por_email(email), email_informado=email, ip=ip)
        falhas = consultas.contar_falhas_login(email, minutos=janela)
        if falhas > alertas.limite_alerta() and alertas.reservar_alerta(email, janela):
            # Em segundo plano: a resposta do login nao espera o SMTP. A senha nunca e repassada.
            tarefas.add_task(alertas.enviar_alerta_login, email, falhas, ip)
        # Resposta direta (e nao HTTPException) para que as BackgroundTasks rodem depois dela.
        # Mensagem generica: nao revela se o e-mail existe.
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_corpo_erro("CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.", status.HTTP_401_UNAUTHORIZED),
            background=tarefas,
        )

    _auditar("login_ok", funcionario_id=funcionario.get("id"), email_informado=email, ip=ip)
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


# ---------------------------------------------------------------------------
# Clientes e ativacao
# ---------------------------------------------------------------------------
@router.get("/clientes", dependencies=PROTEGIDO)
def listar_clientes(
    termo: str | None = Query(None, max_length=100, description="Nome, e-mail, CPF, instalacao ou codigo de indicacao"),
    status_cliente: str | None = Query(None, alias="status", max_length=20, description="ativo, em_ativacao ou cancelado"),
    cidade: str | None = Query(None, max_length=80),
    etapa: int | None = Query(None, ge=1, le=5, description="Etapa atual da ativacao (1 a 5)"),
    pagina: int = Query(1, ge=1, le=100_000),
    por_pagina: int | None = Query(None, ge=1, le=100),
    limite: int | None = Query(None, ge=1, le=100, deprecated=True, description="Use por_pagina (mantido da v1)"),
) -> dict:
    """Busca paginada de clientes: {data, pagina, por_pagina, total, total_paginas}."""
    return consultas.buscar_clientes_paginado(
        termo=_limpar(termo),
        status=status_cliente or None,
        cidade=_limpar(cidade),
        etapa=etapa,
        pagina=pagina,
        por_pagina=por_pagina or limite or 20,
    )


# Declarada antes de /clientes/{cliente_id} para "parados" nao ser lido como id.
@router.get("/clientes/parados", dependencies=PROTEGIDO)
def listar_clientes_parados(
    etapa: int | None = Query(None, ge=1, le=5),
    dias_minimos: int = Query(30, ge=0, le=3650, description="Dias minimos sem avancar de etapa"),
    limite: int = Query(50, ge=1, le=100),
) -> list[dict]:
    """Clientes em ativacao parados na mesma etapa, do mais parado ao menos parado."""
    return consultas.listar_clientes_parados(etapa=etapa, dias_minimos=dias_minimos, limite=limite)


@router.get("/clientes/{cliente_id}")
def ficha_cliente(
    request: Request,
    cliente_id: str = Path(..., min_length=1, max_length=64),
    funcionario: dict = Depends(funcionario_logado),
) -> dict:
    """Ficha completa do cliente, agregando todas as consultas. 404 se nao existir. Grava ver_ficha."""
    cliente = consultas.obter_cliente(cliente_id)
    if cliente is None:
        raise _erro(
            "CLIENTE_NAO_ENCONTRADO",
            f"Cliente com id {cliente_id} nao foi encontrado.",
            status.HTTP_404_NOT_FOUND,
        )
    # Trilha de auditoria (LGPD): quem abriu a ficha de quem.
    _auditar("ver_ficha", funcionario_id=funcionario.get("id"), recurso_tipo="cliente",
             recurso_id=cliente_id, ip=_ip(request))
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


@router.get("/ativacoes/resumo", dependencies=PROTEGIDO)
def resumo_ativacoes() -> dict:
    """Resumo das ativacoes: por etapa, dias medios na etapa, atrasados e ativados nos ultimos 30 dias."""
    return consultas.resumo_ativacoes()


# ---------------------------------------------------------------------------
# Adesoes e atendimentos (paginados)
# ---------------------------------------------------------------------------
@router.get("/adesoes", dependencies=PROTEGIDO)
def listar_adesoes(
    situacao: str | None = Query(None, max_length=20, description="rascunho, enviada, aprovada ou recusada"),
    pagina: int = Query(1, ge=1, le=100_000),
    por_pagina: int | None = Query(None, ge=1, le=100),
    limite: int | None = Query(None, ge=1, le=100, deprecated=True, description="Use por_pagina (mantido da v1)"),
) -> dict:
    """Adesoes (pedidos de assinatura), paginadas."""
    return consultas.listar_adesoes_paginado(situacao=situacao or None, pagina=pagina,
                                             por_pagina=por_pagina or limite or 20)


@router.get("/atendimentos", dependencies=PROTEGIDO)
def listar_atendimentos(
    status_atendimento: str | None = Query(None, alias="status", max_length=20, description="aberto, em_andamento ou resolvido"),
    cliente_id: str | None = Query(None, max_length=64),
    pagina: int = Query(1, ge=1, le=100_000),
    por_pagina: int | None = Query(None, ge=1, le=100),
    limite: int | None = Query(None, ge=1, le=100, deprecated=True, description="Use por_pagina (mantido da v1)"),
) -> dict:
    """Atendimentos de todos os clientes (ou de um cliente), paginados, com cliente_nome."""
    return consultas.listar_atendimentos_paginado(cliente_id=_limpar(cliente_id), status=status_atendimento or None,
                                                  pagina=pagina, por_pagina=por_pagina or limite or 20)


# ---------------------------------------------------------------------------
# Catalogos
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Gestao (somente admin)
# ---------------------------------------------------------------------------
@router.get("/auditoria")
def listar_auditoria(
    request: Request,
    funcionario_id: int | None = Query(None, ge=1),
    acao: str | None = Query(None, max_length=30, description=", ".join(ACOES_AUDITORIA)),
    pagina: int = Query(1, ge=1, le=100_000),
    por_pagina: int = Query(50, ge=1, le=100),
    admin: dict = Depends(exigir_admin),
) -> dict:
    """Trilha de auditoria paginada (somente admin). A propria consulta fica registrada (ver_auditoria)."""
    resultado = consultas.listar_auditoria(funcionario_id=funcionario_id, acao=_limpar(acao),
                                           pagina=pagina, por_pagina=por_pagina)
    filtros = {"funcionario_id": funcionario_id, "acao": _limpar(acao), "pagina": pagina}
    _auditar("ver_auditoria", funcionario_id=admin.get("id"), ip=_ip(request),
             detalhe=json.dumps({k: v for k, v in filtros.items() if v is not None}, ensure_ascii=False))
    return resultado


@router.get("/uso-chatbot")
def uso_chatbot(
    dias: int = Query(30, ge=1, le=365),
    admin: dict = Depends(exigir_admin),
) -> dict:
    """Uso e custo estimado do assistente no periodo (somente admin)."""
    return consultas.metricas_uso_chatbot(dias=dias)


@router.post("/admin/expurgo")
def expurgar_dados(request: Request, admin: dict = Depends(exigir_admin)) -> dict:
    """
    Aplica a retencao de dados (LGPD) agora: apaga conversas do chat mais antigas que CHAT_RETENCAO_DIAS (180)
    e auditoria mais antiga que AUDITORIA_RETENCAO_DIAS (730). Somente admin; grava "expurgo" na auditoria.
    Resposta: as contagens de expurgar_dados_antigos + os prazos usados (dias_chat, dias_auditoria).
    """
    dias_chat = alertas.ler_inteiro_env("CHAT_RETENCAO_DIAS", PADRAO_CHAT_RETENCAO_DIAS, minimo=1, maximo=36_500)
    dias_auditoria = alertas.ler_inteiro_env("AUDITORIA_RETENCAO_DIAS", PADRAO_AUDITORIA_RETENCAO_DIAS,
                                             minimo=1, maximo=36_500)
    removidos = consultas.expurgar_dados_antigos(dias_chat=dias_chat, dias_auditoria=dias_auditoria)
    _auditar("expurgo", funcionario_id=admin.get("id"), ip=_ip(request),
             detalhe=json.dumps({"dias_chat": dias_chat, "dias_auditoria": dias_auditoria,
                                 "removidos": removidos}, ensure_ascii=False)[:500])
    logger.info("Expurgo manual por funcionario %s: %s", admin.get("id"), removidos)
    return {**removidos, "dias_chat": dias_chat, "dias_auditoria": dias_auditoria}
