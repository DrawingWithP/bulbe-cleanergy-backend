# Painel de Gestão Bulbe (`app/painel/`)

Painel interno para funcionários da Bulbe Energia consultarem clientes (dados **fictícios**)
e conversarem com o assistente (Claude Haiku 5.5) sobre clientes e sobre o funcionamento do app.

```
app/painel/
├── __init__.py
├── auth.py          # token HMAC-SHA256, dependências funcionario_logado / exigir_admin
├── alertas.py       # limites de tentativas de login + alerta por e-mail (smtplib, só stdlib)
├── controller.py    # router /v1/painel (login, métricas, clientes, ativações, auditoria, ...)
└── static/          # interface servida em /painel (HTML/CSS/JS puro, sem frameworks)
    ├── index.html   # login
    ├── login.js
    ├── painel.html  # app de uma página (menu lateral + conteúdo + chat)
    ├── painel.css
    ├── painel.js
    └── logo-bulbe.svg
```

## Integração (em `app/main.py`)

```python
from app.painel.controller import router as painel_router

app.include_router(painel_router)
app.mount("/painel", StaticFiles(directory=Path(__file__).parent / "painel" / "static", html=True), name="painel")
```

Acesse `http://localhost:8000/painel/` (login) → `http://localhost:8000/painel/painel.html`.
O `app/main.py` carrega o `.env` e devolve `{"error": {...}}` puro para as `HTTPException` do painel.

## Autenticação

- `POST /v1/painel/login` com `{email, senha}` → `{token, funcionario: {id, nome, email, perfil}}`.
  Erros: 401 `CREDENCIAIS_INVALIDAS` (mensagem genérica, não revela se o e-mail existe) e
  429 `LOGIN_BLOQUEADO` (ver abaixo).
- Token: `base64url(payload JSON) + "." + base64url(HMAC-SHA256(payload))`, só com a stdlib.
  Payload: `id, nome, email, perfil, iat, exp`. **Expira em 8 horas.** Assinatura comparada com `hmac.compare_digest`.
- Segredo: variável `PAINEL_SECRET`. Sem ela, usa um segredo de desenvolvimento e registra `logging.warning`.
- Envio: cabeçalho `Authorization: Bearer <token>`. A interface guarda o token no `sessionStorage`
  (some ao fechar a aba) e volta ao login em qualquer 401.
- Dependências: `funcionario_logado` → `{id, nome, email, perfil}` ou 401; `exigir_admin` → 403 `ACESSO_NEGADO`.

### Segurança do login (v2)

| Variável | Padrão | Efeito |
|---|---|---|
| `LOGIN_JANELA_MINUTOS` | 15 | janela de contagem das falhas (por e-mail, sem diferenciar maiúsculas) |
| `LOGIN_BLOQUEIO_APOS_FALHAS` | 5 | com esse número de falhas na janela, o login responde **429 `LOGIN_BLOQUEADO`** com `Retry-After` (segundos) até a janela passar, **mesmo com a senha certa** |
| `LOGIN_ALERTA_APOS_FALHAS` | 3 | quando as falhas passam desse número (na 4ª), sai **um** e-mail de alerta para `ALERTA_LOGIN_EMAIL` |
| `SMTP_HOST`, `SMTP_PORTA` (587), `SMTP_USUARIO`, `SMTP_SENHA`, `SMTP_REMETENTE`, `SMTP_TLS` (true) | — | servidor de envio; com `SMTP_TLS=true` usa STARTTLS. Remetente vazio usa o `SMTP_USUARIO`. Gmail: `smtp.gmail.com`, porta 587 e uma **senha de app** |

- As falhas são contadas pela auditoria (`contar_falhas_login`), então o bloqueio vale também depois de reiniciar o servidor.
  Tentativas bloqueadas (`login_bloqueado`) não contam como falha nem prolongam a janela.
- O alerta (`alertas.enviar_alerta_login`) roda em `BackgroundTasks`, depois da resposta do login. Ele informa o e-mail tentado,
  a quantidade de falhas, o IP e o horário; **nunca** recebe nem inclui a senha digitada.
- "1 alerta por e-mail a cada janela": reserva em memória protegida por `threading.Lock` + consulta à auditoria
  (`alerta_email` recente do mesmo e-mail), que cobre reinícios do servidor.
- Sem SMTP configurado ou com erro de envio, o login continua normal: o problema vai para o log (sem a senha do SMTP)
  e para a auditoria (`alerta_email`, com o detalhe). Envio bem-sucedido também fica registrado em `alerta_email`.
- Todas as variáveis são lidas do ambiente a cada uso; valores inválidos usam o padrão (com aviso no log).

### Auditoria (`registrar_auditoria`, com o IP do `Request`)

`login_ok`, `login_falha` (com `funcionario_id` quando o e-mail é de um funcionário; `null` se o e-mail não existe),
`login_bloqueado`, `alerta_email`, `ver_ficha` (recurso `cliente`/id), `ver_auditoria` (filtros usados) e `expurgo`
(prazos e contagens). Uma falha ao gravar a auditoria vai para o log e não derruba a requisição.
O IP é o do socket (`request.client.host`); atrás de proxy, rode o uvicorn com `--proxy-headers`.

## Rotas (`/v1/painel`)

