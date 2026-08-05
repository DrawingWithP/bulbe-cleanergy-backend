---
description: Cria planos de implementação detalhados por meio de pesquisa e iteração interativas
model: opus
---

# Plano de implementação

Sua tarefa é criar planos de implementação detalhados por meio de um processo interativo e iterativo. Você deve ser cético, minucioso e trabalhar de forma colaborativa com o usuário para produzir especificações técnicas de alta qualidade.

## Resposta inicial

Quando este comando for invocado:

1. **Verifique se foram informados parâmetros**:
   - Se um caminho de arquivo ou referência de ticket foi passado como parâmetro, pule a mensagem padrão
   - Leia imediatamente POR COMPLETO quaisquer arquivos informados
   - Inicie o processo de pesquisa

2. **Se nenhum parâmetro for informado**, responda com:
```
I'll help you create a detailed implementation plan. Let me start by understanding what we're building.

Please provide:
1. The task/ticket description (or reference to a ticket file)
2. Any relevant context, constraints, or specific requirements
3. Links to related research or previous implementations

I'll analyze this information and work with you to create a comprehensive plan.

Tip: You can also invoke this command with a ticket file directly: `/create_plan thoughts/allison/tickets/eng_1234.md`
For deeper analysis, try: `/create_plan think deeply about thoughts/allison/tickets/eng_1234.md`
```

Depois aguarde a entrada do usuário.

## Passos do processo

### Passo 1: Coleta de contexto e análise inicial

1. **Leia todos os arquivos mencionados imediatamente e POR COMPLETO**:
   - Arquivos de ticket (ex.: `thoughts/allison/tickets/eng_1234.md`)
   - Documentos de pesquisa
   - Planos de implementação relacionados
   - Quaisquer arquivos JSON/de dados mencionados
   - **IMPORTANTE**: Use a ferramenta Read SEM parâmetros de limit/offset para ler os arquivos inteiros
   - **CRÍTICO**: NÃO dispare subtarefas antes de ler esses arquivos você mesmo, no contexto principal
   - **NUNCA** leia arquivos parcialmente - se um arquivo for mencionado, leia-o por completo

2. **Dispare tarefas iniciais de pesquisa para reunir contexto**:
   Antes de fazer qualquer pergunta ao usuário, use agentes especializados para pesquisar em paralelo:

   - Use o agente **codebase-locator** para encontrar todos os arquivos relacionados ao ticket/tarefa
   - Use o agente **codebase-analyzer** para entender como a implementação atual funciona
   - Se for relevante, use o agente **thoughts-locator** para encontrar documentos de thoughts existentes sobre esta funcionalidade
   - Se um ticket do Linear for mencionado, use o agente **linear-ticket-reader** para obter os detalhes completos

   Esses agentes vão:
   - Encontrar arquivos-fonte, configurações e testes relevantes
   - Identificar os diretórios específicos em que focar (ex.: se a WUI for mencionada, eles focarão em humanlayer-wui/)
   - Rastrear o fluxo de dados e as funções-chave
   - Retornar explicações detalhadas com referências arquivo:linha

3. **Leia todos os arquivos identificados pelas tarefas de pesquisa**:
   - Depois que as tarefas de pesquisa concluírem, leia TODOS os arquivos que elas identificaram como relevantes
   - Leia-os POR COMPLETO no contexto principal
   - Isso garante que você tenha entendimento completo antes de prosseguir

4. **Analise e verifique o entendimento**:
   - Cruze os requisitos do ticket com o código real
   - Identifique quaisquer discrepâncias ou mal-entendidos
   - Anote suposições que precisam ser verificadas
   - Determine o escopo real com base na realidade da base de código

5. **Apresente o entendimento embasado e perguntas focadas**:
   ```
   Based on the ticket and my research of the codebase, I understand we need to [accurate summary].

   I've found that:
   - [Current implementation detail with file:line reference]
   - [Relevant pattern or constraint discovered]
   - [Potential complexity or edge case identified]

   Questions that my research couldn't answer:
   - [Specific technical question that requires human judgment]
   - [Business logic clarification]
   - [Design preference that affects implementation]
   ```

   Faça apenas perguntas que você genuinamente não consegue responder investigando o código.

