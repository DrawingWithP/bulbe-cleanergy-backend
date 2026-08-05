---
description: Retoma o trabalho a partir de um documento de handoff, com análise de contexto e validação
---

# Retomar o trabalho a partir de um documento de handoff

Sua tarefa é retomar o trabalho a partir de um documento de handoff, por meio de um processo interativo. Esses handoffs contêm contexto crítico, aprendizados e próximos passos de sessões de trabalho anteriores, que precisam ser compreendidos e continuados.

## Resposta inicial

Quando este comando for invocado:

1. **Se o caminho de um documento de handoff for informado**:
   - Se um caminho de documento de handoff foi passado como parâmetro, pule a mensagem padrão
   - Leia imediatamente o documento de handoff POR COMPLETO
   - Leia imediatamente quaisquer documentos de pesquisa ou plano vinculados a ele em `thoughts/shared/plans` ou `thoughts/shared/research`. NÃO use um subagente para ler esses arquivos críticos.
   - Comece o processo de análise incorporando o contexto relevante do documento de handoff e lendo os arquivos adicionais que ele menciona
   - Depois proponha um curso de ação ao usuário e confirme, ou peça esclarecimentos sobre a direção.

2. **Se um número de ticket (como ENG-XXXX) for informado**:
   - rode `humanlayer thoughts sync` para garantir que seu diretório `thoughts/` está atualizado.
   - localize o documento de handoff mais recente do ticket. Os tickets ficam em `thoughts/shared/handoffs/ENG-XXXX`, onde `ENG-XXXX` é o número do ticket. Ex.: para `ENG-2124`, os handoffs estariam em `thoughts/shared/handoffs/ENG-2124/`. **Liste o conteúdo desse diretório.**
   - Pode haver zero, um ou vários arquivos no diretório.
   - **Se houver zero arquivos no diretório, ou se o diretório não existir**: diga ao usuário: "Desculpe, não consegui encontrar esse documento de handoff. Você pode me informar o caminho dele?"
   - **Se houver apenas um arquivo no diretório**: prossiga com esse handoff
   - **Se houver vários arquivos no diretório**: usando a data e a hora especificadas no nome do arquivo (estará no formato `YYYY-MM-DD_HH-MM-SS`, em formato de 24 horas), prossiga com o documento de handoff _mais recente_.
   - Leia imediatamente o documento de handoff POR COMPLETO
   - Leia imediatamente quaisquer documentos de pesquisa ou plano vinculados a ele em `thoughts/shared/plans` ou `thoughts/shared/research`; NÃO use um subagente para ler esses arquivos críticos.
   - Comece o processo de análise incorporando o contexto relevante do documento de handoff e lendo os arquivos adicionais que ele menciona
   - Depois proponha um curso de ação ao usuário e confirme, ou peça esclarecimentos sobre a direção.

3. **Se nenhum parâmetro for informado**, responda com:
```
I'll help you resume work from a handoff document. Let me find the available handoffs.

Which handoff would you like to resume from?

Tip: You can invoke this command directly with a handoff path: `/resume_handoff `thoughts/shared/handoffs/ENG-XXXX/YYYY-MM-DD_HH-MM-SS_ENG-XXXX_description.md`

