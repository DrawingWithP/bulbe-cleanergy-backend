# CHANGELOG — app/chatbot (agente "chatbot")

## Melhorias (v2) — branch `feat/python-melhorias-sistema`

### Adicionado
- **Streaming (SSE)**: `POST /v1/painel/chat/stream` com `StreamingResponse` (`text/event-stream`, `Cache-Control: no-cache`,
  `X-Accel-Buffering: no`). Eventos `inicio`, `ferramenta`, `texto`, `fim` e `erro`, uma linha `data: <json>` por evento.
  Usa `client.messages.stream(...)` + `get_final_message()` do SDK `anthropic` 1.x. Erros durante o stream viram o evento
  `erro` (`{"code", "message", "status"}`) em vez de derrubar a conexão; erros detectados antes de começar (sem chave,
  conversa inexistente, conversa longa) respondem com o status HTTP normal, para a interface poder cair para o `POST /chat`.
- **Conversas no servidor**: `POST /v1/painel/chat` e `/stream` aceitam `conversa_id`; sem ele, criam uma conversa
  (título = início da pergunta, até 60 caracteres). Rotas `GET /v1/painel/chat/conversas` (com `limite` opcional 1–100) e
  `GET /v1/painel/chat/conversas/{id}` (só mensagens com texto visível; 404 se não for do funcionário).
- **Histórico exato e só de acréscimo** ("preserved thinking" do Claude Haiku 5.5): cada mensagem da API é gravada com
  `to_dict(mode="json")` (inclusive blocos `thinking`) e reenviada igual; o turno só é gravado quando termina.
- **Ferramentas novas**: `listar_clientes_parados` e `resumo_ativacoes`; filtro `etapa` (1–5) em `buscar_clientes`;
  descrições com `bonus_clube`, `bonus_clube_total`, etapa "5" = ativados em 30 dias e `bonus_pagos`. Total: 19 ferramentas.
- **Uso e custo**: soma de `usage` de todas as voltas (entrada, saída, leitura e escrita de cache) e custo estimado em USD
  com preços configuráveis em `config.py` (Haiku 5.5: US$ 0,10 / 0,50 por milhão; cache 0,1× e 1,25× a entrada; tabela de
  prompt longo acima de 100 mil tokens). Resposta e evento `fim` trazem `uso`; `registrar_chat(..., conversa_id=, modelo=,
  uso=, duracao_ms=)`.
- **Avaliações**: `avaliacoes/casos.json` (33 casos: dados de clientes, gestão da ativação, conhecimento, LGPD, limites,
  injeção de prompt, data de contexto) e `avaliacoes/avaliar.py` (roda contra a API real, imprime acertos/erros, tokens e
  custo; filtros `--ids`/`--categoria`, `--saida` em JSON). Não executado (gasta créditos).
- `PENDENCIAS.md` com as lacunas do contrato.

### Alterado
- **Prompt de sistema estático**: a data e o funcionário saíram do `system` e vão no início de cada nova pergunta
  (`[Contexto: hoje é DD/MM/AAAA; funcionário: Nome (perfil)]`), para o `system` ficar idêntico byte a byte em toda a
  conversa (cache e raciocínio preservado). `montar_contexto_dinamico` foi mantida por compatibilidade, sem uso.
- Prompt: seção "Contexto de cada pergunta", seção "Gestão da ativação e do Clube" (quando usar `resumo_ativacoes`,
  `listar_clientes_parados` e o filtro `etapa`; significado da etapa 5 e do `bonus_clube`) e "Histórico da conversa"
  ajustado para conversas salvas (com as consultas) e antigas (só texto).
- `TOOLS` com `eager_input_streaming: true` em todas as ferramentas, iguais nos modos síncrono e de stream (o campo é ignorado
  sem streaming). A validação local da entrada passou a aceitar também texto JSON (interpretado com `json.loads`).
- Cache: além do ponto no `system`, `cache_control` automático no nível da requisição para o histórico que cresce a cada volta.
- `resposta` passa a juntar o texto de todas as voltas (o mesmo texto mostrado no stream), separado por linha em branco.
- `ChatbotService.responder(mensagem, historico, funcionario, conversa_id=None)` mantém a assinatura da v1 e devolve também
  `conversa_id` e `uso`. Novos: `preparar`, `executar` (gerador de eventos), `responder_contexto`, `definir_cliente`
  (injeção de cliente falso), `listar_conversas`, `obter_conversa_visivel`.
