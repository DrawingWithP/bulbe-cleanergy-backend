# Segurança e LGPD — painel de gestão e chatbot

> Escopo: o painel interno (`/painel`, `/v1/painel/*`), o chatbot (`/v1/painel/chat`) e o banco fictício.
> Base legal de referência: **Lei 13.709/2018 (LGPD)** — princípios de finalidade, necessidade,
> segurança, prevenção e responsabilização (art. 6º).
>
> **v2:** acrescentou bloqueio de login por tentativas, alerta por e-mail, auditoria de acesso em tabela própria
> (inclusive de cada ficha aberta), retenção com expurgo automático, conversas guardadas no servidor e
> acompanhamento do custo do chatbot (seções 6 a 11).

## 1. Dados fictícios

- O banco é gerado por `app/database/seed.py` com gerador determinístico (`random.Random(42)`), **sem dados reais**.
  Nomes, e-mails, CPFs (11 dígitos de formato válido, sem titular real), telefones e endereços são inventados.
- Os personagens das telas do front (ex.: Marcos Andrade, Clara Ribeiro) também são fictícios.
- O arquivo `.db` não é versionado (`*.db` no `.gitignore`); cada pessoa gera o seu localmente.
- **Antes de ligar o painel a dados reais da Bulbe**, os itens da seção 14 são obrigatórios.

## 2. Minimização: mascaramento antes do modelo

O painel mostra a ficha completa ao funcionário autenticado, mas o chatbot envia à API da Anthropic
**só o necessário**:

| Dado | Como chega ao modelo | Exemplo |
|---|---|---|
| CPF | Mascarado: só os dígitos do meio aparecem | `***.456.789-**` |
| Telefone | Mascarado: DDD e últimos dígitos | `(31) *****-1234` |
| Demais campos | Como estão no banco (nome, cidade, status, valores) | — |

O mascaramento acontece em `app/chatbot/ferramentas.py` (`mascarar_dados`, `mascarar_cpf`, `mascarar_telefone`),
depois da consulta e antes de montar o `tool_result`. Ele é recursivo e funciona por nome de campo (`cpf*`,
`telefone*`, `celular*`, `contato*` com cara de telefone) e, em textos livres (`descricao`, `observacao`, `mensagem`,
`assunto`, `titulo`), por expressão regular de CPF formatado e de telefone — assim um CPF digitado dentro da
descrição de um atendimento também sai mascarado.
As funções de `app/database/consultas.py` devolvem os dados sem máscara porque também servem ao painel.

## 3. Chatbot somente leitura

- As ferramentas expostas ao modelo mapeiam 1-para-1 em funções de **leitura** de `consultas.py`
  (buscar, obter, listar, métricas, simular). Nenhuma ferramenta altera, apaga ou envia nada.
- A única escrita do fluxo do chat é `registrar_chat(...)`, feita **pelo código** (não pelo modelo) para auditoria.
- O prompt de sistema reforça que o assistente é somente leitura, mas a garantia real é **estrutural**:
  mesmo que o modelo "quisesse", não existe ferramenta de escrita para ele chamar.
- O loop tem limite de **8 voltas** de ferramentas por pergunta, e cada consulta tem `limite` de linhas.

## 4. Senhas com PBKDF2

- `app/database/seguranca.py` usa apenas a biblioteca padrão: `hashlib.pbkdf2_hmac("sha256", ...)` com
  **salt aleatório de 16 bytes** por senha e **240.000 iterações**.
- Formato armazenado: `pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>` — o número de iterações viaja junto,
  permitindo aumentar o custo no futuro sem invalidar senhas antigas.
- A verificação usa `hmac.compare_digest` (comparação em tempo constante, evita *timing attack*). Um hash malformado
  devolve `False` em vez de quebrar.
- `autenticar_funcionario` gasta o mesmo tempo quando o e-mail **não existe** (verifica um hash fictício) e o login
  responde sempre a mesma mensagem genérica (`CREDENCIAIS_INVALIDAS`), para não revelar quais e-mails são válidos.
