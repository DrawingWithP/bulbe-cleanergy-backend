// Navegação entre telas sem recarregar a página.
// Para navegar: use o atributo data-nav="screen-id" em qualquer botão/elemento.
// Para voltar: use data-nav-back em qualquer botão/elemento.

const history = [];

function updateTestButtons(screenId) {
  const show = (id, cond) => { const el = document.getElementById(id); if (el) el.style.display = cond ? 'block' : 'none'; };
  show('st-btn-anterior', screenId === 'screen-status');
  show('st-btn-proxima',  screenId === 'screen-status');
  show('det-btn-anterior',   screenId === 'screen-detalhes');
  show('det-btn-avancar',    screenId === 'screen-detalhes');
  show('van-btn-voltar-dia', screenId === 'screen-vantagens');
  show('van-btn-passar-dia', screenId === 'screen-vantagens');
  show('van-btn-resetar',    screenId === 'screen-vantagens');
}

function navigateTo(screenId) {
  const current = document.querySelector('.screen.active');
  const next = document.getElementById(screenId);

  if (!next) { BulbeAPI.report(new Error('Esta tela não está implementada no frontend original.')); return; }
  if (next === current) return;

  if (current) {
    history.push(current.id);
    current.classList.add('slide-out');
    setTimeout(() => {
      current.classList.remove('active', 'slide-out');
    }, 280);
  }

  next.classList.add('active', 'slide-in');
  setTimeout(() => {
    next.classList.remove('slide-in');
  }, 280);

  updateTestButtons(screenId);

  // Hooks de tela
  setTimeout(() => {
    if (screenId === 'screen-dicas')            window._onDicas?.();
    if (screenId === 'screen-status' || screenId === 'screen-detalhes') window._onAtivacao?.();
    if (screenId === 'screen-vantagens')        window._onVantagens?.();
    if (screenId === 'screen-carta')            window._onCarta?.();
    if (screenId === 'screen-recompensa-carta') window._onRecompensa?.();
    if (screenId === 'screen-trilha')           window._onTrilha?.();
  }, 290);
}

function navigateBack() {
  if (history.length === 0) return;
  const previousId = history.pop();
  const current = document.querySelector('.screen.active');
  const previous = document.getElementById(previousId);

  if (!previous) return;

  if (current) {
    current.classList.add('slide-out');
    setTimeout(() => {
      current.classList.remove('active', 'slide-out');
    }, 280);
  }

  previous.classList.add('active');
  updateTestButtons(previousId);
  if (previousId === 'screen-status' || previousId === 'screen-detalhes') window._onAtivacao?.();
  if (previousId === 'screen-vantagens') window._onVantagens?.();
  if (previousId === 'screen-dicas') window._onDicas?.();
}

document.addEventListener('click', (e) => {
  // Abrir menu lateral
  if (e.target.closest('[data-open-menu]')) {
    const drawer = document.getElementById('menu-lateral');
    requestAnimationFrame(() => drawer.classList.add('open'));
    return;
  }

  // Fechar menu lateral: botão X ou qualquer clique fora da sidebar
  const drawer = document.getElementById('menu-lateral');
  if (drawer.classList.contains('open')) {
    if (e.target.closest('#ml-btn-fechar') || !e.target.closest('.ml-sidebar')) {
      drawer.classList.remove('open');
      return;
    }
  }

  const target = e.target.closest('[data-nav]');
  if (target) {
    document.getElementById('menu-lateral').classList.remove('open');
    navigateTo(target.dataset.nav);
    return;
  }

  const back = e.target.closest('[data-nav-back]');
  if (back) {
    document.getElementById('menu-lateral').classList.remove('open');
    navigateBack();
  }
});

// ============================================================
// CLUBE BULBE — ESTADO OBTIDO DA API
// ============================================================
const ClubeBulbe = BulbeAPI.clube;

// ============================================================
// DICAS — CARROSSEL
// ============================================================
(function () {
  const ul = document.getElementById('dc-dicas-list');
  const indicators = document.getElementById('dc-dicas-indicators');
  let currentIndex = 0;

  let economias = [];
  window._onDicas = async function () {
    ul.replaceChildren(); indicators.replaceChildren();
    document.querySelector('.dc-mensal span').textContent = '—';
    document.querySelector('.dc-anual span').textContent = '—';
    try {
      const dicas = await BulbeAPI.request('/v1/dicas');
      ul.replaceChildren(); indicators.replaceChildren();
      economias = dicas.map(d => ({ mensal: BulbeAPI.money(d.economia), anual: BulbeAPI.money(d.economia * 12) }));
      dicas.forEach((d, i) => {
        const li = document.createElement('li');
        const article = document.createElement('article'); article.className = 'dc-card';
        const img = document.createElement('img'); img.alt = '';
        img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(d.imagem_svg);
        const h2 = document.createElement('h2'); h2.textContent = d.titulo;
        const p = document.createElement('p'); p.textContent = d.descricao;
        article.append(img, h2, p); li.append(article); ul.append(li);
        const dot = document.createElement('li');
        const label = document.createElement('span'); label.className = 'sr-only'; label.textContent = `Dica ${i + 1}`;
        dot.append(label); indicators.append(dot);
      });
      if (dicas.length) showIndex(0);
      else {
        document.querySelector('.dc-mensal span').textContent = '—';
        document.querySelector('.dc-anual span').textContent = '—';
      }
    } catch (error) { BulbeAPI.report(error); }
  };

  function updateSavings(index) {
    const e = economias[index];
    if (!e) return;
    const screen = document.getElementById('screen-dicas');
    const mensal = screen.querySelector('.dc-mensal span');
    const anual  = screen.querySelector('.dc-anual span');
    if (mensal) mensal.textContent = e.mensal;
    if (anual)  anual.textContent  = e.anual;
  }

  function showIndex(index) {
    const items = Array.from(ul.children);
    if (index < 0) index = items.length - 1;
    if (index >= items.length) index = 0;
    items.forEach((li, i) => {
      if (i === index) { li.style.display = 'block'; li.removeAttribute('aria-hidden'); }
      else             { li.style.display = 'none';  li.setAttribute('aria-hidden', 'true'); }
    });
    Array.from(indicators.children).forEach((dot, i) => {
      if (i === index) dot.setAttribute('aria-current', 'true');
      else             dot.removeAttribute('aria-current');
    });
    currentIndex = index;
    updateSavings(index);
  }

  indicators.addEventListener('click', (e) => {
    const li = e.target.closest('li');
    if (!li) return;
    const idx = Array.from(indicators.children).indexOf(li);
    if (idx >= 0) showIndex(idx);
  });

  let startX = 0;
  ul.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; }, { passive: true });
  ul.addEventListener('touchend',   (e) => {
    const dx = e.changedTouches[0].clientX - startX;
    if (dx < -40) showIndex(currentIndex + 1);
    else if (dx > 40) showIndex(currentIndex - 1);
  });

  let mouseDown = false;
  ul.addEventListener('mousedown', (e) => { mouseDown = true; startX = e.clientX; });
  window.addEventListener('mouseup', (e) => {
    if (!mouseDown) return;
    const dx = e.clientX - startX;
    if (dx < -40) showIndex(currentIndex + 1);
    else if (dx > 40) showIndex(currentIndex - 1);
    mouseDown = false;
  });
}());

