# app/chatbot — Assistente do Painel de Gestão (Claude Haiku 5.5)

Chatbot interno para funcionários da Bulbe perguntarem sobre **clientes** (dados do banco fictício),
sobre a **gestão da ativação** e sobre o **funcionamento do app**. Usa o SDK oficial `anthropic` (1.x)
com **loop manual de tool use**, respostas **síncronas ou em streaming (SSE)** e **histórico guardado no servidor**.
É **somente leitura**: as ferramentas só chamam as consultas de `app.database.consultas`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `config.py` | Variáveis de ambiente (chave, modelo, esforço, timeout, limite de mensagens por conversa) e **preços** usados no custo estimado. Carrega `.env` se `python-dotenv` estiver instalado. |
| `base_conhecimento.py` | Texto sobre a Bulbe, regras de negócio, CEMIG × Bulbe, FAQ e funcionalidades marcadas como **existente** ou **novo (squad Cleanergy)**. |
| `prompts.py` | Prompt de sistema **estático** (instruções + base de conhecimento) e a linha de contexto `[Contexto: hoje é …; funcionário: …]` colocada no início de cada pergunta. |
| `ferramentas.py` | `TOOLS` (19 ferramentas com JSON Schema e `eager_input_streaming`) e `executar_ferramenta(nome, entrada) -> (texto, is_error)`: valida, chama a consulta, mascara CPF/telefone e serializa em JSON. |
| `servico.py` | `ChatbotService`: `preparar` (valida e carrega/cria a conversa), `executar` (gerador de eventos, síncrono ou streaming), `responder` (modo síncrono), uso/custo, gravação e registro; `chatbot_service` (instância única). |
| `controller.py` | `router` com as rotas abaixo e a conversão dos eventos em Server-Sent Events. |
| `avaliacoes/casos.json` | 33 perguntas de avaliação com o que a resposta precisa conter e as ferramentas esperadas. |
| `avaliacoes/avaliar.py` | Roda os casos contra a **API real** (gasta créditos) e imprime acertos/erros, tokens e custo. |
| `PENDENCIAS.md` | Lacunas do contrato e decisões que dependem de outras pastas. |

## Rotas (todas com `Authorization: Bearer <token>`)

| Método | Rota | Corpo / resposta |
|---|---|---|
| POST | `/v1/painel/chat` | req `{mensagem (1–2000), conversa_id?: str\|null, historico?: [{papel, texto}] (máx. 20)}` → `{resposta, ferramentas_usadas, modelo, conversa_id, uso}` |
| POST | `/v1/painel/chat/stream` | mesmo corpo; resposta `text/event-stream` (uma linha `data: <json>` por evento, separadas por linha em branco) |
| GET | `/v1/painel/chat/conversas?limite=` | `{conversas: [{id, titulo, criado_em, atualizado_em, total_mensagens}]}` do funcionário logado (`limite` 1–100, padrão 20) |
| GET | `/v1/painel/chat/conversas/{id}` | `{id, titulo, mensagens: [{papel: "funcionario"\|"assistente", texto}]}` só com mensagens de texto visível; 404 se não for do funcionário |
| GET | `/v1/painel/chat/sugestoes` | `{sugestoes: [str]}` |

`uso` = `{input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, custo_estimado_usd}` — soma de **todas** as voltas da pergunta.

- **Com `conversa_id`**: o histórico vem do servidor e `historico` é ignorado.
- **Sem `conversa_id`**: cria uma conversa nova (título = início da pergunta, até 60 caracteres). Se vier `historico` de texto (formato da v1),
  ele é convertido como antes e gravado na conversa nova junto com a troca atual — a v1 continua funcionando.

### Eventos do stream

```
data: {"tipo": "inicio", "conversa_id": "…"}
data: {"tipo": "ferramenta", "nome": "buscar_clientes"}     ← quando o modelo começa a chamar uma ferramenta
data: {"tipo": "texto", "delta": "O Marcos está…"}          ← pedaços da resposta, em ordem
data: {"tipo": "fim", "resposta": "<texto completo>", "ferramentas_usadas": [...], "modelo": "…", "conversa_id": "…", "uso": {...}}
data: {"tipo": "erro", "error": {"code", "message", "status"}}   ← encerra o stream
```

