# Guia do painel de gestão e do chatbot

> Público: funcionários da Bulbe (atendimento e administração) e quem for rodar a demonstração.
> Todos os clientes do banco são **fictícios**. Este guia descreve a **v2** do sistema.

## 1. Pré-requisitos

- Python 3.12 ou superior.
- Uma chave da API da Anthropic (só é necessária para o chatbot; o resto do painel funciona sem ela).
- Opcional: uma conta de e-mail com SMTP (por exemplo, Gmail com senha de app) para o alerta de tentativas de login.
- Rodar os comandos **dentro da pasta `sistema-de-gerenciamento/`**, porque os imports são absolutos a partir de `app`.

## 2. Configurar o `.env`

Copie o modelo e preencha os valores:

```bash
cp .env.example .env          # no Windows (PowerShell): Copy-Item .env.example .env
```

### 2.1 Chatbot, banco e login

| Variável | Obrigatória? | Padrão | Para que serve |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Só para o chatbot | — | Chave da API da Anthropic. Sem ela, o chat responde `503 CHATBOT_INDISPONIVEL` e o restante do painel segue funcionando. |
| `CHATBOT_MODELO` | Não | `claude-haiku-5-5` | Modelo usado pelo chatbot (Claude Haiku 5.5). |
| `CHATBOT_ESFORCO` | Não | `high` | Nível de esforço (`output_config.effort`): `low`, `medium`, `high`, `xhigh` ou `max`. Mais esforço = respostas mais cuidadosas, porém mais lentas e caras. |
| `CHATBOT_TIMEOUT` | Não | `60` | Tempo máximo, em segundos, de cada chamada à API da Anthropic. |
| `BULBE_DB_URL` | Não | SQLite em `app/database/bulbe_ficticio.db` | URL do banco no formato SQLAlchemy, para usar outro arquivo ou outro banco. |
| `PAINEL_SECRET` | Sim (em qualquer ambiente compartilhado) | segredo **público** de desenvolvimento, com aviso no log | Segredo que assina os tokens de login (HMAC-SHA256). Use um texto longo e aleatório, por exemplo gerado com `python -c "import secrets; print(secrets.token_hex(32))"`. Trocar o valor desloga todo mundo. |
| `PAINEL_SENHA_DEMO` | Não | definido em `app/database/seed.py` | Senha dos 3 funcionários de demonstração criados pelo seed. Defina a sua **antes** de criar o banco (ou recrie o banco depois de mudá-la). |

### 2.2 Novas na v2: conversas e custo do chatbot

Todas opcionais; os padrões já servem para o Claude Haiku 5.5.

| Variável | Padrão | Para que serve |
|---|---|---|
| `CHATBOT_MAX_MENSAGENS_CONVERSA` | `200` | Tamanho máximo de uma conversa guardada no servidor (mensagens da API). Acima disso o chat pede para abrir uma nova conversa. |
| `CHATBOT_PRECO_ENTRADA_MTOK` | `0.10` | Preço, em US$ por milhão de tokens de entrada, usado no custo estimado. |
| `CHATBOT_PRECO_SAIDA_MTOK` | `0.50` | Preço, em US$ por milhão de tokens de saída. |
| `CHATBOT_FATOR_CACHE_LEITURA` | `0.1` | Multiplicador do preço de entrada para tokens lidos do cache. |
| `CHATBOT_FATOR_CACHE_ESCRITA` | `1.25` | Multiplicador do preço de entrada para tokens gravados no cache. |
| `CHATBOT_LIMITE_PROMPT_LONGO` | `100000` | Acima desse número de tokens de entrada numa chamada, vale a tabela de prompt longo. |
| `CHATBOT_PRECO_ENTRADA_LONGO_MTOK` | `0.50` | Preço de entrada da tabela de prompt longo. |
| `CHATBOT_PRECO_SAIDA_LONGO_MTOK` | `2.50` | Preço de saída da tabela de prompt longo. |

### 2.3 Novas na v2: retenção e segurança do login

