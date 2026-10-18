# `app/database/` — Banco de dados fictício da Bulbe

Banco **SQLite** (SQLAlchemy 2) usado pelo **painel de gestão** e pelo **chatbot** dos funcionários.
Todos os dados são **100% fictícios**: nomes são combinações aleatórias, CPFs têm dígitos
verificadores válidos mas foram sorteados, e telefones, instalações, protocolos e IPs também são inventados.

| Arquivo | Papel |
|---|---|
| `conexao.py` | `Base`, `engine`, `SessionLocal`, `obter_sessao()`, `inicializar_banco(recriar=False)` |
| `seguranca.py` | `gerar_hash_senha()` / `verificar_senha()`: PBKDF2-SHA256, só com a biblioteca padrão |
| `modelos.py` | As 20 tabelas (ORM), com relacionamentos e constraints (CHECK, UNIQUE e FK) |
| `seed.py` | `popular_banco(sessao, semente=42)`: dados fictícios, determinísticos e coerentes entre as tabelas |
| `consultas.py` | Consultas que devolvem `dict`/`list` JSON-serializáveis, mais as escritas do chat, da auditoria e da retenção |

## Como criar / recriar o banco

```bash
# a partir da raiz do repositório, com as dependências instaladas
python -m app.database.seed          # APAGA e recria app/database/bulbe_ficticio.db
```

- Na subida da API, `inicializar_banco()` cria as tabelas que faltam e roda o seed **só se o banco estiver totalmente vazio** (`clientes`, `funcionarios`, `usinas` e `parceiros` sem linhas). Num estado parcial, o seed não roda e aparece um aviso no log para recriar o banco.
- **Banco da v1**: a v2 tem tabelas e colunas novas e o caminho recomendado é recriar o banco (`python -m app.database.seed`). Como rede de segurança, `inicializar_banco()` cria as tabelas novas e adiciona as colunas que faltarem nas tabelas antigas (`ALTER TABLE ... ADD COLUMN`, com o default do modelo e um aviso no log), para a API não quebrar antes da recriação. As faturas antigas ficam com `bonus_clube = 0`.
- O caminho padrão é absoluto (`Path(__file__).parent / "bulbe_ficticio.db"`). Para usar outro banco (ex.: testes), defina `BULBE_DB_URL`.
- A senha dos funcionários vem de `PAINEL_SENHA_DEMO` (padrão `bulbe@demo123`).
  Os logins são `admin@bulbe.com.br` (admin), `atendimento@bulbe.com.br` e `ana.souza@bulbe.com.br` (atendimento).
- O arquivo `.db` **não** vai para o git (está no `.gitignore`).
- As datas são relativas ao dia atual em UTC (`agora_utc().date()`, a mesma fonte usada nas consultas), então o banco sempre "parece atual". Com a mesma semente e no mesmo dia, o conteúdo sai igual (só o salt dos hashes muda).
- Nenhuma notificação, atendimento ou `ultimo_login_app` fica antes do `criado_em` do cliente.

## Modelo de dados

A coluna **Origem** indica se a funcionalidade **já existe no app/site da Bulbe** ou se foi **criada pela squad Cleanergy**.

| Tabela | Chave | Principais campos | Origem |
|---|---|---|---|
| `funcionarios` | int | nome, email (único), senha_hash, perfil (`atendimento`/`admin`), ativo | Painel (novo) |
| `chat_historico` | int | funcionario_id → funcionarios, pergunta, resposta, ferramentas_usadas (JSON), criado_em; **v2:** conversa_id → chat_conversas (nulo), modelo, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens (int, default 0), custo_estimado_usd (float, default 0), duracao_ms (nulo) | Painel (auditoria/LGPD e uso/custo) |
| `chat_conversas` (**v2**) | UUID | funcionario_id → funcionarios, titulo (até 120 caracteres), criado_em, atualizado_em | Painel (histórico do chat no servidor) |
| `chat_mensagens` (**v2**) | int | conversa_id → chat_conversas, ordem (única por conversa), papel (`user`/`assistant`), conteudo_json (conteúdo **exato** enviado/recebido da API), texto (o que a interface mostra, pode ser vazio), criado_em | Painel |
| `auditoria_acessos` (**v2**) | int | funcionario_id → funcionarios (nulo em login falho de e-mail inexistente), email_informado, acao (`login_ok`/`login_falha`/`login_bloqueado`/`alerta_email`/`ver_ficha`/`ver_auditoria`/`expurgo`), recurso_tipo, recurso_id, ip, detalhe (até 500 caracteres), criado_em | Painel (segurança/LGPD) |
| `usinas` | int | nome, localizacao, capacidade_geracao_kwh, status, data_ativacao | Bulbe |
| `clientes` | UUID | dados pessoais, endereço, numero_instalacao (único), usina_id, status, codigo_indicacao (único), acesso ao app | Bulbe |
| `faturas` | int | cliente_id, mes_referencia (único por cliente), consumo, valor_sem_bulbe, desconto, bonus_indicacao, **bonus_clube (v2, default 0)**, valor_total, vencimento, situacao | Bulbe (2ª via / histórico) |
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
`funcionarios 1–N chat_historico / chat_conversas / auditoria_acessos`, `chat_conversas 1–N chat_mensagens` (`ON DELETE CASCADE`),
`chat_conversas 1–N chat_historico` (opcional, `ON DELETE SET NULL`). No SQLite, as FKs são ligadas com `PRAGMA foreign_keys=ON`.

