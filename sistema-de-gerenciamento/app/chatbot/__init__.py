"""
Pacote do chatbot do Painel de Gestao da Bulbe (Claude Haiku 5.5 com tool use).

Modulos:
- config: variaveis de ambiente (modelo, esforco, chave da API).
- base_conhecimento: texto sobre o app da Bulbe e as funcionalidades da squad.
- prompts: prompt de sistema do assistente interno.
- ferramentas: definicao das ferramentas (somente leitura) e execucao.
- servico: loop manual de tool use com o SDK oficial `anthropic`.
- controller: rotas /v1/painel/chat.
"""
