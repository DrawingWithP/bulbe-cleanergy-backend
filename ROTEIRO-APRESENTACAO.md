# Roteiro de apresentação — Bulbe Energia (Cleanergy Squad)

Duração alvo: **25 minutos** + perguntas. O foco do projeto é o **back-end**: a demonstração mostra o app e o painel
funcionando, mas cada parte termina explicando o que a API faz por trás.

A divisão abaixo é uma sugestão. Troquem os nomes à vontade, mas mantenham a ordem: ela segue a jornada de um cliente.

| # | Parte | Quem | Tempo |
|---|---|---|---|
| 1 | Abertura: problema e solução | Samuel (líder) | 2 min |
| 2 | Arquitetura e back-end por dentro | Luiz | 4 min |
| 3 | Demo 1: visitante → adesão → aprovação → primeiro acesso | Rafael | 4 min |
| 4 | Demo 2: ativação e Clube Bulbe (relógio, cupom sorteado, carta especial) | João | 5 min |
| 5 | Demo 3: Fale conosco (assistente + atendente real) e painel | Gabriel | 5 min |
| 6 | Qualidade: testes, CI, documentação, segurança e LGPD | Rodrigo | 3 min |
| 7 | Encerramento: aprendizados, próximos passos, extensão | Samuel | 2 min |

---

## Antes de começar (checklist do ambiente)

Façam isto **10 minutos antes**, no computador que vai para o projetor.

1. Branch certa e dependências instaladas: `git checkout feat/entrega-final` (ou a `main`, depois do merge).
2. Subir tudo com bancos limpos (o seed recria os dados de demonstração):

   ```bash
   .venv\Scripts\python.exe iniciar.py
   ```

   Esperar aparecer `Uvicorn running on http://127.0.0.1:8000` e `...:8001`.
3. Abrir **duas janelas lado a lado** (a da esquerda em modo celular, F12 → ícone de celular, ~390 px):
   - Esquerda — **App**: <http://127.0.0.1:8000/frontend/final.html>
   - Direita — **Painel**: <http://127.0.0.1:8001/painel/> → entrar com `admin@bulbe.com.br` / `bulbe@demo123`
4. Deixar abertas também, em abas: Swagger <http://127.0.0.1:8000/docs> e o README (diagrama de arquitetura).
5. Conferir no topo do painel: **"Data do app"** aparece (modo demonstração) e o contador de Atendimentos aparece
   (a conversa da Ana já está na fila, destacada como "Aguardando atendente").
6. Dados úteis (fictícios, do seed):
   - CPF da adesão para aprovar: **168.995.350-09** (João da Silva)
   - CPF do Marcos (cliente em ativação, Clube com 3 semanas): **529.982.247-25**
   - CPF da Ana (já tem conversa aguardando atendente): **111.444.777-35**
   - Fora de produção a própria tela mostra o código de 6 dígitos do primeiro acesso (não há SMS real).
7. Plano B: se algo travar, `Ctrl+C` no terminal e rodar `iniciar.py` de novo (≈20 s). Tenham prints das telas
   principais numa pasta, caso a internet/projetor falhe (o projeto roda 100% local, não depende de internet,
   só o assistente do painel precisa da chave da IA).

> Ensaiem a demo inteira pelo menos uma vez com o ambiente recém-iniciado: as etapas 3, 4 e 5 mudam os dados.

---

## 1. Abertura — Samuel (2 min)

- **Problema:** quem conhece a Bulbe precisa fazer login para entender o serviço; não dá para simular a economia antes
  de contratar; depois de contratar, o cliente espera até 90 dias pela CEMIG **sem ver em que pé está**; e a equipe não
  tem uma visão única dos clientes.
- **Solução em três partes:** um **app** para o cliente (simular, aderir, acompanhar a ativação, Clube Bulbe, falar com
  a Bulbe), uma **API** que guarda as regras de negócio e um **sistema de gerenciamento** para a equipe operar tudo.
- Frase de efeito: *"O cliente vê a ativação andar e o atendente move essa ativação — tudo pela mesma API."*

## 2. Arquitetura e back-end por dentro — Luiz (4 min)

Mostrar o diagrama do README e, depois, o Swagger.

- **Três sistemas:** app (HTML/CSS/JS) → **API FastAPI** (fonte da verdade, SQLite/SQLAlchemy) ← **painel** (FastAPI
  próprio, com banco próprio que **sincroniza** com o app e escreve no app **pela API**, com token de operador).
- **Camadas** da API: controllers (rotas) → services (regras) → repositories (banco) → domain (Pydantic). Erros de
  negócio padronizados `{"error": {"code", "message", "status"}}`.
- **Banco versionado** com Alembic (migrations da entrega final: relógio de demonstração, catálogo de cupons, dicas
  com vitrine, atendimentos).
- **Autenticação:** JWT para operadores; rotas de escrita protegidas; painel com perfis `admin` e `atendimento`.
- No Swagger, abrir 2 exemplos rápidos: `POST /v1/simulacoes` (regra da bandeira tarifária) e
  `POST /v1/cartas/{id}/abertura` (sorteio do cupom).

## 3. Demo 1: do visitante ao cliente — Rafael (4 min)

**App (esquerda):**
1. Entrar como **visitante** → **simulador**: conta de R$ 320, mudar a bandeira → a economia vem da API.
2. **Abrir conta** (adesão) com dados fictícios → "pedido enviado".

**Painel (direita):**
3. **Adesões** → aparece o pedido feito no app (filtro "Feitas no app"). Explicar: *a equipe confere endereço e conta
   da CEMIG antes de aprovar.*
4. **Aprovar** o João da Silva (CPF 168.995.350-09) → confirmação → "cliente criado no app".

