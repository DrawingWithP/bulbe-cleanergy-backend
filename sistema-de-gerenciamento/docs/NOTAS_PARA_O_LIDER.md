# Notas para o líder — agente `docs`

Inconsistências e dúvidas encontradas ao documentar. Em cada uma segui a melhor suposição indicada.

## 1. Formato de erro: `error` × `erro`
- `CONTRATOS.md` §2.2 e o `app/main.py` usam `{"error": {"code", "message", "status"}}`.
- `docs/Lista_de_endpoints.md` (Convenções) define `{ "erro": { "codigo", "mensagem", "campos" } }`.
- **Suposição:** a documentação do painel segue o código/contrato (`error`). Sugiro alinhar a `Lista_de_endpoints.md` numa próxima sprint.

## 2. Código do cupom da Araújo no front × contrato
- O front (`final.html`, tela de recompensa) mostra o cupom `ARAUJO50` para "15% de desconto na Araújo".
- O contrato (§1.4) define `BULBE15` para Araújo 15%.
- **Suposição:** documentei os códigos do contrato (`BULBE15`, `INTERCASH`, `BULBEDUO`, `BULBELIV500`, `BULBE10`).

## 3. Nomes das personas × personagens do seed
- Personas do front: "Clara **Galvão**" e "Marcos **Carneiro**". Telas do front e `Lista_de_endpoints.md`: "Marcos **Andrade**". Contrato: "Marcos Andrade" e "Clara **Ribeiro**".
- **Suposição:** documentei os nomes do contrato/seed (Marcos Andrade, Clara Ribeiro). Todos fictícios.

## 4. Base do desconto (D-06)
- `demandas.md` (D-06) diz "excluindo frete e taxa de iluminação pública"; o site diz que o desconto não incide sobre **iluminação pública e PIS/COFINS**.
- **Suposição:** documentei a versão do site (iluminação pública e PIS/COFINS).

## 5. Numeração de User Stories
- O front tem US-01 a US-06 (ligadas a D-01..D-06); `docs/user-stories.md` do back-end tem US-01 a US-35 (por endpoint) com outro significado.
- **Suposição:** na coluna "US do front" do levantamento usei a numeração do README do front (US-01..US-06), a mesma do "Mapa de rastreabilidade" de `Lista_de_endpoints.md`.

## 6. README raiz do repositório
- O `README.md` raiz ainda é o template da disciplina (estrutura `src/`, tecnologias em branco). Sugiro que o líder aponte para `docs/chatbot/README.md` e preencha stack/execução.

## 7. Conferência final com o código (após os agentes db, chatbot e painel)
A documentação foi alinhada ao código real. Pontos que dependem do líder:

- ~~`listar_faturas_vencidas` não é ferramenta do chatbot~~ — **resolvido**: o agente `chatbot` adicionou a
  ferramenta durante a conferência (agora são 17). Documentação atualizada.
- ~~**Handlers em `app/main.py`**~~ — **resolvido** pelo líder: um *handler* para cada classe `ErroDeNegocio`
  (usina e dica) e um *handler* global de `StarletteHTTPException` que devolve `{"error": {...}}` puro.
  `arquitetura.md` e `guia-do-painel.md` atualizados.
- ~~**Variável `CHATBOT_TIMEOUT` no `.env.example`**~~ — **resolvido**: já está no `.env.example`.
- **Senha demo em texto em arquivos versionados:** `CONTRATOS.md` §1.5, `app/database/README.md` e agora também o
  `.env.example` trazem o valor padrão de `PAINEL_SENHA_DEMO`. O guia desta pasta propositalmente não cita. Sugestão: deixar `PAINEL_SENHA_DEMO=` vazio no `.env.example`
  (o seed já tem um padrão) e tirar o valor dos dois documentos. É só uma demo com dados fictícios, então não bloqueia a entrega.
- **Telas sem rota de interface:** `/v1/painel/dicas` não tem tela; usinas e parceiros aparecem só na Visão geral.
  Documentado como está.
- **`ativacao_por_etapa`** conta só clientes `em_ativacao` (etapas 1–4); a barra da etapa 5 fica sempre vazia.
  Documentado no dicionário de dados.
- **`exigir_admin`** existe em `auth.py`, mas nenhuma rota usa; os dois perfis veem os mesmos dados. Registrado como limite em `seguranca-e-lgpd.md`.
