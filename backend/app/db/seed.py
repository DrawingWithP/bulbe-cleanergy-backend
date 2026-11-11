"""
Seed: popula o banco com dados ficticios para a demo da Sprint Review.

Uso (na pasta backend/, depois de "alembic upgrade head"):
    python -m app.db.seed

Idempotente: pode rodar quantas vezes quiser.
So insere o que ainda nao existe e nao desfaz o que foi
alterado durante a demonstracao.

Os dados sao ficticios e correspondem aos registros que antes
ficavam nos repositorios em memoria.

Usuario de demonstracao do painel:
    Endpoint: POST /v1/auth/login
    Email: admin@bulbe.com.br
    Senha: bulbe12345
"""

from datetime import date
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.security import gerar_hash_senha
from app.db.database import SessionLocal, engine
from app.db.models import (
    AdesaoModel,
    AtivacaoModel,
    CartaModel,
    ClienteModel,
    CupomModel,
    DicaModel,
    OfensivaClubeModel,
    ParceiroModel,
    UsinaModel,
    UsuarioModel,
)


ID_MARCOS = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
ID_ANA = "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22"

ID_ARAUJO = "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9"
ID_INTER = "2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819"
ID_LIVELO = "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06"

ID_CARTA_MARCOS = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"
ID_CUPOM_MARCOS = "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"

EMAIL_ADMIN = "admin@bulbe.com.br"
SENHA_ADMIN = "bulbe12345"

CPF_MARCOS = "52998224725"
CPF_ANA = "11144477735"
CPF_ADESAO = "16899535009"

SVG_LAMPADA = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'viewBox="0 0 24 24">'
    '<path d="M9 21h6v-1H9v1zm3-19a7 7 0 0 0-4 '
    '12.7V17h8v-2.3A7 7 0 0 0 12 2z"/>'
    "</svg>"
)


def _inserir_por_id(
    session: Session,
    modelo_cls: type,
    id_valor: Any,
    **campos: Any,
) -> bool:
    """
    Insere uma linha caso a chave primaria ainda nao exista.

    Retorna True quando um registro novo for inserido.
    """

    if session.get(modelo_cls, id_valor) is not None:
        return False

    chave_primaria = (
        modelo_cls.__mapper__.primary_key[0].key
    )

    modelo = modelo_cls(
        **{
            chave_primaria: id_valor,
            **campos,
        }
    )

    session.add(modelo)

    return True


def _inserir_se_nao_existir(
    session: Session,
    modelo_cls: type,
    filtro: Any,
    **campos: Any,
) -> bool:
    """
    Insere uma linha caso nenhum registro corresponda
    ao filtro informado.

    Utilizado principalmente em tabelas com ID automatico.
    """

    consulta = select(modelo_cls).where(filtro)

    existente = session.scalars(
        consulta
    ).first()

    if existente is not None:
        return False

    session.add(
        modelo_cls(**campos)
    )

    return True


def _popular_usuario(session: Session) -> int:
    return int(
        _inserir_se_nao_existir(
            session,
            UsuarioModel,
            UsuarioModel.email == EMAIL_ADMIN,
            nome="Operacao Bulbe",
            email=EMAIL_ADMIN,
            senha_hash=gerar_hash_senha(
                SENHA_ADMIN
            ),
        )
    )


def _popular_usinas(session: Session) -> int:
    inseridos = 0

    usinas = [
        (
            "Usina Solar Uberlandia",
            "Uberlandia, MG",
            5000.0,
        ),
        (
            "Usina Solar Montes Claros",
            "Montes Claros, MG",
            3200.0,
        ),
        (
            "Usina Solar Janauba",
            "Janauba, MG",
            7800.0,
        ),
    ]

    for nome, localizacao, capacidade in usinas:
        inseridos += _inserir_se_nao_existir(
            session,
            UsinaModel,
            UsinaModel.nome == nome,
            nome=nome,
            localizacao=localizacao,
            capacidade_geracao_kwh=capacidade,
            status="ativa",
            data_ativacao=date(2026, 3, 1),
        )

    return inseridos


def _popular_dicas(session: Session) -> int:
    inseridos = 0

    dicas = [
        (
            "Desligue o stand-by",
            (
                "Tire da tomada aparelhos que ficam "
                "em stand-by."
            ),
            12.5,
        ),
        (
            "Banho mais curto",
            (
                "Reduza o banho de chuveiro eletrico "
                "em 5 minutos."
            ),
            25.0,
        ),
    ]

    for titulo, descricao, economia in dicas:
        inseridos += _inserir_se_nao_existir(
            session,
            DicaModel,
            DicaModel.titulo == titulo,
            titulo=titulo,
            descricao=descricao,
            economia=economia,
            imagem_svg=SVG_LAMPADA,
            data_ativacao=date(2026, 4, 1),
        )

    return inseridos


