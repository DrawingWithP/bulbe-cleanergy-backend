"""
Configuracao comum da suite de testes (pytest).

ATENCAO: as variaveis de ambiente sao definidas no topo deste arquivo, ANTES de qualquer
import de `app`, porque `app.database.conexao` cria o engine no momento do import e varios
modulos chamam `load_dotenv()` (que nao sobrescreve variaveis ja definidas). Assim:
- o banco usado e um SQLite temporario (o banco real app/database/bulbe_ficticio.db nunca e tocado);
- ANTHROPIC_API_KEY fica vazia (o .env local nao consegue repor a chave real);
- SMTP fica sem configuracao (nenhum e-mail real e enviado);
- PAINEL_SECRET e PAINEL_SENHA_DEMO tem valores proprios de teste.
"""
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) Ambiente de teste (antes de importar app)
# ---------------------------------------------------------------------------
PASTA_PROJETO = Path(__file__).resolve().parent.parent
if str(PASTA_PROJETO) not in sys.path:
    sys.path.insert(0, str(PASTA_PROJETO))

PASTA_TEMPORARIA = Path(tempfile.mkdtemp(prefix="bulbe-testes-"))
CAMINHO_BANCO_TESTE = PASTA_TEMPORARIA / "bulbe_teste.db"

SENHA_DEMO_TESTE = "senha-demo-de-teste-123"
SEGREDO_TESTE = "segredo-do-painel-usado-somente-nos-testes-0123456789"

AMBIENTE_TESTE: dict[str, str] = {
    "BULBE_DB_URL": "sqlite:///" + CAMINHO_BANCO_TESTE.as_posix(),
    "PAINEL_SECRET": SEGREDO_TESTE,
    "PAINEL_SENHA_DEMO": SENHA_DEMO_TESTE,
    # Vazia (e nao apagada): load_dotenv(override=False) nao repoe a chave do .env.
    "ANTHROPIC_API_KEY": "",
    "CHATBOT_MODELO": "claude-haiku-5-5",
    "CHATBOT_ESFORCO": "high",
    "CHATBOT_TIMEOUT": "5",
    # Sem SMTP: nenhum alerta sai de verdade (os testes de alerta usam um SMTP simulado).
    "SMTP_HOST": "",
    "SMTP_PORTA": "587",
    "SMTP_USUARIO": "",
    "SMTP_SENHA": "",
    "SMTP_REMETENTE": "",
    "SMTP_TLS": "true",
    "ALERTA_LOGIN_EMAIL": "alerta@teste.local",
    # Valores padrao do contrato (fixados para o .env local nao alterar os testes).
    "LOGIN_ALERTA_APOS_FALHAS": "3",
    "LOGIN_BLOQUEIO_APOS_FALHAS": "5",
    "LOGIN_JANELA_MINUTOS": "15",
    "CHAT_RETENCAO_DIAS": "180",
    "AUDITORIA_RETENCAO_DIAS": "730",
}
os.environ.update(AMBIENTE_TESTE)

# ---------------------------------------------------------------------------
# 2) Imports do sistema (depois do ambiente)
# ---------------------------------------------------------------------------
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import conexao  # noqa: E402

CAMINHO_BANCO_REAL = (PASTA_PROJETO / "app" / "database" / "bulbe_ficticio.db").resolve()

# Trava de seguranca: os testes nunca podem apontar para o banco real.
assert "bulbe_ficticio.db" not in str(conexao.engine.url), "Os testes nao podem usar o banco real."
assert Path(str(conexao.engine.url.database)).resolve() == CAMINHO_BANCO_TESTE.resolve()


