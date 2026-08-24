# Projeto Back-End — Bulbe Energia

> Uma ou duas linhas descrevendo o que o sistema faz e para qual empresa parceira foi desenvolvido.

## Sobre o projeto

- **Empresa parceira:** Bulbe Energia
- **Problema que o projeto resolve:** [descrição breve do contexto e da demanda real da empresa]
- **Continuidade:** este repositório é o backend construído no Projeto Ciência de Dados II, consumido pelo frontend entregue no Projeto Ciência de Dados I. Repositório do frontend: [link](https://github.com/gabrielmercedo/Bulbe-Squad-cleanergy)

## Equipe

| Nome | Matrícula | Frente principal |
|---|---|---|
| [nome do aluno] | [matrícula] | API / Banco de Dados / Autenticação / Testes |
| Luiz Felipe Luppi Mendonça | 2025 0287 6254 | |
| Samuel Gandra Paranhos | 2025 0713 9975 | |
| João Victor Silva Lenza | 2025 0701 4218 | |
| Gabriel Mercedo Faria | 2025 0701 4226 | |
| Rafael Alcântara Brescia | 2025 0100 7431 | |
| Rodrigo Rennò | | |

## Tecnologias utilizadas

- **Linguagem:** [ex: Python, Java, Node.js]
- **Framework:** [ex: FastAPI, Spring Boot, Express]
- **Banco de dados:** [ex: PostgreSQL, MySQL]
- **ORM:** [ex: SQLAlchemy, Hibernate, Prisma]
- **Testes:** [ex: Pytest, JUnit, Jest]
- **Outras ferramentas:** [ex: Docker, Swagger/OpenAPI]

## Arquitetura

Descrição breve das camadas do sistema (apresentação, serviço, domínio, persistência) e como elas se comunicam. Diagrama completo em `docs/arquitetura/diagrama-camadas.png`.

## Estrutura de pastas

```
src/
├── controllers/    recebe requisições e formata respostas
├── services/       regras de negócio e orquestração
├── repositories/   acesso a dados
├── domain/         entidades do domínio
├── middlewares/     autenticação e tratamento de erros
└── config/         configurações da aplicação
```

## Como executar o projeto

1. Clonar o repositório
   ```bash
   git clone [url-do-repositorio]
   ```
2. Instalar as dependências
   ```bash
   [comando de instalação]
   ```
3. Configurar as variáveis de ambiente
   ```bash
   cp .env.example .env
   ```
4. Rodar as migrations do banco de dados
   ```bash
   [comando de migration]
   ```
5. Iniciar o servidor
   ```bash
   [comando para rodar o projeto]
   ```

A aplicação sobe por padrão em `http://localhost:[porta]`.

## Como rodar os testes

```bash
[comando de teste unitário]
[comando de teste de integração]
```

## Documentação da API

Contrato completo em `docs/api/openapi.yaml`. Principais endpoints:

| Método | Rota | Descrição |
|---|---|---|
| GET | `/exemplo` | [descrição] |
| POST | `/exemplo` | [descrição] |
| PUT | `/exemplo/{id}` | [descrição] |
| DELETE | `/exemplo/{id}` | [descrição] |

## Banco de dados

Modelo lógico, físico e dicionário de dados em `docs/banco-de-dados/`.

## Sprints e backlog

- Board do projeto: [link Trello/Jira/GitHub Projects]
- Documentação de cada Planning e Review em `docs/sprints/`

## Convenção de commits e branches

- Branches: `main` (estável) e `feature/nome-da-funcionalidade`
- Commits no padrão Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- Pull Requests revisados por pelo menos um integrante do grupo antes do merge

## Extensão universitária

Como o projeto se conecta a um dos eixos da ementa (relações étnico-raciais, cultura afro-brasileira e indígena, direitos humanos, sustentabilidade ou educação ambiental). [descrição a ser preenchida na Aula 32]

## Contexto acadêmico

Projeto desenvolvido para a disciplina Projeto Ciência de Dados II, Ibmec, 2º semestre de 2026, sob orientação do professor Cristiano de Macedo Neto, M.Sc.