// ============================================================
// CARTA — tela screen-carta
// ============================================================
(function () {

  // Atualiza a tela carta com dados do ClubeBulbe
  async function renderCarta() {
    try { await ClubeBulbe.refresh(); } catch (error) { BulbeAPI.report(error); return; }
    const s = ClubeBulbe.getState();
    const streak = s.semanaStreak;
    const meta = 5;
    const streakText = streak === 1 ? '1 semana' : `${streak} semanas`;
    document.getElementById('carta-numero-streak').textContent = streakText;
    const faltam = Math.max(0, meta - streak);
    document.getElementById('carta-sub-streak').textContent = faltam === 0
      ? 'Bônus especial desbloqueado! 🎁'
      : faltam === 1 ? 'Mais 1 semana e você ganha o bônus especial'
      : `Mais ${faltam} semanas e você ganha o bônus especial`;
    const pct = Math.min(100, Math.round((streak / meta) * 100));
    document.getElementById('carta-barra-fill').style.width = `${pct}%`;
    document.getElementById('carta-label-atual').textContent = `${streak} de 5`;
    document.getElementById('carta-progresso-label').textContent = faltam === 0
      ? 'Você conquistou o bônus especial! 🎉'
      : faltam === 1 ? 'Falta apenas 1 semana para o bônus especial!'
      : `Faltam apenas ${faltam} semanas para o bônus especial!`;
  }

  document.getElementById('carta-btn-abrir').addEventListener('click', async () => {
    try {
    if (ClubeBulbe.getState().especialPendente) {
      navigateTo('screen-bonus-extra');
      return;
    }
    const cupom = await ClubeBulbe.abrirCarta();
    populateRecompensaScreen(cupom);
    navigateTo('screen-recompensa-carta');
    } catch (error) { BulbeAPI.report(error); }
  });

  window._onCarta = renderCarta;
}());

// ============================================================
// RECOMPENSA CARTA — tela screen-recompensa-carta
// ============================================================
(function () {

  function mostrarPopup(id) {
    const el = document.getElementById(id);
    el.classList.add('visivel');
    setTimeout(() => el.classList.remove('visivel'), 3000);
  }

  // Popula a tela com os dados do cupom atual
  window.populateRecompensaScreen = function (cupom) {
    if (!cupom) return;
    const MESES = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
    const dv = cupom.dataVencimento ? new Date(cupom.dataVencimento) : (() => { const d = new Date(2026,4,29); d.setDate(d.getDate()+cupom.diaExpiracao); return d; })();
    const validadeStr = `${dv.getDate()} de ${MESES[dv.getMonth()]} de ${dv.getFullYear()}`;
    document.getElementById('rc-tag').textContent     = cupom.tag;
    document.getElementById('rc-logo').src            = cupom.logo;
    document.getElementById('rc-logo').alt            = cupom.empresa;
    document.getElementById('rc-titulo').textContent  = cupom.titulo;
    document.getElementById('rc-desc').textContent    = cupom.descricao;
    document.getElementById('rc-cupom-codigo').textContent = cupom.codigo;
    const validadeEl = document.getElementById('rc-validade');
    validadeEl.textContent = cupom.especial ? '' : `Válido até ${validadeStr}`;
    validadeEl.style.display = cupom.especial ? 'none' : '';
    document.getElementById('rc-btn-copiar').textContent   = 'Copiar';
    document.getElementById('screen-recompensa-carta').classList.toggle('especial', !!cupom.especial);
  };

  // Hook: ao navegar para esta tela, carrega recompensa atual
  window._onRecompensa = function () {
    const s = ClubeBulbe.getState();
    window.populateRecompensaScreen(s.recompensaAtual);
  };

  document.getElementById('rc-btn-copiar').addEventListener('click', () => {
    navigator.clipboard.writeText(document.getElementById('rc-cupom-codigo').textContent).catch(() => {});
    mostrarPopup('rc-popup-copiado');
    const btn = document.getElementById('rc-btn-copiar');
    btn.textContent = 'Copiado!';
    setTimeout(() => { btn.textContent = 'Copiar'; }, 3000);
  });

  function concluir(popupId) {
    mostrarPopup(popupId);
    setTimeout(() => {
      ClubeBulbe.fecharCarta();
      window._onVantagens?.();
      navigateTo('screen-vantagens');
    }, 1800);
  }

  document.getElementById('rc-btn-voltar').addEventListener('click', () => {
    ClubeBulbe.fecharCarta(); navigateTo('screen-vantagens');
  });
  document.getElementById('rc-btn-salvar').addEventListener('click', async () => {
    try { await ClubeBulbe.salvarCupom('salvo'); concluir('rc-popup-salvo'); }
    catch (error) { BulbeAPI.report(error); }
  });
}());

