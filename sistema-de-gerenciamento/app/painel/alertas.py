"""
Camada de Seguranca do Painel, limites de tentativas de login e alerta por e-mail.

- Le a configuracao do ambiente a cada uso (o .env e carregado pelo app/main.py,
  possivelmente depois do import deste modulo).
- reservar_alerta(): garante no maximo 1 alerta por e-mail tentado a cada janela
  (controle em memoria protegido por threading.Lock + consulta a auditoria, que cobre
  o caso de o servidor ter sido reiniciado dentro da janela).
- enviar_alerta_login(): monta e envia o e-mail com smtplib + email.message (somente
  biblioteca padrao), com STARTTLS quando SMTP_TLS=true. Pensada para rodar em
  BackgroundTasks: nunca levanta excecao; qualquer problema vira aviso no log e a
  acao "alerta_email" na auditoria com o detalhe.

O e-mail de alerta informa o e-mail tentado, a quantidade de falhas, o IP e o horario.
A senha digitada nunca chega a este modulo.
"""
import logging
import os
import smtplib
import ssl
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.database import consultas

logger = logging.getLogger(__name__)

# Valores padrao (contrato da v2, secao 3.1).
PADRAO_SMTP_PORTA = 587
PADRAO_ALERTA_APOS_FALHAS = 3
PADRAO_BLOQUEIO_APOS_FALHAS = 5
PADRAO_JANELA_MINUTOS = 15
TEMPO_LIMITE_SMTP_SEGUNDOS = 15
TAMANHO_MAXIMO_DETALHE = 500
TAMANHO_MAXIMO_EMAIL = 254
ACAO_ALERTA = "alerta_email"

# Controle "1 alerta por e-mail a cada janela": e-mail normalizado -> momento (UTC) da reserva.
_trava = threading.Lock()
_ultimos_alertas: dict[str, datetime] = {}


# ---------------------------------------------------------------------------
# Configuracao (lida do ambiente a cada uso)
# ---------------------------------------------------------------------------
def ler_inteiro_env(nome: str, padrao: int, minimo: int = 1, maximo: int = 100_000) -> int:
    """Le um inteiro do ambiente; valor ausente, invalido ou fora da faixa usa o padrao."""
    bruto = (os.getenv(nome) or "").strip()
    if not bruto:
        return padrao
    try:
        valor = int(bruto)
    except ValueError:
        logger.warning("Variavel %s invalida (%r): usando o padrao %s.", nome, bruto, padrao)
        return padrao
    if valor < minimo or valor > maximo:
        logger.warning("Variavel %s fora da faixa %s..%s: usando o padrao %s.", nome, minimo, maximo, padrao)
        return padrao
    return valor


def _ler_booleano_env(nome: str, padrao: bool) -> bool:
    bruto = (os.getenv(nome) or "").strip().lower()
    if not bruto:
        return padrao
    return bruto in ("1", "true", "sim", "yes", "on")


def janela_minutos() -> int:
    """LOGIN_JANELA_MINUTOS (padrao 15)."""
    return ler_inteiro_env("LOGIN_JANELA_MINUTOS", PADRAO_JANELA_MINUTOS, minimo=1, maximo=24 * 60)


def limite_alerta() -> int:
    """LOGIN_ALERTA_APOS_FALHAS (padrao 3): o alerta sai quando as falhas passam deste numero."""
    return ler_inteiro_env("LOGIN_ALERTA_APOS_FALHAS", PADRAO_ALERTA_APOS_FALHAS, minimo=1, maximo=1000)


def limite_bloqueio() -> int:
    """LOGIN_BLOQUEIO_APOS_FALHAS (padrao 5): com esse numero de falhas na janela o login fica bloqueado."""
    return ler_inteiro_env("LOGIN_BLOQUEIO_APOS_FALHAS", PADRAO_BLOQUEIO_APOS_FALHAS, minimo=1, maximo=1000)


