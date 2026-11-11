"""
Camada de Serviço, ClienteService
(regras de negócio para US-05, US-31 e US-34).
"""

from datetime import datetime, timezone
import re
import uuid

from app.domain.cliente import (
    Cliente,
    ClienteCreate,
    ClienteCriadoResponse,
    ClienteListaPaginada,
    ClienteResumo,
    ClienteUpdate,
    StatusCliente,
)
from app.repositories.cliente_repository import (
    ClienteRepository,
    cliente_repository,
)


class ErroDeNegocio(Exception):
    """
    Erro de negócio com formato padronizado:
    code, message e status.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class ClienteService:
    def __init__(
        self,
        repository: ClienteRepository,
    ) -> None:
        self._repository = repository

    def _validar_cpf(self, cpf: str) -> str:
        """
        Remove a formatação do CPF e valida seus
        dígitos verificadores.
        """

        cpf_limpo = re.sub(r"\D", "", cpf)

        if (
            len(cpf_limpo) != 11
            or len(set(cpf_limpo)) == 1
        ):
            raise ErroDeNegocio(
                code="CPF_INVALIDO",
                message="CPF informado é inválido.",
                status=400,
            )

        # Validação do primeiro dígito verificador.
        soma = sum(
            int(cpf_limpo[i]) * (10 - i)
            for i in range(9)
        )

        resto = soma % 11
        primeiro_digito = (
            0 if resto < 2 else 11 - resto
        )

        if primeiro_digito != int(cpf_limpo[9]):
            raise ErroDeNegocio(
                code="CPF_INVALIDO",
                message="CPF informado é inválido.",
                status=400,
            )

        # Validação do segundo dígito verificador.
        soma = sum(
            int(cpf_limpo[i]) * (11 - i)
            for i in range(10)
        )

        resto = soma % 11
        segundo_digito = (
            0 if resto < 2 else 11 - resto
        )

        if segundo_digito != int(cpf_limpo[10]):
            raise ErroDeNegocio(
                code="CPF_INVALIDO",
                message="CPF informado é inválido.",
                status=400,
            )

        return cpf_limpo

    def listar(
        self,
        page: int = 1,
        limit: int = 20,
        status_filtro: StatusCliente | None = None,
    ) -> ClienteListaPaginada:
        """
        Lista clientes utilizando paginação
        e filtro opcional por status.
        """

        if page < 1:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message=(
                    "O número da página deve ser "
                    "maior ou igual a 1."
                ),
                status=400,
            )

        if limit < 1 or limit > 100:
            raise ErroDeNegocio(
                code="PARAMETROS_INVALIDOS",
                message="O limite deve estar entre 1 e 100.",
                status=400,
            )

        clientes, total = self._repository.listar(
            page,
            limit,
            status_filtro,
        )

        itens_resumo = [
            ClienteResumo(
                id=cliente.id,
                nome=cliente.nome,
                email=cliente.email,
                cpf=cliente.cpf,
                telefone=cliente.telefone,
                cidade=cliente.endereco.cidade,
                uf=cliente.endereco.uf,
                status=cliente.status,
                criado_em=cliente.criado_em,
            )
            for cliente in clientes
        ]

        return ClienteListaPaginada(
            data=itens_resumo,
            page=page,
            total=total,
        )

    def buscar_por_id(
        self,
        cliente_id: str,
    ) -> Cliente:
        """
        Retorna um cliente pelo ID.
        """

        cliente = self._repository.buscar_por_id(
            cliente_id
        )

        if not cliente:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cliente com id '{cliente_id}' "
                    "não foi encontrado."
                ),
                status=404,
            )

        return cliente

    def criar(
        self,
        dados: ClienteCreate,
    ) -> ClienteCriadoResponse:
        """
        Cria um novo cliente após validar CPF
        e verificar duplicidades.
        """

        cpf_limpo = self._validar_cpf(dados.cpf)

        cliente_com_cpf = (
            self._repository.buscar_por_cpf(cpf_limpo)
        )

        if cliente_com_cpf:
            raise ErroDeNegocio(
                code="CONFLITO_DADOS",
                message=(
                    "Já existe um cliente cadastrado "
                    "com este CPF."
                ),
                status=409,
            )

        cliente_com_email = (
            self._repository.buscar_por_email(dados.email)
        )

        if cliente_com_email:
            raise ErroDeNegocio(
                code="CONFLITO_DADOS",
                message=(
                    "Já existe um cliente cadastrado "
                    "com este e-mail."
                ),
                status=409,
            )

        novo_id = str(uuid.uuid4())

        criado_em = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        cliente = Cliente(
            id=novo_id,
            nome=dados.nome,
            email=dados.email,
            cpf=cpf_limpo,
            telefone=dados.telefone,
            endereco=dados.endereco,
            distribuidora=dados.distribuidora,
            numero_instalacao=dados.numero_instalacao,
            status=StatusCliente.em_ativacao,
            acesso_habilitado=False,
            criado_em=criado_em,
        )

        self._repository.criar(cliente)

        return ClienteCriadoResponse(
            id=cliente.id,
            nome=cliente.nome,
            email=cliente.email,
            status=cliente.status,
            criado_em=cliente.criado_em,
        )

    def atualizar(
        self,
        cliente_id: str,
        dados: ClienteUpdate,
    ) -> Cliente:
        """
        Atualiza os dados permitidos de um cliente.
        """

        cliente_atual = self.buscar_por_id(cliente_id)

        dados_dict = dados.model_dump(
            exclude_unset=True
        )

        if not dados_dict:
            return cliente_atual

        if (
            "nome" in dados_dict
            and dados_dict["nome"] is not None
        ):
            cliente_atual.nome = dados_dict["nome"]

        if (
            "telefone" in dados_dict
            and dados_dict["telefone"] is not None
        ):
            cliente_atual.telefone = dados_dict["telefone"]

        if (
            "distribuidora" in dados_dict
            and dados_dict["distribuidora"] is not None
        ):
            cliente_atual.distribuidora = (
                dados_dict["distribuidora"]
            )

        if (
            "numero_instalacao" in dados_dict
            and dados_dict["numero_instalacao"] is not None
        ):
            cliente_atual.numero_instalacao = (
                dados_dict["numero_instalacao"]
            )

        if dados.endereco is not None:
            endereco_dict = dados.endereco.model_dump(
                exclude_unset=True
            )

            for campo, valor in endereco_dict.items():
                if valor is not None:
                    setattr(
                        cliente_atual.endereco,
                        campo,
                        valor,
                    )

        return self._repository.atualizar(
            cliente_atual
        )

    def remover(
        self,
        cliente_id: str,
    ) -> None:
        """
        Remove um cliente pelo ID.
        """

        removido = self._repository.remover(
            cliente_id
        )

        if not removido:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message=(
                    f"Cliente com id '{cliente_id}' "
                    "não foi encontrado."
                ),
                status=404,
            )


cliente_service = ClienteService(cliente_repository)
