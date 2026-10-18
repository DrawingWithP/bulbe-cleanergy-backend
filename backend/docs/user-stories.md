# User Stories

| ID | User Story | Endpoint | Prioridade | Story Points |
| --- | -------- | --------- | ---------- | -------- |
| US-01 | Como aplicação frontend, quero enviar os dados de uma nova adesão para a API, para que o cliente possa se tornar cliente Bulbe | POST /v1/adesoes | Alta | 8 |
| US-02 | Como aplicação frontend, quero consultar os parceiros do Clube Bulbe para exibi-los ao cliente | GET /v1/parceiros | Média | 3 |
| US-03 | Como aplicação frontend, quero consultar os cupons do cliente para exibir eles na tela | GET /v1/clientes/{id}/cupons | Média | 2 |
| US-04 | Como aplicação frontend, quero buscar dicas por meio da API, para que elas possam ser exibidas ao usuário | GET /v1/dicas | Baixa | 1 |
| US-05 | Como aplicação frontend, quero buscar dados de um cliente específico, para que eu possa mostrá-los ao cliente | GET /v1/clientes/{id} | Média | 3 |
| US-06 | Como aplicação frontend, quero buscar dados de uma adesão específica, para poder retomar uma adesão em andamento | GET /v1/adesoes/{id} | Média | 5 |
| US-07 | Como aplicação frontend, quero atualizar dados de uma adesão específica, para dar continuidade à adesão em andamento | PATCH /v1/adesoes/{id} | Média | 3 |
| US-08 | Como aplicação frontend, quero deletar dados de uma adesão em andamento específica, caso o usuário decida cancelar uma adesão incompleta | DELETE /v1/adesoes/{id} | Baixa | 2 |
| US-09 | Como aplicação frontend, quero enviar o CPF informado pelo usuário para a API, para que ela verifique se ele já é cliente e dispare o código | POST /v1/primeiro-acesso/verificacoes | Média | 5 |
| US-10 | Como aplicação frontend, quero enviar um código para a API, para que ela confirme o código e habilite o acesso do cliente ao app | POST /v1/primeiro-acesso/confirmacoes | Média | 8 |
| US-11 | Como aplicação frontend, quero consultar o status atual da ativação do cliente, para exibir dados relevantes | GET /v1/clientes/{id}/ativacao | Alta | 8 |
| US-12 | Como aplicação frontend, quero atualizar as etapas da ativação de um determinado cliente, para corrigir ou atualizar os dados | PATCH /v1/clientes/{id}/ativacao | Média | 5 |
| US-13 | Como aplicação frontend, quero enviar uma solicitação de cálculo de economia à API, para que o cliente possa receber esta simulação | POST /v1/simulacoes | Média | 3 |
| US-14 | Como aplicação frontend, quero consultar uma lista de indicações feitas pelo usuário, para exibir elas na tela | GET /v1/clientes/{id}/indicacoes | Baixa | 3 |
| US-15 | Como aplicação frontend, quero enviar os dados de uma nova indicação à API, para que ela possa ser cadastrada no sistema | POST /v1/indicacoes | Média | 2 |
| US-16 | Como aplicação frontend, quero consultar dados de uma indicação específica, para que possam ser exibidos ao cliente na tela | GET /v1/indicacoes/{id} | Baixa | 2 |
| US-17 | Como aplicação frontend, excluir dados de uma indicação específica, para descartar indicações pendentes | DELETE /v1/indicacoes/{id} | Baixa | 2 |
| US-18 | Como aplicação frontend, quero consultar dados da situação do cliente no Clube Bulbe, para que possam ser exibidos ao cliente na tela | GET /v1/clientes/{id}/clube | Média | 3 |
| US-19 | Como aplicação frontend, quero consultar o histórico de cartas do cliente, para que possam ser exibidos na seção "Histórico de Cartas" | GET /v1/clientes/{id}/cartas | Média | 3 |
| US-20 | Como aplicação frontend, quero consultar cartas do Clube Bulbe, para que possam ser exibidos ao cliente na tela | GET /v1/cartas/{id} | Média | 3 |
| US-21 | Como aplicação frontend, quero notificar a API de que o usuário abriu uma carta, para que ele possa receber a recompensa | POST /v1/cartas/{id}/abertura | Alta | 3 |
| US-22 | Como aplicação frontend, quero consultar dados de um cupom específico, para que possam ser exibidos ao cliente na tela | GET /v1/cupons/{id} | Média | 2 |
| US-23 | Como aplicação frontend, quero atualizar dados de um cupom específico, para que o sistema saiba se um cupom foi salvo ou usado | PATCH /v1/cupons/{id} | Média | 1 |
| US-24 | Como aplicação frontend, quero cadastrar um novo parceiro do Clube Bulbe, para que ele possa ser exibido no app | POST /v1/parceiros | Baixa | 1 |
| US-25 | Como aplicação frontend, quero consultar dados de um parceiro do Clube Bulbe específico, para que possam ser exibidos ao cliente na tela | GET /v1/parceiros/{id} | Média | 2 |
| US-26 | Como aplicação frontend, quero excluir um parceiro do Clube Bulbe, para que possam ser removidos os parceiros caso necessário | DELETE /v1/parceiros/{id} | Baixa | 1 |
| US-27 | Como aplicação frontend, quero cadastrar novas dicas no sistema, para que possam ser exibidas ao cliente na tela | POST /v1/dicas | Baixa | 1 |
| US-28 | Como aplicação frontend, quero consultar dados de uma dica específica, para que possam ser exibidos ao cliente na tela | GET /v1/dicas/{id} | Média | 1 |
| US-29 | Como aplicação frontend, quero atualizar dados de uma dica específica, para que possam ser exibidos ao cliente na tela | PUT /v1/dicas/{id} | Baixa | 1 |
| US-30 | Como aplicação frontend, quero remover uma dica específica do sistema, para que ela não seja exibida no carrossel | DELETE /v1/dicas/{id} | Baixa | 1 |
| US-31 | Como aplicação frontend, quero criar um novo cliente, para que o processo de adesão possa ser concluído | POST /v1/clientes | Alta | 8 |
| US-32	| Como aplicação frontend, quero listar as dicas de economia cadastradas via API, para que possam ser exibidas no carrossel e na seção de dicas do aplicativo | GET /v1/dicas |	Média |	2
| US-33	| Como aplicação frontend, quero listar os parceiros do Clube Bulbe via API, para que possam ser exibidos na vitrine de benefícios do aplicativo | 	GET /v1/parceiros |	Média |	2
| US-34	| Como aplicação frontend, quero atualizar os dados cadastrais do cliente via API, para que as informações de perfil permaneçam atualizadas no sistema | PUT /v1/clientes/{id}	| Média |	3
| US-35	| Como aplicação frontend, quero consultar as solicitações de adesão via API, para que seja possível listar e acompanhar as entradas no sistema | 	GET /v1/adesoes |	Baixa | 2
