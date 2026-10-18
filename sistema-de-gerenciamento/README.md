# Sistema de Gerenciamento — Bulbe Energia

Painel web interno para os funcionários da Bulbe. O funcionário faz login, vê as métricas da operação, busca clientes e abre a ficha completa de cada um. Também pode perguntar ao **assistente (Claude Haiku 5.5)** sobre qualquer cliente ou sobre o funcionamento do app.

Os dados vêm de um **banco fictício** (SQLite + SQLAlchemy). Ele junta o que o app da Bulbe já tem (faturas, instalação, indicações, notificações, atendimentos) com as funcionalidades criadas pela squad no front-end: jornada de ativação em 5 etapas, Clube Bulbe com cartas e cupons, simulador sem login, adesão pelo app e dicas.

**Versão 2:**
- **Chat:** respostas em streaming, conversas guardadas no servidor e ferramentas de gestão da ativação (clientes parados, resumo por etapa).
- **Login:** bloqueio após tentativas erradas e alerta por e-mail quando alguém erra a senha mais de 3 vezes.
- **Gestão (só admin):** auditoria de acesso às fichas, uso e custo do assistente e retenção de dados.
- **Telas:** Ativações, Dicas, Usinas e Parceiros, com paginação nas listas.
- **Testes:** suíte automatizada com `pytest`.

Este sistema é independente do back-end do app (pasta [`../backend`](../backend)). A integração futura entre os dois será pelo banco de dados: quando o app gravar os dados reais, o painel e o chatbot passam a mostrá-los.

## Estrutura

| Pasta | O que tem |
|---|---|
| `app/main.py` | Ponto de entrada: rotas, montagem do `/painel`, inicialização do banco e tratamento de erros |
| `app/erros.py` | `ErroDeNegocio` no formato `{"error": {code, message, status}}` |
| `app/database/` | Modelos (20 tabelas), conexão, seed fictício determinístico, consultas, conversas do chat, auditoria e retenção |
| `app/chatbot/` | Integração com a API da Anthropic (tool use e streaming), 19 ferramentas, base de conhecimento, conversas e custo; avaliações em `app/chatbot/avaliacoes/` |
| `app/painel/` | Autenticação, bloqueio e alerta de login (`alertas.py`), rotas `/v1/painel/*` e a interface web (HTML/CSS/JS puro) |
| `tests/` | Testes automatizados (`pytest`) de todo o sistema |
| `docs/` | Contratos, levantamento de funcionalidades, arquitetura, dicionário de dados, guia do painel e LGPD |

## Como rodar

Todos os comandos são executados **dentro desta pasta** (`sistema-de-gerenciamento`).

1. Criar o ambiente virtual e instalar as dependências:

   ```bash
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

2. Copiar `.env.example` para `.env` e preencher `ANTHROPIC_API_KEY` e `PAINEL_SECRET`. Para o alerta de login por e-mail, preencher também `ALERTA_LOGIN_EMAIL` e as variáveis `SMTP_*` (veja o [guia](docs/guia-do-painel.md)).

3. Subir o servidor:

   ```bash
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
   ```

4. Abrir <http://localhost:8000/painel>. Os usuários de demonstração estão em [`docs/guia-do-painel.md`](docs/guia-do-painel.md); a senha é o valor de `PAINEL_SENHA_DEMO` no `.env`.

O banco é criado e populado automaticamente na primeira execução. Quem já tinha o banco da versão 1 deve recriá-lo, com o servidor parado:

```bash
.venv\Scripts\python.exe -m app.database.seed
```

Para rodar os testes (não usam a API da Anthropic nem enviam e-mail):

```bash
.venv\Scripts\python.exe -m pytest
```

Documentação completa em [`docs/README.md`](docs/README.md).

## Uso de IA no desenvolvimento

No desenvolvimento deste sistema foi utilizado um **agente de IA de programação** (Claude Code, da Anthropic) como ferramenta de apoio na escrita do código, da documentação e na revisão. A squad definiu os requisitos, as funcionalidades e as decisões de projeto, conduziu o agente e testou o resultado.

Isso é diferente do **chatbot do painel**, que é uma funcionalidade do próprio sistema: ele usa a API da Anthropic (modelo Claude Haiku 5.5) para responder às perguntas dos funcionários.