def _popular_clientes(session: Session) -> int:
    inseridos = 0

    inseridos += _inserir_por_id(
        session,
        ClienteModel,
        ID_MARCOS,
        nome="Marcos Andrade",
        email="marcos.andrade@email.com",
        cpf=CPF_MARCOS,
        telefone="(31) 98888-1234",
        cep="30130-010",
        logradouro="Av. Afonso Pena",
        numero="1000",
        complemento="Apto 302",
        bairro="Centro",
        cidade="Belo Horizonte",
        uf="MG",
        distribuidora="CEMIG",
        numero_instalacao="3001234567",
        status="em_ativacao",
        acesso_habilitado=False,
        criado_em="2026-05-02T13:20:00Z",
    )

    inseridos += _inserir_por_id(
        session,
        ClienteModel,
        ID_ANA,
        nome="Ana Carolina Souza",
        email="ana.souza@email.com",
        cpf=CPF_ANA,
        telefone="(31) 97777-4321",
        cep="30180-100",
        logradouro="Rua dos Timbiras",
        numero="1200",
        complemento=None,
        bairro="Lourdes",
        cidade="Belo Horizonte",
        uf="MG",
        distribuidora="CEMIG",
        numero_instalacao="3007654321",
        status="ativo",
        acesso_habilitado=False,
        criado_em="2026-05-10T09:00:00Z",
    )

    session.flush()

    return inseridos


def _popular_ativacao(session: Session) -> int:
    return int(
        _inserir_por_id(
            session,
            AtivacaoModel,
            ID_MARCOS,
            etapa_atual=2,
            distribuidora="CEMIG",
            prazo_ativacao_dias=90,
            previsao_conclusao="2026-11-16",
            atualizado_em="2026-08-18T08:00:00Z",
            observacoes=[],
        )
    )


def _popular_parceiros(session: Session) -> int:
    inseridos = 0

    parceiros = [
        (
            ID_ARAUJO,
            "Drogaria Araújo",
            "Farmácia",
            "araujo.png",
            "2026-05-20T12:00:00Z",
        ),
        (
            ID_INTER,
            "Banco Inter",
            "Banco",
            "inter.png",
            "2026-05-21T10:00:00Z",
        ),
        (
            ID_LIVELO,
            "Livelo",
            "Programa de pontos",
            "livelo.svg",
            "2026-05-22T10:00:00Z",
        ),
    ]

    for (
        parceiro_id,
        nome,
        categoria,
        arquivo_logo,
        criado_em,
    ) in parceiros:
        logo_url = (
            "https://cdn.bulbeenergia.com.br/"
            f"parceiros/{arquivo_logo}"
        )

        inseridos += _inserir_por_id(
            session,
            ParceiroModel,
            parceiro_id,
            nome=nome,
            categoria=categoria,
            logo_url=logo_url,
            ativo=True,
            criado_em=criado_em,
            atualizado_em=None,
        )

    return inseridos


def _popular_clube_bulbe(session: Session) -> int:
    inseridos = 0

    inseridos += _popular_parceiros(session)

    inseridos += _inserir_por_id(
        session,
        CartaModel,
        ID_CARTA_MARCOS,
        cliente_id=ID_MARCOS,
        semana=3,
        tipo="normal",
        situacao="disponivel",
        disponivel_em="2026-06-12T09:00:00Z",
        aberta_em=None,
        cupom_id=None,
    )

    session.flush()

    inseridos += _inserir_por_id(
        session,
        CupomModel,
        ID_CUPOM_MARCOS,
        cliente_id=ID_MARCOS,
        carta_id=ID_CARTA_MARCOS,
        tag="PARCERIA DROGARIA ARAÚJO",
        titulo="15% de desconto na Araújo",
        descricao=(
            "Use o cupom em qualquer loja física "
            "ou no app da Araújo."
        ),
        codigo="BULBE15",
        parceiro_id=ID_ARAUJO,
        parceiro_nome="Drogaria Araújo",
        parceiro_categoria="Farmácia",
        situacao="ativo",
        valido_ate="2026-11-15",
        dias_restantes=14,
        criado_em="2026-06-12T19:42:00Z",
        usado_em=None,
    )

    inseridos += _inserir_por_id(
        session,
        OfensivaClubeModel,
        ID_MARCOS,
        semanas_sequencia=3,
    )

    return inseridos


def _popular_adesao(session: Session) -> int:
    return int(
        _inserir_se_nao_existir(
            session,
            AdesaoModel,
            AdesaoModel.cpf == CPF_ADESAO,
            nome="João da Silva",
            email="joaosilva@email.com",
            cpf=CPF_ADESAO,
            telefone="31999999999",
            cep="30575160",
            logradouro="Rua Oliveira",
            numero=213,
            bairro="Buritis",
            cidade="Belo Horizonte",
            uf="MG",
            distribuidora="CEMIG",
            numero_instalacao="3242412",
            valor_conta_atual=399.0,
            status="enviada",
            data_ativacao=date(2026, 6, 1),
        )
    )


