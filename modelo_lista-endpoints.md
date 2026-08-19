# Lista de Endpoints da API, App Bulbe Energia

## Identificação

- **Projeto:** App Bulbe Energia — API (back-end do front-end entregue na Sprint anterior)
- **Empresa parceira:** Bulbe Energia — bulbeenergia.com.br
- **Equipe:** squad cleanergy
- **Integrantes:** Luiz Felipe Luppi Mendonça, Rodrigo Rennó Pimentel Bello Santos, Gabriel Mercedo Moreira Lins de Faria, Samuel Gandra Paranhos (líder), João Victor Silva Lenza, Rafael Alcântara Brescia
- **Data:** 19/08/2026
- **Sprint / Etapa:** Sprint 1, Design da API

## Convenções desta API

- **URL base:** `/v1`
- **Formato de dados:** JSON, tanto na requisição quanto na resposta
- **Autenticação:** [a definir na Aula 29, Autenticação e Autorização]
- **Nomenclatura:** recursos no plural, kebab-case para múltiplas palavras, sem verbos na URL
- **Identificadores:** `id` em formato UUID v4, sempre serializado como string
- **Datas:** ISO 8601 — `AAAA-MM-DD` para datas e `AAAA-MM-DDTHH:MM:SSZ` (UTC) para instantes
- **Valores monetários:** número decimal em reais, com até 2 casas (ex.: `287.50`)
- **Paginação:** `page` (padrão 1) e `limit` (padrão 20, máximo 100) nas coleções; a resposta traz `data`, `page` e `total`
- **Erros:** corpo padronizado `{ "erro": { "codigo": "...", "mensagem": "...", "campos": [...] } }`
- **Rastreabilidade:** a coluna Requisito de Origem aponta para as User Stories US-01 a US-06 do README (§4), que por sua vez estão ligadas às demandas D-01 a D-06 levantadas na entrevista com a Bulbe em 04/03/2026 (`docs/demandas.md`)

### Mapa de rastreabilidade

| US | Título | Demanda | O que exige da API |
|---|---|---|---|
| US-01 | Entender como o serviço funciona | D-01 | Conteúdo explicativo acessível sem login |
| US-02 | Visualizar economia antes de contratar | D-06 | Simulador de economia sem login |
| US-03 | Confiar no serviço antes do desconto | D-02 | Prova social e parceiros do Clube |
| US-04 | Interagir com o app antes de contratar | D-05 | Modo visitante e fluxo de adesão pelo app |
| US-05 | Engajar com o aplicativo | D-04 | Área do cliente: Clube Bulbe, cupons, indicações, dicas |
| US-06 | Acompanhar prazo de ativação | D-03 | Jornada de ativação em 5 etapas junto à CEMIG |

## Visão Geral dos Endpoints

Um endpoint por linha, cobrindo o CRUD de cada entidade do domínio. A coluna Requisito de Origem conecta cada endpoint às User Stories entregues na Aula 03.

