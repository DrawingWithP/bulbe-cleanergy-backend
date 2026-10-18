"""
Camada de Conhecimento, Chatbot.

Texto de referencia que o assistente usa para explicar o negocio da Bulbe e o
funcionamento do app. Cada funcionalidade esta marcada como:
- [existente]: ja existe no app/site da Bulbe hoje;
- [novo (squad Cleanergy)]: criada pela squad Cleanergy no prototipo e ainda
  nao disponivel no app oficial da Bulbe.

O texto e estatico (nao muda entre requisicoes) para aproveitar o cache de
prompt da API. Dados de clientes NAO ficam aqui: vem sempre das ferramentas.
"""

BASE_CONHECIMENTO: str = """\
# Base de conhecimento — Bulbe Energia

## 1. Quem é a Bulbe
- A Bulbe Energia oferece **energia solar por assinatura** (geração distribuída compartilhada) em **Minas Gerais**, com foco em Belo Horizonte e região metropolitana. Há planos de expansão para a Bahia.
- Números institucionais: **mais de 60 mil clientes** e presença em **mais de 700 cidades de MG**.
- Como funciona: a Bulbe gera energia em **usinas solares** próprias/parceiras. A energia gerada vira **créditos de energia** que são compensados na conta de luz do cliente junto à distribuidora (**CEMIG**). O cliente não instala nada.
- Diferenciais: **sem obras** e sem placas no telhado, **sem fidelidade** (pode cancelar), **adesão grátis**, processo **100% digital**.
- Base legal:
  - **Lei 14.300/2022** — marco legal da micro e minigeração distribuída; regula o Sistema de Compensação de Energia Elétrica (SCEE), que permite usar créditos gerados em usinas remotas.
  - **REN ANEEL 1.000/2021** — regras de prestação do serviço de distribuição de energia (direitos e deveres do consumidor e da distribuidora).

## 2. Regras de negócio
- **Desconto de até 15%** sobre a conta de energia. O desconto **não incide** sobre a **contribuição de iluminação pública** nem sobre **PIS/COFINS**. Por isso a economia real costuma ser um pouco menor do que 15% do total da conta.
- **Conta de luz Bulbe única**: o cliente paga uma só fatura, emitida pela Bulbe, com o desconto já aplicado (e eventuais bônus de indicação abatidos).
- **Indique e Ganhe**: **R$ 50 para quem indica + R$ 50 para o indicado**, creditados na fatura quando o indicado adere (indicação válida). Cada cliente tem um **código de indicação** (ex.: `MARCOS50`).
- **Ativação em até 90 dias** após o cadastro, em **5 etapas**:
  1. **Cadastro** (15%) — dados do cliente recebidos.
  2. **Documentos** (30%) — conferência de documentos e da conta de luz.
  3. **Solicitação à CEMIG** (45%) — Bulbe pede o cadastro da unidade consumidora na usina.
  4. **Análise CEMIG** (70%) — a distribuidora analisa e aprova o vínculo (prazo depende da CEMIG).
  5. **Energia liberada** (90%) — créditos começam a ser compensados; vira 100% quando o cliente passa a `ativo`.
- **Clube Bulbe**: 1 carta a cada 7 dias; meta de **5 semanas seguidas**; cada cupom vale **14 dias**; ao completar 5 semanas o cliente ganha **bônus especial de R$ 50 na fatura**. Recompensas do clube: Araújo 15% (`BULBE15`), Inter cashback dobrado (`INTERCASH`), indicação dobrada por 30 dias (`BULBEDUO`), Livelo 500 pontos (`BULBELIV500`), Araújo 10% (`BULBE10`).

## 3. Responsabilidades: CEMIG × Bulbe
- **CEMIG (distribuidora)**: rede elétrica, falta de energia, religação, leitura do medidor, troca/defeito de medidor, aprovação do vínculo da unidade com a usina (etapa 4) e compensação dos créditos no faturamento.
  Falta de luz ou problema na rede → orientar o cliente a falar com a CEMIG.
- **Bulbe**: geração nas usinas, alocação dos créditos, cálculo do desconto, emissão da fatura Bulbe e 2ª via, programa de indicação, Clube Bulbe, atendimento sobre a assinatura, adesão e cancelamento.

## 4. Funcionalidades do app e dos canais
### Já existentes na Bulbe
- **Status da instalação/ativação** do cliente — [existente]
- **2ª via de faturas** — [existente]
- **Histórico de pagamentos** — [existente]
- **Promoções** (campanhas genéricas) — [existente]
- **Notificações** (vencimento, ativação, indicação, promoção) por app, WhatsApp ou e-mail — [existente]
- **Indique e Ganhe** (R$ 50 + R$ 50) — [existente]
- **Conta de luz Bulbe única** com desconto de até 15% — [existente]
- **Adesão pelo site** — [existente]
- **Atendimento**: WhatsApp, e-mail **atendimento@bulbe.com.br** e **ouvidoria** (para casos não resolvidos no atendimento) — [existente]
- **Login no app** (hoje é obrigatório para usar qualquer função) — [existente]

### Novas, criadas pela squad Cleanergy (ainda não estão no app oficial)
- **Home aberta / modo visitante** — o app passa a ter uma tela inicial sem login que explica como a Bulbe funciona. — [novo (squad Cleanergy)]
- **Simulador de economia sem login** — o visitante informa o valor da conta, o período (meses) e quantos amigos indicaria; o app mostra desconto mensal, economia no período, bônus de indicação e o bloco **"Com esse dinheiro você poderia..."** (mercado, jantar em família, gasolina, streaming, remédios, tênis). — [novo (squad Cleanergy)]
- **Adesão pelo app** — fluxo guiado de contratação dentro do próprio app (situações: rascunho, enviada, aprovada, recusada). — [novo (squad Cleanergy)]
- **Primeiro acesso por CPF com código** — o cliente informa o CPF e recebe um código de verificação no contato cadastrado para criar o acesso ao app. — [novo (squad Cleanergy)]
- **Jornada de ativação em 5 etapas com trilha visual** — barra de progresso (15/30/45/70/90%), etapa atual destacada e prazo de até 90 dias explicado ao cliente. — [novo (squad Cleanergy)]
- **Clube Bulbe** — cartas semanais, sequência de 5 semanas, cupons de parceiros (Araújo, Inter, Livelo...) e bônus de R$ 50 na fatura. — [novo (squad Cleanergy)]
- **Dicas de economia** — trocar lâmpadas por LED, banhos mais rápidos, lavar roupa com o cesto cheio, manter ligados só os cômodos em uso (com economia mensal/anual estimada). — [novo (squad Cleanergy)]
- **Painel de Gestão com chatbot** (este sistema) — painel interno para funcionários: métricas, busca de clientes, ficha do cliente e este assistente. — [novo (squad Cleanergy)]

## 5. Painel de Gestão (uso interno)
- Login de funcionário (perfis `atendimento` e `admin`).
- Visão geral com métricas; busca de clientes por nome, e-mail, CPF, nº de instalação ou código de indicação; ficha completa do cliente (ativação, faturas, economia, indicações, Clube, cupons, notificações, atendimentos).
- O chatbot é **somente leitura**: consulta dados, não altera cadastro, fatura, cupom ou atendimento. Alterações são feitas nos sistemas operacionais da Bulbe pelo time responsável.
- CPF e telefone aparecem **mascarados** no chat (LGPD). Para ver o dado completo, o funcionário usa a ficha do cliente no painel.
- Cada pergunta e resposta do chat fica registrada para auditoria.

## 6. Significado dos status (dados do painel)
- Cliente: `ativo` (recebendo créditos), `em_ativacao` (em alguma das 5 etapas), `cancelado`.
- Fatura: `paga`, `em_aberto` (dentro do prazo), `vencida` (passou do vencimento sem pagamento).
- Adesão: `rascunho`, `enviada`, `aprovada` (vira cliente), `recusada`. Origem: `app`, `site`, `whatsapp`.
- Indicação: `pendente`, `aderiu` (bônus devido/creditado), `expirada`.
- Cupom: `ativo`, `salvo`, `usado`, `expirado`, `descartado`. Carta: `disponivel`, `aberta`, `expirada`.
- Atendimento: `aberto`, `em_andamento`, `resolvido`. Canais: `whatsapp`, `email`, `app`, `ouvidoria`.
- Usina: `ativa`, `em_manutencao`, `inativa`.

## 7. Perguntas frequentes (FAQ)
- **Preciso instalar placas?** Não. A energia vem de usinas remotas; não há obra.
- **Tem fidelidade ou multa?** Não há fidelidade. A adesão é gratuita.
- **Quanto vou economizar?** Até 15% sobre a parte da conta em que o desconto incide (não incide em iluminação pública e PIS/COFINS), mais R$ 50 por indicação válida.
- **Quando começa o desconto?** Após a ativação, que leva até 90 dias e depende da análise da CEMIG (etapa 4).
- **Continuo cliente da CEMIG?** Sim. A CEMIG segue responsável pela rede e pelo fornecimento; a Bulbe fornece os créditos de energia solar.
- **Falta de energia?** É com a CEMIG.
- **Como pego a 2ª via?** Pelo app (área de faturas) ou pelos canais de atendimento.
- **Como indico alguém?** Compartilhando o código de indicação (WhatsApp, link ou e-mail); quando o indicado adere, os dois ganham R$ 50.
- **Atendimento**: WhatsApp oficial da Bulbe, e-mail atendimento@bulbe.com.br; se não resolver, ouvidoria.
"""
