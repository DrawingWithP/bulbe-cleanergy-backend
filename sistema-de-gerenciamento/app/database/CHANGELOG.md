# CHANGELOG — `app/database/` (agente `db`)

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