def popular(session: Session) -> int:
    """
    Insere os dados ficticios da demonstracao.

    Retorna a quantidade de registros novos criados.
    """

    inseridos = 0

    try:
        inseridos += _popular_usuario(session)
        inseridos += _popular_usinas(session)
        inseridos += _popular_dicas(session)
        inseridos += _popular_clientes(session)
        inseridos += _popular_ativacao(session)
        inseridos += _popular_clube_bulbe(session)
        inseridos += _popular_adesao(session)

        session.commit()

        return inseridos

    except Exception:
        session.rollback()
        raise


def main() -> None:
    if not inspect(engine).has_table("clientes"):
        raise SystemExit(
            "As tabelas ainda nao existem. "
            "Rode primeiro: alembic upgrade head"
        )

    with SessionLocal() as session:
        novos = popular(session)

    print(
        "Seed concluido: "
        f"{novos} registro(s) novo(s) em {engine.url}."
    )


if __name__ == "__main__":
    main()"""
Seed: popula o banco com dados ficticios para a demo da Sprint Review.

Uso (na pasta backend/, depois de "alembic upgrade head"):
    python -m app.db.seed

Idempotente: pode rodar quantas vezes quiser; so insere o que ainda nao existe
(e nao desfaz o que foi alterado durante a demo).

Os dados sao os mesmos que antes viviam nos repositorios em memoria
(cliente Marcos Andrade, carta da semana 3, cupom BULBE15, etc.).
Todos sao ficticios.

Usuario de demonstracao do painel (login em POST /v1/auth/login):
    email: admin@bulbe.com.br
    senha: bulbe12345
"""

from datetime import date

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.security import gerar_hash_senha
from app.db.database import SessionLocal, engine
from app.db.models import (
    AdesaoModel,
    AtivacaoModel,
    CartaModel,
    ClienteModel,
    CupomModel,
    DicaModel,
    OfensivaClubeModel,
    ParceiroModel,
    UsinaModel,
    UsuarioModel,
)

ID_MARCOS = "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
ID_ANA = "7b2c1a5d-3e8f-4a0b-8d61-2c5b0a9d6e22"
ID_ARAUJO = "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9"
ID_INTER = "2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819"
ID_LIVELO = "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06"
ID_CARTA_MARCOS = "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55"
ID_CUPOM_MARCOS = "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"

SVG_LAMPADA = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path d="M9 21h6v-1H9v1zm3-19a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>'
)


def _inserir_por_id(session: Session, modelo_cls, id_valor, **campos) -> bool:
    """Insere a linha se a chave primaria ainda nao existir. Devolve True se inseriu."""
    if session.get(modelo_cls, id_valor) is not None:
        return False
    chave = modelo_cls.__mapper__.primary_key[0].key
    session.add(modelo_cls(**{chave: id_valor}, **campos))
    return True


def _inserir_se_nao_existir(session: Session, modelo_cls, filtro, **campos) -> bool:
    """Insere a linha se nenhuma outra bater com o filtro (para tabelas com id automatico)."""
    if session.scalars(select(modelo_cls).where(filtro)).first() is not None:
        return False
    session.add(modelo_cls(**campos))
    return True