// ============================================================
// STATUS / DETALHES — API real, sem avanço local de etapas.
// ============================================================
window._onAtivacao = async function () {
  document.getElementById('st-progresso-pct').textContent = '—';
  document.getElementById('st-progresso-num').textContent = '—';
  document.getElementById('det-numero-etapa').textContent = '—';
  document.getElementById('det-status-titulo').textContent = '—';
  document.getElementById('det-status-descricao').textContent = '—';
  document.querySelectorAll('.st-etapa-card, .st-circles').forEach(el => el.style.display = 'none');
  try {
    const path = BulbeAPI.clientePath();
    const [resumo, etapas] = await Promise.all([
      BulbeAPI.request(path + '/ativacao'), BulbeAPI.request(path + '/ativacao/etapas')
    ]);
    const etapa = resumo.etapa_atual;
    const screen = document.getElementById('screen-status');
    document.getElementById('st-progresso-pct').textContent = `${resumo.percentual_concluido}%`;
    document.getElementById('st-progresso-num').textContent = etapa;
    screen.querySelectorAll('.st-circles').forEach(el => el.style.display = 'none');
    screen.querySelector(`.st-etapa_${etapa}.st-circles`)?.style.setProperty('display', 'grid');
    screen.querySelectorAll('.st-etapa-card').forEach(el => el.style.display = 'none');
    const card = screen.querySelector(`.st-etapa_${etapa}.st-etapa-card`);
    if (card) {
      card.style.display = 'block';
      card.querySelector('.st-etapa-titulo').textContent = resumo.titulo;
      card.querySelector('.st-etapa-desc').textContent = resumo.descricao;
    }
    screen.querySelectorAll('.st-jornada-labels span').forEach((el, i) => {
      el.classList.toggle('st-label-concluido', i < etapa - 1);
      el.classList.toggle('st-label-atual', i === etapa - 1);
    });
    document.getElementById('det-numero-etapa').textContent = etapa;
    document.getElementById('det-status-titulo').textContent = resumo.titulo;
    document.getElementById('det-status-descricao').textContent = resumo.descricao;
    document.querySelector('.det-progress-fill').style.width = `${(etapa - 1) / 4 * 100}%`;
    etapas.data.forEach(item => {
      const el = document.getElementById(`det-etapa-${item.numero}`);
      el.classList.toggle('det-concluido', item.situacao === 'concluida');
      el.classList.toggle('det-ativo', item.situacao === 'atual');
      el.classList.toggle('det-pendente', item.situacao === 'pendente');
      el.querySelector('h4').textContent = item.titulo;
      el.querySelector('small').textContent = item.descricao;
    });
    const item = document.getElementById(`det-etapa-${etapa}`);
    document.getElementById('det-timeline').style.setProperty('--det-progress-height', `${item.offsetTop + 22}px`);
  } catch (error) {
    document.getElementById('st-progresso-pct').textContent = '—';
    document.getElementById('st-progresso-num').textContent = '—';
    BulbeAPI.report(error);
  }
};
// Os controles do protótipo avançavam etapas sem persistência. Não representam uma ação do cliente.
['st-btn-proxima', 'st-btn-anterior', 'det-btn-avancar', 'det-btn-anterior'].forEach(id => {
  document.getElementById(id).addEventListener('click', () => BulbeAPI.report(new Error('Controle de demonstração indisponível na integração. A etapa é consultada na API.')));
});

