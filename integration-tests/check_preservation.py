"""Verifica CSS/assets originais, HTML e escopo do backend. Sem dependências extras."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((Path(__file__).with_name('frontend-source-sha256.json')).read_text())
for name, digest in manifest['sha256'].items():
    if name not in {'final.html', 'final.js'}:
        assert hashlib.sha256((ROOT/'frontend'/name).read_bytes()).hexdigest() == digest, name
html = (ROOT/'frontend/final.html').read_bytes()
html = html.replace(b'  <script src="config.js"></script>\n  <script src="api.js"></script>\n', b'')
assert hashlib.sha256(html).hexdigest() == manifest['sha256']['final.html']
files = subprocess.check_output(['git', 'diff', '86e8777040bb7733e13d3c325c5bd2c3de49d099', '--name-only', '--', 'backend/app', 'backend/migrations', 'sistema-de-gerenciamento'], cwd=ROOT, text=True)
assert not files.strip(), files
print(f"PASS: {len(manifest['sha256']) - 2} arquivos originais idênticos; HTML só adiciona scripts; backend e sistema independente preservados")
