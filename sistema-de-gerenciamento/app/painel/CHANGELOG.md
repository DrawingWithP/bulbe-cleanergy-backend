# CHANGELOG — `app/painel/`

## Melhorias (v2)

### Segurança do login
- Novo `alertas.py` (só biblioteca padrão: `smtplib` + `email.message`): leitura das variáveis `LOGIN_*`, `SMTP_*` e
  `ALERTA_LOGIN_EMAIL` a cada uso (valores inválidos caem no padrão com aviso no log), reserva de "1 alerta por e-mail
  a cada janela" em memória com `threading.Lock` e conferência na auditoria (cobre reinícios), montagem do e-mail
  (e-mail tentado, falhas, IP e horário, sem a senha; caracteres de controle removidos) e envio com STARTTLS quando
  `SMTP_TLS=true`. O envio nunca levanta exceção: sucesso, falta de configuração ou erro de SMTP viram log + `alerta_email`
  na auditoria com o detalhe.
- `POST /v1/painel/login`: com `LOGIN_BLOQUEIO_APOS_FALHAS` (5) falhas do e-mail em `LOGIN_JANELA_MINUTOS` (15) responde
  **429 `LOGIN_BLOQUEADO`** com `Retry-After` (a janela inteira, em segundos), mesmo com a senha certa; na falha que passa de
  `LOGIN_ALERTA_APOS_FALHAS` (3) agenda o alerta em `BackgroundTasks`. O 401 passou a ser devolvido como `JSONResponse`
  (mesmo corpo `{"error": {...}}`) para as tarefas em segundo plano rodarem depois da resposta.
- Auditoria com IP do `Request`: `login_ok`, `login_falha` (com `funcionario_id` quando o e-mail pertence a um funcionário),
  `login_bloqueado`, `ver_ficha`, `ver_auditoria` e `expurgo`. Falha ao gravar a auditoria é registrada no log sem derrubar a rota.

### Rotas
- `/clientes` paginada (`etapa`, `pagina`, `por_pagina`; `limite` da v1 aceito como sinônimo); `/adesoes` e `/atendimentos`
  paginadas (`/atendimentos` aceita também `cliente_id`).
- Novas: `/clientes/parados` (antes de `/clientes/{id}`), `/ativacoes/resumo`, e só para admin (`exigir_admin`)
  `/auditoria`, `/uso-chatbot` e `POST /admin/expurgo` (prazos `CHAT_RETENCAO_DIAS` 180 e `AUDITORIA_RETENCAO_DIAS` 730,
  mínimo de 1 dia; resposta com as contagens e os prazos usados).

### Interface
- Paginação real (anterior/próxima, "página X de Y", itens por página) em Clientes, Adesões, Atendimentos e Auditoria,
  com carregamento genérico que aceita também a lista simples da v1; filtro por etapa em Clientes.
- Telas novas: Ativações (resumo + clientes parados com filtros), Dicas, Usinas, Parceiros e, só para admin (menu "Gestão"),
  Auditoria (com expurgo sob confirmação) e Uso do assistente.
- Visão geral: barra "Ativados (30 dias)" e bônus pagos do Clube. Ficha: coluna "Bônus Clube" nas faturas e "Bônus do Clube"
  na economia.
- Chat com streaming (`fetch` + `ReadableStream`, leitor de SSE tolerante a pedaços quebrados e a `\r\n`), indicador do
  que o assistente está fazendo, ferramentas consultadas na hora, custo estimado discreto por resposta, `conversa_id`
  guardado (memória + `sessionStorage`), "Nova conversa", lista de conversas anteriores e reabertura; fallback para
  `POST /v1/painel/chat` quando o stream falha antes de começar; tempo limite por inatividade do stream (90 s).
- Login: mensagem "Muitas tentativas. Tente de novo em N minutos." no 429, com N calculado pelo `Retry-After`.
- Mantidos: escape de todo dado da API, CSP sem script/estilo inline, `aria-*` e foco; o streaming usa `aria-busy` para o
  leitor de tela anunciar a resposta pronta.

