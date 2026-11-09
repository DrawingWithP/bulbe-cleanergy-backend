# Integração frontend–backend para revisão humana

## Escopo e origem

Frontend: `gabrielmercedo/Bulbe-Squad-cleanergy`, commit `fb18142214f16b5528ac1defd1ecbb42659ed62e`.
Backend: `DrawingWithP/bulbe-cleanergy-backend`, base `86e8777040bb7733e13d3c325c5bd2c3de49d099`.

O frontend original não possui arquivo de licença. A cópia de código e assets para este destino foi expressamente autorizada pelo solicitante, que confirmou ter autorização dos responsáveis. Essa confirmação não cria uma licença pública nem transfere direitos sobre marcas ou assets de terceiros. A autoria original permanece com a equipe Cleanergy identificada no repositório de origem.

A entrada integrada é `frontend/final.html`. Foram copiados os arquivos dessa aplicação consolidada e seus assets, preservando os caminhos originais. As páginas, CSS e scripts independentes em `screens/` não foram duplicados: apenas seus assets, utilizados pela aplicação consolidada. Documentos, slides, caches, dependências e segredos não foram importados.

Nenhum arquivo preexistente do backend foi alterado. `backend/app/`, banco/schema/migrations e `sistema-de-gerenciamento/` permanecem intactos. `backend/dev_frontend.py` é uma entrada opcional para desenvolvimento; a entrada existente `app.main:app` mantém seu comportamento. Não há mudança de produção, merge, deploy ou auto-merge.

## Funcionalidades conectadas

| Interface existente | Contrato real | Comunicação |
|---|---|---|
| Conexão e detalhes | `GET /v1/clientes/{id}/ativacao` e `/ativacao/etapas` | Percentual, etapa, títulos e descrições retornados pela API |
| Dicas e carrossel | `GET /v1/dicas` | Títulos, descrições, SVG como imagem e economia; mesmas classes HTML |
| Vantagens | `GET /v1/clientes/{id}/clube`, `/cartas`, `/cupons` | Disponibilidade, sequência, próxima data e histórico; paginação completa |
| Parceiros do clube | `GET /v1/parceiros` | Catálogo ativo com os assets originais conhecidos; sem executar HTML da API |
| Abrir carta | `POST /v1/cartas/{id}/abertura` | Cupom real; bloqueio de clique concorrente; erro sem recompensa simulada |
| Selecionar/resgatar cupom | `GET /v1/cupons/{id}`, `PATCH /v1/cupons/{id}` | Reutiliza tela de recompensa; Resgatar envia `situacao=salvo` |
| Controle Usar do overlay existente | `PATCH /v1/cupons/{id}` | Envia `situacao=usado`; não representa uma compra ou pagamento |
| Simuladores aberto e logado | `POST /v1/simulacaos` | JSON `valor_atual`, `valor_proposto`, `periodo_meses`, `indicacoes`; resultado somente após resposta válida e persistida |

O backend da simulação apenas valida e persiste os valores; não calcula a economia. A aritmética existente do frontend foi mantida. Os controles disparam uma gravação por alteração estabilizada (debounce de 350 ms). Respostas antigas são descartadas na apresentação, mas a API não oferece chave de idempotência para essas gravações.

Erros de rede/timeout, JSON inválido, `detail` do FastAPI e `error.message` de negócio são exibidos por alertas nativos, preservando HTML/CSS. Sem retries automáticos de escrita. Dados dinâmicos usam `textContent` ou escape nos templates existentes. O SVG de dica é carregado como imagem, sem inserção de markup executável. A interface continua com o mesmo layout e assets; o conteúdo de dados passa a refletir a API.

## Incompatibilidades e limites mantidos

