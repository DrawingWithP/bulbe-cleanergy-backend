"""
Camada de Persistência, ParceiroRepository.
"""
from app.domain.parceiro import Parceiro


class ParceiroRepository:
    def __init__(self) -> None:
        self._parceiros: dict[str, Parceiro] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        p1 = Parceiro(
            id="1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
            nome="Drogaria Araújo",
            categoria="Farmácia",
            logo_url="https://cdn.bulbeenergia.com.br/parceiros/araujo.png",
            ativo=True,
            criado_em="2026-05-20T12:00:00Z",
        )
        p2 = Parceiro(
            id="2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819",
            nome="Banco Inter",
            categoria="Banco",
            logo_url="https://cdn.bulbeenergia.com.br/parceiros/inter.png",
            ativo=True,
            criado_em="2026-05-21T10:00:00Z",
        )
        self._parceiros[p1.id] = p1
        self._parceiros[p2.id] = p2

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> tuple[list[Parceiro], int]:
        todos = list(self._parceiros.values())
        if categoria:
            todos = [p for p in todos if p.categoria.lower() == categoria.lower()]
        if ativo is not None:
            todos = [p for p in todos if p.ativo == ativo]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, parceiro_id: str) -> Parceiro | None:
        return self._parceiros.get(parceiro_id)

    def buscar_por_nome(self, nome: str) -> Parceiro | None:
        nome_limpo = nome.strip().lower()
        for p in self._parceiros.values():
            if p.nome.strip().lower() == nome_limpo:
                return p
        return None

    def criar(self, parceiro: Parceiro) -> Parceiro:
        self._parceiros[parceiro.id] = parceiro
        return parceiro

    def atualizar(self, parceiro: Parceiro) -> Parceiro:
        self._parceiros[parceiro.id] = parceiro
        return parceiro

    def remover(self, parceiro_id: str) -> bool:
        if parceiro_id in self._parceiros:
            del self._parceiros[parceiro_id]
            return True
        return False


parceiro_repository = ParceiroRepository()
