# CHANGELOG — `docs/`

## Melhorias (v2) — branch `feat/python-melhorias-sistema`

Documentação atualizada conforme a seção 5 de `CONTRATOS-MELHORIAS.md` e conferida, no fim, com o código de
`app/database`, `app/chatbot`, `app/painel`, `tests/`, `app/main.py` e `.env.example` (e com os `CHANGELOG.md` e
`PENDENCIAS.md` dessas pastas).

### Adicionado
- `testes.md`: como rodar a suíte (`.venv\Scripts\python.exe -m pytest`, com `requirements-dev.txt`), organização da
  pasta `tests/` arquivo por arquivo, isolamento (SQLite temporário, chave da Anthropic vazia, SMTP vazio, travas contra o
  banco real), API da Anthropic e SMTP simulados, *fixtures* principais e a avaliação do chatbot com o modelo real
  (`app/chatbot/avaliacoes/`, fora do `pytest` porque gasta créditos).
- `PENDENCIAS.md`: diferenças entre o contrato e o que foi implementado, e pontos que dependem da integração.

### Alterado
- `README.md`: resumo do que a v2 acrescentou, aviso de recriação do banco, pacotes com os arquivos novos
  (`alertas.py`, `avaliacoes/`, `tests/`), índice com `CONTRATOS-MELHORIAS.md`, `testes.md` e `PENDENCIAS.md`, começo
  rápido com `.venv`, seed e testes; princípios de rastreabilidade e retenção.
- `arquitetura.md`: tabela "o que mudou na v2"; camadas com 20 tabelas, `alertas.py`, 19 ferramentas e retenção no
  *lifespan*; diagrama de componentes atualizado (SMTP, streaming, expurgo); fluxo do chat com **streaming SSE** passo a
  passo (conversa criada antes da chamada, prompt de sistema idêntico byte a byte com contexto na pergunta, cache,
  `eager_input_streaming`, gravação só da troca concluída); formato e eventos do stream; erros do SDK no stream;
  **conversas no servidor com histórico só de acréscimo** (limite de mensagens, modo da v1, resposta cortada no meio de
  ferramenta, reenvio sem `thinking`); **uso e custo** com a fórmula, a tabela de prompt longo e as variáveis de preço;
  **login com bloqueio, alerta por e-mail e auditoria** com diagrama de sequência PlantUML; **retenção e expurgo**;
  ferramentas novas; diagrama de sequência do chat com streaming; rotas e códigos de erro novos.
- `dicionario-de-dados.md`: tabelas `chat_conversas`, `chat_mensagens` e `auditoria_acessos`; colunas novas de
  `chat_historico` (conversa, modelo, tokens, custo, duração) e `faturas.bonus_clube`; volumes do seed da v2;
  diagrama ER com as tabelas novas; campos calculados novos (parados, resumo de ativações, bônus, uso do chatbot,
  paginação).
- `guia-do-painel.md`: variáveis novas do `.env` (conversas e preços do chatbot, retenção, limites do login, SMTP) e
  passo a passo da **senha de app do Gmail** para `SMTP_SENHA` (o destino do alerta vem de `ALERTA_LOGIN_EMAIL`);
  instalação com `.venv`; **recriação do banco** com `python -m app.database.seed` depois da atualização; **como rodar os
  testes**; telas novas (Ativações, Dicas, Usinas, Parceiros, Auditoria e Uso do assistente) e mudanças nas antigas
  (paginação, bônus do Clube, chat com streaming e conversas); sugestões e perguntas de exemplo novas; problemas comuns
  da v2 (429, alerta que não chega, banco da v1, 409/404 de conversa). Removida a observação sobre execução apenas após
  liberação e corrigida a pasta de onde os comandos são rodados.
- `seguranca-e-lgpd.md`: novas seções de **limite de tentativas e bloqueio**, **alerta por e-mail**, **auditoria de
  acesso** (inclusive `ver_ficha`), **registro do chatbot e conversas no servidor**, **retenção e expurgo** e **custo do
  chatbot**; defesa contra *prompt injection* atualizada (histórico controlado pelo servidor); `exigir_admin` agora em uso;
  revogação da senha de app; tabela de limites e próximos passos revista.
- `levantamento-funcionalidades.md`: onde as funcionalidades aparecem na v2 (tela Ativações, bônus do Clube, telas de
  Dicas e Parceiros, auditoria, streaming e conversas).
- `CHANGELOG.md`: entradas da v1 reescritas de forma impessoal.

## 2026-10-18 (v1)

