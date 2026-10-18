# Contratos entre as pastas — Painel de Gestão + Chatbot Bulbe

> Documento do **líder** (somente leitura para os agentes). Ele define as interfaces
> que cada pasta expõe para as outras, para que todos trabalhem em paralelo sem
> editar arquivos alheios. Se algo aqui estiver errado ou faltando, **não edite**:
> anote em `NOTAS_PARA_O_LIDER.md` dentro da sua própria pasta.

Branch: `feat/python-adiciona-chatbot` · Stack: FastAPI + SQLAlchemy 2 (SQLite) + Anthropic SDK (Claude Haiku 5.5) + HTML/CSS/JS puro.

## Regras para todos os agentes

1. Edite **somente** a sua pasta (tabela abaixo). Ler qualquer arquivo é permitido.
2. **Não** rode `npm install` nem `pip install`. **Não** suba o servidor nem rode o sistema/seed.
   Validação permitida: `python -m py_compile <arquivo>` (só checa sintaxe).
3. **Não** faça `git add`, `git commit`, `git push`, `git checkout` nem crie branches. Só o líder commita.
4. Documente o que fez em `CHANGELOG.md` (ou `README.md`) dentro da sua pasta.
5. Código, nomes e comentários em **português**, no mesmo estilo do projeto
   (docstring de módulo no topo: `"""Camada X, ..."""`, type hints, sem acentos em identificadores).
6. Todos os dados são **fictícios**. Nunca use dados reais de pessoas.

| Agente | Pasta que pode editar | Entrega |
|---|---|---|
| `db` | `app/database/` | Modelos SQLAlchemy, conexão, seed fictício, consultas somente leitura, hash de senha |
| `chatbot` | `app/chatbot/` | Integração com o Claude Haiku (tool use), ferramentas, base de conhecimento, rota de chat |
| `painel` | `app/painel/` | Autenticação do funcionário, rotas do painel e a interface web (HTML/CSS/JS) |
| `docs` | `docs/chatbot/` (exceto este arquivo) | Levantamento de funcionalidades, arquitetura, dicionário de dados, guia de uso |
| líder | `app/main.py`, `app/requirements.txt`, `.env.example`, `.gitignore`, `README.md`, este arquivo | Integração final e commits |

Imports sempre absolutos a partir de `app` (ex.: `from app.database.consultas import obter_cliente`), igual ao código existente.
Cada pasta nova deve ter um `__init__.py`.

---

## 1. `app/database/` (agente `db`)

### 1.1 `app/database/conexao.py`
```python
Base                      # declarative_base do SQLAlchemy 2 (class Base(DeclarativeBase))
engine                    # create_engine(BULBE_DB_URL), default: sqlite no arquivo app/database/bulbe_ficticio.db
SessionLocal              # sessionmaker(bind=engine, expire_on_commit=False)
def obter_sessao() -> Iterator[Session]          # @contextmanager: abre, commita se ok, rollback em erro, fecha
def inicializar_banco(recriar: bool = False) -> None
    # cria as tabelas; se a tabela clientes estiver vazia (ou recriar=True), chama seed.popular_banco
```
Variável de ambiente: `BULBE_DB_URL` (opcional). Para SQLite usar `connect_args={"check_same_thread": False}`.

### 1.2 `app/database/seguranca.py` (só stdlib)
```python
def gerar_hash_senha(senha: str) -> str          # pbkdf2_hmac sha256, salt aleatório, formato "pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>"
def verificar_senha(senha: str, senha_hash: str) -> bool   # compara com hmac.compare_digest
```

### 1.3 Tabelas (`app/database/modelos.py`)
IDs de cliente, adesão, carta, cupom, indicação, parceiro: UUID v4 em string. Demais: inteiro autoincremento.
Datas em `date`/`datetime` (UTC). Valores monetários em `float` com 2 casas.
A coluna "Origem" diz se a funcionalidade **já existe no app da Bulbe** ou foi **criada pela squad Cleanergy**.

