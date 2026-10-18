# Testes automatizados

> A v2 do sistema de gerenciamento ganhou uma suíte **pytest** (185 testes, contando os parametrizados) que
> cobre o banco, a segurança, as rotas do painel e o chatbot. Ela roda sem internet, sem chave da Anthropic, sem SMTP
> e sem tocar no banco fictício real.

## 1. Como rodar

Dentro da pasta `sistema-de-gerenciamento/`, com o ambiente virtual criado (ver [guia-do-painel.md](guia-do-painel.md#3-instalar-e-rodar)):

```bash
# dependências de desenvolvimento (inclui as de produção, pytest e httpx)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# a suíte inteira
.venv\Scripts\python.exe -m pytest
```

Variações úteis:

```bash
.venv\Scripts\python.exe -m pytest tests/test_login_bloqueio_alerta.py   # um arquivo
.venv\Scripts\python.exe -m pytest -k stream                            # testes cujo nome contém "stream"
.venv\Scripts\python.exe -m pytest -x                                   # para no primeiro erro
.venv\Scripts\python.exe -m pytest -v                                   # mostra o nome de cada teste
```

O `pytest.ini` aponta para a pasta `tests/` e usa saída resumida (`-q`). No Linux/macOS, troque
`.venv\Scripts\python.exe` por `.venv/bin/python`. Não é preciso subir o servidor nem ter `.env`: a suíte define o
próprio ambiente.

## 2. Organização da pasta `tests/`

| Arquivo | O que testa |
|---|---|
| `conftest.py` | Ambiente de teste e *fixtures* comuns (seção 3) |
| `apoio.py` | API da Anthropic simulada, SMTP simulado e utilitários para ler eventos SSE |
| `test_seguranca_senha_token.py` | Hash PBKDF2 e verificação de senha; token do painel (válido, adulterado, expirado, malformado); 401 sem token ou com token inválido; 403 em rota de admin para o perfil `atendimento` |
| `test_consultas.py` | Consultas de `app.database.consultas`: formatos (só tipos JSON), filtros, paginação (`data`, `pagina`, `por_pagina`, `total`, `total_paginas`, limites de 1 a 100), clientes parados, resumo de ativações, métricas (etapa 5 = ativados em 30 dias, bônus pagos) e bônus do Clube nas faturas e na economia |
| `test_conversas_auditoria_retencao.py` | Conversas **só de acréscimo** (mensagens antigas nunca mudam, conteúdo devolvido idêntico ao gravado, posse da conversa), registro de uso e custo, auditoria, contagem de falhas de login sem diferenciar maiúsculas e expurgo por retenção |
| `test_login_bloqueio_alerta.py` | Login com auditoria (`login_ok`, `login_falha`, `login_bloqueado`); bloqueio `429 LOGIN_BLOQUEADO` com `Retry-After` na 6ª tentativa, mesmo com a senha certa, também para e-mail inexistente, e desbloqueio quando a janela passa; alerta enviado **uma única vez** na 4ª falha, com SMTP simulado, sem a senha no texto; login que não quebra sem SMTP ou com erro de envio |
| `test_painel_rotas.py` | Rotas do painel: paginação e filtros de clientes, adesões, atendimentos e auditoria; rotas novas (clientes parados, resumo de ativações, uso do assistente, expurgo); admin × atendimento; registro de `ver_ficha`, `ver_auditoria` e `expurgo` |
| `test_chatbot.py` | Chatbot com a API simulada: loop de ferramentas, mascaramento de CPF e telefone, erros da API (429, 502, 503), soma de uso e custo, conversa persistida e reenviada **igual** na pergunta seguinte, prompt de sistema fixo com a data e o funcionário no texto da pergunta, modo antigo com `historico`, eventos do stream na ordem certa (`inicio` → `ferramenta`/`texto` → `fim`, ou `erro`) |

Cada arquivo começa com uma *docstring* que resume o que ele cobre. Testes que mexem no login usam um funcionário e um
e-mail próprios (fixture `criar_funcionario`), para as falhas de um teste não bloquearem o outro.

## 3. Como a suíte é isolada

O `tests/conftest.py` define as variáveis de ambiente **no topo do arquivo, antes de importar `app`**, porque o engine
do banco é criado no momento do import e vários módulos chamam `load_dotenv()`:

| O que faz | Por quê |
|---|---|
| Aponta `BULBE_DB_URL` para um SQLite numa pasta temporária, recria e popula com `popular_banco` uma vez por sessão e apaga a pasta no fim | O banco real `app/database/bulbe_ficticio.db` nunca é usado. Há travas: a suíte falha se o engine apontar para o banco real e confere, no fim, que ele não foi modificado |
| Define `PAINEL_SECRET` e `PAINEL_SENHA_DEMO` de teste | Tokens e logins previsíveis, sem depender do `.env` de quem roda |
| Define `ANTHROPIC_API_KEY` **vazia** (e não apagada) | Com a variável apagada, o `load_dotenv()` repõe a chave real do `.env` local; vazia, ele não repõe. Além disso, a fixture automática `guarda_anthropic` faz o teste falhar se alguém tentar criar um cliente real da Anthropic |
| Deixa as variáveis `SMTP_*` vazias | Nenhum e-mail sai; os testes de alerta usam a fixture `smtp_falso`/`configurar_smtp` |
| Fixa `LOGIN_*`, `CHAT_RETENCAO_DIAS` e `AUDITORIA_RETENCAO_DIAS` nos padrões | O `.env` local não altera o resultado dos testes |

**API da Anthropic simulada** (`apoio.py`): os testes usam o SDK `anthropic` de verdade (mesmas classes, erros e
acumulador de streaming), mas com um transporte HTTP falso que responde a `/v1/messages` a partir de um roteiro, em
JSON ou em SSE. O cliente é injetado com `chatbot_service.definir_cliente(...)` (fixture `api_anthropic`), e os corpos
enviados ficam registrados para o teste conferir, por exemplo, que o histórico reenviado é idêntico ao gravado e que o
`system` não muda entre perguntas.

Outras *fixtures*: `cliente_http` (`TestClient` sobre o `app` de `app/main.py`), `token_admin`/`token_atendimento`/
`token_ana` e os cabeçalhos `cab_admin`/`cab_atendimento`/`cab_ana`, `sem_chave_anthropic` e
`reiniciar_estado_em_memoria` (limpa, antes e depois de cada teste, o controle em memória dos alertas de login).

Os testes contam só com o que o seed garante: os totais (64 clientes, 16 em ativação...), os personagens fixos
(Marcos Andrade, `MARCOS50`, Clara Ribeiro, Renato Souza) e os funcionários de demonstração. Nomes e valores de
clientes sorteados podem mudar se o seed mudar.

## 4. Avaliação do chatbot com o modelo real (fora da suíte)

A suíte verifica o **código** com um modelo simulado. A qualidade das **respostas** do modelo real é medida à parte, em
`app/chatbot/avaliacoes/`:

- `casos.json` — 33 casos (dados de clientes, gestão da ativação, conhecimento do app, LGPD, limites, injeção de prompt,
  data de contexto), cada um com o que a resposta precisa conter e as ferramentas esperadas;
- `avaliar.py` — roda os casos contra a API real, pelo mesmo fluxo da rota de chat mas sem gravar conversa nem
  histórico, e imprime acertos, erros, tokens e custo estimado. Sai com código 0 se todos passaram, 1 se algum falhou
  e 2 se não foi possível rodar.

Como **gasta créditos**, `avaliar.py` não faz parte do `pytest` e só deve ser rodado de propósito, com
`ANTHROPIC_API_KEY` configurada:

```bash
.venv\Scripts\python.exe -m app.chatbot.avaliacoes.avaliar                          # todos os casos
.venv\Scripts\python.exe -m app.chatbot.avaliacoes.avaliar --categoria gestao-ativacao --detalhes
.venv\Scripts\python.exe -m app.chatbot.avaliacoes.avaliar --ids data-de-hoje --saida resultado.json
```

Os valores esperados valem para o seed com a semente 42 e o banco de `BULBE_DB_URL` (se ele não existir, é criado e
populado). Opções: `--casos`, `--ids`, `--categoria`, `--detalhes`, `--pausa` (segundos entre casos) e `--saida`.

## 5. Boas práticas ao mexer no sistema

- Rode a suíte inteira antes de abrir um *pull request*.
- Ao criar uma consulta, rota ou ferramenta, acrescente o teste correspondente no arquivo da área.
- Nunca coloque chave, senha ou dado real em teste: use os valores de teste do `conftest.py` e os dados fictícios do seed.
- Não dependa de dados sorteados pelo seed nem da hora exata; o seed gera datas relativas ao dia atual.