Regras das tabelas novas:
- **Histórico só de acréscimo**: `adicionar_mensagens` sempre grava depois da última `ordem` e nunca altera mensagens antigas. `conteudo_json = json.dumps(conteudo, ensure_ascii=False)` e `obter_conversa` devolve `json.loads` disso, idêntico ao gravado (inclusive blocos `thinking`/`tool_use`).
- **Faturas**: `valor_total = valor_sem_bulbe − desconto − bonus_indicacao − bonus_clube`, nunca negativo.
- Todos os instantes gravados (conversas, mensagens, chat, auditoria) vêm de `agora_utc()`.

## O que o seed gera (semente 42)

- **3 funcionários**, **4 usinas** (1 em manutenção), **6 parceiros** (Araújo, Inter, Livelo, Bulbe e mais 2 marcas inventadas: *Café Serrano Mineiro* e *EcoBike BH*, esta inativa), as **4 dicas** do front.
- **64 clientes** em cidades de MG (a maioria em BH e na região metropolitana):
  - 40 `ativo`: etapa 5 concluída, até **12 faturas** (últimos 12 meses) com **15% de desconto**, bônus de indicação e bônus do Clube quando houver; 5 inadimplentes com faturas **vencidas**.
    As faturas começam no mês seguinte à liberação da energia, então **clientes com menos de 1 ano de conexão têm menos de 12 faturas**.
    **3 deles tiveram a energia liberada nos últimos 30 dias** (alimentam a etapa 5 do funil, "ativados nos últimos 30 dias") e ainda não têm fatura.
  - 16 `em_ativacao`: etapas 1–4 e **nenhuma fatura**, com eventos coerentes com a etapa. Um deles já passou do prazo de 90 dias (aparece como `atrasado`).
  - 8 `cancelado`: 5 cancelaram depois de ativos (faturas até o cancelamento) e 3 durante a ativação.
- **Personagens do front**: **Marcos Andrade** (`MARCOS50`, em ativação na etapa 2, indicou Renato Souza) e
  **Clara Ribeiro** (adesão `enviada` pelo app, R$ 320,00 de conta).
- **16 adesões** (8 aprovadas ligadas a clientes em ativação, 4 enviadas, 2 rascunhos, 2 recusadas).
- **Indicações**: as que deram certo apontam para clientes reais do banco. Quem indicou recebe R$ 50 na primeira fatura a partir do mês da adesão (`creditado_em`), e o indicado também recebe R$ 50. Há ainda indicações pendentes e expiradas.
- **Clube Bulbe**: só para clientes com acesso ao app que não cancelaram. Recebem 1 carta a cada 7 dias, cada carta aberta gera um cupom de uma das 5 recompensas (`BULBE15`, `INTERCASH`, `BULBEDUO`, `BULBELIV500`, `BULBE10`) válido por 14 dias.
  Quem completa 5 semanas seguidas recebe uma carta **especial**:
  - se ela saiu nos últimos 7 dias, fica `disponivel` e o bônus fica pendente;
  - se é mais antiga, foi aberta (gerando o cupom `usado` "R$ 50 de desconto na fatura", do parceiro Bulbe Energia) ou expirou, e a sequência recomeça.
  - **v2**: a carta especial aberta vira **R$ 50 em `faturas.bonus_clube` na primeira fatura emitida depois da abertura** (a fatura de `AAAA-MM` é emitida no dia 1 do mês seguinte), descontados do `valor_total` sem deixá-lo negativo. Se essa fatura ainda não foi emitida (ou o cliente ainda está em ativação), o bônus fica para depois e não aparece no banco.

  `proxima_carta_em` sempre fica no futuro, e a carta da semana, quando existe, foi liberada nos últimos 7 dias.
- **Notificações** (vencimento, ativação, clube, indicação, promoção), cerca de 40 **atendimentos** e **200 simulações**.
- **Auditoria (v2)**: cerca de **125 registros** em `auditoria_acessos` nos últimos 90 dias, todos com pelo menos 2 dias (não interferem na janela de bloqueio de login):
  logins `login_ok` dos 3 funcionários, cada um seguido de 0 a 2 `ver_ficha` (recurso `cliente`, de clientes que já existiam no momento);
  erros de digitação (`login_falha` seguido de `login_ok`); `login_falha` de e-mails inexistentes (`funcionario_id` nulo);
  `ver_auditoria` do admin; uma rajada de senhas erradas contra o admin vinda de um IP externo (4ª falha → `alerta_email`, depois da 5ª → 2 × `login_bloqueado`);
  e um `expurgo` rodado pelo admin. IPs fictícios: rede interna `10.20.x.x` e faixas reservadas para documentação (RFC 5737: `192.0.2.x`, `198.51.100.x`, `203.0.113.x`).
