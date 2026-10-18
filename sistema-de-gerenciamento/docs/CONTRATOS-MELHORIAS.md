# Contrato das melhorias (2ª versão do sistema de gerenciamento)

Branch: `feat/python-melhorias-sistema`. Complementa o [CONTRATOS.md](CONTRATOS.md): tudo que está lá continua valendo,
salvo quando este documento diz o contrário. **Somente leitura para quem implementa.**

Todos os caminhos abaixo são relativos à pasta `sistema-de-gerenciamento/`.

## Regras para quem implementa

1. Edite **somente** a sua pasta (tabela abaixo). Ler qualquer arquivo é permitido.
2. Pode instalar dependências **somente** no `.venv` do sistema (`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`)
   e rodar `pytest` e `python -m py_compile`. **Não** suba o servidor, **não** rode o seed sobre o banco real
   (`app/database/bulbe_ficticio.db`) e **não** chame a API da Anthropic de verdade.
3. **Não** use git (nada de add/commit/push/checkout/branch/stash). Só o integrador commita.
4. Registre o que fez no `CHANGELOG.md` da sua pasta, em uma seção "Melhorias (v2)". Escreva de forma impessoal
   (o que mudou e por quê), sem atribuir o trabalho a "agentes" ou "líder".
5. Dúvidas ou lacunas do contrato: **não** edite a pasta de outra pessoa; anote em `PENDENCIAS.md` na sua pasta
   e siga com a suposição mais compatível com este contrato.
6. Mantenha **compatibilidade**: nenhuma função ou rota existente muda de assinatura de forma incompatível,
   a não ser onde este contrato manda explicitamente.
7. Código e comentários em português, no estilo do projeto, com type hints. Dados 100% fictícios.

| Responsável | Pasta | Entrega |
|---|---|---|
| `db` | `app/database/` | Novas tabelas e colunas, consultas paginadas e de gestão, auditoria, conversas do chat, uso/custo, retenção, bônus do Clube |
| `chatbot` | `app/chatbot/` | Streaming, histórico no servidor, novas ferramentas, registro de uso/custo, avaliações |
| `painel` | `app/painel/` | Limite de tentativas e alerta por e-mail, rotas de admin, auditoria, paginação, telas novas, chat com streaming e conversas |
| `testes` | `tests/` | Suíte `pytest` de todo o sistema |
| `docs` | `docs/` (exceto os arquivos `CONTRATOS*.md`) | Documentação da v2 |
| integrador | `app/main.py`, `app/erros.py`, `requirements*.txt`, `pytest.ini`, `.env.example`, `README.md`, contratos | Integração e commits |

---

## 1. Banco (`app/database/`)

### 1.1 Mudanças de esquema
O banco local será **recriado** com `python -m app.database.seed` depois da integração (não há migração).

| Tabela | Mudança |
|---|---|
| `faturas` | nova coluna `bonus_clube` (float, default 0). O seed aplica R$ 50 na fatura seguinte de quem completou 5 semanas do Clube; `valor_total` desconta o bônus (sem ficar negativo). |
| `chat_historico` | novas colunas opcionais: `conversa_id` (FK `chat_conversas`, null), `modelo`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` (int, default 0), `custo_estimado_usd` (float, default 0), `duracao_ms` (int, null) |
| `chat_conversas` (nova) | `id` UUID, `funcionario_id` FK, `titulo` (até 120 caracteres), `criado_em`, `atualizado_em` |
| `chat_mensagens` (nova) | `id` int, `conversa_id` FK, `ordem` int (único por conversa), `papel` (`user`/`assistant`), `conteudo_json` (texto JSON com o conteúdo **exato** enviado/recebido da API), `texto` (texto visível para a interface, pode ser vazio), `criado_em` |
| `auditoria_acessos` (nova) | `id` int, `funcionario_id` (FK, null p/ login falho de e-mail inexistente), `email_informado` (null), `acao` (`login_ok`/`login_falha`/`login_bloqueado`/`alerta_email`/`ver_ficha`/`ver_auditoria`/`expurgo`), `recurso_tipo` (null), `recurso_id` (null), `ip` (null), `detalhe` (null, até 500 caracteres), `criado_em` |

O seed também gera: ~120 registros de `auditoria_acessos` plausíveis e algumas conversas de exemplo **não** (o chat começa vazio).

### 1.2 Consultas novas ou alteradas (`app/database/consultas.py`)
Todas continuam devolvendo só tipos JSON-serializáveis. Formato paginado padrão:
`{"data": [...], "pagina": int, "por_pagina": int, "total": int, "total_paginas": int}` (`por_pagina` de 1 a 100).

```python
# --- clientes e ativação ---
def buscar_clientes(termo=None, status=None, cidade=None, limite=20, etapa: int | None = None) -> list[dict]   # novo filtro opcional
def buscar_clientes_paginado(termo: str | None = None, status: str | None = None, cidade: str | None = None,
                             etapa: int | None = None, pagina: int = 1, por_pagina: int = 20) -> dict
