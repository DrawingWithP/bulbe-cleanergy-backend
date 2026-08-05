---
description: Gera descrições completas de PR seguindo os templates do repositório
---

# Gerar descrição de PR

Sua tarefa é gerar uma descrição completa de pull request seguindo o template padrão do repositório.

## Passos a seguir:

1. **Leia o template de descrição de PR:**
   - Primeiro, verifique se o `thoughts/shared/pr_description.md` existe
   - Se não existir, informe ao usuário que a configuração do `humanlayer thoughts` está incompleta e que ele precisa criar um template de descrição de PR em `thoughts/shared/pr_description.md`
   - Leia o template com atenção para entender todas as seções e requisitos


2. **Identifique o PR a ser descrito:**
   - Verifique se a branch atual tem um PR associado: `gh pr view --json url,number,title,state 2>/dev/null`
   - Se não existir PR para a branch atual, ou se você estiver na main/master, liste os PRs abertos: `gh pr list --limit 10 --json number,title,headRefName,author`
   - Pergunte ao usuário qual PR ele quer descrever

3. **Verifique se já existe uma descrição:**
   - Verifique se o `thoughts/shared/prs/{number}_description.md` já existe
   - Se existir, leia-o e informe ao usuário que você vai atualizá-lo
   - Considere o que mudou desde que a última descrição foi escrita

4. **Reúna informações completas do PR:**
   - Obtenha o diff completo do PR: `gh pr diff {number}`
   - Se você receber um erro sobre não haver repositório remoto padrão, oriente o usuário a rodar `gh repo set-default` e selecionar o repositório apropriado
   - Obtenha o histórico de commits: `gh pr view {number} --json commits`
   - Revise a branch base: `gh pr view {number} --json baseRefName`
   - Obtenha os metadados do PR: `gh pr view {number} --json url,title,number,state`

5. **Analise as alterações a fundo:** (ultrathink sobre as mudanças de código, suas implicações arquiteturais e possíveis impactos)
   - Leia todo o diff com atenção
   - Para ter contexto, leia quaisquer arquivos referenciados mas não exibidos no diff
   - Entenda o propósito e o impacto de cada alteração
   - Identifique mudanças visíveis ao usuário vs. detalhes internos de implementação
   - Procure por mudanças quebradiças ou requisitos de migração

6. **Trate os requisitos de verificação:**
   - Procure por itens de checklist na seção "How to verify it" do template
   - Para cada passo de verificação:
     - Se for um comando que você pode rodar (como `make check test`, `npm test` etc.), rode-o
     - Se passar, marque a caixa: `- [x]`
     - Se falhar, deixe-a desmarcada e anote o que falhou: `- [ ]` com a explicação
     - Se exigir teste manual (interações de UI, serviços externos), deixe desmarcada e sinalize para o usuário
   - Documente quaisquer passos de verificação que você não conseguiu concluir

7. **Gere a descrição:**
   - Preencha cada seção do template de forma completa:
     - Responda a cada pergunta/seção com base na sua análise
     - Seja específico sobre os problemas resolvidos e as alterações feitas
     - Foque no impacto ao usuário quando for relevante
     - Inclua detalhes técnicos nas seções apropriadas
     - Escreva uma entrada de changelog concisa
   - Garanta que todos os itens do checklist foram tratados (marcados ou explicados)

8. **Salve e sincronize a descrição:**
   - Escreva a descrição finalizada em `thoughts/shared/prs/{number}_description.md`
   - Rode `humanlayer thoughts sync` para sincronizar o diretório thoughts
   - Mostre a descrição gerada ao usuário

9. **Atualize o PR:**
   - Atualize a descrição do PR diretamente: `gh pr edit {number} --body-file thoughts/shared/prs/{number}_description.md`
   - Confirme que a atualização foi bem-sucedida
   - Se ainda houver passos de verificação desmarcados, lembre o usuário de concluí-los antes do merge

## Notas importantes:
- Este comando funciona em diferentes repositórios - sempre leia o template local
- Seja completo, mas conciso - as descrições devem ser fáceis de escanear
- Foque tanto no "porquê" quanto no "o quê"
- Inclua eventuais mudanças quebradiças ou notas de migração em destaque
- Se o PR toca em vários componentes, organize a descrição de acordo
- Sempre tente rodar os comandos de verificação quando possível
- Comunique com clareza quais passos de verificação precisam de teste manual
