# Dicionário de dados — banco fictício do painel

> Banco: **SQLite** (arquivo `app/database/bulbe_ficticio.db`, configurável por `BULBE_DB_URL`), mapeado com
> **SQLAlchemy 2** em `app/database/modelos.py` e populado por `app/database/seed.py` com dados **fictícios**
> e determinísticos (`random.Random(42)`, sem Faker).

## Convenções

- **IDs**: `clientes`, `adesoes`, `cartas`, `cupons`, `indicacoes` e `parceiros` usam **UUID v4 em texto** (36 caracteres).
  As demais tabelas usam **inteiro autoincremento**.
- **Datas**: `date` (`AAAA-MM-DD`) e `datetime` em **UTC**; as consultas devolvem tudo como texto ISO 8601.
- **Dinheiro**: `float` com 2 casas, em reais.
- **CPF e telefone**: só dígitos no banco. O painel mostra completo; o chatbot **mascara** antes de enviar ao modelo.
- **Coluna "Origem"**: diz se a informação/funcionalidade **já existe na Bulbe** (app ou site),
  foi **criada pela squad** Cleanergy (front do Projeto I / API do Projeto II) ou é **do painel** (nova, interna).
- **Enumerações** são guardadas como texto; os valores aceitos aparecem na descrição e são garantidos por
  restrições `CHECK` no banco (assim como as faixas: etapa 1–5, sequência 0–5, meses 1–60, CPF com 11 dígitos).
- **Unicidade** garantida no banco: e-mail do funcionário, CPF e nº de instalação do cliente, código de indicação,
  nome do parceiro, uma fatura por cliente e mês, uma carta por cliente e semana.
- **Chaves estrangeiras** ligadas no SQLite com `PRAGMA foreign_keys=ON`. `cartas.cupom_id` ↔ `cupons.carta_id`
  formam uma FK circular (resolvida com `use_alter` + `post_update`).
- "null" na coluna Tipo indica campo opcional (`Optional` em `modelos.py`).
- Conferido em `app/database/modelos.py` (classes `Mapped`/`mapped_column`) em 18/10/2026.

## Visão geral das tabelas

| Tabela | Descrição | Origem | Volume no seed |
|---|---|---|---|
| `funcionarios` | Funcionários que acessam o painel | Painel | 3 |
| `usinas` | Fazendas solares da Bulbe | Bulbe | 4 (1 em manutenção) |
| `clientes` | Clientes (assinantes) | Bulbe | 64 (40 `ativo`, 16 `em_ativacao`, 8 `cancelado`) |
| `adesoes` | Pedidos de adesão (app, site, WhatsApp) | Squad + Bulbe | 16 (8 aprovadas, 4 enviadas, 2 rascunhos, 2 recusadas) |
| `ativacoes` | Etapa atual da jornada de ativação | Squad | 1 por cliente |
| `ativacao_eventos` | Histórico de passagens de etapa | Squad | 1 por etapa atingida |
| `faturas` | Faturas mensais (2ª via, histórico) | Bulbe | até 12 meses por cliente ativo; 5 inadimplentes com faturas vencidas; nenhuma para quem está em ativação |
| `indicacoes` | Indique e Ganhe | Bulbe | várias (aderiu, pendente, expirada) |
| `parceiros` | Parceiros do Clube Bulbe | Squad | 6 (Araújo, Inter, Livelo, Bulbe e duas marcas inventadas, uma inativa) |
| `clube_status` | Sequência do cliente no Clube | Squad | 1 por cliente com acesso ao app que não cancelou |
| `cartas` | Cartas semanais do Clube | Squad | 1 a cada 7 dias por participante |
| `cupons` | Cupons gerados pelas cartas | Squad | 1 por carta aberta |
| `dicas` | Dicas de economia | Squad | 4 |
| `simulacoes` | Simulações de economia (visitante ou cliente) | Squad | 200 |
| `notificacoes` | Notificações enviadas ao cliente | Bulbe | várias |
| `atendimentos` | Chamados de atendimento | Bulbe | ~40 |
| `chat_historico` | Auditoria das conversas com o chatbot | Painel | começa vazia |

As datas do seed são relativas a `date.today()`: o banco sempre "parece atual". Com a mesma semente, no mesmo dia,
o conteúdo é igual (só o *salt* dos hashes muda).

## Diagrama entidade-relacionamento

