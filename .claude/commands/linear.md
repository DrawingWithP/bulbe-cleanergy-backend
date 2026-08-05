---
description: Gerencia tickets do Linear - criar, atualizar, comentar e seguir os padrões de fluxo de trabalho
---

# Linear - Gerenciamento de tickets

Sua tarefa é gerenciar tickets do Linear, incluindo criar tickets a partir de documentos de thoughts, atualizar tickets existentes e seguir os padrões específicos de fluxo de trabalho do time.

## Preparação inicial

Primeiro, verifique se as ferramentas MCP do Linear estão disponíveis, checando se existem ferramentas `mcp__linear__`. Se não existirem, responda:
```
I need access to Linear tools to help with ticket management. Please run the `/mcp` command to enable the Linear MCP server, then try again.
```

Se as ferramentas estiverem disponíveis, responda de acordo com a solicitação do usuário:

### Para solicitações gerais:
```
I can help you with Linear tickets. What would you like to do?
1. Create a new ticket from a thoughts document
2. Add a comment to a ticket (I'll use our conversation context)
3. Search for tickets
4. Update ticket status or details
```

### Para solicitações específicas de criação:
```
I'll help you create a Linear ticket from your thoughts document. Please provide:
1. The path to the thoughts document (or topic to search for)
2. Any specific focus or angle for the ticket (optional)
```

Depois aguarde a entrada do usuário.

## Fluxo de trabalho do time e progressão de status

O time segue um fluxo específico para garantir alinhamento antes da implementação do código:

1. **Triage** → Todos os tickets novos começam aqui, para revisão inicial
2. **Spec Needed** → É preciso mais detalhe - problema a resolver e esboço da solução são necessários
3. **Research Needed** → O ticket exige investigação antes que um plano possa ser escrito
4. **Research in Progress** → Pesquisa/investigação ativa em andamento
5. **Research in Review** → Descobertas da pesquisa em revisão (etapa opcional)
6. **Ready for Plan** → Pesquisa concluída, o ticket precisa de um plano de implementação
7. **Plan in Progress** → Escrevendo ativamente o plano de implementação
8. **Plan in Review** → Plano escrito e em discussão
9. **Ready for Dev** → Plano aprovado, pronto para implementação
10. **In Dev** → Desenvolvimento ativo
11. **Code Review** → PR enviado
12. **Done** → Concluído

**Princípio-chave**: A revisão e o alinhamento acontecem na etapa do plano (não na etapa do PR), para avançar mais rápido e evitar retrabalho.

## Convenções importantes

### Mapeamento de URLs para documentos de thoughts
Ao referenciar documentos de thoughts, sempre forneça links do GitHub usando o parâmetro `links`:
- `thoughts/shared/...` → `https://github.com/humanlayer/thoughts/blob/main/repos/humanlayer/shared/...`
- `thoughts/allison/...` → `https://github.com/humanlayer/thoughts/blob/main/repos/humanlayer/allison/...`
- `thoughts/global/...` → `https://github.com/humanlayer/thoughts/blob/main/global/...`

### Valores padrão
- **Status**: Sempre crie tickets novos no status "Triage"
- **Projeto**: Para tickets novos, use por padrão "M U L T I C L A U D E" (ID: f11c8d63-9120-4393-bfae-553da0b04fd8), salvo instrução em contrário
- **Prioridade**: Use Medium (3) por padrão para a maioria das tarefas; use o bom senso ou pergunte ao usuário
  - Urgent (1): Bloqueios críticos, questões de segurança
  - High (2): Funcionalidades importantes com prazo, bugs graves
  - Medium (3): Tarefas de implementação padrão (padrão)
  - Low (4): Coisas desejáveis, melhorias menores
- **Links**: Use o parâmetro `links` para anexar URLs (não apenas links markdown na descrição)

### Atribuição automática de labels
Aplique labels automaticamente com base no conteúdo do ticket:
- **hld**: Para tickets sobre o diretório `hld/` (o daemon)
- **wui**: Para tickets sobre `humanlayer-wui/`
- **meta**: Para tickets sobre comandos do `hlyr`, a ferramenta thoughts ou o diretório `thoughts/`

Nota: meta é mutuamente exclusivo com hld/wui. Tickets podem ter hld e wui juntos, mas não meta com nenhum dos dois.

## Instruções específicas por ação

### 1. Criando tickets a partir de thoughts

#### Passos a seguir após receber a solicitação:

