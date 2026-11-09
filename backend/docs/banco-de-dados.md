# Banco de dados (Sprint 3)

O backend guarda os dados em um banco relacional com **SQLAlchemy 2** (ORM) e **Alembic** (migrations).
Por padrão usa **SQLite** no arquivo `backend/bulbe.db`, que fica fora do Git (`*.db` no `.gitignore`).

## Como rodar

Tudo a partir da pasta `backend/`, com o venv ativado:

```bash
pip install -r requirements.txt
alembic upgrade head        # cria/atualiza as tabelas no bulbe.db
python -m app.db.seed       # (opcional) dados fictícios para a demo
uvicorn app.main:app --reload
```

- `alembic current` mostra a versão do banco (deve aparecer `(head)`).
- O schema é criado **só** pela migration, nunca no startup da API.
  Se aparecer `no such table`, faltou o `alembic upgrade head`.
- Usuário de demonstração criado pelo seed: veja o docstring de [`app/db/seed.py`](../app/db/seed.py).

### Usar PostgreSQL em vez de SQLite

Basta trocar a variável de ambiente (e instalar o driver, ex.: `pip install "psycopg[binary]"`):

```bash
BULBE_DATABASE_URL=postgresql+psycopg://bulbe:bulbe@localhost:5432/bulbe
```

## Quando mudar um modelo

1. Altere `app/db/models.py`.
2. Gere a migration: `alembic revision --autogenerate -m "descreve a mudanca"`.
3. **Leia** o arquivo gerado em `migrations/versions/` antes de aplicar
   (coluna renomeada vira "apagar e criar" e perde os dados).
4. Aplique: `alembic upgrade head`. Para desfazer: `alembic downgrade -1`.
5. Commite o modelo **e** a migration juntos.

## Onde fica cada coisa

| Arquivo | Papel |
|---|---|
| `app/core/config.py` | `DATABASE_URL` (variável `BULBE_DATABASE_URL`, padrão `sqlite:///./bulbe.db`) |
| `app/db/database.py` | `engine`, `SessionLocal` e `Base` (e liga as FKs no SQLite) |
| `app/db/models.py` | Modelos ORM (`UsinaModel`, `ClienteModel`, ...) |
| `app/db/seed.py` | Dados fictícios da demo (`python -m app.db.seed`) |
| `alembic.ini`, `migrations/` | Configuração e versões das migrations (vão para o Git) |
| `app/repositories/*.py` | Contrato `Protocol` + `InMemory...` + `Sql...` |

## Repositórios: um contrato, duas implementações

Cada repositório tem:

- `XRepository` (`Protocol`): o contrato que o Service conhece;
- `InMemoryXRepository`: dicionário Python, usado nos **testes unitários** de Service;
- `SqlXRepository`: SQLAlchemy, usado pela API (`x_repository`).

Todo método SQL segue o mesmo padrão: abre a sessão com `with`, opera, dá `commit` (e `refresh`)
e converte o modelo ORM para o objeto Pydantic do Domínio. Nenhum objeto do SQLAlchemy sai do repositório.
Controllers, Domínio e `main.py` não mudaram.

## Tabelas e chaves estrangeiras

| Tabela | PK | FK |
|---|---|---|
| `usuarios` | `id` | (email único) |
| `usinas`, `dicas`, `adesoes`, `simulacoes` | `id` | |
| `indicacoes` | `id` | ainda sem FK (ver pendências) |
| `clientes` | `id` (UUID) | (email e CPF únicos) |
| `ativacoes` | `cliente_id` | `cliente_id → clientes.id` (CASCADE) |
| `verificacoes_primeiro_acesso` | `id` | `cliente_id → clientes.id` (CASCADE) |
| `parceiros` | `id` | |
| `cartas` | `id` | `cliente_id → clientes.id` (CASCADE) |
| `cupons` | `id` | `cliente_id → clientes.id` (CASCADE), `carta_id → cartas.id` (SET NULL) |
| `ofensivas_clube` | `cliente_id` | `cliente_id → clientes.id` (CASCADE) |

Remover um cliente apaga, no próprio banco, a ativação, as cartas, os cupons e a ofensiva dele.

Escolhas de modelagem:

- `cupons` guarda um "retrato" do parceiro (`parceiro_id`, `parceiro_nome`, `parceiro_categoria`) **sem FK**:
  o cupom emitido continua válido mesmo que o parceiro saia do Clube (US-26).
- `cartas.cupom_id` não é FK, porque `cupons.carta_id` já aponta para a carta e uma FK nos dois sentidos criaria um ciclo.

## Testes

```bash
pytest
```

- **Unitários** (`test_cliente.py`, `test_carta.py`, ...): Services com repositórios `InMemory`, sem banco.
- **Integração** (`test_sql_repository.py`, `test_api_integracao.py`): usam `bulbe_test.db`,
  recriado do zero antes de cada teste (`tests/conftest.py`).
  O `os.environ["BULBE_DATABASE_URL"]` do `conftest.py` vem **antes** de qualquer `from app`,
  senão os testes apagariam o seu `bulbe.db`.

## Pendências

- `indicacoes.cliente_id` é inteiro no Domínio (`IndicacaoBase.cliente_id: int`), mas `clientes.id` é UUID (texto).
  Para criar a FK é preciso alinhar o tipo no Domínio e na rota `GET /v1/clientes/{cliente_id}/indicacoes`.
- Datas como `criado_em` continuam como texto ISO 8601 (como no Domínio). Trocar por `DateTime` exige mudar o Domínio.
