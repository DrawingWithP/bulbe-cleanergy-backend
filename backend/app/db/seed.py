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

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core import relogio
from app.core.security import gerar_hash_senha
from app.domain.bandeira import BANDEIRA_PADRAO, mes_referencia_atual
from app.db.database import SessionLocal, engine
from app.db.models import (
    AdesaoModel,
    AtivacaoModel,
    BandeiraTarifariaModel,
    CupomCatalogoModel,
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


def _popular_usuario(
    session: Session,
) -> int:
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


def _popular_usinas(
    session: Session,
) -> int:
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


# Dicas: (titulo, descricao, economia mensal, icone). As 5 primeiras formam a
# vitrine inicial do app; as 4 primeiras sao as dicas originais do protótipo.
DICAS = (
    ("Troque por LED", "Lâmpadas LED duram mais e gastam menos energia.", 8.0, "lampada_led"),
    ("Banhos rápidos", "Além de economizar água, você economiza energia.", 25.0, "chuveiro"),
    ("Cestos cheios", "Use a máquina de lavar só quando estiver cheia: menos ciclos, menos energia.", 15.0,
     "maquina_lavar"),
    ("Cômodos em uso", "Deixe acesas só as luzes dos cômodos em que você está.", 10.0, "lampada_apagada"),
    ("Desligue o stand-by", "Tire da tomada aparelhos que ficam em stand-by.", 12.5, "tomada"),
    ("Banho mais curto", "Reduza o banho de chuveiro elétrico em 5 minutos.", 25.0, "chuveiro"),
    ("Geladeira longe do fogão", "Calor por perto faz o motor da geladeira trabalhar mais.", 9.0, "geladeira"),
    ("Ar-condicionado em 23 °C", "Cada grau a menos aumenta o consumo; portas e janelas fechadas.", 30.0,
     "ar_condicionado"),
    ("Junte as roupas para passar", "Passe tudo de uma vez: o ferro gasta mais para esquentar.", 7.0, "ferro_passar"),
    ("Aproveite a luz do sol", "Abra cortinas e janelas durante o dia e apague as lâmpadas.", 6.0, "sol"),
)


def _popular_dicas(
    session: Session,
) -> int:
    inseridos = 0

    for titulo, descricao, economia, icone in DICAS:
        inseridos += _inserir_se_nao_existir(
            session,
            DicaModel,
            DicaModel.titulo == titulo,
            titulo=titulo,
            descricao=descricao,
            economia=economia,
            icone=icone,
            imagem_svg=None,
            data_ativacao=date(2026, 4, 1),
        )

    session.flush()

    # Bancos antigos: dicas criadas antes dos icones ficam com o padrao.
    icones = {titulo: icone for titulo, _, _, icone in DICAS}
    for dica in session.scalars(select(DicaModel)).all():
        if dica.titulo in icones and dica.icone in (None, "lampada_led") and icones[dica.titulo] != dica.icone:
            dica.icone = icones[dica.titulo]

    # Vitrine inicial: so se ninguem montou a vitrine ainda.
    if not session.scalars(select(DicaModel).where(DicaModel.em_exibicao.is_(True))).first():
        for ordem, (titulo, *_resto) in enumerate(DICAS[:5], start=1):
            dica = session.scalars(select(DicaModel).where(DicaModel.titulo == titulo)).first()
            if dica is not None:
                dica.em_exibicao = True
                dica.ordem = ordem

    return inseridos


def _cpf_valido(cpf: str) -> bool:
    """Confere os dois digitos verificadores do CPF."""

    digitos = "".join(c for c in str(cpf or "") if c.isdigit())
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(
            int(digitos[i]) * (posicao + 1 - i)
            for i in range(posicao)
        )
        if (soma * 10) % 11 % 10 != int(digitos[posicao]):
            return False
    return True


def _corrigir_cpf_de_demonstracao(
    session: Session,
) -> int:
    """
    Bancos criados por versoes antigas do seed guardavam CPFs
    ficticios antigos para os clientes de demonstracao
    (12345678900 e 98765432100). O primeiro nem e um CPF valido,
    o que impede o login pelo app. Para todo mundo ter os mesmos
    CPFs de demonstracao, troca o CPF de um cliente de demonstracao
    quando ele e invalido ou e um desses valores antigos.
    """

    corrigidos = 0

    for cliente_id, cpf, antigo in (
        (ID_MARCOS, CPF_MARCOS, "12345678900"),
        (ID_ANA, CPF_ANA, "98765432100"),
    ):
        cliente = session.get(ClienteModel, cliente_id)

        if cliente is None or cliente.cpf == cpf:
            continue

        if _cpf_valido(cliente.cpf) and cliente.cpf != antigo:
            continue

        ocupado = session.scalars(
            select(ClienteModel).where(
                ClienteModel.cpf == cpf,
                ClienteModel.id != cliente_id,
            )
        ).first()

        if ocupado is None:
            cliente.cpf = cpf
            corrigidos += 1

    return corrigidos


def _popular_clientes(
    session: Session,
) -> int:
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

    inseridos += _corrigir_cpf_de_demonstracao(session)

    session.flush()

    return inseridos


def _popular_ativacao(
    session: Session,
) -> int:
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


def _popular_parceiros(
    session: Session,
) -> int:
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


def _popular_clube_bulbe(
    session: Session,
) -> int:
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
        # Validade relativa: o cupom de demonstracao vale 14 dias a partir de hoje.
        valido_ate=(relogio.hoje() + timedelta(days=14)).isoformat(),
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


def _popular_adesao(
    session: Session,
) -> int:
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


# Catalogo de cupons sorteados nas cartas normais (ids fixos: seed idempotente).
CATALOGO_CUPONS = (
    ("c1a0f3e2-0001-4b6c-9a11-000000000001", ID_ARAUJO, "PARCERIA DROGARIA ARAÚJO",
     "15% de desconto na Araújo", "Use o cupom em qualquer loja física ou no app da Araújo.", "BULBE15", 3),
    ("c1a0f3e2-0002-4b6c-9a11-000000000002", ID_ARAUJO, "PARCERIA DROGARIA ARAÚJO",
     "10% de desconto na Araújo", "Use o cupom em qualquer loja física ou no app da Araújo.", "BULBE10", 2),
    ("c1a0f3e2-0003-4b6c-9a11-000000000003", ID_INTER, "PARCERIA BANCO INTER",
     "Cashback dobrado no Inter", "Compras no débito ou crédito Inter com cashback em dobro por 30 dias.", "INTERCASH", 2),
    ("c1a0f3e2-0004-4b6c-9a11-000000000004", ID_LIVELO, "PARCERIA LIVELO",
     "500 pontos Livelo", "Use o cupom no app ou site da Livelo para liberar 500 pontos.", "BULBELIV", 2),
)


def _popular_catalogo(
    session: Session,
) -> int:
    inseridos = 0

    for modelo_id, parceiro_id, tag, titulo, descricao, prefixo, peso in CATALOGO_CUPONS:
        if session.get(ParceiroModel, parceiro_id) is None:
            continue
        inseridos += int(
            _inserir_por_id(
                session,
                CupomCatalogoModel,
                modelo_id,
                parceiro_id=parceiro_id,
                tag=tag,
                titulo=titulo,
                descricao=descricao,
                prefixo_codigo=prefixo,
                validade_dias=14,
                peso=peso,
                ativo=True,
                criado_em="2026-05-20T12:00:00Z",
            )
        )

    return inseridos


def _popular_bandeira(
    session: Session,
) -> int:
    """Bandeira do mes atual (verde), usada pelo simulador."""

    return int(
        _inserir_por_id(
            session,
            BandeiraTarifariaModel,
            mes_referencia_atual(),
            bandeira=BANDEIRA_PADRAO.value,
            atualizado_em=datetime.now(),
        )
    )


def popular(
    session: Session,
) -> int:
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
        inseridos += _popular_bandeira(session)
        session.flush()
        inseridos += _popular_catalogo(session)

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
    main()
