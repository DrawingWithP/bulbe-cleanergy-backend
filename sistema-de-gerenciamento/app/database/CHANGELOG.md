# CHANGELOG — `app/database/` (agente `db`)

## Melhorias (v2) — branch `feat/python-melhorias-sistema`

Implementa a seção 1 de `docs/CONTRATOS-MELHORIAS.md`. Tudo o que existia continua com a mesma assinatura e o mesmo formato; as mudanças são campos e parâmetros opcionais a mais.

### Esquema (`modelos.py`)
- `faturas.bonus_clube` (float, default 0), incluído na CHECK de valores não negativos.
- `chat_historico`: `conversa_id` (FK `chat_conversas`, nula, `ON DELETE SET NULL`), `modelo`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` (int, default 0), `custo_estimado_usd` (float, default 0) e `duracao_ms` (nula).
- Tabelas novas: `chat_conversas` (UUID), `chat_mensagens` (`UNIQUE(conversa_id, ordem)`, CHECK de `papel`, `ON DELETE CASCADE`) e `auditoria_acessos` (CHECK de `acao`, FK de funcionário nula). Agora são 20 tabelas.
- Novas tuplas reutilizáveis: `PAPEIS_CHAT`, `ACOES_AUDITORIA` e os tamanhos `TAMANHO_TITULO_CONVERSA` (120) e `TAMANHO_DETALHE_AUDITORIA` (500).

### Conexão (`conexao.py`)
- `inicializar_banco()` adiciona as colunas que faltarem num banco criado pela v1 (`ALTER TABLE ... ADD COLUMN` com o default do modelo, e um aviso no log). Isso evita erro 500 se a API subir antes de o banco ser recriado. O caminho recomendado continua sendo `python -m app.database.seed`.

### Seed (`seed.py`)
- **Bônus do Clube nas faturas**: a carta especial aberta gera R$ 50 em `bonus_clube` na primeira fatura emitida depois da abertura, e o `valor_total` desconta o bônus sem ficar negativo. Para isso, o Clube passou a ser gerado antes das faturas. A notificação "Fatura disponível" soma o bônus na economia.
- **Ativados recentes**: 3 dos 40 clientes ativos tiveram a energia liberada nos últimos 30 dias. Sem isso, a etapa 5 do funil ("ativados nos últimos 30 dias") ficaria sempre zerada. Os inadimplentes passaram a ser sorteados só entre quem tem a energia liberada há mais de 90 dias, para continuarem com faturas vencidas.
- **Ativação atrasada**: um dos clientes em ativação já passou do prazo de 90 dias, para o painel ter um caso `atrasado`.
- **Auditoria**: cerca de 125 registros plausíveis em `auditoria_acessos` nos últimos 90 dias, todos com pelo menos 2 dias de idade, para não interferirem na janela de bloqueio do login. Incluem logins, fichas vistas, erros de digitação, e-mails inexistentes, consultas do admin à auditoria, uma rajada contra o admin (com alerta e bloqueio) e um expurgo. Os IPs são fictícios (`10.20.x.x` e faixas de documentação da RFC 5737).
- O chat começa vazio: nenhuma conversa, mensagem ou histórico.
- Os totais continuam os mesmos (64 clientes: 40 ativos, 16 em ativação, 8 cancelados; 16 adesões; Marcos e Clara). Como a ordem dos sorteios mudou, os dados individuais de cada cliente não são mais os mesmos da v1.

### Consultas (`consultas.py`)
- Paginação padrão: `{data, pagina, por_pagina, total, total_paginas}`, com `pagina < 1` virando 1, `por_pagina` entre 1 e 100 e `total_paginas >= 1`.
- `buscar_clientes(..., etapa=None)` e `buscar_clientes_paginado(...)`. A busca foi extraída para um gerador comum, sem mudar o resultado da v1.
- `listar_clientes_parados(...)` e `resumo_ativacoes()`.
- `metricas_gerais()`:
  - `ativacao_por_etapa["5"]` passa a contar os clientes ativados nos últimos 30 dias.
  - Novas chaves `ativacao_etapa5_descricao` e `clube.bonus_pagos`.
  - `economia_total_gerada` passa a somar também o `bonus_clube`.
- `listar_adesoes_paginado(...)` e `listar_atendimentos_paginado(...)`. As listas não paginadas ganharam um desempate estável na ordenação.
- `bonus_clube` em `listar_faturas` e `listar_faturas_vencidas`. `bonus_clube_total` em `resumo_economia_cliente`, também somado em `economia_total`.
- Conversas do chat:
  - Novas funções `criar_conversa`, `listar_conversas`, `obter_conversa` e `adicionar_mensagens`.
  - O histórico é só de acréscimo.
  - `conteudo_json` é gravado com `json.dumps(..., ensure_ascii=False)`, e `obter_conversa` devolve o `json.loads` desse conteúdo, idêntico ao gravado.
- `registrar_chat(..., *, conversa_id, modelo, uso, duracao_ms)` e `metricas_uso_chatbot(dias=30)`.
- `registrar_auditoria`, `listar_auditoria`, `contar_falhas_login` e `expurgar_dados_antigos`.
- Todos os instantes gravados vêm de `agora_utc()`.
- Nova `obter_funcionario_por_email(email) -> dict | None`, a pedido da integração. A busca ignora maiúsculas e espaços nas pontas e devolve `{id, nome, email, perfil, ativo}`, inclusive de funcionários inativos, ou `None` se o e-mail não existir. O painel a usa para preencher o `funcionario_id` na auditoria de login falho.

### Validação
- Num SQLite temporário fora do repositório (`BULBE_DB_URL`), `inicializar_banco(recriar=True)` rodou sem erro.
- Todas as consultas, antigas e novas, foram chamadas e passaram em `json.dumps`, com conferência de:
  - assinaturas exatas e formato paginado;
  - coerência do `valor_total` das faturas;
  - preservação das mensagens antigas nas conversas e conteúdo devolvido idêntico ao gravado;
  - posse da conversa;
  - contagem de falhas sem diferenciar maiúsculas;
  - expurgo;
  - inclusão de coluna faltante num banco antigo.
- O banco real (`bulbe_ficticio.db`) não foi tocado.

Lacunas e suposições estão em `PENDENCIAS.md`.

## [Não lançado] — branch `feat/python-adiciona-chatbot`

### Adicionado
- `__init__.py`: docstring do pacote. Não importa nada, para não carregar o SQLAlchemy sem necessidade.
- `conexao.py`
  - `Base` (DeclarativeBase), `engine`, `SessionLocal` (`expire_on_commit=False`), `obter_sessao()` e `inicializar_banco(recriar=False)`.
  - O caminho padrão do SQLite é **absoluto**: `Path(__file__).parent / "bulbe_ficticio.db"`, montado com `URL.create` para não quebrar com espaços e acentos no caminho ("Área de Trabalho").
  - `BULBE_DB_URL` é opcional. Para SQLite usa `check_same_thread=False` e liga `PRAGMA foreign_keys=ON` em cada conexão.
  - `recriar=True` desliga as FKs só durante o `DROP` (por causa da FK circular entre cartas e cupons).
  - Carrega o `.env` com `python-dotenv`, se a biblioteca existir (é opcional).
- `seguranca.py`: `gerar_hash_senha` / `verificar_senha` (PBKDF2-HMAC-SHA256, 240.000 iterações, salt de 16 bytes, formato `pbkdf2_sha256$iter$salt$hash`, `hmac.compare_digest`). Um hash malformado devolve `False` em vez de levantar exceção.
- `modelos.py`: as **17 tabelas** no estilo `Mapped` / `mapped_column`, com relacionamentos, `CHECK` para todos os "enums" e faixas (etapa 1–5, sequência 0–5, meses 1–60, CPF com 11 dígitos), `UNIQUE` (e-mail do funcionário, CPF, instalação, código de indicação, fatura por cliente e mês, carta por cliente e semana) e índices. As tuplas de valores válidos (`STATUS_CLIENTE`, `SITUACOES_FATURA`...) ficam expostas para reuso.
- `seed.py`: `popular_banco(sessao, semente=42)`, determinístico (`random.Random`) e sem Faker, com datas relativas ao dia atual em UTC (`agora_utc().date()`). Roda com `python -m app.database.seed`, que recria o banco. As regras de coerência entre tabelas estão no `README.md`.
- `consultas.py`: todas as funções da seção 1.6, com os formatos do contrato. As datas saem em ISO (`AAAA-MM-DD` ou `AAAA-MM-DDTHH:MM:SSZ`) e nunca há objetos ORM no retorno.
  - A busca de clientes ignora maiúsculas **e acentos** ("joao" encontra "João"). O CPF e a instalação só são comparados por dígitos quando o termo parece um documento.
  - Em `autenticar_funcionario`, quando o e-mail não existe, a função gasta o mesmo tempo verificando um hash fictício, para não revelar quais e-mails existem.
- `README.md`: modelo de dados (tabela → origem Bulbe ou squad) e como recriar o banco.

### Pedidos do líder durante a tarefa
- **`listar_faturas_vencidas(limite: int = 20) -> list[dict]`**: faturas `vencida` de todos os clientes, da mais antiga para a mais recente (por vencimento). Item: `{fatura_id, cliente_id, cliente_nome, mes_referencia, valor_total, vencimento, dias_em_atraso}`.
- **`listar_atendimentos`**: cada item agora inclui `cliente_nome`, além de `cliente_id`, para a tela de Atendimentos do painel.

### Correções da revisão estática do líder
1. **Carta especial "travando" o Clube** (`seed.py`, `criar_clube`).
   - A carta especial só fica `disponivel` se foi liberada nos últimos 7 dias. Mais antiga que isso, ela foi `aberta` (75%, gerando o cupom `usado` "R$ 50 de desconto na fatura" do parceiro Bulbe Energia) ou `expirada`. Nos dois casos a sequência é zerada e o laço continua.
   - `proxima_carta_em` agora fica **sempre no futuro**: é a próxima carta semanal, ou a carta disponível + 7 dias.
   - A notificação "Carta especial liberada!" nunca sai antiga.
   - Novos auxiliares: `_abertura()` e `_cupom_especial()`.
2. **`obter_ativacao` para cliente `cancelado`** (`consultas.py`).
   - Título "Processo encerrado". A descrição é "O cliente cancelou a assinatura; a jornada de ativação foi interrompida.", ou uma variante quando o cancelamento veio depois da conexão (etapa 5).
   - Nenhuma etapa aparece como `atual`: a etapa em que o processo parou fica `pendente`; se o cliente cancelou já na etapa 5, todas ficam `concluida`.
   - Novo campo `status_cliente` em todos os retornos.
3. **Atendimento de cancelamento antes do cadastro** (`seed.py`): `criado = max(cliente.criado_em + 1h, cancelamento - n dias)`. Além disso, `_atendimento()` limita qualquer `criado_em` para depois do cadastro e garante `resolvido_em >= criado_em`.
4. **Datas antes do `criado_em` do cliente** (`seed.py`).
   - Novo auxiliar `_apos_cadastro()`, usado em `ultimo_login_app` (ativos, em ativação e cancelados) e no atendimento "Prazo de ativação".
   - `_notificar()` pula qualquer notificação anterior ao cadastro. Isso cobre a promoção do Café Serrano para clientes que se cadastraram depois do anúncio.
5. **"Hoje" consistente.** O seed usa `self.agora = agora_utc()` e `self.hoje = self.agora.date()`. Nas consultas, `_agora()` e `_hoje()` derivam de `modelos.agora_utc()` (usados em `obter_ativacao.dias_desde_cadastro` e em `listar_faturas_vencidas.dias_em_atraso`). O `date.today()` (horário local) foi removido.
6. **Ativos com menos de 12 faturas:** documentado no `README.md`. Clientes com menos de 1 ano de conexão têm menos faturas.
7. **`inicializar_banco`** (`conexao.py`): o seed só roda com `recriar=True` ou com `clientes`, `funcionarios`, `usinas` e `parceiros` **todos vazios**. Num estado parcial, o seed não roda (evita `IntegrityError` nas colunas únicas) e um `logger.warning` sugere `python -m app.database.seed`.

### Decisões
- `resumo_economia_cliente` e `listar_indicacoes` devolvem `None` quando o cliente não existe, seguindo a regra geral do contrato para "não encontrado". Por isso a anotação é `dict | None`.
- `simular_economia` levanta `ValueError` (com mensagem em português) para entradas inválidas, o equivalente ao 400 da API.
- `obter_funcionario` devolve `{id, nome, email, perfil}` e `None` se o funcionário estiver inativo.
- `metricas_gerais.ativacao_por_etapa` conta só os clientes `em_ativacao`. Como esses clientes ficam nas etapas 1–4, a chave `"5"` normalmente vale 0. `clube.cupons_ativos` conta só a situação `ativo` (sem `salvo`), para bater com `listar_cupons(situacao="ativo")`.
- Faturas: `desconto = 15% de valor_sem_bulbe` (simplificação). No banco fictício, `valor_sem_bulbe` representa a parcela sobre a qual o desconto incide.
- O bônus especial de R$ 50 do Clube não tem coluna em `faturas`. Ele aparece como o cupom `usado` "R$ 50 de desconto na fatura" da carta especial aberta, mas **não** entra no `valor_total` das faturas (veja a correção 1 abaixo).
- A recompensa `BULBEDUO` (indicação dobrada) existe como cupom, mas o seed não dobra o bônus de nenhuma indicação.
- Os parceiros "Café Serrano Mineiro" e "EcoBike BH" são marcas inventadas, para completar os 6 parceiros.

### Pendências
- O banco **não** foi gerado nem executado (regra da squad). Só a sintaxe foi checada com `py_compile`. O primeiro `python -m app.database.seed` deve ser feito pelo líder, com as dependências instaladas.