### Adicionado
- `README.md`: visão geral da entrega (painel + chatbot + banco fictício), índice e começo rápido.
- `levantamento-funcionalidades.md`: pesquisa do site `bulbeenergia.com.br` e das lojas (Google Play `com.bulbe.areadocliente`, App Store id1662527941, versão 2.5.5, nota 4,7 com 352 avaliações); demandas D-01..D-06; tabela comparando o que a Bulbe já tem com as funcionalidades da squad (colunas "Já existe na Bulbe?", "Demanda", "US do front", "Onde aparece no banco/painel"); regras de negócio consolidadas.
- `arquitetura.md`: camadas existentes (controllers/services/repositories/domain) e novas (database, painel, chatbot), fluxo de uma pergunta ao chatbot com *tool use* passo a passo, tabela de ferramentas, rotas, diagramas PlantUML de componentes e de sequência.
- `dicionario-de-dados.md`: 17 tabelas com campos, tipos, descrição e origem (Bulbe / squad / painel), convenções e diagrama ER em PlantUML.
- `guia-do-painel.md`: variáveis do `.env`, instalação e execução (quando liberado), usuários demo (sem a senha), telas, uso do chatbot, 15 perguntas de exemplo e problemas comuns.
- `seguranca-e-lgpd.md`: dados fictícios, mascaramento de CPF/telefone, chatbot somente leitura, PBKDF2, token HMAC com expiração, auditoria em `chat_historico`, defesa contra *prompt injection*, gestão da chave da API, limites e próximos passos.
- `NOTAS_PARA_O_LIDER.md`: inconsistências encontradas entre contrato, front e documentos da API.

### Alterado (conferência com o código de `app/database`, `app/chatbot` e `app/painel`)
- `arquitetura.md`: arquivos reais de cada pacote (`servico.py`, `ferramentas.py`, `prompts.py`, `config.py`, `static/painel.*`); fluxo do chat alinhado a `servico.py` (system em dois blocos com cache de prompt, `CHATBOT_TIMEOUT`, validação/mascaramento em `ferramentas.py`, resultado vazio ≠ erro, `pause_turn`, registro só de trocas concluídas); tabela de erros do SDK → códigos HTTP; tabela de códigos de erro do painel; ressalva sobre `listar_faturas_vencidas` ainda não exposta como ferramenta; diagramas atualizados.
- `dicionario-de-dados.md`: campos opcionais, unicidades, `CHECK`s e FK circular conforme `modelos.py`; volumes reais do seed (64 clientes, 16 adesões, 6 parceiros, ~40 atendimentos, 200 simulações); detalhes dos personagens; nova seção de campos calculados devolvidos pelas consultas.
- `guia-do-painel.md`: `CHATBOT_TIMEOUT`; comportamento real de `PAINEL_SECRET` e `BULBE_DB_URL`; telas conforme `painel.html`/`painel.js` (menu Visão geral, Clientes, Adesões, Atendimentos; ficha; chat recolhível; botão "Perguntar ao assistente sobre este cliente"); sugestões reais de `GET /v1/painel/chat/sugestoes`; perguntas de exemplo ajustadas ao seed (Marcos em ativação não tem faturas); tabela de problemas com os códigos de erro reais.
- `seguranca-e-lgpd.md`: PBKDF2 com 240.000 iterações e salt de 16 bytes, proteção contra enumeração de e-mails, formato do token, segredo de desenvolvimento, mascaramento recursivo inclusive em textos livres, CSP da interface, histórico só em memória, log de abertura de ficha, limites (sem *rate limit* de login, `exigir_admin` sem uso).
- `README.md`: arquivos entregues por pacote e responsabilidades da integração.
- `NOTAS_PARA_O_LIDER.md`: seção 7 com as pendências encontradas na conferência final.
- Ferramenta `listar_faturas_vencidas` (17ª), prevista na 2ª rodada do `CONTRATOS.md`, incluída em `arquitetura.md`, `guia-do-painel.md` e `README.md`; ressalva removida e nota correspondente marcada como resolvida.

### Alterado (integração em `app/main.py`)
- Lido o `app/main.py` integrado, mais `.env.example`, `app/requirements.txt` e `.gitignore`.
- `arquitetura.md`: linha do `app/main.py` na tabela de camadas descreve o que já está feito (carga do `.env`, *lifespan* com `inicializar_banco()`, *handler* por classe `ErroDeNegocio`, *handler* global de `StarletteHTTPException`, montagem e redirecionamento de `/painel`); a seção de erros deixou de tratar o envelope `{"detail": ...}` como pendência.
- `guia-do-painel.md`: removida a linha de problema "erros aparecem como `{"detail": ...}`"; explicado que o `main.py` carrega o `.env` e popula o banco no *lifespan*; `/painel` redireciona para `/painel/`.
- `README.md`: a integração aparece como concluída (antes estava pendente).
- `NOTAS_PARA_O_LIDER.md`: *handlers* e `CHATBOT_TIMEOUT` marcados como resolvidos; nota da senha demo passa a citar também o `.env.example`.