- A senha de demonstração vem de `PAINEL_SENHA_DEMO` e não aparece em documentação nem em código versionado.
  Atende ao requisito **RNF-01** ("usar hash ou salt para criptografar senhas") de `backend/docs/Lista_de_requisitos.md`.

## 5. Token assinado com HMAC e expiração

- Após o login, `app/painel/auth.py` emite um token `<payload>.<assinatura>` (ambos em base64url): o payload é um JSON com
  os dados mínimos do funcionário (`id`, `nome`, `email`, `perfil`), `iat` e `exp` (**8 horas**); a assinatura é
  **HMAC-SHA256** do payload com `PAINEL_SECRET`. Só biblioteca padrão (sem PyJWT).
- Sem `PAINEL_SECRET`, o painel usa um segredo de desenvolvimento **público** e registra um aviso no log —
  aceitável só na máquina do desenvolvedor.
- `validar_token` recalcula a assinatura, compara em tempo constante e rejeita tokens expirados, adulterados,
  malformados ou maiores que 4096 caracteres.
- Rotas protegidas usam a dependência `funcionario_logado` (`401` se inválido); rotas administrativas usam `exigir_admin` (`403`).
  Na v2, `exigir_admin` protege a auditoria (`/v1/painel/auditoria`), o uso do assistente (`/v1/painel/uso-chatbot`)
  e o expurgo (`/v1/painel/admin/expurgo`); a interface esconde essas telas do perfil `atendimento`, mas a proteção
  real é a do servidor.
- O front guarda o token em `sessionStorage` (apagado ao fechar a aba) e o envia em `Authorization: Bearer <token>`;
  qualquer 401 leva de volta ao login.
- Trocar `PAINEL_SECRET` invalida todos os tokens emitidos (útil em caso de vazamento).

## 6. Limite de tentativas e bloqueio do login

- Cada senha errada grava `login_falha` em `auditoria_acessos`, com o e-mail digitado e o IP.
- Antes de conferir a senha, o login conta as falhas recentes daquele e-mail (`contar_falhas_login`, sem diferenciar
  maiúsculas e minúsculas). Com **5 falhas em 15 minutos** (`LOGIN_BLOQUEIO_APOS_FALHAS`, `LOGIN_JANELA_MINUTOS`), a
  resposta passa a ser `429 LOGIN_BLOQUEADO` com o cabeçalho `Retry-After` (a janela inteira, 900 s com o padrão),
  **mesmo com a senha certa**, até a janela passar. A tentativa bloqueada também é registrada (`login_bloqueado`), e a
  senha nem chega a ser conferida.
- Isso reduz ataques de força bruta e de dicionário contra uma conta. A mensagem de senha errada continua genérica
  (`CREDENCIAIS_INVALIDAS`) e o bloqueio vale também para e-mails que não existem, para não revelar quais são válidos.
- Limite conhecido: o bloqueio é por e-mail, não por IP. Uma tentativa espalhada por muitos e-mails não é barrada
  (ver seção 14).

## 7. Alerta por e-mail

- Quando um e-mail passa de **3 falhas em 15 minutos** (`LOGIN_ALERTA_APOS_FALHAS`), ou seja, na 4ª, o sistema envia
  **um** e-mail de alerta para o endereço de `ALERTA_LOGIN_EMAIL`, no máximo um por e-mail tentado a cada 15 minutos
  (evita inundar a caixa durante um ataque).
- O alerta informa o e-mail tentado, quantas falhas, o IP e o horário. **Nunca** inclui a senha digitada: ela não é
  repassada ao módulo de alerta. Caracteres de controle são removidos dos valores digitados, o que impede injetar
  cabeçalhos ou linhas no e-mail.