| Variável | Padrão | Para que serve |
|---|---|---|
| `CHAT_RETENCAO_DIAS` | `180` | Conversas e registros do chatbot mais antigos que isso são apagados (ao subir o servidor e no expurgo manual). |
| `AUDITORIA_RETENCAO_DIAS` | `730` | Registros de `auditoria_acessos` mais antigos que isso são apagados. |
| `LOGIN_ALERTA_APOS_FALHAS` | `3` | Quando um e-mail **passa** desse número de senhas erradas na janela (na 4ª, com o padrão), um alerta é enviado por e-mail. |
| `LOGIN_BLOQUEIO_APOS_FALHAS` | `5` | Com esse número de falhas na janela, o login daquele e-mail fica bloqueado (`429`) até a janela passar. |
| `LOGIN_JANELA_MINUTOS` | `15` | Tamanho da janela de contagem das falhas, em minutos. |

### 2.4 Novas na v2: e-mail de alerta (SMTP)

| Variável | Padrão | Para que serve |
|---|---|---|
| `ALERTA_LOGIN_EMAIL` | — | **Destino** do alerta: o endereço que recebe o aviso de tentativas de login erradas (ex.: o e-mail do responsável pela segurança). |
| `SMTP_HOST` | — | Servidor de envio. Para Gmail: `smtp.gmail.com`. Vazio = alerta desligado (só log e auditoria). |
| `SMTP_PORTA` | `587` | Porta do servidor (587 com STARTTLS). |
| `SMTP_USUARIO` | — | Usuário da conta que envia (no Gmail, o endereço completo da conta). |
| `SMTP_SENHA` | — | Senha de autenticação SMTP. No Gmail, uma **senha de app** (veja abaixo), nunca a senha normal da conta. |
| `SMTP_REMETENTE` | `SMTP_USUARIO` | Endereço que aparece como remetente (no Gmail, normalmente o mesmo de `SMTP_USUARIO`). |
| `SMTP_TLS` | `true` | Usa STARTTLS na conexão. Mantenha `true`. (Conexão SMTPS direta na porta 465 não é suportada.) |

**Como criar a senha de app do Gmail para `SMTP_SENHA`:**

1. Entre na conta Google que vai **enviar** os alertas.
2. Abra **Conta Google > Segurança > Verificação em duas etapas** e ative-a, se ainda não estiver ativa
   (a opção de senha de app só aparece com a verificação em duas etapas ligada).
3. Dentro de **Verificação em duas etapas**, vá até **Senhas de app**.
4. Dê um nome para identificar o uso (por exemplo, "Painel Bulbe") e clique em **Criar**.
5. O Google mostra uma senha de 16 caracteres **uma única vez**. Copie-a direto para `SMTP_SENHA` no `.env`
   (sem espaços). Ela não deve ser escrita em nenhum outro lugar.
6. Preencha `SMTP_HOST=smtp.gmail.com`, `SMTP_PORTA=587`, `SMTP_TLS=true`, `SMTP_USUARIO` e `SMTP_REMETENTE` com o
   endereço da conta, e `ALERTA_LOGIN_EMAIL` com quem deve **receber** o alerta (pode ser outro endereço).
7. Reinicie o servidor. Para revogar, apague a senha de app na mesma tela; o alerta para de sair e o login continua funcionando.

> **Nunca** commite o `.env` nem cole a chave da API, o segredo do token ou a senha de app em código, issue,
> documentação ou chat. O `.gitignore` do projeto ignora `.env` e `*.db`.

## 3. Instalar e rodar

Todos os comandos são executados dentro da pasta `sistema-de-gerenciamento/` (exemplos para Windows; no Linux/macOS
troque `.venv\Scripts\python.exe` por `.venv/bin/python`).

```bash
# 1. ambiente virtual
python -m venv .venv

# 2. dependências (fastapi, uvicorn, pydantic, sqlalchemy, anthropic, python-dotenv)
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. subir a API
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
```

- O `app/main.py` carrega o `.env` sozinho e, ao subir, cria as tabelas, popula o banco se ele estiver vazio e
  aplica a **retenção** (apaga chat e auditoria mais antigos que os prazos do `.env`).
- Painel: <http://localhost:8000/painel/> (`/painel` sem a barra redireciona para cá).
- Swagger da API: <http://localhost:8000/docs>.

### 3.1 Recriar o banco depois de atualizar para a v2

A v2 acrescentou tabelas e colunas e **não há migração de dados**. Ao subir, o sistema cria as tabelas novas e
acrescenta as colunas que faltarem num banco da v1 (com um aviso no log), então a API não quebra; mas esse banco
antigo fica sem os dados novos (bônus do Clube zerados, auditoria vazia, nenhum cliente "ativado nos últimos 30 dias").
Por isso, depois de atualizar o código, com o servidor **parado**:

