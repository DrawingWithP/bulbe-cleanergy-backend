# Sistema de Gerenciamento — Bulbe Energia

Painel web interno para os funcionários da Bulbe. O funcionário faz login, vê as métricas da operação, busca clientes e abre a ficha completa de cada um. Também pode perguntar ao **assistente (Claude Haiku 5.5)** sobre qualquer cliente ou sobre o funcionamento do app.

Os dados vêm de um **banco fictício** (SQLite + SQLAlchemy). Ele junta o que o app da Bulbe já tem (faturas, instalação, indicações, notificações, atendimentos) com as funcionalidades criadas pela squad no front-end: jornada de ativação em 5 etapas, Clube Bulbe com cartas e cupons, simulador sem login, adesão pelo app e dicas.

Este sistema é independente do back-end do app (pasta [`../backend`](../backend)). A integração futura entre os dois será pelo banco de dados: quando o app gravar os dados reais, o painel e o chatbot passam a mostrá-los.

## Estrutura

| Pasta | O que tem |
|---|---|
| `app/main.py` | Ponto de entrada: rotas, montagem do `/painel`, inicialização do banco e tratamento de erros |
| `app/erros.py` | `ErroDeNegocio` no formato `{"error": {code, message, status}}` |
| `app/database/` | Modelos (17 tabelas), conexão, seed fictício determinístico e consultas somente leitura |
| `app/chatbot/` | Integração com a API da Anthropic (tool use), ferramentas, base de conhecimento e rota `/v1/painel/chat` |
| `app/painel/` | Autenticação do funcionário, rotas `/v1/painel/*` e a interface web (HTML/CSS/JS puro) |
| `docs/` | Contratos, levantamento de funcionalidades, arquitetura, dicionário de dados, guia do painel e LGPD |

## Como rodar

Todos os comandos são executados **dentro desta pasta** (`sistema-de-gerenciamento`).

1. Criar o ambiente virtual e instalar as dependências:

   ```bash
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Copiar `.env.example` para `.env` e preencher `ANTHROPIC_API_KEY` e `PAINEL_SECRET`.

3. Subir o servidor:

   ```bash
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
   ```

4. Abrir <http://localhost:8000/painel>. Os usuários de demonstração estão em [`docs/guia-do-painel.md`](docs/guia-do-painel.md); a senha é o valor de `PAINEL_SENHA_DEMO` no `.env`.

O banco é criado e populado automaticamente na primeira execução. Para recriá-lo (com o servidor parado):

```bash
.venv\Scripts\python.exe -m app.database.seed
```

Documentação completa em [`docs/README.md`](docs/README.md).