- **Login:** o botão Entrar original apenas navega; não existem campos de email/senha. `/v1/auth/login` autentica operadores (`application/x-www-form-urlencoded`: `username`, `password`), e `/v1/auth/me` retorna um usuário sem `cliente_id`. Não foi criado vínculo, formulário ou autenticação fictícia. A integração local exige um cliente de teste explicitamente configurado. Esse ID é contexto de demonstração, nunca credencial ou autorização de acesso. Esta entrada local não constitui uma aplicação pronta para produção.
- **Primeiro acesso, adesão e indicações:** os botões apontam para `screen-primeiro-acesso`, `screen-abrir-conta` e `screen-indicacoes`, ausentes na aplicação consolidada; não existem formulários correspondentes no frontend recebido. A API tem endpoints, mas criar telas ou recolher campos novos ampliaria o escopo. A navegação para esses destinos informa a ausência.
- **Zero indicações:** permitido pelo protótipo, rejeitado por `SimulacaoCreate.indicacoes > 0` com 422. A tela mostra o erro e não exibe sucesso local. Nenhum valor foi falsificado para contornar a validação.
- **Ativação etapa 1:** a API oferece cinco etapas, mas o status original só tem representações visuais dos círculos/cards das etapas 2–5. O número/percentual e os detalhes aceitam etapa 1; não foi criado um novo card ou desenho.
- **Controles de demonstração:** avançar/voltar etapas, passar/voltar dias e resetar clube não representam ações de cliente com contratos equivalentes. Os controles preservados não alteram dados e informam a limitação. Não foi exposto PATCH de ativação por esses botões.
- **Bônus especial:** a API decide disponibilidade/tipo de carta e o cupom gerado. Seu serviço atual gera recompensa Livelo; não foi implementado o bônus financeiro fictício do protótipo.
- **Compartilhar, WhatsApp, notificações, perfil, mudança de endereço, termos, FAQ externo e contato:** comportamento original preservado; não há contrato correspondente na interface recebida. Copiar código continua sendo ação local do navegador, sem mudar situação do cupom.
- **Próxima carta e validade:** valores seguem a resposta atual do backend, inclusive suas limitações de agenda e `dias_restantes`; não foram corrigidas regras de negócio.
- **Autorização de clientes:** vários endpoints existentes de cliente/clube não exigem JWT. Não foi enfraquecida nem ampliada sua política; a ausência de vínculo usuário–cliente impede homologar uma jornada autenticada de consumidor final.
- **Produção/PostgreSQL/SMS/WhatsApp/parceiros reais:** não exercitados. Testes usam apenas seed fictício e SQLite temporário. Não foram feitos contatos, envios, transações ou mudanças em serviços externos.

## Executar localmente