| Tabela | Campos principais | Origem |
|---|---|---|
| `funcionarios` | id, nome, email (único), senha_hash, perfil (`atendimento`/`admin`), ativo, criado_em | painel (novo) |
| `usinas` | id, nome, localizacao, capacidade_geracao_kwh, status (`ativa`/`em_manutencao`/`inativa`), data_ativacao | Bulbe |
| `clientes` | id, nome, email, cpf (só dígitos), telefone (só dígitos), tipo (`residencia`/`empresa`), cep, logradouro, numero, complemento, bairro, cidade, uf, distribuidora (`CEMIG`), numero_instalacao (único), usina_id, status (`ativo`/`em_ativacao`/`cancelado`), codigo_indicacao (único, ex. `MARCOS50`), app_acesso_habilitado (bool), ultimo_login_app (datetime ou null), criado_em, atualizado_em | Bulbe |
| `adesoes` | id, nome, email, cpf, telefone, cidade, uf, distribuidora, numero_instalacao, valor_conta_atual, economia_mensal_estimada, situacao (`rascunho`/`enviada`/`aprovada`/`recusada`), origem (`app`/`site`/`whatsapp`), cliente_id (null até aprovar), criado_em | squad (adesão pelo app) + Bulbe (site) |
| `ativacoes` | cliente_id (PK/FK), etapa_atual (1–5), previsao_conclusao (date), atualizado_em | squad (jornada 5 etapas) |
| `ativacao_eventos` | id, cliente_id, etapa, observacao, ocorrido_em | squad |
| `faturas` | id, cliente_id, mes_referencia (`AAAA-MM`), consumo_kwh, valor_sem_bulbe, desconto, bonus_indicacao, valor_total, vencimento, situacao (`paga`/`em_aberto`/`vencida`), pago_em | Bulbe (2ª via / histórico) |
| `indicacoes` | id, cliente_id, nome_indicado, contato_indicado, canal (`whatsapp`/`link`/`email`), situacao (`pendente`/`aderiu`/`expirada`), bonus (50.00), creditado_em, criado_em | Bulbe (Indique e Ganhe) |
| `parceiros` | id, nome, categoria, logo_url, ativo, criado_em | squad (Clube Bulbe) |
| `clube_status` | cliente_id (PK/FK), semanas_sequencia (0–5), meta_sequencia (5), proxima_carta_em, bonus_especial_pendente (bool), atualizado_em | squad (Clube Bulbe) |
| `cartas` | id, cliente_id, semana, tipo (`normal`/`especial`), situacao (`disponivel`/`aberta`/`expirada`), disponivel_em, aberta_em, cupom_id | squad |
| `cupons` | id, cliente_id, carta_id, parceiro_id, titulo, descricao, codigo, situacao (`ativo`/`salvo`/`usado`/`expirado`/`descartado`), aberto_em, valido_ate, usado_em | squad (Bulbe tem "promoções" genéricas) |
| `dicas` | id, titulo, descricao, economia_mensal, economia_anual, ordem | squad |
| `simulacoes` | id, origem (`visitante`/`cliente`), cliente_id (null), valor_conta, meses, amigos_indicados, economia_total, criado_em | squad (simulador sem login / modo visitante) |
| `notificacoes` | id, cliente_id, tipo (`vencimento`/`ativacao`/`clube`/`indicacao`/`promocao`), titulo, mensagem, canal (`app`/`whatsapp`/`email`), enviada_em, lida | Bulbe |
| `atendimentos` | id, cliente_id, canal (`whatsapp`/`email`/`app`/`ouvidoria`), assunto, descricao, status (`aberto`/`em_andamento`/`resolvido`), criado_em, resolvido_em | Bulbe |
| `chat_historico` | id, funcionario_id, pergunta, resposta, ferramentas_usadas (texto JSON), criado_em | painel (auditoria do chatbot) |

### 1.4 Regras de negócio (vindas do front-end e do site da Bulbe)
- Desconto de **15%** sobre a conta (não incide sobre iluminação pública e PIS/COFINS).
- **R$ 50** por indicação válida (para quem indica e para o indicado).
- Ativação em **até 90 dias**, 5 etapas: 1 Cadastro, 2 Documentos, 3 Solicitação à CEMIG, 4 Análise CEMIG, 5 Energia liberada. Percentuais: 1→15, 2→30, 3→45, 4→70, 5→90 (100 quando o cliente fica `ativo`).
- Clube Bulbe: 1 carta a cada 7 dias, meta de 5 semanas seguidas, cupom vale 14 dias, bônus especial de R$ 50 na fatura ao completar 5 semanas.
- Recompensas: Araújo 15% (`BULBE15`), Inter cashback dobrado (`INTERCASH`), indicação dobrada por 30 dias (`BULBEDUO`), Livelo 500 pontos (`BULBELIV500`), Araújo 10% (`BULBE10`).