```bash
.venv\Scripts\python.exe -m app.database.seed
```

O comando apaga e recria o banco fictício (o mesmo de `BULBE_DB_URL`) com os dados de demonstração da v2: os mesmos
totais e personagens da v1 (64 clientes, Marcos Andrade, Clara Ribeiro), bônus do Clube nas faturas, 3 clientes
ativados nos últimos 30 dias, 1 ativação atrasada e cerca de 125 registros de auditoria de exemplo (todos com pelo
menos 2 dias, para não bloquearem nenhum login). O chat começa vazio. Como a ordem dos sorteios mudou, os dados
individuais dos demais clientes não são os mesmos da v1. Use o mesmo comando sempre que mudar `PAINEL_SENHA_DEMO`
ou quiser voltar aos dados originais.

### 3.2 Rodar os testes

```bash
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest
```

Os testes usam um banco SQLite **temporário** (o banco real não é tocado), não chamam a API da Anthropic e não
enviam e-mail. Detalhes em [testes.md](testes.md).

## 4. Usuários de demonstração

| E-mail | Perfil | Observação |
|---|---|---|
| `admin@bulbe.com.br` | `admin` | Acesso total, inclusive **Auditoria**, **Uso do assistente** e expurgo |
| `atendimento@bulbe.com.br` | `atendimento` | Perfil do atendimento |
| `ana.souza@bulbe.com.br` | `atendimento` | Funcionária fictícia |

A senha dos três é o valor de `PAINEL_SENHA_DEMO` no seu `.env` (a senha não é escrita neste guia).
O banco guarda apenas o **hash** dela.

## 5. Telas do painel

A interface é um app de uma página (`painel.html`) com menu lateral, a ficha do cliente e o chat sempre à direita.
As telas marcadas com **(v2)** são novas; as marcadas com **(admin)** só aparecem para o perfil `admin`.

| Tela | O que mostra | Rotas usadas |
|---|---|---|
| **Login** (`/painel/`) | E-mail e senha. O token fica em `sessionStorage` (some ao fechar a aba) e expira em 8 h. **v2:** depois de muitas tentativas erradas aparece "Muitas tentativas. Tente de novo em N minutos." | `POST /v1/painel/login` |
| **Visão geral** | Cards de clientes por status, economia total, faturas vencidas, indicações, Clube Bulbe (**v2:** com o total de bônus pagos), adesões, simulações e acesso ao app; barras de ativação por etapa (**v2:** a barra da etapa 5 mostra "Ativados (30 dias)"). | `GET /v1/painel/metricas` |
| **Clientes** | Busca por nome, e-mail, CPF, nº de instalação ou código de indicação, com filtros de status, cidade e (**v2**) etapa da ativação. **v2:** paginação real (anterior/próxima, "página X de Y", itens por página). | `GET /v1/painel/clientes` |
| **Ficha do cliente** (`#/cliente/<id>`) | Dados cadastrais e usina; jornada de ativação em 5 etapas; economia (**v2:** com total de bônus do Clube); Indique e Ganhe; faturas (**v2:** coluna de bônus do Clube); Clube e cartas; cupons; notificações; atendimentos. Botão "Perguntar ao assistente sobre este cliente". **v2:** cada abertura fica registrada na auditoria. | `GET /v1/painel/clientes/{id}` |
| **Ativações** (v2) | Resumo da jornada (em ativação, por etapa, dias médios na etapa, atrasados há mais de 90 dias, ativados nos últimos 30 dias, tempo médio) e lista de **clientes parados**, com filtros de etapa e de dias mínimos parados. | `GET /v1/painel/ativacoes/resumo`, `GET /v1/painel/clientes/parados` |
| **Adesões** | Filtro de situação e link para a ficha quando já virou cliente. **v2:** paginada. | `GET /v1/painel/adesoes` |
| **Atendimentos** | Filtro de status, nome do cliente e link para a ficha. **v2:** paginada. | `GET /v1/painel/atendimentos` |
| **Dicas** (v2) | Dicas de economia com valor mensal e anual. | `GET /v1/painel/dicas` |
| **Usinas** (v2) | Usinas, localização, capacidade, status e clientes ativos. | `GET /v1/painel/usinas` |
| **Parceiros** (v2) | Parceiros do Clube Bulbe e categoria. | `GET /v1/painel/parceiros` |
| **Auditoria** (v2, admin) | Registros de `auditoria_acessos` (quem, ação, recurso, IP, quando), com filtros por funcionário e ação e paginação. Consultar esta tela também fica registrado (`ver_auditoria`). Botão **Expurgar dados antigos** (pede confirmação). | `GET /v1/painel/auditoria`, `POST /v1/painel/admin/expurgo` |
| **Uso do assistente** (v2, admin) | Perguntas, conversas, funcionários ativos, tokens, **custo estimado** total e por pergunta, ranking por funcionário, ferramentas mais usadas e série por dia, nos últimos 7, 30, 90 ou 365 dias. | `GET /v1/painel/uso-chatbot?dias=` |
| **Chat** (lateral, em todas as telas) | **v2:** a resposta aparece enquanto é escrita (streaming), com indicação do que o assistente está consultando e o custo estimado discreto ao final; botões **Nova conversa** e **Conversas anteriores** (reabre uma conversa). | `POST /v1/painel/chat/stream` (reserva: `POST /v1/painel/chat`), `GET /v1/painel/chat/conversas`, `GET /v1/painel/chat/conversas/{id}`, `GET /v1/painel/chat/sugestoes` |

