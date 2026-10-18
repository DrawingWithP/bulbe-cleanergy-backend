"""
Erros de negocio do Sistema de Gerenciamento.

Mesmo formato padronizado usado no back-end do app (code, message e status),
mas definido aqui para que o sistema nao dependa do codigo do app.
"""


class ErroDeNegocio(Exception):
    """Erro de negocio com formato padronizado: code, message e status."""

    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)
