# `app/database/` — Banco de dados fictício da Bulbe

Banco **SQLite** (SQLAlchemy 2) usado pelo **painel de gestão** e pelo **chatbot** dos funcionários.
Todos os dados são **100% fictícios**: nomes são combinações aleatórias, CPFs têm dígitos
verificadores válidos mas foram sorteados, e telefones, instalações e protocolos também são inventados.

| Arquivo | Papel |
|---|---|
| `conexao.py` | `Base`, `engine`, `SessionLocal`, `obter_sessao()`, `inicializar_banco(recriar=False)` |
| `seguranca.py` | `gerar_hash_senha()` / `verificar_senha()`: PBKDF2-SHA256, só com a biblioteca padrão |
| `modelos.py` | As 17 tabelas (ORM), com relacionamentos e constraints (CHECK, UNIQUE e FK) |
| `seed.py` | `popular_banco(sessao, semente=42)`: dados fictícios, determinísticos e coerentes entre as tabelas |
| `consultas.py` | Funções **somente leitura** que devolvem `dict`/`list` JSON-serializáveis. A única escrita é `registrar_chat` |

## Como criar / recriar o banco

```bash
# a partir da raiz do repositório, com as dependências instaladas
python -m app.database.seed          # APAGA e recria app/database/bulbe_ficticio.db
```

- Na subida da API, `inicializar_banco()` cria as tabelas que faltam e roda o seed **só se o banco estiver totalmente vazio** (`clientes`, `funcionarios`, `usinas` e `parceiros` sem linhas). Num estado parcial, o seed não roda e aparece um aviso no log para recriar o banco.
- O caminho padrão é absoluto (`Path(__file__).parent / "bulbe_ficticio.db"`). Para usar outro banco, defina `BULBE_DB_URL`.
- A senha dos funcionários vem de `PAINEL_SENHA_DEMO` (padrão `bulbe@demo123`).
  Os logins são `admin@bulbe.com.br` (admin), `atendimento@bulbe.com.br` e `ana.souza@bulbe.com.br` (atendimento).
- O arquivo `.db` **não** vai para o git (o líder cuida do `.gitignore`).
- As datas são relativas ao dia atual em UTC (`agora_utc().date()`, a mesma fonte usada nas consultas), então o banco sempre "parece atual". Com a mesma semente e no mesmo dia, o conteúdo sai igual (só o salt dos hashes muda).
- Nenhuma notificação, atendimento ou `ultimo_login_app` fica antes do `criado_em` do cliente.

## Modelo de dados

A coluna **Origem** indica se a funcionalidade **já existe no app/site da Bulbe** ou se foi **criada pela squad Cleanergy**.

| Tabela | Chave | Principais campos | Origem |
|---|---|---|---|
| `funcionarios` | int | nome, email (único), senha_hash, perfil (`atendimento`/`admin`), ativo | Painel (novo) |
| `chat_historico` | int | funcionario_id → funcionarios, pergunta, resposta, ferramentas_usadas (JSON) | Painel (auditoria/LGPD) |
| `usinas` | int | nome, localizacao, capacidade_geracao_kwh, status, data_ativacao | Bulbe |
| `clientes` | UUID | dados pessoais, endereço, numero_instalacao (único), usina_id, status, codigo_indicacao (único), acesso ao app | Bulbe |
| `faturas` | int | cliente_id, mes_referencia (único por cliente), consumo, valor_sem_bulbe, desconto, bonus_indicacao, valor_total, vencimento, situacao | Bulbe (2ª via / histórico) |
| `indicacoes` | UUID | cliente_id (quem indicou), nome/contato do indicado, canal, situacao, bonus (R$ 50), creditado_em | Bulbe (Indique e Ganhe) |
| `notificacoes` | int | cliente_id, tipo, titulo, mensagem, canal, enviada_em, lida | Bulbe |
| `atendimentos` | int | cliente_id, canal, assunto, descricao, status, criado_em, resolvido_em | Bulbe |
| `adesoes` | UUID | dados do interessado, valor da conta, economia estimada, situacao, origem, cliente_id (após aprovação) | Squad (app) + Bulbe (site) |
| `ativacoes` | cliente_id | etapa_atual (1–5), previsao_conclusao (cadastro + 90 dias) | Squad (jornada de 5 etapas) |
| `ativacao_eventos` | int | cliente_id, etapa, observacao (ex.: "Protocolo 2026-CEMIG-88214 aberto."), ocorrido_em | Squad |
| `parceiros` | UUID | nome (único), categoria, logo_url, ativo | Squad (Clube Bulbe) |
| `clube_status` | cliente_id | semanas_sequencia (0–5), meta_sequencia (5), proxima_carta_em, bonus_especial_pendente | Squad |
| `cartas` | UUID | cliente_id, semana, tipo (`normal`/`especial`), situacao, disponivel_em, aberta_em, cupom_id | Squad |
| `cupons` | UUID | cliente_id, carta_id, parceiro_id, titulo, codigo, situacao, aberto_em, valido_ate (+14 dias), usado_em | Squad (a Bulbe tem só "promoções" genéricas) |
| `dicas` | int | titulo, descricao, economia_mensal, economia_anual, ordem | Squad |
| `simulacoes` | int | origem (`visitante`/`cliente`), cliente_id, valor_conta, meses, amigos_indicados, economia_total | Squad (simulador sem login) |

