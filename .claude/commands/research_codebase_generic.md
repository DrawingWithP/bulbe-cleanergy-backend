---
description: Pesquisa a base de código de forma abrangente usando subagentes em paralelo
model: opus
---

# Pesquisar a base de código

Sua tarefa é conduzir uma pesquisa abrangente na base de código para responder às perguntas do usuário, disparando subagentes em paralelo e sintetizando as descobertas deles.

## Preparação inicial:

Quando este comando for invocado, responda com:
```
I'm ready to research the codebase. Please provide your research question or area of interest, and I'll analyze it thoroughly by exploring relevant components and connections.
```

Depois aguarde a consulta de pesquisa do usuário.

## Passos a seguir após receber a consulta de pesquisa:

1. **Leia primeiro quaisquer arquivos mencionados diretamente:**
   - Se o usuário mencionar arquivos específicos (tickets, docs, JSON), leia-os POR COMPLETO primeiro
   - **IMPORTANTE**: Use a ferramenta Read SEM parâmetros de limit/offset para ler os arquivos inteiros
   - **CRÍTICO**: Leia esses arquivos você mesmo, no contexto principal, antes de disparar quaisquer subtarefas
   - Isso garante que você tenha o contexto completo antes de decompor a pesquisa

2. **Analise e decomponha a pergunta de pesquisa:**
   - Quebre a consulta do usuário em áreas de pesquisa combináveis
   - Reserve um tempo para ultrathink sobre os padrões subjacentes, conexões e implicações arquiteturais que o usuário pode estar buscando
   - Identifique componentes, padrões ou conceitos específicos a investigar
   - Crie um plano de pesquisa usando o TodoWrite para acompanhar todas as subtarefas
   - Considere quais diretórios, arquivos ou padrões arquiteturais são relevantes

3. **Dispare subagentes em paralelo para uma pesquisa abrangente:**
   - Crie múltiplos agentes de Task para pesquisar diferentes aspectos simultaneamente

   A chave é usar esses agentes com inteligência:
   - Comece pelos agentes localizadores, para descobrir o que existe
   - Depois use os agentes analisadores sobre as descobertas mais promissoras
   - Rode vários agentes em paralelo quando estiverem buscando coisas diferentes
   - Cada agente conhece o próprio trabalho - apenas diga a ele o que você está procurando
   - Não escreva prompts detalhados sobre COMO buscar - os agentes já sabem

4. **Aguarde todos os subagentes concluírem e sintetize as descobertas:**
   - IMPORTANTE: Aguarde TODAS as tarefas de subagente concluírem antes de prosseguir
   - Compile todos os resultados dos subagentes (descobertas da base de código e do thoughts)
   - Priorize as descobertas do código vivo como fonte primária da verdade
   - Use as descobertas de thoughts/ como contexto histórico complementar
   - Conecte as descobertas entre diferentes componentes
   - Inclua caminhos de arquivo e números de linha específicos para referência
   - Verifique se todos os caminhos de thoughts/ estão corretos (ex.: thoughts/allison/, não thoughts/shared/, para arquivos pessoais)
   - Destaque padrões, conexões e decisões arquiteturais
   - Responda às perguntas específicas do usuário com evidências concretas

5. **Reúna os metadados para o documento de pesquisa:**
   - gere todos os metadados relevantes
   - Nome do arquivo: `thoughts/shared/research/YYYY-MM-DD-ENG-XXXX-description.md`
     - Formato: `YYYY-MM-DD-ENG-XXXX-description.md`, onde:
       - YYYY-MM-DD é a data de hoje
       - ENG-XXXX é o número do ticket (omita se não houver ticket)
       - description é uma breve descrição em kebab-case do tema da pesquisa
     - Exemplos:
       - Com ticket: `2025-01-08-ENG-1478-parent-child-tracking.md`
       - Sem ticket: `2025-01-08-authentication-flow.md`

6. **Gere o documento de pesquisa:**
   - Use os metadados coletados no passo 4
   - Estruture o documento com frontmatter YAML seguido do conteúdo:
     ```markdown
     ---
     date: [Current date and time with timezone in ISO format]
     researcher: [Researcher name]
     git_commit: [Current commit hash]
     branch: [Current branch name]
     repository: [Repository name]
     topic: "[User's Question/Topic]"
     tags: [research, codebase, relevant-component-names]
     status: complete
     last_updated: [Current date in YYYY-MM-DD format]
     last_updated_by: [Researcher name]
     ---

     # Research: [User's Question/Topic]

     **Date**: [Current date and time with timezone from step 4]
     **Researcher**: [Researcher name]
     **Git Commit**: [Current commit hash from step 4]
     **Branch**: [Current branch name from step 4]
     **Repository**: [Repository name]

     ## Research Question
     [Original user query]

     ## Summary
     [High-level findings answering the user's question]

     ## Detailed Findings

     ### [Component/Area 1]
     - Finding with reference ([file.ext:line](link))
     - Connection to other components
     - Implementation details

     ### [Component/Area 2]
     ...

     ## Code References
     - `path/to/file.py:123` - Description of what's there
     - `another/file.ts:45-67` - Description of the code block

     ## Architecture Insights
     [Patterns, conventions, and design decisions discovered]

     ## Historical Context (from thoughts/)
     [Relevant insights from thoughts/ directory with references]
     - `thoughts/shared/something.md` - Historical decision about X
     - `thoughts/local/notes.md` - Past exploration of Y
     Note: Paths exclude "searchable/" even if found there

     ## Related Research
     [Links to other research documents in thoughts/shared/research/]

     ## Open Questions
     [Any areas that need further investigation]
     ```

