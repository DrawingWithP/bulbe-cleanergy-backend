"""
Login do painel (secao 3.1 do contrato de melhorias): auditoria, bloqueio 429 na 6a tentativa
e alerta por e-mail (uma vez, na 4a falha) com SMTP simulado.

Cada teste usa um funcionario/e-mail proprio, para as falhas de um nao interferirem nos outros.
"""
import uuid
from datetime import timedelta

from sqlalchemy import func, update

from app.database import consultas
from app.database.conexao import Base, engine
from tests.apoio import texto_do_email

ROTA = "/v1/painel/login"


def _login(cliente_http, email: str, senha: str):
    return cliente_http.post(ROTA, json={"email": email, "senha": senha})


def _auditoria(acao: str, email: str | None = None, funcionario_id: int | None = None) -> list[dict]:
    itens = consultas.listar_auditoria(acao=acao, funcionario_id=funcionario_id, por_pagina=100)["data"]
    if email is not None:
        itens = [i for i in itens if (i.get("email_informado") or "").lower() == email.lower()
                 or email.lower() in (i.get("detalhe") or "").lower()]
    return itens


def _envelhecer_falhas(email: str, minutos: int) -> None:
    from app.database import modelos  # noqa: F401

    t = Base.metadata.tables["auditoria_acessos"]
    with engine.begin() as con:
        linhas = con.execute(
            t.select().where(func.lower(t.c.email_informado) == email.lower())
        ).mappings().all()
        for linha in linhas:
            con.execute(update(t).where(t.c.id == linha["id"])
                        .values(criado_em=linha["criado_em"] - timedelta(minutes=minutos)))


