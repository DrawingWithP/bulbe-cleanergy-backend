/* ============================================================
   TELAS: Usinas, Auditoria e integração (admin) e Uso do assistente (admin)
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var G = P.graficos;
  var esc = P.esc;

  /* ======================= USINAS ======================= */
  P.tela('usinas', {
    titulo: 'Usinas',
    descricao: 'Usinas solares que geram a energia compartilhada com os clientes.',
    montar: async function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao) + '<div data-alvo="c">' + P.htmlCarregando('Carregando usinas...') + '</div>';
      var alvo = secao.querySelector('[data-alvo="c"]');
      try {
        var lista = await P.api('/v1/painel/usinas');
        if (!ctx.ativa()) return;
        lista = Array.isArray(lista) ? lista : [];
        var capacidade = lista.reduce(function (s, u) { return s + (Number(u.capacidade_geracao_kwh) || 0); }, 0);
        var clientes = lista.reduce(function (s, u) { return s + (Number(u.clientes_ativos) || 0); }, 0);
        alvo.innerHTML = '<div class="grade grade-kpi">' +
          P.kpi('Usinas', P.numero(lista.length), P.numero(lista.filter(function (u) { return u.status === 'ativa'; }).length) + ' ativas', 'azul') +
          P.kpi('Capacidade total', P.numero(capacidade) + ' kWh', 'geração por mês', 'amarelo') +
          P.kpi('Clientes atendidos', P.numero(clientes), 'clientes ativos ligados às usinas', 'verde') + '</div>' +
          '<div class="grade grade-12"><div class="col-5">' + P.cartao('Clientes por usina', G.barras(lista.map(function (u, i) {
            return { rotulo: u.nome, valor: u.clientes_ativos || 0, cor: (i % 4) + 1 };
          }))) + '</div><div class="col-7">' +
          P.cartao('Todas as usinas', lista.length ? '<div class="tabela-rolagem"><table class="tabela"><thead><tr><th>Usina</th><th>Localização</th>' +
            '<th class="col-numero">Capacidade</th><th class="col-numero">Clientes</th><th>Status</th><th>Ativa desde</th></tr></thead><tbody>' +
            lista.map(function (u) {
              return '<tr><td><strong>' + esc(u.nome) + '</strong></td><td>' + esc(P.ou(u.localizacao)) + '</td>' +
                '<td class="col-numero">' + esc(P.numero(u.capacidade_geracao_kwh)) + ' kWh</td><td class="col-numero">' + esc(P.numero(u.clientes_ativos)) + '</td>' +
                '<td>' + P.selo(u.status) + '</td><td class="col-nowrap">' + esc(P.data(u.data_ativacao)) + '</td></tr>';
            }).join('') + '</tbody></table></div>' : P.htmlVazio('Nenhuma usina cadastrada.')) + '</div></div>';
        P.aplicarLarguras(alvo);
      } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
    }
  });

  /* ======================= AUDITORIA E INTEGRAÇÃO ======================= */
  var ACOES = {
    login_ok: ['ok', 'Login com sucesso'], login_falha: ['alerta', 'Login com falha'], login_bloqueado: ['erro', 'Login bloqueado'],
    alerta_email: ['erro', 'Alerta por e-mail'], ver_ficha: ['info', 'Abriu ficha'], ver_auditoria: ['neutro', 'Consultou auditoria'],
    expurgo: ['neutro', 'Expurgo'], sincronizar_app: ['neutro', 'Sincronizou com o app'], alterar_ativacao: ['info', 'Alterou etapa no app']
  };
  var filtrosAuditoria = { acao: '', funcionario_id: '', por_pagina: '50', pagina: 1 };

  function integracao(r) {
    r = r || {};
    if (!r.ativa) return '<div class="aviso aviso-alerta">Integração com o app desligada' + (r.motivo ? ': ' + esc(r.motivo) : '.') + '</div>';
    var html = '<p>' + (r.sucesso === false ? P.seloTom('erro', 'Falha') + ' ' + esc(P.ou(r.erro, '')) : P.seloTom('ok', 'Funcionando')) +
      ' <span class="texto-suave">Última sincronização: ' + esc(r.ultima_execucao ? P.dataHora(r.ultima_execucao) : 'nunca') +
      (r.intervalo_segundos ? ' · a cada ' + esc(r.intervalo_segundos) + ' s' : '') + '</span></p>';
    var contagens = r.contagens || {};
    var nomes = Object.keys(contagens);
    if (nomes.length) {
      html += '<div class="tabela-rolagem espaco-cima"><table class="tabela"><thead><tr><th>Dado</th><th class="col-numero">Criados</th><th class="col-numero">Atualizados</th>' +
        '<th class="col-numero">Vinculados</th><th class="col-numero">Removidos</th></tr></thead><tbody>' + nomes.map(function (n) {
          var c = contagens[n] || {};
          return '<tr><th scope="row">' + esc(P.rotulo(n)) + '</th><td class="col-numero">' + esc(P.numero(c.criados)) + '</td><td class="col-numero">' + esc(P.numero(c.atualizados)) +
            '</td><td class="col-numero">' + esc(P.numero(c.vinculados)) + '</td><td class="col-numero">' + esc(P.numero(c.removidos)) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    }
    return html;
  }

  P.tela('auditoria', {
    titulo: 'Auditoria e integração',
    descricao: 'Quem fez o quê no painel, e o estado da sincronização com o app.',
    admin: true,
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao) +
        '<div class="grade grade-12"><div class="col-8"><section class="cartao"><div class="cartao-cabecalho"><h2 class="cartao-titulo">Integração com o app</h2>' +
        '<button type="button" class="botao botao-secundario botao-pequeno" data-acao="sincronizar">Sincronizar agora</button></div><div data-alvo="integracao">' +
        P.htmlCarregando() + '</div></section></div>' +
        '<div class="col-4"><section class="cartao"><h2 class="cartao-titulo">Retenção de dados (LGPD)</h2>' +
        '<p class="texto-suave espaco-cima">Apaga conversas do assistente e registros de auditoria mais antigos que o prazo configurado no servidor.</p>' +
        '<div class="formulario-acoes"><button type="button" class="botao botao-perigo" data-acao="expurgo">Expurgar dados antigos</button></div></section></div></div>' +
        '<form class="filtros" data-form="filtros"><div class="campo"><label for="au-acao">Ação</label><select id="au-acao" name="acao"><option value="">Todas</option>' +
        Object.keys(ACOES).map(function (k) { return '<option value="' + k + '">' + esc(ACOES[k][1]) + '</option>'; }).join('') + '</select></div>' +
        '<div class="campo"><label for="au-func">ID do funcionário</label><input id="au-func" name="funcionario_id" type="number" min="1"></div>' +
        '<div class="tela-acoes"><button type="submit" class="botao botao-primario">Filtrar</button></div></form>' +
        '<div data-alvo="lista"></div>';
      var alvoInt = secao.querySelector('[data-alvo="integracao"]');
      var alvo = secao.querySelector('[data-alvo="lista"]');
      var form = secao.querySelector('form');
      form.acao.value = filtrosAuditoria.acao;
      form.funcionario_id.value = filtrosAuditoria.funcionario_id;

      async function carregarIntegracao() {
        try { alvoInt.innerHTML = integracao(await P.api('/v1/painel/integracao')); } catch (e) { alvoInt.innerHTML = P.htmlErro(e); }
      }
      async function carregar() {
        alvo.innerHTML = P.htmlCarregando('Carregando auditoria...');
        try {
          var p = P.normalizarPagina(await P.api('/v1/painel/auditoria' + P.montarQuery(filtrosAuditoria)));
          if (!ctx.ativa()) return;
          alvo.innerHTML = (p.data.length ? '<div class="tabela-rolagem"><table class="tabela"><thead><tr><th>Quando</th><th>Ação</th><th>Funcionário</th>' +
            '<th>Recurso</th><th>IP</th><th>Detalhe</th></tr></thead><tbody>' + p.data.map(function (a) {
              var acao = ACOES[a.acao] || ['neutro', P.rotulo(a.acao)];
              var recurso = a.recurso_tipo === 'cliente' && a.recurso_id
                ? '<a href="' + esc(P.hashCliente(a.recurso_id)) + '">Cliente ' + esc(a.recurso_id) + '</a>'
                : esc([a.recurso_tipo, a.recurso_id].filter(Boolean).join(' ') || '—');
              return '<tr><td class="col-nowrap">' + esc(P.dataHora(a.criado_em)) + '</td><td>' + P.seloTom(acao[0], acao[1]) + '</td>' +
                '<td>' + esc(a.funcionario_nome || (a.funcionario_id ? '#' + a.funcionario_id : P.ou(a.email_informado))) + '</td>' +
                '<td>' + recurso + '</td><td class="col-nowrap">' + esc(P.ou(a.ip)) + '</td><td>' + esc(P.ou(a.detalhe)) + '</td></tr>';
            }).join('') + '</tbody></table></div>' : P.htmlVazio('Nenhum registro com esses filtros.')) + P.htmlPaginacao(p, 'registros');
        } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        filtrosAuditoria.acao = form.acao.value;
        filtrosAuditoria.funcionario_id = form.funcionario_id.value;
        filtrosAuditoria.pagina = 1;
        carregar();
      });
      form.acao.addEventListener('change', function () { form.requestSubmit(); });
      alvo.addEventListener('click', function (e) {
        var pag = e.target.closest('[data-pagina]');
        if (pag) { filtrosAuditoria.pagina = Number(pag.getAttribute('data-pagina')) || 1; carregar(); }
      });
      secao.querySelector('[data-acao="sincronizar"]').addEventListener('click', async function (e) {
        try {
          var r = await P.comBotao(e.currentTarget, function () { return P.api('/v1/painel/admin/sincronizar', { metodo: 'POST', tempoLimite: 60000 }); });
          alvoInt.innerHTML = integracao(r);
          P.toast('Sincronização concluída.', 'ok');
          carregar();
        } catch (erro) { P.toastErro(erro); }
      });
      secao.querySelector('[data-acao="expurgo"]').addEventListener('click', async function (e) {
        var botao = e.currentTarget;
        if (!(await P.confirmar('Expurgar dados antigos', 'Apagar agora as conversas do assistente e a auditoria mais antigas que o prazo de retenção? Não dá para desfazer.', 'Expurgar', true))) return;
        try {
          var r = await P.comBotao(botao, function () { return P.api('/v1/painel/admin/expurgo', { metodo: 'POST' }); }) || {};
          P.toast('Expurgo concluído: ' + P.numero((r.chat_conversas || 0) + (r.chat_mensagens || 0) + (r.chat_historico || 0)) +
            ' registros do chat e ' + P.numero(r.auditoria || 0) + ' de auditoria removidos.', 'ok');
          carregar();
        } catch (erro) { P.toastErro(erro); }
      });
      carregarIntegracao();
      carregar();
    }
  });

  /* ======================= USO DO ASSISTENTE ======================= */
  P.tela('uso-assistente', {
    titulo: 'Uso do assistente',
    descricao: 'Perguntas, tokens e custo estimado (US$) do assistente interno no período.',
    admin: true,
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        '<div class="campo"><label for="uso-dias">Período</label><select id="uso-dias"><option value="7">Últimos 7 dias</option>' +
        '<option value="30" selected>Últimos 30 dias</option><option value="90">Últimos 90 dias</option><option value="365">Últimos 365 dias</option></select></div>') +
        '<div data-alvo="c"></div>';
      var alvo = secao.querySelector('[data-alvo="c"]');
      var seletor = secao.querySelector('#uso-dias');

      async function carregar() {
        alvo.innerHTML = P.htmlCarregando('Carregando uso do assistente...');
        try {
          var u = await P.api('/v1/painel/uso-chatbot?dias=' + encodeURIComponent(seletor.value)) || {};
          if (!ctx.ativa()) return;
          var porDia = Array.isArray(u.por_dia) ? u.por_dia.slice(-14) : [];
          var funcionarios = Array.isArray(u.por_funcionario) ? u.por_funcionario : [];
          var ferramentas = Array.isArray(u.ferramentas_mais_usadas) ? u.ferramentas_mais_usadas : [];
          alvo.innerHTML = '<div class="grade grade-kpi">' +
            P.kpi('Perguntas', P.numero(u.perguntas), P.numero(u.conversas) + ' conversas · ' + P.numero(u.funcionarios_ativos) + ' funcionário(s)', 'azul') +
            P.kpi('Custo estimado', P.dolar(u.custo_estimado_usd), 'no período', 'amarelo') +
            P.kpi('Custo por pergunta', P.dolar(u.custo_medio_por_pergunta_usd), 'média', 'amarelo') +
            P.kpi('Tempo de resposta', P.ehNumero(u.duracao_media_ms) ? P.decimal(u.duracao_media_ms / 1000) + ' s' : '—', 'média', 'ciano') +
            P.kpi('Tokens', P.compacto((Number(u.input_tokens) || 0) + (Number(u.output_tokens) || 0)), P.compacto(u.cache_read_tokens) + ' lidos do cache', 'verde') + '</div>' +
            '<div class="grade grade-12"><div class="col-7">' + P.cartao('Perguntas por dia', porDia.some(function (d) { return Number(d.perguntas) > 0; })
              ? G.colunas(porDia.map(function (d) { return P.data(d.data).slice(0, 5); }), [{ nome: 'Perguntas', valores: porDia.map(function (d) { return d.perguntas; }), cor: 2 }])
              : P.htmlVazio('Nenhuma pergunta no período.'), 'Últimos 14 dias com uso') + '</div>' +
            '<div class="col-5">' + P.cartao('Ferramentas mais usadas', ferramentas.length
              ? G.barras(ferramentas.map(function (f, i) { return { rotulo: f.nome, valor: f.usos, cor: (i % 4) + 1 }; }))
              : P.htmlVazio('Nenhuma consulta no período.'), 'Consultas ao banco feitas pelo assistente') + '</div>' +
            '<div class="col-12">' + P.cartao('Por funcionário', funcionarios.length ? '<div class="tabela-rolagem"><table class="tabela"><thead><tr><th>Funcionário</th>' +
              '<th class="col-numero">Perguntas</th><th class="col-numero">Custo estimado</th></tr></thead><tbody>' + funcionarios.map(function (f) {
                return '<tr><td>' + esc(P.ou(f.nome)) + '</td><td class="col-numero">' + esc(P.numero(f.perguntas)) + '</td><td class="col-numero">' + esc(P.dolar(f.custo_estimado_usd)) + '</td></tr>';
              }).join('') + '</tbody></table></div>' : P.htmlVazio('Nenhuma pergunta no período.')) + '</div></div>' +
            '<p class="texto-suave">O custo é estimado pelo servidor a partir dos tokens e dos preços configurados; a fatura oficial é a do console da Anthropic.</p>';
          P.aplicarLarguras(alvo);
        } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }
      seletor.addEventListener('change', carregar);
      carregar();
    }
  });
})();