| Método | Recurso (URI) | Descrição | Requisito de Origem | Status |
|---|---|---|---|---|
| GET | `/v1/clientes` | Lista os clientes cadastrados | US-05 | 200 |
| POST | `/v1/clientes` | Cria um novo cliente | US-05 | 201 / 400 / 409 |
| GET | `/v1/clientes/{id}` | Retorna um cliente específico | US-05 | 200 / 404 |
| PUT | `/v1/clientes/{id}` | Atualiza os dados de um cliente | US-05 | 200 / 400 / 404 |
| DELETE | `/v1/clientes/{id}` | Remove um cliente | US-05 | 204 / 404 |
| GET | `/v1/adesoes` | Lista as solicitações de adesão | US-04 | 200 |
| POST | `/v1/adesoes` | Inicia uma adesão pelo app | US-04 | 201 / 400 / 422 |
| GET | `/v1/adesoes/{id}` | Retorna uma adesão específica | US-04 | 200 / 404 |
| PUT | `/v1/adesoes/{id}` | Atualiza os dados de uma adesão em andamento | US-04 | 200 / 400 / 404 / 409 |
| DELETE | `/v1/adesoes/{id}` | Cancela uma adesão não concluída | US-04 | 204 / 404 / 409 |
| POST | `/v1/primeiro-acesso/verificacoes` | Verifica se o CPF informado já é cliente e dispara o código | US-05 | 202 / 404 |
| POST | `/v1/primeiro-acesso/confirmacoes` | Confirma o código e habilita o acesso ao app | US-05 | 201 / 400 / 410 |
| GET | `/v1/clientes/{id}/ativacao` | Retorna o status atual da ativação | US-06 | 200 / 404 |
| GET | `/v1/clientes/{id}/ativacao/etapas` | Lista as 5 etapas da jornada de ativação | US-06 | 200 / 404 |
| PATCH | `/v1/clientes/{id}/ativacao` | Avança ou corrige a etapa atual da ativação | US-06 | 200 / 400 / 404 |
| POST | `/v1/simulacoes` | Calcula a economia estimada, sem persistir | US-02 | 200 / 400 |
| GET | `/v1/clientes/{id}/indicacoes` | Lista as indicações feitas pelo cliente | US-05 | 200 / 404 |
| POST | `/v1/indicacoes` | Registra uma nova indicação | US-05 | 201 / 400 / 409 |
| GET | `/v1/indicacoes/{id}` | Retorna uma indicação específica | US-05 | 200 / 404 |
| DELETE | `/v1/indicacoes/{id}` | Cancela uma indicação ainda pendente | US-05 | 204 / 404 / 409 |
| GET | `/v1/clientes/{id}/clube` | Retorna a sequência e a próxima carta do Clube Bulbe | US-05 | 200 / 404 |
| GET | `/v1/clientes/{id}/cartas` | Lista o histórico de cartas do cliente | US-05 | 200 / 404 |
| GET | `/v1/cartas/{id}` | Retorna uma carta específica | US-05 | 200 / 404 |
| POST | `/v1/cartas/{id}/abertura` | Abre a carta da semana e gera o cupom | US-05 | 201 / 404 / 409 |
| GET | `/v1/clientes/{id}/cupons` | Lista os cupons do cliente | US-05 | 200 / 404 |
| GET | `/v1/cupons/{id}` | Retorna um cupom específico | US-05 | 200 / 404 |
| PATCH | `/v1/cupons/{id}` | Atualiza a situação do cupom (salvo ou usado) | US-05 | 200 / 400 / 404 / 409 |
| DELETE | `/v1/cupons/{id}` | Descarta um cupom do cliente | US-05 | 204 / 404 |
| GET | `/v1/parceiros` | Lista os parceiros do Clube Bulbe | US-03 | 200 |
| POST | `/v1/parceiros` | Cadastra um novo parceiro | US-03 | 201 / 400 |
| GET | `/v1/parceiros/{id}` | Retorna um parceiro específico | US-03 | 200 / 404 |
| PUT | `/v1/parceiros/{id}` | Atualiza os dados de um parceiro | US-03 | 200 / 400 / 404 |
| DELETE | `/v1/parceiros/{id}` | Remove um parceiro | US-03 | 204 / 404 |
| GET | `/v1/dicas` | Lista as dicas de economia | US-05 | 200 |
| POST | `/v1/dicas` | Cadastra uma nova dica | US-05 | 201 / 400 |
| GET | `/v1/dicas/{id}` | Retorna uma dica específica | US-05 | 200 / 404 |
| PUT | `/v1/dicas/{id}` | Atualiza uma dica | US-05 | 200 / 400 / 404 |
| DELETE | `/v1/dicas/{id}` | Remove uma dica | US-05 | 204 / 404 |

## Detalhamento dos Endpoints

### GET /v1/clientes

- **Descrição:** lista todos os clientes cadastrados, com paginação. Uso administrativo (back-office da Bulbe).
- **Requisito de origem:** US-05
- **Parâmetros de query:** `page` (número da página, opcional), `limit` (itens por página, opcional), `status` (`ativo`, `em_ativacao`, `cancelado`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
      "nome": "Marcos Andrade",
      "email": "marcos.andrade@email.com",
      "cpf": "123.456.789-00",
      "telefone": "(31) 98888-1234",
      "cidade": "Belo Horizonte",
      "uf": "MG",
      "status": "em_ativacao",
      "criado_em": "2026-05-02T13:20:00Z"
    }
  ],
  "page": 1,
  "total": 1
}
```

- **Status codes:** `200` sucesso

### POST /v1/clientes

- **Descrição:** cria um novo cliente. Chamado ao final do fluxo de adesão aprovado.
- **Requisito de origem:** US-05
- **Corpo da requisição:**

```json
{
  "nome": "Marcos Andrade",
  "email": "marcos.andrade@email.com",
  "cpf": "12345678900",
  "telefone": "31988881234",
  "endereco": {
    "cep": "30130-010",
    "logradouro": "Av. Afonso Pena",
    "numero": "1000",
    "complemento": "Apto 302",
    "bairro": "Centro",
    "cidade": "Belo Horizonte",
    "uf": "MG"
  },
  "distribuidora": "CEMIG",
  "numero_instalacao": "3001234567"
}
```

- **Exemplo de resposta (201):**

```json
{
  "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome": "Marcos Andrade",
  "email": "marcos.andrade@email.com",
  "status": "em_ativacao",
  "criado_em": "2026-05-02T13:20:00Z"
}
```

- **Status codes:** `201` criado, `400` dados inválidos, `409` CPF ou número de instalação já cadastrado

### GET /v1/clientes/{id}

- **Descrição:** retorna os dados completos de um cliente, usados no cabeçalho e na saudação da área logada.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome": "Marcos Andrade",
  "email": "marcos.andrade@email.com",
  "cpf": "123.456.789-00",
  "telefone": "(31) 98888-1234",
  "endereco": {
    "cep": "30130-010",
    "logradouro": "Av. Afonso Pena",
    "numero": "1000",
    "complemento": "Apto 302",
    "bairro": "Centro",
    "cidade": "Belo Horizonte",
    "uf": "MG"
  },
  "distribuidora": "CEMIG",
  "numero_instalacao": "3001234567",
  "status": "em_ativacao",
  "codigo_indicacao": "MARCOS50",
  "criado_em": "2026-05-02T13:20:00Z"
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### PUT /v1/clientes/{id}

- **Descrição:** atualiza os dados cadastrais do cliente. Atende também o item "Mudança de endereço" do menu lateral do app.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "nome": "Marcos Andrade",
  "email": "marcos.andrade@email.com",
  "telefone": "31988881234",
  "endereco": {
    "cep": "30140-071",
    "logradouro": "Rua Pernambuco",
    "numero": "550",
    "complemento": "Apto 101",
    "bairro": "Funcionários",
    "cidade": "Belo Horizonte",
    "uf": "MG"
  }
}
```

