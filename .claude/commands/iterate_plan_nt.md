---
description: Itera sobre planos de implementação existentes, com pesquisa aprofundada e atualizações
model: opus
---

# Iterar plano de implementação

Sua tarefa é atualizar planos de implementação existentes com base no feedback do usuário. Você deve ser cético, minucioso e garantir que as mudanças estejam ancoradas na realidade concreta da base de código.

## Resposta inicial

Quando este comando for invocado:

1. **Faça o parsing da entrada para identificar**:
   - Caminho do arquivo do plano (ex.: `thoughts/shared/plans/2025-10-16-feature.md`)
   - Mudanças/feedback solicitados

2. **Trate os diferentes cenários de entrada**:

   **Se NENHUM arquivo de plano for informado**:
   ```
   I'll help you iterate on an existing implementation plan.

   Which plan would you like to update? Please provide the path to the plan file (e.g., `thoughts/shared/plans/2025-10-16-feature.md`).

   Tip: You can list recent plans with `ls -lt thoughts/shared/plans/ | head`
   ```
   Aguarde a entrada do usuário e então verifique novamente se há feedback.

   **Se o arquivo do plano for informado, mas NÃO houver feedback**:
   ```
   I've found the plan at [path]. What changes would you like to make?

   For example:
   - "Add a phase for migration handling"
   - "Update the success criteria to include performance tests"
   - "Adjust the scope to exclude feature X"
   - "Split Phase 2 into two separate phases"
   ```
   Aguarde a entrada do usuário.

   **Se AMBOS, o arquivo do plano E o feedback, forem informados**:
   - Prossiga imediatamente para o Passo 1
   - Nenhuma pergunta preliminar é necessária

## Passos do processo

### Passo 1: Ler e entender o plano atual

1. **Leia o arquivo do plano existente POR COMPLETO**:
   - Use a ferramenta Read SEM parâmetros de limit/offset
   - Entenda a estrutura, as fases e o escopo atuais
   - Anote os critérios de sucesso e a abordagem de implementação

2. **Entenda as mudanças solicitadas**:
   - Analise o que o usuário quer adicionar/modificar/remover
   - Identifique se as mudanças exigem pesquisa na base de código
   - Determine o escopo da atualização

### Passo 2: Pesquisar, se necessário

**Só dispare tarefas de pesquisa se as mudanças exigirem novo entendimento técnico.**

Se o feedback do usuário exigir entender novos padrões de código ou validar suposições:

1. **Crie uma lista de todos de pesquisa** usando o TodoWrite

2. **Dispare subtarefas em paralelo para a pesquisa**:
   Use o agente certo para cada tipo de pesquisa:

   **Para investigação de código:**
   - **codebase-locator** - Para encontrar os arquivos relevantes
   - **codebase-analyzer** - Para entender os detalhes de implementação
   - **codebase-pattern-finder** - Para encontrar padrões semelhantes

   **Seja EXTREMAMENTE específico quanto aos diretórios**:
   - Inclua o contexto de caminho completo nos prompts

3. **Leia quaisquer novos arquivos identificados pela pesquisa**:
   - Leia-os POR COMPLETO no contexto principal
   - Cruze com os requisitos do plano

4. **Aguarde TODAS as subtarefas concluírem** antes de prosseguir

### Passo 3: Apresentar o entendimento e a abordagem

Antes de fazer mudanças, confirme seu entendimento:

```
Based on your feedback, I understand you want to:
- [Change 1 with specific detail]
- [Change 2 with specific detail]

My research found:
- [Relevant code pattern or constraint]
- [Important discovery that affects the change]

I plan to update the plan by:
1. [Specific modification to make]
2. [Another modification]

Does this align with your intent?
```

Obtenha a confirmação do usuário antes de prosseguir.

### Passo 4: Atualizar o plano

1. **Faça edições focadas e precisas** no plano existente:
   - Use a ferramenta Edit para mudanças cirúrgicas
   - Mantenha a estrutura existente, a menos que a mudança seja explicitamente nela
   - Mantenha todas as referências arquivo:linha precisas
   - Atualize os critérios de sucesso, se necessário

2. **Garanta consistência**:
   - Se adicionar uma nova fase, garanta que ela siga o padrão existente
   - Se modificar o escopo, atualize a seção "What We're NOT Doing"
   - Se mudar a abordagem, atualize a seção "Implementation Approach"
   - Mantenha a distinção entre critérios de sucesso automatizados e manuais

