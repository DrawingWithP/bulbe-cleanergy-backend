/* ============================================================
   TELAS: Atendimentos (fila) e Atendimento (conversa com o cliente do app)
   O cliente fala primeiro com o assistente automático do app; se pedir,
   entra na fila "aguardando atendente" e o funcionário responde por aqui.
   GET  /v1/painel/atendimentos?status=           (fila, sincronizada do app)
   POST /v1/painel/atendimentos/atualizacao       (busca os novos agora)
   GET  /v1/painel/atendimentos/{id}/conversa?depois_de=<id da última mensagem>
   POST /v1/painel/atendimentos/{id}/respostas    {texto}
   POST /v1/painel/atendimentos/{id}/encerramento
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;
  var filtros = { status: 'aberto', por_pagina: '20', pagina: 1 };
  var INTERVALO_CONVERSA = 2500;
  var INTERVALO_FILA = 10000;

  function hashAtendimento(id) { return '#/atendimento/' + encodeURIComponent(id); }

  function linha(a) {
    var aguardando = a.status_app === 'aguardando_atendente';
    return '<tr class="clicavel' + (aguardando ? ' destaque-linha' : '') + '" data-href="' + esc(hashAtendimento(a.id)) + '">' +
      '<td>' + P.pessoa(a.cliente_nome, P.rotulo(a.canal) + (a.id_app ? ' · chat do app' : ''), hashAtendimento(a.id)) + '</td>' +
      '<td><strong>' + esc(P.ou(a.assunto)) + '</strong>' + (a.descricao ? '<small class="bloco texto-suave">' + esc(a.descricao) + '</small>' : '') + '</td>' +
      '<td>' + P.selo(a.status_app || a.status) + '</td>' +
      '<td>' + esc(P.ou(a.atendente_nome)) + '</td>' +
      '<td class="col-nowrap" title="' + esc(P.dataHora(a.atualizado_em || a.criado_em)) + '">' + esc(P.relativo(a.atualizado_em || a.criado_em)) + '</td></tr>';
  }

  function tabela(lista) {
    if (!lista.length) return P.htmlVazio('Nenhum atendimento com esse filtro.');
    return '<div class="tabela-rolagem"><table class="tabela"><caption class="visualmente-oculto">Atendimentos</caption><thead><tr>' +
      '<th>Cliente</th><th>Assunto</th><th>Situação</th><th>Atendente</th><th>Atualizado</th></tr></thead><tbody>' +
      lista.map(linha).join('') + '</tbody></table></div>';
  }

  P.tela('atendimentos', {
    titulo: 'Atendimentos',
    descricao: 'Conversas do “Fale conosco” do app. Clique em um atendimento para abrir o chat e responder o cliente.',
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        '<button type="button" class="botao botao-secundario botao-pequeno" data-acao="buscar">Buscar novos no app</button>') +
        '<div class="grade grade-kpi" data-alvo="kpis"></div>' +
        '<form class="filtros" data-form="filtros"><div class="campo"><label for="at-status">Situação</label><select id="at-status" name="status">' +
        '<option value="aberto">Abertos (assistente ou aguardando)</option><option value="em_andamento">Em atendimento</option>' +
        '<option value="resolvido">Resolvidos</option><option value="">Todos</option></select></div>' +
        '<p class="texto-suave">A lista se atualiza sozinha a cada 10 segundos.</p></form>' +
        '<div data-alvo="lista"></div>';
      var form = secao.querySelector('form');
      var alvo = secao.querySelector('[data-alvo="lista"]');
      var kpis = secao.querySelector('[data-alvo="kpis"]');
      form.querySelector('select').value = filtros.status;

      async function contar(status) {
        var r = await P.api('/v1/painel/atendimentos' + P.montarQuery({ status: status, por_pagina: 1 }));
        return P.normalizarPagina(r).total;
      }
      async function carregarKpis() {
        try {
          var t = await Promise.all([contar('aberto'), contar('em_andamento'), contar('resolvido')]);
          if (!ctx.ativa()) return;
          kpis.innerHTML = P.kpi('Abertos', P.numero(t[0]), 'com o assistente ou aguardando atendente', t[0] ? 'amarelo' : 'verde') +
            P.kpi('Em atendimento', P.numero(t[1]), 'conversando com a equipe', 'ciano') +
            P.kpi('Resolvidos', P.numero(t[2]), 'histórico total', 'verde');
        } catch (e) { kpis.innerHTML = ''; }
      }
      async function carregar(silencioso) {
        if (!silencioso) alvo.innerHTML = P.htmlCarregando('Carregando atendimentos...');
        try {
          var p = P.normalizarPagina(await P.api('/v1/painel/atendimentos' + P.montarQuery(filtros)));
          if (!ctx.ativa()) return;
          alvo.innerHTML = tabela(p.data) + P.htmlPaginacao(p, p.total === 1 ? 'atendimento' : 'atendimentos');
        } catch (erro) { if (!silencioso && erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }

      form.addEventListener('change', function () { filtros.status = form.querySelector('select').value; filtros.pagina = 1; carregar(); });
      form.addEventListener('submit', function (e) { e.preventDefault(); });
      secao.querySelector('[data-acao="buscar"]').addEventListener('click', async function (e) {
        try {
          await P.comBotao(e.currentTarget, function () { return P.api('/v1/painel/atendimentos/atualizacao', { metodo: 'POST' }); });
          await Promise.all([carregar(true), carregarKpis()]);
          if (P.atualizarContadorAtendimentos) P.atualizarContadorAtendimentos();
          P.toast('Atendimentos atualizados com o app.', 'ok');
        } catch (erro) { P.toastErro(erro); }
      });
      alvo.addEventListener('click', function (e) {
        var pag = e.target.closest('[data-pagina]');
        if (pag) { filtros.pagina = Number(pag.getAttribute('data-pagina')) || 1; carregar(); return; }
        if (e.target.closest('a, button')) return;
        var tr = e.target.closest('tr[data-href]');
        if (tr) window.location.hash = tr.getAttribute('data-href');
      });
      var timer = setInterval(function () { carregar(true); carregarKpis(); }, INTERVALO_FILA);
      ctx.aoSair(function () { clearInterval(timer); });
      carregarKpis();
      carregar();
    }
  });

  /* ======================= CONVERSA ======================= */

  var AUTORES = { cliente: 'Cliente', bot: 'Assistente automático', atendente: 'Atendente', sistema: '' };

  function bolha(m, nomeCliente, nomeAtendente) {
    var autor = AUTORES[m.autor] !== undefined ? m.autor : 'sistema';
    var div = document.createElement('div');
    div.className = 'bolha bolha-' + autor;
    div.setAttribute('data-mensagem', m.id);
    if (autor !== 'sistema') {
      var quem = document.createElement('span');
      quem.className = 'bolha-autor';
      quem.textContent = autor === 'cliente' ? (nomeCliente || 'Cliente')
        : autor === 'atendente' ? (nomeAtendente || AUTORES[autor]) : AUTORES[autor];
      div.appendChild(quem);
    }
    div.appendChild(document.createTextNode(m.texto || ''));
    if (Array.isArray(m.opcoes) && m.opcoes.length) {
      var ops = document.createElement('div');
      ops.className = 'bolha-opcoes';
      m.opcoes.forEach(function (o) {
        var chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = o;
        ops.appendChild(chip);
      });
      div.appendChild(ops);
    }
    if (autor !== 'sistema') {
      var hora = document.createElement('small');
      hora.textContent = P.hora(m.criado_em);
      div.appendChild(hora);
    }
    return div;
  }

  function painelInfo(a, conversa) {
    var status = (conversa && conversa.status) || a.status_app || a.status;
    return '<section class="cartao"><div class="cartao-cabecalho"><h2 class="cartao-titulo">Sobre o atendimento</h2><span data-alvo="status-info">' + P.selo(status) + '</span></div>' +
      '<dl class="dados dados-1">' +
      '<div><dt>Cliente</dt><dd><a href="' + esc(P.hashCliente(a.cliente_id)) + '">' + esc(P.ou(a.cliente_nome)) + '</a></dd></div>' +
      '<div><dt>Assunto</dt><dd>' + esc(P.ou(a.assunto)) + '</dd></div>' +
      '<div><dt>Canal</dt><dd>' + esc(P.rotulo(a.canal)) + '</dd></div>' +
      '<div><dt>Aberto em</dt><dd>' + esc(P.dataHora(a.criado_em)) + '</dd></div>' +
      '<div><dt>Atendente</dt><dd data-alvo="atendente">' + esc(P.ou((conversa && conversa.atendente_nome) || a.atendente_nome, 'Ninguém ainda')) + '</dd></div>' +
      (conversa && conversa.avaliacao ? '<div><dt>Avaliação do cliente</dt><dd>' + esc('★'.repeat(conversa.avaliacao)) + '</dd></div>' : '') +
      '</dl><div class="formulario-acoes">' +
      '<a class="botao botao-secundario" href="' + esc(P.hashCliente(a.cliente_id)) + '">Abrir ficha</a>' +
      (conversa && status !== 'resolvido' ? '<button type="button" class="botao botao-perigo" data-acao="encerrar">Encerrar conversa</button>' : '') +
      '</div></section>' +
      '<div class="aviso aviso-info">Fluxo: o assistente automático do app responde primeiro (prazo, fatura, Clube, indicação, endereço). ' +
      'Se não resolver, o cliente toca em <strong>“Falar com um atendente”</strong> e a conversa cai aqui.</div>';
  }

  P.tela('atendimento', {
    titulo: 'Atendimento',
    montar: async function (secao, id, ctx) {
      secao.innerHTML = P.htmlCarregando('Abrindo a conversa...');
      var ultimo = 0;
      var nomeCliente = '';
      var nomeAtendente = '';
      var timer = null;
      ctx.aoSair(function () { clearTimeout(timer); });

      var dados;
      try {
        dados = await P.api('/v1/painel/atendimentos/' + encodeURIComponent(id) + '/conversa');
      } catch (erro) {
        if (erro.status === 401) return;
        secao.innerHTML = P.cabecalhoTela('Atendimento') + P.htmlErro(erro) + '<p><a class="botao botao-secundario" href="#/atendimentos">← Voltar</a></p>';
        return;
      }
      if (!ctx.ativa()) return;
      var a = dados.atendimento || {};
      var conversa = dados.conversa;
      nomeCliente = a.cliente_nome || 'Cliente';
      document.title = 'Atendimento · ' + nomeCliente + ' · Painel Bulbe';

      var cabecalho = P.cabecalhoTela('Atendimento · ' + nomeCliente, P.ou(a.assunto, ''),
        '<a class="botao botao-secundario" href="#/atendimentos">← Voltar para a fila</a>');

      if (!conversa) {
        secao.innerHTML = cabecalho + '<div class="atendimento-grade"><section class="cartao">' +
          '<div class="aviso aviso-alerta">Atendimento do histórico fictício do painel: não tem conversa no app.</div>' +
          '<p class="espaco-cima">' + esc(P.ou(a.descricao, 'Sem descrição.')) + '</p></section><div>' + painelInfo(a, null) + '</div></div>';
        return;
      }

      secao.innerHTML = cabecalho + '<div class="atendimento-grade">' +
        '<section class="cartao conversa-cartao" aria-label="Conversa com o cliente">' +
          '<div class="conversa-topo"><div>' + P.pessoa(nomeCliente, 'Chat do app · atualiza a cada 2,5 s') + '</div><span data-alvo="status">' + P.selo(conversa.status) + '</span></div>' +
          '<div class="conversa-mensagens" data-alvo="mensagens" role="log" aria-live="polite"></div>' +
          '<form class="conversa-form" data-form="resposta"><label for="resposta" class="visualmente-oculto">Resposta</label>' +
          '<textarea id="resposta" name="texto" maxlength="1000" rows="2" placeholder="Escreva a resposta para o cliente (Enter envia)"></textarea>' +
          '<button type="submit" class="botao botao-primario">Enviar</button></form>' +
        '</section><div data-alvo="info">' + painelInfo(a, conversa) + '</div></div>';

      var caixa = secao.querySelector('[data-alvo="mensagens"]');
      var form = secao.querySelector('[data-form="resposta"]');
      var entrada = form.querySelector('textarea');

      function adicionar(lista) {
        var perto = caixa.scrollHeight - caixa.scrollTop - caixa.clientHeight < 120;
        (lista || []).forEach(function (m) {
          if (m.id <= ultimo) return;
          caixa.appendChild(bolha(m, nomeCliente, nomeAtendente));
          ultimo = m.id;
        });
        if (perto || !caixa.dataset.rolou) { caixa.scrollTop = caixa.scrollHeight; caixa.dataset.rolou = '1'; }
      }
      function aplicarStatus(c) {
        secao.querySelector('[data-alvo="status"]').innerHTML = P.selo(c.status);
        var info = secao.querySelector('[data-alvo="status-info"]');
        if (info) info.innerHTML = P.selo(c.status);
        var fechado = c.status === 'resolvido';
        entrada.disabled = fechado;
        form.querySelector('button').disabled = fechado;
        entrada.placeholder = fechado ? 'Conversa encerrada.' : 'Escreva a resposta para o cliente (Enter envia)';
        var botaoEncerrar = secao.querySelector('[data-acao="encerrar"]');
        if (botaoEncerrar && fechado) botaoEncerrar.remove();
        if (c.atendente_nome) {
          nomeAtendente = c.atendente_nome;
          secao.querySelector('[data-alvo="atendente"]').textContent = c.atendente_nome;
        }
      }
      async function buscarNovas() {
        try {
          var r = await P.api('/v1/painel/atendimentos/' + encodeURIComponent(id) + '/conversa?depois_de=' + ultimo);
          if (!ctx.ativa()) return;
          if (r.conversa) { aplicarStatus(r.conversa); adicionar(r.conversa.mensagens); }
        } catch (e) { /* tenta de novo no próximo ciclo */ }
        if (ctx.ativa()) timer = setTimeout(buscarNovas, INTERVALO_CONVERSA);
      }

      nomeAtendente = conversa.atendente_nome || '';
      adicionar(conversa.mensagens);
      aplicarStatus(conversa);
      if (!entrada.disabled) entrada.focus();
      timer = setTimeout(buscarNovas, INTERVALO_CONVERSA);

      async function enviar() {
        var texto = entrada.value.trim();
        if (!texto) return;
        try {
          var r = await P.comBotao(form.querySelector('button'), function () {
            return P.api('/v1/painel/atendimentos/' + encodeURIComponent(id) + '/respostas', { metodo: 'POST', corpo: { texto: texto } });
          });
          entrada.value = '';
          if (r && Array.isArray(r.mensagens)) { aplicarStatus(r); adicionar(r.mensagens); }
          caixa.scrollTop = caixa.scrollHeight;
        } catch (erro) { P.toastErro(erro); }
        entrada.focus();
      }
      form.addEventListener('submit', function (e) { e.preventDefault(); enviar(); });
      entrada.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviar(); }
      });
      secao.addEventListener('click', async function (e) {
        var botao = e.target.closest('[data-acao="encerrar"]');
        if (!botao) return;
        if (!(await P.confirmar('Encerrar conversa', 'O cliente verá “Conversa encerrada” no app e poderá avaliar o atendimento.', 'Encerrar', true))) return;
        try {
          var r = await P.comBotao(botao, function () {
            return P.api('/v1/painel/atendimentos/' + encodeURIComponent(id) + '/encerramento', { metodo: 'POST' });
          });
          if (r && Array.isArray(r.mensagens)) adicionar(r.mensagens);
          aplicarStatus(r || { status: 'resolvido' });
          P.toast('Conversa encerrada.', 'ok');
          if (P.atualizarContadorAtendimentos) P.atualizarContadorAtendimentos();
        } catch (erro) { P.toastErro(erro); }
      });
    }
  });
})();
