# Pendências e suposições — `app/database/` (v2)

Pontos em que `docs/CONTRATOS-MELHORIAS.md` (seção 1) não era explícito. Em cada um, segui a opção mais compatível com o contrato.

1. **Escritas com entrada inválida levantam `ValueError`.** O contrato não diz como `criar_conversa`, `adicionar_mensagens` e `registrar_auditoria` reagem a uma entrada inválida (a regra de "nunca levantar exceção" vale para as consultas de leitura). Por isso:
   - `criar_conversa` levanta `ValueError` se o funcionário não existe;
   - `adicionar_mensagens` levanta `ValueError` se a conversa não existe, se o papel não é `user`/`assistant` ou se falta `conteudo`. Nesses casos nada é gravado;
   - `registrar_auditoria` levanta `ValueError` se a ação não está na lista do contrato.
   O `chatbot` e o `painel` podem capturar a exceção, se quiserem.
2. **`registrar_chat` com `conversa_id` inexistente** (ex.: a conversa já foi expurgada) grava a troca com `conversa_id` nulo e registra um aviso no log, para a auditoria do chat não falhar.
3. **`listar_clientes_parados` e `dias_na_etapa`.** A referência de tempo é o movimento mais recente da ativação: o maior valor entre o último `ativacao_eventos.ocorrido_em` e `ativacoes.atualizado_em`. Uma pendência registrada dentro da mesma etapa (ex.: "documento reenviado") também reinicia a contagem, seguindo o "desde o último evento/atualização" do contrato.
4. **"Ativados nos últimos 30 dias"** (`metricas_gerais.ativacao_por_etapa["5"]` e `resumo_ativacoes.ativados_30_dias`):
   - conta pelo primeiro evento da etapa 5 de cada cliente, qualquer que seja o status atual (inclui quem ativou e depois cancelou);
   - sem evento da etapa 5, usa `ativacoes.atualizado_em` dos clientes que estão na etapa 5.
   `tempo_medio_ativacao_dias` usa a mesma data de liberação e considera todos os ativados, sem recorte de período.
5. **`economia_total_gerada` passa a incluir o `bonus_clube`**, por coerência com o `economia_total` do resumo do cliente, que o contrato manda somar. É uma mudança de valor (não de formato) em relação à v1.
6. **`buscar_clientes(etapa=...)`** filtra pela `etapa_atual` da ativação, qualquer que seja o status. Com `etapa=5`, aparecem os ativos e os cancelados depois da conexão. Para restringir, combine com `status`.
7. **`metricas_uso_chatbot`:**
   - o período é de dias de calendário (hoje incluso), então `por_dia` tem exatamente `dias` itens, inclusive os dias sem uso;
   - `duracao_media_ms` é um inteiro e vale 0 quando não há duração registrada;
   - `conversas` conta as conversas distintas citadas no `chat_historico` do período;
   - há uma chave extra, `cache_creation_tokens`;
   - `ferramentas_mais_usadas` traz todas as ferramentas, da mais usada para a menos usada.
8. **`resumo_ativacoes.dias_medios_na_etapa`** vale `0.0` para uma etapa sem clientes, porque o contrato pede `float`.
9. **Seed: os dados individuais mudaram.** Os totais e os personagens continuam iguais. Mas, para aplicar o bônus do Clube na fatura seguinte, o Clube passou a ser gerado antes das faturas. Além disso, 3 ativos viraram "ativados recentes" e 1 cliente em ativação ficou atrasado. Isso mudou a sequência de sorteios. Testes não devem depender de nomes ou valores de clientes sorteados (só de Marcos Andrade, Clara Ribeiro, Renato Souza, `MARCOS50` e dos totais).
10. **Auditoria do seed:** todos os registros têm pelo menos 2 dias, então `contar_falhas_login` começa em 0 para qualquer e-mail, e `expurgar_dados_antigos()` com os padrões não apaga nada do seed.
11. **Banco já existente:** `inicializar_banco()` adiciona as colunas novas num banco da v1 (sem a FK de `chat_historico.conversa_id`, que o SQLite não acrescenta via `ALTER TABLE`). Mesmo assim, o certo é recriar o banco com `python -m app.database.seed` depois da integração, como o contrato prevê.