or using a ticket number to resume from the most recent handoff for that ticket: `/resume_handoff ENG-XXXX`
```

Depois aguarde a entrada do usuário.

## Passos do processo

### Passo 1: Ler e analisar o handoff

1. **Leia o documento de handoff por completo**:
   - Use a ferramenta Read SEM parâmetros de limit/offset
   - Extraia todas as seções:
     - Tarefa(s) e seus status
     - Alterações recentes
     - Aprendizados
     - Artefatos
     - Itens de ação e próximos passos
     - Outras notas

2. **Dispare tarefas de pesquisa focadas**:
   Com base no conteúdo do handoff, dispare tarefas de pesquisa em paralelo para verificar o estado atual:

   ```
   Task 1 - Gather artifact context:
   Read all artifacts mentioned in the handoff.
   1. Read feature documents listed in "Artifacts"
   2. Read implementation plans referenced
   3. Read any research documents mentioned
   4. Extract key requirements and decisions
   Use tools: Read
   Return: Summary of artifact contents and key decisions
   ```

3. **Aguarde TODAS as subtarefas concluírem** antes de prosseguir

4. **Leia os arquivos críticos identificados**:
   - Leia por completo os arquivos da seção "Aprendizados"
   - Leia os arquivos de "Alterações recentes" para entender as modificações
   - Leia quaisquer novos arquivos relacionados descobertos durante a pesquisa

### Passo 2: Sintetizar e apresentar a análise

1. **Apresente uma análise completa**:
   ```
   I've analyzed the handoff from [date] by [researcher]. Here's the current situation:

   **Original Tasks:**
   - [Task 1]: [Status from handoff] → [Current verification]
   - [Task 2]: [Status from handoff] → [Current verification]

   **Key Learnings Validated:**
   - [Learning with file:line reference] - [Still valid/Changed]
   - [Pattern discovered] - [Still applicable/Modified]

   **Recent Changes Status:**
   - [Change 1] - [Verified present/Missing/Modified]
   - [Change 2] - [Verified present/Missing/Modified]

   **Artifacts Reviewed:**
   - [Document 1]: [Key takeaway]
   - [Document 2]: [Key takeaway]

   **Recommended Next Actions:**
   Based on the handoff's action items and current state:
   1. [Most logical next step based on handoff]
   2. [Second priority action]
   3. [Additional tasks discovered]

   **Potential Issues Identified:**
   - [Any conflicts or regressions found]
   - [Missing dependencies or broken code]

   Shall I proceed with [recommended action 1], or would you like to adjust the approach?
   ```

2. **Obtenha a confirmação** antes de prosseguir

### Passo 3: Criar o plano de ação

1. **Use o TodoWrite para criar a lista de tarefas**:
   - Converta os itens de ação do handoff em todos
   - Adicione quaisquer novas tarefas descobertas durante a análise
   - Priorize com base nas dependências e nas orientações do handoff

2. **Apresente o plano**:
   ```
   I've created a task list based on the handoff and current analysis:

   [Show todo list]

   Ready to begin with the first task: [task description]?
   ```

### Passo 4: Iniciar a implementação

1. **Comece pela primeira tarefa aprovada**
2. **Referencie os aprendizados do handoff** ao longo da implementação
3. **Aplique os padrões e abordagens documentados** no handoff
4. **Atualize o progresso** conforme as tarefas forem concluídas

## Diretrizes

1. **Seja completo na análise**:
   - Leia todo o documento de handoff primeiro
   - Verifique se TODAS as alterações mencionadas ainda existem
   - Verifique se há regressões ou conflitos
   - Leia todos os artefatos referenciados

2. **Seja interativo**:
   - Apresente as descobertas antes de começar o trabalho
   - Obtenha concordância sobre a abordagem
   - Permita correções de rota
   - Adapte-se com base no estado atual vs. o estado do handoff

3. **Aproveite a sabedoria do handoff**:
   - Preste atenção especial à seção "Aprendizados"
   - Aplique os padrões e abordagens documentados
   - Evite repetir os erros mencionados
   - Construa sobre as soluções descobertas

4. **Mantenha a continuidade**:
   - Use o TodoWrite para manter a continuidade das tarefas
   - Referencie o documento de handoff nos commits
   - Documente quaisquer desvios do plano original
   - Considere criar um novo handoff ao terminar

5. **Valide antes de agir**:
   - Nunca presuma que o estado do handoff corresponde ao estado atual
   - Verifique se todas as referências de arquivo ainda existem
   - Verifique se houve mudanças quebradiças desde o handoff
   - Confirme se os padrões ainda são válidos

## Cenários comuns

### Cenário 1: Continuação limpa
- Todas as alterações do handoff estão presentes
- Sem conflitos ou regressões
- Próximos passos claros nos itens de ação
- Prossiga com as ações recomendadas

### Cenário 2: Base de código divergente
- Algumas alterações estão faltando ou foram modificadas
- Novo código relacionado foi adicionado desde o handoff
- É necessário reconciliar as diferenças
- Adapte o plano com base no estado atual

### Cenário 3: Trabalho de handoff incompleto
- Tarefas marcadas como "in_progress" no handoff
- É preciso concluir primeiro o trabalho inacabado
- Pode ser necessário reentender implementações parciais
- Foque em concluir antes de iniciar trabalho novo

### Cenário 4: Handoff desatualizado
- Passou-se um tempo significativo
- Ocorreram grandes refatorações
- A abordagem original pode não se aplicar mais
- É preciso reavaliar a estratégia

## Exemplo de fluxo de interação

```
User: /resume_handoff specification/feature/handoffs/handoff-0.md
Assistant: Let me read and analyze that handoff document...

[Reads handoff completely]
[Spawns research tasks]
[Waits for completion]
[Reads identified files]

I've analyzed the handoff from [date]. Here's the current situation...

[Presents analysis]

Shall I proceed with implementing the webhook validation fix, or would you like to adjust the approach?

User: Yes, proceed with the webhook validation
Assistant: [Creates todo list and begins implementation]
```
