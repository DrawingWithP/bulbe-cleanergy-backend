# app/chatbot — Assistente do Painel de Gestão (Claude Haiku 5.5)

Chatbot interno para funcionários da Bulbe perguntarem sobre **clientes** (dados do banco fictício)
e sobre o **funcionamento do app**. Usa o SDK oficial `anthropic` com **loop manual de tool use**.
É **somente leitura**: as ferramentas só chamam as consultas de `app.database.consultas`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `config.py` | Variáveis de ambiente (`ANTHROPIC_API_KEY`, `CHATBOT_MODELO`, `CHATBOT_ESFORCO`, `CHATBOT_TIMEOUT`); carrega `.env` se `python-dotenv` estiver instalado. |
| `base_conhecimento.py` | Texto sobre a Bulbe, regras de negócio, CEMIG × Bulbe, FAQ e funcionalidades marcadas como **existente** ou **novo (squad Cleanergy)**. |
| `prompts.py` | Prompt de sistema (instruções + base de conhecimento) e contexto dinâmico (funcionário + data). |
| `ferramentas.py` | `TOOLS` (17 ferramentas com JSON Schema: as 16 consultas da seção 1.6 + `listar_faturas_vencidas`) e `executar_ferramenta(nome, entrada) -> (texto, is_error)`: valida, chama a consulta, mascara CPF/telefone e serializa em JSON. |
| `servico.py` | `ChatbotService.responder(...)` — loop de tool use, tratamento de `stop_reason` e de erros; `chatbot_service` (instância única). |
| `controller.py` | `router` com `POST /v1/painel/chat` e `GET /v1/painel/chat/sugestoes`. |

## Rotas

| Método | Rota | Corpo / resposta |
|---|---|---|
| POST | `/v1/painel/chat` | `{mensagem (1–2000), historico: [{papel: "funcionario"\|"assistente", texto}] (máx. 20)}` → `{resposta, ferramentas_usadas, modelo}` |
| GET | `/v1/painel/chat/sugestoes` | `{sugestoes: [str]}` |

Ambas exigem `Authorization: Bearer <token>` (dependência `funcionario_logado` de `app.painel.auth`).
O histórico é **sem estado no servidor**: a interface reenvia as trocas anteriores (só texto).

## Fluxo de tool use

```
Funcionário ──POST /v1/painel/chat──▶ controller ──▶ ChatbotService.responder
                                                        │
  system = [prompt fixo (cache_control: ephemeral), contexto do funcionário + data]
  messages = histórico convertido (funcionario→user, assistente→assistant) + pergunta
                                                        │
        ┌──────────────── loop (máx. 8 voltas) ─────────┘
        ▼
  client.messages.create(model, max_tokens=8000, system, tools=TOOLS, messages,
                         output_config={"effort": CHATBOT_ESFORCO})
        │
        ├─ stop_reason == "tool_use"  → anexa {"role":"assistant","content": response.content};
        │                               executa TODOS os blocos tool_use (executar_ferramenta);
        │                               devolve TODOS os tool_result numa única mensagem "user"
        │                               (is_error=True para ferramenta desconhecida/entrada inválida/exceção); continua
        ├─ stop_reason == "pause_turn" → anexa o conteúdo do assistente e chama de novo
        ├─ stop_reason == "end_turn"   → texto final = blocos type=="text" concatenados
        ├─ stop_reason == "max_tokens" → texto parcial + aviso de resposta interrompida
        └─ stop_reason == "refusal"    → mensagem amigável
                                                        │
  registrar_chat(funcionario_id, pergunta, resposta, ferramentas_usadas)  (auditoria/LGPD)
                                                        ▼
                         {resposta, ferramentas_usadas, modelo}
```

Detalhes:
- `block.input` já vem como `dict`; a validação converte tipos (ex.: `"12"` → `12`, `"320,50"` → `320.5`),
  confere enums/limites e ignora parâmetros desconhecidos. Nunca se compara JSON como string.
- Resultados das ferramentas passam por `mascarar_dados`: CPF vira `***.456.789-**`, telefone vira
  `(31) *****-1234` (também em campos de contato e CPFs/telefones escritos em textos livres).
- Resultado vazio não é erro: a ferramenta responde "Nenhum registro encontrado..." para o modelo sugerir refinar a busca.
  Isso cobre `None` para cliente inexistente (inclusive `resumo_economia_cliente` e `listar_indicacoes`).
- `ValueError` levantado pela consulta (ex.: `simular_economia` com valor ≤ 0 ou meses fora de 1..60) vira
  `tool_result` com `is_error: True` e a mensagem em português da consulta; outras exceções viram erro genérico logado.
- `listar_faturas_vencidas` responde "quais clientes têm fatura vencida?" (todos os clientes, da mais antiga para a mais recente).
- O prompt instrui o modelo a tratar o conteúdo das ferramentas como **dados, não instruções** (proteção contra prompt injection
  vinda, por exemplo, da descrição de um atendimento).
- No Haiku 5.5 **não** usamos `budget_tokens`, `temperature`/`top_p`/`top_k`, prefill de assistente nem `tool_choice` forçado (dão 400).

## Erros

| Situação | HTTP | `code` |
|---|---|---|
| Sem `ANTHROPIC_API_KEY` ou SDK `anthropic` não instalado | 503 | `CHATBOT_INDISPONIVEL` |
| Chave recusada (401/403) ou API sobrecarregada (500/503/529) | 503 | `CHATBOT_INDISPONIVEL` |
| `anthropic.RateLimitError` | 429 | `CHATBOT_LIMITE_REQUISICOES` |
| Outro `anthropic.APIStatusError` | 502 | `CHATBOT_ERRO_API` |
| `anthropic.APIConnectionError` (inclui timeout) | 503 | `CHATBOT_SEM_CONEXAO` |

Os erros são `ErroDeNegocio` (de `app/erros.py`) e saem no formato
`{"error": {"code", "message", "status"}}` pelo handler registrado em `app/main.py`.

## Como configurar a chave

1. Gere uma chave em <https://console.anthropic.com/> (menu *API Keys*).
2. Na raiz do projeto, crie um arquivo `.env` (não versionado) com:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   CHATBOT_MODELO=claude-haiku-5-5   # opcional
   CHATBOT_ESFORCO=high              # opcional: low | medium | high | xhigh | max
   CHATBOT_TIMEOUT=60                # opcional, em segundos
   ```
   Ou exporte as variáveis no terminal (PowerShell: `$env:ANTHROPIC_API_KEY = "sk-ant-..."`).
3. Dependências (instaladas pelo líder via `requirements.txt`): `anthropic`, `python-dotenv` (opcional).

Sem a chave, o restante da API e do painel continuam funcionando; só o chat responde 503.