- **Exemplo de resposta (200):**

```json
{
  "id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome": "Marcos Andrade",
  "email": "marcos.andrade@email.com",
  "telefone": "(31) 98888-1234",
  "endereco": {
    "cep": "30140-071",
    "logradouro": "Rua Pernambuco",
    "numero": "550",
    "complemento": "Apto 101",
    "bairro": "Funcionários",
    "cidade": "Belo Horizonte",
    "uf": "MG"
  },
  "atualizado_em": "2026-08-19T10:05:00Z"
}
```

- **Status codes:** `200` atualizado, `400` dados inválidos, `404` cliente não encontrado

### DELETE /v1/clientes/{id}

- **Descrição:** remove o cliente (cancelamento da assinatura). A exclusão é lógica: o registro passa a `status: "cancelado"` e deixa de ser retornado nas listagens.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` removido, `404` cliente não encontrado

### GET /v1/adesoes

- **Descrição:** lista as solicitações de adesão feitas pelo app, com paginação.
- **Requisito de origem:** US-04
- **Parâmetros de query:** `page`, `limit`, `situacao` (`rascunho`, `enviada`, `aprovada`, `recusada`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "b2d9f4c1-7e35-42aa-8c10-5f9d2e6b4a03",
      "nome": "Clara Ribeiro",
      "email": "clara.ribeiro@email.com",
      "cidade": "Belo Horizonte",
      "uf": "MG",
      "valor_conta_atual": 320.00,
      "situacao": "enviada",
      "criado_em": "2026-08-12T09:40:00Z"
    }
  ],
  "page": 1,
  "total": 1
}
```

- **Status codes:** `200` sucesso

### POST /v1/adesoes

- **Descrição:** inicia o fluxo de adesão ("Abrir conta de luz com a Bulbe") direto pelo app, sem login. Retorna a economia estimada já calculada para reforçar o valor do serviço antes da confirmação.
- **Requisito de origem:** US-04
- **Corpo da requisição:**

```json
{
  "nome": "Clara Ribeiro",
  "email": "clara.ribeiro@email.com",
  "cpf": "98765432100",
  "telefone": "31977776666",
  "endereco": {
    "cep": "30130-010",
    "logradouro": "Av. Afonso Pena",
    "numero": "1000",
    "bairro": "Centro",
    "cidade": "Belo Horizonte",
    "uf": "MG"
  },
  "distribuidora": "CEMIG",
  "numero_instalacao": "3007654321",
  "valor_conta_atual": 320.00
}
```

- **Exemplo de resposta (201):**

```json
{
  "id": "b2d9f4c1-7e35-42aa-8c10-5f9d2e6b4a03",
  "situacao": "enviada",
  "economia_mensal_estimada": 48.00,
  "prazo_ativacao_dias": 90,
  "criado_em": "2026-08-12T09:40:00Z"
}
```

- **Status codes:** `201` criado, `400` dados inválidos, `422` instalação fora da área atendida pela Bulbe

### GET /v1/adesoes/{id}

- **Descrição:** retorna uma adesão específica, permitindo ao usuário retomar um cadastro interrompido.
- **Requisito de origem:** US-04
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "b2d9f4c1-7e35-42aa-8c10-5f9d2e6b4a03",
  "nome": "Clara Ribeiro",
  "email": "clara.ribeiro@email.com",
  "cpf": "987.654.321-00",
  "telefone": "(31) 97777-6666",
  "distribuidora": "CEMIG",
  "numero_instalacao": "3007654321",
  "valor_conta_atual": 320.00,
  "economia_mensal_estimada": 48.00,
  "situacao": "enviada",
  "cliente_id": null,
  "criado_em": "2026-08-12T09:40:00Z"
}
```

- **Status codes:** `200` sucesso, `404` adesão não encontrada

### PUT /v1/adesoes/{id}

- **Descrição:** atualiza os dados de uma adesão ainda não aprovada (correção de cadastro ou continuação de rascunho).
- **Requisito de origem:** US-04
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "nome": "Clara Ribeiro",
  "email": "clara.ribeiro@email.com",
  "telefone": "31955554444",
  "numero_instalacao": "3007654321",
  "valor_conta_atual": 350.00
}
```

