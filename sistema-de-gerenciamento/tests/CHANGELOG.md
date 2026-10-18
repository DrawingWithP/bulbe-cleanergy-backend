# CHANGELOG — testes

## Melhorias (v2)

- Suíte `pytest` criada para todo o sistema (183 testes). Ela roda com `.venv\Scripts\python.exe -m pytest`.
- `conftest.py`: define o ambiente antes de importar `app` (SQLite temporário, segredo e senha de teste,
  sem chave da Anthropic e sem SMTP), popula o banco uma vez por sessão e oferece fixtures de cliente HTTP,
  tokens de admin e de atendimento, fábrica de funcionários isolados, API da Anthropic simulada e SMTP simulado.
- `apoio.py`: implementa a API da Anthropic simulada sobre o SDK real (transporte HTTP falso, respostas
  JSON e SSE), o SMTP simulado e utilitários de leitura de eventos SSE.
- Arquivos por área: `test_seguranca_senha_token.py`, `test_consultas.py`,
  `test_conversas_auditoria_retencao.py`, `test_painel_rotas.py`, `test_login_bloqueio_alerta.py`
  e `test_chatbot.py`.
- Nenhum teste acessa a rede, chama a API da Anthropic ou envia e-mail. O banco real não é tocado.
- Suposições sobre pontos em aberto do contrato: `PENDENCIAS.md`.
