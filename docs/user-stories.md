# User Stories

| ID | User Story | Endpoint | Prioridade |
| --- | -------- | --------- | ---------- |
| US-01 | Como aplicação frontend, quero enviar os dados de uma nova adesão para a API, para que o cliente possa se tornar cliente Bulbe | POST /v1/adesoes | Alta |
| US-02 | Como aplicação frontend, quero consultar os parceiros do Clube Bulbe para exibi-los ao cliente | GET /v1/parceiros | Média |
| US-03 | Como aplicação frontend, quero consultar os cupons do cliente para exibir eles na tela | GET /v1/clientes/{id}/cupons | Média |
| US-04 | Como aplicação frontend, quero buscar dicas por meio da API, para que elas possam ser exibidas ao usuário | GET /v1/dicas | Baixa |
| US-05 | Como aplicação frontend, quero buscar dados de um cliente específico, para que eu possa mostrá-los ao cliente | GET /v1/clientes/{id} | Média |
| US-06 | Como aplicação frontend, quero buscar dados de uma adesão específica, para poder retomar uma adesão em andamento | GET /v1/adesoes/{id} | Baixa |
| US-07 | Como aplicação frontend, quero atualizar dados de uma adesão específica, para dar continuidade à adesão em andamento | POST /v1/adesoes/{id} | Baixa |
| US-08 | Como aplicação frontend, quero deletar dados de uma adesão em andamento específica, caso o usuário decida cancelar uma adesão incompleta | DELETE /v1/adesoes/{id} | Baixa |
| US-09 | Como aplicação frontend, quero enviar o CPF informado pelo usuário para a API, para que ela verifique se ele já é cliente e dispare o código | POST /v1/primeiro-acesso/verificacoes | Baixa |
| US-10 | Como aplicação frontend, quero enviar um código para a API, para que ela confirme o código e habilite o acesso do cliente ao app | POST /v1/primeiro-acesso/confirmacoes | Baixa |
| US-11 | Como aplicação frontend, quero consultar o status atual da ativação do cliente, para exibir dados relevantes | GET /v1/clientes/{id}/ativacao | Alta |
| US-12 | Como aplicação frontend, quero atualizar as etapas da ativação de um determinado cliente, para corrigir ou atualizar os dados | PATCH /v1/clientes/{id}/ativacao | Baixa |
| US-13 | Como aplicação frontend, quero enviar uma solicitação de cálculo de economia à API, para que o cliente possa receber esta simulação | POST /v1/simulacoes | Baixa |
| US-14 | Como aplicação frontend, quero consultar uma lista de indicações feitas pelo usuário, para exibir elas na tela | GET /v1/clientes/{id}/indicacoes | Baixa |
| US-15 | Como aplicação frontend, quero enviar os dados de uma nova indicação à API, para que ela possa ser cadastrada no sistema | POST /v1/indicacoes | Média |
| US-16 | Como aplicação frontend, quero consultar dados de uma indicação específica, para que possam ser exibidos ao cliente na tela | GET /v1/indicacoes/{id} | Baixa |