// ============================================================
// SIMULADOR DE ECONOMIA
// ============================================================
(function () {
  let valorConta = 0;
  let meses = 3;
  let amigos = 0;

  const screen = document.getElementById('screen-simulador');

  const inputValor    = screen.querySelector('#sim-vlr-pago');
  const pills         = screen.querySelectorAll('.sim-pill');
  const principal     = screen.querySelector('#sim-custom-principal');
  const secundario    = screen.querySelector('#sim-custom-secundario');
  const customInput   = screen.querySelector('#sim-custom-meses');
  const btnOk         = secundario.querySelector('.sim-btn-ok');
  const contadorNum   = screen.querySelector('.sim-contador-num');
  const btnMenos      = screen.querySelector('.sim-btn-contador:not(.sim-btn-mais)');
  const btnMais       = screen.querySelector('.sim-btn-mais');
  const secEconomia   = screen.querySelector('.sim-sec-economia');
  const secComp       = screen.querySelector('.sim-sec-comp-mensal');

  inputValor.addEventListener('focus', () => {
    inputValor.value = `R$ ${valorConta > 0 ? simFmt(valorConta) : '0'}`;
    setTimeout(() => inputValor.setSelectionRange(inputValor.value.length, inputValor.value.length), 0);
  });

  inputValor.addEventListener('input', () => {
    const raw = inputValor.value.replace(/[^\d]/g, '');
    const num = raw ? parseInt(raw) : 0;
    const formatted = `R$ ${num > 0 ? num.toLocaleString('pt-BR') : '0'}`;
    inputValor.value = formatted;
    inputValor.setSelectionRange(formatted.length, formatted.length);
  });

  inputValor.addEventListener('blur', () => {
    const raw = parseInt(inputValor.value.replace(/[^\d]/g, ''));
    valorConta = isNaN(raw) || raw <= 0 ? 0 : raw;
    inputValor.value = `R$ ${simFmt(valorConta)}`;
    const temPill = [...pills].some(p => p.classList.contains('ativo'));
    if (valorConta > 0 && !temPill && secundario.classList.contains('oculto')) {
      pills[0].classList.add('ativo');
      meses = 3;
    }
    simAtualizar();
  });

  inputValor.addEventListener('keydown', (e) => { if (e.key === 'Enter') inputValor.blur(); });

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('ativo'));
      pill.classList.add('ativo');
      meses = pill.textContent.trim() === '1 ano' ? 12 : parseInt(pill.textContent);
      secundario.classList.add('oculto');
      principal.classList.remove('oculto');
      simAtualizar();
    });
  });

  principal.addEventListener('click', () => {
    pills.forEach(p => p.classList.remove('ativo'));
    principal.classList.add('oculto');
    secundario.classList.remove('oculto');
    customInput.focus();
  });

  customInput.addEventListener('input', () => {
    if (parseInt(customInput.value) < 1) customInput.value = 1;
  });

  btnOk.addEventListener('click', () => {
    const val = parseInt(customInput.value);
    meses = val >= 1 ? val : 1;
    customInput.value = meses;
    simAtualizar();
  });

  btnMais.addEventListener('click', () => {
    amigos++;
    contadorNum.value = amigos;
    simAtualizar();
  });

  btnMenos.addEventListener('click', () => {
    if (amigos <= 0) return;
    amigos--;
    contadorNum.value = amigos;
    simAtualizar();
  });

  contadorNum.addEventListener('input', () => {
    const val = parseInt(contadorNum.value);
    amigos = isNaN(val) || val < 0 ? 0 : val;
    contadorNum.value = amigos;
    simAtualizar();
  });

  contadorNum.addEventListener('keydown', (e) => { if (e.key === 'Enter') contadorNum.blur(); });

  let simRevision = 0;
  let simTimer;
  function simAtualizar() {
    const revision = ++simRevision;
    clearTimeout(simTimer);
    secEconomia.classList.add('oculto'); secComp.classList.add('oculto');
    screen.querySelector('#sim-poderia-total').textContent = '—';
    screen.querySelectorAll('.sim-poderia-card').forEach(c => c.classList.add('sim-poderia-bloqueado'));
    simTimer = setTimeout(() => simConsultar(revision), 350);
  }
  async function simConsultar(revision) {
    if (valorConta <= 0) {
      secEconomia.classList.add('oculto');
      secComp.classList.add('oculto');
      screen.querySelector('#sim-poderia-total').textContent = 'R$0';
      screen.querySelectorAll('.sim-poderia-card').forEach(c => c.classList.add('sim-poderia-bloqueado'));
      return;
    }

    try {
      const simulacao = await BulbeAPI.request('/v1/simulacoes', { method: 'POST', body: JSON.stringify({
        valor_atual: valorConta, valor_proposto: Math.max(0, valorConta * 0.85), periodo_meses: meses, indicacoes: amigos
      }) });
      if (revision !== simRevision) return;
      valorConta = simulacao.valor_atual; meses = simulacao.periodo_meses; amigos = simulacao.indicacoes;
    } catch (error) {
      if (revision === simRevision) BulbeAPI.report(error);
      return;
    }

    secEconomia.classList.remove('oculto');
    secComp.classList.remove('oculto');

    const descontoMensal = valorConta * 0.15;
    const descontoTotal  = descontoMensal * meses;
    const bonusTotal     = amigos * 50;
    const total          = descontoTotal + bonusTotal;
    const novaConta      = Math.max(0, valorConta - descontoMensal);
    const periodoLabel   = meses === 12 ? '1 ANO' : `${meses} ${meses === 1 ? 'MÊS' : 'MESES'}`;

    screen.querySelector('#sim-economia-titulo').textContent    = `ECONOMIA EM ${periodoLabel}`;
    screen.querySelector('#sim-economia-total').textContent     = simFmt(total);
    screen.querySelector('#sim-economia-descricao').textContent = `Sua fatura de R$${simFmt(valorConta)} cai para R$${simFmt(novaConta)} todo mês`;
    screen.querySelector('#sim-desconto-valor').textContent     = `R$${simFmt(descontoTotal)}`;
    screen.querySelector('#sim-desconto-pct').textContent       = `15% da conta`;
    screen.querySelector('#sim-bonus-valor').textContent        = `R$${simFmt(bonusTotal)}`;
    screen.querySelector('#sim-bonus-sub').textContent          = `${amigos} amigo${amigos !== 1 ? 's' : ''} × R$50`;

    screen.querySelector('#sim-poderia-total').textContent = `R$${simFmt(total)}`;
    const precos = [150, 70, 150, 30, 50, 200];
    precos.forEach((preco, i) => {
      const mult = Math.max(1, Math.floor(total / preco));
      const el = screen.querySelector(`#sim-mult-${i}`);
      el.textContent = `${mult}x`;
      const card = el.closest('.sim-poderia-card');
      card.classList.toggle('sim-poderia-bloqueado', total < preco);
    });

    const periodoTexto = meses === 1 ? 'Por 1 mês' : meses === 12 ? 'Por 1 ano' : `Por ${meses} meses`;
    screen.querySelector('#sim-comp-sem-mensal').textContent        = `R$${simFmt(valorConta)}`;
    screen.querySelector('#sim-comp-sem-periodo-label').textContent = periodoTexto;
    screen.querySelector('#sim-comp-sem-periodo').textContent       = `R$${simFmt(valorConta * meses)}`;
    screen.querySelector('#sim-comp-com-mensal').textContent        = `R$${simFmt(novaConta)}`;
    screen.querySelector('#sim-comp-com-periodo-label').textContent = periodoTexto;
    screen.querySelector('#sim-comp-com-periodo').textContent       = `R$${simFmt(novaConta * meses)}`;
  }

  function simFmt(n) {
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }
}());

