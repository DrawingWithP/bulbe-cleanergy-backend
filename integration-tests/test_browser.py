"""Jornadas reais: Chromium -> HTTP -> FastAPI -> SQLite temporário. Sem mocks.
Executar: python integration-tests/test_browser.py [--reference /caminho/frontend-original]
Dependências de teste: playwright + backend/requirements.txt; playwright install chromium.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
CLIENT = '8f1c2a6e-4b7d-4c1a-9f52-3d6a1b0c7e11'


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server(command, cwd, env):
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log)
        try:
            yield process
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            if process.returncode not in [0, -15]:
                log.seek(0); print(log.read().decode(), file=sys.stderr)


def ready(url, process):
    for _ in range(200):
        try:
            urllib.request.urlopen(url, timeout=1).close(); return
        except Exception:
            if process.poll() is not None:
                raise RuntimeError('Servidor terminou antes de iniciar')
            time.sleep(.1)
    raise RuntimeError('Servidor não iniciou')


def run(reference):
    with tempfile.TemporaryDirectory(prefix='bulbe-integration-') as tmp:
        env = {**os.environ, 'BULBE_DATABASE_URL':'sqlite:///' + tmp + '/test.db',
               'BULBE_SECRET_KEY':'isolated-integration-test-key-only',
               'BULBE_FRONTEND_CLIENTE_ID':CLIENT}
        # Somente banco descartável; mesmos modelos e seed já existentes no backend.
        subprocess.run([sys.executable, '-c',
            'from app.db import models; from app.db.database import Base, engine, SessionLocal; '
            'from app.db.seed import popular; Base.metadata.create_all(engine); '
            's=SessionLocal(); popular(s); s.close()'], cwd=ROOT/'backend', env=env, check=True)
        address = f'http://127.0.0.1:{port()}'
        with server([sys.executable, '-m', 'uvicorn', 'dev_frontend:app', '--host', '127.0.0.1', '--port', address.rsplit(':',1)[1]], ROOT/'backend', env) as proc:
            ready(address + '/', proc)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width':430, 'height':932}, device_scale_factor=1)
                errors, dialogs, requests = [], [], []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
                page.on('request', lambda r: requests.append((r.method, r.url, r.post_data)))
                page.goto(address + '/frontend/final.html')
                page.wait_for_timeout(600)
                assert not errors, errors
                if reference:
                    original = f'http://127.0.0.1:{port()}'
                    with server([sys.executable, '-m', 'http.server', original.rsplit(':',1)[1], '--bind', '127.0.0.1'], reference, env) as ref:
                        ready(original + '/final.html', ref)
                        baseline = browser.new_page(viewport={'width':430,'height':932}, device_scale_factor=1)
                        baseline.goto(original + '/final.html'); baseline.wait_for_timeout(600)
                        assert page.screenshot() == baseline.screenshot(), 'Tela inicial mudou visualmente'
                        baseline.close()
                    print('PASS: screenshot da tela inicial idêntica ao original')
                # Availability, auth and validation over real HTTP (no dependency overrides).
                api = page.request
                assert api.get(address+'/').status == 200
                assert api.get(address+'/v1/auth/me').status == 401
                assert api.post(address+'/v1/auth/login', form={'username':'missing@example.test','password':'bad'}).status == 401
                login = api.post(address+'/v1/auth/login', form={'username':'admin@bulbe.com.br','password':'bulbe12345'})
                assert login.status == 200
                assert api.get(address+'/v1/auth/me', headers={'Authorization':'Bearer '+login.json()['access_token']}).status == 200
                print('PASS: inicialização e autenticação real (200/401)')
                page.locator('.primary-button').click()
                expect(page.locator('#st-progresso-pct')).to_have_text('30%')
                page.locator('.st-jornada-detalhes').click()
                expect(page.locator('#det-numero-etapa')).to_have_text('2')
                expect(page.locator('#det-status-titulo')).not_to_have_text('—')
                page.locator('#screen-detalhes [data-nav-back]').click()
                page.locator('#screen-status [data-nav="screen-dicas"]').click()
                expect(page.locator('#dc-dicas-list li')).to_have_count(2)
                expect(page.locator('.dc-mensal span')).to_have_text('R$ 12,50')
                page.locator('#dc-dicas-indicators li').nth(1).click()
                expect(page.locator('.dc-mensal span')).to_have_text('R$ 25,00')
                print('PASS: status, detalhes, dicas e carrossel com dados da API')
                page.locator('#screen-dicas [data-nav="screen-vantagens"]').click()
                expect(page.locator('#van-titulo-dias')).to_have_text('Sua carta chegou! ✨')
                expect(page.locator('.van-lista-parceiros li')).to_have_count(3)
                page.locator('#van-card-proxima-carta').click()
                page.locator('#carta-btn-abrir').click()
                expect(page.locator('#rc-titulo')).to_have_text('500 pontos Livelo')
                code = page.locator('#rc-cupom-codigo').inner_text()
                page.locator('#rc-btn-salvar').click()
                expect(page.locator('#screen-vantagens')).to_have_class('screen active', timeout=10000)
                coupons = api.get(address + f'/v1/clientes/{CLIENT}/cupons').json()['data']
                generated = next(c for c in coupons if c['codigo'] == code)
                assert generated['situacao'] == 'salvo'
                page.reload()
                page.locator('.primary-button').click()
                page.locator('#screen-status [data-nav="screen-vantagens"]').click()
                expect(page.locator('#van-container-cupons')).to_contain_text('500 pontos Livelo')
                # Opening the same letter through the real API remains idempotent.
                result = api.post(address + '/v1/cartas/a7c4e2b9-5d31-4f80-9e6b-8c2a1d4f7b55/abertura')
                assert result.json()['cupom']['id'] == generated['id']
                page.locator('#van-container-cupons li').filter(has_text='500 pontos Livelo').click()
                expect(page.locator('#rc-cupom-codigo')).to_have_text(code)
                page.locator('#rc-btn-copiar').click()
                expect(page.locator('#rc-btn-copiar')).to_have_text('Copiado!')
                print('PASS: carta, resgate, cupom salvo e persistência após recarregar; abertura idempotente')
                # Both existing simulators, including validation for the unsupported zero-referral input.
                for screen, prefix in [('screen-simulador','sim'), ('screen-simulador-logado','slog')]:
                    page.evaluate('(id) => navigateTo(id)', screen)
                    page.wait_for_timeout(350)
                    page.locator(f'#{prefix}-vlr-pago').fill('200')
                    page.locator(f'#{prefix}-vlr-pago').blur()
                    page.wait_for_timeout(800)
                    assert any('indicacoes' in d for d in dialogs), dialogs
                    assert 'oculto' in page.locator(f'#{screen} .sim-sec-economia').get_attribute('class')
                    page.locator(f'#{screen} .sim-btn-mais').click()
                    expect(page.locator(f'#{prefix}-economia-total')).to_have_text('140')
                    page.locator(f'#{screen} .sim-pill').nth(2).click()
                    expect(page.locator(f'#{prefix}-economia-total')).to_have_text('410')
                    page.locator(f'#{prefix}-custom-principal').click()
                    page.locator(f'#{prefix}-custom-meses').fill('2')
                    page.locator(f'#{screen} .sim-btn-ok').click()
                    expect(page.locator(f'#{prefix}-economia-total')).to_have_text('110')
                print('PASS: dois simuladores, períodos, indicação e erro 422 real')
                # Broken client -> real 404 -> no simulated fallback.
                missing = browser.new_page()
                missing.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
                missing.goto(address + '/frontend/final.html')
                missing.evaluate("window.BULBE_CONFIG.clienteId = 'inexistente'")
                missing.locator('.primary-button').click()
                expect(missing.locator('#st-progresso-pct')).to_have_text('—')
                missing.wait_for_timeout(800)
                assert any('não foi encontrado' in d for d in dialogs), dialogs
                assert not errors, errors
                assert any('/v1/simulacaos' in r[1] for r in requests)
                # Verify actual rows, rather than relying on the UI as persistence evidence.
                subprocess.run([sys.executable, '-c',
                    'from sqlalchemy import select; from app.db.database import SessionLocal; '
                    'from app.db.models import SimulacaoModel, CupomModel; '
                    's=SessionLocal(); assert len(s.scalars(select(SimulacaoModel)).all()) >= 6; '
                    f'assert s.get(CupomModel, "{generated["id"]}").situacao == "salvo"; s.close()'], cwd=ROOT/'backend', env=env, check=True)
                assert all(url.startswith(address + '/') for _, url, _ in requests if '/v1/' in url)
                invalid_json = page.evaluate("async () => { try { await BulbeAPI.request('/frontend/final.html'); return ''; } catch (e) { return e.message; } }")
                assert 'JSON inválida' in invalid_json
                print('PASS: 404, persistência SQL de simulações/cupons, nenhum erro JavaScript ou CORS')
                proc.terminate(); proc.wait(timeout=10)
                page.evaluate('() => window._onAtivacao()')
                expect(page.locator('#st-progresso-pct')).to_have_text('—')
                assert any('Não foi possível comunicar' in d for d in dialogs)
                print('PASS: servidor indisponível e JSON inválido, sem sucesso simulado')
                browser.close()
        # New server process, same temporary DB: verifies persistence across restart.
        with server([sys.executable, '-m', 'uvicorn', 'dev_frontend:app', '--host', '127.0.0.1', '--port', address.rsplit(':',1)[1]], ROOT/'backend', env) as proc:
            ready(address+'/', proc)
            saved = json.load(urllib.request.urlopen(address + '/v1/cupons/' + generated['id']))
            assert saved['situacao'] == 'salvo'
        print('PASS: persistência após reiniciar o backend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path)
    run(parser.parse_args().reference)
