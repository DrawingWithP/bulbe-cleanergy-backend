# Segurança e LGPD — painel de gestão e chatbot

> Escopo: o painel interno (`/painel`, `/v1/painel/*`), o chatbot (`/v1/painel/chat`) e o banco fictício.
> Base legal de referência: **Lei 13.709/2018 (LGPD)** — princípios de finalidade, necessidade,
> segurança, prevenção e responsabilização (art. 6º).

## 1. Dados fictícios

- O banco é gerado por `app/database/seed.py` com gerador determinístico (`random.Random(42)`), **sem dados reais**.
  Nomes, e-mails, CPFs (11 dígitos de formato válido, sem titular real), telefones e endereços são inventados.
- Os personagens das telas do front (ex.: Marcos Andrade, Clara Ribeiro) também são fictícios.
- O arquivo `.db` não é versionado (`*.db` no `.gitignore`); cada pessoa gera o seu localmente.
- **Antes de ligar o painel a dados reais da Bulbe**, os itens da seção 9 são obrigatórios.

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
  Atende ao requisito **RNF-01** ("usar hash ou salt para criptografar senhas") de `docs/Lista_de_requisitos.md`.

## 5. Token assinado com HMAC e expiração

- Após o login, `app/painel/auth.py` emite um token `<payload>.<assinatura>` (ambos em base64url): o payload é um JSON com
  os dados mínimos do funcionário (`id`, `nome`, `email`, `perfil`), `iat` e `exp` (**8 horas**); a assinatura é
  **HMAC-SHA256** do payload com `PAINEL_SECRET`. Só biblioteca padrão (sem PyJWT).
- Sem `PAINEL_SECRET`, o painel usa um segredo de desenvolvimento **público** e registra um aviso no log —
  aceitável só na máquina do desenvolvedor.
- `validar_token` recalcula a assinatura, compara em tempo constante e rejeita tokens expirados, adulterados,
  malformados ou maiores que 4096 caracteres.
- Rotas protegidas usam a dependência `funcionario_logado` (`401` se inválido); rotas administrativas usam `exigir_admin` (`403`).
- O front guarda o token em `sessionStorage` (apagado ao fechar a aba) e o envia em `Authorization: Bearer <token>`;
  qualquer 401 leva de volta ao login.
- Trocar `PAINEL_SECRET` invalida todos os tokens emitidos (útil em caso de vazamento).

## 6. Auditoria em `chat_historico`

Cada troca com o chatbot grava: `funcionario_id`, `pergunta`, `resposta`, `ferramentas_usadas` (JSON) e `criado_em`.
Isso permite responder **quem consultou o quê e quando** (princípio da responsabilização) e investigar
respostas incorretas. Além disso, cada abertura de ficha no painel gera um log `INFO` com o id do funcionário e
o id do cliente. Recomendações:

- Definir prazo de retenção (ex.: 6 a 12 meses) e rotina de expurgo.
- Restringir a leitura de `chat_historico` ao perfil `admin`.
- A resposta gravada já contém apenas os dados que o modelo recebeu (CPF/telefone mascarados).

## 7. Defesa contra *prompt injection*

Campos como `descricao` de atendimentos, `observacao` de eventos ou nomes de indicados são texto livre e
poderiam conter frases do tipo "ignore as instruções anteriores". As defesas adotadas:

1. **Resultados de ferramentas são dados, não instruções** — o prompt de sistema diz isso explicitamente e os
   resultados chegam ao modelo como `tool_result` em JSON, separados das mensagens do funcionário.
2. **Sem ferramentas perigosas** — não há escrita, envio de mensagens, acesso à web nem execução de código;
   o pior caso de uma injeção é uma resposta errada, não uma ação.
3. **Entrada validada** — `mensagem` com 1 a 2000 caracteres e `historico` com no máximo 20 itens, papel
   `funcionario` ou `assistente` (Pydantic). O `input` das ferramentas é lido como dicionário e validado por
   `validar_entrada` (tipos, valores permitidos, limites, textos de até 200 caracteres); parâmetros desconhecidos
   são ignorados. O resultado de cada ferramenta é limitado a 40.000 caracteres.
4. **Saída tratada como texto** — a interface passa todo dado por `esc()` e escapa a resposta do chat antes de
   converter `**negrito**`, listas e quebras de linha, evitando XSS a partir de texto vindo do banco ou do modelo.
   Além disso, uma *Content Security Policy* por `<meta>` bloqueia scripts e estilos inline e de outros domínios
   (exceto Google Fonts); não há frameworks nem CDN de JavaScript.
5. **Histórico sem estado no servidor** — o servidor não guarda contexto entre perguntas além da auditoria;
   o histórico enviado pelo navegador contém só texto, nunca resultados de ferramentas anteriores, e fica só na
   memória da página (não é gravado no navegador).
6. **Dados de clientes nunca entram no prompt fixo** — a base de conhecimento é estática; dado de cliente só
   chega ao modelo como resultado de ferramenta, já mascarado.

## 8. Chave da API e configuração

- `ANTHROPIC_API_KEY` fica **somente no `.env`** (ignorado pelo Git) ou em variável de ambiente do servidor.
  Nunca em código, `.env.example`, documentação, issue ou print de tela.
- A chave é lida do ambiente a cada chamada (`config.obter_chave_api()`), nunca registrada em log.
- Sem a chave (ou sem o pacote `anthropic`), o chatbot responde `503 CHATBOT_INDISPONIVEL` e o restante da API
  funciona normalmente.
- O mesmo vale para `PAINEL_SECRET` e `PAINEL_SENHA_DEMO`.
- Se uma chave vazar: revogar no console da Anthropic, gerar outra e atualizar o `.env`.

## 9. Limites conhecidos e próximos passos

| Limite atual | Próximo passo sugerido |
|---|---|
| Dados fictícios em SQLite local | Para dados reais: banco gerenciado com criptografia em repouso, backups e acesso por perfil |
| Dados de clientes enviados (mascarados) a um provedor externo de IA | Avaliar com o DPO da Bulbe a base legal, o contrato de tratamento de dados com o provedor, a política de retenção e o registro da operação (RIPD/DPIA) |
| Login apenas com e-mail e senha, **sem limite de tentativas** | MFA, bloqueio após tentativas falhas e *rate limit* em `/v1/painel/login` |
| Token sem revogação individual | Lista de revogação ou sessões no servidor; *refresh token* curto |
| Perfis `atendimento` e `admin` veem os mesmos dados de cliente (`exigir_admin` existe, mas nenhuma rota usa ainda) | Controle mais fino (ex.: atendimento vê só clientes do seu atendimento; `chat_historico` só para admin) |
| Log de abertura de ficha só no log da aplicação | Gravar também em tabela de auditoria, como já é feito com o chat |
| Sem HTTPS na demonstração local | Em qualquer ambiente compartilhado, servir apenas por HTTPS e com CORS restrito |
| Auditoria grava a pergunta em texto livre | Orientar funcionários a não colar dados sensíveis desnecessários; expurgo periódico |
| Chatbot pode errar ou interpretar mal | Exibir as ferramentas consultadas em cada resposta e orientar a conferir na ficha antes de agir |
| Sem testes automatizados de segurança | Testes de token adulterado/expirado, de mascaramento e de injeção em campos de texto |