- **Exemplo de resposta (200):**

```json
{
  "id": "b2d9f4c1-7e35-42aa-8c10-5f9d2e6b4a03",
  "situacao": "enviada",
  "valor_conta_atual": 350.00,
  "economia_mensal_estimada": 52.50,
  "atualizado_em": "2026-08-13T11:02:00Z"
}
```

- **Status codes:** `200` atualizado, `400` dados inválidos, `404` adesão não encontrada, `409` adesão já aprovada, não pode ser alterada

### DELETE /v1/adesoes/{id}

- **Descrição:** cancela uma adesão ainda não aprovada (desistência do usuário).
- **Requisito de origem:** US-04
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` cancelada, `404` adesão não encontrada, `409` adesão já aprovada, não pode ser cancelada por aqui

### POST /v1/primeiro-acesso/verificacoes

- **Descrição:** atende o botão "É minha primeira vez no app". Verifica se o CPF informado corresponde a um cliente existente e dispara um código de confirmação para o contato cadastrado.
- **Requisito de origem:** US-05
- **Corpo da requisição:**

```json
{
  "cpf": "12345678900",
  "canal": "whatsapp"
}
```

- **Exemplo de resposta (202):**

```json
{
  "verificacao_id": "5c8e1f77-9a0b-4d62-93ac-1e7b8d40f2aa",
  "canal": "whatsapp",
  "destino_mascarado": "(31) *****-1234",
  "expira_em": "2026-08-19T10:15:00Z"
}
```

- **Status codes:** `202` código enviado, `404` CPF não encontrado na base de clientes

### POST /v1/primeiro-acesso/confirmacoes

- **Descrição:** confirma o código recebido e habilita o acesso do cliente ao app. A emissão de credenciais/token depende da definição de autenticação da Aula 29.
- **Requisito de origem:** US-05
- **Corpo da requisição:**

```json
{
  "verificacao_id": "5c8e1f77-9a0b-4d62-93ac-1e7b8d40f2aa",
  "codigo": "482913"
}
```

- **Exemplo de resposta (201):**

```json
{
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "acesso_habilitado": true,
  "confirmado_em": "2026-08-19T10:12:00Z"
}
```

- **Status codes:** `201` acesso habilitado, `400` código inválido, `410` código expirado

### GET /v1/clientes/{id}/ativacao

- **Descrição:** retorna o resumo da jornada de ativação exibido na tela Conexão: percentual concluído, etapa atual e prazo estimado.
- **Requisito de origem:** US-06
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "etapa_atual": 2,
  "total_etapas": 5,
  "percentual_concluido": 30,
  "titulo": "Documentação sendo analisada",
  "descricao": "Seus documentos estão em análise. Em breve entraremos em contato.",
  "distribuidora": "CEMIG",
  "prazo_ativacao_dias": 90,
  "previsao_conclusao": "2026-07-31",
  "atualizado_em": "2026-08-18T08:00:00Z"
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### GET /v1/clientes/{id}/ativacao/etapas

- **Descrição:** lista as 5 etapas da jornada, com a situação de cada uma. Alimenta a timeline da tela Detalhes.
- **Requisito de origem:** US-06
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    { "numero": 1, "nome": "Cadastro",        "titulo": "Cadastro realizado",             "descricao": "Seu cadastro foi concluído com sucesso.",                                        "situacao": "concluida", "concluida_em": "2026-05-02" },
    { "numero": 2, "nome": "Documentos",      "titulo": "Documentação sendo analisada",   "descricao": "Seus documentos estão em análise. Em breve entraremos em contato.",               "situacao": "atual",     "concluida_em": null },
    { "numero": 3, "nome": "Solicitação",     "titulo": "Solicitação enviada à CEMIG",    "descricao": "A Bulbe protocolou o pedido para a CEMIG liberar sua conexão.",                   "situacao": "pendente",  "concluida_em": null },
    { "numero": 4, "nome": "Análise CEMIG",   "titulo": "Em análise pela CEMIG",          "descricao": "Aguardando aprovação da CEMIG.",                                                  "situacao": "pendente",  "concluida_em": null },
    { "numero": 5, "nome": "Energia liberada","titulo": "Energia aprovada",               "descricao": "Em breve ela será liberada e seu desconto vai começar a aparecer na fatura.",     "situacao": "pendente",  "concluida_em": null }
  ],
  "total": 5
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### PATCH /v1/clientes/{id}/ativacao

- **Descrição:** avança ou corrige a etapa atual da ativação. Uso interno da Bulbe e da integração com a concessionária; é o endpoint que substitui os botões de teste "Próxima etapa" do protótipo.
- **Requisito de origem:** US-06
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "etapa_atual": 3,
  "observacao": "Protocolo 2026-CEMIG-88214 aberto."
}
```

- **Exemplo de resposta (200):**

```json
{
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "etapa_atual": 3,
  "percentual_concluido": 45,
  "titulo": "Solicitação enviada à CEMIG",
  "atualizado_em": "2026-08-19T10:20:00Z"
}
```