### Passo 2: Pesquisa e descoberta

Depois de obter os esclarecimentos iniciais:

1. **Se o usuário corrigir algum mal-entendido**:
   - NÃO simplesmente aceite a correção
   - Dispare novas tarefas de pesquisa para verificar a informação correta
   - Leia os arquivos/diretórios específicos que ele mencionar
   - Só prossiga depois de ter verificado os fatos você mesmo

2. **Crie uma lista de todos de pesquisa** usando o TodoWrite, para acompanhar as tarefas de exploração

3. **Dispare subtarefas em paralelo para uma pesquisa abrangente**:
   - Crie múltiplos agentes de Task para pesquisar diferentes aspectos simultaneamente
   - Use o agente certo para cada tipo de pesquisa:

   **Para investigação mais profunda:**
   - **codebase-locator** - Para encontrar arquivos mais específicos (ex.: "encontre todos os arquivos que lidam com [componente específico]")
   - **codebase-analyzer** - Para entender detalhes de implementação (ex.: "analise como [sistema] funciona")
   - **codebase-pattern-finder** - Para encontrar funcionalidades semelhantes que possam servir de modelo

   **Para contexto histórico:**
   - **thoughts-locator** - Para encontrar pesquisas, planos ou decisões sobre esta área
   - **thoughts-analyzer** - Para extrair os insights principais dos documentos mais relevantes

   **Para tickets relacionados:**
   - **linear-searcher** - Para encontrar issues semelhantes ou implementações passadas

   Cada agente sabe como:
   - Encontrar os arquivos e padrões de código certos
   - Identificar convenções e padrões a seguir
   - Procurar pontos de integração e dependências
   - Retornar referências arquivo:linha específicas
   - Encontrar testes e exemplos

3. **Aguarde TODAS as subtarefas concluírem** antes de prosseguir

4. **Apresente as descobertas e as opções de design**:
   ```
   Based on my research, here's what I found:

   **Current State:**
   - [Key discovery about existing code]
   - [Pattern or convention to follow]

   **Design Options:**
   1. [Option A] - [pros/cons]
   2. [Option B] - [pros/cons]

   **Open Questions:**
   - [Technical uncertainty]
   - [Design decision needed]

   Which approach aligns best with your vision?
   ```

### Passo 3: Desenvolvimento da estrutura do plano

Uma vez alinhados quanto à abordagem:

1. **Crie o esboço inicial do plano**:
   ```
   Here's my proposed plan structure:

   ## Overview
   [1-2 sentence summary]

   ## Implementation Phases:
   1. [Phase name] - [what it accomplishes]
   2. [Phase name] - [what it accomplishes]
   3. [Phase name] - [what it accomplishes]

   Does this phasing make sense? Should I adjust the order or granularity?
   ```

2. **Obtenha feedback sobre a estrutura** antes de escrever os detalhes

### Passo 4: Escrita detalhada do plano

Após a aprovação da estrutura:

1. **Escreva o plano** em `thoughts/shared/plans/YYYY-MM-DD-ENG-XXXX-description.md`
   - Formato: `YYYY-MM-DD-ENG-XXXX-description.md`, onde:
     - YYYY-MM-DD é a data de hoje
     - ENG-XXXX é o número do ticket (omita se não houver ticket)
     - description é uma breve descrição em kebab-case
   - Exemplos:
     - Com ticket: `2025-01-08-ENG-1478-parent-child-tracking.md`
     - Sem ticket: `2025-01-08-improve-error-handling.md`
2. **Use esta estrutura de template**:

````markdown
# [Feature/Task Name] Implementation Plan

## Overview

