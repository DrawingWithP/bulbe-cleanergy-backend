# Sistema de Gerenciamento — Bulbe Energia

Painel web interno para os funcionários da Bulbe. O funcionário faz login, vê as métricas da operação, busca clientes e abre a ficha completa de cada um. Também pode perguntar ao **assistente (Claude Haiku 5.5)** sobre qualquer cliente ou sobre o funcionamento do app.

Os dados vêm do **app da Bulbe** (pasta [`../backend`](../backend)), sincronizados a cada 30 segundos, e de um **banco fictício** (SQLite + SQLAlchemy) que completa o que só o painel tem: faturas, notificações, atendimentos e o histórico que alimenta métricas e o chatbot. Na ficha de um cliente do app, o funcionário também **altera a etapa de ativação**, que vai direto para o app.

**Versão 2:**
- **Chat:** respostas em streaming, conversas guardadas no servidor e ferramentas de gestão da ativação (clientes parados, resumo por etapa).
- **Login:** bloqueio após tentativas erradas e alerta por e-mail quando alguém erra a senha mais de 3 vezes.
- **Gestão (só admin):** auditoria de acesso às fichas, uso e custo do assistente e retenção de dados.
- **Telas:** Ativações, Dicas, Usinas e Parceiros, com paginação nas listas.
- **Testes:** suíte automatizada com `pytest`.

**Versão 3 — integração com o app:**
- **Sincronização app → painel:** clientes, ativação, Clube (cartas, cupons e ofensiva), indicações, simulações, adesões, parceiros, dicas e usinas, lidos do banco do app em modo somente leitura. Registros equivalentes (mesmo CPF/e-mail, mesmo nome) são vinculados, não duplicados.
- **Painel → app:** botão **Atualizar no app** na ficha muda a etapa de ativação pela API do app (auditado).
- **Interface:** selo **App** nos clientes do app, estado da integração na visão geral e botão **Sincronizar com o app** para o admin.

Detalhes em [`docs/integracao-com-o-app.md`](docs/integracao-com-o-app.md). O sistema continua rodando sozinho: sem o banco do app (ou com `INTEGRACAO_APP_DB_URL` vazia) ele usa só o banco fictício.

## Estrutura

| Pasta | O que tem |
|---|---|
| `app/main.py` | Ponto de entrada: rotas, montagem do `/painel`, inicialização do banco e tratamento de erros |
| `app/erros.py` | `ErroDeNegocio` no formato `{"error": {code, message, status}}` |
| `app/database/` | Modelos (20 tabelas), conexão, seed fictício determinístico, consultas, conversas do chat, auditoria e retenção |
| `app/integracao/` | Sincronização com o banco do app e cliente da API do app (alterar etapa de ativação) |
| `app/chatbot/` | Integração com a API da Anthropic (tool use e streaming), 19 ferramentas, base de conhecimento, conversas e custo; avaliações em `app/chatbot/avaliacoes/` |
| `app/painel/` | Autenticação, bloqueio e alerta de login (`alertas.py`), rotas `/v1/painel/*` (inclui `/integracao`, `/admin/sincronizar` e `PATCH /clientes/{id}/ativacao`) e a interface web (HTML/CSS/JS puro) |
| `app/chatbot/` (rotas) | `/v1/painel/chat`, `/chat/stream`, `/chat/conversas` e `/chat/sugestoes` |
| `tests/` | Testes automatizados (`pytest`) de todo o sistema |
| `docs/` | Contratos, levantamento de funcionalidades, arquitetura, dicionário de dados, guia do painel e LGPD |

## Como rodar

O jeito mais simples é subir **tudo junto** pela raiz do repositório (app + painel): `python iniciar.py` (veja o [README da raiz](../README.md#como-executar-o-projeto)). O painel fica em <http://127.0.0.1:8001/painel/>.

Para rodar só o painel, todos os comandos são executados **dentro desta pasta** (`sistema-de-gerenciamento`).

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

4. Abrir <http://localhost:8000/painel>. Os usuários de demonstração estão em [`docs/guia-do-painel.md`](docs/guia-do-painel.md); a senha é o valor de `PAINEL_SENHA_DEMO` no `.env` (vazio = senha padrão do seed).

   Rodando só o painel na porta 8000, aponte a API do app para outro endereço (`INTEGRACAO_APP_API_URL`) ou desligue a integração (`INTEGRACAO_APP_DB_URL=` vazio).

O banco é criado e populado automaticamente na primeira execução. Quem já tinha o banco da versão 1 ou 2 deve recriá-lo, com o servidor parado:

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