// ============================================================
// SIMULADOR LOGADO
// ============================================================
(function () {
  let valorConta = 0;
  let meses = 3;
  let amigos = 0;

  const screen     = document.getElementById('screen-simulador-logado');
  const inputValor = screen.querySelector('#slog-vlr-pago');
  const pills      = screen.querySelectorAll('.slog-pills .sim-pill');
  const principal  = screen.querySelector('#slog-custom-principal');
  const secundario = screen.querySelector('#slog-custom-secundario');
  const customInput = screen.querySelector('#slog-custom-meses');
  const btnOk      = secundario.querySelector('.sim-btn-ok');
  const contadorNum = screen.querySelector('#slog-contador-input');
  const btnMenos   = screen.querySelector('.slog-btn-menos');
  const btnMais    = screen.querySelector('.slog-btn-mais');
  const secEconomia = screen.querySelector('#slog-sec-economia');
  const secComp    = screen.querySelector('#slog-sec-comp');

  inputValor.addEventListener('focus', () => {
    inputValor.value = `R$ ${valorConta > 0 ? slogFmt(valorConta) : '0'}`;
    setTimeout(() => inputValor.setSelectionRange(inputValor.value.length, inputValor.value.length), 0);
  });

  inputValor.addEventListener('input', () => {
    const raw = inputValor.value.replace(/[^\d]/g, '');
    const num = raw ? parseInt(raw) : 0;
    const formatted = `R$ ${num > 0 ? num.toLocaleString('pt-BR') : '0'}`;
    inputValor.value = formatted;
    inputValor.setSelectionRange(formatted.length, formatted.length);
  });

  inputValor.addEventListener('blur', () => {
    const raw = parseInt(inputValor.value.replace(/[^\d]/g, ''));
    valorConta = isNaN(raw) || raw <= 0 ? 0 : raw;
    inputValor.value = `R$ ${slogFmt(valorConta)}`;
    const temPill = [...pills].some(p => p.classList.contains('ativo'));
    if (valorConta > 0 && !temPill && secundario.classList.contains('oculto')) {
      pills[0].classList.add('ativo');
      meses = 3;
    }
    slogAtualizar();
  });

  inputValor.addEventListener('keydown', (e) => { if (e.key === 'Enter') inputValor.blur(); });

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('ativo'));
      pill.classList.add('ativo');
      meses = pill.textContent.trim() === '1 ano' ? 12 : parseInt(pill.textContent);
      secundario.classList.add('oculto');
      principal.classList.remove('oculto');
      slogAtualizar();
    });
  });

  principal.addEventListener('click', () => {
    pills.forEach(p => p.classList.remove('ativo'));
    principal.classList.add('oculto');
    secundario.classList.remove('oculto');
    customInput.focus();
  });

  customInput.addEventListener('input', () => { if (parseInt(customInput.value) < 1) customInput.value = 1; });

  btnOk.addEventListener('click', () => {
    meses = parseInt(customInput.value) >= 1 ? parseInt(customInput.value) : 1;
    customInput.value = meses;
    slogAtualizar();
  });

  btnMais.addEventListener('click',  () => { amigos++; contadorNum.value = amigos; slogAtualizar(); });
  btnMenos.addEventListener('click', () => { if (amigos <= 0) return; amigos--; contadorNum.value = amigos; slogAtualizar(); });

  contadorNum.addEventListener('input', () => {
    const val = parseInt(contadorNum.value);
    amigos = isNaN(val) || val < 0 ? 0 : val;
    contadorNum.value = amigos;
    slogAtualizar();
  });

  contadorNum.addEventListener('keydown', (e) => { if (e.key === 'Enter') contadorNum.blur(); });

  let slogRevision = 0;
  let slogTimer;
  function slogAtualizar() {
    const revision = ++slogRevision;
    clearTimeout(slogTimer);
    secEconomia.classList.add('oculto'); secComp.classList.add('oculto');
    screen.querySelector('#slog-poderia-total').textContent = '—';
    screen.querySelectorAll('.sim-poderia-card').forEach(c => c.classList.add('sim-poderia-bloqueado'));
    slogTimer = setTimeout(() => slogConsultar(revision), 350);
  }
  async function slogConsultar(revision) {
    if (valorConta <= 0) {
      secEconomia.classList.add('oculto');
      secComp.classList.add('oculto');
      screen.querySelector('#slog-poderia-total').textContent = 'R$0';
      screen.querySelectorAll('.sim-poderia-card').forEach(c => c.classList.add('sim-poderia-bloqueado'));
      return;
    }

    try {
      const simulacao = await BulbeAPI.request('/v1/simulacoes', { method: 'POST', body: JSON.stringify({
        valor_atual: valorConta, valor_proposto: Math.max(0, valorConta * 0.85), periodo_meses: meses, indicacoes: amigos
      }) });
      if (revision !== slogRevision) return;
      valorConta = simulacao.valor_atual; meses = simulacao.periodo_meses; amigos = simulacao.indicacoes;
    } catch (error) {
      if (revision === slogRevision) BulbeAPI.report(error);
      return;
    }

    secEconomia.classList.remove('oculto');
    secComp.classList.remove('oculto');

    const descontoMensal = valorConta * 0.15;
    const descontoTotal  = descontoMensal * meses;
    const bonusTotal     = amigos * 50;
    const total          = descontoTotal + bonusTotal;
    const novaConta      = Math.max(0, valorConta - descontoMensal);
    const periodoLabel   = meses === 12 ? '1 ANO' : `${meses} ${meses === 1 ? 'MÊS' : 'MESES'}`;

    screen.querySelector('#slog-economia-titulo').textContent    = `ECONOMIA EM ${periodoLabel}`;
    screen.querySelector('#slog-economia-total').textContent     = slogFmt(total);
    screen.querySelector('#slog-economia-descricao').textContent = `Sua fatura de R$${slogFmt(valorConta)} cai para R$${slogFmt(novaConta)} todo mês`;
    screen.querySelector('#slog-desconto-valor').textContent     = `R$${slogFmt(descontoTotal)}`;
    screen.querySelector('#slog-desconto-pct').textContent       = `15% da conta`;
    screen.querySelector('#slog-bonus-valor').textContent        = `R$${slogFmt(bonusTotal)}`;
    screen.querySelector('#slog-bonus-sub').textContent          = `${amigos} amigo${amigos !== 1 ? 's' : ''} × R$50`;

    screen.querySelector('#slog-poderia-total').textContent = `R$${slogFmt(total)}`;
    [150, 70, 150, 30, 50, 200].forEach((preco, i) => {
      const el = screen.querySelector(`#slog-mult-${i}`);
      el.textContent = `${Math.max(1, Math.floor(total / preco))}x`;
      el.closest('.sim-poderia-card').classList.toggle('sim-poderia-bloqueado', total < preco);
    });

    const periodoTexto = meses === 1 ? 'Por 1 mês' : meses === 12 ? 'Por 1 ano' : `Por ${meses} meses`;
    screen.querySelector('#slog-comp-sem-mensal').textContent        = `R$${slogFmt(valorConta)}`;
    screen.querySelector('#slog-comp-sem-periodo-label').textContent = periodoTexto;
    screen.querySelector('#slog-comp-sem-periodo').textContent       = `R$${slogFmt(valorConta * meses)}`;
    screen.querySelector('#slog-comp-com-mensal').textContent        = `R$${slogFmt(novaConta)}`;
    screen.querySelector('#slog-comp-com-periodo-label').textContent = periodoTexto;
    screen.querySelector('#slog-comp-com-periodo').textContent       = `R$${slogFmt(novaConta * meses)}`;
  }

  function slogFmt(n) {
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }
}());

