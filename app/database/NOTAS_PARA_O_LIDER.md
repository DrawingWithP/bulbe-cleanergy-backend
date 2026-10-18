# Notas para o líder — agente `db`

1. **Assinatura × regra de "não encontrado" (contrato 1.6).** `resumo_economia_cliente` e `listar_indicacoes`
   aparecem como `-> dict`, mas a regra geral diz "cliente inexistente: devolver None". Segui a regra geral:
   as duas devolvem `None` quando o cliente não existe (anotação `dict | None`). Os agentes `chatbot`
   e `painel` devem tratar esse `None`.
2. **`simular_economia` com entrada inválida** (valor ≤ 0, meses fora de 1..60, amigos < 0) levanta `ValueError`
   com mensagem em português. O chatbot deve capturar a exceção e devolver `is_error: True`.
3. **Campos a mais (só acréscimos, nada foi removido):** `listar_atendimentos` traz `cliente_nome` (seu pedido),
   `listar_usinas` traz `clientes_ativos`, `listar_faturas` traz `cliente_id`, e existe a função nova
   `listar_faturas_vencidas` (seu pedido). Vale registrar no contrato e avisar o agente `chatbot` caso ele queira expor isso como ferramenta.
4. **`ativacao_por_etapa`** conta só os clientes `em_ativacao` (que ficam nas etapas 1–4). A chave `"5"` existe, mas costuma valer 0.
5. **Texto da observação do simulador:** `docs/Lista_de_endpoints.md` diz "não incide sobre o frete e a taxa de
   iluminação pública", enquanto o contrato 1.4 diz "iluminação pública e PIS/COFINS". Usei o texto do contrato.
6. **Integração (`app/main.py`):** `inicializar_banco()` no startup. O `conexao.py` já tenta `load_dotenv()`
   (se o python-dotenv estiver instalado) antes de ler `BULBE_DB_URL`. Mesmo assim, carregar o `.env` no início
   do `main.py` garante que `PAINEL_SENHA_DEMO` e as demais variáveis estejam disponíveis.
7. **`.gitignore`:** incluir `app/database/*.db` (ou `*.db`).
8. **Bônus especial do Clube × faturas:** a carta especial aberta gera o cupom `usado` "R$ 50 de desconto na fatura",
   mas `faturas` não tem coluna para esse bônus, então ele não entra no `valor_total`. Se quiserem essa coerência,
   uma coluna `bonus_clube` em `faturas` (mudança de contrato) resolveria.
9. **`obter_ativacao`** agora tem o campo `status_cliente`. Para clientes cancelados, nenhuma etapa vem como `atual`
   (a etapa onde o processo parou vem como `pendente`). Vale avisar o agente `painel` para a timeline.
10. Não gerei o `.db` e não rodei o seed (regra da squad). Só passei o `py_compile`. Recomendo rodar
   `python -m app.database.seed` uma vez depois do `pip install`, para validar em execução.
