---
description: Pesquisa o ticket de maior prioridade no Linear que precisa de investigação
---

## PARTE I - SE UM TICKET DO LINEAR FOR MENCIONADO

0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para entender qual pesquisa é necessária e quais tentativas já foram feitas

## PARTE I - SE NENHUM TICKET FOR MENCIONADO

0.  leia o .claude/commands/linear.md
0a. busque os 10 itens de maior prioridade no linear com status "research needed" usando as ferramentas MCP, anotando todos os itens da seção `links`
0b. selecione a issue SMALL ou XS de maior prioridade da lista (se não existir nenhuma issue SMALL ou XS, SAIA IMEDIATAMENTE e informe o usuário)
0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para entender qual pesquisa é necessária e quais tentativas já foram feitas

## PARTE II - PRÓXIMOS PASSOS

pense a fundo

1. mova o item para "research in progress" usando as ferramentas MCP
1a. leia quaisquer documentos vinculados na seção `links` para entender o contexto
1b. se não houver informação suficiente para conduzir a pesquisa, adicione um comentário pedindo esclarecimentos e mova de volta para "research needed"

pense a fundo sobre as necessidades da pesquisa

2. conduza a pesquisa:
2a. leia o .claude/commands/research_codebase.md para orientações sobre pesquisa eficaz na base de código
2b. se os comentários do linear sugerirem que é necessária pesquisa na web, use o WebSearch para pesquisar soluções externas, APIs ou boas práticas
2c. busque na base de código por implementações e padrões relevantes
2d. examine funcionalidades semelhantes existentes ou código relacionado
2e. identifique restrições e oportunidades técnicas
2f. Seja imparcial - não pense demais em um plano de implementação ideal; apenas documente todos os arquivos relacionados e como os sistemas funcionam hoje
2g. documente as descobertas em um novo documento de thoughts: `thoughts/shared/research/YYYY-MM-DD-ENG-XXXX-description.md`
   - Formato: `YYYY-MM-DD-ENG-XXXX-description.md`, onde:
     - YYYY-MM-DD é a data de hoje
     - ENG-XXXX é o número do ticket (omita se não houver ticket)
     - description é uma breve descrição em kebab-case do tema da pesquisa
   - Exemplos:
     - Com ticket: `2025-01-08-ENG-1478-parent-child-tracking.md`
     - Sem ticket: `2025-01-08-error-handling-patterns.md`

pense a fundo sobre as descobertas

3. sintetize a pesquisa em insights acionáveis:
3a. resuma as principais descobertas e decisões técnicas
3b. identifique possíveis abordagens de implementação
3c. anote quaisquer riscos ou preocupações identificados
3d. rode `humanlayer thoughts sync` para salvar a pesquisa

4. atualize o ticket:
4a. anexe o documento de pesquisa ao ticket usando as ferramentas MCP, com a formatação de link adequada
4b. adicione um comentário resumindo os resultados da pesquisa
4c. mova o item para "research in review" usando as ferramentas MCP

pense a fundo e use o TodoWrite para acompanhar suas tarefas. Ao buscar no linear, pegue os 10 itens de maior prioridade, mas trabalhe em apenas UM item - especificamente a issue de maior prioridade.

## PARTE III - Quando você terminar

Imprima uma mensagem para o usuário (substitua os placeholders pelos valores reais):

```
✅ Completed research for ENG-XXXX: [ticket title]

Research topic: [research topic description]

The research has been:

Created at thoughts/shared/research/YYYY-MM-DD-ENG-XXXX-description.md
Synced to thoughts repository
Attached to the Linear ticket
Ticket moved to "research in review" status

Key findings:
- [Major finding 1]
- [Major finding 2]
- [Major finding 3]

View the ticket: https://linear.app/humanlayer/issue/ENG-XXXX/[ticket-slug]
```