def popular(session: Session) -> int:
    """Insere os dados da demo e devolve quantas linhas novas foram criadas."""
    inseridos = 0

    # Painel ------------------------------------------------------------
    inseridos += _inserir_se_nao_existir(
        session, UsuarioModel, UsuarioModel.email == "admin@bulbe.com.br",
        nome="Operacao Bulbe",
        email="admin@bulbe.com.br",
        senha_hash=gerar_hash_senha("bulbe12345"),
    )

    for nome, local, capacidade in [
        ("Usina Solar Uberlandia", "Uberlandia, MG", 5000.0),
        ("Usina Solar Montes Claros", "Montes Claros, MG", 3200.0),
        ("Usina Solar Janauba", "Janauba, MG", 7800.0),
    ]:
        inseridos += _inserir_se_nao_existir(
            session, UsinaModel, UsinaModel.nome == nome,
            nome=nome, localizacao=local, capacidade_geracao_kwh=capacidade,
            status="ativa", data_ativacao=date(2026, 3, 1),
        )

    for titulo, descricao, economia in [
        ("Desligue o stand-by", "Tire da tomada aparelhos que ficam em stand-by.", 12.5),
        ("Banho mais curto", "Reduza o banho de chuveiro eletrico em 5 minutos.", 25.0),
    ]:
        inseridos += _inserir_se_nao_existir(
            session, DicaModel, DicaModel.titulo == titulo,
            titulo=titulo, descricao=descricao, economia=economia,
            imagem_svg=SVG_LAMPADA, data_ativacao=date(2026, 4, 1),
        )

    # Clientes (precisam vir antes das tabelas com FK para clientes) -----
    inseridos += _inserir_por_id(
        session, ClienteModel, ID_MARCOS,
        nome="Marcos Andrade", email="marcos.andrade@email.com", cpf="12345678900",
        telefone="(31) 98888-1234", cep="30130-010", logradouro="Av. Afonso Pena",
        numero="1000", complemento="Apto 302", bairro="Centro", cidade="Belo Horizonte",
        uf="MG", distribuidora="CEMIG", numero_instalacao="3001234567",
        status="em_ativacao", acesso_habilitado=False, criado_em="2026-05-02T13:20:00Z",
    )
    inseridos += _inserir_por_id(
        session, ClienteModel, ID_ANA,
        nome="Ana Carolina Souza", email="ana.souza@email.com", cpf="98765432100",
        telefone="(31) 97777-4321", cep="30180-100", logradouro="Rua dos Timbiras",
        numero="1200", complemento=None, bairro="Lourdes", cidade="Belo Horizonte",
        uf="MG", distribuidora="CEMIG", numero_instalacao="3007654321",
        status="ativo", acesso_habilitado=False, criado_em="2026-05-10T09:00:00Z",
    )
    session.flush()  # garante os clientes no banco antes das linhas que apontam para eles

    inseridos += _inserir_por_id(
        session, AtivacaoModel, ID_MARCOS,
        etapa_atual=2, distribuidora="CEMIG", prazo_ativacao_dias=90,
        previsao_conclusao="2026-07-31", atualizado_em="2026-08-18T08:00:00Z", observacoes=[],
    )

    # Clube Bulbe -------------------------------------------------------
    for id_parceiro, nome, categoria, logo, criado in [
        (ID_ARAUJO, "Drogaria Araújo", "Farmácia", "araujo.png", "2026-05-20T12:00:00Z"),
        (ID_INTER, "Banco Inter", "Banco", "inter.png", "2026-05-21T10:00:00Z"),
        (ID_LIVELO, "Livelo", "Programa de pontos", "livelo.svg", "2026-05-22T10:00:00Z"),
    ]:
        inseridos += _inserir_por_id(
            session, ParceiroModel, id_parceiro,
            nome=nome, categoria=categoria,
            logo_url=f"https://cdn.bulbeenergia.com.br/parceiros/{logo}",
            ativo=True, criado_em=criado, atualizado_em=None,
        )

    inseridos += _inserir_por_id(
        session, CartaModel, ID_CARTA_MARCOS,
        cliente_id=ID_MARCOS, semana=3, tipo="normal", situacao="disponivel",
        disponivel_em="2026-06-12T09:00:00Z", aberta_em=None, cupom_id=None,
    )
    session.flush()

    inseridos += _inserir_por_id(
        session, CupomModel, ID_CUPOM_MARCOS,
        cliente_id=ID_MARCOS, carta_id=ID_CARTA_MARCOS, tag="PARCERIA DROGARIA ARAÚJO",
        titulo="15% de desconto na Araújo",
        descricao="Use o cupom em qualquer loja física ou no app da Araújo.",
        codigo="BULBE15", parceiro_id=ID_ARAUJO, parceiro_nome="Drogaria Araújo",
        parceiro_categoria="Farmácia", situacao="ativo", valido_ate="2026-11-15",
        dias_restantes=14, criado_em="2026-06-12T19:42:00Z", usado_em=None,
    )
    inseridos += _inserir_por_id(session, OfensivaClubeModel, ID_MARCOS, semanas_sequencia=3)

    # Captacao ----------------------------------------------------------
    inseridos += _inserir_se_nao_existir(
        session, AdesaoModel, AdesaoModel.cpf == "14444444444",
        nome="João da Silva", email="joaosilva@email.com", cpf="14444444444",
        telefone="31999999999", cep="30575160", logradouro="Rua Oliveira", numero=213,
        bairro="Buritis", cidade="Belo Horizonte", uf="MG", distribuidora="CEMIG",
        numero_instalacao="3242412", valor_conta_atual=399.0, status="enviada",
        data_ativacao=date(2026, 6, 1),
    )

    session.commit()
    return inseridos


def main() -> None:
    if not inspect(engine).has_table("clientes"):
        raise SystemExit(
            "As tabelas ainda nao existem. Rode primeiro:  alembic upgrade head"
        )
    with SessionLocal() as session:
        novos = popular(session)
    print(f"Seed concluido: {novos} registro(s) novo(s) em {engine.url}.")


if __name__ == "__main__":
    main()