- Sugestões do chat incluem perguntas de gestão da ativação.

### Decisões
- **Sem `conversa_id` + `historico` de texto (v1)**: o histórico é convertido como antes e gravado na conversa nova junto
  com a troca, para que as perguntas seguintes (com o `conversa_id` devolvido) reenviem exatamente o que foi enviado.
  A pergunta atual vai numa mensagem própria (a API junta mensagens seguidas do mesmo papel).
- **Resposta cortada no meio de um `tool_use`** (`max_tokens`/recusa): a ferramenta não roda (a entrada pode estar
  truncada); na próxima pergunta o `tool_result` de erro vai antes do texto, mantendo o histórico válido sem editá-lo.
- **400 de assinatura do `thinking`** (ex.: prompt mudou entre versões): a pergunta é reenviada uma vez sem os blocos
  `thinking`, sem alterar o histórico gravado.
- **Limite de mensagens por conversa** (`CHATBOT_MAX_MENSAGENS_CONVERSA`, padrão 200): acima dele, 409
  `CONVERSA_MUITO_LONGA`, porque cortar o início invalidaria o raciocínio preservado.
- O evento `ferramenta` sai no `content_block_start` do `tool_use` (antes de a entrada terminar de chegar).
- `registrar_chat` com a assinatura da v1 (sem os campos novos) ainda funciona: em `TypeError`, registra no formato antigo.
- Sem `thinking` explícito (o Haiku 5.5 usa pensamento adaptativo por padrão), sem `temperature`/`budget_tokens`/prefill/
  `tool_choice` forçado, como na v1.

### Validação
- `python -m py_compile` em todos os `.py` da pasta.
- Teste local com cliente Anthropic simulado (objetos reais do SDK para mensagens/eventos, sem rede e sem banco real):
  pergunta com 2 voltas de ferramenta (uso somado e custo), reenvio do histórico idêntico ao gravado numa segunda pergunta,
  `system`/`tools` idênticos em todas as chamadas, ordem dos eventos do stream, evento `erro` no meio do stream (429),
  503/404 antes do stream, modo antigo com `historico`, `tool_use` cortado por `max_tokens` e recuperação do 400 de
  assinatura. Também pelo `MessageStream` real do SDK com transporte HTTP simulado (`httpx2.MockTransport`).

## [Não lançado] — branch `feat/python-adiciona-chatbot`

### Ajustes pedidos pelo líder (2ª rodada)
- `ferramentas.py`: nova ferramenta **`listar_faturas_vencidas`** (parâmetro opcional `limite` 1–100, padrão 20),
  mapeada para `app.database.consultas.listar_faturas_vencidas` (itens `{fatura_id, cliente_id, cliente_nome,
  mes_referencia, valor_total, vencimento, dias_em_atraso}`, da mais antiga para a mais recente). Total: 17 ferramentas.
- `ferramentas.py`: `executar_ferramenta` agora captura **`ValueError`** da consulta à parte (ex.: `simular_economia`
  com valor ≤ 0, meses fora de 1..60, amigos < 0) e devolve `("Entrada invalida para '<nome>': <mensagem>", True)`.
  Outras exceções continuam como erro genérico logado.
- Conferido: `resumo_economia_cliente` e `listar_indicacoes` devolvem `None` para cliente inexistente — já tratado como
  "Nenhum registro encontrado..." (`is_error=False`), igual às demais consultas.
- `prompts.py`: orienta usar `listar_faturas_vencidas` para inadimplência geral e `metricas_gerais` para totais.
- `README.md` e `NOTAS_PARA_O_LIDER.md` atualizados (a lacuna de faturas vencidas foi resolvida).

### Adicionado
- `__init__.py` — pacote do chatbot.
- `config.py` — `CHATBOT_MODELO` (default `claude-haiku-5-5`), `CHATBOT_ESFORCO` (default `low`),
  `CHATBOT_TIMEOUT` (default 60 s), `MAX_TOKENS=8000`, `MAX_VOLTAS=8`, `obter_chave_api()` (lê `ANTHROPIC_API_KEY`
  a cada chamada). Carrega `.env` com `python-dotenv` se instalado (sem quebrar se não estiver).
