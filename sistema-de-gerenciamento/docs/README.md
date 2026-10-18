# Painel de Gestão + Chatbot — Bulbe Energia (squad Cleanergy)

Painel web **interno** para funcionários da Bulbe Energia (energia solar por assinatura em Minas Gerais)
consultarem clientes e a operação, com um **chatbot** (Claude Haiku 5.5, modelo `claude-haiku-5-5`, via
*tool use*) que responde perguntas sobre clientes e sobre o funcionamento do app — tudo apoiado num
**banco de dados fictício** (SQLite + SQLAlchemy 2).

- Branches: `feat/python-adiciona-chatbot` (v1) e `feat/python-melhorias-sistema` (v2)
- Disciplina: Projeto Ciência de Dados II — Ibmec, 2º semestre de 2026
- Front-end do cliente (Projeto I): repositório `Bulbe-Squad-cleanergy`

## Por que um painel com chatbot?

As demandas levantadas com a Bulbe (D-01 a D-06) mostram que o cliente não entende o serviço, não confia antes
do desconto chegar e pergunta o tempo todo "já estou ativo?". O front da squad ataca isso do lado do cliente
(home aberta, simulador, jornada de ativação, Clube Bulbe). O painel ataca do lado da Bulbe: o atendente
encontra o cliente, vê a etapa da ativação, as faturas e o engajamento em segundos — ou simplesmente pergunta ao chatbot.

## O que a v2 acrescentou

| Área | Novidades |
|---|---|
| **Chatbot** | Resposta em **streaming** (SSE) que aparece enquanto é escrita; **conversas guardadas no servidor**, com histórico só de acréscimo e lista de conversas anteriores; 2 ferramentas novas (`listar_clientes_parados`, `resumo_ativacoes`) e filtro por etapa; **tokens e custo estimado** registrados por pergunta; casos de avaliação com o modelo real |
| **Segurança** | **Bloqueio** do login após 5 falhas em 15 minutos (`429`); **alerta por e-mail** na 4ª falha, enviado para `ALERTA_LOGIN_EMAIL` via SMTP; **auditoria de acesso** em tabela própria (logins, fichas abertas, consultas à auditoria, expurgos); rotas exclusivas de admin |
| **LGPD** | **Retenção** configurável (`CHAT_RETENCAO_DIAS`, `AUDITORIA_RETENCAO_DIAS`) com expurgo ao subir o servidor e por rota de admin |
| **Painel** | Paginação real; telas **Ativações** (resumo e clientes parados), **Dicas**, **Usinas** e **Parceiros**; para admin, **Auditoria** e **Uso do assistente** (custo por período, por funcionário, por dia) |
| **Dados** | Tabelas `chat_conversas`, `chat_mensagens` e `auditoria_acessos`; bônus de R$ 50 do Clube Bulbe nas faturas (`bonus_clube`); colunas de uso e custo em `chat_historico`; a etapa 5 das métricas passa a contar os ativados nos últimos 30 dias |
| **Qualidade** | Suíte **pytest** isolada (banco temporário, Anthropic e SMTP simulados) |

