# Plano de finalização do projeto

Registro de tudo o que a equipe pediu para a reta final, com o que já existe hoje, o que cada pedido exige no
back-end e no front-end e a ordem sugerida. **Status (15/11/2026): todos os itens das seções 2 e 3 foram implementados** na branch `feat/entrega-final`, com testes. O que ficou de fora está marcado com `[ ]`.

- Branch de trabalho: `feat/entrega-final` (criada a partir da `main` depois do merge do PR #57)
- Foco do projeto: **back-end**. Por isso cada item lista primeiro o que muda na API e no banco.
- Legenda: `[ ]` a fazer · `[~]` em andamento · `[x]` feito

---

## 1. Resposta: para que serve a tela "Adesões" do sistema de gerenciamento?

**Adesão é o pedido de contratação de quem ainda não é cliente.** Quando alguém clica em *Abrir conta de luz com a
Bulbe* no app (tela nova *Abrir conta*), preenche dados, endereço e conta de luz e envia, nasce uma adesão
(`POST /v1/adesoes`). Ela passa pelas situações:

| Situação | Significado |
|---|---|
| `rascunho` | começou a preencher e não enviou |
| `enviada` | pedido enviado, aguardando análise da Bulbe |
| `aprovada` | a Bulbe aceitou: a pessoa vira cliente e começa a jornada de ativação |
| `recusada` | não foi possível atender (ex.: fora da área da CEMIG) |

A tela *Adesões* do painel é a **fila de novos clientes**: mostra quem pediu para entrar, por qual canal
(app, site, WhatsApp), o valor da conta e a economia estimada. Hoje ela **só mostra** — não tem ação.

Proposta (item G-04): botões **Aprovar** e **Recusar**. Aprovar cria o cliente no app com a jornada na etapa 1;
a pessoa então usa o *Primeiro acesso* com o CPF e passa a acompanhar tudo pelo app. Isso fecha o funil
**simulação → adesão → cliente → ativação** e é uma ótima história para a apresentação.

---

## 2. Sistema de gerenciamento (painel interno)

### G-00 · Refatoração geral do front-end do painel
> "O que mais está pesando nele é o front-end, ele está bem mal feito, quero que você faça uma refatoração em todo o front do sistema."

- [x] Novo layout base: menu lateral, cabeçalho, grade de cards, tabelas, formulários, modais, toasts e estados vazios/carregando/erro com o mesmo padrão.
- [x] Organizar `painel.css` por variáveis (tokens de cor, espaçamento, tipografia, raio, sombra), como no app.
- [x] Separar `painel.js` (≈2 mil linhas) em módulos por tela (`telas/visao-geral.js`, `telas/clientes.js`, …) e um módulo comum (`api.js`, componentes).
- [x] Gráficos em SVG próprio (`js/graficos.js`): a CSP do painel não permite scripts de CDN.
- [x] Responsivo e acessível (teclado, contraste, `aria-*`), mantendo o que já existe.
- Critério de aceite: todas as telas atuais continuam funcionando; os 198 testes do painel seguem passando.

### G-01 · Visão geral (só front-end)
> "Refatore o design da tela, coloque alguns gráficos, separe mais alguns widgets."

- [x] Linha de KPIs: clientes ativos, em ativação, adesões aguardando, economia gerada, faturas vencidas, atendimentos abertos.
- [x] Gráficos: funil de ativação por etapa (barras), clientes por status (rosca), economia por mês (linha), adesões por canal (barras), uso do Clube (cartas abertas × cupons usados).
- [x] Widgets separados: "clientes parados há mais tempo", "últimos atendimentos abertos", "últimas adesões", estado da integração com o app.
- Back-end: nenhum endpoint novo obrigatório (usa `/v1/painel/metricas`); se faltar série mensal, acrescentar um campo na métrica.

### G-02 · Clientes: filtros e ordenação
> "Mais algumas opções de filtros, como ordenar por data, por status etc."

- [x] Ordenar por: nome, data de cadastro, status, etapa, cidade (asc/desc).
- [x] Filtros: status, etapa da ativação, cidade, origem (app/fictício), com acesso ao app, período de cadastro.
- [x] Back-end do painel: `GET /v1/painel/clientes` ganha `ordenar_por`, `ordem`, `etapa`, `origem`, `cadastro_de`, `cadastro_ate` (validados por lista fechada, sem SQL dinâmico).

### G-03 · Adesões
- [x] Explicação registrada na seção 1.
- [x] (proposta) Ações Aprovar / Recusar — ver G-04.

### G-04 · Adesões: aprovar e recusar (proposta, ainda não confirmada pelo grupo)
- [x] Back-end do app: `POST /v1/adesoes/{id}/aprovacao` (cria o cliente + ativação etapa 1, marca `aprovada`) e `POST /v1/adesoes/{id}/recusa` (com motivo); ambos com token de operador.
- [x] Painel: botões na tela Adesões chamando a API do app (mesmo padrão do "Atualizar no app").

### G-05 · Atendimentos com chat em tempo real (app ↔ painel)
> "Quando eu clicar na pessoa já abra uma tela específica daquele atendimento. Quando a pessoa começar um atendimento pelo app, respostas automáticas; se não resolver, opção de falar com um atendente real. Na apresentação: a pessoa conversando pelo app e o atendente respondendo pelo sistema de gerenciamento. Se o status estiver em aberto, ao clicar abre o chat."

Hoje: o painel tem uma tabela `atendimentos` fictícia (canal, assunto, descrição, status) **sem mensagens**, e o
app/back-end **não têm atendimento nenhum**. Tudo abaixo é novo.

- [x] **Back-end do app (fonte da verdade)**
  - Tabelas: `atendimentos` (id, cliente_id, assunto, status `bot`/`aguardando_atendente`/`em_atendimento`/`resolvido`, criado_em, atualizado_em, atendente) e `atendimento_mensagens` (id, atendimento_id, autor `cliente`/`bot`/`atendente`, texto, criado_em). Migration nova.
  - Rotas do cliente: `POST /v1/atendimentos` (abre), `GET /v1/clientes/{id}/atendimentos`, `GET /v1/atendimentos/{id}/mensagens?depois_de=`, `POST /v1/atendimentos/{id}/mensagens`, `POST /v1/atendimentos/{id}/atendente` (pede humano), `PATCH /v1/atendimentos/{id}` (encerrar).
  - **Respostas automáticas**: um fluxo simples por menu/palavras-chave (prazo de ativação, fatura, Clube, indicação, mudança de endereço) com respostas prontas que usam os dados do cliente (ex.: "sua conexão está na etapa 3"). Depois de 2–3 respostas: botões "Resolveu" / "Falar com um atendente".
  - Rotas do operador (token): listar fila, assumir atendimento, responder, encerrar.
  - Atualização "ao vivo": *polling* a cada 2–3 s com `depois_de=<última mensagem>` (simples e confiável na apresentação). WebSocket/SSE fica como melhoria.
- [x] **Painel**
  - Tela Atendimentos: fila com status; clicar na linha abre a **tela do atendimento** (`#/atendimento/{id}`) com o chat; em status aberto/aguardando, o atendente pode assumir e responder.
  - Sincronização: atendimentos do app entram no painel (como os demais dados) e as respostas do atendente vão pela API do app.
- [x] **App**: ver A-02 (tela Fale conosco).
- Critério de aceite: na apresentação, uma pessoa escreve no app, recebe respostas automáticas, pede atendente; outra responde no painel e a resposta aparece no app em poucos segundos.

### G-06 · Ativações: reorganizar a tela
> "Achei um pouco confuso, melhore a distribuição das informações; os clientes parados na mesma etapa ficaram bem confusos."

- [x] Topo: 4 números (em ativação, atrasados > 90 dias, tempo médio, ativados em 30 dias).
- [x] Funil das 5 etapas lado a lado: quantos clientes em cada uma e dias médios na etapa; clicar numa etapa filtra a lista.
- [x] "Clientes parados" vira uma lista simples: nome, etapa (com nome da etapa), há quantos dias, previsão, botão "Abrir ficha" (a etapa muda na ficha, com "Atualizar no app"). Destaque visual para quem passou do prazo.
- Back-end: nada novo obrigatório (`/ativacoes/resumo` e `/clientes/parados` já existem).

### G-07 · Dicas: vitrine do app com arrastar e soltar
> "Uma linha principal com 5 cards (o que está nela aparece no app); abaixo, mais cards e opção de cadastrar nova dica. Troca arrastando o card; a linha principal tem exatamente 5; dá para reordenar, tirar e colocar; botão Confirmar alterações que só muda no app ao clicar."

- [x] **Back-end do app**
  - `dicas` ganha `em_exibicao` (bool), `ordem` (int) e `icone` (chave de um ícone pronto, ver A-01). Migration.
  - `GET /v1/dicas` (público, usado pelo app) passa a devolver **só as 5 em exibição, na ordem**; `GET /v1/dicas?todas=true` (operador) devolve o acervo.
  - `PUT /v1/dicas/vitrine` (operador): recebe a lista ordenada de **exatamente 5** ids e grava tudo numa transação (422 se não forem 5, se houver id repetido ou inexistente).
  - `POST /v1/dicas` já existe: passa a aceitar `icone` (lista fechada) no lugar do SVG livre.
- [x] **Painel**: linha "No app agora" com 5 posições + "Acervo" abaixo; arrastar e soltar (HTML5 drag-and-drop + alternativa por teclado/botões); botão **Confirmar alterações** (desabilitado enquanto a linha não tiver 5); modal **Nova dica** com escolha de ícone pronto.
- Critério de aceite: mudar a ordem no painel não altera o app até confirmar; depois de confirmar, o carrossel do app mostra as 5 na nova ordem.

### G-08 · Parceiros e cupons (cadastro no painel + base de cupons)
> "Além de cadastrar parceiros, cadastrar novos cupons para a tela de Vantagens do app, para adicionar ou mudar cupons."

Hoje: a API do app já tem CRUD de parceiros (com token), mas o painel só **lista**; e **toda carta aberta gera o mesmo
cupom fixo** ("500 pontos Livelo", escrito no código de `carta_service.py`).

- [x] **Back-end do app**
  - Nova tabela `cupons_catalogo` (modelo de cupom): parceiro_id, título, descrição, tag, prefixo do código, validade em dias, ativo, peso (chance de sorteio).
  - CRUD com token: `GET/POST /v1/catalogo-cupons`, `PUT/PATCH/DELETE /v1/catalogo-cupons/{id}`.
  - Os `cupons` do cliente continuam como hoje (cópia do modelo no momento da abertura, com código único), então mudar o catálogo não altera cupons já entregues.
- [x] **Painel**: tela Parceiros com cadastrar/editar/desativar parceiro e, dentro de cada parceiro, os cupons do catálogo (cadastrar, editar, ativar/desativar).
- [x] Ver A-03 para o sorteio semanal.

### G-09 · Relógio de demonstração ("pular data")
> "Uma opção de pular data apenas para fins demonstrativos, para mostrar o app funcionando, os dias da carta passando etc."

Hoje: cartas e cupons usam a hora real do servidor (`datetime.now`), então a carta da semana só libera depois de 7 dias de verdade.

- [x] **Back-end do app**: um "relógio" único (`app/core/relogio.py`) usado por todos os serviços no lugar de `datetime.now()`, com um **deslocamento** guardado no banco (tabela `demonstracao`).
  - `GET /v1/demonstracao/relogio`, `POST /v1/demonstracao/relogio/avancar` (`{"dias": 1}`), `POST /v1/demonstracao/relogio/resetar`.
  - Só existem fora de produção (`BULBE_AMBIENTE != producao`) e exigem token de operador.
- [x] **Painel**: controle "Data de demonstração" (mostra a data simulada; botões +1 dia, +7 dias, voltar ao hoje) visível só para admin e só quando a API informar que está em modo demonstração.
- [ ] **App** (opcional, não feito): os botões flutuantes antigos do protótipo ("Passar dia", "Próxima etapa"), hoje desativados, podem chamar esse relógio no modo demonstração (opcional).
- Critério de aceite: com +7 dias, a carta da semana fica disponível no app; o cupom mostra os dias restantes corretos.

---

## 3. App (frontend + API)

### A-01 · Ícones das dicas
> "Na tela de dicas os ícones estão pretos e feios, isso tem que mudar para os ícones antigos; criar ícones novos para quando a pessoa criar a dica no sistema escolher uma opção pronta que faça sentido."

Causa encontrada: o carrossel passou a usar o campo `imagem_svg` de cada dica vindo da API, e o seed grava o **mesmo SVG genérico de lâmpada (preto)** para todas. Os ícones coloridos originais continuam em `frontend/screens/dicas/icons/` (`light_lamp`, `dark_lamp`, `shower`, `laundry`, `piggybank`).

- [x] Biblioteca fixa de ícones no front (`frontend/icons_final/dicas/*.svg`), começando pelos originais + novos no mesmo estilo (ex.: geladeira, ar-condicionado, chuveiro, lâmpada, tomada/stand-by, sol, máquina de lavar, ferro de passar, TV, cofrinho).
- [x] Back-end: dica guarda `icone` (chave da lista fechada, validada) em vez de SVG livre — também elimina o risco de SVG malicioso. Migration que converte as dicas existentes para um ícone.
- [x] App: o carrossel monta a imagem a partir da chave; painel (G-07) escolhe o ícone num seletor visual.

### A-02 · Tela "Fale conosco" (chat)
> "Desenvolva a tela de chat/conversa para conseguirmos fazer a mecânica do atendimento."

- [x] Nova tela no padrão das telas novas (`telas.css`/`telas.js`, prefixo próprio, variáveis do `:root`): lista de conversas + tela de conversa (balões cliente/bot/atendente, digitando, horário), atalhos de perguntas frequentes, botão "Falar com um atendente", encerrar e avaliar.
- [x] Ligar o item "Fale conosco" do menu lateral à tela.
- [x] Usa as rotas de G-05 com *polling*; só para cliente com sessão (senão, leva ao Entrar).

### A-03 · Cupom aleatório por semana; carta especial fixa
> "Cada pessoa recebe aleatório, para todo mundo não receber sempre o mesmo cupom; base de cupons onde cada semana atualiza na carta do cliente; só a carta especial é sempre fixa: R$ 50 de desconto na fatura."

- [x] Back-end (`carta_service.abrir_carta`): carta **normal** sorteia um modelo ativo do catálogo (G-08), com peso, evitando repetir o cupom da semana anterior do mesmo cliente; carta **especial** (5ª semana) gera sempre "R$ 50 de desconto na fatura".
- [x] Sorteio reproduzível nos testes (gerador com semente injetável).
- [x] Testes: dois clientes podem receber cupons diferentes; o mesmo cliente não recebe o mesmo cupom duas semanas seguidas (quando houver mais de um modelo); especial sempre R$ 50.

---

## 4. Resumo do que muda no back-end

| Área | Banco (migration) | API |
|---|---|---|
| Atendimento | `atendimentos`, `atendimento_mensagens` | rotas do cliente e do operador, respostas automáticas |
| Dicas | `em_exibicao`, `ordem`, `icone` | `PUT /v1/dicas/vitrine`, `GET /v1/dicas` só vitrine |
| Cupons | `cupons_catalogo` | CRUD do catálogo; sorteio na abertura da carta |
| Demonstração | `demonstracao` (deslocamento do relógio) | `/v1/demonstracao/relogio*` (fora de produção) |
| Adesões (proposta) | — | aprovar / recusar |
| Clientes no painel | — | ordenação e filtros novos |

Para cada item: testes unitários (serviço) + integração (API com banco de teste) + atualizar `docs/api/openapi.json`,
a sincronização do painel (`sincronizacao.py`) e o teste entre sistemas.

---

## 5. Ordem sugerida

1. **Relógio de demonstração (G-09)** — base para testar Clube e prazos.
2. **Catálogo de cupons + sorteio semanal (G-08, A-03)**.
3. **Dicas com vitrine e ícones (G-07, A-01)**.
4. **Atendimento: back-end, chat do app e tela no painel (G-05, A-02)** — maior item; deixar pronto com folga antes do ensaio.
5. **Refatoração do front do painel (G-00) junto com Visão geral, Clientes e Ativações (G-01, G-02, G-06)**.
6. (Se o grupo aprovar) **Adesões com aprovar/recusar (G-04)**.
7. **Roteiro de apresentação (seção 7)** e ensaio com os dados de demonstração.

---

## 6. Ideias de melhoria (sugestões, não pedidas)

**Back-end / app**
- [ ] **Token de cliente**: o primeiro acesso devolver um JWT de cliente e as rotas do cliente exigirem esse token (hoje é só identificação). É a melhoria de segurança mais relevante para um projeto focado em back-end.
- [ ] **Notificações** (o sino do app): mudança de etapa, carta disponível, resposta do atendente, cupom perto de vencer.
- [ ] **Código de indicação do cliente** gerado pela API e um link "indique" com esse código; a adesão que usar o código vira indicação "aderiu" automaticamente.
- [ ] **Faturas e economia real no back-end** (hoje só existem no banco fictício do painel), para o app mostrar "você já economizou R$ X".
- [ ] **Limite de tentativas** no envio de código do primeiro acesso por CPF/IP.
- [ ] Endpoint `/health` e logs estruturados; `docker-compose` com PostgreSQL para mostrar o projeto rodando fora do SQLite.
- [ ] Paginação e filtros padronizados em todas as listas da API.

**Sistema de gerenciamento**
- [ ] Tela para definir a **bandeira tarifária do mês** (a API já tem `PUT /v1/bandeiras/{mes}`): mostra o efeito no simulador na hora.
- [ ] **Funil completo** na visão geral: simulações → adesões → clientes → ativados, com taxa de conversão.
- [ ] O assistente (chatbot) **sugerir a resposta** ao atendente no chat (G-05), com o atendente revisando antes de enviar.
- [ ] Exportar listas (clientes, adesões, atendimentos) em CSV.
- [x] Notificar o atendente (badge no menu) quando um cliente pedir atendimento humano. *(feito: contador de atendimentos abertos no menu do painel)*

---

## 7. Roteiro de apresentação

Pronto em [`ROTEIRO-APRESENTACAO.md`](ROTEIRO-APRESENTACAO.md): divisão por integrante, tempo de cada parte, falas-chave,
passo a passo da demonstração (app e painel lado a lado) e checklist do ambiente.

---

## 8. Pendências que só a equipe resolve

- [ ] Matrícula do Rodrigo e link do board no README.
- [ ] Revisar o texto da extensão universitária no README.
- [ ] Story points das US-36 a US-38.
- [x] Decidir se G-04 (aprovar/recusar adesões) entra. *(entrou)*
