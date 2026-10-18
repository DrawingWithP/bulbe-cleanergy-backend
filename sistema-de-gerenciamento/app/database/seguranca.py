"""
Camada de Persistencia, seguranca das senhas dos funcionarios do painel.

Usa somente a biblioteca padrao (hashlib/hmac/secrets).
Formato do hash salvo no banco: "pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>".
"""
import hashlib
import hmac
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACOES_PADRAO = 240_000
TAMANHO_SALT_BYTES = 16


def _derivar(senha: str, salt: bytes, iteracoes: int) -> bytes:
    """Aplica o PBKDF2-HMAC-SHA256 sobre a senha."""
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)


def gerar_hash_senha(senha: str) -> str:
    """Gera o hash da senha com salt aleatorio, no formato pbkdf2_sha256$iter$salt$hash."""
    salt = secrets.token_bytes(TAMANHO_SALT_BYTES)
    derivado = _derivar(senha, salt, ITERACOES_PADRAO)
    return f"{ALGORITMO}${ITERACOES_PADRAO}${salt.hex()}${derivado.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """
    Confere a senha contra o hash salvo (comparacao em tempo constante).
    Hash malformado ou algoritmo desconhecido devolve False (nunca levanta excecao).
    """
    try:
        algoritmo, iteracoes_txt, salt_hex, hash_hex = senha_hash.split("$")
        if algoritmo != ALGORITMO:
            return False
        iteracoes = int(iteracoes_txt)
        if iteracoes <= 0:
            return False
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
    except (AttributeError, ValueError):
        return False
    calculado = _derivar(senha, salt, iteracoes)
    return hmac.compare_digest(calculado, esperado)