[Brief description of what we're implementing and why]

## Current State Analysis

[What exists now, what's missing, key constraints discovered]

## Desired End State

[A Specification of the desired end state after this plan is complete, and how to verify it]

### Key Discoveries:
- [Important finding with file:line reference]
- [Pattern to follow]
- [Constraint to work within]

## What We're NOT Doing

[Explicitly list out-of-scope items to prevent scope creep]

## Implementation Approach

[High-level strategy and reasoning]

## Phase 1: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Changes Required:

#### 1. [Component/File Group]
**File**: `path/to/file.ext`
**Changes**: [Summary of changes]

```[language]
// Specific code to add/modify
```

### Success Criteria:

#### Automated Verification:
- [ ] Migration applies cleanly: `make migrate`
- [ ] Unit tests pass: `make test-component`
- [ ] Type checking passes: `npm run typecheck`
- [ ] Linting passes: `make lint`
- [ ] Integration tests pass: `make test-integration`

#### Manual Verification:
- [ ] Feature works as expected when tested via UI
- [ ] Performance is acceptable under load
- [ ] Edge case handling verified manually
- [ ] No regressions in related features

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: [Descriptive Name]

[Similar structure with both automated and manual success criteria...]

---

## Testing Strategy

### Unit Tests:
- [What to test]
- [Key edge cases]

### Integration Tests:
- [End-to-end scenarios]

### Manual Testing Steps:
1. [Specific step to verify feature]
2. [Another verification step]
3. [Edge case to test manually]

## Performance Considerations

[Any performance implications or optimizations needed]

## Migration Notes

[If applicable, how to handle existing data/systems]

## References

- Original ticket: `thoughts/allison/tickets/eng_XXXX.md`
- Related research: `thoughts/shared/research/[relevant].md`
- Similar implementation: `[file:line]`
````

### Passo 5: Sincronizar e revisar

1. **Sincronize o diretório thoughts**:
   - Rode `humanlayer thoughts sync` para sincronizar o plano recém-criado
   - Isso garante que o plano seja indexado corretamente e fique disponível

2. **Apresente a localização do rascunho do plano**:
   ```
   I've created the initial implementation plan at:
   `thoughts/shared/plans/YYYY-MM-DD-ENG-XXXX-description.md`

   Please review it and let me know:
   - Are the phases properly scoped?
   - Are the success criteria specific enough?
   - Any technical details that need adjustment?
   - Missing edge cases or considerations?
   ```

3. **Itere com base no feedback** - esteja pronto para:
   - Adicionar fases faltantes
   - Ajustar a abordagem técnica
   - Esclarecer os critérios de sucesso (automatizados e manuais)
   - Adicionar/remover itens de escopo
   - Depois de fazer alterações, rode `humanlayer thoughts sync` novamente

4. **Continue refinando** até o usuário ficar satisfeito

## Diretrizes importantes

1. **Seja cético**:
   - Questione requisitos vagos
   - Identifique possíveis problemas cedo
   - Pergunte "por quê" e "e se"
   - Não presuma - verifique no código

2. **Seja interativo**:
   - Não escreva o plano inteiro de uma vez
   - Obtenha concordância a cada etapa importante
   - Permita correções de rota
   - Trabalhe de forma colaborativa

3. **Seja minucioso**:
   - Leia todos os arquivos de contexto POR COMPLETO antes de planejar
   - Pesquise os padrões reais de código usando subtarefas em paralelo
   - Inclua caminhos de arquivo e números de linha específicos
   - Escreva critérios de sucesso mensuráveis, com distinção clara entre automatizados e manuais
   - os passos automatizados devem usar `make` sempre que possível - por exemplo, `make -C humanlayer-wui check` em vez de `cd humanlayer-wui && bun run fmt`

4. **Seja prático**:
   - Foque em mudanças incrementais e testáveis
   - Considere migração e rollback
   - Pense nos casos extremos
   - Inclua o "o que NÃO vamos fazer"

5. **Acompanhe o progresso**:
   - Use o TodoWrite para acompanhar as tarefas de planejamento
   - Atualize os todos conforme concluir a pesquisa
   - Marque as tarefas de planejamento como concluídas quando terminar

6. **Sem perguntas em aberto no plano final**:
   - Se você encontrar perguntas em aberto durante o planejamento, PARE
   - Pesquise ou peça esclarecimentos imediatamente
   - NÃO escreva o plano com perguntas não resolvidas
   - O plano de implementação precisa ser completo e acionável
   - Toda decisão deve ser tomada antes de finalizar o plano

## Diretrizes dos critérios de sucesso

**Sempre separe os critérios de sucesso em duas categorias:**

1. **Verificação automatizada** (pode ser executada por agentes de execução):
   - Comandos que podem ser rodados: `make test`, `npm run lint` etc.
   - Arquivos específicos que devem existir
   - Compilação/checagem de tipos do código
   - Suítes de teste automatizadas

2. **Verificação manual** (requer teste humano):
   - Funcionalidade de UI/UX
   - Performance em condições reais
   - Casos extremos difíceis de automatizar
   - Critérios de aceitação do usuário

**Exemplo de formato:**
```markdown
### Success Criteria:

#### Automated Verification:
- [ ] Database migration runs successfully: `make migrate`
- [ ] All unit tests pass: `go test ./...`
- [ ] No linting errors: `golangci-lint run`
- [ ] API endpoint returns 200: `curl localhost:8080/api/new-endpoint`

#### Manual Verification:
- [ ] New feature appears correctly in the UI
- [ ] Performance is acceptable with 1000+ items
- [ ] Error messages are user-friendly
- [ ] Feature works correctly on mobile devices
```

## Padrões comuns

### Para mudanças de banco de dados:
- Comece pelo schema/migração
- Adicione os métodos de store
- Atualize a lógica de negócio
- Exponha via API
- Atualize os clientes

### Para novas funcionalidades:
- Pesquise primeiro os padrões existentes
- Comece pelo modelo de dados
- Construa a lógica de backend
- Adicione os endpoints de API
- Implemente a UI por último

### Para refatoração:
- Documente o comportamento atual
- Planeje mudanças incrementais
- Mantenha a retrocompatibilidade
- Inclua a estratégia de migração

## Boas práticas ao disparar subtarefas

Ao disparar subtarefas de pesquisa:

1. **Dispare várias tarefas em paralelo**, por eficiência
2. **Cada tarefa deve ser focada** em uma área específica
3. **Forneça instruções detalhadas**, incluindo:
   - Exatamente o que buscar
   - Em quais diretórios focar
   - Que informação extrair
   - Formato de saída esperado
4. **Seja EXTREMAMENTE específico quanto aos diretórios**:
   - Se o ticket menciona a "WUI", especifique o diretório `humanlayer-wui/`
   - Se menciona o "daemon", especifique o diretório `hld/`
   - Nunca use termos genéricos como "UI" quando você quer dizer "WUI"
   - Inclua o contexto de caminho completo nos seus prompts
5. **Especifique as ferramentas somente leitura** a serem usadas
6. **Peça referências arquivo:linha específicas** nas respostas
7. **Aguarde todas as tarefas concluírem** antes de sintetizar
8. **Verifique os resultados das subtarefas**:
   - Se uma subtarefa retornar resultados inesperados, dispare tarefas de acompanhamento
   - Confronte as descobertas com a base de código real
   - Não aceite resultados que pareçam incorretos

Exemplo de disparo de várias tarefas:
```python
# Spawn these tasks concurrently:
tasks = [
    Task("Research database schema", db_research_prompt),
    Task("Find API patterns", api_research_prompt),
    Task("Investigate UI components", ui_research_prompt),
    Task("Check test patterns", test_research_prompt)
]
```

## Exemplo de fluxo de interação

```
User: /create_plan
Assistant: I'll help you create a detailed implementation plan...

User: We need to add parent-child tracking for Claude sub-tasks. See thoughts/allison/tickets/eng_1478.md
Assistant: Let me read that ticket file completely first...

[Reads file fully]

Based on the ticket, I understand we need to track parent-child relationships for Claude sub-task events in the hld daemon. Before I start planning, I have some questions...

[Interactive process continues...]
```
