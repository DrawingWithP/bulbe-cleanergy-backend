---
description: Cria documento de handoff para transferir o trabalho a outra sessão
---

# Criar handoff

Sua tarefa é escrever um documento de handoff para repassar seu trabalho a outro agente em uma nova sessão. Você vai criar um documento de handoff que seja completo, mas também **conciso**. O objetivo é compactar e resumir seu contexto sem perder nenhum dos detalhes-chave daquilo em que você está trabalhando.


## Processo
### 1. Caminho do arquivo e metadados
Use as informações a seguir para entender como criar seu documento:
    - crie seu arquivo em `thoughts/shared/handoffs/ENG-XXXX/YYYY-MM-DD_HH-MM-SS_ENG-ZZZZ_description.md`, onde:
        - YYYY-MM-DD é a data de hoje
        - HH-MM-SS são as horas, minutos e segundos com base no horário atual, em formato de 24 horas (ou seja, use `13:00` para `1:00 pm`)
        - ENG-XXXX é o número do ticket (substitua por `general` se não houver ticket)
        - ENG-ZZZZ é o número do ticket (omita se não houver ticket)
        - description é uma breve descrição em kebab-case
    - Rode o script `scripts/spec_metadata.sh` para gerar todos os metadados relevantes
    - Exemplos:
        - Com ticket: `2025-01-08_13-55-22_ENG-2166_create-context-compaction.md`
        - Sem ticket: `2025-01-08_13-55-22_create-context-compaction.md`

### 2. Escrita do handoff
usando as convenções acima, escreva seu documento. use o caminho definido e o padrão de frontmatter YAML a seguir. Use os metadados coletados no passo 1 e estruture o documento com o frontmatter YAML seguido do conteúdo:

Use a seguinte estrutura de template:
```markdown
---
date: [Current date and time with timezone in ISO format]
researcher: [Researcher name from thoughts status]
git_commit: [Current commit hash]
branch: [Current branch name]
repository: [Repository name]
topic: "[Feature/Task Name] Implementation Strategy"
tags: [implementation, strategy, relevant-component-names]
status: complete
last_updated: [Current date in YYYY-MM-DD format]
last_updated_by: [Researcher name]
type: implementation_strategy
---

# Handoff: ENG-XXXX {very concise description}

## Task(s)
{description of the task(s) that you were working on, along with the status of each (completed, work in progress, planned/discussed). If you are working on an implementation plan, make sure to call out which phase you are on. Make sure to reference the plan document and/or research document(s) you are working from that were provided to you at the beginning of the session, if applicable.}

## Critical References
{List any critical specification documents, architectural decisions, or design docs that must be followed. Include only 2-3 most important file paths. Leave blank if none.}

## Recent changes
{describe recent changes made to the codebase that you made in line:file syntax}

## Learnings
{describe important things that you learned - e.g. patterns, root causes of bugs, or other important pieces of information someone that is picking up your work after you should know. consider listing explicit file paths.}

## Artifacts
{ an exhaustive list of artifacts you produced or updated as filepaths and/or file:line references - e.g. paths to feature documents, implementation plans, etc that should be read in order to resume your work.}

## Action Items & Next Steps
{ a list of action items and next steps for the next agent to accomplish based on your tasks and their statuses}

## Other Notes
{ other notes, references, or useful information - e.g. where relevant sections of the codebase are, where relevant documents are, or other important things you leanrned that you want to pass on but that don't fall into the above categories}
```
---

### 3. Aprovar e sincronizar
Rode `humanlayer thoughts sync` para salvar o documento.

Uma vez concluído, você deve responder ao usuário com o template entre as tags XML <template_response></template_response>. NÃO inclua as tags na sua resposta.

<template_response>
Handoff criado e sincronizado! Você pode retomar a partir deste handoff em uma nova sessão com o seguinte comando:

```bash
/resume_handoff path/to/handoff.md
```
</template_response>

por exemplo (entre as tags XML <example_response></example_response> - NÃO inclua essas tags na sua resposta real ao usuário)

<example_response>
Handoff criado e sincronizado! Você pode retomar a partir deste handoff em uma nova sessão com o seguinte comando:

```bash
/resume_handoff thoughts/shared/handoffs/ENG-2166/2025-01-08_13-44-55_ENG-2166_create-context-compaction.md
```
</example_response>

---
##.  Notas e instruções adicionais
- **mais informação, não menos**. Esta é uma diretriz que define o mínimo que um handoff deve ser. Sinta-se sempre à vontade para incluir mais informação se necessário.
- **seja completo e preciso**. inclua tanto os objetivos de alto nível quanto os detalhes de baixo nível, conforme necessário.
- **evite trechos de código excessivos**. Embora um trecho breve para descrever alguma mudança-chave seja importante, evite grandes blocos de código ou diffs; não inclua um a menos que seja necessário (ex.: relacionado a um erro que você está depurando). Prefira usar referências `/path/to/file.ext:line` que um agente possa seguir depois, quando estiver pronto, ex.: `packages/dashboard/src/app/dashboard/page.tsx:12-24`