7. **Adicione permalinks do GitHub (se aplicável):**
   - Verifique se você está na branch main ou se o commit foi enviado: `git branch --show-current` e `git status`
   - Se estiver na main/master ou o commit tiver sido enviado, gere permalinks do GitHub:
     - Obtenha as informações do repositório: `gh repo view --json owner,name`
     - Crie os permalinks: `https://github.com/{owner}/{repo}/blob/{commit}/{file}#L{line}`
   - Substitua as referências locais de arquivo por permalinks no documento

8. **Sincronize e apresente as descobertas:**
   - Apresente um resumo conciso das descobertas ao usuário
   - Inclua as principais referências de arquivo para facilitar a navegação
   - Pergunte se ele tem dúvidas de acompanhamento ou precisa de esclarecimentos

9. **Trate as perguntas de acompanhamento:**
   - Se o usuário tiver perguntas de acompanhamento, acrescente ao mesmo documento de pesquisa
   - Atualize os campos de frontmatter `last_updated` e `last_updated_by` para refletir a atualização
   - Adicione `last_updated_note: "Added follow-up research for [brief description]"` ao frontmatter
   - Adicione uma nova seção: `## Follow-up Research [timestamp]`
   - Dispare novos subagentes conforme necessário para investigação adicional
   - Continue atualizando o documento e sincronizando

## Notas importantes:
- Sempre use agentes de Task em paralelo para maximizar a eficiência e minimizar o uso de contexto
- Sempre faça uma pesquisa nova na base de código - nunca dependa apenas de documentos de pesquisa existentes
- O diretório thoughts/ fornece contexto histórico para complementar as descobertas atuais
- Foque em encontrar caminhos de arquivo e números de linha concretos, para referência dos desenvolvedores
- Documentos de pesquisa devem ser autocontidos, com todo o contexto necessário
- Cada prompt de subagente deve ser específico e focado em operações somente leitura
- Considere as conexões entre componentes e os padrões arquiteturais
- Inclua contexto temporal (quando a pesquisa foi conduzida)
- Faça links para o GitHub quando possível, para referências permanentes
- Mantenha o agente principal focado na síntese, não na leitura profunda de arquivos
- Incentive os subagentes a encontrar exemplos e padrões de uso, não apenas definições
- Explore todo o diretório thoughts/, não apenas o subdiretório de pesquisa
- **Leitura de arquivos**: Sempre leia os arquivos mencionados POR COMPLETO (sem limit/offset) antes de disparar subtarefas
- **Ordem crítica**: Siga os passos numerados exatamente
  - SEMPRE leia os arquivos mencionados antes de disparar subtarefas (passo 1)
  - SEMPRE aguarde todos os subagentes concluírem antes de sintetizar (passo 4)
  - SEMPRE reúna os metadados antes de escrever o documento (passo 5 antes do passo 6)
  - NUNCA escreva o documento de pesquisa com valores de placeholder
- **Tratamento de caminhos**: O diretório thoughts/searchable/ contém hard links para busca
  - Sempre documente os caminhos removendo APENAS "searchable/" - preserve todos os outros subdiretórios
  - Exemplos de transformações corretas:
    - `thoughts/searchable/allison/old_stuff/notes.md` → `thoughts/allison/old_stuff/notes.md`
    - `thoughts/searchable/shared/prs/123.md` → `thoughts/shared/prs/123.md`
    - `thoughts/searchable/global/shared/templates.md` → `thoughts/global/shared/templates.md`
  - NUNCA troque allison/ por shared/ nem vice-versa - preserve a estrutura de diretórios exata
  - Isso garante que os caminhos estejam corretos para edição e navegação
- **Consistência do frontmatter**:
  - Sempre inclua o frontmatter no início dos documentos de pesquisa
  - Mantenha os campos do frontmatter consistentes entre todos os documentos de pesquisa
  - Atualize o frontmatter ao adicionar pesquisa de acompanhamento
  - Use snake_case para nomes de campo com várias palavras (ex.: `last_updated`, `git_commit`)
  - As tags devem ser relevantes ao tema da pesquisa e aos componentes estudados