1. **Localize e leia o documento de thoughts:**
   - Se um caminho for informado, leia o documento diretamente
   - Se um tema/palavra-chave for informado, busque no diretório thoughts/ usando o Grep para encontrar documentos relevantes
   - Se várias correspondências forem encontradas, mostre a lista e peça ao usuário para escolher
   - Crie uma lista com TodoWrite para acompanhar: Ler documento → Analisar conteúdo → Rascunhar ticket → Obter entrada do usuário → Criar ticket

2. **Analise o conteúdo do documento:**
   - Identifique o problema central ou a funcionalidade em discussão
   - Extraia os principais detalhes de implementação ou decisões técnicas
   - Anote quaisquer arquivos de código ou áreas mencionados
   - Procure por itens de ação ou próximos passos
   - Identifique em que estágio a ideia está (ideação inicial vs. pronta para implementar)
   - Reserve um tempo para ultrathink sobre destilar a essência deste documento em um enunciado claro do problema e em uma abordagem de solução

3. **Verifique o contexto relacionado (se mencionado no documento):**
   - Se o documento referenciar arquivos de código específicos, leia as seções relevantes
   - Se mencionar outros documentos de thoughts, dê uma olhada rápida neles
   - Procure por tickets do Linear já existentes que sejam mencionados

4. **Obtenha o contexto do workspace do Linear:**
   - Liste os times: `mcp__linear__list_teams`
   - Se houver vários times, peça ao usuário para escolher um
   - Liste os projetos do time selecionado: `mcp__linear__list_projects`

5. **Rascunhe o resumo do ticket:**
   Apresente um rascunho ao usuário:
   ```
   ## Draft Linear Ticket

   **Title**: [Clear, action-oriented title]

   **Description**:
   [2-3 sentence summary of the problem/goal]

   ## Key Details
   - [Bullet points of important details from thoughts]
   - [Technical decisions or constraints]
   - [Any specific requirements]

   ## Implementation Notes (if applicable)
   [Any specific technical approach or steps outlined]

   ## References
   - Source: `thoughts/[path/to/document.md]` ([View on GitHub](converted GitHub URL))
   - Related code: [any file:line references]
   - Parent ticket: [if applicable]

   ---
   Based on the document, this seems to be at the stage of: [ideation/planning/ready to implement]
   ```

6. **Refinamento interativo:**
   Pergunte ao usuário:
   - Este resumo captura o ticket com precisão?
   - Em qual projeto isso deve entrar? [mostre a lista]
   - Qual prioridade? (Padrão: Medium/3)
   - Algum contexto adicional a acrescentar?
   - Devemos incluir mais/menos detalhes de implementação?
   - Você quer atribuí-lo a si mesmo?

   Nota: O ticket será criado no status "Triage" por padrão.

7. **Crie o ticket do Linear:**
   ```
   mcp__linear__create_issue with:
   - title: [refined title]
   - description: [final description in markdown]
   - teamId: [selected team]
   - projectId: [use default project from above unless user specifies]
   - priority: [selected priority number, default 3]
   - stateId: [Triage status ID]
   - assigneeId: [if requested]
   - labelIds: [apply automatic label assignment from above]
   - links: [{url: "GitHub URL", title: "Document Title"}]
   ```

8. **Ações pós-criação:**
   - Mostre a URL do ticket criado
   - Pergunte se o usuário quer:
     - Adicionar um comentário com detalhes adicionais de implementação
     - Criar subtarefas para itens de ação específicos
     - Atualizar o documento de thoughts original com a referência do ticket
   - Se sim para atualizar o documento de thoughts:
     ```
     Adicione no topo do documento:
     ---
     linear_ticket: [URL]
     created: [date]
     ---
     ```

## Exemplos de transformação:

### De thoughts verboso:
```
"I've been thinking about how our resumed sessions don't inherit permissions properly.
This is causing issues where users have to re-specify everything. We should probably
store all the config in the database and then pull it when resuming. Maybe we need
new columns for permission_prompt_tool and allowed_tools..."
```

### Para ticket conciso:
```
Title: Fix resumed sessions to inherit all configuration from parent

Description:

## Problem to solve
Currently, resumed sessions only inherit Model and WorkingDir from parent sessions,
causing all other configuration to be lost. Users must re-specify permissions and
settings when resuming.

## Solution
Store all session configuration in the database and automatically inherit it when
resuming sessions, with support for explicit overrides.
```

### 2. Adicionando comentários e links a tickets existentes

Quando o usuário quiser adicionar um comentário a um ticket:

1. **Determine qual é o ticket:**
   - Use o contexto da conversa atual para identificar o ticket relevante
   - Se houver incerteza, use `mcp__linear__get_issue` para exibir os detalhes do ticket e confirmar com o usuário
   - Procure por referências a tickets no trabalho recente discutido

2. **Formate os comentários para clareza:**
   - Tente manter os comentários concisos (~10 linhas), a menos que mais detalhe seja necessário
   - Foque no insight-chave ou na informação mais útil para um leitor humano
   - Não apenas o que foi feito, mas o que importa a respeito disso
   - Inclua referências relevantes de arquivo com crase e links do GitHub

3. **Formatação de referências de arquivo:**
   - Envolva os caminhos em crases: `thoughts/allison/example.md`
   - Adicione o link do GitHub em seguida: `([View](url))`
   - Faça isso tanto para arquivos de thoughts/ quanto para arquivos de código mencionados

4. **Exemplo de estrutura de comentário:**
   ```markdown
   Implemented retry logic in webhook handler to address rate limit issues.

   Key insight: The 429 responses were clustered during batch operations,
   so exponential backoff alone wasn't sufficient - added request queuing.

   Files updated:
   - `hld/webhooks/handler.go` ([GitHub](link))
   - `thoughts/shared/rate_limit_analysis.md` ([GitHub](link))
   ```

5. **Trate os links corretamente:**
   - Se estiver adicionando um link com um comentário: atualize a issue com o link E mencione-o no comentário
   - Se estiver adicionando apenas um link: ainda assim crie um comentário registrando qual link foi adicionado, para posteridade
   - Sempre adicione os links à própria issue usando o parâmetro `links`

6. **Para comentários com links:**
   ```
   # First, update the issue with the link
   mcp__linear__update_issue with:
   - id: [ticket ID]
   - links: [existing links + new link with proper title]

   # Then, create the comment mentioning the link
   mcp__linear__create_comment with:
   - issueId: [ticket ID]
   - body: [formatted comment with key insights and file references]
   ```

7. **Apenas para links:**
   ```
   # Update the issue with the link
   mcp__linear__update_issue with:
   - id: [ticket ID]
   - links: [existing links + new link with proper title]

   # Add a brief comment for posterity
   mcp__linear__create_comment with:
   - issueId: [ticket ID]
   - body: "Added link: `path/to/document.md` ([View](url))"
   ```

### 3. Buscando tickets

Quando o usuário quiser encontrar tickets:

1. **Reúna os critérios de busca:**
   - Texto da consulta
   - Filtros de time/projeto
   - Filtros de status
   - Intervalos de data (createdAt, updatedAt)

2. **Execute a busca:**
   ```
   mcp__linear__list_issues with:
   - query: [search text]
   - teamId: [if specified]
   - projectId: [if specified]
   - stateId: [if filtering by status]
   - limit: 20
   ```

3. **Apresente os resultados:**
   - Mostre o ID, o título, o status e o responsável pelo ticket
   - Agrupe por projeto, se houver vários projetos
   - Inclua links diretos para o Linear

### 4. Atualizando o status dos tickets

Ao mover tickets pelo fluxo de trabalho:

1. **Obtenha o status atual:**
   - Busque os detalhes do ticket
   - Mostre o status atual no fluxo

2. **Sugira o próximo status:**
   - Triage → Spec Needed (falta detalhe/enunciado do problema)
   - Spec Needed → Research Needed (assim que problema/solução estiverem esboçados)
   - Research Needed → Research in Progress (iniciando a pesquisa)
   - Research in Progress → Research in Review (opcional, pode pular para Ready for Plan)
   - Research in Review → Ready for Plan (pesquisa aprovada)
   - Ready for Plan → Plan in Progress (começando a escrever o plano)
   - Plan in Progress → Plan in Review (plano escrito)
   - Plan in Review → Ready for Dev (plano aprovado)
   - Ready for Dev → In Dev (trabalho iniciado)

3. **Atualize com contexto:**
   ```
   mcp__linear__update_issue with:
   - id: [ticket ID]
   - stateId: [new status ID]
   ```

   Considere adicionar um comentário explicando a mudança de status.

## Notas importantes