# ---------------------------------------------------------------------------
# 3) Banco populado uma vez por sessao
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def banco_de_teste() -> dict:
    """
    Recria e popula o SQLite temporario uma vez por sessao. Devolve contagens tiradas
    logo depois do seed (para testes que verificam o estado inicial).
    """
    real_antes = CAMINHO_BANCO_REAL.stat().st_mtime if CAMINHO_BANCO_REAL.exists() else None
    conexao.inicializar_banco(recriar=True)
    contagens: dict = {}
    with conexao.engine.connect() as con:
        for tabela in ("clientes", "funcionarios", "chat_conversas", "chat_mensagens", "auditoria_acessos"):
            try:
                contagens[tabela] = con.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar_one()
            except Exception:  # noqa: BLE001 - tabela ainda nao existe no codigo atual
                contagens[tabela] = None
        try:
            contagens["acoes_auditoria"] = sorted(
                {linha[0] for linha in con.execute(text("SELECT DISTINCT acao FROM auditoria_acessos"))}
            )
        except Exception:  # noqa: BLE001
            contagens["acoes_auditoria"] = None
    yield contagens
    conexao.engine.dispose()
    real_depois = CAMINHO_BANCO_REAL.stat().st_mtime if CAMINHO_BANCO_REAL.exists() else None
    shutil.rmtree(PASTA_TEMPORARIA, ignore_errors=True)
    assert real_antes == real_depois, "O banco real foi modificado durante os testes."


@pytest.fixture(scope="session")
def app_fastapi(banco_de_teste):
    """A aplicacao FastAPI (importada so depois de o banco de teste existir)."""
    from app.main import app

    return app


@pytest.fixture(scope="session")
def cliente_http(app_fastapi) -> TestClient:
    """TestClient unico da sessao (o lifespan roda uma vez; o banco ja tem dados)."""
    with TestClient(app_fastapi) as cliente:
        yield cliente


# ---------------------------------------------------------------------------
# 4) Funcionarios e tokens
# ---------------------------------------------------------------------------
def _funcionario_por_email(email: str) -> dict:
    with conexao.engine.connect() as con:
        linha = con.execute(
            text("SELECT id, nome, email, perfil FROM funcionarios WHERE lower(email) = :e"),
            {"e": email.lower()},
        ).mappings().first()
    assert linha is not None, f"Funcionario {email} nao existe no banco de teste."
    return dict(linha)


@pytest.fixture(scope="session")
def funcionario_admin(banco_de_teste) -> dict:
    return _funcionario_por_email("admin@bulbe.com.br")


@pytest.fixture(scope="session")
def funcionario_atendimento(banco_de_teste) -> dict:
    return _funcionario_por_email("atendimento@bulbe.com.br")


@pytest.fixture(scope="session")
def funcionario_ana(banco_de_teste) -> dict:
    return _funcionario_por_email("ana.souza@bulbe.com.br")


@pytest.fixture(scope="session")
def token_admin(funcionario_admin) -> str:
    """Token criado direto pelo auth (nao passa pelo login, para nao gerar falhas/bloqueios)."""
    from app.painel.auth import criar_token

    return criar_token(funcionario_admin)


@pytest.fixture(scope="session")
def token_atendimento(funcionario_atendimento) -> str:
    from app.painel.auth import criar_token

    return criar_token(funcionario_atendimento)


@pytest.fixture(scope="session")
def token_ana(funcionario_ana) -> str:
    from app.painel.auth import criar_token

    return criar_token(funcionario_ana)


@pytest.fixture
def cab_admin(token_admin) -> dict:
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def cab_atendimento(token_atendimento) -> dict:
    return {"Authorization": f"Bearer {token_atendimento}"}


@pytest.fixture
def cab_ana(token_ana) -> dict:
    return {"Authorization": f"Bearer {token_ana}"}