def configuracao_smtp() -> dict:
    """Configuracao SMTP atual. A senha nunca deve ser registrada em log."""
    usuario = (os.getenv("SMTP_USUARIO") or "").strip()
    return {
        "host": (os.getenv("SMTP_HOST") or "").strip(),
        "porta": ler_inteiro_env("SMTP_PORTA", PADRAO_SMTP_PORTA, minimo=1, maximo=65535),
        "usuario": usuario,
        "senha": os.getenv("SMTP_SENHA") or "",
        "remetente": (os.getenv("SMTP_REMETENTE") or "").strip() or usuario,
        "tls": _ler_booleano_env("SMTP_TLS", True),
        "destinatario": (os.getenv("ALERTA_LOGIN_EMAIL") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Controle de 1 alerta por janela
# ---------------------------------------------------------------------------
def _normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def _para_datetime_utc(valor: object) -> datetime | None:
    """Converte o criado_em (string ISO) da auditoria em datetime UTC."""
    if not isinstance(valor, str) or not valor:
        return None
    try:
        momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    if momento.tzinfo is None:  # o banco grava em UTC sem fuso
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def _alerta_registrado_na_auditoria(email: str, desde: datetime) -> bool:
    """Procura um "alerta_email" recente para o mesmo e-mail (cobre reinicios do servidor)."""
    try:
        pagina = consultas.listar_auditoria(acao=ACAO_ALERTA, pagina=1, por_pagina=100)
    except Exception:  # noqa: BLE001 - a auditoria nao pode derrubar o login
        logger.exception("Nao foi possivel consultar a auditoria de alertas de login.")
        return False
    itens = pagina.get("data", []) if isinstance(pagina, dict) else []
    for item in itens:
        if not isinstance(item, dict) or _normalizar_email(item.get("email_informado") or "") != email:
            continue
        momento = _para_datetime_utc(item.get("criado_em"))
        if momento is not None and momento >= desde:
            return True
    return False


def reservar_alerta(email: str, janela: int | None = None, agora: datetime | None = None) -> bool:
    """
    Devolve True se este e-mail ainda nao teve alerta na janela atual e marca a reserva.
    Chamadas concorrentes para o mesmo e-mail: so a primeira recebe True.
    """
    chave = _normalizar_email(email)
    if not chave:
        return False
    minutos = janela if janela is not None else janela_minutos()
    momento = agora or datetime.now(timezone.utc)
    desde = momento - timedelta(minutes=minutos)
    with _trava:
        # Limpa reservas vencidas para o dicionario nao crescer sem limite.
        for chave_antiga in [c for c, quando in _ultimos_alertas.items() if quando < desde]:
            del _ultimos_alertas[chave_antiga]
        if chave in _ultimos_alertas:
            return False
        if _alerta_registrado_na_auditoria(chave, desde):
            _ultimos_alertas[chave] = momento
            return False
        _ultimos_alertas[chave] = momento
        return True


def reiniciar_controle() -> None:
    """Esquece as reservas em memoria (uso em testes)."""
    with _trava:
        _ultimos_alertas.clear()


# ---------------------------------------------------------------------------
# Envio do e-mail
# ---------------------------------------------------------------------------
def _limpar_texto(valor: object, tamanho: int = TAMANHO_MAXIMO_EMAIL) -> str:
    """Remove caracteres de controle (evita injecao de cabecalho/linhas) e limita o tamanho."""
    texto = "".join(c for c in str(valor or "") if c.isprintable())
    return texto[:tamanho]


def _horario_local(momento: datetime) -> str:
    """Horario no fuso de Brasilia quando o sistema tiver a base de fusos; senao, em UTC."""
    momento_utc = momento.astimezone(timezone.utc) if momento.tzinfo else momento.replace(tzinfo=timezone.utc)
    try:
        from zoneinfo import ZoneInfo

        local = momento_utc.astimezone(ZoneInfo("America/Sao_Paulo"))
        return local.strftime("%d/%m/%Y %H:%M:%S (horario de Brasilia)")
    except Exception:  # noqa: BLE001 - tzdata ausente (comum no Windows)
        return momento_utc.strftime("%d/%m/%Y %H:%M:%S (UTC)")


def montar_mensagem(email_tentado: str, falhas: int, ip: str | None, momento: datetime,
                    remetente: str, destinatario: str, janela: int) -> EmailMessage:
    """Monta o e-mail de alerta (texto puro). Nunca recebe nem inclui a senha digitada."""
    email_limpo = _limpar_texto(email_tentado) or "(vazio)"
    ip_limpo = _limpar_texto(ip, 64) or "desconhecido"
    mensagem = EmailMessage()
    mensagem["Subject"] = "[Painel Bulbe] Alerta de seguranca: tentativas de login com falha"
    mensagem["From"] = remetente
    mensagem["To"] = destinatario
    mensagem["Date"] = formatdate(localtime=False)
    mensagem["Message-ID"] = make_msgid(domain="painel.bulbe.local")
    mensagem.set_content(
        "Alerta automatico do Painel de Gestao da Bulbe Energia.\n\n"
        f"O e-mail abaixo errou a senha {falhas} vez(es) nos ultimos {janela} minutos.\n\n"
        f"E-mail tentado: {email_limpo}\n"
        f"Falhas na janela: {falhas}\n"
        f"IP de origem: {ip_limpo}\n"
        f"Horario: {_horario_local(momento)}\n\n"
        "Se nao foi um funcionario esquecendo a senha, verifique a tela Auditoria do painel.\n"
        "O login desse e-mail e bloqueado temporariamente depois de algumas falhas seguidas.\n"
        "Este alerta e enviado no maximo uma vez por janela para o mesmo e-mail.\n"
    )
    return mensagem


def _registrar_alerta_na_auditoria(email: str, ip: str | None, detalhe: str) -> None:
    try:
        consultas.registrar_auditoria(
            ACAO_ALERTA,
            email_informado=_limpar_texto(email) or None,
            ip=ip,
            detalhe=detalhe[:TAMANHO_MAXIMO_DETALHE],
        )
    except Exception:  # noqa: BLE001
        logger.exception("Nao foi possivel gravar o alerta de login na auditoria.")


def enviar_alerta_login(email_tentado: str, falhas: int, ip: str | None = None,
                        momento: datetime | None = None) -> bool:
    """
    Envia o alerta de tentativas de login. Devolve True se o servidor SMTP aceitou a mensagem.
    Nunca levanta excecao (roda em BackgroundTasks): falhas viram log + auditoria "alerta_email".
    """
    momento = momento or datetime.now(timezone.utc)
    janela = janela_minutos()
    try:
        config = configuracao_smtp()
        faltando = [nome for nome, chave in (("SMTP_HOST", "host"), ("ALERTA_LOGIN_EMAIL", "destinatario"),
                                             ("SMTP_REMETENTE ou SMTP_USUARIO", "remetente")) if not config[chave]]
        if faltando:
            detalhe = (f"Alerta nao enviado: SMTP nao configurado (faltando {', '.join(faltando)}). "
                       f"{falhas} falhas em {janela} min.")
            logger.warning("Alerta de login nao enviado: SMTP nao configurado (faltando %s).", ", ".join(faltando))
            _registrar_alerta_na_auditoria(email_tentado, ip, detalhe)
            return False

        mensagem = montar_mensagem(email_tentado, falhas, ip, momento, config["remetente"],
                                   config["destinatario"], janela)
        # smtplib.SMTP e lido na hora da chamada (permite simular o servidor nos testes).
        with smtplib.SMTP(config["host"], config["porta"], timeout=TEMPO_LIMITE_SMTP_SEGUNDOS) as servidor:
            if config["tls"]:
                servidor.starttls(context=ssl.create_default_context())
            if config["usuario"]:
                servidor.login(config["usuario"], config["senha"])
            servidor.send_message(mensagem)
    except Exception as erro:  # noqa: BLE001 - qualquer falha de envio nao pode afetar o login
        # Registra so o tipo e a mensagem do erro (sem a configuracao, que inclui a senha SMTP).
        detalhe = f"Falha ao enviar o alerta ({type(erro).__name__}: {_limpar_texto(erro, 300)}). {falhas} falhas em {janela} min."
        logger.warning("Falha ao enviar o alerta de login por e-mail: %s", type(erro).__name__)
        _registrar_alerta_na_auditoria(email_tentado, ip, detalhe)
        return False

    logger.info("Alerta de tentativas de login enviado (%s falhas).", falhas)
    _registrar_alerta_na_auditoria(
        email_tentado, ip, f"Alerta enviado para {_limpar_texto(config['destinatario'])}: {falhas} falhas em {janela} min."
    )
    return True