3. **Preserve os padrões de qualidade**:
   - Inclua caminhos de arquivo e números de linha específicos para o novo conteúdo
   - Escreva critérios de sucesso mensuráveis
   - Use comandos `make` para a verificação automatizada
   - Mantenha a linguagem clara e acionável

### Passo 5: Sincronizar e revisar

**Apresente as mudanças feitas**:
   ```
   I've updated the plan at `thoughts/shared/plans/[filename].md`

   Changes made:
   - [Specific change 1]
   - [Specific change 2]

   The updated plan now:
   - [Key improvement]
   - [Another improvement]

   Would you like any further adjustments?
   ```

**Esteja pronto para iterar mais** com base no feedback

## Diretrizes importantes

1. **Seja cético**:
   - Não aceite cegamente pedidos de mudança que pareçam problemáticos
   - Questione feedbacks vagos - peça esclarecimentos
   - Verifique a viabilidade técnica com pesquisa no código
   - Aponte possíveis conflitos com as fases existentes do plano

2. **Seja cirúrgico**:
   - Faça edições precisas, não reescritas completas
   - Preserve o bom conteúdo que não precisa mudar
   - Pesquise apenas o necessário para as mudanças específicas
   - Não sobre-engenharize as atualizações

3. **Seja minucioso**:
   - Leia todo o plano existente antes de fazer mudanças
   - Pesquise padrões de código se as mudanças exigirem novo entendimento técnico
   - Garanta que as seções atualizadas mantenham os padrões de qualidade
   - Verifique se os critérios de sucesso continuam mensuráveis

4. **Seja interativo**:
   - Confirme o entendimento antes de fazer mudanças
   - Mostre o que você pretende mudar antes de fazê-lo
   - Permita correções de rota
   - Não desapareça na pesquisa sem se comunicar

5. **Acompanhe o progresso**:
   - Use o TodoWrite para acompanhar as tarefas de atualização, se for complexo
   - Atualize os todos conforme concluir a pesquisa
   - Marque as tarefas como concluídas quando terminar

6. **Sem perguntas em aberto**:
   - Se a mudança solicitada levantar dúvidas, PERGUNTE
   - Pesquise ou obtenha esclarecimentos imediatamente
   - NÃO atualize o plano com perguntas não resolvidas
   - Toda mudança deve ser completa e acionável

## Diretrizes dos critérios de sucesso

Ao atualizar os critérios de sucesso, sempre mantenha a estrutura de duas categorias:

1. **Verificação automatizada** (pode ser executada por agentes de execução):
   - Comandos que podem ser rodados: `make test`, `npm run lint` etc.
   - Arquivos específicos que devem existir
   - Compilação/checagem de tipos do código

2. **Verificação manual** (requer teste humano):
   - Funcionalidade de UI/UX
   - Performance em condições reais
   - Casos extremos difíceis de automatizar
   - Critérios de aceitação do usuário

## Boas práticas ao disparar subtarefas

Ao disparar subtarefas de pesquisa:

1. **Só dispare se for realmente necessário** - não pesquise para mudanças simples
2. **Dispare várias tarefas em paralelo**, por eficiência
3. **Cada tarefa deve ser focada** em uma área específica
4. **Forneça instruções detalhadas**, incluindo:
   - Exatamente o que buscar
   - Em quais diretórios focar
   - Que informação extrair
   - Formato de saída esperado
5. **Peça referências arquivo:linha específicas** nas respostas
6. **Aguarde todas as tarefas concluírem** antes de sintetizar
7. **Verifique os resultados das subtarefas** - se algo parecer estranho, dispare tarefas de acompanhamento

## Exemplos de fluxo de interação

**Cenário 1: O usuário fornece tudo de uma vez**
```
User: /iterate_plan thoughts/shared/plans/2025-10-16-feature.md - add phase for error handling
Assistant: [Reads plan, researches error handling patterns, updates plan]
```

**Cenário 2: O usuário fornece apenas o arquivo do plano**
```
User: /iterate_plan thoughts/shared/plans/2025-10-16-feature.md
Assistant: I've found the plan. What changes would you like to make?
User: Split Phase 2 into two phases - one for backend, one for frontend
Assistant: [Proceeds with update]
```

**Cenário 3: O usuário não fornece nenhum argumento**
```
User: /iterate_plan
Assistant: Which plan would you like to update? Please provide the path...
User: thoughts/shared/plans/2025-10-16-feature.md
Assistant: I've found the plan. What changes would you like to make?
User: Add more specific success criteria to phase 4
Assistant: [Proceeds with update]
```