```plantuml
@startuml der-banco-ficticio
hide circle
skinparam linetype ortho

entity funcionarios { *id : int }
entity chat_historico { *id : int\n--\nfuncionario_id : int <<FK>> }
entity usinas { *id : int }
entity clientes { *id : uuid\n--\nusina_id : int <<FK>> }
entity adesoes { *id : uuid\n--\ncliente_id : uuid <<FK, null>> }
entity ativacoes { *cliente_id : uuid <<PK, FK>> }
entity ativacao_eventos { *id : int\n--\ncliente_id : uuid <<FK>> }
entity faturas { *id : int\n--\ncliente_id : uuid <<FK>> }
entity indicacoes { *id : uuid\n--\ncliente_id : uuid <<FK>> }
entity parceiros { *id : uuid }
entity clube_status { *cliente_id : uuid <<PK, FK>> }
entity cartas { *id : uuid\n--\ncliente_id : uuid <<FK>>\ncupom_id : uuid <<FK, null>> }
entity cupons { *id : uuid\n--\ncliente_id : uuid <<FK>>\ncarta_id : uuid <<FK>>\nparceiro_id : uuid <<FK>> }
entity dicas { *id : int }
entity simulacoes { *id : int\n--\ncliente_id : uuid <<FK, null>> }
entity notificacoes { *id : int\n--\ncliente_id : uuid <<FK>> }
entity atendimentos { *id : int\n--\ncliente_id : uuid <<FK>> }

funcionarios ||--o{ chat_historico
usinas ||--o{ clientes
clientes |o--o{ adesoes
clientes ||--o| ativacoes
clientes ||--o{ ativacao_eventos
clientes ||--o{ faturas
clientes ||--o{ indicacoes
clientes ||--o| clube_status
clientes ||--o{ cartas
clientes ||--o{ cupons
cartas |o--o| cupons
parceiros ||--o{ cupons
clientes |o--o{ simulacoes
clientes ||--o{ notificacoes
clientes ||--o{ atendimentos
@enduml
```

## Tabelas e campos

### `funcionarios` — origem: painel
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `nome` | texto | Nome do funcionário (fictício) |
| `email` | texto, único | Login do painel (`admin@bulbe.com.br`, `atendimento@bulbe.com.br`, `ana.souza@bulbe.com.br`) |
| `senha_hash` | texto | Hash PBKDF2 no formato `pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>` (nunca a senha) |
| `perfil` | texto | `atendimento` ou `admin` |
| `ativo` | bool | Funcionário inativo não consegue logar |
| `criado_em` | datetime | Criação do registro |

### `usinas` — origem: Bulbe
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador (mesmo modelo de `app/domain/usina.py`) |
| `nome` | texto | Nome da fazenda solar |
| `localizacao` | texto | Cidade e UF, ex.: `Uberlândia, MG` |
| `capacidade_geracao_kwh` | float | Capacidade de geração em kWh |
| `status` | texto | `ativa`, `em_manutencao` ou `inativa` |
| `data_ativacao` | date | Início da operação |

### `clientes` — origem: Bulbe
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `nome` | texto | Nome completo (fictício) |
| `email` | texto | E-mail |
| `cpf` | texto (11 dígitos), único | CPF fictício, só dígitos (dígitos verificadores válidos, sorteados) |
| `telefone` | texto (até 11 dígitos) | Telefone com DDD, só dígitos |
| `tipo` | texto | `residencia` ou `empresa` |
| `cep`, `logradouro`, `numero`, `complemento` (null), `bairro`, `cidade`, `uf` | texto | Endereço da unidade consumidora (MG); CEP com 8 dígitos |
| `distribuidora` | texto | `CEMIG` |
| `numero_instalacao` | texto, único | Número da instalação na CEMIG |
| `usina_id` | int (FK → `usinas.id`), null | Usina que gera os créditos do cliente |
| `status` | texto | `ativo`, `em_ativacao` (padrão) ou `cancelado` |
| `codigo_indicacao` | texto, único | Código do Indique e Ganhe, ex.: `MARCOS50` |
| `app_acesso_habilitado` | bool | Já fez o primeiro acesso ao app (CPF + código) — squad |
| `ultimo_login_app` | datetime, null | Último login no app (engajamento, D-04) — squad |
| `criado_em`, `atualizado_em` | datetime | Auditoria do registro |

### `adesoes` — origem: squad (adesão pelo app) + Bulbe (site/WhatsApp)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `nome`, `email` | texto | Dados de quem pediu a adesão |
| `cpf`, `telefone` | texto, null | Só dígitos (podem faltar num rascunho) |
| `cidade`, `uf` | texto, null | Local da unidade consumidora |
| `distribuidora` | texto, null | `CEMIG` |
| `numero_instalacao` | texto, null | Instalação informada |
| `valor_conta_atual` | float, null | Valor médio da conta informado |
| `economia_mensal_estimada` | float, null | 15% do valor da conta |
| `situacao` | texto | `rascunho` (padrão), `enviada`, `aprovada` ou `recusada` |
| `origem` | texto | `app`, `site` ou `whatsapp` |
| `cliente_id` | uuid (FK → `clientes.id`), null | Preenchido quando a adesão é aprovada |
| `criado_em` | datetime | Data do pedido |

