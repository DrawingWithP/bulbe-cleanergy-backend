"""
Camada de Persistência, AtivacaoRepository.
"""
from app.domain.ativacao import AtivacaoCliente


class AtivacaoRepository:
    def __init__(self) -> None:
        self._ativacoes: dict[str, AtivacaoCliente] = {}
        self._inicializar_mock()

    def _inicializar_mock(self) -> None:
        ativacao_padrao = AtivacaoCliente(
            cliente_id="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
            etapa_atual=2,
            distribuidora="CEMIG",
            prazo_ativacao_dias=90,
            previsao_conclusao="2026-07-31",
            atualizado_em="2026-08-18T08:00:00Z",
            observacoes=[],
        )
        self._ativacoes[ativacao_padrao.cliente_id] = ativacao_padrao

    def buscar_por_cliente_id(self, cliente_id: str) -> AtivacaoCliente | None:
        return self._ativacoes.get(cliente_id)

    def salvar_ou_atualizar(self, ativacao: AtivacaoCliente) -> AtivacaoCliente:
        self._ativacoes[ativacao.cliente_id] = ativacao
        return ativacao


ativacao_repository = AtivacaoRepository()
