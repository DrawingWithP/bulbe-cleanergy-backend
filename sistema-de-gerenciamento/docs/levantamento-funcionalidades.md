# Levantamento de funcionalidades — app atual da Bulbe × entregas da squad Cleanergy

> Objetivo: registrar **o que o app e o site da Bulbe já oferecem hoje** e **o que a squad Cleanergy
> acrescentou** (front-end do Projeto I, API do Projeto II e, agora, o painel de gestão com chatbot),
> mostrando onde cada funcionalidade aparece no banco fictício e no painel.
>
> Todos os dados de clientes citados neste repositório são **fictícios**.

## 1. Fontes consultadas

| Fonte | O que foi observado | Quem levantou |
|---|---|---|
| Site institucional `bulbeenergia.com.br` | Proposta de valor, passo a passo, números, Indique e Ganhe, regulação, canais de atendimento | Squad |
| Google Play — pacote `com.bulbe.areadocliente` | Descrição do app "Área do Cliente", versão **2.5.5** | Squad |
| App Store — id `1662527941` | Mesma descrição; nota **4,7** com **352 avaliações** | Squad |
| Entrevista com a equipe da Bulbe (04/03/2026) | Demandas D-01 a D-06 (`Bulbe-Squad-cleanergy/docs/demandas.md`) | Squad (Projeto I) |
| Front-end da squad (`final.html`, `README.md`) | Telas e fluxos novos (home aberta, simulador, jornada de ativação, Clube Bulbe, dicas) | Squad (Projeto I) |
| `backend/docs/Lista_de_endpoints.md`, `backend/docs/user-stories.md` | Contrato da API REST `/v1` que sustenta o front | Squad (Projeto II) |

> Os números do site (clientes, cidades, valores investidos) são os divulgados publicamente pela
> empresa na data da pesquisa e podem mudar. Eles entram na base de conhecimento do chatbot
> apenas como referência institucional, nunca como dado de cliente.

## 2. O que a Bulbe já tem hoje

### 2.1 App "Área do Cliente" (lojas, versão 2.5.5)

| Funcionalidade | Descrição resumida |
|---|---|
| Status da instalação | O cliente acompanha se a conexão com a usina já foi concluída |
| 2ª via de faturas | Download/cópia da fatura Bulbe |
| Histórico de pagamentos | Lista de faturas pagas e em aberto |
| Promoções exclusivas | Ofertas genéricas para clientes |
| Notificações personalizadas | Avisos de vencimento, status e campanhas |

Restrições observadas (confirmadas pela entrevista, D-04 e D-05): o app **só funciona com login** e
"poucos clientes fazem login". Não há área para visitante, simulador nem fluxo de adesão dentro do app.

### 2.2 Site institucional

| Tema | O que o site diz |
|---|---|
| Proposta | Energia solar por assinatura em Minas Gerais: **adesão grátis, sem fidelidade e sem obras** |
| Desconto | **Até 15%** na conta de luz; o desconto **não incide** sobre iluminação pública nem sobre PIS/COFINS |
| Conta única | O cliente passa a receber uma **conta de luz Bulbe única**, com economia e consumo |
| Como funciona (4 passos) | 1. Contratar · 2. A Bulbe resolve tudo com a Cemig e o cliente acompanha pelo app · 3. Nova conta Bulbe com economia e consumo · 4. Indique e ganhe |
| Indique e Ganhe | **R$ 50 para quem indica e R$ 50 para o indicado**, sem limite de indicações, gerido pelo app |
| Números | **+60 mil clientes**, **+700 cidades em MG**, **R$ 35 milhões economizados**, **+R$ 300 milhões investidos** em fazendas solares |
| Regulação | **Lei 14.300/2022** (marco legal da geração distribuída) e **REN ANEEL 1.000/2021** |
| Atendimento | WhatsApp, e-mail `atendimento@bulbe.com.br` e ouvidoria |

## 3. Demandas da Bulbe (entrevista de 04/03/2026)

| ID | Demanda | MoSCoW |
|---|---|---|
| D-01 | Clientes não entendem como o serviço funciona | Should |
| D-02 | Clientes não confiam antes de receber o benefício (baixa adimplência da 1ª fatura) | Must |
| D-03 | Não conseguimos comunicar com clareza o prazo de ativação (até 90 dias) | Should |
| D-04 | Clientes não engajam com o aplicativo | Must |
| D-05 | Clientes não conseguem interagir com o app antes de assinar | Should |
| D-06 | Falta ferramenta que mostre a economia gerada | Should |

