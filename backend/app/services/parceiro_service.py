"""
Camada de Serviço, ParceiroService (regras de negócio para US-02, US-24, US-25, US-26 e US-33).
"""
from datetime import datetime, timezone
import uuid

from app.domain.parceiro import (
    Parceiro,
    ParceiroCreate,
    ParceiroCriadoResponse,
    ParceiroListaPaginada,
    ParceiroUpdate,
)
from app.repositories.parceiro_repository import ParceiroRepository, parceiro_repository


class ErroDeNegocio(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class ParceiroService:
    def __init__(self, repository: ParceiroRepository) -> None:
        self._repository = repository

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        categoria: str | None = None,
        ativo: bool | None = None,
    ) -> ParceiroListaPaginada:
        """US-02 / US-33: Lista os parceiros do Clube Bulbe."""
        if page < 1 or limit < 1 or limit > 100:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message="Parâmetros de paginação inválidos.",
                status=400,
            )

        parceiros, total = self._repository.listar(page, limit, categoria, ativo)
        return ParceiroListaPaginada(data=parceiros, page=page, total=total)

    def buscar_por_id(self, parceiro_id: str) -> Parceiro:
        """US-25: Consulta dados de um parceiro específico."""
        parceiro = self._repository.buscar_por_id(parceiro_id)
        if not parceiro:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Parceiro com id '{parceiro_id}' não foi encontrado.",
                status=404,
            )
        return parceiro

    def criar(self, dados: ParceiroCreate) -> ParceiroCriadoResponse:
        """US-24: Cadastra um novo parceiro do Clube Bulbe."""
        existente = self._repository.buscar_por_nome(dados.nome)
        if existente:
            raise ErroDeNegocio(
                code="CONFLITO_DADOS",
                message=f"Já existe um parceiro cadastrado com o nome '{dados.nome}'.",
                status=409,
            )

        novo_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        parceiro = Parceiro(
            id=novo_id,
            nome=dados.nome,
            categoria=dados.categoria,
            logo_url=dados.logo_url,
            ativo=dados.ativo,
            criado_em=criado_em,
        )
        self._repository.criar(parceiro)

        return ParceiroCriadoResponse(
            id=parceiro.id,
            nome=parceiro.nome,
            categoria=parceiro.categoria,
            ativo=parceiro.ativo,
            criado_em=parceiro.criado_em,
        )

    def atualizar(self, parceiro_id: str, dados: ParceiroUpdate) -> Parceiro:
        parceiro_atual = self.buscar_por_id(parceiro_id)

        dados_dict = dados.model_dump(exclude_unset=True)
        if not dados_dict:
            return parceiro_atual

        if "nome" in dados_dict and dados_dict["nome"]:
            parceiro_atual.nome = dados_dict["nome"]
        if "categoria" in dados_dict and dados_dict["categoria"]:
            parceiro_atual.categoria = dados_dict["categoria"]
        if "logo_url" in dados_dict:
            parceiro_atual.logo_url = dados_dict["logo_url"]
        if "ativo" in dados_dict and dados_dict["ativo"] is not None:
            parceiro_atual.ativo = dados_dict["ativo"]

        parceiro_atual.atualizado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return self._repository.atualizar(parceiro_atual)

    def remover(self, parceiro_id: str) -> None:
        """US-26: Remove um parceiro do Clube Bulbe."""
        removido = self._repository.remover(parceiro_id)
        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=f"Parceiro com id '{parceiro_id}' não foi encontrado.",
                status=404,
            )


parceiro_service = ParceiroService(parceiro_repository)