Relacionamentos principais: `clientes 1–N faturas / indicacoes / notificacoes / atendimentos / cartas / cupons / ativacao_eventos`,
`clientes 1–1 ativacoes / clube_status`, `usinas 1–N clientes`, `adesoes N–1 clientes` (opcional),
`cartas 1–1 cupons` (FK circular: `cartas.cupom_id` usa `use_alter` + `post_update`), `parceiros 1–N cupons`,
`funcionarios 1–N chat_historico`. No SQLite, as FKs são ligadas com `PRAGMA foreign_keys=ON`.

## O que o seed gera (semente 42)

- **3 funcionários**, **4 usinas** (1 em manutenção), **6 parceiros** (Araújo, Inter, Livelo, Bulbe e mais 2 marcas inventadas: *Café Serrano Mineiro* e *EcoBike BH*, esta inativa), as **4 dicas** do front.
- **64 clientes** em cidades de MG (a maioria em BH e na região metropolitana):
  - 40 `ativo`: etapa 5 concluída, até **12 faturas** (últimos 12 meses) com **15% de desconto** e bônus de indicação quando houver; 5 inadimplentes com faturas **vencidas**.
    As faturas começam no mês seguinte à liberação da energia, então **clientes com menos de 1 ano de conexão têm menos de 12 faturas** (cerca de 30% dos ativos).
  - 16 `em_ativacao`: etapas 1–4 e **nenhuma fatura**, com eventos coerentes com a etapa.
  - 8 `cancelado`: 5 cancelaram depois de ativos (faturas até o cancelamento) e 3 durante a ativação.
- **Personagens do front**: **Marcos Andrade** (`MARCOS50`, em ativação na etapa 2, indicou Renato Souza) e
  **Clara Ribeiro** (adesão `enviada` pelo app, R$ 320,00 de conta).
- **16 adesões** (8 aprovadas ligadas a clientes em ativação, 4 enviadas, 2 rascunhos, 2 recusadas).
- **Indicações**: as que deram certo apontam para clientes reais do banco. Quem indicou recebe R$ 50 na primeira fatura a partir do mês da adesão (`creditado_em`), e o indicado também recebe R$ 50. Há ainda indicações pendentes e expiradas.
- **Clube Bulbe**: só para clientes com acesso ao app que não cancelaram. Recebem 1 carta a cada 7 dias, cada carta aberta gera um cupom de uma das 5 recompensas (`BULBE15`, `INTERCASH`, `BULBEDUO`, `BULBELIV500`, `BULBE10`) válido por 14 dias.
  Quem completa 5 semanas seguidas recebe uma carta **especial**:
  - se ela saiu nos últimos 7 dias, fica `disponivel` e o bônus fica pendente;
  - se é mais antiga, foi aberta (gerando o cupom `usado` "R$ 50 de desconto na fatura", do parceiro Bulbe Energia) ou expirou, e a sequência recomeça.

  `proxima_carta_em` sempre fica no futuro, e a carta da semana, quando existe, foi liberada nos últimos 7 dias.
- **Notificações** (vencimento, ativação, clube, indicação, promoção), cerca de 40 **atendimentos** e **200 simulações**.
- `chat_historico` começa vazio e só é preenchido em tempo de execução por `registrar_chat`.

## Consultas (`consultas.py`)

Todas seguem a seção 1.6 de `docs/CONTRATOS.md`. Além delas, há:
- `listar_faturas_vencidas(limite=20)`, pedida pelo líder: lista as faturas `vencida` de todos os clientes, da mais antiga para a mais recente, com `dias_em_atraso`.
- `listar_atendimentos(...)`: cada item traz também `cliente_nome`.
- `listar_usinas()`: cada item traz também `clientes_ativos`.
