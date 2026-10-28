# Testes automatizados do backend

Este documento resume o trabalho de testes feito na API da Bulbe Energia (`backend/`): o que foi feito, como foi feito, como rodar e onde encontrar o resto da documentação.

| Documento | Conteúdo |
|---|---|
| [README.md](README.md) (este arquivo) | Visão geral, estratégia e como rodar |
| [catalogo-de-testes.md](catalogo-de-testes.md) | O que cada teste faz e como, arquivo por arquivo |
| [proximos-passos.md](proximos-passos.md) | Bugs encontrados pelos testes e o que fazer em seguida |

## Resumo

| | Antes | Depois |
|---|---|---|
| Arquivos de teste | 8 (1 deles vazio) | 26 |
| Casos de teste | 45 | 314 (309 passam e 5 são `xfail`, ou seja, bugs documentados) |
| Testes de API (HTTP) | 0 | 11 arquivos `test_*_api.py`, mais o `test_app.py` e os testes HTTP do `test_simulacao.py` |
| Módulos sem nenhum teste | Auth, Usina, Dica, Simulação, Indicação | nenhum |
| Cobertura de código (`app/`) | não medida | **99%** |

As linhas que continuam descobertas não são alcançáveis pelo código atual. Uma delas é o exception handler que é sobrescrito em `main.py` (ver [proximos-passos.md](proximos-passos.md)). As outras são ramos `return False` de repositórios que o service nunca chama com id inexistente.

## O que foi feito

1. **Infraestrutura**
   - `requirements.txt` ganhou o `email-validator`. O `EmailStr` do domínio de Cliente depende dele e, sem ele, **nenhum teste rodava** (erro de import na coleta). Também ganhou o `pytest-cov`, para medir a cobertura.
   - `tests/conftest.py` passou a zerar **todos** os repositórios em memória antes de cada teste, e não só o de Adesões. Também zera as sequências de ofensiva guardadas no `CartaService`. Sem isso, os testes de API deixariam dados para os testes seguintes.
2. **Testes novos** para os módulos que não tinham nenhum: Auth (segurança, service e API), Usina, Dica, Simulação e Indicação.
3. **Testes completados** nos módulos que já tinham testes: Adesão, Cliente, Cupom, Parceiro, Carta, Ativação e Primeiro Acesso. Foram cobertos os caminhos de erro (404, 409, 400), os filtros, a paginação e as regras de negócio que faltavam.
4. **Testes de API** (`test_*_api.py`) para todas as rotas. Eles verificam os status HTTP, o formato padronizado de erro e a exigência de token nas rotas protegidas.
5. **Bugs documentados com `xfail`**. Cada um tem um teste que descreve o comportamento correto e hoje falha (ver abaixo).

Cada arquivo de teste foi um commit separado com prefixo `test:`, seguindo o Conventional Commits do projeto. Os commits estão na branch `testes/cobertura-backend`.

## Como foi feito

### Duas camadas de teste

**Testes unitários** (`test_<modulo>.py`) testam o **service** e o **domínio** sem passar por HTTP.

- Cada teste cria um repositório novo e injeta no service (`AdesaoService(AdesaoRepository())`). Assim, os dados de um teste não aparecem no outro.
- Os erros de negócio são verificados com `pytest.raises(ErroDeNegocio)`, conferindo o `status` e o `code` do erro.
- As validações do Pydantic são verificadas com `pytest.raises(ValidationError)`.

**Testes de integração** (`test_<modulo>_api.py`) chamam as rotas de verdade pelo `TestClient` do FastAPI, sem subir o uvicorn.

- Verificam o status HTTP (200, 201, 202, 204, 400, 401, 404, 409, 422).
- Verificam o corpo de erro padronizado: `{"error": {"code", "message", "status"}}`.
- Verificam que as rotas protegidas recusam a requisição sem token (401) e aceitam com token, usando a fixture `headers_auth`.

### Fixtures compartilhadas (`tests/conftest.py`)

