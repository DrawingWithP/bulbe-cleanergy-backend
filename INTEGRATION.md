# Integração frontend–backend para revisão humana

## Escopo e origem

Frontend: `gabrielmercedo/Bulbe-Squad-cleanergy`, commit `fb18142214f16b5528ac1defd1ecbb42659ed62e`.

Backend: `DrawingWithP/bulbe-cleanergy-backend`, base originalmente utilizada `86e8777040bb7733e13d3c325c5bd2c3de49d099`.

O frontend original não possui arquivo de licença. A cópia de código e assets para este destino foi expressamente autorizada pelo solicitante, que confirmou ter autorização dos responsáveis. Essa confirmação não cria uma licença pública nem transfere direitos sobre marcas ou assets de terceiros. A autoria original permanece com a equipe Cleanergy identificada no repositório de origem.

A entrada integrada é `frontend/final.html`. Foram copiados os arquivos da aplicação consolidada e seus assets, preservando os caminhos necessários.

As páginas, CSS e scripts independentes em `screens/` não foram duplicados quando não eram necessários para a aplicação consolidada. Os assets utilizados pelo frontend integrado foram preservados.

Documentos, slides, caches, segredos e dados de produção não fazem parte da integração.

Durante a revisão, arquivos em `backend/app/` foram atualizados intencionalmente para padronização, correção de contratos, validações e compatibilidade entre frontend e backend.

As migrations existentes e `sistema-de-gerenciamento/` permanecem fora do escopo dessas alterações.

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
| Simuladores aberto e logado | `POST /v1/simulacoes` | Persiste `valor_atual`, `valor_proposto`, `periodo_meses` e `indicacoes` |

O backend de simulações valida e persiste os valores recebidos. O cálculo visual de economia continua sendo realizado pelo frontend existente.

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

As operações de carta e cupom consumidas diretamente pelo frontend permanecem de acordo com o contrato público utilizado pela integração atual. Isso não representa uma política adequada de autorização para uma aplicação de consumidor final em produção.

## Incompatibilidades e limites mantidos

### Login do aplicativo

O botão Entrar do frontend original apenas navega para outra tela.

Não existem campos de e-mail e senha no frontend recebido.

Também não existe atualmente vínculo entre o usuário retornado por `/v1/auth/me` e um cliente de `/v1/clientes`.

Não foi criada autenticação fictícia para ocultar essa incompatibilidade.

### Primeiro acesso, adesão e indicações

A API possui endpoints para primeiro acesso, adesões e indicações.

Entretanto, os destinos correspondentes do frontend consolidado não possuem os formulários necessários para executar essas jornadas completas.

Criar novas telas ou solicitar novos campos modificaria o escopo visual recebido.

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
| DELETE | `/v1/cupons/{cupom_id}` | Não |
| GET | `/v1/clientes/{cliente_id}/clube` | Não |
| GET | `/v1/clientes/{cliente_id}/cartas` | Não |
| GET | `/v1/cartas/{carta_id}` | Não |
| POST | `/v1/cartas/{carta_id}/abertura` | Não |
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

Até essa nova execução, este documento não afirma aprovação do estado final revisado.

## Preservação

`integration-tests/check_preservation.py` verifica:

- hashes SHA-256 dos CSS/assets originais;
- preservação do HTML original, descontando apenas as referências explicitamente adicionadas para `config.js` e `api.js`;
- ausência de mudanças no escopo configurado como preservado, incluindo migrations e `sistema-de-gerenciamento`.

`backend/app/` não é tratado como intocado, pois contém alterações intencionais realizadas durante esta revisão.

O manifesto:

```text
integration-tests/frontend-source-sha256.json
```

continua sendo a referência para os hashes do frontend original.

## Próxima etapa

Executar a suíte completa de testes no estado final do repositório.

Após a execução, atualizar somente a seção de resultados deste documento com os valores realmente observados.

Merge e implantação continuam dependendo exclusivamente de revisão e decisão dos desenvolvedores responsáveis.
