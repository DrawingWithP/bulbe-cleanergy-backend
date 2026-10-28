# Próximos passos

Este documento lista os problemas que os testes encontraram e as melhorias sugeridas, em ordem de prioridade. O que já foi feito está no [README](README.md), e o detalhe de cada teste está no [catálogo](catalogo-de-testes.md).

## 1. Corrigir os bugs documentados com `xfail`

Cada bug abaixo tem um teste marcado com `@pytest.mark.xfail(strict=True)`. Depois de corrigir o bug, **remova o decorator `xfail`** do teste correspondente. Se ele ficar, a suíte vai falhar com `XPASS(strict)`, de propósito.

### 1.1 Header `WWW-Authenticate` some das respostas 401

- **Onde:** `app/main.py`, nas funções `tratar_erro_de_negocio` e `tratar_erro_usina`.
- **Problema:** as duas usam `@app.exception_handler(ErroDeNegocio)`. O FastAPI guarda os handlers em um dicionário pela classe da exceção, então o segundo substitui o primeiro. A versão que adiciona o header `WWW-Authenticate: Bearer` nunca roda. O relatório de cobertura confirma: as linhas desse handler nunca são executadas.
- **Correção:** apagar `tratar_erro_usina` e manter só `tratar_erro_de_negocio`.
- **Teste:** `test_auth_api.py::test_resposta_401_tem_header_www_authenticate`.

### 1.2 `AdesaoUpdate` não permite atualização parcial

- **Onde:** `app/domain/adesao.py`, classe `AdesaoUpdate`.
- **Problema:** os campos são `str | None = Field(..., ...)`. O `...` torna o campo **obrigatório**, embora o docstring diga "Todos opcionais". Um `PUT /v1/adesoes/{id}` só com `{"status": "aprovada"}` devolve 422.
- **Correção:** trocar `Field(...,` por `Field(None,` nos quatro campos, como já é feito em `UsinaUpdate` e `DicaUpdate`.
- **Testes:** `test_adesao_domain.py::test_adesao_update_aceita_atualizacao_parcial` e `test_adesao_api.py::test_atualizar_somente_o_status_da_adesao`.
- **Atenção:** depois da correção, vale revisar `test_adesao_service.py::test_atualizar_status_da_adesao`, que hoje envia todos os campos só para contornar o bug.

### 1.3 Renomear parceiro para um nome já existente

- **Onde:** `app/services/parceiro_service.py`, método `atualizar`.
- **Problema:** o `criar` barra nomes duplicados com 409, mas o `atualizar` não. Dá para ter dois parceiros chamados "Banco Inter".
- **Correção:** antes de trocar o nome, chamar `self._repository.buscar_por_nome(novo_nome)` e lançar `CONFLITO_DADOS` (409) se encontrar outro parceiro com id diferente.
- **Teste:** `test_parceiro.py::test_renomear_parceiro_para_nome_existente`.

### 1.4 Primeiro Acesso não atualiza o cadastro do cliente

- **Onde:** `app/repositories/primeiro_acesso_repository.py`.
- **Problema:** o repositório tem a **própria lista de clientes** (Marcos e Ana), separada do `ClienteRepository`. Confirmar o código muda `acesso_habilitado` só nessa lista. `GET /v1/clientes/{id}` continua mostrando `false`. Além disso, um cliente cadastrado por `POST /v1/clientes` não consegue fazer o primeiro acesso.
- **Correção:** fazer o `PrimeiroAcessoRepository` (ou o service) buscar e atualizar os clientes pelo `cliente_repository`.
- **Teste:** `test_primeiro_acesso_api.py::test_confirmacao_reflete_no_cadastro_do_cliente`.

## 2. Segurança

