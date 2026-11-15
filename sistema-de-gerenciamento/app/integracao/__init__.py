"""
Integracao do sistema de gerenciamento com o app da Bulbe (pasta backend/).

- sincronizacao: le o banco do app (somente leitura) e espelha no banco do painel
  clientes, ativacoes, Clube (cartas e cupons), parceiros, dicas, usinas, adesoes,
  indicacoes e simulacoes. Roda ao subir o servidor, de tempos em tempos e pela rota de admin.
- api_app: cliente HTTP da API do app, usado para o painel alterar a etapa de
  ativacao de um cliente (a mudanca aparece no app na hora).
"""