- A rota responde com `Cache-Control: no-cache` e `X-Accel-Buffering: no` (sem buffer em proxy).
- Problemas detectados **antes** de começar (sem chave da API, conversa inexistente/de outro funcionário, conversa longa demais)
  respondem com o **status HTTP normal** em JSON — a interface pode cair para o `POST /v1/painel/chat`.
- Erros **durante** o stream (429, 5xx, conexão, erro inesperado) viram o evento `erro`, sem quebrar a conexão.
- O texto concatenado dos `delta` é igual ao `resposta` do `fim`, exceto em recusa (o `fim` traz a mensagem de recusa):
  a interface deve usar o `resposta` do `fim` como texto definitivo.
- Entre o texto de voltas diferentes (antes e depois de uma consulta) vem um `delta` `"\n\n"`.

## Histórico no servidor e "preserved thinking"

O Claude Haiku 5.5 devolve blocos `thinking` cuja assinatura vale só para a conversa que os gerou: se algo antes deles
mudar (`system`, `tools` ou mensagens anteriores), a API recusa o histórico. Por isso:

1. Cada mensagem enviada/recebida é gravada (`adicionar_mensagens`) com o **conteúdo exato** da API:
   `response.content` serializado com `bloco.to_dict(mode="json")`, inclusive blocos `thinking` com texto vazio.
   Na pergunta seguinte, `obter_conversa` devolve esse conteúdo e ele é reenviado **igual**.
2. O histórico é **só de acréscimo**: nada é editado, reordenado ou removido.
3. O `system` é **idêntico byte a byte** em toda requisição (sem data nem funcionário) e o `tools` é o mesmo nas rotas síncrona
   e de stream. A data de hoje e o funcionário vão no início do texto de cada nova pergunta:
   `[Contexto: hoje é 18/10/2026; funcionário: Ana Souza (atendimento)]` + linha em branco + pergunta.
   O texto **visível** gravado (`texto`) é só a pergunta, sem essa linha.
4. O turno inteiro (pergunta, voltas de ferramenta e resposta) só é gravado **quando termina**; se a API falhar no meio,
   nada é gravado e o histórico continua consistente.
5. Se uma resposta for cortada (`max_tokens`/recusa) no meio de um `tool_use`, a ferramenta **não** roda; na pergunta seguinte
   o servidor manda antes o `tool_result` de erro correspondente (acréscimo, nunca edição).
6. Se a API ainda assim recusar o raciocínio preservado (400 de assinatura — por exemplo, após mudar o prompt numa nova versão),
   a pergunta é reenviada **uma vez sem os blocos thinking**; o histórico gravado não é alterado.
7. O texto visível de cada troca fica na mensagem final do assistente (as intermediárias têm `texto` vazio), então
   `GET /conversas/{id}` mostra uma pergunta e uma resposta por troca.

Uma conversa aceita até `CHATBOT_MAX_MENSAGENS_CONVERSA` mensagens da API (padrão 200); acima disso responde
409 `CONVERSA_MUITO_LONGA` (cortar o início invalidaria o raciocínio preservado — abra uma nova conversa).

## Fluxo de tool use

```
Funcionário ──POST /chat ou /chat/stream──▶ controller ──▶ ChatbotService.preparar (chave, conversa)
                                                        ──▶ ChatbotService.executar (gerador de eventos)
  system   = [prompt fixo (cache_control: ephemeral)]                       ← idêntico sempre
  messages = histórico gravado (igual) + "[Contexto: …]\n\n<pergunta>"
        ┌──────────────── loop (máx. 8 voltas) ─────────────────┐
        ▼                                                         │
  síncrono:  client.messages.create(...)                          │
  streaming: client.messages.stream(...) → content_block_start/   │
             content_block_delta → eventos ferramenta/texto;      │
             stream.get_final_message()                           │
  (model, max_tokens=8000, tools=TOOLS, output_config={"effort"}, │
   cache_control={"type":"ephemeral"} para o histórico)           │
        │                                                         │
        ├─ "tool_use"  → valida e executa TODOS os tool_use; TODOS os tool_result numa mensagem "user" ─┘
        ├─ "pause_turn"→ reenvia para continuar
        ├─ "end_turn"  → resposta = texto de todas as voltas
        ├─ "max_tokens"→ texto parcial + aviso (tool_use cortado não roda)
        └─ "refusal"   → mensagem amigável
                                                        │
  adicionar_mensagens(conversa_id, turno)  +  registrar_chat(..., conversa_id, modelo, uso, duracao_ms)
                                                        ▼
                     evento "fim" / {resposta, ferramentas_usadas, modelo, conversa_id, uso}
```

