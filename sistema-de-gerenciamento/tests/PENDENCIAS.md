# Pendências e suposições da suíte de testes

Pontos em que o contrato (`docs/CONTRATOS-MELHORIAS.md`) deixa margem e a suposição adotada nos testes.

1. **Banco temporário**: o contrato sugere `tmp_path_factory`, mas o engine é criado no import de
   `app.database.conexao`, antes de qualquer fixture existir. O `conftest.py` usa `tempfile.mkdtemp`
   no topo do arquivo e apaga a pasta no fim da sessão. Há travas que impedem o uso do banco real
   e que conferem, no fim, se `app/database/bulbe_ficticio.db` não foi modificado.
2. **`ANTHROPIC_API_KEY` vazia em vez de removida**: `main.py`, `conexao.py` e `chatbot/config.py` chamam
   `load_dotenv()`, que repõe variáveis ausentes a partir do `.env`. Com a variável definida como vazia,
   o `.env` local não consegue repor a chave real. O mesmo vale para as variáveis de SMTP.
3. **API da Anthropic simulada**: um cliente do SDK real, com transporte HTTP falso (`MockTransport` do
   pacote `httpx2`, que o SDK `anthropic` 1.15 usa no lugar de `httpx`), é injetado com
   `chatbot_service.definir_cliente(...)`. Os testes conferem os corpos JSON enviados à API.
   Uma fixture automática (`guarda_anthropic`) substitui `anthropic.Anthropic`/`AsyncAnthropic` em todos
   os testes e faz o teste falhar se houver tentativa de criar um cliente real.
4. **Erros da API → status da rota**: 429 → 429; 400 → 502; 503/529 e falha de conexão → 503.
   O 500 da API não é testado porque o contrato não define o mapeamento.
5. **Stream com erro**: a resposta do stream é sempre 200 e o último evento é `erro`. Sem chave
   da API, os testes aceitam tanto 503 HTTP quanto um evento `erro` com status 503.
6. **`ferramentas_usadas`**: os testes comparam o conjunto de nomes (sem exigir ordem nem nomes repetidos).
7. **Custo**: os testes usam volumes abaixo de 100 mil tokens por chamada. A implementação aplica uma
   tabela de "prompt longo" acima desse limite (US$ 0,50 / US$ 2,50 por milhão), que o contrato não
   prevê; acima do limite, o custo calculado é 5 vezes o da regra do contrato.
8. **Contexto da pergunta**: os testes exigem a data de hoje (dd/mm/aaaa, local ou UTC) e o primeiro nome
   do funcionário no texto da mensagem do usuário, e que a data não apareça no `system`.
9. **Conversa de outro funcionário no `POST /chat`**: o contrato só define o 404 do `GET /conversas/{id}`.
   Os testes aceitam 403 ou 404 e exigem que a API não seja chamada.
10. **Parâmetros de paginação inválidos nas rotas** (`por_pagina=101`, `pagina=0`): os testes aceitam
    422 ou valores normalizados para o intervalo válido.