@pytest.fixture
def criar_funcionario(banco_de_teste):
    """
    Fabrica de funcionarios exclusivos de um teste (e-mail unico), para isolar contagens,
    auditoria e tentativas de login. Devolve {id, nome, email, perfil, senha, token, cabecalho}.
    """
    from app.database.conexao import obter_sessao
    from app.database.modelos import Funcionario
    from app.database.seguranca import gerar_hash_senha
    from app.painel.auth import criar_token

    def _criar(perfil: str = "atendimento", senha: str = "Senha-Correta-123", prefixo: str = "teste") -> dict:
        email = f"{prefixo}.{uuid.uuid4().hex[:10]}@bulbe.com.br"
        nome = f"Funcionario de Teste {email[:18]}"
        with obter_sessao() as sessao:
            funcionario = Funcionario(
                nome=nome, email=email, senha_hash=gerar_hash_senha(senha), perfil=perfil, ativo=True
            )
            sessao.add(funcionario)
            sessao.flush()
            fid = funcionario.id
        dados = {"id": fid, "nome": nome, "email": email, "perfil": perfil}
        token = criar_token(dados)
        return {**dados, "senha": senha, "token": token, "cabecalho": {"Authorization": f"Bearer {token}"}}

    return _criar


# ---------------------------------------------------------------------------
# 5) API da Anthropic simulada
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def guarda_anthropic(monkeypatch, app_fastapi):
    """
    Em TODOS os testes: criar anthropic.Anthropic/AsyncAnthropic de verdade e proibido.
    A tentativa e recusada e o teste falha (protege contra chamadas pagas acidentais).
    """
    from tests.apoio import instalar_guarda_anthropic

    guarda = instalar_guarda_anthropic(monkeypatch)
    yield guarda
    assert guarda.tentativas == [], f"Cliente real da Anthropic instanciado: {guarda.tentativas}"


@pytest.fixture
def api_anthropic(app_fastapi, guarda_anthropic):
    """
    API da Anthropic simulada, injetada com chatbot_service.definir_cliente(...): o cliente
    e o SDK real com um transporte HTTP falso (nenhuma requisicao sai da maquina). Ver tests/apoio.py.
    """
    from tests.apoio import ApiAnthropicFalsa, injetar_api_falsa, remover_api_falsa

    api = ApiAnthropicFalsa()
    injetar_api_falsa(api)
    yield api
    remover_api_falsa()


@pytest.fixture
def sem_chave_anthropic(monkeypatch, app_fastapi, guarda_anthropic):
    """Garante ANTHROPIC_API_KEY vazia e nenhum cliente injetado ou em cache no servico."""
    from tests.apoio import limpar_clientes_em_cache, remover_api_falsa

    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    remover_api_falsa()
    limpar_clientes_em_cache(monkeypatch)


@pytest.fixture(autouse=True)
def reiniciar_estado_em_memoria(app_fastapi):
    """Limpa o controle em memoria de alertas de login antes e depois de cada teste."""
    try:
        from app.painel import alertas
    except ImportError:  # pragma: no cover - modulo ainda nao existe
        yield
        return
    reiniciar = getattr(alertas, "reiniciar_controle", None)
    if callable(reiniciar):
        reiniciar()
    yield
    if callable(reiniciar):
        reiniciar()


# ---------------------------------------------------------------------------
# 6) SMTP simulado
# ---------------------------------------------------------------------------
@pytest.fixture
def smtp_falso(monkeypatch, app_fastapi):
    """
    Substitui smtplib.SMTP/SMTP_SSL por uma classe que so registra as mensagens.
    Nao configura o SMTP; use `configurar_smtp` para isso.
    """
    from tests.apoio import instalar_smtp_falso

    return instalar_smtp_falso(monkeypatch)


@pytest.fixture
def configurar_smtp(monkeypatch, smtp_falso):
    """Configura o SMTP (host .invalid, nunca resolvivel) e o destino do alerta."""
    from tests.apoio import aplicar_config_smtp

    def _configurar(**extra: str) -> dict:
        valores = {
            "SMTP_HOST": "smtp.teste.invalid",
            "SMTP_PORTA": "587",
            "SMTP_USUARIO": "usuario@teste.invalid",
            "SMTP_SENHA": "senha-smtp-de-teste",
            "SMTP_REMETENTE": "painel@teste.invalid",
            "SMTP_TLS": "true",
            "ALERTA_LOGIN_EMAIL": "seguranca@teste.invalid",
        }
        valores.update(extra)
        aplicar_config_smtp(monkeypatch, valores)
        return valores

    return _configurar