- Marque usuários em descrições e comentários usando o formato `@[name](ID)`, ex.: `@[dex](16765c85-2286-4c0f-ab49-0d4d79222ef5)`
- Mantenha os tickets concisos, porém completos - busque conteúdo fácil de escanear
- Todos os tickets devem incluir um "problem to solve" claro - se o usuário pedir um ticket e fornecer apenas detalhes de implementação, você DEVE perguntar "Para escrever um bom ticket, por favor explique o problema que você está tentando resolver da perspectiva do usuário"
- Foque no "o quê" e no "porquê"; inclua o "como" apenas se estiver bem definido
- Sempre preserve os links para o material de origem usando o parâmetro `links`
- Não crie tickets a partir de brainstorming em estágio inicial, a menos que seja solicitado
- Use a formatação markdown adequada do Linear
- Inclua referências de código como: `path/to/file.ext:linenum`
- Peça esclarecimentos em vez de adivinhar projeto/status
- Lembre-se de que as descrições do Linear suportam markdown completo, incluindo blocos de código
- Sempre use o parâmetro `links` para URLs externas (não apenas links markdown)
- lembre-se - você precisa obter um "Problem to solve"!

## Diretrizes de qualidade dos comentários

Ao criar comentários, foque em extrair a **informação mais valiosa** para um leitor humano:

- **Insights-chave em vez de resumos**: Qual é o momento "aha" ou o entendimento crítico?
- **Decisões e trade-offs**: Que abordagem foi escolhida e o que ela viabiliza/impede
- **Bloqueios resolvidos**: O que estava impedindo o progresso e como foi resolvido
- **Mudanças de estado**: O que está diferente agora e o que isso significa para os próximos passos
- **Surpresas ou descobertas**: Achados inesperados que afetam o trabalho

Evite:
- Listas mecânicas de mudanças, sem contexto
- Repetir o que já é óbvio nos diffs de código
- Resumos genéricos que não agregam valor

Lembre-se: o objetivo é ajudar um leitor futuro (inclusive você mesmo) a entender rapidamente o que importa nesta atualização.

## IDs usados com frequência

### Time de engenharia
- **Team ID**: `6b3b2115-efd4-4b83-8463-8160842d2c84`

### IDs de label
- **bug**: `ff23dde3-199b-421e-904c-4b9f9b3d452c`
- **hld**: `d28453c8-e53e-4a06-bea9-b5bbfad5f88a`
- **meta**: `7a5abaae-f343-4f52-98b0-7987048b0cfa`
- **wui**: `996deb94-ba0f-4375-8b01-913e81477c4b`

### IDs de estado do fluxo de trabalho
- **Triage**: `77da144d-fe13-4c3a-a53a-cfebd06c0cbe` (type: triage)
- **spec needed**: `274beb99-bff8-4d7b-85cf-04d18affbc82` (type: unstarted)
- **research needed**: `d0b89672-8189-45d6-b705-50afd6c94a91` (type: unstarted)
- **research in progress**: `c41c5a23-ce25-471f-b70a-eff1dca60ffd` (type: unstarted)
- **research in review**: `1a9363a7-3fae-42ee-a6c8-1fc714656f09` (type: unstarted)
- **ready for plan**: `995011dd-3e36-46e5-b776-5a4628d06cc8` (type: unstarted)
- **plan in progress**: `a52b4793-d1b6-4e5d-be79-b2254185eed0` (type: started)
- **plan in review**: `15f56065-41ea-4d9a-ab8c-ec8e1a811a7a` (type: started)
- **ready for dev**: `c25bae2f-856a-4718-aaa8-b469b7822f58` (type: started)
- **in dev**: `6be18699-18d7-496e-a7c9-37d2ddefe612` (type: started)
- **code review**: `8ca7fda1-08d4-48fb-a0cf-954246ccbe66` (type: started)
- **Ready for Deploy**: `a3ad0b54-17bf-4ad3-b1c1-2f56c1f2515a` (type: started)
- **Done**: `8159f431-fbc7-495f-a861-1ba12040f672` (type: completed)
- **Backlog**: `6cf6b25a-054a-469b-9845-9bd9ab39ad76` (type: backlog)
- **PostIts**: `a57f2ab3-c6f8-44c7-a36b-896154729338` (type: backlog)
- **Todo**: `ddf85246-3a7c-4141-a377-09069812bbc3` (type: unstarted)
- **Duplicate**: `2bc0e829-9853-4f76-ad34-e8732f062da2` (type: canceled)
- **Canceled**: `14a28d0d-c6aa-4d8e-9ff2-9801d4cc7de1` (type: canceled)


## IDs de usuário do Linear

- allison: b157f9e4-8faf-4e7e-a598-dae6dec8a584
- dex: 16765c85-2286-4c0f-ab49-0d4d79222ef5
- sundeep: 0062104d-9351-44f5-b64c-d0b59acb516b
