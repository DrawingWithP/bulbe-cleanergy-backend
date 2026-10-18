"""
Pacote do chatbot do Painel de Gestao da Bulbe (Claude Haiku 5.5 com tool use).

Modulos:
- config: variaveis de ambiente (modelo, esforco, chave da API, precos para o custo estimado).
- base_conhecimento: texto sobre o app da Bulbe e as funcionalidades da squad.
- prompts: prompt de sistema estatico e a linha de contexto de cada pergunta.
- ferramentas: definicao das ferramentas (somente leitura) e execucao.
- servico: loop manual de tool use (sincrono e streaming), historico no servidor, uso/custo.
- controller: rotas /v1/painel/chat (chat, stream SSE, conversas, sugestoes).
- avaliacoes: casos de avaliacao e o executor contra a API real.
"""
