# Documento de Requisitos Técnicos, App Bulbe Energia - Cleanergy

> Preencha os campos entre colchetes. Remova esta linha de instrução antes da entrega.

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

## Próximos passos

Estes requisitos serão utilizados na Aula 04 (Engenharia de Requisitos para APIs) para desenhar o contrato de endpoints da API.
