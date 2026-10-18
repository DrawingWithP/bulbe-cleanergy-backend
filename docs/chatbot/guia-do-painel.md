# Guia do painel de gestão e do chatbot

> Público: funcionários da Bulbe (atendimento e administração) e quem for rodar a demonstração.
> Todos os clientes do banco são **fictícios**.

## 1. Pré-requisitos

- Python 3.12 ou superior.
- Uma chave da API da Anthropic (só é necessária para o chatbot; o resto do painel funciona sem ela).
- Rodar os comandos **a partir da raiz do repositório** (`bulbe-cleanergy-backend/`), porque os imports são absolutos a partir de `app`.

## 2. Configurar o `.env`

Copie o modelo e preencha os valores:

```bash
cp .env.example .env
```

| Variável | Obrigatória? | Padrão | Para que serve |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Só para o chatbot | — | Chave da API da Anthropic. Sem ela, `POST /v1/painel/chat` responde `503 CHATBOT_INDISPONIVEL` e o restante do painel segue funcionando. |
| `CHATBOT_MODELO` | Não | `claude-haiku-5-5` | Modelo usado pelo chatbot (Claude Haiku 5.5). |
| `CHATBOT_ESFORCO` | Não | `low` | Nível de esforço (`output_config.effort`): `low`, `medium`, `high`, `xhigh` ou `max`. Mais esforço = respostas mais cuidadosas, porém mais lentas e caras. |
| `CHATBOT_TIMEOUT` | Não | `60` | Tempo máximo, em segundos, de cada chamada à API da Anthropic (o SDK ainda tenta de novo até 2 vezes). |
| `BULBE_DB_URL` | Não | SQLite em `app/database/bulbe_ficticio.db` (caminho absoluto, funciona com espaços e acentos na pasta) | URL do banco no formato SQLAlchemy, para usar outro arquivo ou outro banco. |
| `PAINEL_SECRET` | Sim (em qualquer ambiente compartilhado) | segredo **público** de desenvolvimento, com aviso no log | Segredo usado para assinar os tokens de login (HMAC-SHA256). Use um texto longo e aleatório, por exemplo gerado com `python -c "import secrets; print(secrets.token_hex(32))"`. Trocar o valor desloga todo mundo. |
| `PAINEL_SENHA_DEMO` | Não | definido em `app/database/seed.py` | Senha dos 3 funcionários de demonstração criados pelo seed. Defina a sua **antes** de o banco ser criado (ou recrie o banco depois de mudá-la). |

> **Nunca** commite o arquivo `.env` nem cole a chave da API em código, issue ou chat.
> O `.gitignore` do projeto ignora `.env` e `*.db`.

## 3. Instalar e rodar

> Para a squad: estes passos só devem ser executados quando o líder liberar (durante o desenvolvimento
> em paralelo os agentes não instalam dependências nem sobem o servidor).

```bash
# 1. (opcional) ambiente virtual
python -m venv .venv
# Windows: .venv\Scripts\activate    |   Linux/macOS: source .venv/bin/activate

# 2. dependências (fastapi, uvicorn, pydantic, sqlalchemy, anthropic, python-dotenv)
pip install -r app/requirements.txt

# 3. (opcional) recriar o banco fictício do zero
python -m app.database.seed

# 4. subir a API
uvicorn app.main:app --reload
```

- O `app/main.py` carrega o `.env` sozinho (se o `python-dotenv` estiver instalado) e, no *lifespan* da aplicação,
  `inicializar_banco()` cria as tabelas e popula o banco se ele estiver vazio — o passo 3 só é
  necessário para **recriar** os dados.
- Painel: <http://localhost:8000/painel/> (`/painel` sem a barra redireciona para cá)
- Swagger da API: <http://localhost:8000/docs>

## 4. Usuários de demonstração

| E-mail | Perfil | Observação |
|---|---|---|
| `admin@bulbe.com.br` | `admin` | Acesso total ao painel |
| `atendimento@bulbe.com.br` | `atendimento` | Perfil do atendimento |
| `ana.souza@bulbe.com.br` | `atendimento` | Funcionária fictícia |

