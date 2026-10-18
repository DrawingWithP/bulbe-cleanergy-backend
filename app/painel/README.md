# Painel de Gestão Bulbe (`app/painel/`)

Painel interno para funcionários da Bulbe Energia consultarem clientes (dados **fictícios**)
e conversarem com o assistente (Claude Haiku 5.5) sobre clientes e sobre o funcionamento do app.

```
app/painel/
├── __init__.py
├── auth.py          # token HMAC-SHA256, dependências funcionario_logado / exigir_admin
├── controller.py    # router /v1/painel (login, métricas, clientes, ficha, adesões, ...)
└── static/          # interface servida em /painel (HTML/CSS/JS puro, sem frameworks)
    ├── index.html   # login
    ├── login.js
    ├── painel.html  # app de uma página (menu lateral + conteúdo + chat)
    ├── painel.css
    ├── painel.js
    └── logo-bulbe.svg
```

## Integração (feita pelo líder em `app/main.py`)

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.painel.controller import router as painel_router

app.include_router(painel_router)
app.mount("/painel", StaticFiles(directory=Path(__file__).parent / "painel" / "static", html=True), name="painel")
```

Acesse `http://localhost:8000/painel/` (login) → `http://localhost:8000/painel/painel.html`.

## Autenticação

- `POST /v1/painel/login` com `{email, senha}` → `{token, funcionario: {id, nome, email, perfil}}`.
  Credenciais conferidas por `app.database.consultas.autenticar_funcionario`. Erro: 401 `CREDENCIAIS_INVALIDAS`
  (mensagem genérica, não revela se o e-mail existe).
- Token: `base64url(payload JSON) + "." + base64url(HMAC-SHA256(payload))`, só com a stdlib.
  Payload: `id, nome, email, perfil, iat, exp`. **Expira em 8 horas.** Assinatura comparada com `hmac.compare_digest`.
- Segredo: variável `PAINEL_SECRET`. Sem ela, usa um segredo de desenvolvimento e registra `logging.warning`
  (uma vez). **Defina `PAINEL_SECRET` fora do ambiente local**, senão qualquer um que leia o código forja tokens.
- Envio: cabeçalho `Authorization: Bearer <token>`. A interface guarda o token no `sessionStorage`
  (some ao fechar a aba) e volta ao login em qualquer 401.
- Dependências para outras pastas (o chatbot usa a primeira):
  - `funcionario_logado` → `{id, nome, email, perfil}` ou 401 (`NAO_AUTENTICADO` / `TOKEN_INVALIDO`);
  - `exigir_admin` → 403 `ACESSO_NEGADO` se `perfil != "admin"`.
- Erros no formato `{"error": {"code", "message", "status"}}`, enviados como `detail` de `HTTPException`.

## Rotas (`/v1/painel`)

| Método | Rota | Resposta |
|---|---|---|
| POST | `/login` | `{token, funcionario}` (público) |
| GET | `/me` | funcionário do token |
| GET | `/metricas` | `metricas_gerais()` |
| GET | `/clientes?termo=&status=&cidade=&limite=` | `buscar_clientes(...)` (`limite` 1–100) |
| GET | `/clientes/{id}` | `{cliente, ativacao, faturas, economia, indicacoes, clube, cupons, notificacoes, atendimentos}` ou 404 `CLIENTE_NAO_ENCONTRADO` |
| GET | `/adesoes?situacao=&limite=` | `listar_adesoes(...)` |
| GET | `/atendimentos?status=&limite=` | `listar_atendimentos(...)` |
| GET | `/usinas`, `/parceiros?apenas_ativos=`, `/dicas` | listas |

Todas, menos `/login`, exigem `Depends(funcionario_logado)`. A abertura de uma ficha gera um log
`INFO` com o id do funcionário e do cliente (trilha de auditoria / LGPD).

## Telas

- **Login** (`/painel/`): e-mail + senha; avisos de sessão expirada ou encerrada.
- **Visão geral**: cards de métricas (clientes, economia gerada, faturas vencidas, indicações, Clube Bulbe,
  adesões, simulações, acesso ao app), barras em CSS da ativação por etapa, clientes por status, adesões
  por situação, usinas e parceiros.
- **Clientes**: busca (nome, e-mail, CPF, instalação, código de indicação) e filtros de status/cidade/quantidade;
  tabela com linhas clicáveis (o nome é um link, acessível por teclado).
- **Ficha do cliente** (`#/cliente/<id>`): dados cadastrais; jornada de ativação de 5 etapas
  (cartão azul "Etapa X de 5" + círculos e linha do tempo, inspirados nas telas Status/Detalhes do app);
  economia; Indique e Ganhe; faturas; Clube Bulbe (sequência semanal, cartas); cupons; notificações;
  atendimentos. Botão **"Perguntar ao assistente sobre este cliente"** pré-preenche a pergunta com nome e id.
- **Adesões** e **Atendimentos**: tabelas com filtro de situação/status e link para a ficha.
- **Chat** (todas as telas): painel lateral fixo e recolhível (vira gaveta em telas ≤ 1200 px).
  - Sugestões em chips vindas de `GET /v1/painel/chat/sugestoes`.
  - `POST /v1/painel/chat` com `{mensagem, historico: [{papel: "funcionario"|"assistente", texto}]}`
    (últimos 20 itens; histórico só em memória — some ao recarregar a página).
  - Indicador "digitando...", ferramentas usadas exibidas discretamente sob a resposta.
  - 503 `CHATBOT_INDISPONIVEL` → aviso pedindo para configurar `ANTHROPIC_API_KEY`.
  - Resposta renderizada com HTML **escapado**; só `**negrito**`, listas `- ` e quebras de linha viram marcação.
  - Enter envia, Shift+Enter quebra a linha; limite de 2000 caracteres.

## Segurança da interface

- Todo dado da API passa por `esc()` antes de entrar no HTML; a resposta do chat é escapada antes da formatação.
- CSP via `<meta>`: só scripts/estilos do próprio domínio (+ Google Fonts), sem scripts inline;
  larguras das barras aplicadas via CSSOM (`el.style.width`), não por atributo `style`.
- Sem frameworks nem CDN de JavaScript.

## Acessibilidade

Link "Pular para o conteúdo", `aria-current` no menu, foco no título ao trocar de tela, `role="log"` no chat,
selos com texto (não só cor), contraste AA nos textos (tons escuros de verde/amarelo), `prefers-reduced-motion`.