As User Stories do front (README do Projeto I) ligam-se a essas demandas assim:
US-01 → D-01, US-02 → D-06, US-03 → D-02, US-04 → D-05, US-05 → D-04, US-06 → D-03
(mesmo mapa usado em `backend/docs/Lista_de_endpoints.md`).

## 4. Comparativo: Bulbe hoje × funcionalidades da squad Cleanergy

Legenda da coluna "Já existe na Bulbe?": **Sim** (já existe no app/site), **Parcial** (existe algo
parecido, mas a squad mudou o formato ou o canal), **Não** (novidade da squad).

| # | Funcionalidade | Já existe na Bulbe? | Demanda | US do front | Onde aparece no banco / painel |
|---|---|---|---|---|---|
| 1 | **Modo visitante / home aberta** (usar o app sem login, entender o serviço, "Como funciona" e trilha em 4 etapas) | Não — o app exige login | D-01, D-05 | US-01, US-04 | Conteúdo institucional na base de conhecimento do chatbot (`app/chatbot/base_conhecimento.py`); simulações de visitante em `simulacoes.origem = 'visitante'`; métrica `simulacoes_30_dias` na visão geral do painel |
| 2 | **Simulador de economia sem login** (valor da conta, período 3/6/12 meses ou personalizado, amigos indicados, comparativo com/sem Bulbe e "com esse dinheiro você poderia...") | Não | D-06 | US-02 | Tabela `simulacoes`; consulta `simular_economia()`; ferramenta do chatbot de simulação; card de simulações na visão geral |
| 3 | **Adesão pelo app** (abrir conta de luz com a Bulbe dentro do app) | Parcial — hoje a adesão é pelo site/WhatsApp | D-05 | US-04 | Tabela `adesoes` (`origem` = `app`/`site`/`whatsapp`, `situacao` = `rascunho`/`enviada`/`aprovada`/`recusada`); rota `GET /v1/painel/adesoes`; card de adesões na visão geral |
| 4 | **Primeiro acesso por CPF com código** (verifica se o CPF já é cliente e envia código para habilitar o app) | Parcial — existe login, mas sem fluxo guiado de primeiro acesso | D-04 | US-05 | Campos `clientes.app_acesso_habilitado` e `clientes.ultimo_login_app`; métrica `app.clientes_com_acesso` / `app.logins_ultimos_30_dias` |
| 5 | **Jornada de ativação em 5 etapas + trilha visual** (Cadastro → Documentos → Solicitação à CEMIG → Análise CEMIG → Energia liberada; prazo de até 90 dias; percentual 15/30/45/70/90/100) | Parcial — o app mostra "status da instalação", sem etapas nem prazo | D-03 | US-06 | Tabelas `ativacoes` e `ativacao_eventos`; consulta `obter_ativacao()`; ficha do cliente (bloco "Jornada de ativação"); métrica `ativacao_por_etapa`; **v2:** tela **Ativações** (`resumo_ativacoes()`, `listar_clientes_parados()`) e ferramentas do chatbot de mesmo nome |
| 6 | **Clube Bulbe** (carta semanal a cada 7 dias, sequência de 5 semanas, bônus especial de R$ 50 na fatura, cupons de parceiros Araújo / Inter / Livelo com validade de 14 dias) | Parcial — a Bulbe tem "promoções exclusivas" genéricas | D-04, D-02 | US-05, US-03 | Tabelas `parceiros`, `clube_status`, `cartas`, `cupons`; consultas `obter_clube()`, `listar_cupons()`, `listar_parceiros()`; ficha do cliente (bloco "Clube Bulbe e cupons"); métrica `clube`; **v2:** bônus de R$ 50 aplicado em `faturas.bonus_clube` e somado em `clube.bonus_pagos`; tela **Parceiros** |
| 7 | **Indique e Ganhe** (R$ 50 + R$ 50, código pessoal como `MARCOS50`) | Sim — gerido pelo app | D-04 | US-05 | Tabela `indicacoes` e campo `clientes.codigo_indicacao`; bônus aplicado em `faturas.bonus_indicacao`; ficha do cliente (bloco "Indicações") |
| 8 | **Dicas de economia** (LED, banhos rápidos, cestos cheios, cômodos em uso, com economia mensal/anual) | Não | D-04, D-06 | US-05 | Tabela `dicas`; consulta `listar_dicas()`; rota `GET /v1/painel/dicas`; **v2:** tela **Dicas** no painel |
| 9 | **Prova social e regulação na home** (número de clientes, investimento, Lei 14.300/2022) | Parcial — está no site, não no app | D-02 | US-03 | Base de conhecimento do chatbot |
| 10 | **Faturas, 2ª via e histórico de pagamentos** | Sim | D-06 | US-05 | Tabela `faturas` (consumo, valor sem Bulbe, desconto, bônus, total, situação); consultas `listar_faturas()` e `resumo_economia_cliente()` |
| 11 | **Notificações personalizadas** | Sim | D-03, D-04 | US-06 | Tabela `notificacoes` (tipos `vencimento`, `ativacao`, `clube`, `indicacao`, `promocao`) |
| 12 | **Atendimento (WhatsApp, e-mail, ouvidoria)** | Sim — fora do app | D-03 | US-06 | Tabela `atendimentos`; rota `GET /v1/painel/atendimentos`; ficha do cliente |
| 13 | **Painel de gestão interno** (login de funcionário, visão geral, busca e ficha de clientes) | Não | D-02, D-03, D-04 | — (nova, interna) | Tabela `funcionarios`; rotas `/v1/painel/*`; interface em `/painel`; **v2:** bloqueio e alerta de login, auditoria (`auditoria_acessos`), telas de admin e paginação |
| 14 | **Chatbot do painel** (Claude Haiku 5.5 com ferramentas somente leitura, para funcionários perguntarem sobre clientes e sobre o app) | Não | D-01, D-03 | — (nova, interna) | Rotas `/v1/painel/chat` e `/v1/painel/chat/sugestoes`; registro em `chat_historico`; **v2:** streaming (`/v1/painel/chat/stream`), conversas no servidor (`chat_conversas`, `chat_mensagens`) e custo por pergunta |

