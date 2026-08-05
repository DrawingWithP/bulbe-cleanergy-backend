---
description: Implementa planos técnicos de thoughts/shared/plans com verificação
---

# Implementar plano

Sua tarefa é implementar um plano técnico aprovado a partir de `thoughts/shared/plans/`. Esses planos contêm fases com alterações específicas e critérios de sucesso.

## Começando

Quando receber o caminho de um plano:
- Leia o plano por completo e verifique se há marcações existentes (- [x])
- Leia o ticket original e todos os arquivos mencionados no plano
- **Leia os arquivos por inteiro** - nunca use parâmetros de limit/offset; você precisa do contexto completo
- Pense a fundo em como as peças se encaixam
- Crie uma lista de tarefas para acompanhar seu progresso
- Comece a implementar se você entendeu o que precisa ser feito

Se nenhum caminho de plano for informado, peça um.

## Filosofia de implementação

Os planos são cuidadosamente desenhados, mas a realidade pode ser bagunçada. Seu trabalho é:
- Seguir a intenção do plano, adaptando-se ao que você encontrar
- Implementar cada fase por completo antes de passar para a próxima
- Verificar se o seu trabalho faz sentido no contexto mais amplo da base de código
- Atualizar as caixas de seleção do plano conforme você conclui seções

Quando as coisas não corresponderem exatamente ao plano, pense no porquê e comunique com clareza. O plano é o seu guia, mas o seu julgamento também importa.

Se você encontrar uma divergência:
- PARE e pense a fundo sobre por que o plano não pode ser seguido
- Apresente o problema com clareza:
  ```
  Issue in Phase [N]:
  Expected: [what the plan says]
  Found: [actual situation]
  Why this matters: [explanation]

  How should I proceed?
  ```

## Abordagem de verificação

Após implementar uma fase:
- Rode as verificações dos critérios de sucesso (normalmente o `make check test` cobre tudo)
- Corrija quaisquer problemas antes de prosseguir
- Atualize seu progresso tanto no plano quanto nos seus todos
- Marque os itens concluídos no próprio arquivo do plano usando o Edit
- **Pause para verificação humana**: Após concluir toda a verificação automatizada de uma fase, pause e informe ao humano que a fase está pronta para teste manual. Use este formato:
  ```
  Phase [N] Complete - Ready for Manual Verification

  Automated verification passed:
  - [List automated checks that passed]

  Please perform the manual verification steps listed in the plan:
  - [List manual verification items from the plan]

  Let me know when manual testing is complete so I can proceed to Phase [N+1].
  ```

Se você for instruído a executar várias fases consecutivamente, pule a pausa até a última fase. Caso contrário, presuma que você está fazendo apenas uma fase.

não marque itens dos passos de teste manual até que sejam confirmados pelo usuário.


## Se você travar

Quando algo não estiver funcionando como esperado:
- Primeiro, garanta que você leu e entendeu todo o código relevante
- Considere se a base de código evoluiu desde que o plano foi escrito
- Apresente a divergência com clareza e peça orientação

Use subtarefas com parcimônia - principalmente para depuração pontual ou para explorar território desconhecido.

## Retomando o trabalho

Se o plano tiver marcações existentes:
- Confie que o trabalho concluído já está feito
- Retome a partir do primeiro item não marcado
- Verifique o trabalho anterior apenas se algo parecer errado

Lembre-se: você está implementando uma solução, não apenas marcando caixas. Mantenha o objetivo final em mente e siga em frente.
