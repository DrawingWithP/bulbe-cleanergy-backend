# Catálogo de testes

Este catálogo explica, arquivo por arquivo, o que cada teste verifica e como. Para a estratégia geral, veja o [README](README.md).

Legenda:

- **Unitário**: chama o service ou o modelo Pydantic direto, com um repositório novo.
- **API**: faz uma requisição HTTP pelo `TestClient`.
- **(N casos)**: teste parametrizado, que roda N vezes com entradas diferentes.
- **xfail**: o teste descreve o comportamento correto, mas hoje falha por causa de um bug conhecido.

Dados mock usados nos testes (recriados antes de cada teste pelo `conftest.py`):

| Dado | Valor |
|---|---|
| Cliente padrão | Marcos Andrade, id `8f1c2a6e-...7e11`, CPF `12345678900`, tel. `(31) 98888-1234` |
| Carta padrão | id `a7c4e2b9-...7b55`, semana 3, `disponivel`; ofensiva do cliente = 3 |
| Cupom padrão | id `f6b1d803-...1d22`, código `BULBE15`, parceiro Drogaria Araújo, `ativo` |
| Parceiros | Drogaria Araújo (`1d2c3b4a-...e8f9`, Farmácia) e Banco Inter (Banco) |
| Ativação | cliente padrão na etapa 2 (30%), atualizada em 2026-08-18 |

## Sumário