As telas **Auditoria** e **Uso do assistente** ficam na seção **Gestão** do menu, visível só para `admin`; a API
também recusa essas rotas (403) para o perfil `atendimento`. O expurgo manual apaga na hora o que passou dos prazos
de retenção e mostra quantos registros saíram de cada tabela.

## 6. Como usar o chatbot

- Pergunte em português, como perguntaria a um colega. O assistente consulta o banco por meio de
  **19 ferramentas somente leitura** e responde com base nelas; se não achar o dado, diz que não encontrou
  e sugere refinar (nome completo, e-mail, CPF, nº de instalação, código de indicação ou cidade).
- Ele **não altera nada** (não muda etapa, não dá baixa em fatura, não cancela, não envia mensagem).
- CPF e telefone chegam ao modelo **mascarados** (ex.: `***.456.789-**`, `(31) *****-1234`). Para ver o dado completo, abra a ficha.
- **v2 — conversas:** cada conversa fica guardada no servidor, ligada ao seu usuário. Recarregar a página mantém a
  conversa atual (o identificador fica no `sessionStorage` da aba), e em **Conversas anteriores** dá para reabrir
  qualquer uma e continuar de onde parou. **Nova conversa** começa do zero (útil ao mudar de assunto ou de cliente, e
  deixa as respostas mais rápidas e baratas). Uma conversa aceita até 200 mensagens internas; passando disso, o chat
  pede uma nova conversa. Ninguém mais vê as suas conversas.
- **v2 — custo:** cada resposta mostra discretamente o custo estimado em dólares. Perguntas objetivas e conversas
  curtas custam menos; o administrador acompanha o total na tela **Uso do assistente**.
- Toda pergunta e resposta é registrada em `chat_historico` com o seu usuário, e as conversas antigas são apagadas
  depois de `CHAT_RETENCAO_DIAS` dias.

### 6.1 Sugestões que aparecem na interface

Vêm de `GET /v1/painel/chat/sugestoes` (`app/chatbot/controller.py`):

- Em que etapa da ativação está o Marcos Andrade?
- Quais clientes têm fatura vencida?
- Quais clientes estão parados há mais de 30 dias na mesma etapa da ativação? (v2)
- Como estão as ativações? Quantos clientes em cada etapa e quantos atrasados? (v2)
- Como funciona o Clube Bulbe?
- Quanto um cliente com conta de R$ 320 economiza em 12 meses indicando 2 amigos?
- Quantas adesões estão aguardando análise (situação enviada)?
- Quais atendimentos estão em aberto?
- Qual a diferença entre o que é responsabilidade da CEMIG e da Bulbe?
- Quais funcionalidades do app foram criadas pela squad Cleanergy?

### 6.2 Perguntas de exemplo

**Sobre clientes**

1. "Em que etapa da ativação está o Marcos Andrade e qual a previsão de conclusão?"
2. "Quem é o cliente com código de indicação MARCOS50 e quais indicações ele já fez?"
3. "Liste 5 clientes ativos de Contagem e diga quanto o primeiro já economizou com a Bulbe, somando desconto, indicações e bônus do Clube."
4. "Esse cliente tem alguma fatura vencida ou em aberto? De quais meses?"
5. "Como está a sequência do Clube Bulbe desse cliente e quais cupons ele tem ativos?"
6. "Esse cliente já fez o primeiro acesso ao app? Quando foi o último login?"
7. "Que notificações foram enviadas para ele recentemente e quais atendimentos ele abriu?"

