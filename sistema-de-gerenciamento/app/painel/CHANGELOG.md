# CHANGELOG — `app/painel/` (agente `painel`)

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