| Método | Rota | Resposta |
|---|---|---|
| POST | `/login` | `{token, funcionario}` (público); 401 / 429 com `Retry-After` |
| GET | `/me` | funcionário do token |
| GET | `/metricas` | `metricas_gerais()` (etapa 5 = ativados nos últimos 30 dias; `clube.bonus_pagos`) |
| GET | `/clientes?termo&status&cidade&etapa&pagina&por_pagina` | **paginada** `{data, pagina, por_pagina, total, total_paginas}` (`por_pagina` 1–100; `limite` da v1 ainda aceito como sinônimo) |
| GET | `/clientes/parados?etapa&dias_minimos=30&limite=50` | `listar_clientes_parados(...)` (declarada antes de `/clientes/{id}`) |
| GET | `/clientes/{id}` | ficha `{cliente, ativacao, faturas, economia, indicacoes, clube, cupons, notificacoes, atendimentos}`; grava `ver_ficha`; 404 `CLIENTE_NAO_ENCONTRADO` |
| GET | `/ativacoes/resumo` | `resumo_ativacoes()` |
| GET | `/adesoes?situacao&pagina&por_pagina` | **paginada** |
| GET | `/atendimentos?status&cliente_id&pagina&por_pagina` | **paginada**, itens com `cliente_nome` |
| GET | `/usinas`, `/parceiros?apenas_ativos=`, `/dicas` | listas |
| GET | `/auditoria?funcionario_id&acao&pagina&por_pagina=50` | **só admin**; paginada, itens com `funcionario_nome`; grava `ver_auditoria` |
| GET | `/uso-chatbot?dias=30` | **só admin**; `metricas_uso_chatbot(dias)` |
| POST | `/admin/expurgo` | **só admin**; `expurgar_dados_antigos(CHAT_RETENCAO_DIAS=180, AUDITORIA_RETENCAO_DIAS=730)` → `{chat_historico, chat_conversas, chat_mensagens, auditoria, dias_chat, dias_auditoria}`; grava `expurgo` |

Todas, menos `/login`, exigem `Depends(funcionario_logado)`; as de gestão usam `Depends(exigir_admin)` (403 para atendimento).

## Telas

- **Login** (`/painel/`): e-mail + senha; avisos de sessão expirada/encerrada; no 429 mostra
  "Muitas tentativas. Tente de novo em N minutos." (N calculado pelo `Retry-After`).
- **Visão geral**: cards de métricas (o do Clube mostra os bônus pagos), ativação por etapa
  (a 5ª barra é "Ativados (30 dias)"), clientes por status, adesões, usinas e parceiros.
- **Clientes**: busca + filtros de status, cidade e **etapa da ativação**; paginação real
  (anterior/próxima, "página X de Y", itens por página).
- **Ficha do cliente** (`#/cliente/<id>`): jornada de 5 etapas, economia (com **bônus do Clube**), faturas
  (colunas "Bônus indicação" e **"Bônus Clube"**), Indique e Ganhe, Clube Bulbe, cupons, notificações, atendimentos.
- **Adesões** e **Atendimentos**: tabelas paginadas com filtros.
- **Ativações**: resumo (em ativação, atrasados > 90 dias, ativados em 30 dias, tempo médio, clientes e dias médios por etapa)
  e **clientes parados** com filtros de etapa, dias mínimos e quantidade.
- **Dicas**, **Usinas** (com clientes ativos) e **Parceiros** (opção de incluir inativos).
- Só para admin (o menu "Gestão" só aparece para o perfil admin; a API também exige admin):
  - **Auditoria**: filtros de ação e funcionário, paginação e botão **"Expurgar dados antigos"** (com confirmação).
  - **Uso do assistente**: perguntas, conversas, custo estimado (US$), custo médio, tempo médio, tokens,
    tabela por funcionário, ferramentas mais usadas e tabela por dia (7/30/90/365 dias).
- **Chat** (todas as telas): painel lateral recolhível (gaveta em telas ≤ 1200 px).
  - Envia para `POST /v1/painel/chat/stream` com `fetch` + `ReadableStream` (o `EventSource` não aceita POST nem cabeçalho)
    e lê os eventos SSE `inicio` / `texto` / `ferramenta` / `fim` / `erro`: o texto aparece enquanto chega,
    as ferramentas consultadas aparecem na hora e, no fim, o custo estimado da resposta fica discreto no rodapé.
  - Guarda o `conversa_id` (memória + `sessionStorage`, para reabrir a conversa ao recarregar a página).
  - Botão **Nova conversa** e lista de **conversas anteriores** (`GET /v1/painel/chat/conversas`); reabrir carrega
    `GET /v1/painel/chat/conversas/{id}`.
  - Se o stream falhar **antes de começar** (rota inexistente, rede, resposta que não é SSE), cai para
    `POST /v1/painel/chat` com o mesmo corpo. Erros padronizados (429, 503 `CHATBOT_INDISPONIVEL`, conversa não encontrada)
    viram avisos claros; se a conexão cair no meio, o texto parcial fica com um aviso.

## Segurança da interface

- Todo dado da API passa por `esc()` (ou `textContent`) antes de entrar no HTML; a resposta do chat é escapada antes da
  formatação (`**negrito**`, listas `- ` e quebras de linha), inclusive durante o streaming.
- CSP via `<meta>`: só scripts/estilos do próprio domínio (+ Google Fonts), sem scripts nem estilos inline;
  larguras das barras aplicadas via CSSOM (`el.style.width`).
- Sem frameworks nem CDN de JavaScript. O `sessionStorage` guarda só o token, os dados do funcionário e o id da conversa.

## Acessibilidade

Link "Pular para o conteúdo", `aria-current` no menu, foco no título ao trocar de tela e no resumo da tabela ao paginar,
paginação em `<nav>` com rótulo, `role="log"` no chat com `aria-busy` enquanto a resposta chega (o leitor de tela anuncia
a resposta pronta), `aria-expanded` no botão de conversas, Esc fecha a lista de conversas/gaveta, selos com texto
(não só cor), contraste AA e `prefers-reduced-motion`.