**Sobre a operação**

8. "Quantos clientes estão em ativação hoje e como eles se distribuem pelas etapas?"
9. "Quais clientes estão parados na etapa 3 há mais de 30 dias? Algum já passou dos 90 dias?" (v2)
10. "Qual o tempo médio de ativação e quantos clientes foram ativados nos últimos 30 dias?" (v2)
11. "Quantas faturas estão vencidas, qual o valor total vencido e quais clientes estão há mais tempo em atraso?"
12. "Quais atendimentos estão abertos agora? Algum veio pela ouvidoria?"
13. "Quantas adesões estão como enviadas aguardando aprovação? E a da Clara Ribeiro, em que situação está?"
14. "Quais usinas estão em manutenção e quantos clientes ativos cada usina atende?"

**Sobre o funcionamento do app e do serviço**

15. "Como funciona a jornada de ativação de 5 etapas e por que pode levar até 90 dias?"
16. "Explique o Clube Bulbe: quando chega a carta, quanto tempo vale o cupom e como se ganha o bônus de R$ 50?"
17. "Um cliente com conta de R$ 300 que indicar 2 amigos economiza quanto em 12 meses? O desconto vale sobre a iluminação pública?"

> Dica: no seed, o Marcos Andrade está em ativação e **ainda não tem faturas**. Para perguntas de faturas e
> economia, use um cliente `ativo` (busque por cidade ou status).

## 7. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Login retorna 401 `CREDENCIAIS_INVALIDAS` | E-mail errado, senha diferente da `PAINEL_SENHA_DEMO` usada quando o banco foi criado, ou funcionário inativo | Confira o `.env`; se mudou a senha depois, recrie o banco com `python -m app.database.seed` |
| Login retorna 429 `LOGIN_BLOQUEADO` ("Muitas tentativas") | 5 senhas erradas do mesmo e-mail em 15 minutos | Espere o tempo indicado (cabeçalho `Retry-After`); nem a senha certa entra antes disso |
| O alerta de login não chega | SMTP não configurado, senha de app errada ou revogada, ou verificação em duas etapas desligada | Confira as variáveis `SMTP_*` e `ALERTA_LOGIN_EMAIL`; o motivo fica no log e na auditoria (ação `alerta_email`). Veja também a caixa de spam |
| Bônus do Clube zerados, auditoria vazia ou aviso no log sobre colunas acrescentadas | Banco criado pela v1 | Pare o servidor e rode `python -m app.database.seed` (seção 3.1) |
| Menu sem **Auditoria** e **Uso do assistente** / 403 `ACESSO_NEGADO` | Perfil `atendimento` | Essas telas são só para `admin` |
| Painel volta para o login sozinho | Token expirou (8 h) ou `PAINEL_SECRET` mudou (`TOKEN_INVALIDO`) | Faça login de novo |
| Chat avisa que o assistente está indisponível (503 `CHATBOT_INDISPONIVEL`) | `ANTHROPIC_API_KEY` ausente ou recusada, pacote `anthropic` não instalado, ou API sobrecarregada | Preencha a chave no `.env`, reinicie o servidor e tente de novo |
| A resposta não aparece aos poucos | Algum proxy ou antivírus segurando o stream | A interface cai para a rota sem streaming sozinha; a resposta chega inteira no fim |
| Conversa antiga não abre (404 `CONVERSA_NAO_ENCONTRADA`) | Ela foi apagada pela retenção ou é de outro usuário | Comece uma **Nova conversa** |
| 409 `CONVERSA_MUITO_LONGA` | A conversa passou de `CHATBOT_MAX_MENSAGENS_CONVERSA` mensagens | Comece uma **Nova conversa** |
| 429 `CHATBOT_LIMITE_REQUISICOES` | Limite de taxa da API da Anthropic | Aguarde alguns segundos e reenvie |
| 503 `CHATBOT_SEM_CONEXAO` | Sem acesso à internet / à API | Verifique a rede |
| Resposta diz que atingiu o limite de consultas | Mais de 8 voltas de ferramentas | Faça uma pergunta mais específica (nome completo, código ou id) |
| Dados "sumiram" | O arquivo `.db` foi apagado ou `BULBE_DB_URL` aponta para outro arquivo | Reinicie a API (o banco vazio é populado ao subir) ou rode o seed |
