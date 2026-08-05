---
description: Cria o plano de implementação do ticket de maior prioridade no Linear pronto para spec
---

## PARTE I - SE UM TICKET FOR MENCIONADO

0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para conhecer implementações e pesquisas anteriores, além de quaisquer dúvidas ou preocupações sobre elas


### PARTE I - SE NENHUM TICKET FOR MENCIONADO

0.  leia o .claude/commands/linear.md
0a. busque os 10 itens de maior prioridade no linear com status "ready for spec" usando as ferramentas MCP, anotando todos os itens da seção `links`
0b. selecione a issue SMALL ou XS de maior prioridade da lista (se não existir nenhuma issue SMALL ou XS, SAIA IMEDIATAMENTE e informe o usuário)
0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para conhecer implementações e pesquisas anteriores, além de quaisquer dúvidas ou preocupações sobre elas

### PARTE II - PRÓXIMOS PASSOS

pense a fundo

1. mova o item para "plan in progress" usando as ferramentas MCP
1a. leia o ./claude/commands/create_plan.md
1b. determine se o item tem um documento de plano de implementação vinculado, com base na seção `links`
1d. se o plano existir, você terminou; responda com um link para o ticket
1e. se a pesquisa for insuficiente ou tiver perguntas sem resposta, crie um novo documento de plano seguindo as instruções em ./claude/commands/create_plan.md

pense a fundo

2. quando o plano estiver completo, rode `humanlayer thoughts sync`, anexe o documento ao ticket usando as ferramentas MCP e crie um comentário conciso com um link para ele (releia o .claude/commands/linear.md se necessário)
2a. mova o item para "plan in review" usando as ferramentas MCP

pense a fundo e use o TodoWrite para acompanhar suas tarefas. Ao buscar no linear, pegue os 10 itens de maior prioridade, mas trabalhe em apenas UM item - especificamente a issue de tamanho SMALL ou XS com maior prioridade.

### PARTE III - Quando você terminar


Imprima uma mensagem para o usuário (substitua os placeholders pelos valores reais):

```
✅ Completed implementation plan for ENG-XXXX: [ticket title]

Approach: [selected approach description]

The plan has been:

Created at thoughts/shared/plans/YYYY-MM-DD-ENG-XXXX-description.md
Synced to thoughts repository
Attached to the Linear ticket
Ticket moved to "plan in review" status

Implementation phases:
- Phase 1: [phase 1 description]
- Phase 2: [phase 2 description]
- Phase 3: [phase 3 description if applicable]

View the ticket: https://linear.app/humanlayer/issue/ENG-XXXX/[ticket-slug]
```
