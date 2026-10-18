"""
Camada de Persistencia, seed do banco ficticio da Bulbe.

Todos os dados sao 100% ficticios: nomes sao combinacoes aleatorias, CPFs tem digitos
verificadores validos mas foram gerados ao acaso, telefones/instalacoes/protocolos idem.
O seed e deterministico (random.Random(semente), sem Faker) e todas as datas sao relativas
ao dia atual em UTC (agora_utc().date()), para o banco sempre "parecer atual".
Nenhum registro de um cliente (notificacao, atendimento, login) fica antes do criado_em dele.
v2: bonus do Clube nas faturas (bonus_clube), ~120 registros de auditoria_acessos com IPs ficticios
(todos com pelo menos 2 dias) e nenhuma conversa de chat (o chat comeca vazio).

Recriar o banco (apaga e popula de novo):
    python -m app.database.seed
"""
import os
import random
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.database.modelos import (
    Adesao,
    Atendimento,
    AuditoriaAcesso,
    Ativacao,
    AtivacaoEvento,
    Carta,
    Cliente,
    ClubeStatus,
    Cupom,
    Dica,
    Fatura,
    Funcionario,
    Indicacao,
    Notificacao,
    Parceiro,
    Simulacao,
    Usina,
    agora_utc,
)
from app.database.seguranca import gerar_hash_senha

# ---------------------------------------------------------------------------
# Regras de negocio (secao 1.4 do contrato)
# ---------------------------------------------------------------------------
SEMENTE_PADRAO = 42
PERCENTUAL_DESCONTO = 0.15
BONUS_INDICACAO = 50.0
PRAZO_ATIVACAO_DIAS = 90
INTERVALO_CARTA_DIAS = 7
META_SEQUENCIA = 5
VALIDADE_CUPOM_DIAS = 14
VALIDADE_INDICACAO_DIAS = 60
TARIFA_KWH = 0.98  # R$/kWh ficticio, ja com tributos

# Volumes
QTD_ATIVOS = 40
QTD_ATIVADOS_RECENTES = 3  # entre os 40 ativos: energia liberada nos ultimos 30 dias (etapa 5 do funil)
QTD_EM_ATIVACAO = 15  # + Marcos Andrade = 16
QTD_CANCELADOS_POS_ATIVACAO = 5
QTD_CANCELADOS_NA_ATIVACAO = 3
QTD_INADIMPLENTES = 5
QTD_SIMULACOES = 200
BONUS_CLUBE = 50.0  # bonus especial do Clube Bulbe (5 semanas seguidas), aplicado na fatura seguinte

# ---------------------------------------------------------------------------
# Tabelas de apoio ficticias
# ---------------------------------------------------------------------------
NOMES_FEMININOS = [
    "Ana", "Beatriz", "Camila", "Daniela", "Fernanda", "Gabriela", "Helena", "Isabela",
    "Juliana", "Larissa", "Luana", "Mariana", "Natália", "Patrícia", "Renata", "Sofia",
    "Tatiane", "Vanessa", "Letícia", "Aline", "Bruna", "Carolina", "Eduarda", "Priscila",
]
NOMES_MASCULINOS = [
    "André", "Bruno", "Carlos", "Diego", "Eduardo", "Felipe", "Gustavo", "Henrique",
    "Igor", "Leonardo", "Lucas", "Mateus", "Paulo", "Ricardo", "Thiago", "Vinícius",
    "Fábio", "Leandro", "Otávio", "Caio", "Murilo", "Renan", "Alexandre", "Marcelo",
]
SOBRENOMES = [
    "Almeida", "Barbosa", "Cardoso", "Carvalho", "Castro", "Costa", "Dias", "Ferreira",
    "Fonseca", "Gomes", "Lima", "Lopes", "Machado", "Martins", "Mendes", "Moreira",
    "Nogueira", "Oliveira", "Pereira", "Pinto", "Ramos", "Rezende", "Rocha", "Santos",
    "Silva", "Soares", "Teixeira", "Vieira", "Campos", "Diniz", "Guimarães", "Vasconcelos",
    "Tavares", "Brandão", "Assis", "Queiroz",
]

# (cidade, peso, ddd, faixa de CEP (5 primeiros digitos), bairros)
CIDADES_MG: list[tuple[str, int, str, tuple[int, int], list[str]]] = [
    ("Belo Horizonte", 30, "31", (30110, 31999), [
        "Savassi", "Funcionários", "Lourdes", "Santa Efigênia", "Pampulha", "Castelo",
        "Buritis", "Sion", "Prado", "Barreiro", "Venda Nova", "Santa Tereza", "Floresta",
        "Cidade Nova", "Padre Eustáquio", "Ouro Preto",
    ]),
    ("Contagem", 7, "31", (32010, 32399), ["Eldorado", "Riacho", "Inconfidentes", "Água Branca"]),
    ("Betim", 4, "31", (32600, 32689), ["Centro", "Ingá", "Jardim da Cidade", "Brasiléia"]),
    ("Nova Lima", 4, "31", (34000, 34025), ["Vila da Serra", "Vale do Sereno", "Centro", "Jardim Canadá"]),
    ("Lagoa Santa", 3, "31", (33230, 33239), ["Centro", "Lundcéia", "Joá", "Vila Asas"]),
    ("Santa Luzia", 2, "31", (33010, 33150), ["São Benedito", "Centro", "Belo Vale"]),
    ("Sabará", 2, "31", (34500, 34590), ["Centro", "General Carneiro", "Ana Lúcia"]),
    ("Vespasiano", 2, "31", (33200, 33210), ["Centro", "Morro Alto", "Nova Pampulha"]),
    ("Ribeirão das Neves", 2, "31", (33800, 33990), ["Justinópolis", "Centro", "Veneza"]),
    ("Juiz de Fora", 3, "32", (36010, 36099), ["Centro", "São Mateus", "Cascatinha", "Bom Pastor"]),
    ("Uberlândia", 3, "34", (38400, 38414), ["Centro", "Santa Mônica", "Tibery", "Jardim Karaíba"]),
    ("Montes Claros", 2, "38", (39400, 39409), ["Centro", "Ibituruna", "Todos os Santos"]),
    ("Ipatinga", 2, "31", (35160, 35164), ["Centro", "Cidade Nobre", "Horto"]),
    ("Divinópolis", 2, "37", (35500, 35504), ["Centro", "Sidil", "Bom Pastor"]),
    ("Sete Lagoas", 2, "31", (35700, 35704), ["Centro", "Canaã", "Jardim Cambuí"]),
]

LOGRADOUROS = [
    "Rua das Acácias", "Rua dos Ipês", "Avenida Brasil", "Rua Rio de Janeiro",
    "Rua Espírito Santo", "Avenida Amazonas", "Rua da Bahia", "Rua Pernambuco",
    "Rua Tomé de Souza", "Rua Padre Marinho", "Rua Itapecerica", "Rua São Paulo",
    "Rua Professor Moraes", "Rua Alagoas", "Rua das Palmeiras", "Rua Sete de Setembro",
    "Rua Tiradentes", "Avenida Getúlio Vargas", "Rua Santa Rita", "Rua dos Jacarandás",
]

USINAS = [
    # nome, localizacao, capacidade (kWh/mes), status, dias desde a ativacao
    ("Usina Solar Jaíba I", "Jaíba, MG", 520000.0, "ativa", 1100),
    ("Usina Solar Janaúba", "Janaúba, MG", 410000.0, "ativa", 800),
    ("Usina Solar Pirapora II", "Pirapora, MG", 360000.0, "ativa", 540),
    ("Usina Solar Paracatu", "Paracatu, MG", 280000.0, "em_manutencao", 420),
]

# Os 4 primeiros vem do front (Clube Bulbe); os 2 ultimos sao marcas inventadas.
PARCEIROS = [
    # nome, categoria, logo_url, ativo, dias desde o cadastro
    ("Drogaria Araújo", "Saúde e bem-estar", "img_final/van-image25.png", True, 300),
    ("Banco Inter", "Serviços financeiros", "img_final/van-image26.png", True, 300),
    ("Livelo", "Programa de pontos", "img_final/van-livelo.svg", True, 240),
    ("Bulbe Energia", "Bônus Clube Bulbe", "img_final/van-image28.png", True, 300),
    ("Café Serrano Mineiro", "Alimentação", None, True, 12),
    ("EcoBike BH", "Mobilidade", None, False, 200),
]

