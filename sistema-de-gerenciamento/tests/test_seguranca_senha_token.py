"""
Seguranca: hash de senha (app.database.seguranca), token do painel (app.painel.auth)
e protecao das rotas (401 sem token/token invalido, 403 para quem nao e admin).
"""
import base64
import json
import re
import time

import pytest
from fastapi import HTTPException

from app.database.seguranca import gerar_hash_senha, verificar_senha
from app.painel import auth
from app.painel.auth import criar_token, exigir_admin, validar_token

FORMATO_HASH = re.compile(r"^pbkdf2_sha256\$(\d+)\$([0-9a-f]+)\$([0-9a-f]{64})$")


def _erro_padrao(resposta, status: int) -> dict:
    """Confere o formato {"error": {code, message, status}} e devolve o objeto error."""
    assert resposta.status_code == status, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {"error"}, corpo
    erro = corpo["error"]
    assert isinstance(erro.get("code"), str) and erro["code"]
    assert isinstance(erro.get("message"), str) and erro["message"]
    assert erro.get("status") == status
    return erro


# ---------------------------------------------------------------------------
# Hash de senha
# ---------------------------------------------------------------------------
class TestHashSenha:
    def test_formato_do_hash(self):
        senha_hash = gerar_hash_senha("Senha#Forte1")
        casamento = FORMATO_HASH.match(senha_hash)
        assert casamento, senha_hash
        assert int(casamento.group(1)) > 0
        assert len(casamento.group(2)) >= 16  # salt de pelo menos 8 bytes

    def test_salt_aleatorio(self):
        assert gerar_hash_senha("mesma-senha") != gerar_hash_senha("mesma-senha")

    def test_verifica_senha_certa_e_errada(self):
        senha_hash = gerar_hash_senha("bulbe@2026")
        assert verificar_senha("bulbe@2026", senha_hash) is True
        assert verificar_senha("bulbe@2025", senha_hash) is False
        assert verificar_senha("", senha_hash) is False

    def test_senha_com_acentos(self):
        senha_hash = gerar_hash_senha("çãoéü-Senha")
        assert verificar_senha("çãoéü-Senha", senha_hash) is True
        assert verificar_senha("caoeu-Senha", senha_hash) is False

    @pytest.mark.parametrize("hash_invalido", [
        "", "lixo", "pbkdf2_sha256$abc$00$00", "md5$1$00$00", "pbkdf2_sha256$0$00$00",
        "pbkdf2_sha256$1000$zz$zz", "a$b$c$d$e",
    ])
    def test_hash_malformado_devolve_false_sem_excecao(self, hash_invalido):
        assert verificar_senha("qualquer", hash_invalido) is False


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------
FUNCIONARIO = {"id": 99, "nome": "Pessoa Teste", "email": "pessoa@bulbe.com.br", "perfil": "atendimento"}


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _d64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


class TestToken:
    def test_token_valido_devolve_funcionario(self):
        token = criar_token(FUNCIONARIO)
        assert validar_token(token) == FUNCIONARIO

    def test_token_ignora_campos_extras(self):
        token = criar_token({**FUNCIONARIO, "senha_hash": "nao-deve-ir", "ativo": True})
        assert validar_token(token) == FUNCIONARIO
        assert "nao-deve-ir" not in token
        assert "nao-deve-ir" not in _d64(token.split(".")[0]).decode("utf-8", "replace")

    def test_payload_adulterado_e_recusado(self):
        token = criar_token(FUNCIONARIO)
        corpo, assinatura = token.split(".")
        payload = json.loads(_d64(corpo))
        payload["perfil"] = "admin"
        corpo_falso = _b64(json.dumps(payload, separators=(",", ":")).encode())
        assert validar_token(f"{corpo_falso}.{assinatura}") is None

    def test_assinatura_adulterada_e_recusada(self):
        token = criar_token(FUNCIONARIO)
        corpo, assinatura = token.split(".")
        trocado = ("A" if assinatura[0] != "A" else "B") + assinatura[1:]
        assert validar_token(f"{corpo}.{trocado}") is None

    def test_token_de_outro_segredo_e_recusado(self, monkeypatch):
        monkeypatch.setenv("PAINEL_SECRET", "outro-segredo-qualquer-0000000000000000")
        if hasattr(auth, "PAINEL_SECRET"):
            monkeypatch.setattr(auth, "PAINEL_SECRET", "outro-segredo-qualquer-0000000000000000")
        token_outro = criar_token(FUNCIONARIO)
        monkeypatch.undo()
        assert validar_token(token_outro) is None

    @pytest.mark.parametrize("token", [
        "", "abc", "a.b", "a.b.c", "...", ".", "x" * 5000, "eyJhbGciOiJIUzI1NiJ9.e30.abc",
    ])
    def test_tokens_malformados(self, token):
        assert validar_token(token) is None

    def test_token_expirado(self, monkeypatch):
        agora = time.time()
        with monkeypatch.context() as m:
            m.setattr(time, "time", lambda: agora - 8 * 3600 - 60)
            token = criar_token(FUNCIONARIO)
        assert validar_token(token) is None

    def test_token_ainda_valido_antes_de_8_horas(self, monkeypatch):
        agora = time.time()
        with monkeypatch.context() as m:
            m.setattr(time, "time", lambda: agora - 8 * 3600 + 120)
            token = criar_token(FUNCIONARIO)
        assert validar_token(token) == FUNCIONARIO

    def test_exigir_admin(self):
        admin = {**FUNCIONARIO, "perfil": "admin"}
        assert exigir_admin(admin) == admin
        with pytest.raises(HTTPException) as erro:
            exigir_admin(FUNCIONARIO)
        assert erro.value.status_code == 403