- [Infraestrutura (`conftest.py`)](#infraestrutura-conftestpy)
- [Segurança e autenticação](#segurança-e-autenticação)
- [Adesão](#adesão)
- [Usina](#usina)
- [Dica](#dica)
- [Simulação](#simulação)
- [Indicação](#indicação)
- [Cliente](#cliente)
- [Cupom](#cupom)
- [Parceiro](#parceiro)
- [Clube Bulbe e Cartas](#clube-bulbe-e-cartas)
- [Ativação CEMIG](#ativação-cemig)
- [Primeiro Acesso](#primeiro-acesso)
- [Aplicação (`test_app.py`)](#aplicação-test_apppy)

---

## Infraestrutura (`conftest.py`)

O arquivo não contém testes, só fixtures que o pytest injeta pelo nome do parâmetro.

- `limpar_repositorios` tem `autouse=True`, então roda sozinha antes de todo teste. Ela percorre a lista `REPOSITORIOS_GLOBAIS` e chama `repositorio.__init__()` em cada um. Isso reinicia o objeto **no mesmo lugar da memória**: os services globais continuam apontando para ele, mas com os dados zerados ou com o mock inicial. Ela faz o mesmo com o `carta_service`, que guarda as sequências de ofensiva.
- `client` cria um `TestClient(app)`.
- `headers_auth` faz `POST /v1/auth/registrar` e `POST /v1/auth/login` e devolve o cabeçalho `Authorization: Bearer ...`.
- `usina_valida` devolve um dicionário com uma usina válida.

---

## Segurança e autenticação

### `test_security.py`: unitário, funções de `app/core/security.py`

| Teste | O que verifica | Como |
|---|---|---|
| `test_hash_nao_guarda_a_senha_original` | O hash é diferente da senha e tem o formato bcrypt (`$2...`) | Gera o hash e compara |
| `test_hash_da_mesma_senha_muda_a_cada_chamada` | O bcrypt usa salt aleatório | Gera dois hashes da mesma senha e confirma que são diferentes |
| `test_verificar_senha_correta` | `verificar_senha` devolve `True` para a senha certa | Gera o hash e verifica com a mesma senha |
| `test_verificar_senha_incorreta` | `verificar_senha` devolve `False` para a senha errada | Verifica com outra senha |
| `test_token_guarda_email_no_campo_sub` | O JWT carrega o email do usuário | `criar_token_acesso` → `decodificar_token` devolve o email |
| `test_token_tem_data_de_expiracao` | A validade do token respeita o parâmetro | Cria com 5 min, decodifica com `jwt.decode` e confere `exp - iat == 300` |
| `test_token_expirado_e_rejeitado` | Token vencido é rejeitado | Cria com `timedelta(minutes=-1)` e espera `ExpiredSignatureError` |
| `test_token_assinado_com_outra_chave_e_rejeitado` | Token forjado não passa | Assina com outra chave e espera `InvalidSignatureError` |
| `test_token_malformado_e_rejeitado` | Texto aleatório não é aceito como token | Espera `PyJWTError` |

### `test_auth_service.py`: unitário, `AuthService`

Usa um `UsuarioRepository()` novo em cada teste.

| Teste | O que verifica | Como |
|---|---|---|
| `test_registrar_usuario_com_sucesso` | O cadastro devolve id, email e **não** devolve a senha | Confere os campos e que `senha_hash` não existe no retorno |
| `test_registrar_guarda_somente_o_hash_da_senha` | O repositório guarda o hash, não a senha | Busca no repositório e confere com `verificar_senha` |
| `test_registrar_email_duplicado` | O segundo cadastro com o mesmo email dá 409 `EMAIL_JA_CADASTRADO` | Registra duas vezes |
| `test_registrar_email_duplicado_com_maiusculas` | `OPERACAO@...` conta como o mesmo email | Registra com o email em maiúsculas |
| `test_autenticar_com_sucesso` | O login devolve um token `bearer` | Registra e autentica |
| `test_autenticar_senha_incorreta` | Senha errada dá 401 `CREDENCIAIS_INVALIDAS` | Autentica com a senha errada |
| `test_autenticar_email_inexistente_tem_mesma_mensagem` | Email inexistente e senha errada têm **a mesma** mensagem, para não revelar quais emails existem | Compara `code` e `message` dos dois erros |
| `test_usuario_do_token_valido` | O token devolve o usuário certo | Faz login e chama `usuario_do_token` |
| `test_usuario_do_token_invalido` | Token inválido dá 401 `TOKEN_INVALIDO` | Passa uma string qualquer |
| `test_usuario_do_token_expirado` | Token vencido dá 401 | Gera um token com validade negativa |
| `test_usuario_do_token_de_usuario_inexistente` | Token bem assinado, mas de um email não cadastrado, dá 401 | `criar_token_acesso("fantasma@...")` sem registrar o usuário |

### `test_auth_api.py`: API, `/v1/auth` e a dependência `obter_usuario_atual`

| Teste | O que verifica | Como |
|---|---|---|
| `test_registrar_retorna_201_sem_senha` | `POST /registrar` devolve 201 e só `id`, `nome` e `email` | Compara o JSON inteiro |
| `test_registrar_email_duplicado_retorna_409` | O segundo registro dá 409 | Faz dois POST |
| `test_registrar_dados_invalidos_retorna_422` (3 casos) | Email sem `@`, senha com menos de 8 caracteres e nome com menos de 3 dão 422 | Parametrizado por campo |
| `test_login_retorna_token_bearer` | `POST /login` (formulário) devolve o token | Envia `data=` com `username`/`password` |
| `test_login_senha_errada_retorna_401` | A senha errada dá 401 `CREDENCIAIS_INVALIDAS` | Login com a senha errada |
| `test_me_com_token_valido` | `GET /me` devolve o dono do token | Usa `headers_auth` |
| `test_me_sem_token_retorna_401` | Sem token, devolve 401 no formato padronizado | Compara o corpo de erro inteiro |
| `test_me_com_token_invalido_retorna_401` | Um token qualquer dá 401 | `Bearer token-falso` |
| `test_me_com_token_expirado_retorna_401` | Um token vencido dá 401 | Gera um token com validade negativa |
| `test_resposta_401_tem_header_www_authenticate` **xfail** | A resposta 401 deveria ter `WWW-Authenticate: Bearer` | Lê o header da resposta. Falha por causa do handler duplicado em `main.py` |

---

## Adesão

### `test_adesao_domain.py`: unitário, validações do Pydantic

| Teste | O que verifica | Como |
|---|---|---|
| `test_adesao_valida_tem_status_enviada_por_padrao` | Sem `status` informado, a adesão nasce `enviada` | Cria um `AdesaoCreate` válido |
| `test_adesao_com_campo_invalido_e_rejeitada` (11 casos) | CPF com 10 ou 12 dígitos, CEP com 7, UF com 3 letras, nome curto, telefone curto, `numero=0`, valor da conta ≤ 0, distribuidora curta e status fora do enum são rejeitados | Parametrizado; espera `ValidationError` |
| `test_adesao_sem_campo_obrigatorio_e_rejeitada` (4 casos) | `nome`, `cpf`, `numero_instalacao` e `valor_conta_atual` são obrigatórios | Remove o campo do dicionário |
| `test_adesao_update_aceita_atualizacao_parcial` **xfail** | `AdesaoUpdate(status=...)` deveria ser aceito sozinho | Falha porque os campos usam `Field(...)` |

### `test_adesao_service.py`: unitário, `AdesaoService`

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_adesao_com_mesmo_cpf` | CPF repetido dá 409 | Cria duas vezes |
| `test_consultar_adesao_por_id` | Busca pelo id devolve a adesão criada | Cria e busca o id 1 |
| `test_atualizar_dados_adesao` | A atualização muda o telefone | Atualiza e busca de novo |
| `test_criar_adesao_com_sucesso` | Id 1, status `enviada` e `data_ativacao` preenchida | Cria e confere os campos |
| `test_criar_adesao_com_mesmo_cpf_retorna_codigo_do_erro` | O código do erro de CPF repetido é `CPF_INVALIDO` | Confere o `code` |
| `test_ids_sao_sequenciais` | Os ids crescem 1, 2... | Cria duas com CPFs diferentes |
| `test_listar_adesoes_vazio` | Sem dados, a lista é vazia | `listar()` |
| `test_listar_adesoes` | A lista traz todas as adesões | Cria duas e conta |
| `test_consultar_adesao_inexistente` | Id inexistente dá 404 `RECURSO_NAO_ENCONTRADO` | Busca o id 99 |
| `test_atualizar_adesao_inexistente` | Atualizar um id inexistente dá 404 | Atualiza o id 99 |
| `test_atualizar_status_da_adesao` | Muda o status e preserva os campos não enviados (cidade) | Envia um `AdesaoUpdate` completo (o parcial é o bug acima) |
| `test_remover_adesao` | Depois de remover, a busca dá 404 | Remove e busca |
| `test_remover_adesao_inexistente` | Remover um id inexistente dá 404 | Remove o id 99 |
| `test_service_usa_o_repositorio_recebido` | O service só delega ao repositório injetado | Passa um `Mock` e confere `listar.assert_called_once()` |

### `test_adesao_api.py`: API, `/v1/adesoes` (PUT e DELETE exigem token)

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_adesao_retorna_201` | O POST é público e devolve 201 com status `enviada` | POST com um JSON válido |
| `test_criar_adesao_cpf_duplicado_retorna_409` | Um POST repetido dá 409 no formato padronizado | Fixture `adesao_criada` e outro POST |
| `test_criar_adesao_invalida_retorna_422` | UF inválida dá 422 | `uf="MGS"` |
| `test_listar_e_buscar_adesao` | Os GET de lista e por id funcionam | — |
| `test_buscar_adesao_inexistente_retorna_404` | Id inexistente dá 404 `RECURSO_NAO_ENCONTRADO` | GET `/99` |
| `test_atualizar_adesao_sem_token_retorna_401` | O PUT exige token | PUT sem header |
| `test_atualizar_adesao_com_token` | O PUT com token atualiza o status e o telefone | Usa `headers_auth` |
| `test_remover_adesao_sem_token_retorna_401` | O DELETE exige token | DELETE sem header |
| `test_remover_adesao_com_token_retorna_204` | O DELETE devolve 204 e a adesão some | DELETE e depois GET → 404 |
| `test_atualizar_somente_o_status_da_adesao` **xfail** | Um PUT só com `{"status": ...}` deveria funcionar | Hoje dá 422 |

---

## Usina

### `test_usina.py`: unitário, `UsinaService` e domínio

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_usina_com_sucesso` | Id 1, status padrão `ativa` e `data_ativacao` preenchida | Cria e confere |
| `test_listar_usinas` | A lista começa vazia e depois traz os ids 1 e 2 | Cria duas |
| `test_buscar_usina_por_id` | A busca devolve a usina criada | — |
| `test_buscar_usina_inexistente` | Id inexistente dá 404 | Busca o id 99 |
| `test_atualizar_usina_parcialmente` | Só o campo enviado muda | Envia só `status`; nome e capacidade continuam iguais |
| `test_atualizar_usina_inexistente` | Atualizar um id inexistente dá 404 | — |
| `test_remover_usina` | A usina some da lista | — |
| `test_remover_usina_inexistente` | Remover um id inexistente dá 404 | — |
| `test_usina_com_campo_invalido_e_rejeitada` (5 casos) | Nome e localização curtos, capacidade 0 ou negativa e status inválido são rejeitados | Parametrizado; espera `ValidationError` |

### `test_usina_api.py`: API, `/v1/usinas` (POST, PUT e DELETE exigem token)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_usinas_e_publico` | O GET funciona sem token | — |
| `test_criar_usina_sem_token_retorna_401` | O POST exige token, com o código `TOKEN_INVALIDO` | — |
| `test_criar_usina_com_token_retorna_201` | O POST com token cria a usina | Usa `usina_valida` + `headers_auth` |
| `test_criar_usina_invalida_retorna_422` | Capacidade 0 dá 422 | — |
| `test_fluxo_completo_de_crud` | Criar → consultar → atualizar → remover → 404 | Sequência de chamadas no mesmo teste |
| `test_buscar_usina_inexistente_retorna_erro_padronizado` | O corpo do erro 404 está exatamente no formato padrão | Compara o JSON inteiro |
| `test_atualizar_e_remover_sem_token_retornam_401` | PUT e DELETE sem token são recusados e a usina continua lá | — |
| `test_id_nao_numerico_retorna_422` | `/v1/usinas/abc` dá 422 (o id é `int`) | — |

---

## Dica

### `test_dica.py`: unitário, `DicaService` (US-30)

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_dica_com_sucesso` | Cria com id 1 e guarda o SVG | — |
| `test_listar_dicas` | A lista começa vazia e depois tem 1 | — |
| `test_buscar_dica_por_id` | A busca devolve a dica criada | — |
| `test_buscar_dica_inexistente` | Id inexistente dá 404 | — |
| `test_atualizar_dica_parcialmente` | Só a `economia` muda | — |
| `test_atualizar_dica_inexistente` | Atualizar um id inexistente dá 404 | — |
| `test_remover_dica` | US-30: depois de remover, a busca dá 404 | — |
| `test_remover_dica_inexistente` | Remover um id inexistente dá 404 | — |
| `test_dica_com_campo_invalido_e_rejeitada` (4 casos) | Título e descrição curtos, descrição > 250 e economia 0 são rejeitados | Parametrizado |

### `test_dica_api.py`: API, `/v1/dicas` (POST, PUT e DELETE exigem token)

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_dica_sem_token_retorna_401` | O POST exige token | — |
| `test_criar_dica_com_token_retorna_201` | O POST com token cria a dica | — |
| `test_listar_e_buscar_dica_sao_publicos` | Os GET funcionam sem token | Fixture `dica_criada` |
| `test_atualizar_dica` | O PUT com token atualiza | — |
| `test_remover_dica_retorna_204` | US-30: o DELETE devolve 204 e a dica some | — |
| `test_atualizar_e_remover_sem_token_retornam_401` | PUT e DELETE exigem token | — |
| `test_remover_dica_inexistente_retorna_404` | DELETE de um id inexistente dá 404 `RECURSO_NAO_ENCONTRADO` | — |

---

## Simulação

### `test_simulacao.py`: unitário + API, `SimulacaoService` e `POST /v1/simulacaos`

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_simulacao` | Cria com id 1 e `data_ativacao` | — |
| `test_listar_e_buscar_simulacao` | `listar` e `buscar_por_id` devolvem a simulação criada | — |
| `test_buscar_simulacao_inexistente` | Id inexistente dá 404 | — |
| `test_remover_simulacao` | A simulação some da lista | — |
| `test_remover_simulacao_inexistente` | Remover um id inexistente dá 404 | — |
| `test_valor_proposto_pode_ser_zero` | `valor_proposto` aceita 0 (`ge=0`) | — |
| `test_simulacao_com_campo_invalido_e_rejeitada` (4 casos) | `valor_atual=0`, `valor_proposto<0`, `periodo_meses=0` e `indicacoes=0` são rejeitados | Parametrizado |
| `test_api_criar_simulacao_retorna_201` | O POST devolve 201 | `TestClient` |
| `test_api_criar_simulacao_invalida_retorna_422` | Valor negativo dá 422 | `TestClient` |

---

## Indicação

### `test_indicacao.py`: unitário, `IndicacaoService`

O `IndicacaoService` não recebe o repositório pelo construtor (usa o global), então estes testes dependem da limpeza feita pelo `conftest.py`.

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_indicacao_pendente_com_bonus` | Toda indicação nasce `pendente` com bônus de 50 | — |
| `test_criar_indicacao_com_contato_duplicado` | O mesmo contato não pode ser indicado duas vezes | Espera `IndicacaoDuplicadaError` |
| `test_contato_duplicado_ignora_maiusculas` | `PAULA@EMAIL.COM` = `paula@email.com`, mesmo vindo de outro cliente | — |
| `test_buscar_indicacao_por_id` | A busca devolve a indicação criada | — |
| `test_buscar_indicacao_inexistente` | Id inexistente lança `IndicacaoNaoEncontradaError` | — |
| `test_listar_indicacoes_por_cliente` | Só aparecem as indicações do cliente pedido | Cria 3 indicações para 2 clientes |
| `test_excluir_indicacao_pendente` | Uma indicação pendente pode ser excluída | — |
| `test_excluir_indicacao_nao_pendente` (2 casos) | `aderiu` e `cancelada` não podem ser excluídas | Muda a `situacao` do objeto e espera `IndicacaoNaoPodeSerExcluidaError` |
| `test_excluir_indicacao_inexistente` | Excluir um id inexistente lança `IndicacaoNaoEncontradaError` | — |
| `test_indicacao_com_campo_invalido_e_rejeitada` (3 casos) | `cliente_id=0`, nome curto e contato curto são rejeitados | Parametrizado |

### `test_indicacao_api.py`: API (o DELETE exige token)

Este controller usa `HTTPException`, então o erro vem como `{"detail": "..."}`, e não no formato padronizado.

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_indicacao_retorna_201` | O POST cria a indicação `pendente` | — |
| `test_criar_indicacao_duplicada_retorna_409` | Contato repetido dá 409 com a mensagem no `detail` | — |
| `test_consultar_indicacao` | O GET por id funciona | — |
| `test_consultar_indicacao_inexistente_retorna_404` | Devolve 404 com `{"detail": "Indicacao nao encontrada."}` | Compara o JSON |
| `test_listar_indicacoes_do_cliente` | `GET /v1/clientes/1/indicacoes` | — |
| `test_excluir_indicacao_sem_token_retorna_401` | O DELETE exige token | — |
| `test_excluir_indicacao_com_token_retorna_204` | O DELETE com token remove a indicação | DELETE e depois GET → 404 |
| `test_excluir_indicacao_inexistente_retorna_404` | — | — |
| `test_excluir_indicacao_concluida_retorna_409` | Uma indicação que já `aderiu` não pode ser excluída | Altera a situação direto no repositório global |

---

## Cliente

### `test_cliente.py`: unitário, `ClienteService` (US-05, US-31 e US-34)

| Teste | O que verifica | Como |
|---|---|---|
| `test_criar_cliente_com_sucesso` | US-31: cria com status `em_ativacao` | — |
| `test_criar_cliente_com_cpf_duplicado` | US-31: CPF repetido dá 409 `CONFLITO_DADOS` | — |
| `test_buscar_cliente_por_id_sucesso` | US-05: devolve o cliente mock | — |
| `test_buscar_cliente_inexistente` | Id inexistente dá 404 | — |
| `test_atualizar_cliente_sucesso` | US-34: atualiza o telefone e parte do endereço | — |
| `test_listar_clientes_com_paginacao` | A listagem traz o cliente mock | — |
| `test_remover_cliente_sucesso` | Depois de remover, a busca dá erro | — |
| `test_criar_cliente_com_cpf_invalido` (4 casos) | CPF curto, longo, só zeros (com máscara) e todos os dígitos iguais dão 400 `CPF_INVALIDO` | Parametrizado |
| `test_criar_cliente_salva_cpf_somente_com_digitos` | `111.222.333-44` é salvo como `11122233344` | Lê o repositório |
| `test_criar_cliente_com_cpf_mascarado_duplicado` | O CPF do mock com máscara também é detectado como duplicado | `123.456.789-00` |
| `test_criar_cliente_com_email_duplicado` | O email repetido (sem diferenciar maiúsculas) dá 409 | — |
| `test_cliente_novo_comeca_sem_acesso_habilitado` | O cliente novo tem `acesso_habilitado=False` | — |
| `test_listar_clientes_paginacao_invalida` (3 casos) | `page=0`, `limit=0` e `limit=101` dão 400 `PARAMETROS_INVALIDOS` | Parametrizado |
| `test_listar_clientes_segunda_pagina` | Com `limit=1`, a página 2 traz o segundo cliente e `total=2` | — |
| `test_listar_clientes_filtrando_por_status` | O filtro por status funciona | `em_ativacao`=1, `ativo`=0 |
| `test_atualizar_cliente_inexistente` | Atualizar um id inexistente dá 404 | — |
| `test_atualizar_cliente_sem_campos_nao_altera_nada` | `ClienteUpdate()` vazio devolve o cliente igual | Compara os `model_dump()` de antes e depois |
| `test_atualizar_endereco_mantem_campos_nao_enviados` | US-34: mudar só o número mantém a cidade e o complemento | — |
| `test_remover_cliente_inexistente` | Remover um id inexistente dá 404 | — |
| `test_atualizar_nome_distribuidora_e_instalacao` | US-34: os outros campos cadastrais também mudam, e o telefone continua igual | — |

### `test_cliente_api.py`: API, `/v1/clientes` (PUT e DELETE exigem token)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_clientes` | A lista traz o resumo com a cidade | — |
| `test_listar_clientes_limit_acima_de_100_retorna_422` | O `Query(le=100)` barra o limite antes do service | `?limit=101` |
| `test_listar_clientes_status_invalido_retorna_422` | Status fora do enum dá 422 | — |
| `test_criar_cliente_retorna_201` | US-31: a resposta enxuta só tem 5 campos, a distribuidora padrão é CEMIG e o CPF é salvo limpo | POST e depois GET pelo id |
| `test_criar_cliente_email_invalido_retorna_422` | O `EmailStr` valida o formato | — |
| `test_criar_cliente_cpf_invalido_retorna_400` | Regra do service → 400 `CPF_INVALIDO` | — |
| `test_criar_cliente_cpf_duplicado_retorna_409` | CPF do mock dá 409 | — |
| `test_buscar_cliente` | US-05 | — |
| `test_buscar_cliente_inexistente_retorna_404` | — | — |
| `test_atualizar_cliente_sem_token_retorna_401` | O PUT exige token | — |
| `test_atualizar_cliente_com_token` | US-34: a atualização parcial do endereço mantém o logradouro | — |
| `test_remover_cliente_sem_token_retorna_401` | O DELETE exige token e o cliente continua lá | — |
| `test_remover_cliente_com_token_retorna_204` | DELETE com token → 204 e depois 404 | — |

---

## Cupom

### `test_cupom.py`: unitário, `CupomService` (US-03, US-22 e US-23)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_cupons_cliente_sucesso` | US-03: lista o cupom `BULBE15` | — |
| `test_listar_cupons_cliente_inexistente` | Cliente inexistente dá 404 | — |
| `test_buscar_cupom_por_id_sucesso` | US-22: devolve o cupom com o parceiro | — |
| `test_buscar_cupom_inexistente` | Id inexistente dá 404 | — |
| `test_atualizar_situacao_para_salvo` | US-23: `ativo` → `salvo` | — |
| `test_atualizar_situacao_para_usado` | US-23: `usado` preenche `usado_em` | — |
| `test_descartar_cupom_sucesso` | Depois do descarte, a busca dá 404 | — |
| `test_listar_cupons_paginacao_invalida` (3 casos) | `page=0`, `limit=0` e `limit=101` dão 400 | Parametrizado |
| `test_listar_cupons_filtrando_por_situacao` | O filtro por situação funciona | `ativo`=1, `salvo`=0 |
| `test_atualizar_situacao_nao_permitida` (3 casos) | Só `salvo` ou `usado` são permitidos; `ativo`, `expirado` e `descartado` dão 400 `SITUACAO_INVALIDA` | Parametrizado |
| `test_cupom_usado_nao_volta_para_salvo` | Um cupom `usado` não pode mudar de situação: 409 `CUPOM_JA_UTILIZADO` | Marca como usado e tenta salvar |
| `test_atualizar_situacao_cupom_inexistente` | — | — |
| `test_cupom_descartado_some_da_listagem` | O descarte é lógico: o cupom sai da listagem | — |
| `test_descartar_cupom_inexistente` | — | — |

### `test_cupom_api.py`: API (rotas públicas)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_cupons_do_cliente` | US-03: `GET /v1/clientes/{id}/cupons` | — |
| `test_listar_cupons_com_filtro_de_situacao` | `?situacao=usado` devolve 0 | — |
| `test_listar_cupons_cliente_inexistente_retorna_404` | — | — |
| `test_buscar_cupom` | US-22: devolve o cupom com o resumo do parceiro | — |
| `test_marcar_cupom_como_usado` | US-23: o PATCH devolve `usado_em` preenchido | — |
| `test_patch_situacao_nao_permitida_retorna_400` | `expirado` dá 400 `SITUACAO_INVALIDA` | — |
| `test_patch_situacao_fora_do_enum_retorna_422` | Um valor que não existe no enum dá 422 | — |
| `test_descartar_cupom_retorna_204` | DELETE → 204 e depois GET → 404 | — |

---

## Parceiro

### `test_parceiro.py`: unitário, `ParceiroService` (US-02, US-24, US-25, US-26 e US-33)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_parceiros_sucesso` | Lista os 2 parceiros do mock | — |
| `test_criar_parceiro_sucesso` | US-24: cria a Livelo ativa | — |
| `test_criar_parceiro_duplicado` | US-24: nome repetido dá 409 | — |
| `test_buscar_parceiro_por_id_sucesso` | US-25 | — |
| `test_buscar_parceiro_inexistente` | US-25: 404 | — |
| `test_atualizar_parceiro_sucesso` | Muda a categoria e o `ativo` | — |
| `test_remover_parceiro_sucesso` | US-26 | — |
| `test_listar_parceiros_paginacao_invalida` (3 casos) | 400 `PARAMETROS_INVALIDOS` | Parametrizado |
| `test_listar_parceiros_filtrando_por_categoria` | US-33: o filtro não diferencia maiúsculas (`BANCO`) | — |
| `test_listar_parceiros_filtrando_por_ativo` | `ativo=True` e `ativo=False` separam os parceiros | Desativa um antes |
| `test_criar_parceiro_duplicado_ignora_maiusculas_e_espacos` | `"  banco inter "` é duplicado de `Banco Inter` | — |
| `test_atualizar_parceiro_registra_data_de_atualizacao` | `atualizado_em` é preenchido | — |
| `test_atualizar_parceiro_sem_campos_nao_altera_nada` | Update vazio não mexe em `atualizado_em` | — |
| `test_atualizar_parceiro_pode_remover_logo` | `logo_url=None` apaga o logo | — |
| `test_atualizar_parceiro_inexistente` | 404 | — |
| `test_remover_parceiro_inexistente` | US-26: 404 | — |
| `test_renomear_parceiro_para_nome_existente` **xfail** | Renomear para o nome de outro parceiro deveria dar 409 | Hoje é aceito |

### `test_parceiro_api.py`: API, `/v1/parceiros` (rotas públicas)

| Teste | O que verifica | Como |
|---|---|---|
| `test_listar_parceiros` | `total=2` | — |
| `test_listar_parceiros_com_filtros` | `?categoria=farmácia&ativo=true` | — |
| `test_listar_parceiros_paginado` | `?page=2&limit=1` traz 1 item | — |
| `test_criar_parceiro_retorna_201` | US-24: `ativo` é `true` por padrão | — |
| `test_criar_parceiro_duplicado_retorna_409` | `CONFLITO_DADOS` | — |
| `test_criar_parceiro_sem_categoria_retorna_422` | `categoria` é obrigatória | — |
| `test_buscar_parceiro` | US-25 | — |
| `test_buscar_parceiro_inexistente_retorna_404` | — | — |
| `test_atualizar_parceiro` | O PUT desativa o parceiro | — |
| `test_remover_parceiro_retorna_204` | US-26: DELETE → 204 e depois GET → 404 | — |

---

## Clube Bulbe e Cartas

### `test_carta.py`: unitário, `CartaService` (US-18 a US-21)

A fixture `dados_cliente_novo` cadastra no repositório global um cliente sem cartas e sem ofensiva.

| Teste | O que verifica | Como |
|---|---|---|
| `test_obter_situacao_clube_sucesso` | US-18: meta de 5 semanas, intervalo de 7 dias e carta disponível | — |
| `test_obter_situacao_clube_cliente_inexistente` | 404 | — |
| `test_listar_cartas_cliente_sucesso` | US-19 | — |
| `test_buscar_carta_por_id_sucesso` | US-20 | — |
| `test_buscar_carta_inexistente` | US-20: 404 | — |
| `test_abrir_carta_sucesso` | US-21: gera um cupom e a ofensiva vai de 3 para 4 | — |
| `test_abrir_carta_idempotente` | Abrir duas vezes devolve o mesmo cupom | — |
| `test_abrir_carta_nao_disponivel` | Carta bloqueada dá 409 `CARTA_NAO_DISPONIVEL` | Muda a situação pelo repositório |
| `test_listar_cartas_cliente_inexistente` | US-19: 404 | — |
| `test_abrir_carta_agenda_proxima_carta_bloqueada` | Depois de abrir, a semana 4 é criada `bloqueada` e `normal` | Filtra por situação |
| `test_abrir_carta_marca_carta_como_aberta` | A carta fica `aberta`, com `aberta_em` e `cupom_id` | — |
| `test_abrir_carta_salva_cupom_na_carteira_do_cliente` | O cupom aparece no `cupom_repository` com validade de 14 dias | Lê o repositório global de cupons |
| `test_quinta_semana_gera_carta_especial` | Ao chegar a 5 semanas, a próxima carta é `especial` e `bonus_especial_pendente=True` | Ajusta `service._sequencias` para 4 antes de abrir |
| `test_situacao_clube_sem_carta_disponivel` | Depois de abrir, `carta_disponivel=False` e a próxima tem prazo | — |
| `test_situacao_clube_cliente_sem_ofensiva` | O cliente novo começa com 0 semanas e sem cartas | Usa `dados_cliente_novo` |
| `test_abrir_carta_inexistente` | 404 | — |

### `test_carta_api.py`: API

| Teste | O que verifica | Como |
|---|---|---|
| `test_situacao_do_clube` | US-18: ofensiva 3 e a próxima carta é a carta mock | — |
| `test_situacao_do_clube_cliente_inexistente_retorna_404` | — | — |
| `test_listar_cartas_do_cliente` | US-19: total e filtro `?situacao=aberta` | — |
| `test_buscar_carta` | US-20 | — |
| `test_abrir_carta_retorna_201_com_cupom` | US-21: o cupom gerado aparece em `/v1/cupons/{id}` e na carteira do cliente (total 2) | Integração entre os módulos de carta e cupom |
| `test_abrir_carta_duas_vezes_devolve_o_mesmo_cupom` | Idempotência pela API, e a ofensiva não sobe duas vezes | — |
| `test_abrir_carta_inexistente_retorna_404` | — | — |

---

## Ativação CEMIG

### `test_ativacao.py`: unitário, `AtivacaoService` (US-11 e US-12)

| Teste | O que verifica | Como |
|---|---|---|
| `test_obter_resumo_ativacao_sucesso` | US-11: etapa 2, 30% e distribuidora CEMIG | — |
| `test_obter_resumo_cliente_inexistente` | 404 | — |
| `test_listar_etapas_ativacao_sucesso` | Situações concluída, atual e pendente | — |
| `test_atualizar_etapa_ativacao_sucesso` | US-12: etapa 3 = 45% | — |
| `test_atualizar_etapa_invalida` | Etapas 0 e 6 são barradas pelo Pydantic | Espera `ValidationError` (antes era `Exception` genérica) |
| `test_cliente_sem_jornada_comeca_na_etapa_1` | A jornada é criada na 1ª consulta, com a distribuidora do cliente | Cliente novo com distribuidora "Energisa" |
| `test_listar_etapas_cliente_inexistente` | 404 | — |
| `test_etapas_concluidas_tem_data_de_conclusao` | Só as etapas concluídas têm `concluida_em` | — |
| `test_percentual_de_cada_etapa` (5 casos) | 1→15%, 2→30%, 3→45%, 4→75%, 5→100% | Parametrizado |
| `test_ultima_etapa_marca_todas_anteriores_como_concluidas` | Na etapa 5, as 4 primeiras ficam concluídas | — |
| `test_atualizar_etapa_guarda_observacao` | A observação é guardada; atualizar sem observação não adiciona nada | Lê o repositório |
| `test_atualizar_etapa_cliente_inexistente` | 404 | — |
| `test_service_tambem_valida_etapa_fora_do_intervalo` | O service tem sua própria barreira: 400 `ETAPA_INVALIDA` | Usa `model_construct`, que cria o objeto **sem** validar |

### `test_ativacao_api.py`: API

| Teste | O que verifica | Como |
|---|---|---|
| `test_consultar_resumo_da_ativacao` | US-11: etapa e prazo de 90 dias | — |
| `test_listar_etapas` | A ordem das situações das 5 etapas | — |
| `test_avancar_etapa` | US-12: o PATCH muda a etapa e o GET seguinte já mostra a mudança | — |
| `test_etapa_fora_do_intervalo_retorna_422` | `etapa_atual=6` | — |
| `test_cliente_inexistente_retorna_404` | — | — |

---

## Primeiro Acesso

### `test_primeiro_acesso.py`: unitário, `PrimeiroAcessoService` (US-09 e US-10)

| Teste | O que verifica | Como |
|---|---|---|
| `test_solicitar_verificacao_com_sucesso` | US-09: destino mascarado `(31) *****-1234` | — |
| `test_solicitar_verificacao_cpf_invalido` | CPF curto e com dígitos iguais dão 400 | — |
| `test_solicitar_verificacao_cpf_nao_cadastrado` | 404 `CLIENTE_NAO_ENCONTRADO` | — |
| `test_confirmar_codigo_com_sucesso` | US-10: confirma e habilita o acesso | Lê o código gerado no repositório |
| `test_confirmar_codigo_incorreto` | 400 `CODIGO_INVALIDO` e `tentativas=1` | — |
| `test_confirmar_codigo_expirado` | 410 `CODIGO_EXPIRADO` | Coloca `expira_em` no passado |
| `test_confirmar_codigo_ja_utilizado` | Reusar o código dá 400 `CODIGO_JA_UTILIZADO` | — |
| `test_confirmar_verificacao_inexistente` | 404 | — |
| `test_canal_padrao_e_whatsapp` | Sem informar o canal, usa `whatsapp` | — |
| `test_codigo_gerado_tem_6_digitos_e_expira_em_15_minutos` | O formato do código, a validade e a situação inicial | Compara `expira_em - criado_em` |
| `test_destino_mascarado_com_telefone_incompleto` | Telefone com menos de 10 dígitos vira `(**) *****-****` | `adicionar_cliente_mock` com telefone "1234" |
| `test_cada_solicitacao_gera_uma_verificacao_nova` | Ids diferentes a cada pedido | — |
| `test_confirmar_codigo_habilita_acesso_do_cliente` | Só o cliente certo (Ana) fica com acesso; o outro (Marcos) não | — |
| `test_confirmar_codigo_aceita_espacos_em_volta` | `" 123456 "` é aceito (`strip`) | — |
| `test_codigo_expirado_marca_verificacao_como_expirada` | Depois de expirar, a situação muda para `expirada` | — |
| `test_codigo_correto_funciona_depois_de_tentativas_erradas` | 3 erros contam 3 tentativas e o código certo ainda funciona | Documenta que **não há limite de tentativas** |

### `test_primeiro_acesso_api.py`: API

| Teste | O que verifica | Como |
|---|---|---|
| `test_solicitar_verificacao_retorna_202` | US-09: devolve 202 e **não** expõe o código na resposta | — |
| `test_solicitar_verificacao_cpf_invalido_retorna_400` | — | — |
| `test_solicitar_verificacao_cpf_nao_cadastrado_retorna_404` | — | — |
| `test_solicitar_verificacao_canal_invalido_retorna_422` | `canal="telegram"` | — |
| `test_fluxo_completo_de_primeiro_acesso` | US-09 + US-10 de ponta a ponta → 201 | Lê o código no repositório global entre as duas chamadas |
| `test_confirmar_codigo_errado_retorna_400` | — | — |
| `test_confirmar_codigo_curto_demais_retorna_422` | O código precisa ter de 4 a 10 caracteres | — |
| `test_confirmar_verificacao_inexistente_retorna_404` | — | — |
| `test_confirmacao_reflete_no_cadastro_do_cliente` **xfail** | Depois de confirmar, `GET /v1/clientes/{id}` deveria mostrar `acesso_habilitado=true` | Hoje continua `false` (bases separadas) |

---

## Aplicação (`test_app.py`)

| Teste | O que verifica | Como |
|---|---|---|
| `test_raiz_responde_que_a_api_esta_no_ar` | `GET /` | — |
| `test_swagger_e_openapi_estao_disponiveis` | `/docs` e `/openapi.json` respondem, com o título certo | — |
| `test_todos_os_modulos_estao_registrados` | Nenhum router foi esquecido no `main.py` | Procura uma rota de cada módulo no `openapi.json` |
| `test_rota_inexistente_retorna_404` | — | — |
