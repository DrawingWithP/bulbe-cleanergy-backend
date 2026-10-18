# Pendências e suposições — `app/painel/` (v2)

1. **`funcionario_id` no `login_falha` de e-mail existente.** O contrato pede `funcionario_id` nulo só para e-mail
   inexistente, mas não define uma consulta "funcionário por e-mail" em `app/database/consultas.py`.
   Suposição: o painel usa `consultas.obter_funcionario_por_email(email)` se ela existir e, enquanto não existe,
   faz uma leitura simples (`select(Funcionario.id)` com `obter_sessao`). Sugestão: criar essa consulta na camada de banco.

2. **Resposta de `POST /v1/painel/admin/expurgo`.** O contrato não fixa o formato. Suposição: as contagens de
   `expurgar_dados_antigos` no nível de cima + os prazos usados:
   `{chat_historico, chat_conversas, chat_mensagens, auditoria, dias_chat, dias_auditoria}`.

3. **`Retry-After` do 429.** `contar_falhas_login` devolve só a contagem, sem os horários. O cabeçalho usa a janela
   inteira (`LOGIN_JANELA_MINUTOS * 60`), que é o limite superior e garante o desbloqueio. Para um valor exato seria
   preciso uma consulta com o horário da falha mais antiga da janela.

4. **Compatibilidade das listas.** `/clientes`, `/adesoes` e `/atendimentos` passaram a devolver o objeto paginado
   (mudança prevista no contrato). O parâmetro `limite` da v1 continua aceito como sinônimo de `por_pagina`.
   `/atendimentos` aceita também `cliente_id` (opcional, não previsto na tabela 3.2).

5. **IP atrás de proxy.** O IP auditado é `request.client.host`. Atrás de proxy reverso será o IP do proxy, a menos que o
   uvicorn rode com `--proxy-headers` e `--forwarded-allow-ips` (decisão de implantação).

6. **Vários processos.** A reserva "1 alerta por janela" em memória vale por processo; com vários workers a consulta à
   auditoria reduz, mas não elimina, a chance de dois alertas simultâneos para o mesmo e-mail.

7. **SMTP só com STARTTLS.** Conforme o contrato (porta 587 + `SMTP_TLS`). SMTPS na porta 465 (`SMTP_SSL`) não é suportado.

8. **`ver_auditoria` a cada consulta.** Cada página/filtro da tela Auditoria grava um `ver_auditoria` (o contrato pede o
   registro na rota). Isso gera volume na própria auditoria; pode-se, no futuro, registrar só a primeira página.

9. **Interface não verificada no navegador.** As regras desta etapa não permitem subir o servidor; a interface foi
   validada por `node --check`, teste do leitor de SSE e revisão. Conferir as telas novas, o streaming e a paginação após a
   integração.

10. **`NOTAS_PARA_O_LIDER.md` (v1).** Os itens 1 (handler de `detail.error`, já no `app/main.py`) e 3 (limite de tentativas
    de login) foram resolvidos na v2.