### 4.1 Leitura do comparativo

- **O que já existe** (faturas, Indique e Ganhe, notificações, atendimento) foi modelado no banco para que
  o painel e o chatbot tenham contexto completo do cliente — não é funcionalidade nova da squad.
- **As novidades do cliente final** (itens 1 a 6 e 8) atacam diretamente as demandas Must D-02 e D-04:
  dar motivo para o cliente abrir o app **antes** do desconto chegar (jornada, clube, dicas) e mostrar o
  valor do serviço **antes** de contratar (home aberta e simulador).
- **As novidades internas** (itens 13 e 14) atacam o outro lado de D-03: quando o cliente pergunta
  "já estou ativo?", o atendente responde em segundos consultando a jornada de ativação pelo painel ou
  perguntando ao chatbot.

## 5. Regras de negócio consolidadas

| Regra | Valor | Fonte |
|---|---|---|
| Desconto sobre a conta | 15% (não incide sobre iluminação pública e PIS/COFINS) | Site + D-06 |
| Bônus por indicação válida | R$ 50 para quem indica e R$ 50 para o indicado, sem limite | Site |
| Prazo de ativação | Até 90 dias | D-03 |
| Etapas da ativação | 1 Cadastro (15%), 2 Documentos (30%), 3 Solicitação à CEMIG (45%), 4 Análise CEMIG (70%), 5 Energia liberada (90%); 100% quando o cliente fica `ativo` | Front + contrato |
| Clube Bulbe | 1 carta a cada 7 dias; meta de 5 semanas seguidas; cupom válido por 14 dias; bônus especial de R$ 50 na fatura ao completar 5 semanas | Front + contrato |
| Recompensas do clube | Araújo 15% (`BULBE15`), Inter cashback dobrado (`INTERCASH`), indicação dobrada por 30 dias (`BULBEDUO`), Livelo 500 pontos (`BULBELIV500`), Araújo 10% (`BULBE10`) | Contrato |
| Distribuidora | CEMIG (MG) | Site |
| Adesão | Grátis, sem fidelidade, sem obras | Site |