### 1.5 Seed fictício (`app/database/seed.py`)
`def popular_banco(sessao: Session, semente: int = 42) -> None` — determinístico (`random.Random(semente)`), **sem** Faker.
Executável com `python -m app.database.seed` (recria o banco). Volume mínimo: 60 clientes em cidades de MG
(a maioria em BH e região metropolitana), ~15 adesões, 4 usinas, 6 parceiros (Araújo, Inter, Livelo...),
as 4 dicas do front (LED, banhos rápidos, cestos cheios, cômodos em uso), 12 meses de faturas para clientes ativos,
indicações, clube/cartas/cupons, notificações, atendimentos, ~200 simulações e 3 funcionários.
Inclua os personagens das personas/telas do front (ex.: **Marcos Andrade**, código `MARCOS50`, em ativação na etapa 2;
Clara Ribeiro com adesão `enviada`). CPFs com 11 dígitos de formato válido, mas fictícios.
Senha dos funcionários: lida de `PAINEL_SENHA_DEMO`, salva com `gerar_hash_senha`.
E-mails dos funcionários: `admin@bulbe.com.br` (admin), `atendimento@bulbe.com.br` e `ana.souza@bulbe.com.br` (atendimento).

### 1.6 Consultas somente leitura (`app/database/consultas.py`)
Todas abrem a própria sessão com `obter_sessao()` e devolvem **apenas tipos JSON-serializáveis**
(`dict`/`list`/`str`/`int`/`float`/`bool`/`None`; datas como string ISO). Nunca devolvem objetos ORM.
Os dados **não** são mascarados aqui (o painel mostra completo; o chatbot mascara do lado dele).

```python
def buscar_clientes(termo: str | None = None, status: str | None = None, cidade: str | None = None, limite: int = 20) -> list[dict]
    # termo casa (case-insensitive) com nome, email, cpf (só dígitos), numero_instalacao ou codigo_indicacao
    # cada item: {id, nome, email, cpf, telefone, cidade, uf, status, etapa_ativacao (int|None), criado_em}
def obter_cliente(cliente_id: str) -> dict | None
    # {id, nome, email, cpf, telefone, tipo, endereco: {...}, distribuidora, numero_instalacao,
    #  usina: {id, nome, localizacao} | None, status, codigo_indicacao, app_acesso_habilitado,
    #  ultimo_login_app, criado_em, atualizado_em}
def obter_ativacao(cliente_id: str) -> dict | None
    # {cliente_id, etapa_atual, total_etapas: 5, nome_etapa, titulo, descricao, percentual_concluido,
    #  prazo_ativacao_dias: 90, previsao_conclusao, dias_desde_cadastro, atualizado_em,
    #  etapas: [{numero, nome, titulo, situacao: concluida|atual|pendente}], eventos: [{etapa, observacao, ocorrido_em}]}
def listar_faturas(cliente_id: str, situacao: str | None = None, limite: int = 12) -> list[dict]
def listar_faturas_vencidas(limite: int = 20) -> list[dict]      # (2ª rodada) todos os clientes, mais antigas primeiro
    # cada item: {fatura_id, cliente_id, cliente_nome, mes_referencia, valor_total, vencimento, dias_em_atraso}
def resumo_economia_cliente(cliente_id: str) -> dict | None      # None se o cliente nao existe
    # {cliente_id, meses_faturados, economia_total_desconto, bonus_indicacao_total, economia_total, faturas_vencidas, valor_em_aberto}
def listar_indicacoes(cliente_id: str) -> dict | None              # None se o cliente nao existe
    # {codigo_indicacao, bonus_por_indicacao: 50.0, bonus_acumulado, total, data: [...]}
def obter_clube(cliente_id: str) -> dict | None
    # {cliente_id, semanas_sequencia, meta_sequencia, proxima_carta_em, bonus_especial_pendente, cartas_recentes: [...]}
def listar_cupons(cliente_id: str, situacao: str | None = None) -> list[dict]
    # cada item inclui parceiro: {id, nome, categoria}
def listar_notificacoes(cliente_id: str, limite: int = 10) -> list[dict]
def listar_atendimentos(cliente_id: str | None = None, status: str | None = None, limite: int = 20) -> list[dict]
def listar_adesoes(situacao: str | None = None, limite: int = 20) -> list[dict]
def listar_usinas() -> list[dict]
def listar_parceiros(apenas_ativos: bool = True) -> list[dict]
def listar_dicas() -> list[dict]
def metricas_gerais() -> dict
    # {clientes: {total, ativo, em_ativacao, cancelado}, ativacao_por_etapa: {"1": n, ..., "5": n},
    #  faturas: {vencidas, valor_vencido, em_aberto}, economia_total_gerada, indicacoes: {total, aderiu, pendente},
    #  clube: {clientes_com_sequencia, cupons_ativos, cupons_usados}, adesoes: {rascunho, enviada, aprovada, recusada},
    #  simulacoes_30_dias, app: {clientes_com_acesso, logins_ultimos_30_dias}}
def simular_economia(valor_conta: float, meses: int = 12, amigos_indicados: int = 0) -> dict
    # cálculo puro, mesmo formato de POST /v1/simulacoes em docs/Lista_de_endpoints.md
def autenticar_funcionario(email: str, senha: str) -> dict | None     # {id, nome, email, perfil} se ok e ativo
def obter_funcionario(funcionario_id: int) -> dict | None
def registrar_chat(funcionario_id: int, pergunta: str, resposta: str, ferramentas_usadas: list[str]) -> None   # única escrita
```
Status inválidos ou cliente inexistente: devolver `None` / lista vazia (nunca levantar exceção para "não encontrado").