- **Status codes:** `200` atualizado, `400` etapa fora do intervalo de 1 a 5, `404` cliente não encontrado

### POST /v1/simulacoes

- **Descrição:** calcula a economia estimada com a Bulbe a partir do valor da conta, do período e do número de amigos indicados. É público (não exige login) e **não persiste** a simulação — apenas devolve o cálculo.
- **Requisito de origem:** US-02
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "valor_conta": 320.00,
  "meses": 12,
  "amigos_indicados": 2
}
```

- **Exemplo de resposta (200):**

```json
{
  "valor_conta": 320.00,
  "meses": 12,
  "amigos_indicados": 2,
  "percentual_desconto": 15,
  "desconto_mensal": 48.00,
  "desconto_periodo": 576.00,
  "bonus_indicacoes": 100.00,
  "economia_total": 676.00,
  "nova_conta_mensal": 272.00,
  "comparativo": {
    "sem_bulbe_mensal": 320.00,
    "com_bulbe_mensal": 272.00,
    "sem_bulbe_periodo": 3840.00,
    "com_bulbe_periodo": 3264.00
  },
  "observacao": "O desconto de 15% não incide sobre o frete e a taxa de iluminação pública."
}
```

- **Status codes:** `200` cálculo realizado, `400` dados inválidos (valor da conta menor ou igual a zero, meses fora do intervalo de 1 a 60, amigos indicados negativo)

### GET /v1/clientes/{id}/indicacoes

- **Descrição:** lista as indicações feitas pelo cliente e o bônus acumulado, alimentando o card "Indique e ganhe R$ 50".
- **Requisito de origem:** US-05
- **Parâmetros de query:** `page`, `limit`, `situacao` (`pendente`, `aderiu`, `expirada`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "codigo_indicacao": "MARCOS50",
  "bonus_por_indicacao": 50.00,
  "bonus_acumulado": 100.00,
  "data": [
    {
      "id": "d41f9b02-6c7a-4f18-b0e9-2a5c3d8e7f44",
      "nome_indicado": "Renato Souza",
      "contato_indicado": "(31) 96666-5555",
      "situacao": "aderiu",
      "bonus": 50.00,
      "criado_em": "2026-07-04T14:10:00Z"
    }
  ],
  "page": 1,
  "total": 1
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### POST /v1/indicacoes

- **Descrição:** registra uma nova indicação feita por um cliente. O bônus de R$ 50 é creditado na próxima fatura somente quando o indicado conclui a adesão.
- **Requisito de origem:** US-05
- **Corpo da requisição:**

```json
{
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome_indicado": "Renato Souza",
  "contato_indicado": "31966665555",
  "canal": "whatsapp"
}
```

- **Exemplo de resposta (201):**

```json
{
  "id": "d41f9b02-6c7a-4f18-b0e9-2a5c3d8e7f44",
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome_indicado": "Renato Souza",
  "situacao": "pendente",
  "bonus_previsto": 50.00,
  "criado_em": "2026-08-19T10:30:00Z"
}
```

- **Status codes:** `201` criada, `400` dados inválidos, `409` contato já indicado ou já é cliente Bulbe

### GET /v1/indicacoes/{id}

- **Descrição:** retorna os dados de uma indicação específica.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "d41f9b02-6c7a-4f18-b0e9-2a5c3d8e7f44",
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "nome_indicado": "Renato Souza",
  "contato_indicado": "(31) 96666-5555",
  "canal": "whatsapp",
  "situacao": "aderiu",
  "bonus": 50.00,
  "creditado_em": "2026-07-20",
  "criado_em": "2026-07-04T14:10:00Z"
}
```

- **Status codes:** `200` sucesso, `404` indicação não encontrada

### DELETE /v1/indicacoes/{id}

- **Descrição:** cancela uma indicação ainda pendente.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` cancelada, `404` indicação não encontrada, `409` indicação já convertida, o bônus já foi creditado

### GET /v1/clientes/{id}/clube

- **Descrição:** retorna a situação do cliente no Clube Bulbe: sequência de semanas, meta de 5 semanas e disponibilidade da próxima carta. Alimenta o card "Próxima carta" da tela Vantagens.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "semanas_sequencia": 3,
  "meta_sequencia": 5,
  "carta_disponivel": false,
  "bonus_especial_pendente": false,
  "proxima_carta": {
    "carta_id": "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
    "disponivel_em": "2026-06-19T09:00:00Z",
    "dias_restantes": 4
  },
  "intervalo_dias": 7
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### GET /v1/clientes/{id}/cartas

- **Descrição:** lista o histórico de cartas semanais do cliente, exibido na seção "Histórico de cartas".
- **Requisito de origem:** US-05
- **Parâmetros de query:** `page`, `limit`, `situacao` (`disponivel`, `aberta`, `expirada`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
      "semana": 3,
      "tipo": "normal",
      "situacao": "aberta",
      "disponivel_em": "2026-06-12T09:00:00Z",
      "aberta_em": "2026-06-12T19:42:00Z",
      "cupom_id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"
    }
  ],
  "page": 1,
  "total": 1
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### GET /v1/cartas/{id}

- **Descrição:** retorna uma carta específica, com a recompensa associada quando já aberta.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "semana": 3,
  "tipo": "normal",
  "situacao": "aberta",
  "disponivel_em": "2026-06-12T09:00:00Z",
  "aberta_em": "2026-06-12T19:42:00Z",
  "cupom_id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22"
}
```