def listar_clientes_parados(etapa: int | None = None, dias_minimos: int = 30, limite: int = 50) -> list[dict]
    # clientes em_ativacao sem avançar de etapa há >= dias_minimos (desde o último evento/atualização da ativação),
    # do mais parado ao menos parado. Item: {cliente_id, nome, cidade, etapa_atual, nome_etapa, dias_na_etapa,
    #  dias_desde_cadastro, previsao_conclusao, atrasado (bool: passou dos 90 dias do cadastro)}
def resumo_ativacoes() -> dict
    # {em_ativacao, por_etapa: {"1".."4": n}, dias_medios_na_etapa: {"1".."4": float}, atrasados_90_dias: int,
    #  ativados_30_dias: int, tempo_medio_ativacao_dias: float | None}
def metricas_gerais() -> dict
    # igual à v1, mas ativacao_por_etapa["5"] = clientes ATIVADOS nos últimos 30 dias, e nova chave
    # ativacao_etapa5_descricao = "ativados nos últimos 30 dias"; nova chave clube["bonus_pagos"] (soma de bonus_clube)

# --- paginadas ---
def listar_adesoes_paginado(situacao: str | None = None, pagina: int = 1, por_pagina: int = 20) -> dict
def listar_atendimentos_paginado(cliente_id: str | None = None, status: str | None = None,
                                 pagina: int = 1, por_pagina: int = 20) -> dict   # itens com cliente_nome

# --- faturas / economia ---
# listar_faturas e listar_faturas_vencidas passam a incluir "bonus_clube" em cada item;
# resumo_economia_cliente ganha "bonus_clube_total" (e economia_total soma esse bônus)

# --- chat: conversas no servidor ---
def criar_conversa(funcionario_id: int, titulo: str) -> dict            # {id, titulo, criado_em, atualizado_em}
def listar_conversas(funcionario_id: int, limite: int = 20) -> list[dict]   # mais recentes primeiro; + total_mensagens
def obter_conversa(conversa_id: str, funcionario_id: int) -> dict | None
    # None se não existe OU se pertence a outro funcionário.
    # {id, titulo, criado_em, atualizado_em, mensagens: [{ordem, papel, conteudo, texto, criado_em}]}
    # "conteudo" = json.loads(conteudo_json) (lista de blocos ou string), pronto para reenviar à API
def adicionar_mensagens(conversa_id: str, mensagens: list[dict]) -> None
    # cada item {papel, conteudo (list|str), texto}; grava em ordem crescente, nunca altera mensagens antigas
    # (o histórico é só de acréscimo) e atualiza atualizado_em da conversa
def registrar_chat(funcionario_id: int, pergunta: str, resposta: str, ferramentas_usadas: list[str], *,
                   conversa_id: str | None = None, modelo: str | None = None, uso: dict | None = None,
                   duracao_ms: int | None = None) -> None
    # uso = {input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, custo_estimado_usd}