- `chat_historico`, `chat_conversas` e `chat_mensagens` começam **vazios** (o chat começa do zero) e só são preenchidos em tempo de execução.

## Consultas (`consultas.py`)

Seguem a seção 1.6 de `docs/CONTRATOS.md` e a seção 1.2 de `docs/CONTRATOS-MELHORIAS.md`. Regras gerais:
- Só tipos JSON-serializáveis; datas em ISO (`AAAA-MM-DD`) e instantes em `AAAA-MM-DDTHH:MM:SSZ` (UTC).
- Consultas nunca levantam exceção para "não encontrado" ou filtro inválido: devolvem `None`, lista vazia ou página vazia.
- **Formato paginado**: `{"data", "pagina", "por_pagina", "total", "total_paginas"}`. `pagina < 1` vira 1, `por_pagina` fica entre 1 e 100 e `total_paginas` é sempre ≥ 1 (página além do fim devolve `data` vazio).

Além do contrato v1, há:
- `listar_faturas_vencidas(limite=20)`: lista as faturas `vencida` de todos os clientes, da mais antiga para a mais recente, com `dias_em_atraso` (e `bonus_clube` na v2).
- `listar_atendimentos(...)`: cada item traz também `cliente_nome`.
- `listar_usinas()`: cada item traz também `clientes_ativos`.

Novidades e mudanças da v2:

| Função | Observações |
|---|---|
| `buscar_clientes(..., etapa=None)` | filtro opcional pela `etapa_atual` da ativação (1–5, qualquer status); etapa inválida → `[]` |
| `buscar_clientes_paginado(termo, status, cidade, etapa, pagina, por_pagina)` | mesma busca, paginada |
| `listar_clientes_parados(etapa, dias_minimos=30, limite=50)` | clientes `em_ativacao` cujo último movimento da ativação (o mais recente entre o último evento e `ativacoes.atualizado_em`) tem `dias_minimos` dias ou mais; do mais parado ao menos parado. `atrasado` = mais de 90 dias desde o cadastro |
| `resumo_ativacoes()` | `por_etapa` e `dias_medios_na_etapa` (chaves `"1"`–`"4"`, média 0.0 quando a etapa está vazia), `atrasados_90_dias`, `ativados_30_dias` e `tempo_medio_ativacao_dias` (cadastro → primeiro evento da etapa 5; `None` se ninguém foi ativado) |
| `metricas_gerais()` | `ativacao_por_etapa["5"]` = clientes com energia liberada nos últimos 30 dias (qualquer status atual); `ativacao_etapa5_descricao`; `clube.bonus_pagos`. `economia_total_gerada` passa a somar também o `bonus_clube` |
| `listar_adesoes_paginado`, `listar_atendimentos_paginado` | versões paginadas (mais recentes primeiro) |
| `listar_faturas`, `listar_faturas_vencidas`, `resumo_economia_cliente` | `bonus_clube` em cada fatura; `bonus_clube_total` no resumo (somado em `economia_total`) |
| `criar_conversa`, `listar_conversas`, `obter_conversa`, `adicionar_mensagens` | conversas no servidor. `obter_conversa` devolve `None` se a conversa não existe ou é de outro funcionário. Título vazio vira "Nova conversa"; título longo é cortado em 120 caracteres. `adicionar_mensagens` e `criar_conversa` levantam `ValueError` para papel inválido, item sem `conteudo`, conversa ou funcionário inexistente (nada é gravado) |
| `registrar_chat(..., *, conversa_id, modelo, uso, duracao_ms)` | parâmetros novos só por nome; valores de `uso` ausentes ou inválidos viram 0; `conversa_id` inexistente é gravado como nulo (com aviso no log) |
| `metricas_uso_chatbot(dias=30)` | período = últimos `dias` dias de calendário, hoje incluso (1 a 3650). `por_dia` traz todos os dias do período, mesmo os sem uso. Também devolve `cache_creation_tokens`. `duracao_media_ms` considera só as trocas com duração (0 se nenhuma). `conversas` = conversas distintas citadas no `chat_historico` do período |
| `registrar_auditoria(acao, *, ...)` | ação fora da lista → `ValueError`; textos cortados no tamanho da coluna |
| `listar_auditoria(funcionario_id, acao, pagina, por_pagina=50)` | paginada, mais recentes primeiro, com `funcionario_nome` (nulo se não houver funcionário) |
| `contar_falhas_login(email, minutos=15)` | `login_falha` recentes do e-mail, sem diferenciar maiúsculas; casa por `email_informado` ou pelo funcionário dono do e-mail |
| `expurgar_dados_antigos(dias_chat=180, dias_auditoria=730)` | apaga `chat_historico` (por `criado_em`), conversas pela `atualizado_em` (com as mensagens) e auditoria antiga. Trocas recentes que apontavam para uma conversa expurgada ficam com `conversa_id` nulo |
