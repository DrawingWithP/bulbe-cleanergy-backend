"""
Camada de Persistência, ClienteRepository.
"""
import re
from app.domain.cliente import Cliente, Endereco, StatusCliente


class ClienteRepository:
    def __init__(self) -> None:
        self._clientes: dict[str, Cliente] = {}
        self._inicializar_dados_mock()

    def _inicializar_dados_mock(self) -> None:
        cliente_padrao = Cliente(
            id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            nome="Marcos Andrade",
            email="marcos.andrade@email.com",
            cpf="12345678900",
            telefone="(31) 98888-1234",
            endereco=Endereco(
                cep="30130-010",
                logradouro="Av. Afonso Pena",
                numero="1000",
                complemento="Apto 302",
                bairro="Centro",
                cidade="Belo Horizonte",
                uf="MG",
            ),
            distribuidora="CEMIG",
            numero_instalacao="3001234567",
            status=StatusCliente.em_ativacao,
            acesso_habilitado=False,
            criado_em="2026-05-02T13:20:00Z",
        )
        self._clientes[cliente_padrao.id] = cliente_padrao

    def _normalizar_cpf(self, cpf: str) -> str:
        return re.sub(r"\D", "", cpf)

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> tuple[list[Cliente], int]:
        todos = list(self._clientes.values())
        if status_filtro:
            todos = [c for c in todos if c.status == status_filtro]
        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, cliente_id: str) -> Cliente | None:
        return self._clientes.get(cliente_id)

    def buscar_por_cpf(self, cpf: str) -> Cliente | None:
        cpf_limpo = self._normalizar_cpf(cpf)
        for cliente in self._clientes.values():
            if self._normalizar_cpf(cliente.cpf) == cpf_limpo:
                return cliente
        return None

    def buscar_por_email(self, email: str) -> Cliente | None:
        email_limpo = email.strip().lower()
        for cliente in self._clientes.values():
            if cliente.email.strip().lower() == email_limpo:
                return cliente
        return None

    def criar(self, cliente: Cliente) -> Cliente:
        self._clientes[cliente.id] = cliente
        return cliente

    def atualizar(self, cliente: Cliente) -> Cliente:
        self._clientes[cliente.id] = cliente
        return cliente

    def remover(self, cliente_id: str) -> bool:
        if cliente_id in self._clientes:
            del self._clientes[cliente_id]
            return True
        return False


cliente_repository = ClienteRepository()