A senha dos três é o valor de `PAINEL_SENHA_DEMO` no seu `.env` (a senha não é escrita neste guia).
O banco guarda apenas o **hash** dela.

## 5. Telas do painel

A interface é um app de uma página (`painel.html`) com menu lateral (**Visão geral**, **Clientes**, **Adesões**,
**Atendimentos**), a ficha do cliente e o chat sempre à direita.

| Tela | O que mostra | Rotas usadas |
|---|---|---|
| **Login** (`/painel/`, arquivo `index.html`) | E-mail e senha do funcionário. O token fica em `sessionStorage` (some ao fechar a aba) e expira em 8 h; com token inválido o painel volta ao login com aviso de sessão expirada. | `POST /v1/painel/login` |
| **Visão geral** | Cards de clientes por status, economia total gerada, faturas vencidas e valor vencido, indicações, Clube Bulbe (sequências e cupons), adesões por situação, simulações dos últimos 30 dias e acesso ao app; barras de **ativação por etapa**; listas de usinas e parceiros. Botão para atualizar as métricas. | `GET /v1/painel/metricas`, `/usinas`, `/parceiros` |
| **Clientes** | Busca por nome, e-mail, CPF, nº de instalação ou código de indicação (ignora maiúsculas e acentos), com filtros de status, cidade e quantidade. Clique no nome para abrir a ficha. | `GET /v1/painel/clientes` |
| **Ficha do cliente** (`#/cliente/<id>`) | Dados cadastrais e usina; **jornada de ativação em 5 etapas** (cartão "Etapa X de 5", círculos e linha do tempo, no estilo das telas Status/Detalhes do app); economia; Indique e Ganhe; faturas; Clube Bulbe e cartas; cupons; notificações; atendimentos. Botão **"Perguntar ao assistente sobre este cliente"**, que preenche o chat com o nome e o id. | `GET /v1/painel/clientes/{id}` |
| **Adesões** | Tabela com filtro de situação (`rascunho`, `enviada`, `aprovada`, `recusada`) e link para a ficha quando já virou cliente. | `GET /v1/painel/adesoes` |
| **Atendimentos** | Tabela com filtro de status (`aberto`, `em_andamento`, `resolvido`), nome do cliente e link para a ficha. | `GET /v1/painel/atendimentos` |
| **Chat** (lateral, em todas as telas) | Sugestões em botões, histórico da conversa, indicador "digitando...", ferramentas consultadas sob cada resposta, botão para limpar a conversa. Recolhível; em telas de até 1200 px vira gaveta. Enter envia, Shift+Enter quebra linha, limite de 2000 caracteres. | `POST /v1/painel/chat`, `GET /v1/painel/chat/sugestoes` |

> As rotas `GET /v1/painel/dicas` e `/parceiros?apenas_ativos=false` existem na API (e o chatbot as usa), mas não têm
> tela própria nesta versão.

## 6. Como usar o chatbot

- Pergunte em português, como perguntaria a um colega. O assistente consulta o banco por meio de
  **17 ferramentas somente leitura** e responde com base nelas; se não achar o dado, ele diz que não encontrou
  e sugere refinar (nome completo, e-mail, CPF, nº de instalação, código de indicação ou cidade).
- Para perguntas sobre uma pessoa, ele primeiro busca o cliente e depois consulta os detalhes. Se houver
  vários nomes parecidos, ele lista e pergunta qual é o certo.
- Ele **não altera nada** (não muda etapa, não dá baixa em fatura, não cancela, não envia mensagem). Se você pedir,
  ele explica que o chat é somente leitura e indica o caminho certo.
- CPF e telefone chegam ao modelo **mascarados** (ex.: `***.456.789-**`, `(31) *****-1234`). Para ver o dado completo, abra a ficha do cliente.
- O histórico fica **só na memória da página** e é reenviado a cada pergunta (últimas 20 mensagens). Ao recarregar a página, a conversa recomeça.
- Toda pergunta e resposta é registrada em `chat_historico` com o seu usuário (auditoria).

