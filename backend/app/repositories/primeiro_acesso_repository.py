"""
Camada de Persistência, PrimeiroAcessoRepository.
"""
import re
from typing import Any
from app.domain.primeiro_acesso import Verificacao


class PrimeiroAcessoRepository:
    def __init__(self) -> None:
        self._verificacoes: dict[str, Verificacao] = {}
        # Base inicial de clientes simulados cadastrados na Bulbe
        self._clientes: list[dict[str, Any]] = [
            {
                "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
                "nome": "Marcos Andrade",
                "cpf": "12345678900",
                "telefone": "(31) 98888-1234",
                "email": "marcos.andrade@email.com",
                "acesso_habilitado": False,
            },
            {
                "id": "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22",
                "nome": "Ana Carolina Souza",
                "cpf": "98765432100",
                "telefone": "(31) 97777-4321",
                "email": "ana.souza@email.com",
                "acesso_habilitado": False,
            },
        ]

    def _normalizar_cpf(self, cpf: str) -> str:
        return re.sub(r"\D", "", cpf)

    def buscar_cliente_por_cpf(self, cpf: str) -> dict[str, Any] | None:
        """Busca um cliente cadastrado pelo CPF (apenas dígitos)."""
        cpf_limpo = self._normalizar_cpf(cpf)
        for cliente in self._clientes:
            if self._normalizar_cpf(cliente["cpf"]) == cpf_limpo:
                return cliente
        return None

    def adicionar_cliente_mock(self, cliente: dict[str, Any]) -> None:
        """Adiciona ou atualiza um cliente mock para fins de teste."""
        self._clientes.append(cliente)

    def salvar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        """Salva uma nova verificação."""
        self._verificacoes[verificacao.id] = verificacao
        return verificacao

    def buscar_verificacao_por_id(self, verificacao_id: str) -> Verificacao | None:
        """Retorna uma verificação existente pelo ID."""
        return self._verificacoes.get(verificacao_id)

    def atualizar_verificacao(self, verificacao: Verificacao) -> Verificacao:
        """Atualiza o registro de verificação."""
        self._verificacoes[verificacao.id] = verificacao
        return verificacao

    def habilitar_acesso_cliente(self, cliente_id: str) -> bool:
        """Marca o acesso do cliente como habilitado."""
        for cliente in self._clientes:
            if cliente["id"] == cliente_id:
                cliente["acesso_habilitado"] = True
                return True
        return False


# Instância compartilhada do repositório
primeiro_acesso_repository = PrimeiroAcessoRepository()
