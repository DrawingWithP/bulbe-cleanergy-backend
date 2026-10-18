# Painel de Gestão + Chatbot — Bulbe Energia (squad Cleanergy)

Painel web **interno** para funcionários da Bulbe Energia (energia solar por assinatura em Minas Gerais)
consultarem clientes e a operação, com um **chatbot** (Claude Haiku 5.5, modelo `claude-haiku-5-5`, via
*tool use*) que responde perguntas sobre clientes e sobre o funcionamento do app — tudo apoiado num
**banco de dados fictício** (SQLite + SQLAlchemy 2).

- Branch: `feat/python-adiciona-chatbot`
- Disciplina: Projeto Ciência de Dados II — Ibmec, 2º semestre de 2026
- Front-end do cliente (Projeto I): repositório `Bulbe-Squad-cleanergy`

## Por que um painel com chatbot?

As demandas levantadas com a Bulbe (D-01 a D-06) mostram que o cliente não entende o serviço, não confia antes
do desconto chegar e pergunta o tempo todo "já estou ativo?". O front da squad ataca isso do lado do cliente
(home aberta, simulador, jornada de ativação, Clube Bulbe). O painel ataca do lado da Bulbe: o atendente
encontra o cliente, vê a etapa da ativação, as faturas e o engajamento em segundos — ou simplesmente pergunta ao chatbot.

## O que foi entregue

| Pacote | Conteúdo |
|---|---|
| `app/database/` | `modelos.py` (17 tabelas), `conexao.py`, `seed.py` (64 clientes fictícios, semente 42), `consultas.py` (somente leitura + `registrar_chat`), `seguranca.py` (PBKDF2) |
| `app/painel/` | `auth.py` (token HMAC de 8 h), `controller.py` (rotas `/v1/painel/*`), `static/` (login `index.html` + `login.js`; app `painel.html` + `painel.css` + `painel.js`) |
| `app/chatbot/` | `servico.py` (loop de *tool use* com o Claude Haiku 5.5), `ferramentas.py` (17 ferramentas somente leitura + mascaramento de CPF/telefone), `prompts.py`, `base_conhecimento.py`, `config.py`, `controller.py` (rotas `/v1/painel/chat`) |
| `docs/` | Esta documentação |

Cada pacote tem o seu `README.md`, `CHANGELOG.md` e `NOTAS_PARA_O_LIDER.md`. Tudo fica na pasta
`sistema-de-gerenciamento/`, separada do back-end do app (`backend/`): o sistema tem o próprio
`app/main.py` (carga do `.env`, routers, montagem de `/painel`, `inicializar_banco()` no *lifespan* e *handlers*
de erro no formato `{"error": {...}}`), o próprio `app/erros.py`, o `requirements.txt` (`sqlalchemy`, `anthropic`,
`python-dotenv`) e o `.env.example`.

## Índice da documentação

| Documento | Conteúdo |
|---|---|
| [CONTRATOS.md](CONTRATOS.md) | Contrato entre as pastas (interfaces, rotas, tabelas) definido no início do desenvolvimento |
| [levantamento-funcionalidades.md](levantamento-funcionalidades.md) | O que o app/site da Bulbe já tem × o que a squad criou, com demandas, US e onde aparece no banco/painel |
| [arquitetura.md](arquitetura.md) | Camadas existentes e novas, fluxo de uma pergunta ao chatbot passo a passo, diagramas PlantUML |
| [dicionario-de-dados.md](dicionario-de-dados.md) | Todas as tabelas e campos com tipo, descrição e origem, e diagrama ER |
| [guia-do-painel.md](guia-do-painel.md) | `.env`, instalação, como rodar, usuários demo, telas e 15 perguntas de exemplo |
| [seguranca-e-lgpd.md](seguranca-e-lgpd.md) | Dados fictícios, mascaramento, somente leitura, PBKDF2, token HMAC, auditoria, *prompt injection*, próximos passos |
| [CHANGELOG.md](CHANGELOG.md) | Histórico desta pasta |
| [NOTAS_PARA_O_LIDER.md](NOTAS_PARA_O_LIDER.md) | Dúvidas e inconsistências encontradas durante a documentação |

## Começo rápido

```bash
cd sistema-de-gerenciamento
cp .env.example .env          # preencha ANTHROPIC_API_KEY, PAINEL_SECRET e PAINEL_SENHA_DEMO
pip install -r requirements.txt
uvicorn app.main:app --reload
# abra http://localhost:8000/painel/
```

Detalhes em [guia-do-painel.md](guia-do-painel.md).

## Princípios

1. **Dados fictícios** — nenhum dado real de pessoa no repositório.
2. **Chatbot somente leitura** — ele consulta, nunca altera.
3. **Mínimo necessário ao modelo** — CPF e telefone mascarados antes de sair do servidor.
4. **Rastreável** — toda conversa auditada em `chat_historico`.
5. **Segredos fora do Git** — chave da API, segredo do token e senha demo só no `.env`.