- `base_conhecimento.py` — `BASE_CONHECIMENTO`: quem é a Bulbe (+60 mil clientes, +700 cidades em MG), regras de negócio
  (desconto de até 15% que não incide em iluminação pública e PIS/COFINS, Indique e Ganhe R$ 50 + R$ 50, ativação em
  5 etapas/90 dias, Clube Bulbe), Lei 14.300/2022 e REN ANEEL 1.000/2021, CEMIG × Bulbe, funcionalidades marcadas como
  **[existente]** ou **[novo (squad Cleanergy)]**, significado dos status e FAQ.
- `prompts.py` — `PROMPT_SISTEMA` (instruções + base) e `montar_contexto_dinamico(funcionario, hoje)`.
- `ferramentas.py` — `TOOLS` (16 ferramentas, uma por consulta da seção 1.6, exceto `autenticar_funcionario`,
  `obter_funcionario` e `registrar_chat`), `validar_entrada`, `mascarar_cpf`, `mascarar_telefone`, `mascarar_dados`,
  `executar_ferramenta(nome, entrada) -> tuple[str, bool]`.
- `servico.py` — `ChatbotService.responder(mensagem, historico, funcionario) -> dict` e instância `chatbot_service`.
- `controller.py` — `router` (`/v1/painel/chat`): `POST ""` e `GET /sugestoes` (8 perguntas de exemplo), modelos Pydantic
  `PerguntaChat`, `MensagemHistorico`, `RespostaChat`, `SugestoesChat`.
- `README.md` — fluxo de tool use, erros e como configurar a chave.
- `NOTAS_PARA_O_LIDER.md` — lacunas do contrato e pontos de integração.

### Decisões
- **Uma especificação gera schema e validação** (`_ESPECIFICACAO` em `ferramentas.py`): evita divergência entre o que o
  modelo vê e o que o servidor aceita. Parâmetros desconhecidos são ignorados; textos vazios em opcionais = ausentes.
- **Nomes das ferramentas = nomes das funções** de `app.database.consultas` (mapeamento 1-para-1 por `getattr`,
  resolvido na hora da chamada).
- **Resultado vazio não é erro** (`is_error=False` com mensagem "Nenhum registro encontrado..."), para o modelo sugerir
  refinar a busca; `is_error=True` só para ferramenta desconhecida, entrada inválida ou exceção.
- **Mascaramento por nome de campo** (`cpf*`, `telefone*`, `celular*`, `contato*` com cara de telefone) e, em textos
  livres (`descricao`, `observacao`, `mensagem`, `assunto`, `titulo`), por regex de CPF formatado e telefone.
- **Cache de prompt**: tools + bloco fixo do system com `cache_control: ephemeral`; funcionário e data ficam num segundo
  bloco de system, depois do ponto de cache, para não invalidá-lo.
- **`ferramentas_usadas`** sem repetição, na ordem do primeiro uso.
- **Erros extras dentro de `APIStatusError`** (mantendo a cadeia pedida): 401/403 → 503 `CHATBOT_INDISPONIVEL`
  (chave recusada); 500/503/529 → 503 (sobrecarga); demais → 502 `CHATBOT_ERRO_API`. `RateLimitError` → 429;
  `APIConnectionError` → 503 `CHATBOT_SEM_CONEXAO`.
- **SDK `anthropic` importado com `try/except ImportError`**: sem o pacote, o chat responde 503 e o resto da API sobe.
- **Falha no `registrar_chat` não derruba a resposta** (é logada com `logger.exception`). Só trocas concluídas são registradas.
- Histórico: papéis inválidos/textos vazios descartados, mensagens seguidas do mesmo papel unidas, assistente no início
  descartado, pergunta atual unida à última mensagem se ela também for do funcionário (garante alternância).
- Rotas síncronas (`def`) para o FastAPI rodar a chamada bloqueante ao Claude em threadpool.

### Validação
- `python -m py_compile` em todos os `.py` da pasta (somente sintaxe; nada foi executado nem instalado).

### Pendências
- Ver `NOTAS_PARA_O_LIDER.md` (handler de `ErroDeNegocio` em `main.py`, dependências `anthropic`/`python-dotenv`).
- Testar de ponta a ponta quando `app/database` e `app/painel` estiverem prontos e a chave configurada.

## Ajuste após o primeiro teste real (líder)
- `prompts.py`: nova seção "Histórico da conversa". Como o histórico só traz texto, o modelo
  achava que não tinha consultado as ferramentas nas respostas anteriores e se "corrigia" a cada
  pergunta, refazendo consultas. Agora ele confia nas respostas anteriores e responde só à pergunta atual.
