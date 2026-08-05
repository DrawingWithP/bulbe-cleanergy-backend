---
description: Valida a implementação contra o plano, verifica os critérios de sucesso e identifica problemas
---

# Validar plano

Sua tarefa é validar se um plano de implementação foi executado corretamente, verificando todos os critérios de sucesso e identificando quaisquer desvios ou problemas.

## Preparação inicial

Quando invocado:
1. **Determine o contexto** - Você está em uma conversa existente ou começando do zero?
   - Se existente: Revise o que foi implementado nesta sessão
   - Se do zero: Você precisa descobrir o que foi feito por meio do git e da análise da base de código

2. **Localize o plano**:
   - Se o caminho do plano for informado, use-o
   - Caso contrário, procure referências ao plano nos commits recentes ou pergunte ao usuário

3. **Reúna evidências da implementação**:
   ```bash
   # Check recent commits
   git log --oneline -n 20
   git diff HEAD~N..HEAD  # Where N covers implementation commits

   # Run comprehensive checks
   cd $(git rev-parse --show-toplevel) && make check test
   ```

## Processo de validação

### Passo 1: Descoberta de contexto

Se estiver começando do zero ou precisar de mais contexto:

1. **Leia o plano de implementação** por completo
2. **Identifique o que deveria ter mudado**:
   - Liste todos os arquivos que deveriam ser modificados
   - Anote todos os critérios de sucesso (automatizados e manuais)
   - Identifique as funcionalidades-chave a verificar

3. **Dispare tarefas de pesquisa em paralelo** para descobrir a implementação:
   ```
   Task 1 - Verify database changes:
   Research if migration [N] was added and schema changes match plan.
   Check: migration files, schema version, table structure
   Return: What was implemented vs what plan specified

   Task 2 - Verify code changes:
   Find all modified files related to [feature].
   Compare actual changes to plan specifications.
   Return: File-by-file comparison of planned vs actual

   Task 3 - Verify test coverage:
   Check if tests were added/modified as specified.
   Run test commands and capture results.
   Return: Test status and any missing coverage
   ```

### Passo 2: Validação sistemática

Para cada fase do plano:

1. **Verifique o status de conclusão**:
   - Procure por marcações no plano (- [x])
   - Verifique se o código real corresponde à conclusão declarada

2. **Rode a verificação automatizada**:
   - Execute cada comando de "Automated Verification"
   - Documente o status de aprovação/falha
   - Se houver falhas, investigue a causa raiz

3. **Avalie os critérios manuais**:
   - Liste o que precisa de teste manual
   - Forneça passos claros para a verificação pelo usuário

4. **Pense a fundo sobre casos extremos**:
   - As condições de erro foram tratadas?
   - Faltam validações?
   - A implementação poderia quebrar funcionalidades existentes?

### Passo 3: Gere o relatório de validação

Crie um resumo completo de validação:

```markdown
## Validation Report: [Plan Name]

### Implementation Status
✓ Phase 1: [Name] - Fully implemented
✓ Phase 2: [Name] - Fully implemented
⚠️ Phase 3: [Name] - Partially implemented (see issues)

### Automated Verification Results
✓ Build passes: `make build`
✓ Tests pass: `make test`
✗ Linting issues: `make lint` (3 warnings)

### Code Review Findings

#### Matches Plan:
- Database migration correctly adds [table]
- API endpoints implement specified methods
- Error handling follows plan

#### Deviations from Plan:
- Used different variable names in [file:line]
- Added extra validation in [file:line] (improvement)

#### Potential Issues:
- Missing index on foreign key could impact performance
- No rollback handling in migration

### Manual Testing Required:
1. UI functionality:
   - [ ] Verify [feature] appears correctly
   - [ ] Test error states with invalid input

2. Integration:
   - [ ] Confirm works with existing [component]
   - [ ] Check performance with large datasets

### Recommendations:
- Address linting warnings before merge
- Consider adding integration test for [scenario]
- Document new API endpoints
```

## Trabalhando com contexto existente

Se você participou da implementação:
- Revise o histórico da conversa
- Confira sua lista de todos para ver o que foi concluído
- Concentre a validação no trabalho feito nesta sessão
- Seja honesto sobre quaisquer atalhos ou itens incompletos

## Diretrizes importantes

1. **Seja completo, mas prático** - Foque no que importa
2. **Rode todas as verificações automatizadas** - Não pule comandos de verificação
3. **Documente tudo** - Tanto os sucessos quanto os problemas
4. **Pense criticamente** - Questione se a implementação realmente resolve o problema
5. **Considere a manutenção** - Isso será sustentável no longo prazo?

## Checklist de validação

Sempre verifique:
- [ ] Todas as fases marcadas como concluídas realmente estão prontas
- [ ] Os testes automatizados passam
- [ ] O código segue os padrões existentes
- [ ] Nenhuma regressão foi introduzida
- [ ] O tratamento de erros é robusto
- [ ] A documentação foi atualizada, se necessário
- [ ] Os passos de teste manual estão claros

## Relação com outros comandos

Fluxo recomendado:
1. `/implement_plan` - Executa a implementação
2. `/commit` - Cria commits atômicos para as alterações
3. `/validate_plan` - Verifica a correção da implementação
4. `/describe_pr` - Gera a descrição do PR

A validação funciona melhor depois que os commits são feitos, pois ela consegue analisar o histórico do git para entender o que foi implementado.

Lembre-se: uma boa validação pega problemas antes que eles cheguem à produção. Seja construtivo, mas completo ao identificar lacunas ou melhorias.
