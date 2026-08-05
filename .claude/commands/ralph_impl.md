---
description: Implementa o ticket pequeno de maior prioridade no Linear, com configuração de worktree
model: sonnet
---

## PARTE I - SE UM TICKET FOR MENCIONADO

0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para entender o plano de implementação e quaisquer preocupações

## PARTE I - SE NENHUM TICKET FOR MENCIONADO

0.  leia o .claude/commands/linear.md
0a. busque os 10 itens de maior prioridade no linear com status "ready for dev" usando as ferramentas MCP, anotando todos os itens da seção `links`
0b. selecione a issue SMALL ou XS de maior prioridade da lista (se não existir nenhuma issue SMALL ou XS, SAIA IMEDIATAMENTE e informe o usuário)
0c. use a cli `linear` para buscar o item selecionado no thoughts, com o número do ticket - ./thoughts/shared/tickets/ENG-xxxx.md
0d. leia o ticket e todos os comentários para entender o plano de implementação e quaisquer preocupações

## PARTE II - PRÓXIMOS PASSOS

pense a fundo

1. mova o item para "in dev" usando as ferramentas MCP
1a. identifique o documento de plano de implementação vinculado na seção `links`
1b. se não existir plano, mova o ticket de volta para "ready for spec" e SAIA com uma explicação

pense a fundo sobre a implementação

2. configure a worktree para a implementação:
2a. leia o `hack/create_worktree.sh` e crie uma nova worktree com o nome de branch do Linear: `./hack/create_worktree.sh ENG-XXXX BRANCH_NAME`
2b. inicie a sessão de implementação: `humanlayer-nightly launch --model opus --dangerously-skip-permissions --dangerously-skip-permissions-timeout 15m --title "implement ENG-XXXX" -w ~/wt/humanlayer/ENG-XXXX "/implement_plan and when you are done implementing and all tests pass, read ./claude/commands/commit.md and create a commit, then read ./claude/commands/describe_pr.md and create a PR, then add a comment to the Linear ticket with the PR link"`

pense a fundo e use o TodoWrite para acompanhar suas tarefas. Ao buscar no linear, pegue os 10 itens de maior prioridade, mas trabalhe em apenas UM item - especificamente a issue de tamanho SMALL ou XS com maior prioridade.