| Fixture | O que faz |
|---|---|
| `limpar_repositorios` (autouse) | Antes de **cada** teste, chama `__init__()` de todos os repositórios globais e do `CartaService`. Os dados mock (cliente Marcos Andrade, parceiros, cupom BULBE15, carta da semana 3...) voltam ao estado inicial. |
| `client` | `TestClient(app)` para fazer requisições HTTP. |
| `headers_auth` | Registra um usuário, faz login e devolve `{"Authorization": "Bearer <token>"}`. |
| `usina_valida` | Corpo JSON válido para criar uma usina. |

### Técnicas usadas

- **`@pytest.mark.parametrize`** roda o mesmo teste com várias entradas. Exemplos: CPFs inválidos, campos fora do limite, paginação inválida.
- **Estado preparado direto no repositório**, quando a API não oferece um caminho. Exemplos: forçar `expira_em` no passado para testar código expirado, ou mudar a situação de uma indicação para `aderiu`.
- **`model_copy(update=...)`** cria uma variação dos dados de uma fixture sem duplicar o objeto inteiro.
- **`Mock`** do `unittest.mock` foi usado em um teste para mostrar que o service só delega ao repositório injetado.
- **`@pytest.mark.xfail(strict=True)`** marca os testes que descrevem o comportamento **correto** mas hoje falham por causa de um bug. Com `strict=True`, quando o bug for corrigido o teste passa a dar `XPASS` e a suíte **quebra**. Isso avisa que é hora de remover o `xfail`.

### Bugs encontrados (testes `xfail`)

| Teste | Bug |
|---|---|
| `test_auth_api.py::test_resposta_401_tem_header_www_authenticate` | O `main.py` registra dois handlers para o `ErroDeNegocio`. O segundo sobrescreve o primeiro, então o header `WWW-Authenticate: Bearer` nunca é enviado nas respostas 401. |
| `test_adesao_domain.py::test_adesao_update_aceita_atualizacao_parcial` | O `AdesaoUpdate` usa `Field(...)`, o que torna os campos "opcionais" obrigatórios. |
| `test_adesao_api.py::test_atualizar_somente_o_status_da_adesao` | Consequência do bug acima na API: um `PUT` só com `status` devolve 422. |
| `test_parceiro.py::test_renomear_parceiro_para_nome_existente` | O `PUT` de parceiro não verifica se o nome já existe, embora o `POST` verifique. |
| `test_primeiro_acesso_api.py::test_confirmacao_reflete_no_cadastro_do_cliente` | O Primeiro Acesso tem uma lista de clientes própria. Confirmar o código não muda o `acesso_habilitado` em `/v1/clientes`. |

Os detalhes e a correção sugerida para cada um estão em [proximos-passos.md](proximos-passos.md).

## Como rodar

A partir da pasta `backend/`, com o ambiente virtual ativo:

```bash
pip install -r requirements.txt

# toda a suíte
pytest

# um módulo só
pytest tests/test_cliente.py tests/test_cliente_api.py

# um teste específico
pytest tests/test_carta.py::test_quinta_semana_gera_carta_especial

# só os testes cujo nome contém "token"
pytest -k token

# com relatório de cobertura
pytest --cov=app --cov-report=term-missing
```

A suíte leva cerca de 45 segundos. Quase todo esse tempo vai para o bcrypt da fixture `headers_auth`, que é proposital: o hash de senha precisa ser lento. Em [proximos-passos.md](proximos-passos.md) há uma sugestão para acelerar os testes.

## Convenções para novos testes

- Testes do service e do domínio vão em `tests/test_<modulo>.py`. Testes de rota vão em `tests/test_<modulo>_api.py`.
- O nome do teste descreve o comportamento esperado: `test_<acao>_<cenario>`, por exemplo `test_criar_cliente_com_cpf_duplicado`.
- Coloque a user story na docstring quando houver (`"""US-21: ..."""`).
- Nos testes de erro, verifique o `status` **e** o `code`, não só que "deu exceção".
- Ao criar um repositório global novo, adicione-o à lista `REPOSITORIOS_GLOBAIS` do `conftest.py`.
