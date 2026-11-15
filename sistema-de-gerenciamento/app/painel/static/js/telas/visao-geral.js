/* ============================================================
   TELA: Visão geral — indicadores, gráficos e widgets
   Fontes: /metricas, /metricas/series, /clientes/parados, /atendimentos,
   /adesoes, /usinas e /integracao (todas em /v1/painel).
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var G = P.graficos;
  var esc = P.esc;

  function opcional(promessa) { return promessa.catch(function () { return null; }); }

  function estadoIntegracao(r) {
    if (!r) return '';
    if (!r.ativa) return P.seloTom('alerta', 'Integração com o app desligada');
    if (r.sucesso === false) return P.seloTom('erro', 'Falha na última sincronização');
    return P.seloTom('ok', 'App sincronizado ' + (r.ultima_execucao ? P.relativo(r.ultima_execucao) : ''));
  }

  function listaAtendimentos(pagina) {
    var lista = pagina ? P.normalizarPagina(pagina).data : [];
    if (!lista.length) return P.htmlVazio('Nenhum atendimento aberto. 🎉');
    return '<ul class="lista-compacta">' + lista.map(function (a) {
      return '<li>' + P.pessoa(a.cliente_nome, P.ou(a.assunto) + ' · ' + P.relativo(a.atualizado_em || a.criado_em), '#/atendimento/' + encodeURIComponent(a.id)) +
        P.selo(a.status_app || a.status) + '</li>';
    }).join('') + '</ul>';
  }

  function listaParados(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return P.htmlVazio('Ninguém parado há mais de 30 dias.');
    return '<ul class="lista-compacta">' + lista.map(function (c) {
      return '<li>' + P.pessoa(c.nome, 'Etapa ' + c.etapa_atual + ' · ' + P.ou(c.nome_etapa, ''), P.hashCliente(c.cliente_id)) +
        '<span class="dias-parado' + (c.atrasado ? ' atrasado' : '') + '">' + esc(P.numero(c.dias_na_etapa)) + ' dias</span></li>';
    }).join('') + '</ul>';
  }

  function listaAdesoes(pagina) {
    var lista = pagina ? P.normalizarPagina(pagina).data : [];
    if (!lista.length) return P.htmlVazio('Nenhuma adesão ainda.');
    return '<ul class="lista-compacta">' + lista.map(function (a) {
      return '<li>' + P.pessoa(a.nome, P.ou(a.cidade) + ' · ' + P.data(a.criado_em) + (a.id_app ? ' · app' : '')) +
        P.selo(a.situacao) + '</li>';
    }).join('') + '</ul>';
  }

  function usinas(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return P.htmlVazio('Nenhuma usina cadastrada.');
    return G.barras(lista.map(function (u, i) {
      return { rotulo: u.nome, sub: P.ou(u.localizacao, ''), valor: u.capacidade_geracao_kwh, cor: (i % 4) + 1 };
    }), { formato: function (v) { return P.numero(v) + ' kWh'; } });
  }

  function render(m, series, parados, atendimentos, adesoes, listaUsinas, integracao) {
    var cli = m.clientes || {}, fat = m.faturas || {}, ind = m.indicacoes || {}, clube = m.clube || {},
      ades = m.adesoes || {}, app = m.app || {}, porEtapa = m.ativacao_por_etapa || {};

    var kpis = '<div class="grade grade-kpi">' +
      P.kpi('Clientes', P.numero(cli.total), P.numero(cli.ativo) + ' ativos · ' + P.numero(cli.cancelado) + ' cancelados', 'azul') +
      P.kpi('Economia gerada', P.moeda(m.economia_total_gerada), 'desconto + bônus pagos aos clientes', 'verde') +
      P.kpi('Em ativação', P.numero(cli.em_ativacao), 'jornada de 5 etapas', 'amarelo') +
      P.kpi('Faturas vencidas', P.numero(fat.vencidas), P.moeda(fat.valor_vencido) + ' em atraso', Number(fat.vencidas) ? 'vermelho' : 'verde') +
      P.kpi('Indicações', P.numero(ind.total), P.numero(ind.aderiu) + ' aderiram · ' + P.numero(ind.pendente) + ' pendentes', 'ciano') +
      P.kpi('Adesões aguardando', P.numero(ades.enviada), P.numero(ades.aprovada) + ' aprovadas no total', 'amarelo') +
      '</div>';

    var meses = series && Array.isArray(series.meses) ? series.meses.map(P.mesCurto) : [];
    // O mês corrente ainda não tem faturas fechadas: some do gráfico de economia enquanto estiver zerado.
    var economia = series && Array.isArray(series.economia) ? series.economia.slice() : [];
    var mesesEconomia = meses.slice();
    if (economia.length > 1 && !Number(economia[economia.length - 1])) { economia.pop(); mesesEconomia.pop(); }
    var graficoEconomia = meses.length
      ? G.linhas(mesesEconomia, [{ nome: 'Economia', valores: economia, cor: 3 }], P.compacto)
      : P.htmlVazio('Sem faturas no período.');
    var graficoNovos = meses.length
      ? G.colunas(meses, [
        { nome: 'Clientes novos', valores: series.clientes_novos, cor: 1 },
        { nome: 'Adesões recebidas', valores: series.adesoes, cor: 4 }
      ])
      : P.htmlVazio('Sem dados no período.');

    var funil = G.barras(P.NOMES_ETAPAS.map(function (nome, i) {
      var n = i + 1;
      return {
        rotulo: n === 5 ? 'Ativados nos últimos 30 dias' : n + '. ' + nome,
        valor: porEtapa[String(n)] || 0, cor: n === 5 ? 3 : (n >= 3 ? 4 : 2), href: '#/ativacoes'
      };
    }));

    var rosca = G.rosca([
      { rotulo: 'Ativos', valor: cli.ativo || 0, cor: 3 },
      { rotulo: 'Em ativação', valor: cli.em_ativacao || 0, cor: 4 },
      { rotulo: 'Cancelados', valor: cli.cancelado || 0, cor: 5 }
    ], P.numero(cli.total), 'clientes');

    var clubeHtml = '<div class="mini-numeros">' +
      '<div><strong>' + esc(P.numero(clube.clientes_com_sequencia)) + '</strong><span>em sequência semanal</span></div>' +
      '<div><strong>' + esc(P.numero(clube.cupons_ativos)) + '</strong><span>cupons ativos</span></div>' +
      '<div><strong>' + esc(P.numero(clube.cupons_usados)) + '</strong><span>cupons usados</span></div>' +
      '<div><strong>' + esc(P.moeda(clube.bonus_pagos)) + '</strong><span>em bônus pagos</span></div>' +
      '</div><div class="mini-numeros">' +
      '<div><strong>' + esc(P.numero(app.clientes_com_acesso)) + '</strong><span>clientes com acesso ao app</span></div>' +
      '<div><strong>' + esc(P.numero(app.logins_ultimos_30_dias)) + '</strong><span>logins em 30 dias</span></div>' +
      '<div><strong>' + esc(P.numero(m.simulacoes_30_dias)) + '</strong><span>simulações em 30 dias</span></div>' +
      '</div>';

    return kpis +
      '<div class="faixa-integracao">' + estadoIntegracao(integracao) + '</div>' +
      '<div class="grade grade-12">' +
        '<div class="col-8">' + P.cartao('Economia gerada por mês', graficoEconomia, 'Desconto de 15% + bônus de indicação e do Clube, por mês de referência') + '</div>' +
        '<div class="col-4">' + P.cartao('Clientes por status', rosca) + '</div>' +
        '<div class="col-6">' + P.cartao('Funil de ativação', funil, 'Clientes em cada etapa da jornada (até 90 dias)', '<a class="botao botao-fantasma botao-pequeno" href="#/ativacoes">Ver ativações</a>') + '</div>' +
        '<div class="col-6">' + P.cartao('Crescimento', graficoNovos, 'Clientes novos e adesões recebidas por mês') + '</div>' +
        '<div class="col-4">' + P.cartao('Atendimentos abertos', listaAtendimentos(atendimentos), 'Clique para abrir a conversa', '<a class="botao botao-fantasma botao-pequeno" href="#/atendimentos">Todos</a>') + '</div>' +
        '<div class="col-4">' + P.cartao('Parados há mais tempo', listaParados(parados), 'Mesma etapa há 30 dias ou mais') + '</div>' +
        '<div class="col-4">' + P.cartao('Últimas adesões', listaAdesoes(adesoes), 'Pedidos de assinatura', '<a class="botao botao-fantasma botao-pequeno" href="#/adesoes">Analisar</a>') + '</div>' +
        '<div class="col-7">' + P.cartao('Clube Bulbe e app', clubeHtml) + '</div>' +
        '<div class="col-5">' + P.cartao('Usinas', usinas(listaUsinas), 'Capacidade de geração') + '</div>' +
      '</div>';
  }

  P.tela('visao-geral', {
    titulo: 'Visão geral',
    descricao: 'Como está a operação da Bulbe hoje: clientes, economia, ativações e atendimento.',
    montar: async function (secao, _param, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        '<button type="button" class="botao botao-secundario botao-pequeno" data-acao="atualizar">Atualizar</button>') +
        '<div data-alvo="conteudo">' + P.htmlCarregando('Carregando indicadores...') + '</div>';
      secao.querySelector('[data-acao="atualizar"]').addEventListener('click', ctx.recarregar);
      var alvo = secao.querySelector('[data-alvo="conteudo"]');
      try {
        var r = await Promise.all([
          P.api('/v1/painel/metricas'),
          opcional(P.api('/v1/painel/metricas/series?meses=7')),
          opcional(P.api('/v1/painel/clientes/parados?dias_minimos=30&limite=5')),
          opcional(P.api('/v1/painel/atendimentos?status=aberto&por_pagina=5')),
          opcional(P.api('/v1/painel/adesoes?por_pagina=5')),
          opcional(P.api('/v1/painel/usinas')),
          opcional(P.api('/v1/painel/integracao'))
        ]);
        if (!ctx.ativa()) return;
        alvo.innerHTML = render(r[0] || {}, r[1], r[2], r[3], r[4], r[5], r[6]);
        P.aplicarLarguras(alvo);
      } catch (erro) {
        if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro);
      }
    }
  });
})();
