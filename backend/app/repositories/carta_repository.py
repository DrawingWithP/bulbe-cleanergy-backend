"""
Camada de Persistência, CartaRepository.
"""
from app.domain.carta import Carta, SituacaoCarta, TipoCarta


class CartaRepository:
    def __init__(self) -> None:
        self._cartas: dict[str, Carta] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        c1 = Carta(
            id="a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            semana=3,
            tipo=TipoCarta.normal,
            situacao=SituacaoCarta.disponivel,
            disponivel_em="2026-06-12T09:00:00Z",
            aberta_em=None,
            cupom_id=None,
        )
        self._cartas[c1.id] = c1

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCarta | None = None,
    ) -> tuple[list[Carta], int]:
        todos = [c for c in self._cartas.values() if c.cliente_id == cliente_id]
        if situacao:
            todos = [c for c in todos if c.situacao == situacao]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, carta_id: str) -> Carta | None:
        return self._cartas.get(carta_id)

    def buscar_disponivel_cliente(self, cliente_id: str) -> Carta | None:
        for c in self._cartas.values():
            if c.cliente_id == cliente_id and c.situacao == SituacaoCarta.disponivel:
                return c
        return None

    def salvar(self, carta: Carta) -> Carta:
        self._cartas[carta.id] = carta
        return carta

    def atualizar(self, carta: Carta) -> Carta:
        self._cartas[carta.id] = carta
        return carta


carta_repository = CartaRepository()