# As 5 recompensas do Clube Bulbe (final.js -> RECOMPENSAS)
RECOMPENSAS = [
    ("Drogaria Araújo", "15% de desconto na Araújo",
     "Use o cupom em qualquer loja física ou no app da Araújo.", "BULBE15"),
    ("Banco Inter", "Cashback dobrado no Inter",
     "Compras no débito ou crédito Inter com cashback em dobro.", "INTERCASH"),
    ("Bulbe Energia", "Indicação dobrada por 30 dias",
     "Cada indicação realizada neste período vale o dobro.", "BULBEDUO"),
    ("Livelo", "500 pontos Livelo",
     "Use o cupom no app ou site da Livelo para liberar os 500 pontos na sua conta.", "BULBELIV500"),
    ("Drogaria Araújo", "10% de desconto na Araújo",
     "Use o cupom em qualquer loja física ou no app da Araújo.", "BULBE10"),
]

# As 4 dicas do front (tela Dicas)
DICAS = [
    ("Troque por LED", "Lâmpadas LED duram mais e gastam menos energia", 12.0, 144.0),
    ("Banhos rápidos", "Além de economizar água, você economiza energia", 18.0, 216.0),
    ("Cestos cheios",
     "Prefira usar máquinas de lavar apenas quando estiverem cheias. Menos ciclos, mais energia", 8.0, 96.0),
    ("Cômodos em uso", "Deixe ligadas apenas as luzes dos cômodos em que você está.", 6.0, 72.0),
]

FUNCIONARIOS = [
    ("Paula Menezes", "admin@bulbe.com.br", "admin"),
    ("Equipe de Atendimento", "atendimento@bulbe.com.br", "atendimento"),
    ("Ana Souza", "ana.souza@bulbe.com.br", "atendimento"),
]

# Auditoria de acessos do painel (v2). IPs ficticios: rede interna 10.20.x.x e faixas
# reservadas para documentacao (RFC 5737: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24).
IPS_ESCRITORIO = ["10.20.1.15", "10.20.1.22", "10.20.1.37", "10.20.2.8", "10.20.2.41"]
IPS_EXTERNOS = ["198.51.100.23", "198.51.100.87", "203.0.113.45", "192.0.2.61", "192.0.2.140"]
IP_ATAQUE = "203.0.113.190"
EMAILS_INEXISTENTES = [
    "admin@bulbe.com", "suporte@bulbe.com.br", "paula.menezes@bulbe.com.br", "financeiro@bulbe.com.br",
]
QTD_LOGINS_AUDITORIA = 42
QTD_FALHAS_DIGITACAO = 8
QTD_FALHAS_EMAIL_INEXISTENTE = 5
QTD_VER_AUDITORIA = 4

TITULOS_ETAPA = {
    1: "Cadastro realizado",
    2: "Documentação sendo analisada",
    3: "Solicitação enviada à CEMIG",
    4: "Em análise pela CEMIG",
    5: "Energia aprovada",
}

OBS_ETAPA_1 = ["Cadastro concluído pelo app.", "Cadastro realizado pelo site.", "Cadastro feito com apoio do atendimento via WhatsApp."]
OBS_ETAPA_2 = [
    "Documentos recebidos (RG e conta de luz). Em análise.",
    "Documentação enviada pelo app e em conferência.",
    "Conta de luz e documento com foto recebidos; conferência iniciada.",
]
OBS_ETAPA_4 = [
    "CEMIG iniciou a análise técnica da instalação {instalacao}.",
    "Pedido em análise pela CEMIG (protocolo {protocolo}).",
]
OBS_ETAPA_5 = "CEMIG aprovou a conexão. Energia liberada; desconto a partir da próxima fatura."

ASSUNTOS_ATENDIMENTO_ATIVO = [
    ("Dúvida sobre a fatura",
     "Cliente não entendeu a diferença entre o valor sem Bulbe e o valor com desconto na fatura de {mes}."),
    ("Segunda via de fatura", "Solicitou a segunda via da fatura de {mes}; enviada por e-mail."),
    ("Desconto na fatura",
     "Cliente questionou por que o desconto de 15% não incide sobre iluminação pública e PIS/COFINS; regra explicada."),
    ("Cupom do Clube Bulbe",
     "Cupom não foi aceito no parceiro; orientado a conferir a validade de 14 dias no app."),
    ("Acesso ao app", "Cliente não recebeu o código de primeiro acesso; código reenviado por SMS."),
    ("Atualização cadastral", "Pedido de alteração do telefone e do e-mail de contato."),
    ("Bônus de indicação", "Cliente perguntou quando o bônus de R$ 50 da indicação será creditado na fatura."),
]


# ---------------------------------------------------------------------------
# Estruturas auxiliares do seed (planejamento antes de gravar)
# ---------------------------------------------------------------------------
@dataclass
class _Credito:
    """Bonus de indicacao a ser aplicado na primeira fatura >= mes_minimo."""

    mes_minimo: str
    indicacao: Optional[Indicacao] = None


@dataclass
class _PlanoCliente:
    cliente: Cliente
    criado_dia: date
    status: str
    ddd: str
    etapa: int
    dias_etapas: dict[int, int]  # etapa -> dias apos o cadastro
    liberacao_dia: Optional[date] = None
    cancelamento_dia: Optional[date] = None
    consumo_base_kwh: float = 0.0
    dia_vencimento: int = 10
    inadimplente: bool = False
    personagem: bool = False
    creditos: list[_Credito] = field(default_factory=list)
    creditos_clube: list[date] = field(default_factory=list)  # dia em que a carta especial foi aberta
    faturas: list[Fatura] = field(default_factory=list)
    protocolo: str = ""


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def _mes_str(dia: date) -> str:
    return f"{dia.year:04d}-{dia.month:02d}"


