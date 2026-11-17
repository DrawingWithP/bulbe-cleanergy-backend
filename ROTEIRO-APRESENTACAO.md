# Roteiro de apresentação — Bulbe Energia (Cleanergy Squad)

Duração: **10 minutos** cravados. O foco do projeto é o **back-end**: a demonstração mostra o app e o painel
funcionando, e cada fala termina com uma frase sobre o que a API faz por trás.

Para caber no tempo: **nada é digitado ao vivo** além de uma mensagem no chat. Logins, janelas e dados ficam prontos
antes (veja o checklist). A divisão por pessoa é uma sugestão; troquem os nomes à vontade.

| Tempo | Parte | Quem | Duração |
|---|---|---|---|
| 0:00 | Abertura: problema e solução | Samuel (líder) | 1 min |
| 1:00 | Arquitetura e back-end | Luiz | 1 min 30 s |
| 2:30 | Demo 1: adesão aprovada no painel → cliente entra no app | Rafael | 1 min 30 s |
| 4:00 | Demo 2: etapa da ativação e Clube Bulbe (relógio + cupom sorteado) | João | 2 min |
| 6:00 | Demo 3: Fale conosco (assistente automático + atendente real) | Gabriel | 2 min |
| 8:00 | Qualidade e segurança | Rodrigo | 1 min 15 s |
| 9:15 | Encerramento | Samuel | 45 s |

---

## Checklist (15 minutos antes, no computador do projetor)

1. Subir tudo com bancos limpos: `.venv\Scripts\python.exe iniciar.py` (esperar as portas 8000 e 8001).
2. **Três janelas** abertas, nesta ordem na barra de tarefas:
   - **A — App (normal, modo celular no F12):** <http://127.0.0.1:8000/frontend/final.html>, na tela inicial.
   - **B — App (janela anônima, modo celular):** já logado como **Marcos** (CPF 529.982.247-25 → código que
     aparece na tela), parado na tela de status. A janela anônima tem sessão separada da janela A.
   - **C — Painel:** <http://127.0.0.1:8001/painel/>, logado como `admin@bulbe.com.br` / `bulbe@demo123`, na
     **Visão geral**, com o assistente recolhido.
3. Conferir no topo do painel: aparece **"Data do app"** (modo demonstração).
4. CPF para a Demo 1: **168.995.350-09** (João da Silva, adesão já feita pelo app no seed).
5. Ensaiar a demo inteira uma vez e reiniciar o `iniciar.py` antes de apresentar (a demo altera os dados).
6. Plano B: prints das telas principais numa pasta. Se algo travar, seguir falando com os prints.

---

## 0:00 — Abertura · Samuel (1 min)

- Quem conhece a Bulbe hoje não consegue **simular a economia** sem login e, depois de contratar, espera até
  **90 dias** pela CEMIG **sem saber em que pé está**. A equipe também não tem uma visão única dos clientes.
- Construímos três partes: o **app** do cliente, uma **API** com as regras de negócio e um **sistema de gerenciamento**
  para a equipe.
- *"O cliente vê a ativação andar e o atendente move essa ativação — tudo pela mesma API."*

## 1:00 — Arquitetura e back-end · Luiz (1 min 30 s)

Mostrar o diagrama do README (um slide).

- **API FastAPI é a fonte da verdade** (SQLAlchemy + migrations Alembic). O app consome a API; o painel tem banco
  próprio que **sincroniza** com o app e **só escreve no app pela API**, com token de operador.
- Camadas: rotas → serviços (regras) → repositórios (banco). Erros padronizados e validação com Pydantic.
- Regras que vão aparecer na demo: aprovação de adesão, jornada de 5 etapas, sorteio de cupons, relógio de
  demonstração e atendimento com fila.

## 2:30 — Demo 1: de pedido a cliente · Rafael (1 min 30 s)

1. **Painel (C)** → **Adesões**: *"este pedido chegou pelo simulador do app"* → **Aprovar** o João da Silva → confirmar.
2. **App (A)** → **Entrar** → CPF **168.995.350-09** → código mostrado na tela → o cliente já vê a **jornada na etapa 1**.
3. Por trás: *"a aprovação cria o cliente e a ativação numa única operação da API; aprovar duas vezes devolve erro 409."*

