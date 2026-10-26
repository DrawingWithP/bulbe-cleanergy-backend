"""
Camada de Persistência, CupomRepository.
"""
from app.domain.cupom import Cupom, ParceiroResumoCupom, SituacaoCupom


class CupomRepository:
    def __init__(self) -> None:
        self._cupons: dict[str, Cupom] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        c1 = Cupom(
            id="f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            carta_id="a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
            tag="PARCERIA DROGARIA ARAÚJO",
            titulo="15% de desconto na Araújo",
            descricao="Use o cupom em qualquer loja física ou no app da Araújo.",
            codigo="BULBE15",
            parceiro=ParceiroResumoCupom(
                id="1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
                nome="Drogaria Araújo",
                categoria="Farmácia",
            ),
            situacao=SituacaoCupom.ativo,
            valido_ate="2026-11-15",
            dias_restantes=14,
            criado_em="2026-06-12T19:42:00Z",
        )
        self._cupons[c1.id] = c1

    def listar_por_cliente(
        self,
        cliente_id: str,
        page: int = 1,
        limit: int = 20,
        situacao: SituacaoCupom | None = None,
    ) -> tuple[list[Cupom], int]:
        todos = [
            c for c in self._cupons.values()
            if c.cliente_id == cliente_id and c.situacao != SituacaoCupom.descartado
        ]
        if situacao:
            todos = [c for c in todos if c.situacao == situacao]

        total = len(todos)
        inicio = (page - 1) * limit
        fim = inicio + limit
        return todos[inicio:fim], total

    def buscar_por_id(self, cupom_id: str) -> Cupom | None:
        c = self._cupons.get(cupom_id)
        if c and c.situacao != SituacaoCupom.descartado:
            return c
        return None

    def salvar(self, cupom: Cupom) -> Cupom:
        self._cupons[cupom.id] = cupom
        return cupom

    def atualizar(self, cupom: Cupom) -> Cupom:
        self._cupons[cupom.id] = cupom
        return cupom

    def descartar(self, cupom_id: str) -> bool:
        c = self._cupons.get(cupom_id)
        if c:
            c.situacao = SituacaoCupom.descartado
            return True
        return False


cupom_repository = CupomRepository()
