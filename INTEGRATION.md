# Integração frontend–backend para revisão humana

## Escopo e origem

Frontend: `gabrielmercedo/Bulbe-Squad-cleanergy`, commit `fb18142214f16b5528ac1defd1ecbb42659ed62e`.

Backend: `DrawingWithP/bulbe-cleanergy-backend`, base originalmente utilizada `86e8777040bb7733e13d3c325c5bd2c3de49d099`.

O frontend original não possui arquivo de licença. A cópia de código e assets para este destino foi expressamente autorizada pelo solicitante, que confirmou ter autorização dos responsáveis. Essa confirmação não cria uma licença pública nem transfere direitos sobre marcas ou assets de terceiros. A autoria original permanece com a equipe Cleanergy identificada no repositório de origem.

A entrada integrada é `frontend/final.html`. Foram copiados os arquivos da aplicação consolidada e seus assets, preservando os caminhos necessários.

As páginas, CSS e scripts independentes em `screens/` não foram duplicados quando não eram necessários para a aplicação consolidada. Os assets utilizados pelo frontend integrado foram preservados.

Documentos, slides, caches, segredos e dados de produção não fazem parte da integração.

Durante a revisão, arquivos em `backend/app/` foram atualizados intencionalmente para padronização, correção de contratos, validações e compatibilidade entre frontend e backend.

