/* ============================================================
   TELA: Ativações — jornada de 5 etapas até a energia ser liberada
   GET /v1/painel/ativacoes/resumo  ·  GET /v1/painel/clientes/parados?etapa&dias_minimos&limite
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;
  var PRAZO = 90;
  var filtros = { etapa: '', dias_minimos: '15', limite: '50' };

  function valor(obj, n) { return obj ? (obj[String(n)] !== undefined ? obj[String(n)] : obj[n]) : undefined; }

  function resumo(r) {
    r = r || {};
    var kpis = '<div class="grade grade-kpi">' +
      P.kpi('Em ativação', P.numero(r.em_ativacao), 'clientes na jornada agora', 'azul') +
      P.kpi('Atrasados', P.numero(r.atrasados_90_dias), 'passaram dos 90 dias do cadastro', Number(r.atrasados_90_dias) ? 'vermelho' : 'verde') +
      P.kpi('Ativados (30 dias)', P.numero(r.ativados_30_dias), 'energia liberada no último mês', 'verde') +
      P.kpi('Tempo médio', P.ehNumero(r.tempo_medio_ativacao_dias) ? P.decimal(r.tempo_medio_ativacao_dias) + ' dias' : '—', 'do cadastro à energia liberada', 'amarelo') +
      '</div>';
    var funil = '<div class="funil" role="group" aria-label="Filtrar pela etapa">' + [1, 2, 3, 4].map(function (n) {
      var dias = valor(r.dias_medios_na_etapa, n);
      return '<button type="button" class="funil-etapa" data-etapa="' + n + '" aria-pressed="' + (String(filtros.etapa) === String(n)) + '">' +
        '<span>Etapa ' + n + '</span><strong>' + esc(P.numero(valor(r.por_etapa, n) || 0)) + '</strong>' +
        '<span>' + esc(P.NOMES_ETAPAS[n - 1]) + '</span>' +
        '<span>' + (P.ehNumero(dias) ? esc(P.decimal(dias)) + ' dias em média' : '&nbsp;') + '</span></button>';
    }).join('') +
      '<div class="funil-etapa funil-final"><span>Etapa 5</span><strong>' + esc(P.numero(r.ativados_30_dias || 0)) + '</strong>' +
      '<span>Energia liberada</span><span>nos últimos 30 dias</span></div></div>';
    return kpis + P.cartao('Onde estão os clientes', funil, 'Clique em uma etapa para ver só os clientes dela na lista abaixo');
  }

  function parados(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return P.htmlVazio('Ninguém parado com esses filtros. 👏');
    return '<div class="tabela-rolagem"><table class="tabela"><caption class="visualmente-oculto">Clientes parados na mesma etapa</caption><thead><tr>' +
      '<th>Cliente</th><th>Etapa atual</th><th class="col-numero">Parado há</th><th>Prazo de 90 dias</th><th>Previsão</th><th></th></tr></thead><tbody>' +
      lista.map(function (c) {
        var usado = Math.min(100, (Number(c.dias_desde_cadastro) || 0) * 100 / PRAZO);
        return '<tr class="clicavel" data-href="' + esc(P.hashCliente(c.cliente_id)) + '">' +
          '<td>' + P.pessoa(c.nome, c.cidade, P.hashCliente(c.cliente_id)) + '</td>' +
          '<td><span class="selo selo-info">' + esc(c.etapa_atual) + ' · ' + esc(P.ou(c.nome_etapa, P.NOMES_ETAPAS[c.etapa_atual - 1])) + '</span></td>' +
          '<td class="col-numero"><span class="dias-parado' + (Number(c.dias_na_etapa) >= 30 ? ' atrasado' : '') + '">' + esc(P.numero(c.dias_na_etapa)) + ' dias</span></td>' +
          '<td class="col-prazo"><div class="barra-progresso"><span class="' + (c.atrasado ? 'leg-erro' : usado > 70 ? 'leg-4' : 'leg-3') + '" data-largura="' + usado.toFixed(0) + '"></span></div>' +
            '<small class="texto-suave">' + esc(P.numero(c.dias_desde_cadastro)) + ' de ' + PRAZO + ' dias · ' + (c.atrasado ? '<strong class="texto-erro">atrasado</strong>' : 'no prazo') + '</small></td>' +
          '<td class="col-nowrap">' + esc(P.data(c.previsao_conclusao)) + '</td>' +
          '<td><a class="botao botao-secundario botao-pequeno" href="' + esc(P.hashCliente(c.cliente_id)) + '">Abrir ficha</a></td></tr>';
      }).join('') + '</tbody></table></div>';
  }

  P.tela('ativacoes', {
    titulo: 'Ativações',
    descricao: 'Acompanhe a jornada de ativação (Cadastro → Documentos → Solicitação à CEMIG → Análise CEMIG → Energia liberada).',
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        '<button type="button" class="botao botao-secundario botao-pequeno" data-acao="atualizar">Atualizar</button>') +
        '<div data-alvo="resumo">' + P.htmlCarregando('Carregando resumo...') + '</div>' +
        '<section class="cartao"><div class="cartao-cabecalho"><div><h2 class="cartao-titulo">Clientes parados na mesma etapa</h2>' +
        '<p class="cartao-sub">Quem está há mais tempo sem avançar aparece primeiro. Para mover um cliente do app, abra a ficha e use “Atualizar no app”.</p></div></div>' +
        '<form class="filtros filtros-embutidos" data-form="filtros">' +
          '<div class="campo"><label for="p-etapa">Etapa</label><select id="p-etapa" name="etapa"><option value="">Todas</option>' +
          [1, 2, 3, 4].map(function (n) { return '<option value="' + n + '">' + n + '. ' + esc(P.NOMES_ETAPAS[n - 1]) + '</option>'; }).join('') + '</select></div>' +
          '<div class="campo"><label for="p-dias">Parado há pelo menos</label><select id="p-dias" name="dias_minimos">' +
          [['0', 'Qualquer tempo'], ['7', '7 dias'], ['15', '15 dias'], ['30', '30 dias'], ['60', '60 dias']].map(function (o) {
            return '<option value="' + o[0] + '">' + o[1] + '</option>';
          }).join('') + '</select></div>' +
        '</form><div data-alvo="parados"></div></section>';
      var form = secao.querySelector('[data-form="filtros"]');
      var alvoResumo = secao.querySelector('[data-alvo="resumo"]');
      var alvoParados = secao.querySelector('[data-alvo="parados"]');
      form.etapa.value = filtros.etapa;
      form.dias_minimos.value = filtros.dias_minimos;
      var ultimoResumo = null;

      async function carregarResumo() {
        try {
          ultimoResumo = await P.api('/v1/painel/ativacoes/resumo');
          if (!ctx.ativa()) return;
          alvoResumo.innerHTML = resumo(ultimoResumo);
        } catch (erro) { if (erro.status !== 401) alvoResumo.innerHTML = P.htmlErro(erro); }
      }
      async function carregarParados() {
        alvoParados.innerHTML = P.htmlCarregando('Buscando clientes...');
        try {
          var lista = await P.api('/v1/painel/clientes/parados' + P.montarQuery(filtros));
          if (!ctx.ativa()) return;
          alvoParados.innerHTML = parados(lista);
          P.aplicarLarguras(alvoParados);
        } catch (erro) { if (erro.status !== 401) alvoParados.innerHTML = P.htmlErro(erro); }
      }

      form.addEventListener('change', function () {
        filtros.etapa = form.etapa.value;
        filtros.dias_minimos = form.dias_minimos.value;
        if (ultimoResumo) alvoResumo.innerHTML = resumo(ultimoResumo);
        carregarParados();
      });
      form.addEventListener('submit', function (e) { e.preventDefault(); });
      alvoResumo.addEventListener('click', function (e) {
        var etapa = e.target.closest('[data-etapa]');
        if (!etapa) return;
        var n = etapa.getAttribute('data-etapa');
        filtros.etapa = String(filtros.etapa) === n ? '' : n;
        form.etapa.value = filtros.etapa;
        alvoResumo.innerHTML = resumo(ultimoResumo);
        carregarParados();
      });
      alvoParados.addEventListener('click', function (e) {
        if (e.target.closest('a, button')) return;
        var tr = e.target.closest('tr[data-href]');
        if (tr) window.location.hash = tr.getAttribute('data-href');
      });
      secao.querySelector('[data-acao="atualizar"]').addEventListener('click', function () { carregarResumo(); carregarParados(); });
      carregarResumo();
      carregarParados();
    }
  });
})();