**App:**
5. **Entrar** → primeiro acesso com o CPF 168.995.350-09 → código de 6 dígitos → o cliente já vê a **jornada na
   etapa 1**.

Por trás (falar enquanto clica): `POST /v1/adesoes/{id}/aprovacao` cria o cliente e a ativação numa só operação; adesão
já analisada devolve **409**; o painel chama a API do app e sincroniza na hora.

## 4. Demo 2: ativação e Clube Bulbe — João (5 min)

**Ativação:**
1. Painel → **Ativações**: 4 números, funil das etapas (clicar numa etapa filtra) e clientes parados com a barra do
   prazo de 90 dias.
2. Abrir a ficha do **Marcos Andrade** → **Mudar etapa no app** para a próxima → "Atualizar no app".
3. App: entrar como Marcos (CPF 529.982.247-25) → a etapa já mudou.

**Clube Bulbe (cartas semanais):**
4. App → Vantagens → abrir a carta da semana → mostrar o **cupom sorteado** (cada cliente recebe um cupom aleatório do
   catálogo, sem repetir o da semana anterior).
5. Painel → **Parceiros e cupons**: mostrar o catálogo; cadastrar um cupom novo (ex.: parceiro existente, "20% de
   desconto", prefixo `TESTE20`, peso 5) → *entra no sorteio da próxima carta*.
6. Topo do painel → **+7 dias** (relógio de demonstração). App: a próxima carta liberou. Abrir.
7. **+7 dias** de novo → a carta da 5ª semana é a **especial**: sempre **R$ 50 de desconto na fatura**. Abrir e mostrar.
8. Topo do painel → **Hoje** (volta a data real).

Por trás: um **relógio único** (`app/core/relogio.py`) usado por todos os serviços, com deslocamento salvo no banco e
desligado em produção; sorteio **ponderado** pelo peso do cupom; validade dos cupons recalculada pela data do relógio.

## 5. Demo 3: Fale conosco e painel — Gabriel (5 min)

**Chat (o ponto alto — app e painel lado a lado):**
1. App (logado como Marcos) → menu → **Fale conosco** → nova conversa → tocar em "Prazo da minha conexão": o
   **assistente automático** responde com a **etapa real** do cliente.
2. Tocar em **"Falar com um atendente"** → a conversa entra na fila.
3. Painel → **Atendimentos** (o contador do menu sobe; "Buscar novos no app" se quiser na hora) → clicar na conversa
   → abre o **chat** → responder: *"Oi, Marcos! Aqui é a Paula, da Bulbe. Sua conexão está na análise da CEMIG…"*.
4. A resposta aparece **no app em ~2 segundos**, com o nome da atendente. Trocar mais uma mensagem e **Encerrar**.

**Painel (visão da equipe):**
5. **Visão geral**: indicadores, economia por mês, clientes por status, funil e widgets.
6. **Dicas**: arrastar uma dica do acervo para a vitrine → **Confirmar alterações** → recarregar o app: o carrossel
   mudou. Mostrar o cadastro de nova dica com o seletor de ícones.
7. (Se houver chave da IA) **Assistente** lateral: "Quais clientes estão parados há mais de 30 dias?".

Por trás: atendimento com status `bot → aguardando_atendente → em_atendimento → resolvido`; atualização por *polling*
com `depois_de=<última mensagem>` (só busca o que é novo); vitrine validada no back-end (**exatamente 5**, senão 422).

## 6. Qualidade e segurança — Rodrigo (3 min)

- **Testes:** 319 no back-end e 214 no painel (pytest), jornada real no navegador (Playwright), teste dos dois sistemas
  integrados e verificação de que o front original foi preservado. CI no GitHub Actions.
- **Documentação:** OpenAPI/Swagger gerado, README, INTEGRATION.md, docs do banco e do painel.
- **Segurança e LGPD no painel:** senhas com hash, bloqueio após tentativas, auditoria de quem abriu cada ficha,
  retenção/expurgo de dados, CSP sem scripts externos, perfis de acesso.

## 7. Encerramento — Samuel (2 min)

- **Aprendizados:** projetar a API como fonte da verdade, integrar sistemas sem duplicar regra, testar de ponta a ponta.
- **Próximos passos** (seção 6 do `PLANO-DE-FINALIZACAO.md`): token de cliente nas rotas do app, notificações,
  faturas reais na API, PostgreSQL com Docker, o assistente sugerindo respostas ao atendente.
- **Extensão universitária** e agradecimento à Bulbe.

---

## Perguntas prováveis da banca (e quem responde)

| Pergunta | Resposta curta | Quem |
|---|---|---|
| Por que o painel tem banco próprio? | Para não acoplar o painel ao banco do app: ele sincroniza e **escreve só pela API**, respeitando as regras. | Luiz |
| E se dois atendentes responderem ao mesmo tempo? | As mensagens são gravadas em ordem pela API e cada resposta leva o nome de quem respondeu; o cliente vê todas, na ordem. | Gabriel |
| Como garantem que o cupom é aleatório e justo? | Sorteio ponderado pelo peso no back-end, evitando repetir o da semana anterior; testado com semente fixa. | João |
| O relógio de demonstração não é perigoso em produção? | Ele é ignorado com `BULBE_AMBIENTE=producao` e as rotas devolvem 404; o JWT usa sempre a hora real. | João |
| Por que *polling* e não WebSocket? | Simples e confiável para a demonstração; só busca mensagens novas (`depois_de`). WebSocket/SSE é melhoria futura. | Gabriel |
| Como validam o que vem do painel? | Pydantic nas duas pontas (painel e API), listas fechadas (ícones, etapas, status) e erros padronizados. | Rodrigo |
