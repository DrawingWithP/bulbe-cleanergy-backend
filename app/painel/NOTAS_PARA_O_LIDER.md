# Notas para o líder — agente `painel`

1. **Formato do erro com `HTTPException`.** O contrato pede `HTTPException` com
   `detail={"error": {...}}`. O FastAPI devolve isso como `{"detail": {"error": {...}}}`, e não como
   `{"error": {...}}` puro. A interface (`painel.js`/`login.js`) aceita os dois formatos, mas para seguir
   o padrão do projeto sugiro registrar em `app/main.py`:

   ```python
   from fastapi import HTTPException
   from fastapi.exception_handlers import http_exception_handler

   @app.exception_handler(HTTPException)
   async def tratar_http_exception(request: Request, exc: HTTPException):
       if isinstance(exc.detail, dict) and "error" in exc.detail:
           return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
       return await http_exception_handler(request, exc)
   ```
   (Vale também para o 401/403 de `auth.py` e para o 503 do chatbot.) Use `starlette.exceptions.HTTPException`
   se quiser cobrir também os 404 de rota inexistente.

2. **Montagem dos estáticos.** A interface usa caminhos absolutos `/painel/...` e `/v1/painel/...`.
   Montar com `StaticFiles(directory=<app/painel/static>, html=True)` em `/painel` (como no contrato).
   Arquivos extras além dos listados: `login.js` (script do login, para não ter JS inline por causa da CSP)
   e `logo-bulbe.svg` (cópia do `icons_final/bulbe.svg` do front).

3. **Sem limite de tentativas de login.** Não implementei rate limit / bloqueio por tentativas
   (fora do escopo do contrato). Recomendável antes de qualquer uso fora do ambiente local.

4. **`PAINEL_SECRET`.** Sem a variável, o token é assinado com um segredo de desenvolvimento público
   (há `logging.warning`). Incluir no `.env.example` (já previsto na seção 5 do contrato).

5. **Campos de `listar_atendimentos` sem cliente.** O contrato não diz se cada atendimento traz o nome
   do cliente. A tela de Atendimentos procura `cliente_nome`, `nome_cliente` ou `cliente.nome`; se nada vier,
   mostra o link "Ver ficha" pelo `cliente_id`. Se o agente `db` incluir `cliente_nome`, a tabela fica melhor.

6. **`id` do funcionário como `int`.** O modelo de resposta do login/`/me` (`FuncionarioPublico`) declara
   `id: int`, conforme `obter_funcionario(funcionario_id: int)` no contrato.
