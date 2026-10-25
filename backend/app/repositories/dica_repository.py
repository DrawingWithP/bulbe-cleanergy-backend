"""
Camada de Persistencia, DicaRepository.
"""
from datetime import date
from app.domain.dica import Dica, DicaCreate, DicaUpdate


class DicaRepository:
    def __init__(self) -> None:
        self._dicas: dict[int, Dica] = {}
        self._proximo_id: int = 1

    def listar(self) -> list[Dica]:
        return list(self._dicas.values())

    def buscar_por_id(self, dica_id: int) -> Dica | None:
        return self._dicas.get(dica_id)

    def criar(self, dados: DicaCreate) -> Dica:
        dica = Dica(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )
        self._dicas[dica.id] = dica
        self._proximo_id += 1
        return dica

    def atualizar(self, dica_id: int, dados: DicaUpdate) -> Dica | None:
        dica_atual = self._dicas.get(dica_id)
        if dica_atual is None:
            return None
        dados_atualizados = dica_atual.model_dump()
        dados_atualizados.update(dados.model_dump(exclude_unset=True))
        dica_atualizada = Dica(**dados_atualizados)
        self._dicas[dica_id] = dica_atualizada
        return dica_atualizada

    def remover(self, dica_id: int) -> bool:
        if dica_id in self._dicas:
            del self._dicas[dica_id]
            return True
        return False


dica_repository = DicaRepository()
