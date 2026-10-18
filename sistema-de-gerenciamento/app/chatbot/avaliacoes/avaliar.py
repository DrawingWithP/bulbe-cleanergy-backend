"""
Avaliacao do Assistente Bulbe contra a API REAL da Anthropic.

ATENCAO: cada caso faz chamadas pagas ao Claude (gasta creditos). Rode manualmente,
a partir da pasta `sistema-de-gerenciamento/`, com a ANTHROPIC_API_KEY configurada:

    python -m app.chatbot.avaliacoes.avaliar                  # todos os casos
    python -m app.chatbot.avaliacoes.avaliar --ids data-de-hoje,simulacao-320-12-2
    python -m app.chatbot.avaliacoes.avaliar --categoria gestao-ativacao --detalhes
    python -m app.chatbot.avaliacoes.avaliar --saida resultado.json

Cada caso usa o mesmo fluxo da rota POST /v1/painel/chat (mesmo prompt, ferramentas
e mascaramento), mas SEM gravar conversa nem registrar no historico de auditoria.
As ferramentas leem o banco configurado em BULBE_DB_URL (padrao: app/database/bulbe_ficticio.db);
os valores esperados em `casos.json` valem para o seed com a semente 42.

Imprime acertos/erros por caso, tokens e o custo estimado (precos de app/chatbot/config.py).
Codigo de saida: 0 se todos os casos passaram, 1 se algum falhou, 2 se nao foi possivel rodar.
"""
import argparse
import json
import os
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    # Execucao direta (python app/chatbot/avaliacoes/avaliar.py): coloca a raiz do sistema no sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

ARQUIVO_CASOS_PADRAO: Path = Path(__file__).with_name("casos.json")

# Funcionario ficticio usado na linha de contexto das perguntas (nada e gravado).
FUNCIONARIO_AVALIACAO: dict = {"id": 0, "nome": "Avaliação Automática", "email": "avaliacao@bulbe.com.br",
                               "perfil": "admin"}


# ---------------------------------------------------------------------------
# Conferencia das respostas
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Minusculas, sem acentos e com espacos simples (para comparar trechos)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def _substituir_marcadores(trecho: str, hoje: date) -> str:
    return str(trecho).replace("{hoje}", hoje.strftime("%d/%m/%Y"))


def conferir_caso(caso: dict, resposta: str, ferramentas_usadas: list[str], hoje: date) -> list[str]:
    """Devolve a lista de falhas do caso (vazia = passou)."""
    falhas: list[str] = []
    texto = normalizar(resposta)
    usadas = set(ferramentas_usadas)

    for trecho in caso.get("deve_conter", []):
        alvo = _substituir_marcadores(trecho, hoje)
        if normalizar(alvo) not in texto:
            falhas.append(f"faltou o trecho {alvo!r}")
    for grupo in caso.get("qualquer_de", []):
        opcoes = [_substituir_marcadores(t, hoje) for t in grupo]
        if not any(normalizar(op) in texto for op in opcoes):
            falhas.append(f"nenhum destes trechos apareceu: {opcoes}")
    for trecho in caso.get("nao_deve_conter", []):
        alvo = _substituir_marcadores(trecho, hoje)
        if normalizar(alvo) in texto:
            falhas.append(f"apareceu o trecho proibido {alvo!r}")
    for nome in caso.get("ferramentas_esperadas", []):
        if nome not in usadas:
            falhas.append(f"nao usou a ferramenta {nome!r}")
    for grupo in caso.get("ferramentas_qualquer_de", []):
        if not usadas.intersection(grupo):
            falhas.append(f"nao usou nenhuma destas ferramentas: {grupo}")
    if caso.get("sem_ferramentas") and usadas:
        falhas.append(f"usou ferramentas sem necessidade: {sorted(usadas)}")
    return falhas


