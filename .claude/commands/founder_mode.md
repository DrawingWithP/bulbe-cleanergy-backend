---
description: Cria ticket no Linear e PR para funcionalidades experimentais após a implementação
---

você está trabalhando em uma funcionalidade experimental que não teve a parte de ticket e PR configurada adequadamente.

supondo que você acabou de fazer um commit, aqui estão os próximos passos:


1. obtenha o sha do commit que você acabou de fazer (se você não fez nenhum, leia o `.claude/commands/commit.md` e faça um)

2. leia o `.claude/commands/linear.md` - pense a fundo sobre o que você acabou de implementar, então crie um ticket no linear sobre o que você fez e coloque-o no estado 'in dev' - ele deve ter cabeçalhos ### para "problem to solve" e "proposed solution"
3. busque o ticket para obter o nome de branch git recomendado
4. git checkout main
5. git checkout -b 'BRANCHNAME'
6. git cherry-pick 'COMMITHASH'
7. git push -u origin 'BRANCHNAME'
8. gh pr create --fill
9. leia o '.claude/commands/describe_pr.md' e siga as instruções
