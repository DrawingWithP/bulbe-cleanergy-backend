---
description: Cria commits git das alterações da sessão, com mensagens claras e atômicas
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

3. **Execute após a confirmação:**
   - Use `git add` com arquivos específicos (nunca use `-A` nem `.`)
   - Nunca commite o diretório `thoughts/` nem nada dentro dele!
   - Nunca commite arquivos de teste, scripts descartáveis ou outros arquivos que você criou, ou que aparentem ter sido criados, mas que não fazem parte das suas alterações nem foram causados diretamente por elas (ex.: código gerado)
   - Crie os commits com as mensagens planejadas até que todas as suas alterações estejam commitadas, usando `git commit -m`

## Lembre-se:
- Você tem o contexto completo do que foi feito nesta sessão
- Agrupe alterações relacionadas
- Mantenha os commits focados e atômicos sempre que possível
- O usuário confia no seu julgamento - foi ele quem pediu o commit
- **IMPORTANTE**: - nunca pare para pedir feedback ao usuário.