def carregar_casos(arquivo: Path, ids: list[str] | None = None, categoria: str | None = None) -> list[dict]:
    """Le o arquivo de casos e aplica os filtros por id e categoria."""
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    casos = dados["casos"] if isinstance(dados, dict) else dados
    if ids:
        desconhecidos = set(ids) - {c["id"] for c in casos}
        if desconhecidos:
            raise SystemExit(f"Ids de caso desconhecidos: {', '.join(sorted(desconhecidos))}")
        casos = [c for c in casos if c["id"] in ids]
    if categoria:
        casos = [c for c in casos if c.get("categoria") == categoria]
    return casos


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------
def rodar_caso(servico: Any, caso: dict) -> dict:
    """Roda um caso pelo fluxo sincrono do chatbot, sem gravar nada."""
    inicio = time.monotonic()
    contexto = servico.preparar(caso["pergunta"], FUNCIONARIO_AVALIACAO, persistir=False)
    resultado = servico.responder_contexto(contexto)
    resultado["duracao_s"] = round(time.monotonic() - inicio, 2)
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avalia o Assistente Bulbe contra a API real (gasta creditos).")
    parser.add_argument("--casos", type=Path, default=ARQUIVO_CASOS_PADRAO, help="arquivo JSON de casos")
    parser.add_argument("--ids", default="", help="ids separados por virgula (padrao: todos)")
    parser.add_argument("--categoria", default=None, help="roda so os casos desta categoria")
    parser.add_argument("--detalhes", action="store_true", help="imprime a resposta completa de cada caso")
    parser.add_argument("--pausa", type=float, default=0.0, help="segundos de pausa entre casos (limite de taxa)")
    parser.add_argument("--saida", type=Path, default=None, help="grava os resultados em JSON neste arquivo")
    args = parser.parse_args(argv)

    from app.chatbot import config
    from app.chatbot.servico import ChatbotService
    from app.database.conexao import inicializar_banco
    from app.erros import ErroDeNegocio

    if config.obter_chave_api() is None:
        print("Defina ANTHROPIC_API_KEY (no .env ou no ambiente) para rodar as avaliacoes.", file=sys.stderr)
        return 2

    ids = [i.strip() for i in args.ids.split(",") if i.strip()] or None
    casos = carregar_casos(args.casos, ids=ids, categoria=args.categoria)
    if not casos:
        print("Nenhum caso selecionado.", file=sys.stderr)
        return 2

    inicializar_banco()
    servico = ChatbotService()
    hoje = date.today()
    print(f"Modelo: {config.CHATBOT_MODELO} | esforco: {config.CHATBOT_ESFORCO} | casos: {len(casos)}")
    print(f"Banco: {os.getenv('BULBE_DB_URL') or 'app/database/bulbe_ficticio.db (padrao)'}\n")

    resultados: list[dict] = []
    custo_total = 0.0
    tokens = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_creation_tokens": 0}
    inicio_geral = time.monotonic()

    for numero, caso in enumerate(casos, start=1):
        try:
            resultado = rodar_caso(servico, caso)
        except ErroDeNegocio as exc:
            falhas = [f"erro {exc.status} {exc.code}: {exc.message}"]
            resultado = {"resposta": "", "ferramentas_usadas": [], "uso": {}, "duracao_s": 0.0}
        except Exception as exc:  # noqa: BLE001 - um caso com erro nao interrompe os demais
            falhas = [f"erro inesperado: {type(exc).__name__}: {exc}"]
            resultado = {"resposta": "", "ferramentas_usadas": [], "uso": {}, "duracao_s": 0.0}
        else:
            falhas = conferir_caso(caso, resultado["resposta"], resultado["ferramentas_usadas"], hoje)

        uso = resultado.get("uso") or {}
        custo = float(uso.get("custo_estimado_usd") or 0.0)
        custo_total += custo
        for chave in tokens:
            tokens[chave] += int(uso.get(chave) or 0)

        situacao = "OK    " if not falhas else "FALHOU"
        print(f"[{situacao}] {numero:02d}/{len(casos)} {caso['id']} "
              f"({resultado.get('duracao_s', 0)} s, US$ {custo:.5f}) "
              f"ferramentas: {', '.join(resultado.get('ferramentas_usadas') or []) or '-'}")
        for falha in falhas:
            print(f"         - {falha}")
        if args.detalhes or falhas:
            resposta = (resultado.get("resposta") or "").strip()
            trecho = resposta if args.detalhes else resposta[:400] + ("..." if len(resposta) > 400 else "")
            print("         resposta: " + trecho.replace("\n", "\n                   "))

        resultados.append({
            "id": caso["id"],
            "categoria": caso.get("categoria"),
            "passou": not falhas,
            "falhas": falhas,
            "resposta": resultado.get("resposta"),
            "ferramentas_usadas": resultado.get("ferramentas_usadas"),
            "uso": uso,
            "duracao_s": resultado.get("duracao_s"),
        })
        if args.pausa and numero < len(casos):
            time.sleep(args.pausa)

    acertos = sum(1 for r in resultados if r["passou"])
    total = len(resultados)
    duracao = time.monotonic() - inicio_geral
    print("\n" + "=" * 72)
    print(f"Acertos: {acertos}/{total} ({100 * acertos / total:.0f}%) | erros: {total - acertos}")
    print(f"Tokens: entrada {tokens['input_tokens']}, saida {tokens['output_tokens']}, "
          f"cache lido {tokens['cache_read_tokens']}, cache escrito {tokens['cache_creation_tokens']}")
    print(f"Custo estimado: US$ {custo_total:.4f} (media US$ {custo_total / total:.5f} por caso) | "
          f"tempo total: {duracao:.1f} s")
    if total - acertos:
        print("Casos com erro: " + ", ".join(r["id"] for r in resultados if not r["passou"]))

    if args.saida:
        args.saida.write_text(
            json.dumps({
                "modelo": config.CHATBOT_MODELO,
                "esforco": config.CHATBOT_ESFORCO,
                "data": hoje.isoformat(),
                "acertos": acertos,
                "total": total,
                "custo_estimado_usd": round(custo_total, 6),
                "tokens": tokens,
                "resultados": resultados,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Resultados gravados em {args.saida}")

    return 0 if acertos == total else 1


if __name__ == "__main__":
    sys.exit(main())