Nesta revisão da integração, as migrations existentes e `sistema-de-gerenciamento/` ficaram fora do escopo. Depois dela, na finalização do projeto (branch `chore/finalizacao-projeto`), entraram uma migration nova e a integração do sistema de gerenciamento com o app; veja [Atualizações da finalização](#atualizações-da-finalização).

`backend/dev_frontend.py` fornece uma entrada opcional para desenvolvimento, servindo frontend e API na mesma origem. A aplicação principal continua disponível por `app.main:app`.

Não há deploy, merge automático ou alteração automática de ambiente de produção.

## Funcionalidades conectadas

| Interface existente | Contrato real | Comunicação |
|---|---|---|
| Conexão e detalhes | `GET /v1/clientes/{id}/ativacao` e `GET /v1/clientes/{id}/ativacao/etapas` | Percentual, etapa, títulos e descrições retornados pela API |
| Dicas e carrossel | `GET /v1/dicas` | Títulos, descrições, SVG como imagem e economia |
| Vantagens | `GET /v1/clientes/{id}/clube`, `/cartas` e `/cupons` | Disponibilidade da carta, sequência, próxima data e histórico |
| Parceiros do clube | `GET /v1/parceiros` | Catálogo de parceiros ativos |
| Abrir carta | `POST /v1/cartas/{id}/abertura` | Gera ou recupera o cupom da carta |
| Selecionar cupom | `GET /v1/cupons/{id}` | Recupera o cupom selecionado |
| Salvar cupom | `PATCH /v1/cupons/{id}` | Envia `situacao=salvo` |
| Usar cupom | `PATCH /v1/cupons/{id}` | Envia `situacao=usado` |
| Simuladores aberto e logado | `POST /v1/simulacoes` | Persiste `valor_atual`, `valor_proposto`, `periodo_meses` e `indicacoes`; o logado envia também `cliente_id` |
| Entrar e Primeiro acesso (telas novas) | `POST /v1/primeiro-acesso/verificacoes` e `/confirmacoes` | CPF → código de 6 dígitos → sessão do cliente no navegador |
| Abrir conta (tela nova) | `POST /v1/adesoes` | Adesão em 3 passos (dados, endereço, conta de luz) com protocolo |
| Indicações (tela nova) | `GET /v1/clientes/{id}/indicacoes` e `POST /v1/indicacoes` | Resumo, formulário e lista das indicações do cliente |

O backend de simulações valida, calcula a economia com a bandeira tarifária vigente (RF-03) e persiste. O frontend exibe `economia_mensal` e `economia_total` devolvidos pela API (com bandeira verde, os valores são os mesmos do cálculo original do protótipo).

Os simuladores utilizam debounce de 350 ms para evitar uma gravação a cada evento intermediário de entrada.

Respostas antigas de requisições assíncronas são descartadas na apresentação quando uma revisão mais recente já foi iniciada. A API atualmente não implementa chave de idempotência para criação de simulações.

Erros de rede, timeout, JSON inválido, `detail` do FastAPI e `error.message` das regras de negócio são apresentados utilizando os alertas já disponíveis na interface.

Não são executados retries automáticos de operações de escrita.

Dados dinâmicos utilizam `textContent`, criação direta de elementos DOM ou escape antes da utilização em templates HTML existentes.

O SVG das dicas é utilizado como origem de imagem, evitando inserir diretamente markup executável no documento.

## Autenticação e autorização

A autenticação existente utiliza JWT para operadores do painel.

Endpoints:

- `POST /v1/auth/registrar`
- `POST /v1/auth/login`
- `GET /v1/auth/me`

O login utiliza `OAuth2PasswordRequestForm`, portanto o endpoint recebe `username` e `password` por `application/x-www-form-urlencoded`.

O frontend original integrado não possui formulário de login de operador nem associação entre um usuário autenticado e um `cliente_id`.

Por isso, a integração local utiliza explicitamente:

```text
BULBE_FRONTEND_CLIENTE_ID
```

Esse valor somente identifica o cliente fictício utilizado na demonstração. Ele não funciona como credencial, autenticação ou mecanismo de autorização.

As operações administrativas que possuem autenticação continuam utilizando JWT.

As operações de carta e cupom consumidas diretamente pelo frontend permanecem de acordo com o contrato público utilizado pela integração atual. Isso não representa uma política adequada de autorização para uma aplicação de consumidor final em produção. O descarte de cupom (`DELETE /v1/cupons/{id}`), que o frontend não usa, passou a exigir token de operador.

## Incompatibilidades e limites mantidos

### Login do aplicativo

Na finalização foram criadas as telas **Entrar** e **Primeiro acesso** (`frontend/telas.*`). As duas usam o fluxo de primeiro acesso da API: CPF → código de 6 dígitos → `cliente_id`, guardado no navegador (`localStorage`, chave `bulbe_cliente_id`). O botão Entrar leva à tela de login quando não há sessão e direto à área do cliente quando há; o menu lateral ganha "Sair da conta".

O código não é enviado por SMS/e-mail (fora do escopo). Fora de produção a API devolve `codigo_demonstracao` e a tela o mostra; com `BULBE_AMBIENTE=producao` o campo vem vazio.

Limite que continua: isso é **identificação**, não autenticação. A API ainda não emite token para clientes, e as rotas do cliente seguem públicas. Sem sessão, a área do cliente usa `BULBE_FRONTEND_CLIENTE_ID` (demonstração).

### Primeiro acesso, adesão e indicações

A API possui endpoints para primeiro acesso, adesões e indicações. As indicações usam o UUID do cliente (com FK), então ficam ligadas ao cliente real.

Na finalização foram criadas as telas que faltavam: **Primeiro acesso**, **Abrir conta** (adesão em 3 passos) e **Indicações** (resumo, formulário e lista). Elas ficam num bloco marcado de `final.html` (`BULBE-TELAS-NOVAS`) com CSS e JS próprios (`telas.css`, `telas.js`), seguindo as variáveis do `:root` do `final.css`; o restante do HTML original segue intacto (verificado pelo `check_preservation.py`).

### Zero indicações

Zero indicações agora é um valor válido no domínio de simulação:

```text
indicacoes >= 0
```

Portanto, o simulador pode persistir uma simulação com zero indicações.

Exemplo:

```text
Conta: R$ 200
Desconto mensal: 15% = R$ 30
Período: 3 meses
Indicações: 0

Economia exibida:
R$ 30 × 3 = R$ 90
```

Com uma indicação:

```text
R$ 90 + R$ 50 = R$ 140
```

### Ativação etapa 1

A API suporta cinco etapas.

O frontend original possui representações visuais próprias para a jornada e pode não possuir o mesmo nível de representação gráfica para todas as etapas.

O número, percentual e os detalhes continuam vindo da API. Não foram criados novos desenhos ou componentes gráficos para preencher diferenças do protótipo.

### Alteração da etapa de ativação

O endpoint:

```text
PATCH /v1/clientes/{cliente_id}/ativacao
```

é uma operação protegida por JWT.

Os controles de demonstração existentes no frontend não utilizam esse endpoint.

Avançar/voltar etapas no protótipo não modifica silenciosamente os dados reais do backend.

A etapa real pode ser alterada pelo sistema de gerenciamento (ficha do cliente → **Atualizar no app**), que chama esse endpoint com um token de operador; o frontend mostra a nova etapa na próxima consulta.

### Controles de demonstração

Passar/voltar dias e resetar o Clube não representam atualmente comandos equivalentes da API.

Esses controles não falsificam persistência.

Quando acionados em contexto integrado, informam a limitação.

### Bônus especial

A API controla a sequência e o tipo das cartas.

A recompensa efetivamente retornada pelo serviço atual deve ser considerada a fonte de verdade. Não é criado um prêmio financeiro fictício pelo frontend.

### Compartilhamento e serviços externos

Compartilhar, WhatsApp, notificações, perfil, termos, FAQ externo e contato permanecem limitados ao comportamento presente no frontend recebido quando não existe um contrato correspondente integrado.

Copiar o código de um cupom é uma operação local do navegador e não altera sua situação no backend.

### Produção e serviços externos

Não fazem parte da validação local:

- PostgreSQL de produção;
- SMS real;
- WhatsApp real;
- parceiros externos reais;
- pagamentos;
- compras;
- deploy;
- dados reais de clientes.

Os testes utilizam banco SQLite temporário e dados fictícios.

## Executar localmente

Python 3.10 ou superior.

O ambiente utilizado para a revisão deve preferencialmente usar Python 3.12.

Exemplo:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

cd backend

export BULBE_DATABASE_URL="sqlite:////tmp/bulbe-integracao-local.db"
export BULBE_SECRET_KEY="chave-exclusiva-de-desenvolvimento-local"
export BULBE_FRONTEND_CLIENTE_ID="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"

../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.db.seed

../.venv/bin/uvicorn dev_frontend:app \
    --host 127.0.0.1 \
    --port 8000
```

Abrir:

```text
http://127.0.0.1:8000/frontend/final.html
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Esses comandos devem ser utilizados somente com banco de desenvolvimento/local apropriado.

O seed contém dados fictícios e um operador de demonstração.

`config.js` é servido dinamicamente por `dev_frontend.py` com:

```text
Cache-Control: no-store
```

Nenhum segredo é enviado por esse arquivo.

Frontend e API são servidos pela mesma origem nessa configuração, portanto não é necessário adicionar CORS para a jornada local validada.

O arquivo estático `frontend/config.js` mantém:

```javascript
window.BULBE_CONFIG = {
  apiBase: '',
  clienteId: null
};
```

A entrada de desenvolvimento substitui dinamicamente o `clienteId` conforme `BULBE_FRONTEND_CLIENTE_ID`.

## Validar

Na raiz do projeto:

```sh
(cd backend && ../.venv/bin/pytest -q)

.venv/bin/python integration-tests/check_preservation.py

.venv/bin/pip install playwright
.venv/bin/playwright install chromium

.venv/bin/python integration-tests/test_browser.py
```

Opcionalmente, para comparar visualmente a tela inicial com uma cópia local de referência do frontend original:

```sh
.venv/bin/python integration-tests/test_browser.py \
    --reference /caminho/Bulbe-Squad-cleanergy
```

O teste de navegador:

1. cria um SQLite em diretório temporário;
2. cria as tabelas usando os modelos da aplicação;
3. executa o seed fictício;
4. inicia Uvicorn somente em loopback;
5. executa Chromium através do Playwright;
6. utiliza HTTP real contra FastAPI;
7. verifica persistência diretamente no SQLite;
8. reinicia o backend para validar persistência;
9. encerra os processos quando termina.

Não utiliza mocks nem overrides de dependências.

Playwright continua sendo uma ferramenta de teste opcional e não foi adicionado ao `backend/requirements.txt`.

## Inventário da API implementada

O inventário abaixo corresponde aos controllers revisados.

| Método | Caminho | JWT exigido |
|---|---|---|
| POST | `/v1/auth/registrar` | Não |
| POST | `/v1/auth/login` | Não |
| GET | `/v1/auth/me` | Sim |
| GET | `/v1/usinas` | Não |
| POST | `/v1/usinas` | Sim |
| GET | `/v1/usinas/{usina_id}` | Não |
| PUT | `/v1/usinas/{usina_id}` | Sim |
| DELETE | `/v1/usinas/{usina_id}` | Sim |
| GET | `/v1/adesoes` | Não |
| POST | `/v1/adesoes` | Não |
| GET | `/v1/adesoes/{adesao_id}` | Não |
| PUT | `/v1/adesoes/{adesao_id}` | Sim |
| PATCH | `/v1/adesoes/{adesao_id}` | Sim |
| DELETE | `/v1/adesoes/{adesao_id}` | Sim |
| GET | `/v1/dicas` | Não |
| POST | `/v1/dicas` | Sim |
| GET | `/v1/dicas/{dica_id}` | Não |
| PUT | `/v1/dicas/{dica_id}` | Sim |
| DELETE | `/v1/dicas/{dica_id}` | Sim |
| POST | `/v1/simulacoes` | Não |
| POST | `/v1/indicacoes` | Não |
| GET | `/v1/indicacoes/{indicacao_id}` | Não |
| DELETE | `/v1/indicacoes/{indicacao_id}` | Sim |
| GET | `/v1/clientes/{cliente_id}/indicacoes` | Não |
| POST | `/v1/primeiro-acesso/verificacoes` | Não |
| POST | `/v1/primeiro-acesso/confirmacoes` | Não |
| GET | `/v1/clientes` | Não |
| POST | `/v1/clientes` | Não |
| GET | `/v1/clientes/{cliente_id}` | Não |
| PUT | `/v1/clientes/{cliente_id}` | Sim |
| DELETE | `/v1/clientes/{cliente_id}` | Sim |
| GET | `/v1/clientes/{cliente_id}/ativacao` | Não |
| PATCH | `/v1/clientes/{cliente_id}/ativacao` | Sim |
| GET | `/v1/clientes/{cliente_id}/ativacao/etapas` | Não |
| GET | `/v1/parceiros` | Não |
| POST | `/v1/parceiros` | Sim |
| GET | `/v1/parceiros/{parceiro_id}` | Não |
| PUT | `/v1/parceiros/{parceiro_id}` | Sim |
| DELETE | `/v1/parceiros/{parceiro_id}` | Sim |
| GET | `/v1/clientes/{cliente_id}/cupons` | Não |
| GET | `/v1/cupons/{cupom_id}` | Não |
| PATCH | `/v1/cupons/{cupom_id}` | Não |
| DELETE | `/v1/cupons/{cupom_id}` | Sim |
| GET | `/v1/clientes/{cliente_id}/clube` | Não |
| GET | `/v1/clientes/{cliente_id}/cartas` | Não |
| GET | `/v1/cartas/{carta_id}` | Não |
| POST | `/v1/cartas/{carta_id}/abertura` | Não |
| GET | `/v1/bandeiras` | Não |
| GET | `/v1/bandeiras/atual` | Não |
| GET | `/v1/bandeiras/{mes_referencia}` | Não |
| PUT | `/v1/bandeiras/{mes_referencia}` | Sim |
| GET | `/` | Não |

Além desses endpoints, FastAPI disponibiliza normalmente:

```text
/docs
/redoc
/openapi.json
```

## Estado das validações após a revisão

O código de testes foi atualizado para refletir os contratos atuais, incluindo:

- `/v1/simulacoes`;
- zero indicações como entrada válida;
- abertura idempotente de carta;
- persistência de cupom;
- cliente inexistente retornando erro real;
- JSON inválido;
- indisponibilidade do servidor;
- persistência após reinício;
- comparação opcional da tela inicial com o frontend original.

Os resultados históricos obtidos antes das alterações não devem ser tratados automaticamente como resultado do estado atual do código.

Antes de merge ou implantação, as validações devem ser executadas novamente:

```sh
(cd backend && ../.venv/bin/pytest -q)
.venv/bin/python integration-tests/check_preservation.py
.venv/bin/python integration-tests/test_browser.py
```

Somente após uma nova execução bem-sucedida devem ser registrados números como:

- quantidade de testes aprovados;
- quantidade de warnings;
- quantidade de arquivos preservados;
- resultado da comparação de screenshot;
- quantidade final de arquivos modificados/adicionados.

### Resultados observados (finalização, 15/11/2026)

Executados no Windows 11, Python 3.14, no ambiente único da raiz (`requirements.txt`), no estado final da branch `chore/finalizacao-projeto`:

| Validação | Resultado |
|---|---|
| `alembic upgrade head` + `alembic check` + `downgrade base` + `upgrade head` | sem diferenças entre modelos e migrations |
| `pytest` em `backend/` | 218 aprovados, 0 warnings (1 aviso de depreciação do `httpx` aparece no ambiente só do backend) |
| `pytest` em `sistema-de-gerenciamento/` | 198 aprovados |
| `integration-tests/check_preservation.py` | 72 arquivos originais idênticos; HTML só acrescenta `config.js` e `api.js` |
| `integration-tests/test_browser.py` (Playwright/Chromium) | 8 de 8 verificações aprovadas (inclui login pela tela Entrar, indicação e adesão pelas telas novas), em 4 execuções seguidas |
| `integration-tests/test_sistemas_integrados.py` | aprovado (sincronização app → painel e etapa painel → app) |
| `iniciar.py` + navegador | app e painel no ar juntos; etapa alterada na ficha do painel confirmada na API do app |

A comparação de screenshot com o frontend original (`--reference`) não foi executada, porque exige uma cópia local do repositório de origem.

## Preservação

`integration-tests/check_preservation.py` verifica:

- hashes SHA-256 dos CSS/assets originais;
- preservação do HTML original, descontando apenas os acréscimos declarados: as referências para `config.js`, `api.js`, `telas.css` e `telas.js` e o bloco `BULBE-TELAS-NOVAS` (cada um exatamente uma vez).

A verificação de "escopo preservado" (migrations e `sistema-de-gerenciamento` iguais ao commit base `86e8777`) valia só para esta revisão e foi retirada na finalização, quando essas pastas passaram a evoluir.

O `.gitattributes` desliga a conversão de quebra de linha em `frontend/`: com `core.autocrlf=true` (padrão no Windows) o checkout trocava LF por CRLF e o hash do `final.css` deixava de bater, mesmo sem alteração.

`backend/app/` não é tratado como intocado, pois contém alterações intencionais realizadas durante esta revisão.

O manifesto:

```text
integration-tests/frontend-source-sha256.json
```

continua sendo a referência para os hashes do frontend original.

## Atualizações da finalização

- **Banco:** migration `a3c9e1f4b2d7` (código de verificação com 6 caracteres, indicações com FK para o cliente, simulações com bandeira e economia, tabela `bandeiras_tarifarias`).
- **API:** `/v1/bandeiras` (RF-03), `PATCH /v1/adesoes/{id}` (US-07), `DELETE /v1/cupons/{id}` com token, indicações e simulações validando o cliente; `BULBE_SECRET_KEY` obrigatória com `BULBE_AMBIENTE=producao`.
- **Frontend:** os simuladores exibem a economia calculada pela API; o logado envia `cliente_id`. Telas novas Entrar, Primeiro acesso, Abrir conta e Indicações, com sessão do cliente no navegador.
- **Sistema de gerenciamento:** integrado ao app (veja [`sistema-de-gerenciamento/docs/integracao-com-o-app.md`](sistema-de-gerenciamento/docs/integracao-com-o-app.md)).
- **Execução:** `iniciar.py` na raiz sobe app e painel juntos; CI em `.github/workflows/testes.yml`.

## Próxima etapa

Merge e implantação continuam dependendo exclusivamente de revisão e decisão dos desenvolvedores responsáveis.