### `ativacoes` — origem: squad (jornada de 5 etapas, D-03)
| Campo | Tipo | Descrição |
|---|---|---|
| `cliente_id` | uuid (PK, FK → `clientes.id`) | Um registro por cliente |
| `etapa_atual` | int (1–5) | 1 Cadastro, 2 Documentos, 3 Solicitação à CEMIG, 4 Análise CEMIG, 5 Energia liberada |
| `previsao_conclusao` | date | Data limite (cadastro + até 90 dias) |
| `atualizado_em` | datetime | Última mudança de etapa |

Percentual exibido: etapa 1 → 15%, 2 → 30%, 3 → 45%, 4 → 70%, 5 → 90%; 100% quando o cliente fica `ativo`.

### `ativacao_eventos` — origem: squad
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `cliente_id` | uuid (FK) | Cliente |
| `etapa` | int (1–5) | Etapa atingida |
| `observacao` | texto | Comentário operacional |
| `ocorrido_em` | datetime | Quando aconteceu |

### `faturas` — origem: Bulbe (2ª via e histórico de pagamentos)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `cliente_id` | uuid (FK) | Cliente |
| `mes_referencia` | texto `AAAA-MM` | Mês de consumo (único por cliente) |
| `consumo_kwh` | float | Consumo do mês |
| `valor_sem_bulbe` | float | Quanto pagaria sem a Bulbe |
| `desconto` | float | Desconto Bulbe: 15% de `valor_sem_bulbe` (no banco fictício, `valor_sem_bulbe` já representa a parcela sobre a qual o desconto incide) |
| `bonus_indicacao` | float | Bônus de indicação aplicado na fatura |
| `valor_total` | float | Valor cobrado |
| `vencimento` | date | Data de vencimento |
| `situacao` | texto | `paga`, `em_aberto` ou `vencida` |
| `pago_em` | date, null | Data do pagamento |

### `indicacoes` — origem: Bulbe (Indique e Ganhe)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `cliente_id` | uuid (FK) | Quem indicou |
| `nome_indicado` | texto | Nome do indicado (fictício) |
| `contato_indicado` | texto | Telefone ou e-mail do indicado |
| `canal` | texto | `whatsapp`, `link` ou `email` |
| `situacao` | texto | `pendente`, `aderiu` ou `expirada` |
| `bonus` | float | 50.00 |
| `creditado_em` | date, null | Quando o bônus entrou na fatura (quem indicou e o indicado recebem R$ 50 na primeira fatura a partir da adesão) |
| `criado_em` | datetime | Data da indicação |

### `parceiros` — origem: squad (Clube Bulbe)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `nome` | texto, único | Ex.: Drogaria Araújo, Banco Inter, Livelo; no seed há também duas marcas inventadas |
| `categoria` | texto | Ex.: farmácia, banco, pontos |
| `logo_url` | texto, null | Caminho da logo |
| `ativo` | bool | Aparece na vitrine |
| `criado_em` | datetime | Cadastro |

### `clube_status` — origem: squad
| Campo | Tipo | Descrição |
|---|---|---|
| `cliente_id` | uuid (PK, FK) | Cliente |
| `semanas_sequencia` | int (0–5) | Semanas seguidas abrindo a carta |
| `meta_sequencia` | int | 5 |
| `proxima_carta_em` | datetime, null | Próxima carta (a cada 7 dias) |
| `bonus_especial_pendente` | bool | Completou 5 semanas e ainda não abriu o bônus de R$ 50 |
| `atualizado_em` | datetime | Última atualização |

### `cartas` — origem: squad
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `cliente_id` | uuid (FK) | Cliente |
| `semana` | int | Número da semana (única por cliente) |
| `tipo` | texto | `normal` ou `especial` |
| `situacao` | texto | `disponivel`, `aberta` ou `expirada` |
| `disponivel_em` | datetime | Liberação |
| `aberta_em` | datetime, null | Abertura |
| `cupom_id` | uuid (FK → `cupons.id`), null | Cupom gerado |

### `cupons` — origem: squad (a Bulbe só tem "promoções" genéricas)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Identificador |
| `cliente_id` | uuid (FK) | Cliente |
| `carta_id` | uuid (FK), null | Carta de origem |
| `parceiro_id` | uuid (FK), null | Parceiro |
| `titulo`, `descricao` | texto | Ex.: "15% de desconto na Araújo" |
| `codigo` | texto, null | `BULBE15`, `INTERCASH`, `BULBEDUO`, `BULBELIV500`, `BULBE10` |
| `situacao` | texto | `ativo`, `salvo`, `usado`, `expirado` ou `descartado` |
| `aberto_em` | datetime | Geração |
| `valido_ate` | date | 14 dias após a abertura |
| `usado_em` | datetime, null | Uso |