// ============================================================
// VANTAGENS
// ============================================================
(function () {
  const sc = document.getElementById('screen-vantagens');

  const estado = { semanaStreak: 0, meta: 5 }; // estado local mínimo — fonte de verdade é ClubeBulbe

  const MESES_FULL = ['JANEIRO','FEVEREIRO','MARÇO','ABRIL','MAIO','JUNHO','JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO'];
  const DIAS_SEMANA = ['DOMINGO','SEGUNDA','TERÇA','QUARTA','QUINTA','SEXTA','SÁBADO'];

  function renderizarDots() {
    sc.querySelectorAll('#van-streak-dots span').forEach((span, i) => {
      span.classList.toggle('ativo', i < estado.semanaStreak);
    });
  }

  function mostrarPopup(id) {
    const p = sc.querySelector(`#${id}`);
    p.classList.add('visivel');
    setTimeout(() => p.classList.remove('visivel'), 2500);
  }

  function calcularDataCarta() {
    const data = ClubeBulbe.getState().proximaData;
    return data ? new Date(data).toLocaleString('pt-BR') : '—';
  }

  function atualizarCard() {
    const cb = ClubeBulbe.getState();
    const s = cb.semanaStreak;
    const { meta } = estado;
    const cartaDisponivel = ClubeBulbe.isCartaDisponivel();
    const diasParaProxima = Math.max(0, cb.diaProximaCarta - cb.diaSimulado);

    const ehEspecial = cartaDisponivel && cb.especialPendente;
    const txtDias = cartaDisponivel ? 'Sua carta chegou! ✨' : diasParaProxima === 1 ? 'Em 1 dia' : `Em ${diasParaProxima} dias`;
    sc.querySelector('#van-titulo-dias').textContent = txtDias;
    sc.querySelector('#van-card-proxima-carta').classList.toggle('dia-zero', cartaDisponivel && !ehEspecial);
    sc.querySelector('#van-card-proxima-carta').classList.toggle('estado-especial', ehEspecial);
    sc.querySelector('#van-texto-semanas').textContent = ehEspecial ? '5 semanas seguidas!' : s === 0 ? 'Comece sua sequência!' : s === 1 ? '1 semana seguida!' : `${s} semanas seguidas!`;
    sc.querySelector('#van-texto-bonus').textContent = `Mais ${meta - s} e ganho bônus especial`;
    sc.querySelector('#van-carta-data').textContent = calcularDataCarta();
    const boasVindas = sc.querySelector('#van-boas-vindas');
    if (boasVindas) boasVindas.style.display = (cartaDisponivel && s === 0) ? 'block' : 'none';
    estado.semanaStreak = s;
    renderizarDots();

    const btnPassar = document.getElementById('van-btn-passar-dia');
    const btnVoltar = document.getElementById('van-btn-voltar-dia');
    const recentementeAbriu = cb.diaProximaCarta - cb.diaSimulado === 7;
    if (btnPassar) btnPassar.disabled = cartaDisponivel;
    if (btnVoltar) btnVoltar.disabled = cb.diaSimulado === 0 || cb.especialPendente || recentementeAbriu;
  }

  document.getElementById('van-btn-voltar-dia').addEventListener('click', () => {
    BulbeAPI.report(new Error('A API não oferece alteração de data.'));
    renderizarCupons(); renderizarHistorico(); atualizarCard();
  });

  document.getElementById('van-btn-passar-dia').addEventListener('click', () => {
    BulbeAPI.report(new Error('A API não oferece alteração de data.'));
    renderizarCupons(); renderizarHistorico(); atualizarCard();
  });

  function resetarVantagens() {
    BulbeAPI.report(new Error('A API não oferece reset do clube.'));
    renderizarCupons(); renderizarHistorico(); atualizarCard();
  }

  document.getElementById('van-btn-resetar').addEventListener('click', resetarVantagens);

  window._resetarVantagens = resetarVantagens;

  function renderizarCupons() {
    const cb = ClubeBulbe.getState();
    const dia = cb.diaSimulado;
    const ativas = cb.cupons.filter(cu => dia < cu.diaExpiracao);
    sc.querySelector('#van-titulo-cupons').textContent = `Cartas ativas`;
    const c = sc.querySelector('#van-container-cupons');
    if (!ativas.length) { c.innerHTML = `<div class="van-empty-state"><p class="van-empty-title">Nenhum benefício</p><p class="van-empty-sub">Abra sua carta semanal para desbloquear benefícios exclusivos</p></div>`; return; }
    const ul = document.createElement('ul'); ul.className = 'van-lista-cupons';
    ativas.forEach(cu => {
      const diasRestantes = cu.diaExpiracao - dia;
      const venceHtml = cu.especial ? '' : `<p class="van-cupom-vence">⏰ Vence em ${diasRestantes} dia${diasRestantes !== 1 ? 's' : ''}</p>`;
      const li = document.createElement('li');
      li.innerHTML = `<img src="${BulbeAPI.escape(cu.logo)}" alt="${BulbeAPI.escape(cu.empresa)}"><div><strong>${BulbeAPI.escape(cu.empresa)}</strong><p>${BulbeAPI.escape(cu.titulo)}</p>${venceHtml}</div><img src="icons_final/cf-chevron-right.svg" alt="">`;
      li.addEventListener('click', async () => {
        try { const cupom = await ClubeBulbe.selecionarCupom(cu.id); window.populateRecompensaScreen(cupom); navigateTo('screen-recompensa-carta'); }
        catch (error) { BulbeAPI.report(error); }
      });
      ul.appendChild(li);
    });
    c.innerHTML = ''; c.appendChild(ul);
  }

  function renderizarHistorico() {
    const cb = ClubeBulbe.getState();
    const dia = cb.diaSimulado;
    const c = sc.querySelector('#van-container-historico');
    if (!c) return;
    if (!cb.cartas.length) { c.innerHTML = `<div class="van-empty-state"><p class="van-empty-title">Nenhuma carta no histórico</p><p class="van-empty-sub">Suas cartas abertas aparecerão aqui</p></div>`; return; }
    const ul = document.createElement('ul'); ul.className = 'van-lista-cartas';
    cb.cartas.forEach(carta => {
      const li = document.createElement('li');
      const img = document.createElement('img'); img.src = 'icons_final/van-carta.svg'; img.className = 'van-carta-logo'; img.alt = '';
      const div = document.createElement('div'); const p = document.createElement('p'); p.textContent = `Carta ${carta.semana}`; div.append(p);
      const badge = document.createElement('span'); badge.className = 'van-badge-status'; badge.textContent = carta.situacao.toUpperCase();
      li.append(img, div, badge); ul.append(li);
    });
    c.innerHTML = ''; c.appendChild(ul);
  }

  async function abrirTelaRecompensa() {
    try {
      const cupom = await ClubeBulbe.abrirCarta();
      window.populateRecompensaScreen(cupom);
      sc.querySelector('#van-tela-carta').classList.remove('ativo');
      navigateTo('screen-recompensa-carta');
    } catch (error) { BulbeAPI.report(error); }
  }

  // Eventos
  sc.querySelector('#van-card-proxima-carta').addEventListener('click', () => {
    if (ClubeBulbe.isCartaDisponivel()) {
      const cb = ClubeBulbe.getState();
      if (cb.especialPendente) {
        navigateTo('screen-bonus-extra');
        return;
      }
      const base = new Date(cb.proximaData);
      document.getElementById('carta-data-label').textContent = `${DIAS_SEMANA[base.getDay()]} - ${String(base.getDate()).padStart(2, '0')} DE ${MESES_FULL[base.getMonth()]}`;
      navigateTo('screen-carta');
    } else {
      BulbeAPI.report(new Error('Nenhuma carta disponível na API.'));
    }
  });
  sc.querySelector('#van-voltar-carta').addEventListener('click', () => sc.querySelector('#van-tela-carta').classList.remove('ativo'));
  sc.querySelector('#van-btn-abrir-envelope').addEventListener('click', abrirTelaRecompensa);
  sc.querySelector('#van-btn-abrir-envelope-especial').addEventListener('click', abrirTelaRecompensa);
  sc.querySelector('#van-btn-abrir-carta').addEventListener('click', abrirTelaRecompensa);
  sc.querySelector('#van-btn-abrir-bonus').addEventListener('click', abrirTelaRecompensa);
  sc.querySelector('#van-voltar-recompensa').addEventListener('click', () => sc.querySelector('#van-tela-recompensa').classList.remove('ativo'));

  sc.querySelector('#van-btn-copiar').addEventListener('click', () => {
    const cod = sc.querySelector('#van-cupom-codigo-valor');
    navigator.clipboard.writeText(cod.textContent).catch(() => {});
    mostrarPopup('van-popup-copiado');
    const btn = sc.querySelector('#van-btn-copiar'); btn.textContent = 'Copiado!';
    setTimeout(() => { btn.textContent = 'Copiar'; }, 2500);
  });

  sc.querySelector('#van-btn-salvar').addEventListener('click', async () => { try { await ClubeBulbe.salvarCupom('salvo'); navigateTo('screen-vantagens'); } catch (error) { BulbeAPI.report(error); } });
  sc.querySelector('#van-btn-usar').addEventListener('click', async () => { try { await ClubeBulbe.salvarCupom('usado'); navigateTo('screen-vantagens'); } catch (error) { BulbeAPI.report(error); } });

  // FAQ
  const respostasFAQ = [
    'Você recebe sua carta toda semana no mesmo dia e horário.',
    'Copie o código do cupom e use no site ou app do parceiro.',
    'Sua carta fica disponível por 7 dias. Perder uma semana zera sua sequência.'
  ];
  sc.querySelectorAll('.van-lista-faq li').forEach((item, i) => {
    const seta = item.querySelector('img');
    item.addEventListener('click', () => {
      const existente = item.querySelector('.van-faq-resposta');
      if (existente) { existente.remove(); item.style.flexWrap = 'nowrap'; seta.style.transform = 'rotate(0deg)'; return; }
      const r = document.createElement('div'); r.className = 'van-faq-resposta'; r.textContent = respostasFAQ[i];
      r.style.cssText = 'width:100%;margin-top:14px;padding:12px;border-radius:8px;background-color:#F5F7FA;font-size:12px;line-height:1.5;color:#3E4D5B;border:1px solid #D1D9E0';
      item.style.flexWrap = 'wrap'; seta.style.transform = 'rotate(90deg)'; seta.style.transition = 'transform .3s';
      item.appendChild(r);
    });
  });

  // Hook: ao navegar de volta para vantagens, re-renderiza tudo a partir do ClubeBulbe
  window._onVantagens = async function () {
    sc.querySelector('.van-lista-parceiros').replaceChildren();
    try { await ClubeBulbe.refresh(); } catch (error) { renderizarCupons(); renderizarHistorico(); atualizarCard(); BulbeAPI.report(error); return; }
    renderizarCupons(); renderizarHistorico(); atualizarCard();
    const list = sc.querySelector('.van-lista-parceiros'); list.replaceChildren();
    ClubeBulbe.getState().parceiros.forEach(parceiro => {
      const li = document.createElement('li');
      const img = document.createElement('img'); img.src = BulbeAPI.partnerLogo(parceiro); img.alt = parceiro.nome;
      const p = document.createElement('p'); p.textContent = parceiro.nome;
      const small = document.createElement('small'); small.textContent = parceiro.categoria;
      li.append(img, p, small); list.append(li);
    });
  };

  sc.querySelector('.van-secao-header a').addEventListener('click', e => { e.preventDefault(); window._onVantagens(); });
  atualizarCard(); renderizarCupons(); renderizarHistorico();
}());

