---
description: Cria commits git com aprovação do usuário e sem atribuição ao Claude
---

# Commitar alterações

Sua tarefa é criar commits git para as alterações feitas durante esta sessão.

## Processo:

1. **Pense no que mudou:**
   - Revise o histórico da conversa e entenda o que foi realizado
   - Rode `git status` para ver as alterações atuais
   - Rode `git diff` para entender as modificações
   - Considere se as alterações devem virar um único commit ou vários commits lógicos

2. **Planeje seu(s) commit(s):**
   - Identifique quais arquivos pertencem ao mesmo conjunto
   - Rascunhe mensagens de commit claras e descritivas
   - Use o modo imperativo nas mensagens de commit
   - Foque no porquê das alterações, não apenas no quê

3. **Apresente seu plano ao usuário:**
   - Liste os arquivos que você pretende adicionar a cada commit
   - Mostre a(s) mensagem(ns) de commit que você vai usar
   - Pergunte: "Pretendo criar [N] commit(s) com estas alterações. Posso prosseguir?"

4. **Execute após a confirmação:**
   - Use `git add` com arquivos específicos (nunca use `-A` nem `.`)
   - Crie os commits com as mensagens planejadas
   - Mostre o resultado com `git log --oneline -n [número]`

## Importante:
- **NUNCA adicione informação de coautoria nem atribuição ao Claude**
- Os commits devem ter o usuário como único autor
- Não inclua mensagens do tipo "Generated with Claude"
- Não adicione linhas "Co-Authored-By"
- Escreva as mensagens de commit como se o usuário as tivesse escrito

## Lembre-se:
- Você tem o contexto completo do que foi feito nesta sessão
- Agrupe alterações relacionadas
- Mantenha os commits focados e atômicos sempre que possível
- O usuário confia no seu julgamento - foi ele quem pediu o commit
