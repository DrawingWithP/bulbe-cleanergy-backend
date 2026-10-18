# Pendências e suposições — `docs/` (v2)

Pontos encontrados ao documentar a v2. Em cada um, a documentação segue o **código implementado**; o que depende de
arquivos fora de `docs/` fica registrado aqui.

## Para a integração (arquivos fora de `docs/`)

1. **`README.md` da pasta `sistema-de-gerenciamento/`** ainda descreve a v1: "Modelos (17 tabelas)" (agora são 20),
   a rota do chatbot só como `/v1/painel/chat` (faltam `/chat/stream` e `/chat/conversas`), não cita `tests/`,
   `requirements-dev.txt`, `pytest.ini` nem a recriação do banco depois da atualização. Sugestão: espelhar o resumo da v2
   de [docs/README.md](README.md) e o comando de testes. O parágrafo "Uso de IA no desenvolvimento" deve ficar como está.
2. **`app/main.py`** declara `version="1.0.0"` no `FastAPI`. Sugestão: `2.0.0`, para o Swagger refletir a v2.
3. **`.env.example`** traz o valor padrão de `PAINEL_SENHA_DEMO` (pendência já registrada na v1). Sugestão: deixar vazio,
   já que o seed tem um padrão. A documentação desta pasta não escreve senhas nem chaves.
4. **Arquivos `NOTAS_PARA_O_LIDER.md`** (da v1) continuam em `docs/` e nas pastas `app/*`. O índice os descreve como
   registro da v1; a v2 usa `PENDENCIAS.md`. Se a squad preferir, os antigos podem ser renomeados ou removidos na integração.

## Diferenças entre o contrato e o implementado (documentadas como implementado)

5. **Códigos de erro fora do contrato:** `CONVERSA_NAO_ENCONTRADA` (404), `CONVERSA_MUITO_LONGA` (409),
   `CHATBOT_HISTORICO_INDISPONIVEL` (503) e `CHATBOT_ERRO_INTERNO` (500, só no evento `erro` do stream).
   Estão em `arquitetura.md` e `guia-do-painel.md`.
6. **Preço de prompt longo:** além dos preços do contrato, `app/chatbot/config.py` aplica uma tabela de prompt longo
   acima de 100 mil tokens de entrada por chamada (US$ 0,50 / US$ 2,50 por milhão). Documentado em `arquitetura.md` §5.
7. **Variáveis novas do `.env` não previstas no contrato:** `CHATBOT_MAX_MENSAGENS_CONVERSA` e as sete variáveis de preço
   (`CHATBOT_PRECO_*`, `CHATBOT_FATOR_CACHE_*`, `CHATBOT_LIMITE_PROMPT_LONGO`). Já estão no `.env.example` e no guia.
8. **`Retry-After` do 429** usa a janela inteira (900 s com o padrão), e não o tempo exato até a falha mais antiga
   sair da janela. A mensagem "Tente de novo em N minutos" usa esse mesmo valor.
9. **Resposta do expurgo manual:** as contagens de `expurgar_dados_antigos` mais `dias_chat` e `dias_auditoria`
   (o contrato não fixava o formato).
10. **Parâmetros extras aceitos:** `limite` como sinônimo de `por_pagina` em `/clientes`; `cliente_id` em `/atendimentos`;
    `limite` em `/chat/conversas`.
11. **Volume de auditoria do seed:** o contrato fala em ~120 registros; o seed gera cerca de 125. A documentação usa ~125.
12. **Banco da v1:** além da recriação prevista no contrato, `inicializar_banco()` acrescenta as colunas que faltarem num
    banco antigo. A documentação mantém `python -m app.database.seed` como o caminho recomendado.

## Não verificado

13. A interface não foi aberta no navegador nesta etapa (regra da v2: sem subir o servidor). As telas descritas em
    `guia-do-painel.md` seguem `painel.html`/`painel.js`; convém conferir textos e rótulos depois da integração.
14. ~~Contagem de testes~~ — resolvido: a suíte foi executada na integração e tem 185 testes, todos passando.
