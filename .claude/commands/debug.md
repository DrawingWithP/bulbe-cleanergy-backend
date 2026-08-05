---
description: Depura problemas investigando logs, estado do banco de dados e histórico do git
---

# Debug

Sua tarefa é ajudar a depurar problemas durante testes manuais ou implementação. Este comando permite investigar problemas examinando logs, estado do banco de dados e histórico do git, sem editar arquivos. Pense nisso como uma forma de iniciar uma sessão de depuração sem consumir o contexto da janela principal.

## Resposta inicial

Quando invocado COM um arquivo de plano/ticket:
```
I'll help debug issues with [file name]. Let me understand the current state.

What specific problem are you encountering?
- What were you trying to test/implement?
- What went wrong?
- Any error messages?

I'll investigate the logs, database, and git state to help figure out what's happening.
```

Quando invocado SEM parâmetros:
```
I'll help debug your current issue.

Please describe what's going wrong:
- What are you working on?
- What specific problem occurred?
- When did it last work?

I can investigate logs, database state, and recent changes to help identify the issue.
```

## Informações do ambiente

Você tem acesso a estes locais e ferramentas principais:

**Logs** (criados automaticamente por `make daemon` e `make wui`):
- Logs do MCP: `~/.humanlayer/logs/mcp-claude-approvals-*.log`
- Logs combinados de WUI/daemon: `~/.humanlayer/logs/wui-${BRANCH_NAME}/codelayer.log`
- A primeira linha mostra: `[timestamp] starting [service] in [directory]`

**Banco de dados**:
- Localização: `~/.humanlayer/daemon-{BRANCH_NAME}.db`
- Banco SQLite com sessões, eventos, aprovações etc.
- Pode ser consultado diretamente com `sqlite3`

**Estado do git**:
- Verifique a branch atual, os commits recentes e as alterações não commitadas
- Similar ao funcionamento dos comandos `commit` e `describe_pr`

**Status dos serviços**:
- Verifique se o daemon está rodando: `ps aux | grep hld`
- Verifique se a WUI está rodando: `ps aux | grep wui`
- Socket existe: `~/.humanlayer/daemon.sock`

## Passos do processo

### Passo 1: Entenda o problema

Depois que o usuário descrever o problema:

1. **Leia qualquer contexto fornecido** (arquivo de plano ou ticket):
   - Entenda o que ele está implementando/testando
   - Anote em qual fase ou passo ele está
   - Identifique o comportamento esperado vs. o real

2. **Verificação rápida de estado**:
   - Branch git atual e commits recentes
   - Quaisquer alterações não commitadas
   - Quando o problema começou a ocorrer

### Passo 2: Investigue o problema

Dispare agentes de Task em paralelo para uma investigação eficiente:

```
Task 1 - Check Recent Logs:
Find and analyze the most recent logs for errors:
1. Find latest daemon log: ls -t ~/.humanlayer/logs/daemon-*.log | head -1
2. Find latest WUI log: ls -t ~/.humanlayer/logs/wui-*.log | head -1
3. Search for errors, warnings, or issues around the problem timeframe
4. Note the working directory (first line of log)
5. Look for stack traces or repeated errors
Return: Key errors/warnings with timestamps
```

```
Task 2 - Database State:
Check the current database state:
1. Connect to database: sqlite3 ~/.humanlayer/daemon.db
2. Check schema: .tables and .schema for relevant tables
3. Query recent data:
   - SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;
   - SELECT * FROM conversation_events WHERE created_at > datetime('now', '-1 hour');
   - Other queries based on the issue
4. Look for stuck states or anomalies
Return: Relevant database findings
```

```
Task 3 - Git and File State:
Understand what changed recently:
1. Check git status and current branch
2. Look at recent commits: git log --oneline -10
3. Check uncommitted changes: git diff
4. Verify expected files exist
5. Look for any file permission issues
Return: Git state and any file issues
```

### Passo 3: Apresente as descobertas

Com base na investigação, apresente um relatório de depuração focado:

```markdown
## Debug Report

### What's Wrong
[Clear statement of the issue based on evidence]

### Evidence Found

**From Logs** (`~/.humanlayer/logs/`):
- [Error/warning with timestamp]
- [Pattern or repeated issue]

**From Database**:
```sql
-- Relevant query and result
[Finding from database]
```

**From Git/Files**:
- [Recent changes that might be related]
- [File state issues]

### Root Cause
[Most likely explanation based on evidence]

### Next Steps

1. **Try This First**:
   ```bash
   [Specific command or action]
   ```

2. **If That Doesn't Work**:
   - Restart services: `make daemon` and `make wui`
   - Check browser console for WUI errors
   - Run with debug: `HUMANLAYER_DEBUG=true make daemon`

### Can't Access?
Some issues might be outside my reach:
- Browser console errors (F12 in browser)
- MCP server internal state
- System-level issues

Would you like me to investigate something specific further?
```

## Notas importantes

- **Foque em cenários de teste manual** - Isso é para depuração durante a implementação
- **Sempre exija a descrição do problema** - Não dá para depurar sem saber o que está errado
- **Leia os arquivos por completo** - Sem limit/offset ao ler o contexto
- **Pense como o `commit` ou o `describe_pr`** - Entenda o estado e as alterações do git
- **Devolva ao usuário quando necessário** - Alguns problemas (console do navegador, internals do MCP) estão fora do alcance
- **Sem edição de arquivos** - Apenas investigação

## Referência rápida

**Encontrar os logs mais recentes**:
```bash
ls -t ~/.humanlayer/logs/daemon-*.log | head -1
ls -t ~/.humanlayer/logs/wui-*.log | head -1
```

**Consultas ao banco de dados**:
```bash
sqlite3 ~/.humanlayer/daemon.db ".tables"
sqlite3 ~/.humanlayer/daemon.db ".schema sessions"
sqlite3 ~/.humanlayer/daemon.db "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;"
```

**Verificação de serviços**:
```bash
ps aux | grep hld     # O daemon está rodando?
ps aux | grep wui     # A WUI está rodando?
```

**Estado do git**:
```bash
git status
git log --oneline -10
git diff
```

Lembre-se: este comando ajuda você a investigar sem consumir o contexto da janela principal. Perfeito para quando você esbarra em um problema durante o teste manual e precisa mergulhar nos logs, no banco de dados ou no estado do git.