### 6.1 Sugestões que aparecem na interface

Vêm de `GET /v1/painel/chat/sugestoes` (`app/chatbot/controller.py`):

- Em que etapa da ativação está o Marcos Andrade?
- Quais clientes têm fatura vencida?
- Como funciona o Clube Bulbe?
- Quanto um cliente com conta de R$ 320 economiza em 12 meses indicando 2 amigos?
- Quantas adesões estão aguardando análise (situação enviada)?
- Quais atendimentos estão em aberto?
- Qual a diferença entre o que é responsabilidade da CEMIG e da Bulbe?
- Quais funcionalidades do app foram criadas pela squad Cleanergy?

### 6.2 Quinze perguntas de exemplo

**Sobre clientes**

1. "Em que etapa da ativação está o Marcos Andrade e qual a previsão de conclusão?"
2. "Quem é o cliente com código de indicação MARCOS50 e quais indicações ele já fez?"
3. "Liste 5 clientes ativos de Contagem e diga quanto o primeiro já economizou com a Bulbe, somando desconto e bônus de indicação."
4. "Esse cliente tem alguma fatura vencida ou em aberto? De quais meses?"
5. "Como está a sequência do Clube Bulbe desse cliente e quais cupons ele tem ativos?"
6. "Esse cliente já fez o primeiro acesso ao app? Quando foi o último login?"
7. "Que notificações foram enviadas para ele recentemente e quais atendimentos ele abriu?"

**Sobre a operação**

8. "Quantos clientes estão em ativação hoje e como eles se distribuem pelas etapas?"
9. "Quantas faturas estão vencidas, qual o valor total vencido e quais clientes estão há mais tempo em atraso?"
10. "Quais atendimentos estão abertos agora? Algum veio pela ouvidoria?"
11. "Quantas adesões estão como enviadas aguardando aprovação? E a da Clara Ribeiro, em que situação está?"
12. "Quais usinas estão em manutenção e quantos clientes ativos cada usina atende?"

**Sobre o funcionamento do app e do serviço**

13. "Como funciona a jornada de ativação de 5 etapas e por que pode levar até 90 dias?"
14. "Explique o Clube Bulbe: quando chega a carta, quanto tempo vale o cupom e como se ganha o bônus de R$ 50?"
15. "Um cliente com conta de R$ 300 que indicar 2 amigos economiza quanto em 12 meses? O desconto vale sobre a iluminação pública?"

> Dica: no seed, o Marcos Andrade está em ativação e **ainda não tem faturas**. Para perguntas de faturas e
> economia, use um cliente `ativo` (busque por cidade ou status).

## 7. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Login retorna 401 `CREDENCIAIS_INVALIDAS` | E-mail errado, senha diferente da `PAINEL_SENHA_DEMO` usada quando o banco foi criado, ou funcionário inativo | Confira o `.env`; se mudou a senha depois, recrie o banco com `python -m app.database.seed` |
| Painel volta para o login sozinho | Token expirou (8 h) ou `PAINEL_SECRET` mudou (`TOKEN_INVALIDO`) | Faça login de novo |
| Chat avisa que o assistente está indisponível (503 `CHATBOT_INDISPONIVEL`) | `ANTHROPIC_API_KEY` ausente ou recusada, pacote `anthropic` não instalado, ou API sobrecarregada | Preencha a chave no `.env`, reinicie o `uvicorn` e tente de novo |
| 429 `CHATBOT_LIMITE_REQUISICOES` | Limite de taxa da API da Anthropic | Aguarde alguns segundos e reenvie |
| 503 `CHATBOT_SEM_CONEXAO` | Sem acesso à internet / à API | Verifique a rede |
| Resposta diz que atingiu o limite de consultas | Mais de 8 voltas de ferramentas | Faça uma pergunta mais específica (nome completo, código ou id) |
| Dados "sumiram" | O arquivo `.db` foi apagado ou `BULBE_DB_URL` aponta para outro arquivo | Reinicie a API (o banco vazio é populado no startup) ou rode o seed |