| Item | Detalhe | Sugestão |
|---|---|---|
| Sem limite de tentativas no código de verificação | `test_codigo_correto_funciona_depois_de_tentativas_erradas` mostra que o código de 6 dígitos aceita tentativas sem limite. O campo `tentativas` é contado mas nunca usado. | Bloquear a verificação (ex.: 5 tentativas) com um erro `429` ou `400 TENTATIVAS_EXCEDIDAS`, e criar o teste. |
| Rotas administrativas sem token | Estas rotas são públicas: `POST/PUT/DELETE /v1/parceiros`, `PATCH /v1/clientes/{id}/ativacao` (US-12, feita pelo operador), `PATCH/DELETE /v1/cupons/{id}` e `POST /v1/cartas/{id}/abertura`. | A equipe precisa decidir quais exigem token. Para as que passarem a exigir, copiar o padrão dos testes `*_sem_token_retorna_401`. |
| Chave JWT padrão no código | `app/core/config.py` tem um valor padrão para `BULBE_SECRET_KEY`. | Em produção, falhar na inicialização se a variável de ambiente não estiver definida. |

## 3. Consistência e qualidade do código

| Item | Detalhe |
|---|---|
| `ErroDeNegocio` duplicado | Cada service define a própria classe `ErroDeNegocio`, e o `main.py` registra um handler igual para cada uma (11 no total). Uma única classe em `app/core/erros.py` simplifica o código e evita bugs como o do item 1.1. |
| Indicação usa outro formato de erro | O controller de indicações usa `HTTPException`, que devolve `{"detail": ...}`. Os outros devolvem `{"error": {code, message, status}}`. Os testes em `test_indicacao_api.py` validam o formato atual e precisarão ser ajustados se isso mudar. |
| `cliente_id` de Indicação é `int` | Os clientes usam UUID (`str`), mas `IndicacaoCreate.cliente_id` e a rota `/v1/clientes/{cliente_id}/indicacoes` usam `int`. Uma indicação não consegue apontar para um cliente real. |
| Código de erro de CPF duplicado na Adesão | O CPF repetido devolve 409 com `code="CPF_INVALIDO"`. No módulo de Cliente, o mesmo caso usa `CONFLITO_DADOS`. |
| Próxima carta "fantasma" no Clube | Quando não há carta disponível, `obter_situacao_clube` devolve `carta_id="proxima-carta-agendada"` e `dias_restantes=4` fixos, embora `abrir_carta` já tenha criado a próxima carta real para daqui a 7 dias. |
| Valores fixos | `previsao_conclusao="2026-08-31"` na Ativação (data já passada), `dias_restantes=14` nos cupons (não é calculado a partir de `valido_ate`), parceiro Livelo fixo e código `BULBELIV{ddmm}` repetido para todos os clientes no mesmo dia em `abrir_carta`. |
| Classe com nome errado | `app/domain/simulacao.py` define `UsinaUpdate` (deveria ser `SimulacaoUpdate`), com campos obrigatórios. Ela não é usada, então pode ser corrigida ou removida. |
| Rota `/v1/simulacaos` | O plural correto seria `/v1/simulacoes`. Se mudar, ajuste `test_simulacao.py` e `test_app.py`. |
| Avisos de depreciação | `class Config` está depreciado no Pydantic v2 (11 dos 12 warnings da suíte). O substituto é `model_config = ConfigDict(from_attributes=True)`. O 12º warning vem do Starlette, que pede o `httpx2` no lugar do `httpx` para o `TestClient`. |

## 4. Melhorias na suíte de testes

1. **Acelerar os testes de API.** A suíte leva cerca de 45 s, e quase tudo é o bcrypt rodando na fixture `headers_auth`. Opções:
   - no `conftest.py`, fazer monkeypatch de `bcrypt.gensalt` para usar `rounds=4` (só nos testes);
   - ou gerar o token direto com `criar_token_acesso` depois de criar o usuário no repositório, sem passar pelo login.
2. **Rodar os testes no CI.** Criar um workflow do GitHub Actions que rode `pytest --cov=app --cov-fail-under=95` em todo pull request.
3. **Testes de contrato.** Comparar o `openapi.json` gerado com o `docs/Lista_de_endpoints.md`, para detectar rotas que mudaram sem atualizar a documentação.
4. **Quando entrar o banco de dados.** Os repositórios hoje são em memória e o `conftest.py` os zera com `__init__()`. Com um banco real, essa fixture deve abrir uma transação por teste e dar rollback no fim, ou usar um banco SQLite temporário.
