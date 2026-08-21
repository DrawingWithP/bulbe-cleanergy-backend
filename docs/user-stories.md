# User Stories

| ID | User Story | Endpoint | Prioridade |
| --- | -------- | --------- | ---------- |
| US-01 | Como aplicação frontend, quero enviar os dados de uma nova adesão para a API, para que o cliente possa se tornar cliente Bulbe | POST /v1/adesoes | Alta |
| US-02 | Como aplicação frontend, quero consultar o status de ativação dos clientes para exibir a informação aos mesmos | GET /v1/clientes/{id}/ativacao | Alta |
| US-03 | Como aplicação frontend, quero consultar os parceiros do Clube Bulbe para exibi-los ao cliente | GET /v1/parceiros | Média |
| US-04 | Como aplicação frontend, quero consultar os cupons do cliente para exibir eles na tela | GET /v1/clientes/{id}/cupons | Média |
| US-05 | Como aplicação frontend, quero buscar dicas por meio da API, para que elas possam ser exibidas ao usuário | GET /v1/dicas | Baixa |