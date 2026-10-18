# Notas para o líder — agente "chatbot"

1. **Handler de `ErroDeNegocio` em `app/main.py` (importante).**
   Hoje `main.py` importa `ErroDeNegocio` de `usina_service` e depois de `dica_service` com o mesmo nome; o segundo import
   sobrescreve o primeiro, então **os dois handlers ficam registrados para a classe de `dica_service`**. Como o chatbot
   levanta `app.services.usina_service.ErroDeNegocio` (conforme combinado), o 503 `CHATBOT_INDISPONIVEL` sairia como 500
   se isso não for corrigido. Sugestão: importar com alias e registrar um handler para cada classe
   (ou unificar as duas classes num módulo comum).

2. **[Resolvido] Faturas vencidas entre clientes.** O agente `db` criou `listar_faturas_vencidas(limite)` e o chatbot
   já a expõe como ferramenta. Vale registrar essa função na seção 1.6 do contrato (ela não está lá).
   Também tratados: `None` de `resumo_economia_cliente`/`listar_indicacoes` para cliente inexistente e `ValueError`
   de `simular_economia` (vira `tool_result` com `is_error: True`).

3. **Dependências.** O chatbot usa `anthropic` (obrigatório para o chat) e `python-dotenv` (opcional). Ambos já estão na
   lista da seção 5 do contrato. O `output_config={"effort": ...}` exige uma versão recente do SDK `anthropic`.

4. **Integração em `main.py`:** `from app.chatbot.controller import router as chatbot_router` e
   `app.include_router(chatbot_router)`. Variáveis novas para o `.env.example`: `CHATBOT_TIMEOUT` (opcional, default 60).

5. **Suposições sobre outras pastas** (seguindo o contrato):
   - `app.painel.auth.funcionario_logado` devolve `{id, nome, email, perfil}` com `id` inteiro (usado em `registrar_chat`).
   - `app.database.consultas.registrar_chat(funcionario_id=..., pergunta=..., resposta=..., ferramentas_usadas=...)`
     é chamado com argumentos nomeados, exatamente como na seção 1.6.
   - As consultas aceitam os parâmetros por nome (ex.: `listar_faturas(cliente_id=..., situacao=..., limite=...)`).