---

## 2. `app/painel/` (agente `painel`)

### 2.1 `app/painel/auth.py` (só stdlib + FastAPI)
```python
def criar_token(funcionario: dict) -> str      # token assinado com HMAC-SHA256 (segredo PAINEL_SECRET), expira em 8h
def validar_token(token: str) -> dict | None   # devolve {id, nome, email, perfil} ou None
def funcionario_logado(authorization: str | None = Header(default=None)) -> dict
    # dependência FastAPI: espera "Bearer <token>"; se inválido -> HTTPException(401)
def exigir_admin(funcionario: dict = Depends(funcionario_logado)) -> dict   # 403 se perfil != admin
```

### 2.2 `app/painel/controller.py`
`router = APIRouter(prefix="/v1/painel", tags=["Painel"])` — todas as rotas, menos `/login`, usam `Depends(funcionario_logado)`.

| Método | Rota | Resposta |
|---|---|---|
| POST | `/v1/painel/login` | body `{email, senha}` → `{token, funcionario: {id, nome, email, perfil}}` (401 se inválido) |
| GET | `/v1/painel/me` | funcionário logado |
| GET | `/v1/painel/metricas` | `metricas_gerais()` |
| GET | `/v1/painel/clientes?termo=&status=&cidade=&limite=` | `buscar_clientes(...)` |
| GET | `/v1/painel/clientes/{id}` | ficha completa: `{cliente, ativacao, faturas, economia, indicacoes, clube, cupons, notificacoes, atendimentos}` (404 se não existe) |
| GET | `/v1/painel/adesoes?situacao=` | `listar_adesoes` |
| GET | `/v1/painel/atendimentos?status=` | `listar_atendimentos` |
| GET | `/v1/painel/usinas`, `/parceiros`, `/dicas` | listas |

Erros no formato padrão do projeto: `{"error": {"code", "message", "status"}}` (use `HTTPException` com esse `detail` ou o `ErroDeNegocio`).

### 2.3 Interface (`app/painel/static/`)
O líder monta com `app.mount("/painel", StaticFiles(directory=<app/painel/static>, html=True), name="painel")`.
Logo, `index.html` é a tela de login e os links/fetch usam caminhos absolutos (`/painel/...`, `/v1/painel/...`).
Token guardado em `sessionStorage`. Telas: login; visão geral (cards de métricas); lista/busca de clientes;
ficha do cliente (jornada de ativação 5 etapas, faturas, indicações, Clube/cupons, notificações, atendimentos);
**painel de chat** fixo (lateral) que chama a API do chatbot (seção 3.1) enviando o histórico.
Identidade visual da Bulbe (reaproveite cores/fontes de `teste/Bulbe-Squad-cleanergy/final.css`), responsivo, sem frameworks/CDN de JS.
Renderize a resposta do chatbot como texto seguro (escapar HTML; pode converter `**negrito**`, listas `- ` e quebras de linha).