def metricas_uso_chatbot(dias: int = 30) -> dict
    # {periodo_dias, perguntas, conversas, funcionarios_ativos, input_tokens, output_tokens, cache_read_tokens,
    #  custo_estimado_usd, custo_medio_por_pergunta_usd, duracao_media_ms,
    #  por_funcionario: [{funcionario_id, nome, perguntas, custo_estimado_usd}],
    #  ferramentas_mais_usadas: [{nome, usos}], por_dia: [{data, perguntas, custo_estimado_usd}]}

# --- auditoria e retenção ---
def registrar_auditoria(acao: str, *, funcionario_id: int | None = None, email_informado: str | None = None,
                        recurso_tipo: str | None = None, recurso_id: str | None = None,
                        ip: str | None = None, detalhe: str | None = None) -> None
def listar_auditoria(funcionario_id: int | None = None, acao: str | None = None,
                     pagina: int = 1, por_pagina: int = 50) -> dict   # itens com funcionario_nome
def contar_falhas_login(email: str, minutos: int = 15) -> int        # login_falha recentes daquele e-mail (case-insensitive)
def expurgar_dados_antigos(dias_chat: int = 180, dias_auditoria: int = 730) -> dict
    # apaga chat_historico, chat_mensagens e chat_conversas mais antigos que dias_chat (pela atualização da conversa)
    # e auditoria_acessos mais antiga que dias_auditoria. Devolve {chat_historico, chat_conversas, chat_mensagens, auditoria}
