/* ============================================================
   TELA: Adesões — pedidos de assinatura (simulador do app, site, WhatsApp)
   Aprovar cria o cliente no app (jornada começa na etapa 1); recusar encerra o pedido.
   POST /v1/painel/adesoes/{id}/aprovacao  ·  POST /v1/painel/adesoes/{id}/recusa
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;
  var filtros = { situacao: 'enviada', apenas_app: 'true', por_pagina: '20', pagina: 1 };

  function acoes(a) {
    var pendente = a.situacao === 'enviada' || a.situacao === 'rascunho';
    if (a.cliente_id) return '<a class="botao botao-secundario botao-pequeno" href="' + esc(P.hashCliente(a.cliente_id)) + '">Ver cliente</a>';
    if (!pendente) return '<span class="texto-suave">—</span>';
    if (!a.id_app) return '<span class="texto-suave" title="Pedido do histórico fictício do painel">Só histórico</span>';
    return '<div class="dica-acoes"><button type="button" class="botao botao-sucesso botao-pequeno" data-aprovar="' + esc(a.id) + '">Aprovar</button>' +
      '<button type="button" class="botao botao-perigo botao-pequeno" data-recusar="' + esc(a.id) + '">Recusar</button></div>';
  }

  function tabela(lista) {
    if (!lista.length) return P.htmlVazio('Nenhuma adesão encontrada.');
    return '<div class="tabela-rolagem"><table class="tabela"><caption class="visualmente-oculto">Adesões</caption><thead><tr>' +
      '<th>Interessado</th><th>Cidade</th><th class="col-numero">Conta atual</th><th class="col-numero">Economia/mês</th>' +
      '<th>Origem</th><th>Recebida em</th><th>Situação</th><th>Ação</th></tr></thead><tbody>' +
      lista.map(function (a) {
        return '<tr><td>' + P.pessoa(a.nome, P.ou(a.email, '') + (a.telefone ? ' · ' + P.telefone(a.telefone) : '')) + '</td>' +
          '<td>' + esc(P.ou(a.cidade)) + (a.uf ? '/' + esc(a.uf) : '') + '</td>' +
          '<td class="col-numero">' + esc(P.moeda(a.valor_conta_atual)) + '</td>' +
          '<td class="col-numero texto-ok">' + esc(P.moeda(a.economia_mensal_estimada)) + '</td>' +
          '<td>' + esc(P.rotulo(a.origem)) + (a.id_app ? ' <span class="selo selo-app">App</span>' : '') + '</td>' +
          '<td class="col-nowrap">' + esc(P.data(a.criado_em)) + '</td>' +
          '<td>' + P.selo(a.situacao) + '</td><td>' + acoes(a) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }

  P.tela('adesoes', {
    titulo: 'Adesões',
    descricao: 'Pedidos de assinatura que chegam pelo simulador do app, pelo site ou pelo WhatsApp.',
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao) +
        '<div class="aviso aviso-info"><strong>Como funciona:</strong> a pessoa simula a economia e pede a adesão. ' +
        'A equipe confere os dados (endereço na área atendida, conta da CEMIG) e <strong>aprova</strong> — o cliente é criado no app, ' +
        'recebe o primeiro acesso pelo CPF e começa a jornada de ativação na etapa 1 — ou <strong>recusa</strong> o pedido.</div>' +
        '<form class="filtros" data-form="filtros"><div class="campo"><label for="a-sit">Situação</label><select id="a-sit" name="situacao">' +
        '<option value="">Todas</option><option value="enviada">Aguardando análise</option><option value="rascunho">Rascunho</option>' +
        '<option value="aprovada">Aprovadas</option><option value="recusada">Recusadas</option></select></div>' +
        '<div class="campo"><label for="a-origem">Origem</label><select id="a-origem" name="apenas_app">' +
        '<option value="true">Feitas no app (dá para aprovar)</option><option value="">Todas, inclusive histórico</option></select></div></form>' +
        '<div data-alvo="lista"></div>';
      var form = secao.querySelector('form');
      var alvo = secao.querySelector('[data-alvo="lista"]');
      form.situacao.value = filtros.situacao;
      form.apenas_app.value = filtros.apenas_app;

      async function carregar() {
        alvo.innerHTML = P.htmlCarregando('Carregando adesões...');
        try {
          var p = P.normalizarPagina(await P.api('/v1/painel/adesoes' + P.montarQuery(filtros)));
          if (!ctx.ativa()) return;
          alvo.innerHTML = tabela(p.data) + P.htmlPaginacao(p, p.total === 1 ? 'adesão' : 'adesões');
        } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }

      form.addEventListener('change', function () {
        filtros.situacao = form.situacao.value;
        filtros.apenas_app = form.apenas_app.value;
        filtros.pagina = 1;
        carregar();
      });
      form.addEventListener('submit', function (e) { e.preventDefault(); });
      alvo.addEventListener('click', async function (e) {
        var pag = e.target.closest('[data-pagina]');
        if (pag) { filtros.pagina = Number(pag.getAttribute('data-pagina')) || 1; carregar(); return; }
        var aprovar = e.target.closest('[data-aprovar]');
        var recusar = e.target.closest('[data-recusar]');
        var botao = aprovar || recusar;
        if (!botao) return;
        var id = botao.getAttribute(aprovar ? 'data-aprovar' : 'data-recusar');
        var ok = await P.confirmar(aprovar ? 'Aprovar adesão' : 'Recusar adesão',
          aprovar ? 'O cliente será criado no app e começará a jornada de ativação na etapa 1.' : 'O pedido será marcado como recusado.',
          aprovar ? 'Aprovar e criar cliente' : 'Recusar', !aprovar);
        if (!ok) return;
        try {
          var r = await P.comBotao(botao, function () {
            return P.api('/v1/painel/adesoes/' + encodeURIComponent(id) + (aprovar ? '/aprovacao' : '/recusa'), { metodo: 'POST' });
          });
          P.toast(aprovar ? 'Adesão aprovada: cliente criado no app.' : 'Adesão recusada.', 'ok');
          if (aprovar && r && r.cliente_id) P.toast('O cliente já pode fazer o primeiro acesso pelo CPF.', 'ok');
          carregar();
        } catch (erro) { P.toastErro(erro); }
      });
      carregar();
    }
  });
})();
