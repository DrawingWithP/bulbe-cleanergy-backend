# Documento de Requisitos Técnicos, App Bulbe Energia - Cleanergy

## Identificação

- **Projeto:** App Bulbe Energia — API (back-end do front-end entregue na Sprint anterior)
- **Empresa parceira:** Bulbe Energia — bulbeenergia.com.br
- **Equipe:** Cleanergy Squad
- **Integrantes:** Samuel Gandra Paranhos (líder), Gabriel Mercedo Moreira Lins de Faria, João Victor Silva Lenza, Luiz Felipe Luppi Mendonça, Rafael Alcântara Brescia, Rodrigo Rennó Pimentel Bello Santos.
- **Data:** 17/08/2026
- **Sprint / Etapa:** Sprint 1, Elicitação

## Como este documento foi construído

Os requisitos abaixo foram levantados a partir da análise das funcionalidades já implementadas no frontend do Projeto Ciência de Dados I. Para cada tela ou ação existente, a equipe identificou o que o backend precisa oferecer para sustentá-la, classificando cada requisito como funcional (RF) ou não funcional (RNF).

## Tabela de Requisitos

| ID | Funcionalidade do Frontend (Projeto I) | Requisito Técnico Derivado (Backend) | Tipo | Prioridade |
|---|---|---|---|---|
| RF-01 | Tela de login | Com base no nome, email, senha e número de telefone, criar um novo usuário | RF | Alta |
| RF-02 | Informe de conta de luz (criação de conta) | Confirmar conta de luz, concluindo o sign in, estando ou não a conta no nome do cadastrante | RF | Alta |
| RF-03 | Simulador de economia | Dados variarem segundo a bandeira e cotação atual, mensalmente | RF | Média |
| RF-04 | Tela status/detalhes | Dados tem que mudar segundo os dados do usuário no processo | RF | Média |
| RF-05 | Tela vantagens | Contar, segundo a sequência de login do usuário, sua ofensiva | RF | Baixa |
| RF-06 | Tela vantagens | Mostrar ao usuário suas cartas ativas e as individualidades delas (tempo de uso e expiração) | RF | Medía |
| RF-07 | Tela vantagens | Lista de vantagens | RF | Medía |
| RF-08 | Tela dicas | Listagem de dicas | RF | Medía |
| RNF-01 | Senhas criptografadas | Usar hash ou salt pra criptografar senhas | RNF | Alta |


## Legenda

- **RF, Requisito Funcional:** descreve o que o sistema deve fazer, uma função ou ação esperada.
- **RNF, Requisito Não Funcional:** descreve como o sistema deve se comportar, uma qualidade ou restrição técnica.
- **Prioridade Alta:** essencial para o funcionamento básico do sistema.
- **Prioridade Média:** importante, mas não bloqueia a primeira entrega.
- **Prioridade Baixa:** desejável, pode ficar para uma sprint futura.

## Rastreabilidade (o que foi implementado)

| ID | Onde está | Situação |
|---|---|---|
| RF-01 | `POST /v1/auth/registrar` e `POST /v1/auth/login` (operadores); `POST /v1/clientes` (cliente) | Implementado. O app ainda não tem login de cliente: o frontend usa um cliente de demonstração (`BULBE_FRONTEND_CLIENTE_ID`) |
| RF-02 | `POST /v1/primeiro-acesso/verificacoes` e `/confirmacoes` | Implementado (o envio real de SMS/e-mail fica fora do escopo) |
| RF-03 | `POST /v1/simulacoes` + `/v1/bandeiras` | Implementado: a economia usa a bandeira tarifária do mês, cadastrada pelo operador |
| RF-04 | `GET /v1/clientes/{id}/ativacao` e `/etapas`; `PATCH` (operador e painel interno) | Implementado |
| RF-05 | `GET /v1/clientes/{id}/clube` (sequência de semanas) | Implementado |
| RF-06 | `GET /v1/clientes/{id}/cartas`, `/cupons`, `POST /v1/cartas/{id}/abertura` | Implementado |
| RF-07 | `GET /v1/parceiros` | Implementado |
| RF-08 | `GET /v1/dicas` | Implementado |
| RNF-01 | `app/core/security.py` (bcrypt com salt) | Implementado. Em produção, `BULBE_SECRET_KEY` é obrigatória |

O sistema de gerenciamento interno (`sistema-de-gerenciamento/`) lê os mesmos dados e permite à equipe da Bulbe
acompanhar os clientes e alterar a etapa de ativação, que volta para o app pela API.