// ============================================================
// BÔNUS EXTRA — screen-bonus-extra
// ============================================================
(function () {
  document.getElementById('be-btn-abrir-envelope').addEventListener('click', async () => {
    try {
    const cupom = await ClubeBulbe.abrirCarta();
    window.populateRecompensaScreen(cupom);
    navigateTo('screen-recompensa-carta');
    } catch (error) { BulbeAPI.report(error); }
  });
}());

// Entrar preserva a navegação original, sem apagar dados do cliente
document.querySelector('.primary-button[data-nav="screen-status"]').addEventListener('click', () => {
  // Entrar continua sendo navegação: o protótipo não possui formulário de autenticação.
});

// ============================================================
// TELA: TRILHA
// ============================================================
(function () {
  const primeiraCaixa  = document.getElementById('primeira-caixa');
  const segundaCaixa   = document.getElementById('segunda-caixa');
  const terceiraCaixa  = document.getElementById('terceira-caixa');
  const quartaCaixa    = document.getElementById('quarta-caixa');
  const titulo         = document.getElementById('titulo');
  const botaoIniciar   = document.getElementById('iniciar-trilha');
  const botaoAvancar   = document.getElementById('avancar');
  const resetBtn       = document.getElementById('reset-btn');
  const tabuleiro      = document.getElementById('tabuleiro');

  let currentStep = 0;

  function showEl(el) { if (el) el.classList.remove('hidden'); }
  function hideEl(el) { if (el) el.classList.add('hidden'); }

  function iniciarTrilha() {
    hideEl(titulo);
    hideEl(botaoIniciar);
    tabuleiro.className = 'tabuleiro-mapa etapa-1';
    setTimeout(() => {
      showEl(primeiraCaixa);
      currentStep = 1;
      setTimeout(() => botaoAvancar.classList.remove('hidden'), 140);
    }, 260);
  }

  function proximoPasso() {
    if (currentStep === 1) {
      hideEl(primeiraCaixa);
      botaoAvancar.classList.add('hidden');
      tabuleiro.className = 'tabuleiro-mapa etapa-2';
      setTimeout(() => {
        showEl(segundaCaixa);
        currentStep = 2;
        setTimeout(() => botaoAvancar.classList.remove('hidden'), 140);
      }, 260);
      return;
    }
    if (currentStep === 2) {
      hideEl(segundaCaixa);
      botaoAvancar.classList.add('hidden');
      tabuleiro.className = 'tabuleiro-mapa etapa-3';
      setTimeout(() => {
        showEl(terceiraCaixa);
        currentStep = 3;
        setTimeout(() => botaoAvancar.classList.remove('hidden'), 140);
      }, 260);
      return;
    }
    if (currentStep === 3) {
      hideEl(terceiraCaixa);
      botaoAvancar.classList.add('hidden');
      tabuleiro.className = 'tabuleiro-mapa etapa-4';
      setTimeout(() => {
        showEl(quartaCaixa);
        currentStep = 4;
        setTimeout(() => resetBtn.classList.remove('hidden'), 140);
      }, 260);
      return;
    }
  }

  function resetTrilha() {
    tabuleiro.className = 'tabuleiro-mapa';
    resetBtn.classList.add('hidden');
    hideEl(primeiraCaixa);
    hideEl(segundaCaixa);
    hideEl(terceiraCaixa);
    hideEl(quartaCaixa);
    botaoAvancar.classList.add('hidden');
    setTimeout(() => {
      showEl(titulo);
      showEl(botaoIniciar);
    }, 80);
    currentStep = 0;
  }

  if (botaoIniciar) botaoIniciar.addEventListener('click', iniciarTrilha);
  if (botaoAvancar) botaoAvancar.addEventListener('click', proximoPasso);
  if (resetBtn) resetBtn.addEventListener('click', () => {
    resetBtn.classList.add('animate');
    setTimeout(() => {
      resetBtn.classList.remove('animate');
      resetTrilha();
    }, 520);
  });

  window._onTrilha = resetTrilha;
}());
