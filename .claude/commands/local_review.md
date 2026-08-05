---
description: Configura a worktree para revisar a branch de um colega
---

# Revisão local

Sua tarefa é montar um ambiente de revisão local para a branch de um colega. Isso envolve criar uma worktree, configurar as dependências e iniciar uma nova sessão do Claude Code.

## Processo

Quando invocado com um parâmetro no formato `gh_username:branchName`:

1. **Faça o parsing da entrada**:
   - Extraia o nome de usuário do GitHub e o nome da branch do formato `username:branchname`
   - Se nenhum parâmetro for informado, peça-o no formato: `gh_username:branchName`

2. **Extraia as informações do ticket**:
   - Procure por números de ticket no nome da branch (ex.: `eng-1696`, `ENG-1696`)
   - Use isso para criar um nome curto de diretório para a worktree
   - Se nenhum ticket for encontrado, use uma versão sanitizada do nome da branch

3. **Configure o remote e a worktree**:
   - Verifique se o remote já existe usando `git remote -v`
   - Se não existir, adicione-o: `git remote add USERNAME git@github.com:USERNAME/humanlayer`
   - Faça fetch do remote: `git fetch USERNAME`
   - Crie a worktree: `git worktree add -b BRANCHNAME ~/wt/humanlayer/SHORT_NAME USERNAME/BRANCHNAME`

4. **Configure a worktree**:
   - Copie as configurações do Claude: `cp .claude/settings.local.json WORKTREE/.claude/`
   - Rode o setup: `make -C WORKTREE setup`
   - Inicialize o thoughts: `cd WORKTREE && humanlayer thoughts init --directory humanlayer`

## Tratamento de erros

- Se a worktree já existir, informe ao usuário que ele precisa removê-la primeiro
- Se o fetch do remote falhar, verifique se o usuário/repositório existe
- Se o setup falhar, informe o erro, mas continue com o lançamento

## Exemplo de uso

```
/local_review samdickson22:sam/eng-1696-hotkey-for-yolo-mode
```

Isso vai:
- Adicionar 'samdickson22' como remote
- Criar a worktree em `~/wt/humanlayer/eng-1696`
- Configurar o ambiente