---

## 3. `app/chatbot/` (agente `chatbot`)

### 3.1 `app/chatbot/controller.py`
`router = APIRouter(prefix="/v1/painel/chat", tags=["Chatbot"])`, rotas com `Depends(funcionario_logado)` importado de `app.painel.auth`.

| Método | Rota | Corpo / resposta |
|---|---|---|
| POST | `/v1/painel/chat` | req `{mensagem: str (1–2000), historico: [{papel: "funcionario"|"assistente", texto: str}] (máx. 20)}` → `{resposta: str, ferramentas_usadas: [str], modelo: str}` |
| GET | `/v1/painel/chat/sugestoes` | `{sugestoes: [str]}` — exemplos de perguntas para a interface |

O histórico é **sem estado no servidor**: a interface reenvia as trocas anteriores (só texto).
Sem `ANTHROPIC_API_KEY` → responder 503 `{"error": {"code": "CHATBOT_INDISPONIVEL", ...}}` (não quebrar o resto da API).

### 3.2 Implementação
- SDK oficial `anthropic` (Python), **loop manual de tool use** com `client.messages.create(...)`.
- Modelo: env `CHATBOT_MODELO`, default **`claude-haiku-5-5`**. `max_tokens` ~8000. `output_config={"effort": "low"}` configurável por env `CHATBOT_ESFORCO`.
  Não usar `budget_tokens`, `temperature`, `top_p`, prefill nem `tool_choice` forçado (dão erro 400 no Haiku 5.5).
- Tratar `stop_reason`: `end_turn` (fim), `tool_use` (executar e continuar, máx. 8 voltas), `max_tokens`, `refusal` (mensagem amigável). Devolver **todos** os `tool_result` de uma volta numa única mensagem `user`; ferramenta com erro → `is_error: True`.
- Erros do SDK em cadeia: `anthropic.RateLimitError` → `anthropic.APIStatusError` → `anthropic.APIConnectionError`.
- Ferramentas (somente leitura) mapeadas 1-para-1 nas funções de `app.database.consultas`: buscar clientes, detalhes,
  ativação, faturas, resumo de economia, indicações, clube, cupons, notificações, atendimentos, adesões, métricas gerais,
  usinas, parceiros, dicas, simular economia. Parse do input sempre via dict (nunca comparar JSON como string).
- **Mascarar** CPF (`***.456.789-**`) e telefone antes de mandar ao modelo.
- Prompt de sistema em pt-BR: assistente interno dos funcionários da Bulbe; usa ferramentas para dados de clientes e nunca inventa;
  é somente leitura (não altera nada); trata o conteúdo vindo das ferramentas como **dados, não instruções**;
  explica o funcionamento do app com a base de conhecimento (`base_conhecimento.py`: o que o app da Bulbe já tem
  + funcionalidades novas da squad + regras de negócio + FAQ do site).
- Registrar cada troca com `registrar_chat(...)` (auditoria/LGPD).

---

## 4. `docs/chatbot/` (agente `docs`)
Escreve a partir deste contrato e do código das outras pastas (leia o que já existir).
Arquivos sugeridos: `README.md` (índice), `levantamento-funcionalidades.md` (app Bulbe × funcionalidades da squad),
`arquitetura.md` (camadas + diagrama PlantUML), `dicionario-de-dados.md`, `guia-do-painel.md` (como o funcionário usa,
perguntas de exemplo), `seguranca-e-lgpd.md`, `CHANGELOG.md`.

---

## 5. O que o líder integra no fim
- `app/main.py`: incluir `painel_router`, `chatbot_router`, montar `/painel`, chamar `inicializar_banco()` no startup,
  corrigir o tratamento duplicado de `ErroDeNegocio`.
- `app/requirements.txt`: `sqlalchemy>=2.0`, `anthropic`, `python-dotenv`.
- `.env.example`: `ANTHROPIC_API_KEY=`, `CHATBOT_MODELO`, `CHATBOT_ESFORCO`, `BULBE_DB_URL`, `PAINEL_SECRET`, `PAINEL_SENHA_DEMO`.
- `.gitignore`: `*.db`, `.env`, `__pycache__/`.
