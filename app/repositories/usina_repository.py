"""
Camada de Persistencia, UsinaRepository.
"""
from datetime import date
from app.domain.usina import Usina, UsinaCreate, UsinaUpdate
class UsinaRepository:
    def __init__(self) -> None:
        self._usinas: dict[int, Usina] = {}
        self._proximo_id: int = 1
    def listar(self) -> list[Usina]:
        return list(self._usinas.values())
    def buscar_por_id(self, usina_id: int) -> Usina | None:
        return self._usinas.get(usina_id)
    def criar(self, dados: UsinaCreate) -> Usina:
        usina = Usina(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )
        self._usinas[usina.id] = usina
        self._proximo_id += 1
        return usina
    def atualizar(self, usina_id: int, dados: UsinaUpdate) -> Usina | None:
        usina_atual = self._usinas.get(usina_id)
        if usina_atual is None:
            return None
        dados_atualizados = usina_atual.model_dump()
        dados_atualizados.update(dados.model_dump(exclude_unset=True))
        usina_atualizada = Usina(**dados_atualizados)
        self._usinas[usina_id] = usina_atualizada
        return usina_atualizada
    def remover(self, usina_id: int) -> bool:
        if usina_id not in self._usinas:
            return False
        del self._usinas[usina_id]
        return True
# Uma unica instancia compartilhada por toda a aplicacao.
usina_repository = UsinaRepository()