### Validação
- `python -m py_compile` nos módulos do painel e `node --check` em `login.js` e `painel.js`: OK.
- Teste local do alerta com `smtplib.SMTP` simulado: a 4ª falha envia 1 e-mail (sem a senha digitada), a 5ª não reenvia,
  a 6ª tentativa recebe 429 com `Retry-After: 900`; reinício do controle em memória não reenvia (auditoria); erro de SMTP e
  SMTP ausente viram `alerta_email` com detalhe. Teste do leitor de SSE em Node com pedaços quebrados no meio de caractere.
- Suíte `tests/test_login_bloqueio_alerta.py`, `tests/test_painel_rotas.py` e `tests/test_seguranca_senha_token.py`: todos passando.
- A interface não foi aberta no navegador (o servidor não é iniciado nesta etapa).

## 2026-10-18 — Painel de Gestão + interface do chat

### Criado
- `__init__.py` — pacote do painel.
- `auth.py` — autenticação do funcionário só com stdlib + FastAPI:
  - `criar_token(funcionario)`: `base64url(JSON{id,nome,email,perfil,iat,exp}).base64url(HMAC-SHA256)`, expira em 8h;
  - `validar_token(token)`: confere assinatura com `hmac.compare_digest`, expiração e campos; devolve `{id,nome,email,perfil}` ou `None`;
  - `funcionario_logado` (dependência, `Authorization: Bearer`) → 401 `NAO_AUTENTICADO`/`TOKEN_INVALIDO`;
  - `exigir_admin` → 403 `ACESSO_NEGADO`;
  - segredo `PAINEL_SECRET` lido a cada uso (funciona com `.env` carregado depois do import); default de desenvolvimento com `logging.warning` (uma vez).
- `controller.py` — `router = APIRouter(prefix="/v1/painel", tags=["Painel"])` com as rotas da tabela 2.2:
  login (modelo Pydantic `{email, senha}`, e-mail normalizado em minúsculas, 401 genérico), `/me`, `/metricas`,
  `/clientes` (filtros + `limite` 1–100), `/clientes/{id}` (ficha agregando as 9 consultas; 404 `CLIENTE_NAO_ENCONTRADO`),
  `/adesoes`, `/atendimentos`, `/usinas`, `/parceiros`, `/dicas`. Log de auditoria ao abrir ficha.
- `static/index.html` + `static/login.js` — tela de login (token no `sessionStorage`).
- `static/painel.html`, `static/painel.css`, `static/painel.js` — app de uma página:
  menu lateral (Visão geral, Clientes, Adesões, Atendimentos), ficha do cliente com jornada de 5 etapas
  (estilo das telas Status/Detalhes do front), chat lateral recolhível com sugestões, histórico (máx. 20),
  "digitando...", ferramentas usadas, tratamento de 503 `CHATBOT_INDISPONIVEL` e botão
  "Perguntar ao assistente sobre este cliente".
- `static/logo-bulbe.svg` — logo copiado do front (`icons_final/bulbe.svg`).
- `README.md` — telas, rotas e autenticação. `NOTAS_PARA_O_LIDER.md` — lacunas/sugestões de integração.

### Decisões
- Paleta e fonte (Poppins) do `final.css`; tons escuros derivados para texto em verde/amarelo (contraste AA).
- CSP por `<meta>` sem `unsafe-inline`: nenhum script/estilo inline; larguras via `element.style`.
- Toda saída de dados passa por `esc()`; a resposta do chat é escapada antes de converter `**negrito**`, `- ` e quebras.
- Datas puras (`AAAA-MM-DD`) interpretadas no fuso local; datetimes sem fuso tratados como UTC (contrato).
- `HTTPException` com `detail={"error": {...}}` em todos os erros; a interface entende `{"error"}` e `{"detail": {"error"}}`.
- Histórico do chat só em memória (não persiste no navegador), por LGPD.

### Validação
- `python -m py_compile` em `__init__.py`, `auth.py`, `controller.py`: OK. Nada foi executado (servidor/interface não rodados).

### Pendências
- Handler global para desembrulhar `detail.error` (ver `NOTAS_PARA_O_LIDER.md`, item 1).
- Rate limit de login (item 3).
- Testar a interface com o banco e o chatbot reais após a integração.