## 4:00 — Demo 2: ativação e Clube Bulbe · João (2 min)

1. **Painel (C)** → **Clientes** → **Marcos Andrade** → *Mudar etapa no app* para a próxima → **Atualizar no app**.
2. **App (B)** → sair da tela de status e voltar (o app busca a etapa na API ao abrir a tela): a etapa do Marcos
   mudou. Não use F5: recarregar volta para a tela inicial.
3. **App (B)** → **Vantagens** → abrir a carta da semana → mostrar o **cupom sorteado**.
4. **Painel (C)** → topo → **+7 dias** → **App (B)**: a próxima carta já liberou.
5. Por trás (falar enquanto clica): *"cada cliente recebe um cupom aleatório do catálogo que a equipe cadastra no
   painel, com peso de chance e sem repetir o da semana anterior; na 5ª semana seguida a carta é especial e vale
   sempre R$ 50 na fatura. O relógio de demonstração é um único relógio usado por toda a API, e não existe em produção."*
6. **Painel (C)** → topo → **Hoje** (volta a data).

## 6:00 — Demo 3: Fale conosco · Gabriel (2 min)

1. **App (B)** → menu → **Fale conosco** → nova conversa → **"Prazo da minha conexão"**: o **assistente automático**
   responde com a etapa real do Marcos.
2. Tocar em **"Falar com um atendente"**.
3. **Painel (C)** → **Atendimentos** → *Buscar novos no app* → clicar na conversa do Marcos → responder:
   *"Oi, Marcos! Aqui é a Paula, da Bulbe. Sua conexão está na análise da CEMIG, te aviso aqui quando mudar."*
4. **App (B)**: a resposta aparece em ~2 segundos, com o nome da atendente. **Encerrar** pelo painel.
5. Por trás: *"a conversa passa por bot → aguardando atendente → em atendimento → resolvido, e o app só busca as
   mensagens novas a cada 2,5 segundos."*

## 8:00 — Qualidade e segurança · Rodrigo (1 min 15 s)

Um slide com os números:

- **319 testes** no back-end e **214** no painel, jornada real no navegador (Playwright), teste dos dois sistemas
  integrados e CI no GitHub Actions. Documentação da API gerada (Swagger/OpenAPI).
- Painel: senhas com hash, bloqueio após tentativas, perfis de acesso, **auditoria** de quem abriu cada ficha e
  **expurgo** de dados antigos (LGPD).

## 9:15 — Encerramento · Samuel (45 s)

- Aprendemos a desenhar uma API como fonte da verdade e integrar sistemas sem duplicar regras.
- Próximos passos: token de cliente nas rotas do app, notificações e banco PostgreSQL.
- Agradecimento à Bulbe e à banca.

---

## Se sobrar tempo nas perguntas, mostrar

- **Visão geral** do painel (gráficos e widgets).
- **Dicas**: arrastar uma dica para a vitrine, **Confirmar alterações** e ver o carrossel do app mudar.
- **Parceiros e cupons**: cadastrar um cupom novo que já entra no sorteio.

## Perguntas prováveis da banca

| Pergunta | Resposta curta | Quem |
|---|---|---|
| Por que o painel tem banco próprio? | Para não acoplar o painel ao banco do app: ele sincroniza e **escreve só pela API**, respeitando as regras. | Luiz |
| Como garantem que o cupom é aleatório e justo? | Sorteio ponderado pelo peso no back-end, sem repetir o da semana anterior; testado com semente fixa. | João |
| O relógio de demonstração não é perigoso em produção? | Ele é ignorado com `BULBE_AMBIENTE=producao` e as rotas devolvem 404; o login (JWT) usa sempre a hora real. | João |
| Por que *polling* e não WebSocket? | Simples e confiável; só busca mensagens novas. WebSocket fica como melhoria. | Gabriel |
| Como validam o que vem do painel? | Pydantic nas duas pontas, listas fechadas (ícones, etapas, status) e erros padronizados. | Rodrigo |