### `dicas` — origem: squad
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `titulo` | texto | Troque por LED, Banhos rápidos, Cestos cheios, Cômodos em uso |
| `descricao` | texto | Texto da dica |
| `economia_mensal` | float | Ex.: 12.00 |
| `economia_anual` | float | Ex.: 144.00 |
| `ordem` | int | Ordem no carrossel |

### `simulacoes` — origem: squad (simulador sem login / modo visitante)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `origem` | texto | `visitante` ou `cliente` |
| `cliente_id` | uuid (FK), null | Preenchido se a simulação foi feita logado |
| `valor_conta` | float | Valor da conta informado |
| `meses` | int | Período simulado |
| `amigos_indicados` | int | Amigos no simulador (R$ 50 cada) |
| `economia_total` | float | Resultado |
| `criado_em` | datetime | Data |

### `notificacoes` — origem: Bulbe
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `cliente_id` | uuid (FK) | Destinatário |
| `tipo` | texto | `vencimento`, `ativacao`, `clube`, `indicacao` ou `promocao` |
| `titulo`, `mensagem` | texto | Conteúdo |
| `canal` | texto | `app`, `whatsapp` ou `email` |
| `enviada_em` | datetime | Envio |
| `lida` | bool | Lida pelo cliente |

### `atendimentos` — origem: Bulbe
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `cliente_id` | uuid (FK) | Cliente |
| `canal` | texto | `whatsapp`, `email`, `app` ou `ouvidoria` |
| `assunto`, `descricao` | texto | Motivo do contato |
| `status` | texto | `aberto`, `em_andamento` ou `resolvido` |
| `criado_em` | datetime | Abertura |
| `resolvido_em` | datetime, null | Encerramento |

### `chat_historico` — origem: painel (auditoria / LGPD)
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | Identificador |
| `funcionario_id` | int (FK → `funcionarios.id`) | Quem perguntou |
| `pergunta` | texto | Mensagem do funcionário |
| `resposta` | texto | Resposta do chatbot |
| `ferramentas_usadas` | texto (JSON), padrão `[]` | Lista de ferramentas chamadas, ex.: `["buscar_clientes","obter_ativacao"]` |
| `criado_em` | datetime | Data da troca |

## Personagens fixos do seed

| Personagem | Situação no seed | Por quê |
|---|---|---|
| Marcos Andrade | Cliente `em_ativacao`, etapa 2 (Documentos), código `MARCOS50`, duas indicações pendentes (uma delas para Renato Souza), ainda sem faturas | É o cliente das telas do front (status 30%, "Parabéns, Marcos!") e do exemplo da `Lista_de_endpoints.md` |
| Clara Ribeiro | Adesão `enviada` pelo app, conta de R$ 320,00, ainda não é cliente | Persona "Clara" (adesão rápida pelo app) |

Todos são **fictícios**, assim como todos os CPFs (11 dígitos com verificadores válidos, sorteados, sem correspondência real).

## Campos calculados devolvidos pelas consultas

Além das colunas, `app/database/consultas.py` devolve alguns campos derivados (úteis no painel e no chatbot):

| Consulta | Campos derivados |
|---|---|
| `buscar_clientes` | `etapa_ativacao` (int ou null) |
| `obter_ativacao` | `total_etapas` (5), `nome_etapa`, `titulo`, `descricao`, `percentual_concluido`, `prazo_ativacao_dias` (90), `dias_desde_cadastro`, `etapas[]` (`concluida`/`atual`/`pendente`), `eventos[]` |
| `resumo_economia_cliente` | `meses_faturados`, `economia_total_desconto`, `bonus_indicacao_total`, `economia_total`, `faturas_vencidas`, `valor_em_aberto` (devolve null se o cliente não existe) |
| `listar_indicacoes` | `bonus_por_indicacao` (50.0), `bonus_acumulado`, `total` (null se o cliente não existe) |
| `listar_faturas` | inclui `cliente_id` |
| `listar_faturas_vencidas` | `fatura_id`, `cliente_id`, `cliente_nome`, `mes_referencia`, `valor_total`, `vencimento`, `dias_em_atraso` |
| `listar_atendimentos` | inclui `cliente_nome` |
| `listar_usinas` | inclui `clientes_ativos` |
| `metricas_gerais` | `ativacao_por_etapa` conta só clientes `em_ativacao` (etapas 1–4; a chave `"5"` costuma valer 0); `clube.cupons_ativos` conta só a situação `ativo` |
| `simular_economia` | `percentual_desconto`, `desconto_mensal`, `desconto_periodo`, `bonus_indicacoes`, `economia_total`, `nova_conta_mensal`, `comparativo{}`, `observacao` (não grava em `simulacoes`) |