- **Status codes:** `200` sucesso, `404` carta não encontrada

### POST /v1/cartas/{id}/abertura

- **Descrição:** abre a carta da semana. Sorteia a recompensa, gera o cupom com validade de 14 dias, incrementa a sequência do cliente e agenda a próxima carta para 7 dias depois. Ao completar a 5ª semana, libera o bônus especial de R$ 50 na fatura. A operação é idempotente: reabrir uma carta já aberta devolve o mesmo cupom.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica (a carta e o cliente já estão identificados pela URI)
- **Exemplo de resposta (201):**

```json
{
  "carta_id": "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
  "semanas_sequencia": 4,
  "meta_sequencia": 5,
  "cupom": {
    "id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
    "titulo": "500 pontos Livelo",
    "descricao": "Use o cupom no app ou site da Livelo para liberar os 500 pontos na sua conta.",
    "codigo": "BULBELIV500",
    "parceiro": { "id": "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06", "nome": "Livelo", "categoria": "Programa de pontos" },
    "situacao": "ativo",
    "valido_ate": "2026-06-26"
  },
  "proxima_carta_em": "2026-06-19T09:00:00Z"
}
```

- **Status codes:** `201` carta aberta e cupom gerado, `404` carta não encontrada, `409` carta ainda não disponível ou já expirada

### GET /v1/clientes/{id}/cupons

- **Descrição:** lista os cupons do cliente, usados nas seções "Cartas ativas" e "Histórico" da tela Vantagens.
- **Requisito de origem:** US-05
- **Parâmetros de query:** `page`, `limit`, `situacao` (`ativo`, `salvo`, `usado`, `expirado`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
      "titulo": "15% de desconto na Araújo",
      "codigo": "BULBE15",
      "parceiro": { "id": "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9", "nome": "Drogaria Araújo" },
      "situacao": "ativo",
      "valido_ate": "2026-06-12",
      "dias_restantes": 9
    }
  ],
  "page": 1,
  "total": 1
}
```

- **Status codes:** `200` sucesso, `404` cliente não encontrado

### GET /v1/cupons/{id}

- **Descrição:** retorna um cupom específico, com todos os dados da tela de recompensa.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
  "cliente_id": "8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11",
  "carta_id": "a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55",
  "tag": "PARCERIA DROGARIA ARAÚJO",
  "titulo": "15% de desconto na Araújo",
  "descricao": "Use o cupom em qualquer loja física ou no app da Araújo.",
  "codigo": "BULBE15",
  "parceiro": {
    "id": "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
    "nome": "Drogaria Araújo",
    "categoria": "Farmácia",
    "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/araujo.png"
  },
  "situacao": "ativo",
  "aberto_em": "2026-05-29T09:12:00Z",
  "valido_ate": "2026-06-12",
  "dias_restantes": 9
}
```

- **Status codes:** `200` sucesso, `404` cupom não encontrado

### PATCH /v1/cupons/{id}

- **Descrição:** atualiza a situação do cupom conforme a ação do usuário na tela de recompensa: "Salvar" muda para `salvo`, "Usar agora" muda para `usado`.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "situacao": "usado"
}
```

- **Exemplo de resposta (200):**

```json
{
  "id": "f6b1d803-2e94-4a57-83cd-9b0e5a7c1d22",
  "situacao": "usado",
  "usado_em": "2026-06-03T15:27:00Z"
}
```

- **Status codes:** `200` atualizado, `400` situação inválida, `404` cupom não encontrado, `409` cupom expirado ou já utilizado

### DELETE /v1/cupons/{id}

- **Descrição:** descarta um cupom da lista do cliente. Exclusão lógica, o registro permanece no histórico interno.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` descartado, `404` cupom não encontrado

### GET /v1/parceiros

