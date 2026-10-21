"""
Camada de Persistencia, AdesaoRepository.
"""
from datetime import date
from app.domain.adesao import Adesao, AdesaoCreate, AdesaoUpdate
class AdesaoRepository:
    def __init__(self) -> None:
        self._adesoes: dict[int, Adesao] = {}
        self._proximo_id: int = 1
    def listar(self) -> list[Adesao]:
        return list(self._adesoes.values())
    def buscar_por_id(self, adesao_id: int) -> Adesao | None:
        return self._adesoes.get(adesao_id)
    def criar(self, dados: AdesaoCreate) -> Adesao:
        adesao = Adesao(
            id=self._proximo_id,
            data_ativacao=date.today(),
            **dados.model_dump(),
        )
        self._adesoes[adesao.id] = adesao
        self._proximo_id += 1
        return adesao
    def atualizar(self, adesao_id: int, dados: AdesaoUpdate) -> Adesao | None:
        adesao_atual = self._adesoes.get(adesao_id)
        if adesao_atual is None:
            return None
        dados_atualizados = adesao_atual.model_dump()
        dados_atualizados.update(dados.model_dump(exclude_unset=True))
        adesao_atualizada = Adesao(**dados_atualizados)
        self._adesoes[adesao_id] = adesao_atualizada
        return adesao_atualizada
    def remover(self, adesao_id: int) -> bool:
        if adesao_id not in self._adesoes:
            return False
        del self._adesoes[adesao_id]
        return True
# Uma unica instancia compartilhada por toda a aplicacao.
adesao_repository = AdesaoRepository()