# ---------------------------------------------------------------------------
# Rotas protegidas
# ---------------------------------------------------------------------------
ROTAS_GET_PROTEGIDAS = [
    "/v1/painel/me",
    "/v1/painel/metricas",
    "/v1/painel/clientes",
    "/v1/painel/clientes/parados",
    "/v1/painel/clientes/qualquer-id",
    "/v1/painel/ativacoes/resumo",
    "/v1/painel/adesoes",
    "/v1/painel/atendimentos",
    "/v1/painel/usinas",
    "/v1/painel/parceiros",
    "/v1/painel/dicas",
    "/v1/painel/auditoria",
    "/v1/painel/uso-chatbot",
    "/v1/painel/chat/sugestoes",
    "/v1/painel/chat/conversas",
    "/v1/painel/chat/conversas/qualquer-id",
]

ROTAS_POST_PROTEGIDAS = [
    ("/v1/painel/admin/expurgo", None),
    ("/v1/painel/chat", {"mensagem": "oi"}),
    ("/v1/painel/chat/stream", {"mensagem": "oi"}),
]


class TestRotasProtegidas:
    @pytest.mark.parametrize("rota", ROTAS_GET_PROTEGIDAS)
    def test_get_sem_token_401(self, cliente_http, rota):
        _erro_padrao(cliente_http.get(rota), 401)

    @pytest.mark.parametrize("rota,corpo", ROTAS_POST_PROTEGIDAS)
    def test_post_sem_token_401(self, cliente_http, rota, corpo):
        _erro_padrao(cliente_http.post(rota, json=corpo), 401)

    @pytest.mark.parametrize("cabecalho", [
        "Basic dXN1YXJpbzpzZW5oYQ==", "Bearer", "Bearer ", "Token abc", "Bearer abc.def",
    ])
    def test_cabecalho_invalido_401(self, cliente_http, cabecalho):
        _erro_padrao(cliente_http.get("/v1/painel/me", headers={"Authorization": cabecalho}), 401)

    def test_token_adulterado_401(self, cliente_http, token_atendimento):
        corpo, assinatura = token_atendimento.split(".")
        payload = json.loads(_d64(corpo))
        payload["perfil"] = "admin"
        falso = _b64(json.dumps(payload, separators=(",", ":")).encode()) + "." + assinatura
        _erro_padrao(cliente_http.get("/v1/painel/auditoria", headers={"Authorization": f"Bearer {falso}"}), 401)

    def test_token_expirado_401(self, cliente_http, funcionario_admin, monkeypatch):
        agora = time.time()
        with monkeypatch.context() as m:
            m.setattr(time, "time", lambda: agora - 9 * 3600)
            token = criar_token(funcionario_admin)
        _erro_padrao(cliente_http.get("/v1/painel/me", headers={"Authorization": f"Bearer {token}"}), 401)

    def test_401_traz_www_authenticate(self, cliente_http):
        resposta = cliente_http.get("/v1/painel/me")
        assert resposta.status_code == 401
        assert resposta.headers.get("www-authenticate", "").lower().startswith("bearer")

    def test_me_com_token_valido(self, cliente_http, cab_atendimento, funcionario_atendimento):
        resposta = cliente_http.get("/v1/painel/me", headers=cab_atendimento)
        assert resposta.status_code == 200
        assert resposta.json() == funcionario_atendimento

    @pytest.mark.parametrize("metodo,rota", [
        ("get", "/v1/painel/auditoria"),
        ("get", "/v1/painel/uso-chatbot"),
        ("post", "/v1/painel/admin/expurgo"),
    ])
    def test_rotas_de_admin_403_para_atendimento(self, cliente_http, cab_atendimento, metodo, rota):
        resposta = getattr(cliente_http, metodo)(rota, headers=cab_atendimento)
        _erro_padrao(resposta, 403)