- **Descrição:** lista os parceiros do Clube Bulbe exibidos na seção "Parceiros do Clube". Endpoint público, também serve como prova social para quem ainda não é cliente.
- **Requisito de origem:** US-03
- **Parâmetros de query:** `page`, `limit`, `categoria` (opcional), `ativo` (`true`/`false`, opcional)
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
      "nome": "Drogaria Araújo",
      "categoria": "Farmácia",
      "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/araujo.png",
      "ativo": true
    },
    {
      "id": "2b3c4d5e-6f70-4812-9a3b-c4d5e6f70819",
      "nome": "Banco Inter",
      "categoria": "Banco",
      "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/inter.png",
      "ativo": true
    }
  ],
  "page": 1,
  "total": 2
}
```

- **Status codes:** `200` sucesso

### POST /v1/parceiros

- **Descrição:** cadastra um novo parceiro do Clube Bulbe. Uso administrativo.
- **Requisito de origem:** US-03
- **Corpo da requisição:**

```json
{
  "nome": "Livelo",
  "categoria": "Programa de pontos",
  "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/livelo.svg",
  "ativo": true
}
```

- **Exemplo de resposta (201):**

```json
{
  "id": "3e5a7c19-8b24-4d60-a1f3-7c9e2b5d8a06",
  "nome": "Livelo",
  "categoria": "Programa de pontos",
  "ativo": true,
  "criado_em": "2026-08-19T10:40:00Z"
}
```

- **Status codes:** `201` criado, `400` dados inválidos

### GET /v1/parceiros/{id}

- **Descrição:** retorna um parceiro específico.
- **Requisito de origem:** US-03
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
  "nome": "Drogaria Araújo",
  "categoria": "Farmácia",
  "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/araujo.png",
  "ativo": true,
  "criado_em": "2026-05-20T12:00:00Z"
}
```

- **Status codes:** `200` sucesso, `404` parceiro não encontrado

### PUT /v1/parceiros/{id}

- **Descrição:** atualiza os dados de um parceiro.
- **Requisito de origem:** US-03
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "nome": "Drogaria Araújo",
  "categoria": "Farmácia e saúde",
  "logo_url": "https://cdn.bulbeenergia.com.br/parceiros/araujo-v2.png",
  "ativo": true
}
```

- **Exemplo de resposta (200):**

```json
{
  "id": "1d2c3b4a-5e6f-4071-8293-a4b5c6d7e8f9",
  "nome": "Drogaria Araújo",
  "categoria": "Farmácia e saúde",
  "atualizado_em": "2026-08-19T10:45:00Z"
}
```

- **Status codes:** `200` atualizado, `400` dados inválidos, `404` parceiro não encontrado

### DELETE /v1/parceiros/{id}

- **Descrição:** remove um parceiro do Clube. Cupons já emitidos por esse parceiro continuam válidos até o vencimento.
- **Requisito de origem:** US-03
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` removido, `404` parceiro não encontrado

### GET /v1/dicas

