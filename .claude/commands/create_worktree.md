
---
description: Cria a worktree e inicia a sessão de implementação de um plano
---

2. configure a worktree para a implementação:
2a. leia o `hack/create_worktree.sh` e crie uma nova worktree com o nome de branch do Linear: `./hack/create_worktree.sh ENG-XXXX BRANCH_NAME`

3. determine os dados necessários:

nome da branch
caminho do arquivo do plano (use apenas o caminho relativo)
prompt de lançamento
comando a executar

**USO IMPORTANTE DOS CAMINHOS:**
- O diretório thoughts/ é sincronizado entre o repositório principal e as worktrees
- Sempre use APENAS o caminho relativo iniciando com `thoughts/shared/...`, sem nenhum prefixo de diretório
- Exemplo: `thoughts/shared/plans/fix-mcp-keepalive-proper.md` (não o caminho absoluto completo)
- Isso funciona porque os thoughts são sincronizados e ficam acessíveis a partir da worktree

3a. confirme com o usuário enviando uma mensagem ao humano

```
based on the input, I plan to create a worktree with the following details:

worktree path: ~/wt/humanlayer/ENG-XXXX
branch name: BRANCH_NAME
path to plan file: $FILEPATH
launch prompt:

    /implement_plan at $FILEPATH and when you are done implementing and all tests pass, read ./claude/commands/commit.md and create a commit, then read ./claude/commands/describe_pr.md and create a PR, then add a comment to the Linear ticket with the PR link

command to run:

    humanlayer launch --model opus -w ~/wt/humanlayer/ENG-XXXX "/implement_plan at $FILEPATH and when you are done implementing and all tests pass, read ./claude/commands/commit.md and create a commit, then read ./claude/commands/describe_pr.md and create a PR, then add a comment to the Linear ticket with the PR link"
```

incorpore qualquer feedback do usuário e então:

4. inicie a sessão de implementação: `humanlayer launch --model opus -w ~/wt/humanlayer/ENG-XXXX "/implement_plan at $FILEPATH and when you are done implementing and all tests pass, read ./claude/commands/commit.md and create a commit, then read ./claude/commands/describe_pr.md and create a PR, then add a comment to the Linear ticket with the PR link"`
