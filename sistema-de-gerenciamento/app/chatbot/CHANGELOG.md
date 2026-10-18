# CHANGELOG — app/chatbot (agente "chatbot")

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
