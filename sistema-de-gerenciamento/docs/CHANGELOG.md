# CHANGELOG — `docs/chatbot/` (agente `docs`)

## 2026-10-18

### Adicionado
- `README.md`: visão geral da entrega (painel + chatbot + banco fictício), índice e começo rápido.
- `levantamento-funcionalidades.md`: pesquisa do site `bulbeenergia.com.br` e das lojas (Google Play `com.bulbe.areadocliente`, App Store id1662527941, versão 2.5.5, nota 4,7 com 352 avaliações); demandas D-01..D-06; tabela comparando o que a Bulbe já tem com as funcionalidades da squad (colunas "Já existe na Bulbe?", "Demanda", "US do front", "Onde aparece no banco/painel"); regras de negócio consolidadas.
- `arquitetura.md`: camadas existentes (controllers/services/repositories/domain) e novas (database, painel, chatbot), fluxo de uma pergunta ao chatbot com *tool use* passo a passo, tabela de ferramentas, rotas, diagramas PlantUML de componentes e de sequência.
- `dicionario-de-dados.md`: 17 tabelas com campos, tipos, descrição e origem (Bulbe / squad / painel), convenções e diagrama ER em PlantUML.
- `guia-do-painel.md`: variáveis do `.env`, instalação e execução (quando liberado), usuários demo (sem a senha), telas, uso do chatbot, 15 perguntas de exemplo e problemas comuns.
- `seguranca-e-lgpd.md`: dados fictícios, mascaramento de CPF/telefone, chatbot somente leitura, PBKDF2, token HMAC com expiração, auditoria em `chat_historico`, defesa contra *prompt injection*, gestão da chave da API, limites e próximos passos.
- `NOTAS_PARA_O_LIDER.md`: inconsistências encontradas entre contrato, front e documentos da API.

### Alterado (conferência com o código dos agentes db, chatbot e painel)
- `arquitetura.md`: arquivos reais de cada pacote (`servico.py`, `ferramentas.py`, `prompts.py`, `config.py`, `static/painel.*`); fluxo do chat alinhado a `servico.py` (system em dois blocos com cache de prompt, `CHATBOT_TIMEOUT`, validação/mascaramento em `ferramentas.py`, resultado vazio ≠ erro, `pause_turn`, registro só de trocas concluídas); tabela de erros do SDK → códigos HTTP; tabela de códigos de erro do painel; ressalva sobre `listar_faturas_vencidas` ainda não exposta como ferramenta; diagramas atualizados.
- `dicionario-de-dados.md`: campos opcionais, unicidades, `CHECK`s e FK circular conforme `modelos.py`; volumes reais do seed (64 clientes, 16 adesões, 6 parceiros, ~40 atendimentos, 200 simulações); detalhes dos personagens; nova seção de campos calculados devolvidos pelas consultas.
- `guia-do-painel.md`: `CHATBOT_TIMEOUT`; comportamento real de `PAINEL_SECRET` e `BULBE_DB_URL`; telas conforme `painel.html`/`painel.js` (menu Visão geral, Clientes, Adesões, Atendimentos; ficha; chat recolhível; botão "Perguntar ao assistente sobre este cliente"); sugestões reais de `GET /v1/painel/chat/sugestoes`; perguntas de exemplo ajustadas ao seed (Marcos em ativação não tem faturas); tabela de problemas com os códigos de erro reais.
- `seguranca-e-lgpd.md`: PBKDF2 com 240.000 iterações e salt de 16 bytes, proteção contra enumeração de e-mails, formato do token, segredo de desenvolvimento, mascaramento recursivo inclusive em textos livres, CSP da interface, histórico só em memória, log de abertura de ficha, limites (sem *rate limit* de login, `exigir_admin` sem uso).
- `README.md`: arquivos entregues por pacote e responsabilidades do líder na integração.
- `NOTAS_PARA_O_LIDER.md`: seção 7 com as pendências encontradas na conferência final.
- Ferramenta `listar_faturas_vencidas` (17ª), adicionada pelo agente `chatbot` e prevista na 2ª rodada do `CONTRATOS.md`, incluída em `arquitetura.md`, `guia-do-painel.md` e `README.md`; ressalva removida e nota ao líder marcada como resolvida.

### Alterado (integração do líder em `app/main.py`)
- Lido o `app/main.py` integrado, mais `.env.example`, `app/requirements.txt` e `.gitignore`.
- `arquitetura.md`: linha do `app/main.py` na tabela de camadas descreve o que já está feito (carga do `.env`, *lifespan* com `inicializar_banco()`, *handler* por classe `ErroDeNegocio`, *handler* global de `StarletteHTTPException`, montagem e redirecionamento de `/painel`); a seção de erros deixou de tratar o envelope `{"detail": ...}` como pendência.
- `guia-do-painel.md`: removida a linha de problema "erros aparecem como `{"detail": ...}`"; explicado que o `main.py` carrega o `.env` e popula o banco no *lifespan*; `/painel` redireciona para `/painel/`.
- `README.md`: a integração aparece como concluída pelo líder (antes estava "a cargo do líder").
- `NOTAS_PARA_O_LIDER.md`: *handlers* e `CHATBOT_TIMEOUT` marcados como resolvidos; nota da senha demo passa a citar também o `.env.example`.