# ---------------------------------------------------------------------------
# Login e auditoria
# ---------------------------------------------------------------------------
class TestLogin:
    def test_login_ok(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        resposta = _login(cliente_http, f["email"], f["senha"])
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["funcionario"] == {"id": f["id"], "nome": f["nome"], "email": f["email"], "perfil": f["perfil"]}
        me = cliente_http.get("/v1/painel/me", headers={"Authorization": f"Bearer {corpo['token']}"})
        assert me.status_code == 200 and me.json()["id"] == f["id"]
        registros = _auditoria("login_ok", funcionario_id=f["id"])
        assert len(registros) == 1 and registros[0]["ip"]

    def test_login_email_maiusculo(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        assert _login(cliente_http, "  " + f["email"].upper() + " ", f["senha"]).status_code == 200

    def test_senha_errada_401_e_auditoria(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        senha_digitada = "Errada-" + uuid.uuid4().hex
        resposta = _login(cliente_http, f["email"], senha_digitada)
        assert resposta.status_code == 401
        erro = resposta.json()["error"]
        assert erro["status"] == 401 and erro["code"] and erro["message"]
        falhas = _auditoria("login_falha", email=f["email"])
        assert len(falhas) == 1
        assert falhas[0]["funcionario_id"] == f["id"]
        assert falhas[0]["ip"]
        assert senha_digitada not in str(falhas[0])
        assert consultas.contar_falhas_login(f["email"]) == 1

    def test_email_inexistente_mesma_resposta(self, cliente_http, criar_funcionario):
        f = criar_funcionario()
        inexistente = f"ninguem.{uuid.uuid4().hex[:8]}@bulbe.com.br"
        r1 = _login(cliente_http, f["email"], "senha-errada")
        r2 = _login(cliente_http, inexistente, "senha-errada")
        assert r1.status_code == r2.status_code == 401
        assert r1.json() == r2.json(), "Nao pode revelar se o e-mail existe."
        falhas = _auditoria("login_falha", email=inexistente)
        assert len(falhas) == 1 and falhas[0]["funcionario_id"] is None

    def test_validacao_do_corpo(self, cliente_http):
        assert _login(cliente_http, "", "x").status_code == 422
        assert cliente_http.post(ROTA, json={"email": "a@b.com"}).status_code == 422


# ---------------------------------------------------------------------------
# Bloqueio
# ---------------------------------------------------------------------------
class TestBloqueio:
    def test_bloqueia_na_sexta_tentativa_mesmo_com_senha_certa(self, cliente_http, criar_funcionario):
        f = criar_funcionario(prefixo="bloqueio")
        for i in range(5):
            # Mistura maiusculas/minusculas: a contagem nao diferencia.
            email = f["email"].upper() if i % 2 else f["email"]
            resposta = _login(cliente_http, email, f"errada-{i}")
            assert resposta.status_code == 401, (i, resposta.text)
        resposta = _login(cliente_http, f["email"], f["senha"])
        assert resposta.status_code == 429, resposta.text
        erro = resposta.json()["error"]
        assert erro == {"code": "LOGIN_BLOQUEADO", "message": erro["message"], "status": 429}
        assert erro["message"]
        retry_after = resposta.headers.get("retry-after")
        assert retry_after is not None and retry_after.isdigit()
        assert 0 < int(retry_after) <= 15 * 60
        assert "token" not in resposta.json()
        assert len(_auditoria("login_bloqueado", email=f["email"])) >= 1
        assert _auditoria("login_ok", funcionario_id=f["id"]) == []

    def test_quatro_falhas_nao_bloqueiam(self, cliente_http, criar_funcionario):
        f = criar_funcionario(prefixo="quatro")
        for i in range(4):
            assert _login(cliente_http, f["email"], f"errada-{i}").status_code == 401
        assert _login(cliente_http, f["email"], f["senha"]).status_code == 200

    def test_bloqueio_e_por_email(self, cliente_http, criar_funcionario):
        bloqueado, outro = criar_funcionario(prefixo="bloq"), criar_funcionario(prefixo="livre")
        for i in range(5):
            _login(cliente_http, bloqueado["email"], f"errada-{i}")
        assert _login(cliente_http, bloqueado["email"], bloqueado["senha"]).status_code == 429
        assert _login(cliente_http, outro["email"], outro["senha"]).status_code == 200

    def test_email_inexistente_tambem_bloqueia(self, cliente_http):
        email = f"robo.{uuid.uuid4().hex[:8]}@exemplo.com"
        for i in range(5):
            assert _login(cliente_http, email, f"x{i}").status_code == 401
        assert _login(cliente_http, email, "x").status_code == 429

    def test_desbloqueia_quando_a_janela_passa(self, cliente_http, criar_funcionario):
        f = criar_funcionario(prefixo="janela")
        for i in range(5):
            _login(cliente_http, f["email"], f"errada-{i}")
        assert _login(cliente_http, f["email"], f["senha"]).status_code == 429
        _envelhecer_falhas(f["email"], minutos=16)
        assert consultas.contar_falhas_login(f["email"]) == 0
        assert _login(cliente_http, f["email"], f["senha"]).status_code == 200


# ---------------------------------------------------------------------------
# Alerta por e-mail
# ---------------------------------------------------------------------------
class TestAlerta:
    def test_alerta_enviado_uma_vez_na_quarta_falha(self, cliente_http, criar_funcionario, configurar_smtp,
                                                     smtp_falso):
        config = configurar_smtp()
        f = criar_funcionario(prefixo="alerta")
        senhas = [f"Tentativa-{i}-{uuid.uuid4().hex[:6]}" for i in range(6)]
        for i in range(3):
            assert _login(cliente_http, f["email"], senhas[i]).status_code == 401
        assert smtp_falso.mensagens == [], "Ate 3 falhas nao ha alerta."

        assert _login(cliente_http, f["email"], senhas[3]).status_code == 401
        assert len(smtp_falso.mensagens) == 1, "Na 4a falha o alerta deve ser enviado."

        assert _login(cliente_http, f["email"], senhas[4]).status_code == 401
        assert _login(cliente_http, f["email"], senhas[5]).status_code == 429
        assert len(smtp_falso.mensagens) == 1, "No maximo 1 alerta por e-mail na janela."

        mensagem = smtp_falso.mensagens[0]
        conteudo = texto_do_email(mensagem)
        if not isinstance(mensagem, (str, bytes)):
            assert config["ALERTA_LOGIN_EMAIL"] in str(mensagem.get("To", ""))
        else:
            assert config["ALERTA_LOGIN_EMAIL"] in conteudo or smtp_falso.conexoes
        assert f["email"].lower() in conteudo.lower()
        assert "4" in conteudo  # quantidade de falhas
        assert "testclient" in conteudo  # IP do Request no TestClient
        for senha in senhas + [f["senha"], config["SMTP_SENHA"]]:
            assert senha not in conteudo, "O alerta nunca pode conter senha."
        assert smtp_falso.conexoes and smtp_falso.conexoes[0]["host"] == config["SMTP_HOST"]
        assert len(_auditoria("alerta_email", email=f["email"])) >= 1

    def test_sem_smtp_nao_quebra_e_registra(self, cliente_http, criar_funcionario, smtp_falso):
        f = criar_funcionario(prefixo="semsmtp")
        for i in range(4):
            assert _login(cliente_http, f["email"], f"errada-{i}").status_code == 401
        assert smtp_falso.mensagens == []
        registros = _auditoria("alerta_email", email=f["email"])
        assert len(registros) == 1
        assert registros[0]["detalhe"], "A auditoria deve dizer por que o alerta nao saiu."

    def test_erro_de_envio_nao_quebra_login(self, cliente_http, criar_funcionario, configurar_smtp, smtp_falso):
        import smtplib

        configurar_smtp()
        smtp_falso.falhar_com = smtplib.SMTPAuthenticationError(535, b"credenciais recusadas (simulado)")
        f = criar_funcionario(prefixo="erroenvio")
        for i in range(4):
            assert _login(cliente_http, f["email"], f"errada-{i}").status_code == 401
        assert smtp_falso.mensagens == []
        registros = _auditoria("alerta_email", email=f["email"])
        assert len(registros) == 1 and registros[0]["detalhe"]
        # O login continua funcionando com a senha certa.
        assert _login(cliente_http, f["email"], f["senha"]).status_code == 200