def _somar_meses(ano: int, mes: int, quantidade: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + quantidade
    return total // 12, total % 12 + 1


def _formatar_mes(mes_referencia: str) -> str:
    ano, mes = mes_referencia.split("-")
    return f"{mes}/{ano}"


class _GeradorFicticio:
    """Gera e grava todos os dados ficticios de forma deterministica."""

    def __init__(self, sessao: Session, semente: int) -> None:
        self.s = sessao
        self.rng = random.Random(semente)
        # "hoje" sempre derivado do mesmo instante UTC usado nas consultas (agora_utc)
        self.agora = agora_utc()
        self.hoje = self.agora.date()
        self._cpfs: set[str] = set()
        self._emails: set[str] = set()
        self._instalacoes: set[str] = set()
        self._codigos: set[str] = set()
        self._nomes: set[str] = {"Marcos Andrade", "Clara Ribeiro", "Renato Souza"}
        self.usinas: list[Usina] = []
        self.parceiros: dict[str, Parceiro] = {}
        self.planos: list[_PlanoCliente] = []
        self.funcionarios: list[Funcionario] = []

    # ------------------------------------------------------------- utilitarios
    def _uuid(self) -> str:
        return str(uuid.UUID(int=self.rng.getrandbits(128), version=4))

    def _momento(self, dia: date, hora_ini: int = 8, hora_fim: int = 20) -> datetime:
        """Um instante aleatorio no dia, nunca no futuro."""
        instante = datetime.combine(
            dia, time(self.rng.randint(hora_ini, hora_fim - 1), self.rng.randint(0, 59), self.rng.randint(0, 59))
        )
        return min(instante, self.agora)

    def _apos_cadastro(self, cliente: Cliente, instante: datetime, folga_minutos: int = 30) -> datetime:
        """Garante que o instante nao fique antes do cadastro do cliente (nem no futuro)."""
        return min(max(instante, cliente.criado_em + timedelta(minutes=folga_minutos)), self.agora)

    def _cpf(self) -> str:
        """CPF com digitos verificadores validos, mas ficticio (gerado ao acaso)."""
        while True:
            base = [self.rng.randint(0, 9) for _ in range(9)]
            if len(set(base)) == 1:
                continue
            d1 = self._digito_cpf(base, 10)
            d2 = self._digito_cpf(base + [d1], 11)
            cpf = "".join(str(n) for n in base + [d1, d2])
            if cpf not in self._cpfs:
                self._cpfs.add(cpf)
                return cpf

    @staticmethod
    def _digito_cpf(numeros: list[int], peso_inicial: int) -> int:
        soma = sum(n * p for n, p in zip(numeros, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    def _telefone(self, ddd: str) -> str:
        return f"{ddd}9{self.rng.randint(8000, 9999)}{self.rng.randint(0, 9999):04d}"

    def _instalacao(self) -> str:
        while True:
            numero = f"300{self.rng.randint(0, 9_999_999):07d}"
            if numero not in self._instalacoes:
                self._instalacoes.add(numero)
                return numero

    def _nome(self) -> tuple[str, str, str]:
        """Devolve (nome completo, primeiro nome, ultimo sobrenome), sem repetir."""
        while True:
            primeiro = self.rng.choice(NOMES_FEMININOS if self.rng.random() < 0.5 else NOMES_MASCULINOS)
            sobrenomes = self.rng.sample(SOBRENOMES, 2 if self.rng.random() < 0.35 else 1)
            completo = " ".join([primeiro, *sobrenomes])
            if completo not in self._nomes:
                self._nomes.add(completo)
                return completo, primeiro, sobrenomes[-1]

    def _email(self, primeiro: str, ultimo: str) -> str:
        base = f"{_sem_acentos(primeiro).lower()}.{_sem_acentos(ultimo).lower()}"
        dominio = self.rng.choice(["email.com", "email.com", "exemplo.com.br"])
        email, n = f"{base}@{dominio}", 1
        while email in self._emails:
            n += 1
            email = f"{base}{n}@{dominio}"
        self._emails.add(email)
        return email

    def _codigo_indicacao(self, primeiro: str, ultimo: str) -> str:
        p, u = _sem_acentos(primeiro).upper(), _sem_acentos(ultimo).upper()
        candidatos = [f"{p}50", f"{p}{u[0]}50", f"{p}{u[:3]}50"]
        candidatos += [f"{p}{u[0]}{n}50" for n in range(2, 99)]
        for codigo in candidatos:
            if codigo not in self._codigos:
                self._codigos.add(codigo)
                return codigo
        raise RuntimeError("Nao foi possivel gerar codigo de indicacao unico.")

    def _cidade(self) -> tuple[str, str, tuple[int, int], list[str]]:
        pesos = [c[1] for c in CIDADES_MG]
        cidade, _, ddd, faixa, bairros = self.rng.choices(CIDADES_MG, weights=pesos, k=1)[0]
        return cidade, ddd, faixa, bairros

    def _usina(self) -> Usina:
        pesos = [u.capacidade_geracao_kwh for u in self.usinas]
        return self.rng.choices(self.usinas, weights=pesos, k=1)[0]

    # ------------------------------------------------------------- tabelas fixas
    def criar_funcionarios(self) -> None:
        senha = os.getenv("PAINEL_SENHA_DEMO", "bulbe@demo123")
        for i, (nome, email, perfil) in enumerate(FUNCIONARIOS):
            funcionario = Funcionario(
                nome=nome,
                email=email,
                senha_hash=gerar_hash_senha(senha),
                perfil=perfil,
                ativo=True,
                criado_em=self._momento(self.hoje - timedelta(days=210 - i * 30)),
            )
            self.s.add(funcionario)
            self.funcionarios.append(funcionario)

    def criar_usinas(self) -> None:
        for nome, localizacao, capacidade, status, dias in USINAS:
            usina = Usina(
                nome=nome,
                localizacao=localizacao,
                capacidade_geracao_kwh=capacidade,
                status=status,
                data_ativacao=self.hoje - timedelta(days=dias),
            )
            self.s.add(usina)
            self.usinas.append(usina)

    def criar_parceiros(self) -> None:
        for nome, categoria, logo, ativo, dias in PARCEIROS:
            parceiro = Parceiro(
                id=self._uuid(),
                nome=nome,
                categoria=categoria,
                logo_url=logo,
                ativo=ativo,
                criado_em=self._momento(self.hoje - timedelta(days=dias)),
            )
            self.s.add(parceiro)
            self.parceiros[nome] = parceiro

    def criar_dicas(self) -> None:
        for ordem, (titulo, descricao, mensal, anual) in enumerate(DICAS, start=1):
            self.s.add(Dica(titulo=titulo, descricao=descricao, economia_mensal=mensal,
                            economia_anual=anual, ordem=ordem))

    # ------------------------------------------------------------- clientes
    def _novo_cliente(self, status: str, criado_dia: date, *, nome: Optional[str] = None,
                      primeiro: Optional[str] = None, ultimo: Optional[str] = None) -> tuple[Cliente, str]:
        if nome is None:
            nome, primeiro, ultimo = self._nome()
        assert primeiro is not None and ultimo is not None
        cidade, ddd, faixa, bairros = self._cidade()
        complemento = None
        sorteio = self.rng.random()
        if sorteio < 0.35:
            complemento = f"Apto {self.rng.randint(1, 12)}0{self.rng.randint(1, 4)}"
        elif sorteio < 0.45:
            complemento = f"Casa {self.rng.randint(1, 3)}"
        cliente = Cliente(
            id=self._uuid(),
            nome=nome,
            email=self._email(primeiro, ultimo),
            cpf=self._cpf(),
            telefone=self._telefone(ddd),
            tipo="empresa" if self.rng.random() < 0.15 else "residencia",
            cep=f"{self.rng.randint(*faixa):05d}{self.rng.randint(0, 999):03d}",
            logradouro=self.rng.choice(LOGRADOUROS),
            numero=str(self.rng.randint(10, 2500)),
            complemento=complemento,
            bairro=self.rng.choice(bairros),
            cidade=cidade,
            uf="MG",
            distribuidora="CEMIG",
            numero_instalacao=self._instalacao(),
            status=status,
            codigo_indicacao=self._codigo_indicacao(primeiro, ultimo),
            app_acesso_habilitado=False,
            criado_em=self._momento(criado_dia),
        )
        return cliente, ddd

    def _consumo_base(self, cliente: Cliente) -> float:
        if cliente.tipo == "empresa":
            return float(self.rng.randint(550, 1500))
        return float(self.rng.randint(140, 460))

    def _dias_etapas_completas(self, total_dias: int) -> dict[int, int]:
        d2 = self.rng.randint(1, 5)
        d3 = d2 + self.rng.randint(5, 15)
        d4 = d3 + self.rng.randint(5, 20)
        return {1: 0, 2: d2, 3: d3, 4: d4, 5: total_dias}

    def _etapa_por_tempo(self, dias: int) -> int:
        if dias <= 5:
            return self.rng.choice([1, 2])
        if dias <= 20:
            return self.rng.choice([2, 2, 3])
        if dias <= 45:
            return self.rng.choice([3, 4, 4])
        return self.rng.choice([3, 4, 4, 4])

    def criar_clientes(self) -> None:
        # --- ativos -------------------------------------------------------
        for i in range(QTD_ATIVOS):
            recente = i < QTD_ATIVADOS_RECENTES
            if recente:
                idade = self.rng.randint(50, 100)
            elif self.rng.random() < 0.7:
                idade = self.rng.randint(460, 900)
            else:
                idade = self.rng.randint(150, 459)
            criado = self.hoje - timedelta(days=idade)
            cliente, ddd = self._novo_cliente("ativo", criado)
            if recente:
                # energia liberada entre 1 e 29 dias atras (alimenta "ativados nos ultimos 30 dias")
                total = self.rng.randint(max(45, idade - 29), min(88, idade - 1))
            else:
                total = self.rng.randint(45, 88)
            plano = _PlanoCliente(
                cliente=cliente, criado_dia=criado, status="ativo", ddd=ddd, etapa=5,
                dias_etapas=self._dias_etapas_completas(total),
                liberacao_dia=criado + timedelta(days=total),
                consumo_base_kwh=self._consumo_base(cliente),
                dia_vencimento=self.rng.choice([5, 10, 15, 20, 25]),
            )
            cliente.usina = self._usina()
            if self.rng.random() < 0.75:
                cliente.app_acesso_habilitado = True
                if self.rng.random() < 0.85:
                    dias_login = int(self.rng.triangular(0, 75, 3))
                    cliente.ultimo_login_app = self._apos_cadastro(
                        cliente, self._momento(self.hoje - timedelta(days=dias_login), 7, 23))
            self.planos.append(plano)

        # inadimplentes so entre quem ja tem faturas (energia liberada ha mais de 90 dias)
        com_faturas = [
            p for p in self.planos
            if p.status == "ativo" and p.liberacao_dia is not None and (self.hoje - p.liberacao_dia).days > 90
        ]
        for plano in self.rng.sample(com_faturas, QTD_INADIMPLENTES):
            plano.inadimplente = True

        # --- Marcos Andrade (persona do front: em ativacao, etapa 2) ---------
        criado = self.hoje - timedelta(days=12)
        marcos = Cliente(
            id=self._uuid(),
            nome="Marcos Andrade",
            email="marcos.andrade@email.com",
            cpf=self._cpf(),
            telefone="31988881234",
            tipo="residencia",
            cep="30130010",
            logradouro="Av. Afonso Pena",
            numero="1000",
            complemento="Apto 302",
            bairro="Centro",
            cidade="Belo Horizonte",
            uf="MG",
            distribuidora="CEMIG",
            numero_instalacao=self._instalacao(),
            status="em_ativacao",
            codigo_indicacao="MARCOS50",
            app_acesso_habilitado=True,
            ultimo_login_app=self._momento(self.hoje - timedelta(days=1), 7, 23),
            criado_em=self._momento(criado, 9, 12),
        )
        self._emails.add(marcos.email)
        self._codigos.add("MARCOS50")
        self.planos.append(_PlanoCliente(
            cliente=marcos, criado_dia=criado, status="em_ativacao", ddd="31", etapa=2,
            dias_etapas={1: 0, 2: 3}, consumo_base_kwh=290.0, personagem=True,
        ))

        # --- em ativacao (etapas 1 a 4, sem faturas) ----------------------
        for i in range(QTD_EM_ATIVACAO):
            # o primeiro passou do prazo de 90 dias (ex.: CEMIG demorando), para o painel ter um "atrasado"
            dias = self.rng.randint(95, 120) if i == 0 else self.rng.randint(2, 85)
            criado = self.hoje - timedelta(days=dias)
            cliente, ddd = self._novo_cliente("em_ativacao", criado)
            etapa = self._etapa_por_tempo(dias)
            offsets = sorted(self.rng.sample(range(1, dias + 1), etapa - 1))
            dias_etapas = {1: 0, **{i + 2: d for i, d in enumerate(offsets)}}
            if etapa >= 3:
                cliente.usina = self._usina()
            if self.rng.random() < 0.6:
                cliente.app_acesso_habilitado = True
                cliente.ultimo_login_app = self._apos_cadastro(cliente, self._momento(
                    self.hoje - timedelta(days=self.rng.randint(0, min(dias, 20))), 7, 23))
            self.planos.append(_PlanoCliente(
                cliente=cliente, criado_dia=criado, status="em_ativacao", ddd=ddd, etapa=etapa,
                dias_etapas=dias_etapas, consumo_base_kwh=self._consumo_base(cliente),
            ))

        # --- cancelados depois de ativos (com faturas historicas) --------
        for _ in range(QTD_CANCELADOS_POS_ATIVACAO):
            criado = self.hoje - timedelta(days=self.rng.randint(420, 900))
            cliente, ddd = self._novo_cliente("cancelado", criado)
            total = self.rng.randint(45, 88)
            liberacao = criado + timedelta(days=total)
            limite = (self.hoje - liberacao).days - 20
            cancelamento = liberacao + timedelta(days=self.rng.randint(120, max(121, limite)))
            cliente.usina = self._usina()
            if self.rng.random() < 0.5:
                cliente.ultimo_login_app = self._apos_cadastro(
                    cliente, self._momento(cancelamento - timedelta(days=self.rng.randint(5, 40))))
            self.planos.append(_PlanoCliente(
                cliente=cliente, criado_dia=criado, status="cancelado", ddd=ddd, etapa=5,
                dias_etapas=self._dias_etapas_completas(total), liberacao_dia=liberacao,
                cancelamento_dia=cancelamento, consumo_base_kwh=self._consumo_base(cliente),
                dia_vencimento=self.rng.choice([5, 10, 15, 20, 25]),
            ))

        # --- cancelados durante a ativacao (sem faturas) ------------------
        for _ in range(QTD_CANCELADOS_NA_ATIVACAO):
            criado = self.hoje - timedelta(days=self.rng.randint(100, 300))
            cliente, ddd = self._novo_cliente("cancelado", criado)
            etapa = self.rng.choice([2, 3])
            dias_etapas = {1: 0, 2: self.rng.randint(1, 5)}
            if etapa == 3:
                dias_etapas[3] = dias_etapas[2] + self.rng.randint(5, 12)
            cancelamento = criado + timedelta(days=dias_etapas[etapa] + self.rng.randint(5, 40))
            self.planos.append(_PlanoCliente(
                cliente=cliente, criado_dia=criado, status="cancelado", ddd=ddd, etapa=etapa,
                dias_etapas=dias_etapas, cancelamento_dia=cancelamento,
                consumo_base_kwh=self._consumo_base(cliente),
            ))

        for plano in self.planos:
            self.s.add(plano.cliente)
        self.s.flush()

    # ------------------------------------------------------------- ativacao
    def criar_ativacoes(self) -> None:
        for plano in self.planos:
            cli = plano.cliente
            momentos: dict[int, datetime] = {1: cli.criado_em}
            for etapa, dias in plano.dias_etapas.items():
                if etapa > 1:
                    momentos[etapa] = self._momento(plano.criado_dia + timedelta(days=dias))
            eventos: list[tuple[int, str, datetime]] = []

            if plano.personagem:
                obs1 = "Cadastro concluído pelo app."
            else:
                obs1 = self.rng.choice(OBS_ETAPA_1)
            eventos.append((1, obs1, momentos[1]))

            if plano.etapa >= 2:
                eventos.append((2, OBS_ETAPA_2[0] if plano.personagem else self.rng.choice(OBS_ETAPA_2), momentos[2]))
                if not plano.personagem and self.rng.random() < 0.2:
                    pendencia = momentos[2] + timedelta(hours=self.rng.randint(20, 40))
                    if 3 not in momentos or pendencia < momentos[3]:
                        eventos.append((2, "Pendência: foto da conta de luz ilegível, reenvio solicitado.",
                                        min(pendencia, self.agora)))
                        reenvio = pendencia + timedelta(hours=self.rng.randint(4, 30))
                        if (3 not in momentos or reenvio < momentos[3]) and reenvio <= self.agora:
                            eventos.append((2, "Documento reenviado pelo cliente.", reenvio))
            if plano.etapa >= 3:
                plano.protocolo = f"{momentos[3].year}-CEMIG-{self.rng.randint(10000, 99999)}"
                eventos.append((3, f"Protocolo {plano.protocolo} aberto.", momentos[3]))
            if plano.etapa >= 4:
                modelo = self.rng.choice(OBS_ETAPA_4)
                eventos.append((4, modelo.format(instalacao=cli.numero_instalacao, protocolo=plano.protocolo),
                                momentos[4]))
            if plano.etapa >= 5:
                eventos.append((5, OBS_ETAPA_5, momentos[5]))

            if plano.status == "cancelado" and plano.cancelamento_dia is not None:
                momento_cancel = self._momento(plano.cancelamento_dia)
                if plano.liberacao_dia is None:
                    obs = "Processo encerrado: cliente solicitou o cancelamento antes da conexão."
                else:
                    obs = "Contrato encerrado a pedido do cliente."
                eventos.append((plano.etapa, obs, momento_cancel))

            eventos.sort(key=lambda e: e[2])
            for etapa, observacao, momento in eventos:
                self.s.add(AtivacaoEvento(cliente_id=cli.id, etapa=etapa, observacao=observacao, ocorrido_em=momento))

            ultimo = eventos[-1][2]
            self.s.add(Ativacao(
                cliente_id=cli.id,
                etapa_atual=plano.etapa,
                previsao_conclusao=plano.criado_dia + timedelta(days=PRAZO_ATIVACAO_DIAS),
                atualizado_em=ultimo,
            ))
            cli.atualizado_em = ultimo
            if plano.status == "ativo" and self.rng.random() < 0.4:
                # alguma atualizacao cadastral posterior
                cli.atualizado_em = max(ultimo, self._momento(self.hoje - timedelta(days=self.rng.randint(0, 120))))

            # notificacoes de ativacao (etapas 2+), so para quem ainda esta ativando ou ativou ha pouco
            recente = plano.liberacao_dia is not None and (self.hoje - plano.liberacao_dia).days <= 120
            if plano.status == "em_ativacao" or (plano.status == "ativo" and recente):
                for etapa in range(2, plano.etapa + 1):
                    if etapa == 5:
                        titulo, msg = "Energia liberada!", "Sua energia solar foi liberada. O desconto de 15% começa na próxima fatura."
                    else:
                        titulo = "Sua ativação avançou"
                        msg = f"Etapa {etapa} de 5: {TITULOS_ETAPA[etapa]}."
                    self._notificar(plano, "ativacao", titulo, msg, momentos[etapa] + timedelta(minutes=5))
        self.s.flush()

    # ------------------------------------------------------------- indicacoes
    def criar_indicacoes(self) -> None:
        ativos = [p for p in self.planos if p.status == "ativo"]
        limite_recente = self.hoje - timedelta(days=330)
        candidatos = [
            p for p in self.planos
            if p.status in ("ativo", "em_ativacao") and not p.personagem and p.criado_dia >= limite_recente
        ]
        # indicacoes que viraram cliente (o indicado existe no banco)
        for indicado in candidatos:
            if self.rng.random() > 0.45:
                continue
            indicadores = [a for a in ativos if a is not indicado and a.criado_dia <= indicado.criado_dia - timedelta(days=30)]
            if not indicadores:
                continue
            indicador = self.rng.choice(indicadores)
            criado_ind = self._momento(indicado.criado_dia - timedelta(days=self.rng.randint(2, 20)))
            canal = self.rng.choice(["whatsapp", "whatsapp", "link", "email"])
            contato = indicado.cliente.email if canal == "email" else indicado.cliente.telefone
            indicacao = Indicacao(
                id=self._uuid(), cliente_id=indicador.cliente.id, nome_indicado=indicado.cliente.nome,
                contato_indicado=contato, canal=canal, situacao="aderiu", bonus=BONUS_INDICACAO,
                creditado_em=None, criado_em=criado_ind,
            )
            self.s.add(indicacao)
            mes = _mes_str(indicado.criado_dia)
            indicador.creditos.append(_Credito(mes, indicacao))
            indicado.creditos.append(_Credito(mes, None))
            self._notificar(
                indicador, "indicacao", "Sua indicação deu certo!",
                f"{indicado.cliente.nome.split()[0]} aderiu à Bulbe com o seu código "
                f"{indicador.cliente.codigo_indicacao}. Você ganha R$ 50 na próxima fatura.",
                indicado.cliente.criado_em + timedelta(hours=2),
            )

        # pendentes (recentes) e expiradas (mais de 60 dias), com indicados ficticios fora do banco
        for indicador in self.rng.sample(ativos, 14):
            for _ in range(self.rng.choice([1, 1, 2])):
                expirada = self.rng.random() < 0.4
                if expirada:
                    idade_max = (self.hoje - indicador.criado_dia).days - 5
                    if idade_max <= VALIDADE_INDICACAO_DIAS + 10:
                        continue
                    dias = self.rng.randint(VALIDADE_INDICACAO_DIAS + 10, min(idade_max, 400))
                else:
                    dias = self.rng.randint(1, 45)
                self._indicacao_ficticia(indicador, "expirada" if expirada else "pendente", dias)

        # Marcos Andrade: duas indicacoes pendentes (Renato Souza vem do exemplo da API)
        marcos = next(p for p in self.planos if p.personagem)
        self.s.add(Indicacao(
            id=self._uuid(), cliente_id=marcos.cliente.id, nome_indicado="Renato Souza",
            contato_indicado="31966665555", canal="whatsapp", situacao="pendente",
            bonus=BONUS_INDICACAO, criado_em=self._momento(self.hoje - timedelta(days=3)),
        ))
        self._indicacao_ficticia(marcos, "pendente", 1, canal="link")
        self.s.flush()

    def _indicacao_ficticia(self, indicador: _PlanoCliente, situacao: str, dias_atras: int,
                            canal: Optional[str] = None) -> None:
        nome, primeiro, ultimo = self._nome()
        canal = canal or self.rng.choice(["whatsapp", "whatsapp", "link", "email"])
        if canal == "email":
            contato = f"{_sem_acentos(primeiro).lower()}.{_sem_acentos(ultimo).lower()}@email.com"
        else:
            contato = self._telefone(indicador.ddd)
        self.s.add(Indicacao(
            id=self._uuid(), cliente_id=indicador.cliente.id, nome_indicado=nome, contato_indicado=contato,
            canal=canal, situacao=situacao, bonus=BONUS_INDICACAO,
            criado_em=self._momento(self.hoje - timedelta(days=dias_atras)),
        ))

    # ------------------------------------------------------------- faturas
    def criar_faturas(self) -> None:
        ultimo_ano, ultimo_mes = _somar_meses(self.hoje.year, self.hoje.month, -1)
        for plano in self.planos:
            if plano.liberacao_dia is None:
                continue  # em ativacao ou cancelado antes da conexao: nenhuma fatura
            ano, mes = _somar_meses(plano.liberacao_dia.year, plano.liberacao_dia.month, 1)
            fim_ano, fim_mes = ultimo_ano, ultimo_mes
            if plano.cancelamento_dia is not None:
                fim_ano, fim_mes = _somar_meses(plano.cancelamento_dia.year, plano.cancelamento_dia.month, -1)
            meses: list[tuple[int, int]] = []
            while (ano, mes) <= (fim_ano, fim_mes):
                meses.append((ano, mes))
                ano, mes = _somar_meses(ano, mes, 1)
            meses = meses[-12:]  # historico dos ultimos 12 meses

            pendentes = sorted(plano.creditos, key=lambda c: c.mes_minimo)
            for posicao, (ano, mes) in enumerate(meses):
                referencia = f"{ano:04d}-{mes:02d}"
                fator = 1.10 if mes in (10, 11, 12, 1, 2, 3) else (0.92 if mes in (6, 7, 8) else 1.0)
                consumo = round(plano.consumo_base_kwh * fator * self.rng.uniform(0.88, 1.12))
                valor_sem = round(consumo * TARIFA_KWH, 2)
                desconto = round(valor_sem * PERCENTUAL_DESCONTO, 2)
                emissao_ano, emissao_mes = _somar_meses(ano, mes, 1)
                emissao = date(emissao_ano, emissao_mes, 1)
                vencimento = date(emissao_ano, emissao_mes, plano.dia_vencimento)

                bonus = 0.0
                restantes: list[_Credito] = []
                for credito in pendentes:
                    if credito.mes_minimo <= referencia and bonus + BONUS_INDICACAO <= valor_sem - desconto:
                        bonus += BONUS_INDICACAO
                        if credito.indicacao is not None:
                            credito.indicacao.creditado_em = emissao
                    else:
                        restantes.append(credito)
                pendentes = restantes

                # bonus especial do Clube: R$ 50 na primeira fatura emitida depois da abertura da carta
                creditos_clube = [d for d in plano.creditos_clube if d < emissao]
                plano.creditos_clube = [d for d in plano.creditos_clube if d >= emissao]
                disponivel = round(valor_sem - desconto - bonus, 2)
                bonus_clube = round(min(BONUS_CLUBE * len(creditos_clube), max(0.0, disponivel)), 2)
                valor_total = round(max(0.0, disponivel - bonus_clube), 2)

                ultimas = posicao >= len(meses) - 2
                if vencimento < self.hoje:
                    if plano.inadimplente and ultimas:
                        situacao, pago_em = "vencida", None
                    else:
                        situacao = "paga"
                        if self.rng.random() < 0.12:
                            pago_em = vencimento + timedelta(days=self.rng.randint(1, 6))
                        else:
                            pago_em = vencimento - timedelta(days=self.rng.randint(0, 7))
                        pago_em = min(max(pago_em, emissao), self.hoje)
                else:
                    if self.rng.random() < 0.35 and emissao <= self.hoje:
                        situacao = "paga"
                        pago_em = emissao + timedelta(days=self.rng.randint(0, max(0, (self.hoje - emissao).days)))
                    else:
                        situacao, pago_em = "em_aberto", None

                fatura = Fatura(
                    cliente_id=plano.cliente.id, mes_referencia=referencia, consumo_kwh=float(consumo),
                    valor_sem_bulbe=valor_sem, desconto=desconto, bonus_indicacao=bonus,
                    bonus_clube=bonus_clube, valor_total=valor_total, vencimento=vencimento, situacao=situacao, pago_em=pago_em,
                )
                self.s.add(fatura)
                plano.faturas.append(fatura)

                # notificacoes de fatura
                rotulo = _formatar_mes(referencia)
                if situacao == "em_aberto":
                    self._notificar(plano, "vencimento", "Sua fatura vence em breve",
                                    f"A fatura de {rotulo} (R$ {valor_total:.2f}) vence em {vencimento:%d/%m/%Y}.",
                                    datetime.combine(self._dia_aviso(emissao, vencimento), time(10, 0)))
                elif situacao == "vencida":
                    self._notificar(plano, "vencimento", "Fatura vencida",
                                    f"A fatura de {rotulo} (R$ {valor_total:.2f}) venceu em {vencimento:%d/%m/%Y}. "
                                    "Regularize para evitar encargos.",
                                    datetime.combine(vencimento + timedelta(days=2), time(10, 0)))
                elif posicao == len(meses) - 1:
                    self._notificar(plano, "vencimento", "Fatura disponível",
                                    f"Sua fatura de {rotulo} está disponível no app. Economia de R$ {desconto + bonus + bonus_clube:.2f}.",
                                    datetime.combine(emissao, time(8, 0)))
        self.s.flush()

    def _dia_aviso(self, emissao: date, vencimento: date) -> date:
        """Aviso de vencimento 3 dias antes; se isso ainda for futuro, usa a data de emissao."""
        dia = max(emissao, vencimento - timedelta(days=3))
        return dia if dia <= self.hoje else emissao

    # ------------------------------------------------------------- adesoes
    def criar_adesoes(self) -> None:
        em_ativacao = [p for p in self.planos if p.status == "em_ativacao"]
        marcos = next(p for p in em_ativacao if p.personagem)
        outros = self.rng.sample([p for p in em_ativacao if not p.personagem], 7)
        for plano in [marcos, *outros]:
            cli = plano.cliente
            valor = round(plano.consumo_base_kwh * TARIFA_KWH, 2)
            origem = "app" if plano.personagem else self.rng.choices(["app", "site", "whatsapp"], [6, 3, 1])[0]
            self.s.add(Adesao(
                id=self._uuid(), nome=cli.nome, email=cli.email, cpf=cli.cpf, telefone=cli.telefone,
                cidade=cli.cidade, uf=cli.uf, distribuidora="CEMIG", numero_instalacao=cli.numero_instalacao,
                valor_conta_atual=valor, economia_mensal_estimada=round(valor * PERCENTUAL_DESCONTO, 2),
                situacao="aprovada", origem=origem, cliente_id=cli.id,
                criado_em=cli.criado_em - timedelta(days=self.rng.randint(1, 3), hours=self.rng.randint(0, 5)),
            ))

        # Clara Ribeiro (persona do front): adesao enviada pelo app, ainda nao e cliente
        cpf_clara = self._cpf()
        self.s.add(Adesao(
            id=self._uuid(), nome="Clara Ribeiro", email="clara.ribeiro@email.com", cpf=cpf_clara,
            telefone="31977776666", cidade="Belo Horizonte", uf="MG", distribuidora="CEMIG",
            numero_instalacao=self._instalacao(), valor_conta_atual=320.00, economia_mensal_estimada=48.00,
            situacao="enviada", origem="app", cliente_id=None,
            criado_em=self._momento(self.hoje - timedelta(days=2), 9, 12),
        ))
        self._emails.add("clara.ribeiro@email.com")

        # enviadas, rascunhos e recusadas de pessoas que ainda nao sao clientes
        especificacoes = [
            ("enviada", 0, 6), ("enviada", 0, 6), ("enviada", 1, 8),
            ("rascunho", 1, 20), ("rascunho", 3, 25),
            ("recusada", 15, 60), ("recusada", 20, 90),
        ]
        for i, (situacao, dmin, dmax) in enumerate(especificacoes):
            nome, primeiro, ultimo = self._nome()
            cidade, ddd, _, _ = self._cidade()
            valor = round(self.rng.uniform(140, 780), 2)
            distribuidora = "CEMIG"
            if situacao == "recusada" and i == len(especificacoes) - 2:
                distribuidora = "Energisa Minas Rio"  # fora da area CEMIG atendida pela Bulbe
                cidade, ddd = "Muriaé", "32"
            rascunho = situacao == "rascunho"
            self.s.add(Adesao(
                id=self._uuid(), nome=nome, email=self._email(primeiro, ultimo),
                cpf=None if rascunho and i % 2 else self._cpf(),
                telefone=self._telefone(ddd), cidade=cidade, uf="MG", distribuidora=distribuidora,
                numero_instalacao=None if rascunho else self._instalacao(),
                valor_conta_atual=valor, economia_mensal_estimada=round(valor * PERCENTUAL_DESCONTO, 2),
                situacao=situacao, origem=self.rng.choices(["app", "site", "whatsapp"], [6, 3, 1])[0],
                cliente_id=None,
                criado_em=self._momento(self.hoje - timedelta(days=self.rng.randint(dmin, dmax))),
            ))
        self.s.flush()

    # ------------------------------------------------------------- clube bulbe
    def criar_clube(self) -> None:
        for plano in self.planos:
            cli = plano.cliente
            if not cli.app_acesso_habilitado or plano.status == "cancelado":
                continue
            semanas_hist = self.rng.randint(2, 14)
            primeira = max(plano.criado_dia + timedelta(days=1), self.hoje - timedelta(weeks=semanas_hist))
            sequencia = 0
            semana = 0
            proxima: Optional[datetime] = None
            ultima_carta: Optional[Carta] = None
            intervalo = timedelta(days=INTERVALO_CARTA_DIAS)
            while True:
                dia = primeira + timedelta(days=INTERVALO_CARTA_DIAS * semana)
                disponivel_em = datetime.combine(dia, time(9, 0))
                if disponivel_em > self.agora:
                    proxima = disponivel_em  # sempre no futuro
                    break
                semana += 1
                janela_aberta = (self.agora - disponivel_em) < intervalo

                if sequencia >= META_SEQUENCIA:
                    # 5 semanas seguidas: a carta da vez e a especial (R$ 50 na fatura)
                    if janela_aberta:
                        # liberada nos ultimos 7 dias e ainda nao aberta: bonus pendente
                        carta = Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="especial",
                                      situacao="disponivel", disponivel_em=disponivel_em)
                        self.s.add(carta)
                        ultima_carta, proxima = carta, disponivel_em + intervalo
                        break
                    # especial antiga: foi aberta (bonus aplicado) ou expirou; a sequencia recomeca
                    if self.rng.random() < 0.75:
                        aberta_em = self._abertura(disponivel_em)
                        carta = Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="especial",
                                      situacao="aberta", disponivel_em=disponivel_em, aberta_em=aberta_em)
                        self.s.add(carta)
                        carta.cupom = self._cupom_especial(cli, carta, aberta_em)
                        plano.creditos_clube.append(aberta_em.date())
                    else:
                        carta = Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="especial",
                                      situacao="expirada", disponivel_em=disponivel_em)
                        self.s.add(carta)
                    ultima_carta = carta
                    sequencia = 0
                    continue

                abriu = self.rng.random() < (0.55 if janela_aberta else 0.82)
                if not abriu and janela_aberta:
                    carta = Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="normal",
                                  situacao="disponivel", disponivel_em=disponivel_em)
                    self.s.add(carta)
                    ultima_carta, proxima = carta, disponivel_em + intervalo
                    break
                if not abriu:
                    self.s.add(Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="normal",
                                     situacao="expirada", disponivel_em=disponivel_em))
                    sequencia = 0
                    continue

                aberta_em = self._abertura(disponivel_em)
                carta = Carta(id=self._uuid(), cliente_id=cli.id, semana=semana, tipo="normal",
                              situacao="aberta", disponivel_em=disponivel_em, aberta_em=aberta_em)
                self.s.add(carta)
                ultima_carta = carta
                carta.cupom = self._cupom_da_carta(cli, carta, aberta_em)
                sequencia += 1

            # pendente: carta especial disponivel agora ou a proxima carta (futura) sera a especial
            pendente = sequencia >= META_SEQUENCIA
            self.s.add(ClubeStatus(
                cliente_id=cli.id, semanas_sequencia=min(sequencia, META_SEQUENCIA),
                meta_sequencia=META_SEQUENCIA, proxima_carta_em=proxima,
                bonus_especial_pendente=pendente,
                atualizado_em=(ultima_carta.aberta_em or ultima_carta.disponivel_em) if ultima_carta else self.agora,
            ))
            if ultima_carta is not None and ultima_carta.situacao == "disponivel":
                if ultima_carta.tipo == "especial":
                    titulo, msg = "Carta especial liberada!", "Você completou 5 semanas seguidas. Abra a carta e ganhe R$ 50 na fatura."
                else:
                    titulo, msg = "Sua carta da semana chegou", "Abra a carta do Clube Bulbe no app e descubra sua recompensa."
                self._notificar(plano, "clube", titulo, msg, ultima_carta.disponivel_em, canal="app")
            self.s.flush()

    def _abertura(self, disponivel_em: datetime) -> datetime:
        """Instante de abertura de uma carta: dentro da janela de 7 dias e nunca no futuro."""
        limite = min(disponivel_em + timedelta(days=INTERVALO_CARTA_DIAS - 1), self.agora)
        segundos = max(0, int((limite - disponivel_em).total_seconds()))
        return disponivel_em + timedelta(seconds=self.rng.randint(0, segundos))

    def _cupom_especial(self, cli: Cliente, carta: Carta, aberta_em: datetime) -> Cupom:
        """Recompensa da carta especial (final.js -> RECOMPENSA_ESPECIAL): R$ 50 aplicados automaticamente."""
        cupom = Cupom(
            id=self._uuid(), cliente_id=cli.id, carta_id=carta.id, parceiro_id=self.parceiros["Bulbe Energia"].id,
            titulo="R$ 50 de desconto na fatura",
            descricao="Desconto de R$ 50 aplicado automaticamente na sua próxima fatura. Nenhuma ação necessária.",
            codigo=None, situacao="usado", aberto_em=aberta_em,
            valido_ate=aberta_em.date() + timedelta(days=VALIDADE_CUPOM_DIAS), usado_em=aberta_em,
        )
        self.s.add(cupom)
        return cupom

    def _cupom_da_carta(self, cli: Cliente, carta: Carta, aberta_em: datetime) -> Cupom:
        parceiro_nome, titulo, descricao, codigo = self.rng.choice(RECOMPENSAS)
        valido_ate = aberta_em.date() + timedelta(days=VALIDADE_CUPOM_DIAS)
        usado_em: Optional[datetime] = None
        sorteio = self.rng.random()
        if valido_ate < self.hoje:
            situacao = "usado" if sorteio < 0.5 else ("expirado" if sorteio < 0.9 else "descartado")
            if situacao == "usado":
                usado_em = aberta_em + timedelta(hours=self.rng.randint(1, VALIDADE_CUPOM_DIAS * 24 - 1))
        else:
            situacao = "ativo" if sorteio < 0.45 else ("salvo" if sorteio < 0.75 else "usado")
            if situacao == "usado":
                segundos = max(0, int((self.agora - aberta_em).total_seconds()))
                usado_em = aberta_em + timedelta(seconds=self.rng.randint(0, segundos))
        cupom = Cupom(
            id=self._uuid(), cliente_id=cli.id, carta_id=carta.id, parceiro_id=self.parceiros[parceiro_nome].id,
            titulo=titulo, descricao=descricao, codigo=codigo, situacao=situacao,
            aberto_em=aberta_em, valido_ate=valido_ate, usado_em=usado_em,
        )
        self.s.add(cupom)
        return cupom

    # ------------------------------------------------------------- notificacoes
    def _notificar(self, plano: _PlanoCliente, tipo: str, titulo: str, mensagem: str,
                   enviada_em: datetime, canal: Optional[str] = None) -> None:
        if enviada_em > self.agora or enviada_em < plano.cliente.criado_em:
            return  # nunca no futuro nem antes do cadastro do cliente
        if canal is None:
            if plano.cliente.app_acesso_habilitado:
                canal = "app"
            else:
                canal = self.rng.choice(["whatsapp", "email"])
        idade = (self.agora - enviada_em).days
        lida = self.rng.random() < (0.85 if idade > 7 else 0.4)
        self.s.add(Notificacao(cliente_id=plano.cliente.id, tipo=tipo, titulo=titulo, mensagem=mensagem,
                               canal=canal, enviada_em=enviada_em, lida=lida))

    def criar_promocoes(self) -> None:
        cafe = self.parceiros["Café Serrano Mineiro"]
        for plano in self.planos:
            if plano.status == "cancelado" or self.rng.random() > 0.35:
                continue
            # clientes cadastrados depois do anuncio sao pulados dentro de _notificar
            # (a notificacao nunca fica antes do criado_em do cliente)
            self._notificar(plano, "promocao", "Novo parceiro no Clube Bulbe",
                            f"{cafe.nome} agora faz parte do Clube Bulbe. Fique de olho nas próximas cartas!",
                            cafe.criado_em + timedelta(days=1, hours=self.rng.randint(0, 6)))
        self.s.flush()

    # ------------------------------------------------------------- atendimentos
    def _status_atendimento(self, criado: datetime) -> tuple[str, Optional[datetime]]:
        idade = (self.agora - criado).days
        if idade > 10 or (idade > 3 and self.rng.random() < 0.6):
            return "resolvido", min(criado + timedelta(hours=self.rng.randint(2, 96)), self.agora)
        return self.rng.choice(["aberto", "em_andamento"]), None

    def _atendimento(self, plano: _PlanoCliente, canal: str, assunto: str, descricao: str,
                     criado: datetime, status: Optional[str] = None,
                     resolvido_em: Optional[datetime] = None) -> None:
        criado = self._apos_cadastro(plano.cliente, criado)  # nunca antes do cadastro do cliente
        if status is None:
            status, resolvido_em = self._status_atendimento(criado)
        if resolvido_em is not None:
            resolvido_em = min(max(resolvido_em, criado), self.agora)
        self.s.add(Atendimento(cliente_id=plano.cliente.id, canal=canal, assunto=assunto, descricao=descricao,
                               status=status, criado_em=criado, resolvido_em=resolvido_em))

    def criar_atendimentos(self) -> None:
        canais = ["whatsapp", "whatsapp", "email", "app"]
        for plano in self.planos:
            cli = plano.cliente
            if plano.personagem:
                self._atendimento(plano, "app", "Dúvida sobre documentos",
                                  "Cliente quer confirmar se a conta de luz enviada pelo app foi aceita na etapa de documentos.",
                                  self._momento(self.hoje - timedelta(days=2)), status="em_andamento")
                continue
            if plano.status == "em_ativacao":
                if self.rng.random() < 0.4:
                    dias = (self.hoje - plano.criado_dia).days
                    criado = self._apos_cadastro(
                        cli, self._momento(self.hoje - timedelta(days=self.rng.randint(0, dias))), 60)
                    self._atendimento(plano, self.rng.choice(canais), "Prazo de ativação",
                                      "Cliente perguntou quando a energia será liberada; informado o prazo de até "
                                      f"90 dias e a etapa atual ({TITULOS_ETAPA[plano.etapa]}).", criado)
            elif plano.status == "cancelado" and plano.cancelamento_dia is not None:
                criado = max(
                    cli.criado_em + timedelta(hours=1),
                    self._momento(plano.cancelamento_dia - timedelta(days=self.rng.randint(2, 10))),
                )
                motivo = self.rng.choice([
                    "mudança de endereço para fora da área atendida",
                    "mudança para imóvel alugado com conta em nome do proprietário",
                    "preferiu não aguardar a conclusão da ativação" if plano.liberacao_dia is None
                    else "redução de custos da empresa",
                ])
                canal = "ouvidoria" if self.rng.random() < 0.2 else self.rng.choice(["whatsapp", "email"])
                self._atendimento(plano, canal, "Solicitação de cancelamento",
                                  f"Cliente pediu o cancelamento ({motivo}). Contrato encerrado.", criado,
                                  status="resolvido", resolvido_em=self._momento(plano.cancelamento_dia))
            elif plano.status == "ativo":
                if plano.inadimplente:
                    vencidas = [f for f in plano.faturas if f.situacao == "vencida"]
                    if vencidas:
                        f = vencidas[0]
                        criado = self._momento(min(self.hoje, f.vencimento + timedelta(days=self.rng.randint(3, 10))))
                        self._atendimento(plano, "whatsapp", "Negociação de fatura vencida",
                                          f"Cliente pediu para parcelar a fatura de {_formatar_mes(f.mes_referencia)} "
                                          f"(R$ {f.valor_total:.2f}), vencida em {f.vencimento:%d/%m/%Y}.",
                                          criado, status=self.rng.choice(["aberto", "em_andamento"]))
                if self.rng.random() < 0.45 and plano.faturas:
                    assunto, modelo = self.rng.choice(ASSUNTOS_ATENDIMENTO_ATIVO)
                    fatura = self.rng.choice(plano.faturas)
                    criado = self._momento(min(self.hoje, fatura.vencimento - timedelta(days=self.rng.randint(0, 4))))
                    canal = "app" if cli.app_acesso_habilitado and self.rng.random() < 0.4 else self.rng.choice(canais)
                    self._atendimento(plano, canal, assunto,
                                      modelo.format(mes=_formatar_mes(fatura.mes_referencia)), criado)
        self.s.flush()

    # ------------------------------------------------------------- simulacoes
    def criar_simulacoes(self) -> None:
        for _ in range(QTD_SIMULACOES):
            dias = int(self.rng.triangular(0, 180, 0))
            criado = self._momento(self.hoje - timedelta(days=dias), 6, 24)
            valor = round(min(2000.0, max(90.0, self.rng.lognormvariate(5.6, 0.45))), 2)
            meses = self.rng.choices([1, 3, 6, 12, 24], [5, 10, 20, 50, 15])[0]
            amigos = self.rng.choices([0, 1, 2, 3, 4, 5], [45, 20, 15, 10, 5, 5])[0]
            cliente_id: Optional[str] = None
            origem = "visitante"
            if self.rng.random() < 0.25:
                possiveis = [p for p in self.planos if p.cliente.criado_em <= criado]
                if possiveis:
                    cliente_id = self.rng.choice(possiveis).cliente.id
                    origem = "cliente"
            economia = round(valor * PERCENTUAL_DESCONTO * meses + amigos * BONUS_INDICACAO, 2)
            self.s.add(Simulacao(origem=origem, cliente_id=cliente_id, valor_conta=valor, meses=meses,
                                 amigos_indicados=amigos, economia_total=economia, criado_em=criado))
        self.s.flush()

    # ------------------------------------------------------------- auditoria (v2)
    def criar_auditoria(self) -> None:
        """
        ~120 registros plausiveis de auditoria_acessos nos ultimos 90 dias: logins (ok e com erro de
        digitacao), fichas de clientes vistas, consultas a auditoria pelo admin, tentativas com e-mails
        inexistentes, uma rajada de falhas contra o admin (alerta por e-mail + bloqueio) e um expurgo.
        Tudo fica com pelo menos 1 dia de idade, para nao interferir na janela de bloqueio de login.
        """
        registros: list[AuditoriaAcesso] = []
        pesos = [2 if f.perfil == "admin" else 3 for f in self.funcionarios]
        admin = next(f for f in self.funcionarios if f.perfil == "admin")

        def dia_aleatorio() -> datetime:
            return self._momento(self.hoje - timedelta(days=self.rng.randint(2, 90)), 8, 19)

        def ip_do_funcionario() -> str:
            return self.rng.choice(IPS_ESCRITORIO if self.rng.random() < 0.8 else IPS_EXTERNOS)

        def registrar(acao: str, momento: datetime, funcionario: Optional[Funcionario] = None,
                      email: Optional[str] = None, ip: Optional[str] = None,
                      recurso_tipo: Optional[str] = None, recurso_id: Optional[str] = None,
                      detalhe: Optional[str] = None) -> None:
            registros.append(AuditoriaAcesso(
                funcionario_id=funcionario.id if funcionario else None,
                email_informado=email if email is not None else (funcionario.email if funcionario else None),
                acao=acao, recurso_tipo=recurso_tipo, recurso_id=recurso_id, ip=ip, detalhe=detalhe,
                criado_em=min(momento, self.agora - timedelta(days=1)),
            ))

        def ver_fichas(funcionario: Funcionario, inicio: datetime, ip: str) -> None:
            momento = inicio
            for _ in range(self.rng.choice([0, 1, 1, 1, 2])):
                momento += timedelta(minutes=self.rng.randint(3, 40))
                clientes = [p.cliente for p in self.planos if p.cliente.criado_em < momento]
                if clientes:
                    cliente = self.rng.choice(clientes)
                    registrar("ver_ficha", momento, funcionario, ip=ip, recurso_tipo="cliente", recurso_id=cliente.id)

        # logins bem-sucedidos, cada um seguido de 0 a 2 fichas vistas
        for _ in range(QTD_LOGINS_AUDITORIA):
            funcionario = self.rng.choices(self.funcionarios, weights=pesos, k=1)[0]
            momento, ip = dia_aleatorio(), ip_do_funcionario()
            registrar("login_ok", momento, funcionario, ip=ip)
            ver_fichas(funcionario, momento, ip)

        # erros de digitacao da senha, seguidos do login certo
        for _ in range(QTD_FALHAS_DIGITACAO):
            funcionario = self.rng.choices(self.funcionarios, weights=pesos, k=1)[0]
            momento, ip = dia_aleatorio(), ip_do_funcionario()
            registrar("login_falha", momento, funcionario, ip=ip, detalhe="Senha incorreta.")
            momento += timedelta(seconds=self.rng.randint(20, 120))
            registrar("login_ok", momento, funcionario, ip=ip)
            ver_fichas(funcionario, momento, ip)

        # e-mails que nao existem (funcionario_id nulo)
        for _ in range(QTD_FALHAS_EMAIL_INEXISTENTE):
            registrar("login_falha", dia_aleatorio(), email=self.rng.choice(EMAILS_INEXISTENTES),
                      ip=self.rng.choice(IPS_EXTERNOS + IPS_ESCRITORIO), detalhe="E-mail não cadastrado.")

        # admin consultando a auditoria
        for _ in range(QTD_VER_AUDITORIA):
            momento, ip = dia_aleatorio(), self.rng.choice(IPS_ESCRITORIO)
            registrar("login_ok", momento, admin, ip=ip)
            filtro = self.rng.choice([None, "acao=login_falha", "acao=ver_ficha", f"funcionario_id={admin.id}"])
            registrar("ver_auditoria", momento + timedelta(minutes=self.rng.randint(1, 10)), admin, ip=ip,
                      detalhe=f"Filtros: {filtro}." if filtro else None)

        # rajada de senhas erradas contra o admin: alerta na 4a falha e bloqueio depois da 5a
        momento = self._momento(self.hoje - timedelta(days=self.rng.randint(30, 50)), 2, 5)
        for numero in range(1, 6):
            momento += timedelta(seconds=self.rng.randint(15, 50))
            registrar("login_falha", momento, admin, ip=IP_ATAQUE, detalhe="Senha incorreta.")
            if numero == 4:
                registrar("alerta_email", momento + timedelta(seconds=2), admin, ip=IP_ATAQUE,
                          detalhe="Alerta de 4 falhas de login em 15 minutos enviado ao e-mail de segurança.")
        for _ in range(2):
            momento += timedelta(seconds=self.rng.randint(15, 50))
            registrar("login_bloqueado", momento, admin, ip=IP_ATAQUE,
                      detalhe="Login bloqueado: 5 falhas em 15 minutos.")

        # um expurgo de retencao rodado pelo admin (nada antigo o bastante para apagar)
        momento, ip = self._momento(self.hoje - timedelta(days=self.rng.randint(10, 25)), 9, 17), IPS_ESCRITORIO[0]
        registrar("login_ok", momento, admin, ip=ip)
        registrar("expurgo", momento + timedelta(minutes=2), admin, ip=ip,
                  detalhe="Retenção: chat 180 dias, auditoria 730 dias. Apagados: chat_historico=0, "
                          "chat_conversas=0, chat_mensagens=0, auditoria=0.")

        registros.sort(key=lambda r: r.criado_em)
        self.s.add_all(registros)
        self.s.flush()

    # ------------------------------------------------------------- orquestracao
    def executar(self) -> None:
        self.criar_funcionarios()
        self.criar_usinas()
        self.criar_parceiros()
        self.criar_dicas()
        self.s.flush()
        self.criar_clientes()
        self.criar_ativacoes()
        self.criar_indicacoes()
        self.criar_clube()  # antes das faturas: a carta especial aberta vira bonus_clube na fatura seguinte
        self.criar_faturas()
        self.criar_adesoes()
        self.criar_promocoes()
        self.criar_atendimentos()
        self.criar_simulacoes()
        self.criar_auditoria()
        # chat_conversas / chat_mensagens / chat_historico comecam vazios (o chat comeca do zero)


def popular_banco(sessao: Session, semente: int = SEMENTE_PADRAO) -> None:
    """
    Popula o banco com dados ficticios coerentes entre as tabelas.
    Nao faz commit: quem chama (ex.: obter_sessao) decide. Espera as tabelas vazias.
    """
    _GeradorFicticio(sessao, semente).executar()
    sessao.flush()


def main() -> None:
    """Apaga e recria o banco ficticio (python -m app.database.seed)."""
    from app.database.conexao import BULBE_DB_URL, inicializar_banco

    inicializar_banco(recriar=True)
    print(f"Banco ficticio recriado em: {BULBE_DB_URL}")


if __name__ == "__main__":
    main()
