"""
Camada de Persistencia, pacote do banco de dados ficticio da Bulbe (SQLAlchemy 2 + SQLite).

Modulos:
- conexao.py   -> Base, engine, SessionLocal, obter_sessao(), inicializar_banco()
- seguranca.py -> gerar_hash_senha(), verificar_senha() (somente stdlib)
- modelos.py   -> as 17 tabelas do painel de gestao (ORM)
- seed.py      -> popular_banco() com dados 100% ficticios (python -m app.database.seed)
- consultas.py -> funcoes somente leitura usadas pelo painel e pelo chatbot

Este __init__ nao importa nada de proposito: assim, importar um modulo leve
(ex.: app.database.seguranca) nao obriga a carregar o SQLAlchemy.
"""