```

---

## 2. Chatbot (`app/chatbot/`)

### 2.1 Rotas (todas com `Depends(funcionario_logado)`)

| Método | Rota | Corpo / resposta |
|---|---|---|
| POST | `/v1/painel/chat` | req `{mensagem, conversa_id?: str|null, historico?: [...]}`. Com `conversa_id`, o histórico vem do servidor e `historico` é ignorado; sem ele, cria uma conversa nova (título = início da pergunta, até 60 caracteres). Resp `{resposta, ferramentas_usadas, modelo, conversa_id, uso: {input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, custo_estimado_usd}}` |
| POST | `/v1/painel/chat/stream` | mesmo corpo; resposta `text/event-stream` (SSE), uma linha `data: <json>` por evento, separadas por linha em branco |
| GET | `/v1/painel/chat/conversas` | `{conversas: [{id, titulo, criado_em, atualizado_em, total_mensagens}]}` do funcionário logado |
| GET | `/v1/painel/chat/conversas/{id}` | `{id, titulo, mensagens: [{papel: "funcionario"|"assistente", texto}]}` só com as mensagens que têm texto visível; 404 se não for do funcionário |
| GET | `/v1/painel/chat/sugestoes` | igual à v1 |

Eventos do stream (campo `tipo`):
- `{"tipo": "inicio", "conversa_id": "..."}`
- `{"tipo": "texto", "delta": "..."}` (pedaços da resposta, em ordem)
- `{"tipo": "ferramenta", "nome": "buscar_clientes"}` (quando o modelo chama uma ferramenta)
- `{"tipo": "fim", "resposta": "<texto completo>", "ferramentas_usadas": [...], "modelo": "...", "conversa_id": "...", "uso": {...}}`
- `{"tipo": "erro", "error": {"code", "message", "status"}}` (encerra o stream)

### 2.2 Implementação
- Streaming com `client.messages.stream(...)` do SDK oficial `anthropic` 1.x (confira a API na skill `claude-api`, Python).
  Ferramentas do cliente com `eager_input_streaming: true` e validação da entrada antes de executar.
- **Histórico no servidor e "preserved thinking"**: guarde o conteúdo **exato** de cada mensagem da API
  (`response.content` serializado com `bloco.to_dict()` / `model_dump` sem alterar nada, incluindo blocos `thinking`)
  e reenvie igual. O histórico é **só de acréscimo**: nunca edite, reordene ou remova mensagens antigas.
  O prompt de sistema tem de ser **idêntico byte a byte** em toda a conversa: a data de hoje e o funcionário logado
  saem do `system` e passam a ir no início do texto de cada nova pergunta do usuário (ex.: `[Contexto: hoje é 18/10/2026; funcionário: Ana (atendimento)]`).
- Conversas antigas sem `conversa_id` (corpo com `historico` de texto) continuam funcionando como na v1.
- Novas ferramentas: `listar_clientes_parados`, `resumo_ativacoes`, filtro `etapa` em `buscar_clientes`;
  `bonus_clube` passa a aparecer nas faturas.
- **Uso e custo**: somar `response.usage` de todas as voltas (input, output, cache read, cache creation) e estimar o custo
  em USD com preços configuráveis em `config.py` (Claude Haiku 5.5: US$ 0,10 por milhão de tokens de entrada e
  US$ 0,50 por milhão de saída; acima de 100 mil tokens de entrada por chamada, US$ 0,50 e US$ 2,50; leitura de cache 0,1× a entrada; escrita de cache 1,25× a entrada), gravando com `registrar_chat(...)`.
- **Avaliações**: `app/chatbot/avaliacoes/casos.json` (≥ 25 perguntas com o que a resposta precisa conter/as ferramentas esperadas)
  e `app/chatbot/avaliacoes/avaliar.py` (roda os casos contra a API real e imprime acertos/erros e o custo). **Não execute**
  o `avaliar.py` (gasta créditos); só garanta que compila. O integrador roda.
- Continua valendo da v1: Haiku 5.5 (`claude-haiku-5-5`), esforço por `CHATBOT_ESFORCO` (padrão `high`), loop até 8 voltas,
  mascaramento de CPF/telefone, somente leitura, sem `temperature`/`budget_tokens`/prefill/`tool_choice` forçado.

---

## 3. Painel (`app/painel/`)

### 3.1 Segurança do login
- **Bloqueio**: depois de 5 falhas do mesmo e-mail em 15 minutos (`contar_falhas_login`), o login responde **429**
  `LOGIN_BLOQUEADO` (com `Retry-After`) até a janela passar, mesmo com a senha certa.
- **Alerta por e-mail**: quando um e-mail passar de **3 falhas em 15 minutos** (ou seja, na 4ª falha), enviar **um** e-mail de alerta
  para o endereço configurado em `ALERTA_LOGIN_EMAIL` (no máximo 1 alerta por e-mail a cada 15 minutos). O e-mail
  diz o e-mail tentado, quantas falhas, o IP e o horário; nunca inclui a senha digitada.
  - Módulo `app/painel/alertas.py`, só com a biblioteca padrão (`smtplib` + `email.message`), configurado por
    `SMTP_HOST`, `SMTP_PORTA` (587), `SMTP_USUARIO`, `SMTP_SENHA`, `SMTP_REMETENTE`, `SMTP_TLS` (true), `ALERTA_LOGIN_EMAIL`,
    `LOGIN_ALERTA_APOS_FALHAS` (3), `LOGIN_BLOQUEIO_APOS_FALHAS` (5), `LOGIN_JANELA_MINUTOS` (15).
  - Envio em segundo plano (`BackgroundTasks` do FastAPI), sem atrasar a resposta do login.
  - Sem SMTP configurado ou com erro de envio: não quebra o login; registra aviso no log e a ação `alerta_email` na auditoria com o detalhe do problema.
- Auditoria: `login_ok`, `login_falha`, `login_bloqueado`, `alerta_email` e `ver_ficha` gravados com `registrar_auditoria` (com IP do `Request`).

### 3.2 Rotas (`app/painel/controller.py`)
| Método | Rota | Mudança |
|---|---|---|
| POST | `/v1/painel/login` | bloqueio + alerta + auditoria (3.1) |
| GET | `/v1/painel/clientes?termo&status&cidade&etapa&pagina&por_pagina` | **passa a ser paginada** (formato paginado padrão) |
| GET | `/v1/painel/clientes/parados?etapa&dias_minimos&limite` | `listar_clientes_parados` (declarar antes de `/clientes/{id}`) |
| GET | `/v1/painel/clientes/{id}` | igual, e grava `ver_ficha` na auditoria |
| GET | `/v1/painel/ativacoes/resumo` | `resumo_ativacoes()` |
| GET | `/v1/painel/adesoes?situacao&pagina&por_pagina` | **paginada** |
| GET | `/v1/painel/atendimentos?status&pagina&por_pagina` | **paginada** |
| GET | `/v1/painel/auditoria?funcionario_id&acao&pagina&por_pagina` | **só admin** (`exigir_admin`); grava `ver_auditoria` |
| GET | `/v1/painel/uso-chatbot?dias` | **só admin**; `metricas_uso_chatbot` |
| POST | `/v1/painel/admin/expurgo` | **só admin**; roda `expurgar_dados_antigos` com `CHAT_RETENCAO_DIAS`/`AUDITORIA_RETENCAO_DIAS`; grava `expurgo` |
| GET | `/v1/painel/usinas`, `/parceiros`, `/dicas`, `/metricas`, `/me` | iguais |

### 3.3 Interface (`app/painel/static/`)
- Paginação real (anterior/próxima, "página X de Y", itens por página) em Clientes, Adesões, Atendimentos e Auditoria; filtro por etapa em Clientes.
- Telas novas no menu: **Ativações** (resumo + clientes parados, com filtro de etapa e dias), **Dicas**, **Usinas**, **Parceiros**;
  e, só para admin, **Auditoria** e **Uso do assistente** (perguntas, custo estimado, por funcionário, ferramentas mais usadas, por dia).
- Visão geral: a barra da etapa 5 mostra "Ativados (30 dias)"; card do Clube mostra os bônus pagos.
- Ficha: faturas mostram a coluna de bônus do Clube; economia mostra o total de bônus do Clube.
- Chat: usa `/v1/painel/chat/stream` com `fetch` + `ReadableStream` (o `EventSource` não aceita POST nem cabeçalho),
  mostra o texto chegando, as ferramentas sendo consultadas e o custo da resposta discretamente; guarda o `conversa_id`;
  botão "Nova conversa" e lista das conversas anteriores (reabrir uma conversa carrega `/conversas/{id}`).
  Se o stream falhar antes de começar, cai para o `POST /v1/painel/chat`.
- Login: mensagem clara para 429 ("Muitas tentativas. Tente de novo em N minutos.").

---

## 4. Testes (`tests/`)
- `pytest` + `fastapi.testclient.TestClient` (o integrador cria `requirements-dev.txt` e `pytest.ini`).
- `tests/conftest.py`: antes de importar `app`, apontar `BULBE_DB_URL` para um SQLite temporário (`tmp_path_factory`),
  definir `PAINEL_SECRET`, `PAINEL_SENHA_DEMO`, remover `ANTHROPIC_API_KEY` e SMTP; popular com `popular_banco`.
- Cobrir: consultas (formatos, filtros, paginação, parados, resumo, conversas só de acréscimo, auditoria, expurgo, bônus do Clube),
  segurança (hash, token adulterado/expirado, 401/403, bloqueio 429 na 6ª tentativa, alerta enviado uma vez na 4ª falha com SMTP simulado),
  rotas do painel (paginação, admin x atendimento, auditoria de `ver_ficha`), chatbot com cliente da Anthropic **simulado**
  (loop de ferramentas, mascaramento, erros 429/502/503, uso/custo, conversa persistida e reenviada igual, eventos do stream na ordem certa).
- Os outros módulos estão sendo escritos ao mesmo tempo: escreva contra este contrato e, no fim, rode a suíte e
  relate o que falhou e por quê (bug do código x teste errado), sem editar fora de `tests/`.

## 5. Documentação (`docs/`)
Atualizar `README.md`, `arquitetura.md` (streaming, conversas, auditoria, alerta), `dicionario-de-dados.md` (tabelas/colunas novas),
`guia-do-painel.md` (telas novas, variáveis novas do `.env` incluindo SMTP com senha de app do Gmail, como rodar os testes),
`seguranca-e-lgpd.md` (bloqueio, alerta, auditoria, retenção) e criar `testes.md`. Escrita impessoal, sem "agentes" ou "líder".