Detalhes:
- **Streaming de ferramentas**: todas as ferramentas têm `eager_input_streaming: true` (a entrada chega aos poucos e a API deixa de
  validá-la). Por isso `validar_entrada` confere tipos, enums e limites de toda entrada antes de chamar a consulta, e o loop checa
  `max_tokens`/`refusal` antes de rodar qualquer ferramenta. JSON que o SDK não consegue ler repete a volta (no máx. 2 vezes).
  O campo é ignorado pela API nas chamadas síncronas; o mesmo `tools` é usado nos dois modos para não invalidar cache/raciocínio.
- `block.input` é sempre tratado como `dict` (ou texto JSON interpretado com `json.loads`); nunca se compara JSON como string.
- Resultados das ferramentas passam por `mascarar_dados`: CPF vira `***.456.789-**`, telefone vira `(31) *****-1234`.
- Resultado vazio não é erro ("Nenhum registro encontrado..."); `ValueError` da consulta e entrada inválida viram `is_error: True`.
- No Haiku 5.5 **não** usamos `budget_tokens`, `temperature`/`top_p`/`top_k`, prefill de assistente nem `tool_choice` forçado.
  O `thinking` não é enviado (adaptativo por padrão); o esforço vem de `CHATBOT_ESFORCO` (padrão `high`).

## Ferramentas novas (gestão)

| Ferramenta | Consulta | Uso |
|---|---|---|
| `listar_clientes_parados` | `listar_clientes_parados(etapa, dias_minimos, limite)` | gargalos: quem não avança de etapa há N dias (do mais parado ao menos parado; marca quem passou dos 90 dias) |
| `resumo_ativacoes` | `resumo_ativacoes()` | visão geral: por etapa, média de dias por etapa, atrasados, ativados em 30 dias, tempo médio |
| `buscar_clientes` (filtro novo `etapa` 1–5) | `buscar_clientes(..., etapa=)` | clientes de uma etapa |

As descrições de `listar_faturas`, `listar_faturas_vencidas`, `resumo_economia_cliente` e `metricas_gerais` citam os campos novos
(`bonus_clube`, `bonus_clube_total`, etapa "5" = ativados nos últimos 30 dias, `clube.bonus_pagos`).

## Uso e custo

`UsoAcumulado` soma o `usage` de todas as voltas (`input_tokens`, `output_tokens`, `cache_read_input_tokens`,
`cache_creation_input_tokens`) e estima o custo de cada chamada com os preços de `config.py`:

| Item | Padrão (Claude Haiku 5.5, prompt ≤ 100 mil tokens) | Variável |
|---|---|---|
| Entrada | US$ 0,10 / milhão | `CHATBOT_PRECO_ENTRADA_MTOK` |
| Saída | US$ 0,50 / milhão | `CHATBOT_PRECO_SAIDA_MTOK` |
| Leitura de cache | 0,1 × entrada | `CHATBOT_FATOR_CACHE_LEITURA` |
| Escrita de cache | 1,25 × entrada | `CHATBOT_FATOR_CACHE_ESCRITA` |
| Prompt longo (> 100 mil tokens numa chamada) | US$ 0,50 / US$ 2,50 por milhão | `CHATBOT_LIMITE_PROMPT_LONGO`, `CHATBOT_PRECO_ENTRADA_LONGO_MTOK`, `CHATBOT_PRECO_SAIDA_LONGO_MTOK` |

