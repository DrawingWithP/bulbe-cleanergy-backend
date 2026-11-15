"""
Sobe o projeto inteiro com um comando: app (API + frontend) e sistema de gerenciamento.

    python iniciar.py                # migrations + seed do app e os dois servidores
    python iniciar.py --sem-seed     # nao roda o seed do app
    python iniciar.py --porta-app 8000 --porta-painel 8001

Requer as dependencias das duas partes no Python usado (veja requirements.txt na raiz).

- App (FastAPI + frontend na mesma origem): http://127.0.0.1:8000/frontend/final.html
- Swagger da API:                           http://127.0.0.1:8000/docs
- Sistema de gerenciamento (painel):        http://127.0.0.1:8001/painel/

O painel le o banco do app (backend/bulbe.db) e sincroniza os dados a cada
INTEGRACAO_INTERVALO_SEGUNDOS (30 s por padrao); a mudanca de etapa feita no painel
e enviada para a API do app. Ctrl+C encerra os dois servidores.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"
PAINEL = RAIZ / "sistema-de-gerenciamento"


def _rodar(comando: list[str], pasta: Path, env: dict[str, str]) -> None:
    print(f"$ {' '.join(comando)}  (em {pasta.name}/)", flush=True)
    resultado = subprocess.run(comando, cwd=pasta, env=env)
    if resultado.returncode != 0:
        raise SystemExit(f"Falhou: {' '.join(comando)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sobe o app da Bulbe e o sistema de gerenciamento juntos.")
    parser.add_argument("--porta-app", type=int, default=8000)
    parser.add_argument("--porta-painel", type=int, default=8001)
    parser.add_argument("--host", default="127.0.0.1", help="Use 127.0.0.1 (padrao) para nao expor na rede.")
    parser.add_argument("--sem-seed", action="store_true", help="Nao roda o seed de demonstracao do app.")
    args = parser.parse_args()

    python = sys.executable
    env_app = {**os.environ}
    env_painel = {
        **os.environ,
        "INTEGRACAO_APP_API_URL": f"http://127.0.0.1:{args.porta_app}",
    }
    env_painel.setdefault("INTEGRACAO_APP_DB_URL", "sqlite:///" + (BACKEND / "bulbe.db").as_posix())

    _rodar([python, "-m", "alembic", "upgrade", "head"], BACKEND, env_app)
    if not args.sem_seed:
        _rodar([python, "-m", "app.db.seed"], BACKEND, env_app)

    processos = [
        subprocess.Popen(
            [python, "-m", "uvicorn", "dev_frontend:app", "--host", args.host, "--port", str(args.porta_app)],
            cwd=BACKEND, env=env_app,
        ),
        subprocess.Popen(
            [python, "-m", "uvicorn", "app.main:app", "--host", args.host, "--port", str(args.porta_painel)],
            cwd=PAINEL, env=env_painel,
        ),
    ]

    print(
        "\n"
        f"  App (frontend):  http://{args.host}:{args.porta_app}/frontend/final.html\n"
        f"  API (Swagger):   http://{args.host}:{args.porta_app}/docs\n"
        f"  Painel interno:  http://{args.host}:{args.porta_painel}/painel/\n"
        "  Ctrl+C para encerrar.\n",
        flush=True,
    )

    encerrou_sozinho = None
    try:
        while encerrou_sozinho is None:
            time.sleep(0.5)
            encerrou_sozinho = next((p for p in processos if p.poll() is not None), None)
    except KeyboardInterrupt:
        pass
    finally:
        for processo in processos:
            if processo.poll() is None:
                processo.terminate()
        for processo in processos:
            try:
                processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                processo.kill()

    if encerrou_sozinho is not None:
        raise SystemExit(f"Um dos servidores parou (codigo {encerrou_sozinho.returncode}); o outro foi encerrado.")


if __name__ == "__main__":
    main()