- **Descrição:** lista as dicas de economia de energia exibidas no carrossel da tela Dicas, com a economia estimada de cada uma.
- **Requisito de origem:** US-05
- **Parâmetros de query:** `page`, `limit`
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "data": [
    {
      "id": "9a8b7c6d-5e4f-4031-8291-0a1b2c3d4e5f",
      "titulo": "Troque por LED",
      "descricao": "Lâmpadas LED duram mais e gastam menos energia",
      "icone_url": "https://cdn.bulbeenergia.com.br/dicas/led.svg",
      "economia_mensal": 12.00,
      "economia_anual": 144.00,
      "ordem": 1
    },
    {
      "id": "0b1c2d3e-4f50-4617-a829-3b4c5d6e7f80",
      "titulo": "Banhos rápidos",
      "descricao": "Além de economizar água, você economiza energia",
      "icone_url": "https://cdn.bulbeenergia.com.br/dicas/chuveiro.svg",
      "economia_mensal": 18.00,
      "economia_anual": 216.00,
      "ordem": 2
    }
  ],
  "page": 1,
  "total": 4
}
```

- **Status codes:** `200` sucesso

### POST /v1/dicas

- **Descrição:** cadastra uma nova dica de economia. Uso administrativo.
- **Requisito de origem:** US-05
- **Corpo da requisição:**

```json
{
  "titulo": "Cestos cheios",
  "descricao": "Prefira usar máquinas de lavar apenas quando estiverem cheias. Menos ciclos, mais energia",
  "icone_url": "https://cdn.bulbeenergia.com.br/dicas/lavanderia.svg",
  "economia_mensal": 8.00,
  "economia_anual": 96.00,
  "ordem": 3
}
```

- **Exemplo de resposta (201):**

```json
{
  "id": "1c2d3e4f-5061-4728-b93a-4c5d6e7f8091",
  "titulo": "Cestos cheios",
  "ordem": 3,
  "criado_em": "2026-08-19T10:50:00Z"
}
```

- **Status codes:** `201` criada, `400` dados inválidos

### GET /v1/dicas/{id}

- **Descrição:** retorna uma dica específica.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (200):**

```json
{
  "id": "9a8b7c6d-5e4f-4031-8291-0a1b2c3d4e5f",
  "titulo": "Troque por LED",
  "descricao": "Lâmpadas LED duram mais e gastam menos energia",
  "icone_url": "https://cdn.bulbeenergia.com.br/dicas/led.svg",
  "economia_mensal": 12.00,
  "economia_anual": 144.00,
  "ordem": 1,
  "criado_em": "2026-06-01T09:00:00Z"
}
```

- **Status codes:** `200` sucesso, `404` dica não encontrada

### PUT /v1/dicas/{id}

- **Descrição:** atualiza o conteúdo de uma dica.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:**

```json
{
  "titulo": "Cômodos em uso",
  "descricao": "Deixe ligadas apenas as luzes dos cômodos em que você está.",
  "icone_url": "https://cdn.bulbeenergia.com.br/dicas/lampada-apagada.svg",
  "economia_mensal": 6.00,
  "economia_anual": 72.00,
  "ordem": 4
}
```

- **Exemplo de resposta (200):**

```json
{
  "id": "2d3e4f50-6172-4839-a04b-5d6e7f809102",
  "titulo": "Cômodos em uso",
  "ordem": 4,
  "atualizado_em": "2026-08-19T10:55:00Z"
}
```

- **Status codes:** `200` atualizada, `400` dados inválidos, `404` dica não encontrada

### DELETE /v1/dicas/{id}

- **Descrição:** remove uma dica do carrossel.
- **Requisito de origem:** US-05
- **Parâmetros de query:** não se aplica
- **Corpo da requisição:** não se aplica
- **Exemplo de resposta (204):** sem corpo
- **Status codes:** `204` removida, `404` dica não encontrada

## Observações

**Regras de negócio extraídas do front-end entregue** (todas conferidas no código, não presumidas):

- Desconto de **15%** sobre o valor da conta de energia, excluindo frete e taxa de iluminação pública (`final.js`, `valorConta * 0.15`; README §2 e `docs/demandas.md`, D-06).
- Bônus de **R$ 50 por amigo indicado**, creditado na próxima fatura (`amigos * 50`; card "Indique e ganhe R$50").
- Prazo de ativação de **até 90 dias**, dependente da CEMIG (D-03 e US-06).
- Jornada de ativação com **5 etapas**: Cadastro, Documentos, Solicitação, Análise CEMIG e Energia liberada, com percentuais de 30%, 45%, 70% e 90% para as etapas 2 a 5.
- Clube Bulbe: **1 carta a cada 7 dias**, meta de **5 semanas** de sequência, cupom válido por **14 dias** e bônus especial de **R$ 50 na fatura** ao completar a 5ª semana.
- Recompensas atuais em rotação: Araújo 15% (`BULBE15`), Inter cashback dobrado (`INTERCASH`), indicação dobrada por 30 dias (`BULBEDUO`), Livelo 500 pontos (`BULBELIV500`) e Araújo 10% (`BULBE10`).

**Premissas assumidas pela equipe:**

1. **Rastreabilidade por User Story.** O projeto não produziu um documento com requisitos numerados no formato RF-XX; a rastreabilidade usa as User Stories US-01 a US-06 do README, que já estão ligadas às demandas D-01 a D-06.
2. **Exclusão lógica.** `DELETE` em clientes e cupons não apaga o registro fisicamente: marca-o como cancelado/descartado, preservando o histórico exigido pela operação.
3. **`POST /v1/simulacoes` responde 200, não 201**, porque não cria recurso — o cálculo é feito no servidor e devolvido sem persistência, conforme decisão da squad.
4. **Endpoints públicos vs. autenticados.** São públicos `POST /v1/simulacoes`, `POST /v1/adesoes`, `GET /v1/parceiros` e `GET /v1/dicas`, atendendo às US-02 e US-04 (usar o app antes de assinar). Os demais pressupõem cliente identificado; a forma de autenticação será definida na Aula 29.
5. **A simulação de dias do protótipo não virou API.** Os botões "Passar 1 dia" / "Resetar" do `final.js` são ferramenta de demonstração do front; no back-end a disponibilidade da carta passa a depender de data real.
6. **Estado no servidor.** O Clube Bulbe hoje vive em `localStorage` (chave `clube_bulbe_v3`); com a API, o estado passa a ser do servidor e o app deixa de guardar sequência, cupons e etapas localmente.

**Pontos a validar com o professor ou com a Bulbe:**

- **Adesão e indicações não têm User Story dedicada.** O fluxo de adesão vem do item 3 da Solução Proposta (README §1.3) e o "Indique e ganhe R$ 50" aparece em várias telas, mas nenhum dos dois tem US própria — foram rastreados para US-04 e US-05 por proximidade. Talvez valha criar US-07 (adesão pelo app) e US-08 (programa de indicação).
- **Autenticação e primeiro acesso.** Os dois endpoints de `/v1/primeiro-acesso` cobrem a validação do cliente e o envio de código, mas a emissão de credencial/token depende da definição da Aula 29.
- **Recompensas fixas vs. cadastráveis.** No protótipo, as 5 recompensas do Clube são um array fixo no código. Não foi criada uma entidade `recompensas` com CRUD próprio; se a Bulbe precisar cadastrar campanhas, ela deve entrar na próxima sprint.
- **Fora do escopo desta entrega**, por decisão da squad: faturas e economia realizada, notificações (o sino do app), FAQ/conteúdo institucional, "Fale conosco" e o formulário de mudança de endereço (hoje coberto parcialmente pelo `PUT /v1/clientes/{id}`).

## Próximos passos

Este documento será formalizado em OpenAPI/Swagger em `docs/api/openapi.yaml` e servirá de base para a modelagem dos casos de uso na Aula 06 (Modelagem Comportamental, Casos de Uso da API).
