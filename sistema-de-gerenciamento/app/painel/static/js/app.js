/* ============================================================
   PAINEL BULBE — aplicação: rotas por hash, menu, topo e início
   Rotas: #/visao-geral, #/clientes, #/cliente/<id>, #/adesoes, #/atendimentos,
   #/atendimento/<id>, #/ativacoes, #/dicas, #/parceiros, #/usinas e (admin)
   #/auditoria e #/uso-assistente. Cada tela é um módulo de js/telas/.
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;

  /** Rotas com parâmetro: "#/cliente/<id>" usa a tela "ficha" e marca "clientes" no menu. */
  var ROTAS_COM_ID = { cliente: { tela: 'ficha', menu: 'clientes' }, atendimento: { tela: 'atendimento', menu: 'atendimentos' } };
  var limpezas = [];
  var sequencia = 0;

  function lerRota() {
    var hash = (window.location.hash || '').replace(/^#\/?/, '');
    var partes = hash.split('/');
    var base = partes[0] || 'visao-geral';
    if (ROTAS_COM_ID[base] && partes[1]) {
      var id;
      try { id = decodeURIComponent(partes.slice(1).join('/')); } catch (e) { id = partes[1]; }
      return { tela: ROTAS_COM_ID[base].tela, menu: ROTAS_COM_ID[base].menu, parametro: id };
    }
    if (!P.telas[base] || base === 'ficha' || base === 'atendimento') base = 'visao-geral';
    return { tela: base, menu: base, parametro: null };
  }

  function limpar() {
    limpezas.splice(0).forEach(function (fn) { try { fn(); } catch (e) { /* ignora */ } });
  }

  function navegar() {
    limpar();
    var rota = lerRota();
    var def = P.telas[rota.tela];
    var seq = ++sequencia;

    document.querySelectorAll('.menu-item').forEach(function (item) {
      if (item.getAttribute('data-rota') === rota.menu) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
    P.$('barra-titulo').textContent = def.titulo;
    document.title = def.titulo + ' · Painel Bulbe';

    var conteudo = P.$('conteudo');
    var secao = document.createElement('section');
    secao.className = 'tela';
    secao.setAttribute('data-tela', rota.tela);
    conteudo.textContent = '';
    conteudo.appendChild(secao);
    window.scrollTo(0, 0);

    if (def.admin && P.estado.funcionario && !P.ehAdmin()) {
      secao.innerHTML = P.cabecalhoTela(def.titulo, def.descricao) +
        '<div class="aviso aviso-alerta" role="alert">Esta tela é restrita a administradores.</div>';
      return;
    }
    var ctx = {
      aoSair: function (fn) { limpezas.push(fn); },
      ativa: function () { return seq === sequencia; },
      recarregar: function () { if (seq === sequencia) navegar(); }
    };
    try {
      var resultado = def.montar(secao, rota.parametro, ctx);
      if (resultado && resultado.catch) resultado.catch(function (erro) { if (erro.status !== 401) secao.innerHTML += P.htmlErro(erro); });
    } catch (erro) {
      secao.innerHTML = P.htmlErro(erro);
    }
    var titulo = secao.querySelector('.tela-titulo, h1');
    if (titulo) titulo.focus({ preventScroll: true });
  }
  P.navegar = navegar;

  /* ---------------- topo: funcionário, menu admin ---------------- */
  function mostrarFuncionario(f) {
    var alvo = P.$('funcionario-info');
    if (!f || !f.nome) { alvo.textContent = ''; return; }
    alvo.innerHTML = '<span class="avatar" aria-hidden="true">' + esc(P.iniciais(f.nome)) + '</span>' +
      '<div><strong>' + esc(f.nome) + '</strong><span>' + esc(P.rotulo(f.perfil)) + '</span></div>';
  }
  function aplicarPerfilNoMenu() {
    var admin = P.ehAdmin();
    P.$('menu-admin').hidden = !admin;
    P.$('menu-secao-admin').hidden = !admin;
  }

  /* ---------------- relógio de demonstração ----------------
     O app usa um "relógio" que pode ser adiantado só para a apresentação
     (cartas semanais do Clube, validade de cupons). Some em produção. */
  async function carregarRelogio() {
    var alvo = P.$('relogio');
    try {
      var r = await P.api('/v1/painel/demonstracao/relogio');
      if (!r || !r.modo_demonstracao) { alvo.hidden = true; return; }
      desenharRelogio(r);
    } catch (e) {
      alvo.hidden = true;
    }
  }
  function desenharRelogio(r) {
    var alvo = P.$('relogio');
    var dias = Number(r.dias_adiantados) || 0;
    var botoes = P.ehAdmin()
      ? '<button type="button" class="botao botao-secundario botao-pequeno" data-relogio="1" title="Adiantar o app em 1 dia">+1 dia</button>' +
        '<button type="button" class="botao botao-secundario botao-pequeno" data-relogio="7" title="Adiantar o app em 7 dias (1 semana do Clube)">+7 dias</button>' +
        (dias ? '<button type="button" class="botao botao-fantasma botao-pequeno" data-relogio="hoje" title="Voltar para a data real">Hoje</button>' : '')
      : '';
    alvo.innerHTML = '<span>Data do app: <strong>' + esc(P.data(r.hoje)) + '</strong>' +
      (dias ? ' <span class="texto-suave">(+' + esc(dias) + ' dia' + (dias === 1 ? '' : 's') + ')</span>' : '') + '</span>' + botoes;
    alvo.hidden = false;
  }
  async function mexerNoRelogio(botao) {
    var valor = botao.getAttribute('data-relogio');
    try {
      var r = await P.comBotao(botao, function () {
        return valor === 'hoje'
          ? P.api('/v1/painel/demonstracao/relogio/resetar', { metodo: 'POST' })
          : P.api('/v1/painel/demonstracao/relogio/avancar', { metodo: 'POST', corpo: { dias: Number(valor) } });
      });
      desenharRelogio(r);
      P.toast(valor === 'hoje' ? 'O app voltou para a data real.' : 'App adiantado em ' + valor + ' dia(s): ' + P.data(r.hoje) + '.', 'ok');
      navegar();
    } catch (erro) { P.toastErro(erro); }
  }

  /* ---------------- contador de atendimentos abertos ---------------- */
  async function atualizarContador() {
    try {
      var r = P.normalizarPagina(await P.api('/v1/painel/atendimentos?status=aberto&por_pagina=1'));
      var alvo = P.$('contador-atendimentos');
      alvo.textContent = r.total > 99 ? '99+' : String(r.total);
      alvo.hidden = !r.total;
    } catch (e) { /* silencioso */ }
  }
  P.atualizarContadorAtendimentos = atualizarContador;

  /* ---------------- início ---------------- */
  async function iniciar() {
    if (!P.lerSessao(P.CHAVE_TOKEN)) { window.location.replace('/painel/index.html'); return; }
    try {
      var salvo = JSON.parse(P.lerSessao(P.CHAVE_FUNCIONARIO) || 'null');
      if (salvo && typeof salvo === 'object') { P.estado.funcionario = salvo; mostrarFuncionario(salvo); }
    } catch (e) { /* ignora */ }

    P.$('botao-sair').addEventListener('click', function () { P.sair('encerrada'); });
    P.$('relogio').addEventListener('click', function (e) {
      var botao = e.target.closest('button[data-relogio]');
      if (botao && !botao.disabled) mexerNoRelogio(botao);
    });
    window.addEventListener('hashchange', navegar);
    aplicarPerfilNoMenu();
    if (P.assistente) P.assistente.iniciar();
    navegar();

    try {
      var perfilAntes = P.estado.funcionario && P.estado.funcionario.perfil;
      P.estado.funcionario = await P.api('/v1/painel/me');
      mostrarFuncionario(P.estado.funcionario);
      aplicarPerfilNoMenu();
      if (perfilAntes !== P.estado.funcionario.perfil) navegar();
    } catch (e) { /* 401 já redireciona */ }
    carregarRelogio();
    atualizarContador();
    setInterval(atualizarContador, 20000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