Python 3.10 ou superior (validado com 3.12). Exemplo para um banco novo e exclusivamente local:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
export BULBE_DATABASE_URL="sqlite:////tmp/bulbe-integracao-local.db"
export BULBE_SECRET_KEY="chave-exclusiva-de-desenvolvimento-local"
export BULBE_FRONTEND_CLIENTE_ID="8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11"
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.db.seed
../.venv/bin/uvicorn dev_frontend:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/frontend/final.html`; Swagger em `/docs`. Os comandos usam apenas migrations existentes em um SQLite local novo; não executar em produção. O seed fornece dados fictícios e o operador de demonstração documentado no backend.

`config.js` é servido dinamicamente pela entrada local, com `Cache-Control: no-store`, sem segredos. Frontend/API usam a mesma origem. Não foi necessário adicionar CORS. O arquivo estático `frontend/config.js` deixa o cliente vazio por padrão; mudar `apiBase` para outra origem exige política CORS deliberada do mantenedor e não é a configuração validada.

## Validar

```sh
# Na raiz, com o venv acima
(cd backend && ../.venv/bin/pytest -q)
.venv/bin/python integration-tests/check_preservation.py
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python integration-tests/test_browser.py
# Opcional: referência original local, somente leitura, para comparação de screenshot
.venv/bin/python integration-tests/test_browser.py --reference /caminho/Bulbe-Squad-cleanergy
```

O teste de navegador cria seu próprio SQLite em diretório temporário, instancia os modelos existentes apenas nesse banco, popula o seed fictício, inicia Uvicorn em loopback e encerra os processos ao terminar. Não usa mocks, overrides de dependência nem dados de produção. Playwright é ferramenta de teste opcional; não foi acrescentado às dependências da aplicação.

Resultados e inventário completo de endpoints: seções abaixo. Merge e implantação dependem exclusivamente da revisão e decisão dos desenvolvedores responsáveis.

## Inventário da API implementada

Obtido do OpenAPI gerado por `app.main:app` na base inspecionada. Inclui endpoints administrativos sem interface correspondente; não foram criados controles novos.

| Método | Caminho | JWT exigido pelo contrato |
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
| POST | `/v1/simulacaos` | Não |
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
| PATCH | `/v1/clientes/{cliente_id}/ativacao` | Não |
| GET | `/v1/clientes/{cliente_id}/ativacao/etapas` | Não |
| GET | `/v1/parceiros` | Não |
| POST | `/v1/parceiros` | Não |
| GET | `/v1/parceiros/{parceiro_id}` | Não |
| PUT | `/v1/parceiros/{parceiro_id}` | Não |
| DELETE | `/v1/parceiros/{parceiro_id}` | Não |
| GET | `/v1/clientes/{cliente_id}/cupons` | Não |
| GET | `/v1/cupons/{cupom_id}` | Não |
| PATCH | `/v1/cupons/{cupom_id}` | Não |
| DELETE | `/v1/cupons/{cupom_id}` | Não |
| GET | `/v1/clientes/{cliente_id}/clube` | Não |
| GET | `/v1/clientes/{cliente_id}/cartas` | Não |
| GET | `/v1/cartas/{carta_id}` | Não |
| POST | `/v1/cartas/{carta_id}/abertura` | Não |
| GET | `/` | Não |

Total: 47 operações, além de `/docs`, `/redoc` e `/openapi.json` do FastAPI. O inventário reflete os contratos efetivos, inclusive a grafia `/v1/simulacaos`.

## Resultados da validação — 9 de novembro de 2026

- **Backend:** 66 testes existentes aprovados em Python 3.12; 12 avisos de depreciação das bibliotecas/modelos preexistentes, sem falhas finais.
- **Chromium / API real / SQLite descartável:** aprovados carregamento, autenticação de operador 200/401, status/detalhes, dicas/carrossel, parceiros, abertura de carta, resgate/salvamento e seleção de cupom, cópia local, recarregamento e idempotência da abertura.
- **Simuladores:** aprovados os dois fluxos com indicação válida, troca de período e período personalizado; 422 real com zero indicações, sem exibir sucesso local.
- **Erros e persistência:** aprovados cliente inexistente/404, JSON inválido, indisponibilidade real após encerrar o servidor, gravações consultadas diretamente no SQLite e persistência do cupom após reiniciar o processo do backend. Requisições `/v1/` na mesma origem, sem erros JavaScript ou de CORS nas jornadas testadas.
- **Preservação:** 72 arquivos originais de CSS/assets idênticos por SHA-256; o HTML só acrescenta duas referências de scripts; screenshot da tela inicial de 430×932 idêntica pixel a pixel ao original. Dados dinâmicos em outras telas mudam conforme a API; não se afirma igualdade de screenshots entre dados diferentes.
- **Escopo:** 81 arquivos adicionados no destino, nenhum arquivo preexistente modificado. `git diff --cached --check` aprovado. Sem dependências novas de runtime.
- **Execuções interrompidas:** a primeira tentativa com Python 3.9 parou por incompatibilidade com a sintaxe preexistente; leituras de arquivos/caches em Documents também impediram tentativas intermediárias. Validação final executada integralmente em `/tmp` com Python 3.12. Não houve alteração do produto para contornar esses problemas de ambiente.
- **Não validados:** jornada autenticada de consumidor, telas ausentes de primeiro acesso/adesão/indicações, integrações externas reais, PostgreSQL e produção, pelas limitações descritas acima. Não há resultados simulados substituindo essas validações.

Arquivos acrescentados: `backend/dev_frontend.py`, `frontend/final.html`, `frontend/final.js`, `frontend/api.js`, `frontend/config.js`, `INTEGRATION.md`, os três arquivos em `integration-tests/` e os 72 arquivos originais de CSS/assets listados individualmente em `integration-tests/frontend-source-sha256.json`.