- O limite de um alerta por janela é controlado em memória e conferido na auditoria (vale mesmo depois de um reinício
  do servidor). Com vários processos do servidor ao mesmo tempo, a conferência na auditoria reduz, mas não elimina, a
  chance de dois alertas simultâneos para o mesmo e-mail.
- O envio usa só a biblioteca padrão (`smtplib` + `email.message`, módulo `app/painel/alertas.py`), com STARTTLS na
  porta 587, e roda em segundo plano (`BackgroundTasks`): não atrasa a resposta do login nem revela ao atacante que um
  alerta saiu.
- Sem SMTP configurado ou com erro de envio, o login continua funcionando; o problema vai para o log e para a auditoria
  (ação `alerta_email` com o motivo no `detalhe`). O log e a auditoria registram só o tipo do erro, nunca a
  configuração SMTP (que inclui a senha).
- Credenciais do SMTP ficam só no `.env`. No Gmail, `SMTP_SENHA` deve ser uma **senha de app** (Conta Google >
  Segurança > Verificação em duas etapas > Senhas de app), que vale só para o envio, pode ser revogada a qualquer
  momento e não dá acesso à conta como a senha normal. Passo a passo em [guia-do-painel.md](guia-do-painel.md#24-novas-na-v2-e-mail-de-alerta-smtp).

## 8. Auditoria de acesso

A v2 criou a tabela **`auditoria_acessos`**, que responde **quem acessou o quê, quando e de onde** (princípio da
responsabilização, art. 6º, X):

| Ação | Quando é gravada |
|---|---|
| `login_ok` | Login bem-sucedido |
| `login_falha` | Senha ou e-mail errados (com o e-mail digitado; `funcionario_id` preenchido se o e-mail é de um funcionário, nulo se não existe) |
| `login_bloqueado` | Tentativa recusada pelo bloqueio |
| `alerta_email` | Alerta enviado ou falha ao enviar (com o motivo) |
| `ver_ficha` | Cada abertura da ficha completa de um cliente (`recurso_tipo = cliente`, `recurso_id` = id do cliente) |
| `ver_auditoria` | Cada consulta à própria auditoria (quem fiscaliza também é registrado) |
| `expurgo` | Cada execução do expurgo, com a contagem do que saiu |

- Todos os registros levam o IP da requisição (`request.client.host`) e a data. Atrás de um proxy reverso, o IP
  registrado será o do proxy, a menos que o servidor rode com `--proxy-headers` e `--forwarded-allow-ips`.
- O seed cria cerca de 125 registros fictícios de exemplo (com IPs de faixas privadas e de documentação), para a tela
  já ter conteúdo na demonstração.
- A leitura é **só para admin** (`GET /v1/painel/auditoria`, com filtros por funcionário e ação e paginação).
- A auditoria **nunca** guarda senha, token, chave ou conteúdo da ficha, só a referência ao que foi acessado.
- O chatbot continua registrado em `chat_historico` (seção 9); a ficha aberta pelo painel, que antes só ia para o log
  da aplicação, agora também fica na tabela.

## 9. Registro do chatbot e conversas no servidor

- Cada pergunta grava em `chat_historico`: `funcionario_id`, `pergunta`, `resposta`, `ferramentas_usadas`, a conversa,
  o modelo, os tokens, o custo estimado e a duração.
- Na v2 as conversas ficam **no servidor** (`chat_conversas` e `chat_mensagens`), ligadas ao funcionário que as
  criou. `obter_conversa` só devolve a conversa ao próprio dono; para qualquer outro funcionário ela "não existe" (404).
- O histórico é **só de acréscimo**: as mensagens guardadas são reenviadas ao modelo exatamente como foram geradas e
  nunca são editadas. Isso preserva a integridade do registro (o que está gravado é o que o modelo viu e respondeu).
- O conteúdo guardado é o mesmo que foi à API: dados de cliente vindos de ferramentas já estão com CPF e telefone
  **mascarados**. A pergunta digitada pelo funcionário, porém, é texto livre: a orientação é não colar dados
  sensíveis desnecessários.

## 10. Retenção e expurgo

| Dado | Prazo padrão | Variável |
|---|---|---|
| `chat_historico`, `chat_conversas`, `chat_mensagens` | 180 dias (a idade da conversa conta da última mensagem) | `CHAT_RETENCAO_DIAS` |
| `auditoria_acessos` | 730 dias (2 anos) | `AUDITORIA_RETENCAO_DIAS` |

- O expurgo (`expurgar_dados_antigos`) roda **ao subir o servidor** e **sob demanda** por um admin
  (`POST /v1/painel/admin/expurgo`), que recebe a contagem do que foi apagado; a execução fica registrada na auditoria.
- Atende aos princípios de **necessidade** e de **eliminação após o fim do tratamento** (LGPD, arts. 6º, III, e 16):
  conversas servem para o atendimento do dia a dia e não precisam ficar para sempre; a auditoria fica mais tempo
  porque serve para investigar incidentes.
- Os prazos são valores iniciais para a demonstração. Com dados reais, devem ser definidos com o DPO da Bulbe.
- O expurgo apaga do banco; cópias de segurança do arquivo `.db`, se existirem, precisam seguir a mesma política.

## 11. Custo do chatbot

- Cada resposta soma os tokens de todas as voltas (entrada, saída, leitura e escrita de cache) e calcula um
  **custo estimado em US$** com preços configuráveis em `app/chatbot/config.py` (referência do Claude Haiku 5.5:
  US$ 0,10 por milhão de tokens de entrada e US$ 0,50 por milhão de saída; leitura de cache a 0,1× e escrita a 1,25× o
  preço de entrada; tabela de prompt longo acima de 100 mil tokens de entrada). Os preços podem ser ajustados pelo `.env`.
- Se o navegador fechar a conexão no meio de uma resposta, a troca não é registrada; o custo dessa resposta parcial
  não aparece nas métricas (aparece só na cobrança da Anthropic).
- O admin acompanha na tela **Uso do assistente**: total do período, custo médio por pergunta, por funcionário, por dia
  e ferramentas mais usadas. Isso ajuda a detectar uso anormal (ex.: uma conta fazendo centenas de perguntas, o que
  pode indicar abuso ou token vazado) e a planejar o orçamento.
- Medidas que mantêm o custo baixo: modelo Haiku, cache de prompt (o prompt de sistema é idêntico em toda a conversa),
  limite de 8 voltas por pergunta, resultados de ferramentas com tamanho limitado, limite de tamanho da conversa
  (`CHATBOT_MAX_MENSAGENS_CONVERSA`) e o botão **Nova conversa**.
- O valor é uma estimativa; a cobrança oficial é a do console da Anthropic, onde também convém definir um limite de gasto.

## 12. Defesa contra *prompt injection*

Campos como `descricao` de atendimentos, `observacao` de eventos ou nomes de indicados são texto livre e
poderiam conter frases do tipo "ignore as instruções anteriores". As defesas adotadas:

1. **Resultados de ferramentas são dados, não instruções** — o prompt de sistema diz isso explicitamente e os
   resultados chegam ao modelo como `tool_result` em JSON, separados das mensagens do funcionário.
2. **Sem ferramentas perigosas** — não há escrita, envio de mensagens, acesso à web nem execução de código;
   o pior caso de uma injeção é uma resposta errada, não uma ação.
3. **Entrada validada** — `mensagem` com 1 a 2000 caracteres, `conversa_id` só do próprio funcionário e `historico` com no máximo 20 itens, papel
   `funcionario` ou `assistente` (Pydantic). O `input` das ferramentas é lido como dicionário e validado por
   `validar_entrada` (tipos, valores permitidos, limites, textos de até 200 caracteres); parâmetros desconhecidos
   são ignorados. O resultado de cada ferramenta é limitado a 40.000 caracteres.
4. **Saída tratada como texto** — a interface passa todo dado por `esc()` e escapa a resposta do chat antes de
   converter `**negrito**`, listas e quebras de linha, evitando XSS a partir de texto vindo do banco ou do modelo.
   Além disso, uma *Content Security Policy* por `<meta>` bloqueia scripts e estilos inline e de outros domínios
   (exceto Google Fonts); não há frameworks nem CDN de JavaScript.
5. **Histórico controlado pelo servidor** — na v2 o histórico de uma conversa vem do banco, não do navegador:
   um usuário não consegue forjar respostas anteriores do assistente nem injetar falsos resultados de ferramentas
   pelo corpo da requisição. O formato antigo (com `historico` de texto) continua aceito, só com papéis
   `funcionario`/`assistente` e texto. A data e o funcionário entram como contexto no início da pergunta, e o prompt
   de sistema não muda durante a conversa.
6. **Dados de clientes nunca entram no prompt fixo** — a base de conhecimento é estática; dado de cliente só
   chega ao modelo como resultado de ferramenta, já mascarado.

## 13. Chave da API e configuração

- `ANTHROPIC_API_KEY` fica **somente no `.env`** (ignorado pelo Git) ou em variável de ambiente do servidor.
  Nunca em código, `.env.example`, documentação, issue ou print de tela.
- A chave é lida do ambiente a cada chamada (`config.obter_chave_api()`), nunca registrada em log.
- Sem a chave (ou sem o pacote `anthropic`), o chatbot responde `503 CHATBOT_INDISPONIVEL` e o restante da API
  funciona normalmente.
- O mesmo vale para `PAINEL_SECRET`, `PAINEL_SENHA_DEMO` e `SMTP_SENHA`.
- Se uma chave vazar: revogar no console da Anthropic, gerar outra e atualizar o `.env`. Se a senha de app do
  SMTP vazar: apagá-la em Conta Google > Segurança > Verificação em duas etapas > Senhas de app e criar outra.

## 14. Limites conhecidos e próximos passos

| Limite atual | Próximo passo sugerido |
|---|---|
| Dados fictícios em SQLite local | Para dados reais: banco gerenciado com criptografia em repouso, backups e acesso por perfil |
| Dados de clientes enviados (mascarados) a um provedor externo de IA | Avaliar com o DPO da Bulbe a base legal, o contrato de tratamento de dados com o provedor, a política de retenção e o registro da operação (RIPD/DPIA) |
| Login com e-mail e senha; bloqueio só **por e-mail** (v2) | MFA e limite também por IP em `/v1/painel/login` |
| Alerta "uma vez por janela" controlado por processo; IP auditado é o de `request.client.host` | Em produção com vários processos ou atrás de proxy: controle do alerta só no banco e `--proxy-headers` no servidor |
| Token sem revogação individual | Lista de revogação ou sessões no servidor; *refresh token* curto |
| Perfil `atendimento` vê a ficha de qualquer cliente (as telas de admin já são restritas na v2) | Controle mais fino (ex.: atendimento vê só clientes da sua carteira) |
| Prazos de retenção definidos para a demonstração | Validar os prazos com o DPO; aplicar a mesma política a backups |
| Sem HTTPS na demonstração local | Em qualquer ambiente compartilhado, servir apenas por HTTPS e com CORS restrito |
| Perguntas ao chatbot gravadas em texto livre | Orientar funcionários a não colar dados sensíveis desnecessários; expurgo periódico (já automático na v2) |
| Custo do chatbot é estimado localmente | Conferir com o console da Anthropic e definir limite de gasto na organização |
| Chatbot pode errar ou interpretar mal | Exibir as ferramentas consultadas em cada resposta e orientar a conferir na ficha antes de agir |
| Testes automatizados cobrem token, bloqueio, alerta, mascaramento e permissões (v2, ver [testes.md](testes.md)) | Acrescentar testes de carga e de injeção em campos de texto com o modelo real |