> Depois de atualizar para a v2, o banco local precisa ser **recriado** (`python -m app.database.seed`),
> porque há tabelas e colunas novas e não há migração. Ver [guia-do-painel.md](guia-do-painel.md#31-recriar-o-banco-depois-de-atualizar-para-a-v2).

## O que foi entregue

| Pacote | Conteúdo |
|---|---|
| `app/database/` | `modelos.py` (20 tabelas), `conexao.py`, `seed.py` (64 clientes fictícios, semente 42), `consultas.py` (leitura, paginação, conversas, uso/custo, auditoria e expurgo), `seguranca.py` (PBKDF2) |
| `app/painel/` | `auth.py` (token HMAC de 8 h, `exigir_admin`), `alertas.py` (alerta de login por SMTP), `controller.py` (rotas `/v1/painel/*`), `static/` (login `index.html` + `login.js`; app `painel.html` + `painel.css` + `painel.js`) |
| `app/chatbot/` | `servico.py` (loop de *tool use* com streaming, conversas e custo), `ferramentas.py` (19 ferramentas somente leitura + mascaramento de CPF/telefone), `prompts.py`, `base_conhecimento.py`, `config.py` (inclui os preços para o custo), `controller.py` (rotas `/v1/painel/chat*`), `avaliacoes/` |
| `tests/` | Suíte `pytest` de todo o sistema |
| `docs/` | Esta documentação |

Tudo fica na pasta `sistema-de-gerenciamento/`, separada do back-end do app (`backend/`): o sistema tem o próprio
`app/main.py` (carga do `.env`, routers, montagem de `/painel`, `inicializar_banco()` e retenção no *lifespan*,
*handlers* de erro no formato `{"error": {...}}`), o próprio `app/erros.py`, `requirements.txt`,
`requirements-dev.txt`, `pytest.ini` e `.env.example`.

## Índice da documentação

| Documento | Conteúdo |
|---|---|
| [CONTRATOS.md](CONTRATOS.md) | Contrato entre as pastas (interfaces, rotas, tabelas) da v1 |
| [CONTRATOS-MELHORIAS.md](CONTRATOS-MELHORIAS.md) | Contrato das melhorias da v2 (complementa o anterior) |
| [levantamento-funcionalidades.md](levantamento-funcionalidades.md) | O que o app/site da Bulbe já tem × o que a squad criou, com demandas, US e onde aparece no banco/painel |
| [arquitetura.md](arquitetura.md) | Camadas, streaming SSE, conversas no servidor, uso e custo, login com bloqueio e alerta, auditoria, retenção, ferramentas, rotas e diagramas PlantUML |
| [dicionario-de-dados.md](dicionario-de-dados.md) | Todas as tabelas e campos (inclusive os da v2) com tipo, descrição e origem, e diagrama ER |
| [guia-do-painel.md](guia-do-painel.md) | `.env` (inclusive SMTP e senha de app do Gmail), instalação, recriação do banco, testes, usuários demo, telas e perguntas de exemplo |
| [seguranca-e-lgpd.md](seguranca-e-lgpd.md) | Dados fictícios, mascaramento, somente leitura, PBKDF2, token HMAC, bloqueio, alerta, auditoria, retenção, custo do chatbot, *prompt injection*, próximos passos |
| [testes.md](testes.md) | Como a suíte `pytest` é organizada e isolada, o que cobre e como rodar; avaliação do chatbot com o modelo real |
| [CHANGELOG.md](CHANGELOG.md) | Histórico desta pasta |
| [PENDENCIAS.md](PENDENCIAS.md) | Lacunas e diferenças encontradas ao documentar a v2 |
| [NOTAS_PARA_O_LIDER.md](NOTAS_PARA_O_LIDER.md) | Dúvidas e inconsistências registradas na v1 |

## Começo rápido

```bash
cd sistema-de-gerenciamento
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env        # preencha ANTHROPIC_API_KEY, PAINEL_SECRET e, se quiser o alerta, as variáveis SMTP
.venv\Scripts\python.exe -m app.database.seed          # (re)cria o banco fictício
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
# abra http://localhost:8000/painel/
```

Testes: `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` e `.venv\Scripts\python.exe -m pytest`
(ver [testes.md](testes.md)). Detalhes de uso em [guia-do-painel.md](guia-do-painel.md).

## Princípios

1. **Dados fictícios** — nenhum dado real de pessoa no repositório.
2. **Chatbot somente leitura** — ele consulta, nunca altera.
3. **Mínimo necessário ao modelo** — CPF e telefone mascarados antes de sair do servidor.
4. **Rastreável** — toda conversa registrada em `chat_historico` e todo acesso sensível em `auditoria_acessos`.
5. **Guardado só pelo tempo necessário** — retenção com expurgo automático.
6. **Segredos fora do Git** — chave da API, segredo do token, senha demo e senha SMTP só no `.env`.
