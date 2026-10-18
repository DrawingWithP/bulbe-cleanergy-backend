# Pendências e suposições — app/chatbot (Melhorias v2)

Lacunas do contrato (`docs/CONTRATOS-MELHORIAS.md`, seção 2) e pontos que dependem de outras pastas.
Em cada caso foi seguida a suposição mais compatível com o contrato.

## Importante para testes e integração

1. **`.env` recoloca a `ANTHROPIC_API_KEY`.** `app/chatbot/config.py` e `app/main.py` chamam `load_dotenv(override=False)`.
   Um teste que faz `os.environ.pop("ANTHROPIC_API_KEY")` e depois importa o `app` volta a ter a chave do `.env` e
   **chama a API de verdade**. Nos testes: definir `ANTHROPIC_API_KEY=""` (vazio, não removido) antes de importar o `app`,
   e/ou injetar o cliente falso com `chatbot_service.definir_cliente(fake)`, e/ou substituir `config.obter_chave_api`.
   (Esse problema causou duas chamadas reais acidentais durante a validação desta entrega, em uma rota de teste com 503
   esperado: pergunta "Oi", cerca de US$ 0,0015 cada, sem gravação em banco.)
2. **Variáveis novas para o `.env.example`** (todas opcionais): `CHATBOT_MAX_MENSAGENS_CONVERSA` (200),
   `CHATBOT_PRECO_ENTRADA_MTOK` (0.10), `CHATBOT_PRECO_SAIDA_MTOK` (0.50), `CHATBOT_FATOR_CACHE_LEITURA` (0.1),
   `CHATBOT_FATOR_CACHE_ESCRITA` (1.25), `CHATBOT_LIMITE_PROMPT_LONGO` (100000), `CHATBOT_PRECO_ENTRADA_LONGO_MTOK` (0.50),
   `CHATBOT_PRECO_SAIDA_LONGO_MTOK` (2.50).
3. **Códigos de erro novos** (não estão no contrato): 404 `CONVERSA_NAO_ENCONTRADA`, 503 `CHATBOT_HISTORICO_INDISPONIVEL`,
   409 `CONVERSA_MUITO_LONGA` (a interface pode sugerir "Nova conversa") e, só no evento `erro` do stream,
   500 `CHATBOT_ERRO_INTERNO`.

## Suposições sobre `app/database`

4. Programado contra as assinaturas da seção 1.2: `criar_conversa(funcionario_id, titulo) -> {id, ...}`,
   `obter_conversa(conversa_id, funcionario_id) -> {..., mensagens: [{ordem, papel, conteudo, texto, criado_em}]} | None`,
   `adicionar_mensagens(conversa_id, [{papel, conteudo, texto}])`, `listar_conversas(funcionario_id, limite=)`,
   `registrar_chat(..., conversa_id=, modelo=, uso=, duracao_ms=)`, `buscar_clientes(..., etapa=)`,
   `listar_clientes_parados(etapa=, dias_minimos=, limite=)` e `resumo_ativacoes()`. As consultas são chamadas por nome
   (`consultas.<funcao>`) na hora do uso, então o módulo importa mesmo antes de elas existirem.
5. `adicionar_mensagens` recebe numa só chamada o turno inteiro (e, no modo antigo, também o histórico de texto convertido).
   Supõe-se que grave tudo numa transação; se falhar, o erro é logado e a resposta é devolvida assim mesmo.
6. `registrar_chat` com a assinatura antiga (sem os campos novos) levanta `TypeError`; nesse caso o chat registra no formato
   da v1 (sem uso/custo) e loga um aviso.
7. O `etapa` aceita 1–5 nas ferramentas (o contrato não limita); `listar_clientes_parados` e `resumo_ativacoes` só devem
   trazer etapas 1–4 (clientes `em_ativacao`).

## Comportamentos a combinar com `app/painel`

8. A conversa é criada **antes** da chamada à API (o evento `inicio` já traz o `conversa_id`). Se a primeira pergunta falhar,
   fica uma conversa vazia (`total_mensagens = 0`); a interface pode reaproveitá-la na nova tentativa ou ocultá-la.
9. No stream, o texto definitivo é o `resposta` do evento `fim` (em recusa, ele substitui o texto parcial que já chegou).
   Entre voltas diferentes chega um `delta` `"\n\n"`. O aviso de resposta cortada (`max_tokens`) chega como último `delta`.
10. Se o cliente fechar a conexão no meio do stream, o turno **não** é gravado nem registrado (o custo daquela pergunta
    parcial não entra em `metricas_uso_chatbot`). Gravar um turno pela metade deixaria o histórico inválido.
11. `resposta` agora junta o texto de todas as voltas (antes, só o da última), igual ao que aparece no stream.
12. No limite de 8 voltas, a conversa termina com uma mensagem de `tool_result`; o texto visível ("Não consegui concluir...")
    fica na última mensagem do assistente e a próxima pergunta é aceita normalmente (a API junta as mensagens do usuário).

## Riscos conhecidos

13. **Mudança de prompt/ferramentas entre versões**: conversas antigas passam a ter blocos `thinking` com assinatura de outro
    prefixo. Em contas sujeitas à verificação, a API responde 400; o chat reenvia a pergunta uma vez sem os blocos
    `thinking` (uma requisição recusada a mais por pergunta nessas conversas). Alternativa futura: beta
    `thinking-binding-controls-2026-08-01` com `prefix_mismatch_behavior: "drop_block"`.
14. `avaliar.py` chama `inicializar_banco()` (como o servidor faz ao subir): se o banco não existir ou estiver vazio, ele é
    criado e populado. Os valores esperados em `casos.json` valem para o seed com semente 42 (ex.: 16 clientes em ativação,
    Marcos Andrade na etapa 2, usina Paracatu em manutenção); ajuste os casos se o seed mudar.