O valor é **estimado** (a fatura oficial é a do console da Anthropic) e vai para `registrar_chat(..., uso=..., duracao_ms=...)`.

## Erros

| Situação | HTTP | `code` |
|---|---|---|
| Sem `ANTHROPIC_API_KEY` ou SDK `anthropic` não instalado | 503 | `CHATBOT_INDISPONIVEL` |
| Chave recusada (401/403) ou API sobrecarregada (500/503/529) | 503 | `CHATBOT_INDISPONIVEL` |
| `anthropic.RateLimitError` | 429 | `CHATBOT_LIMITE_REQUISICOES` |
| Outro `anthropic.APIStatusError` | 502 | `CHATBOT_ERRO_API` |
| `anthropic.APIConnectionError` (inclui timeout) | 503 | `CHATBOT_SEM_CONEXAO` |
| `conversa_id` inexistente ou de outro funcionário | 404 | `CONVERSA_NAO_ENCONTRADA` |
| Falha ao ler a conversa no banco | 503 | `CHATBOT_HISTORICO_INDISPONIVEL` |
| Conversa acima do limite de mensagens | 409 | `CONVERSA_MUITO_LONGA` |
| Erro inesperado durante o stream (só no evento `erro`) | 500 | `CHATBOT_ERRO_INTERNO` |

Fora do stream os erros são `ErroDeNegocio` (de `app/erros.py`) e saem como `{"error": {"code", "message", "status"}}`
pelo handler de `app/main.py`; no stream, viram `{"tipo": "erro", "error": {...}}`.

## Avaliações

```
python -m app.chatbot.avaliacoes.avaliar                       # todos os casos (gasta créditos!)
python -m app.chatbot.avaliacoes.avaliar --ids data-de-hoje,simulacao-320-12-2 --detalhes
python -m app.chatbot.avaliacoes.avaliar --categoria gestao-ativacao --saida resultado.json
```

Cada caso de `casos.json` tem `pergunta` e critérios: `deve_conter`, `qualquer_de` (grupos), `nao_deve_conter`,
`ferramentas_esperadas`, `ferramentas_qualquer_de` e `sem_ferramentas` (comparação sem maiúsculas/acentos; `{hoje}` vira a data
de hoje). O script usa o mesmo fluxo da rota síncrona, **sem gravar** conversa nem registro, imprime acertos/erros por caso,
tokens e custo estimado, e sai com código 0 (tudo certo), 1 (alguma falha) ou 2 (não rodou). Os valores esperados valem para o
seed com semente 42.

## Testes com cliente simulado

`ChatbotService(cliente=...)` ou `chatbot_service.definir_cliente(fake)` injeta um cliente falso (objeto com `messages.create`
e `messages.stream`); `definir_cliente(None)` volta ao SDK. **Atenção:** `config.py` e `app/main.py` carregam o `.env`
com `load_dotenv(override=False)`; remover `ANTHROPIC_API_KEY` com `os.environ.pop` **não basta** (o `.env` a recoloca).
Nos testes, defina `ANTHROPIC_API_KEY=""` antes de importar o `app`, injete o cliente falso ou substitua `config.obter_chave_api`.

## Como configurar a chave

1. Gere uma chave em <https://console.anthropic.com/> (menu *API Keys*).
2. Na raiz do projeto, crie um arquivo `.env` (não versionado) com:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   CHATBOT_MODELO=claude-haiku-5-5   # opcional
   CHATBOT_ESFORCO=high              # opcional: low | medium | high | xhigh | max
   CHATBOT_TIMEOUT=60                # opcional, em segundos
   CHATBOT_MAX_MENSAGENS_CONVERSA=200  # opcional
   ```
   Ou exporte as variáveis no terminal (PowerShell: `$env:ANTHROPIC_API_KEY = "sk-ant-..."`).
3. Dependências (instaladas via `requirements.txt`): `anthropic` 1.x, `python-dotenv` (opcional).

Sem a chave, o restante da API e do painel continuam funcionando; só o chat responde 503.
