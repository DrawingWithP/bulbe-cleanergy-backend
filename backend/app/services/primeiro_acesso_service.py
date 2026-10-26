"""
Camada de Serviço, PrimeiroAcessoService (regras de negócio para US-09 e US-10).
"""
from datetime import datetime, timedelta, timezone
import random
import re
import uuid

from app.domain.primeiro_acesso import (
    ConfirmacaoRequest,
    ConfirmacaoResponse,
    SituacaoVerificacao,
    Verificacao,
    VerificacaoRequest,
    VerificacaoResponse,
)
from app.repositories.primeiro_acesso_repository import (
    PrimeiroAcessoRepository,
    primeiro_acesso_repository,
)


class ErroDeNegocio(Exception):
    """
    Erro de negócio com formato padronizado (Aula 10):
    code, message e status.
    """
    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class PrimeiroAcessoService:
    def __init__(self, repository: PrimeiroAcessoRepository) -> None:
        self._repository = repository

    def _validar_cpf(self, cpf: str) -> str:
        """Valida e retorna apenas os dígitos do CPF."""
        cpf_limpo = re.sub(r"\D", "", cpf)
        if len(cpf_limpo) != 11:
            raise ErroDeNegocio(
                code="CPF_INVALIDO",
                message="CPF informado é inválido. Deve conter 11 dígitos.",
                status=400,
            )
        # Rejeita CPFs com todos os dígitos iguais (ex: 00000000000)
        if len(set(cpf_limpo)) == 1:
            raise ErroDeNegocio(
                code="CPF_INVALIDO",
                message="CPF informado é inválido.",
                status=400,
            )
        return cpf_limpo

    def _mascarar_destino(self, telefone: str) -> str:
        """Gera máscara para exibição segura, ex: (31) 98888-1234 -> (31) *****-1234."""
        digitos = re.sub(r"\D", "", telefone)
        if len(digitos) >= 10:
            ddd = digitos[:2]
            ultimos_quatro = digitos[-4:]
            return f"({ddd}) *****-{ultimos_quatro}"
        return "(**) *****-****"

    def solicitar_verificacao(self, dados: VerificacaoRequest) -> VerificacaoResponse:
        """
        US-09: Atende o fluxo de 'É minha primeira vez no app'.
        Valida o CPF, confere se o cliente existe e gera o código de verificação.
        """
        cpf_valido = self._validar_cpf(dados.cpf)
        cliente = self._repository.buscar_cliente_por_cpf(cpf_valido)

        if not cliente:
            raise ErroDeNegocio(
                code="CLIENTE_NAO_ENCONTRADO",
                message="CPF não encontrado na base de clientes da Bulbe.",
                status=404,
            )

        # Geração do código numérico de 6 dígitos
        codigo = f"{random.randint(100000, 999999)}"
        agora = datetime.now(timezone.utc)
        expiracao = agora + timedelta(minutes=15)
        destino_mascarado = self._mascarar_destino(cliente.get("telefone", ""))
        verificacao_id = str(uuid.uuid4())

        nova_verificacao = Verificacao(
            id=verificacao_id,
            cliente_id=str(cliente["id"]),
            cpf=cpf_valido,
            canal=dados.canal.value if hasattr(dados.canal, "value") else str(dados.canal),
            codigo=codigo,
            destino_mascarado=destino_mascarado,
            expira_em=expiracao,
            tentativas=0,
            situacao=SituacaoVerificacao.pendente,
            criado_em=agora,
        )

        self._repository.salvar_verificacao(nova_verificacao)

        return VerificacaoResponse(
            verificacao_id=nova_verificacao.id,
            canal=nova_verificacao.canal,
            destino_mascarado=nova_verificacao.destino_mascarado,
            expira_em=nova_verificacao.expira_em.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def confirmar_codigo(self, dados: ConfirmacaoRequest) -> ConfirmacaoResponse:
        """
        US-10: Confirma o código recebido pelo cliente e habilita o acesso ao app.
        """
        verificacao = self._repository.buscar_verificacao_por_id(dados.verificacao_id)

        if not verificacao:
            raise ErroDeNegocio(
                code="RECURSO_NAO_ENCONTRADO",
                message="Solicitação de verificação não encontrada.",
                status=404,
            )

        if verificacao.situacao == SituacaoVerificacao.usada:
            raise ErroDeNegocio(
                code="CODIGO_JA_UTILIZADO",
                message="Este código de confirmação já foi utilizado.",
                status=400,
            )

        agora = datetime.now(timezone.utc)
        expira_em = (
            verificacao.expira_em
            if verificacao.expira_em.tzinfo
            else verificacao.expira_em.replace(tzinfo=timezone.utc)
        )

        if agora > expira_em:
            verificacao.situacao = SituacaoVerificacao.expirada
            self._repository.atualizar_verificacao(verificacao)
            raise ErroDeNegocio(
                code="CODIGO_EXPIRADO",
                message="Código de confirmação expirado.",
                status=410,
            )

        if verificacao.codigo != dados.codigo.strip():
            verificacao.tentativas += 1
            self._repository.atualizar_verificacao(verificacao)
            raise ErroDeNegocio(
                code="CODIGO_INVALIDO",
                message="Código de confirmação inválido.",
                status=400,
            )

        # Código válido: habilita o acesso e atualiza status da verificação
        verificacao.situacao = SituacaoVerificacao.usada
        self._repository.atualizar_verificacao(verificacao)
        self._repository.habilitar_acesso_cliente(verificacao.cliente_id)

        return ConfirmacaoResponse(
            cliente_id=verificacao.cliente_id,
            acesso_habilitado=True,
            confirmado_em=agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


# Instância compartilhada por toda a aplicação
primeiro_acesso_service = PrimeiroAcessoService(primeiro_acesso_repository)
