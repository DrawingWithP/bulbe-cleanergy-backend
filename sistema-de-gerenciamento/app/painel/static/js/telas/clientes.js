/* ============================================================
   TELAS: Clientes (busca com filtros e ordenação) e Ficha do cliente
   GET /v1/painel/clientes?termo&status&etapa&cidade&origem&acesso_app&cadastro_de&cadastro_ate&ordenar_por&ordem
   GET /v1/painel/clientes/{id}  ·  PATCH /v1/painel/clientes/{id}/ativacao (só clientes do app)
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var G = P.graficos;
  var esc = P.esc;

  var PADRAO = { termo: '', status: '', etapa: '', cidade: '', origem: '', acesso_app: '', cadastro_de: '', cadastro_ate: '',
    ordenar_por: 'nome', ordem: 'asc', por_pagina: '20', pagina: 1 };
  var filtros = Object.assign({}, PADRAO);

  function opcoes(lista, atual) {
    return lista.map(function (o) {
      return '<option value="' + esc(o[0]) + '"' + (String(atual) === String(o[0]) ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
    }).join('');
  }

  function formularioFiltros() {
    var f = filtros;
    return '<form class="filtros" data-form="filtros" role="search">' +
      '<div class="campo campo-largo"><label for="f-termo">Buscar</label>' +
        '<input id="f-termo" name="termo" type="search" maxlength="100" placeholder="Nome, e-mail, CPF, instalação ou código" value="' + esc(f.termo) + '" autocomplete="off"></div>' +
      '<div class="campo"><label for="f-status">Status</label><select id="f-status" name="status">' +
        opcoes([['', 'Todos'], ['ativo', 'Ativo'], ['em_ativacao', 'Em ativação'], ['cancelado', 'Cancelado']], f.status) + '</select></div>' +
      '<div class="campo"><label for="f-etapa">Etapa</label><select id="f-etapa" name="etapa">' +
        opcoes([['', 'Todas']].concat(P.NOMES_ETAPAS.map(function (n, i) { return [i + 1, (i + 1) + '. ' + n]; })), f.etapa) + '</select></div>' +
      '<div class="campo"><label for="f-cidade">Cidade</label><input id="f-cidade" name="cidade" maxlength="80" value="' + esc(f.cidade) + '"></div>' +
      '<div class="campo"><label for="f-origem">Origem</label><select id="f-origem" name="origem">' +
        opcoes([['', 'Todas'], ['app', 'Clientes do app'], ['ficticio', 'Base fictícia']], f.origem) + '</select></div>' +
      '<div class="campo"><label for="f-acesso">Acesso ao app</label><select id="f-acesso" name="acesso_app">' +
        opcoes([['', 'Todos'], ['true', 'Com acesso'], ['false', 'Sem acesso']], f.acesso_app) + '</select></div>' +
      '<div class="campo"><label for="f-de">Cadastro de</label><input id="f-de" name="cadastro_de" type="date" value="' + esc(f.cadastro_de) + '"></div>' +
      '<div class="campo"><label for="f-ate">até</label><input id="f-ate" name="cadastro_ate" type="date" value="' + esc(f.cadastro_ate) + '"></div>' +
      '<div class="campo"><label for="f-ordenar">Ordenar por</label><select id="f-ordenar" name="ordenar_por">' +
        opcoes([['nome', 'Nome'], ['criado_em', 'Data de cadastro'], ['status', 'Status'], ['etapa', 'Etapa'], ['cidade', 'Cidade']], f.ordenar_por) + '</select></div>' +
      '<div class="campo"><label for="f-ordem">Ordem</label><select id="f-ordem" name="ordem">' +
        opcoes([['asc', 'Crescente (A→Z, antigos)'], ['desc', 'Decrescente (Z→A, recentes)']], f.ordem) + '</select></div>' +
      '<div class="campo"><label for="f-por">Por página</label><select id="f-por" name="por_pagina">' +
        opcoes([['20', '20'], ['50', '50'], ['100', '100']], f.por_pagina) + '</select></div>' +
      '<div class="tela-acoes"><button type="submit" class="botao botao-primario">Filtrar</button>' +
        '<button type="button" class="botao botao-fantasma" data-acao="limpar">Limpar</button></div>' +
      '</form>';
  }

  var COLUNAS = [['nome', 'Cliente'], ['cidade', 'Cidade'], ['status', 'Status'], ['etapa', 'Etapa'], ['criado_em', 'Cliente desde']];

  function cabecalhoOrdenavel(campo, texto) {
    var ativa = filtros.ordenar_por === campo;
    var seta = ativa ? (filtros.ordem === 'asc' ? ' ↑' : ' ↓') : '';
    return '<th scope="col"' + (ativa ? ' aria-sort="' + (filtros.ordem === 'asc' ? 'ascending' : 'descending') + '"' : '') + '>' +
      '<button type="button" class="th-ordenavel" data-ordenar="' + campo + '" data-ativa="' + ativa + '">' + esc(texto) + seta + '</button></th>';
  }

  function tabela(lista) {
    if (!lista.length) return P.htmlVazio('Nenhum cliente encontrado com esses filtros.');
    return '<div class="tabela-rolagem"><table class="tabela"><caption class="visualmente-oculto">Clientes</caption><thead><tr>' +
      cabecalhoOrdenavel('nome', 'Cliente') + '<th scope="col">CPF</th>' + COLUNAS.slice(1).map(function (c) { return cabecalhoOrdenavel(c[0], c[1]); }).join('') +
      '<th scope="col">App</th></tr></thead><tbody>' +
      lista.map(function (c) {
        var href = P.hashCliente(c.id);
        return '<tr class="clicavel" data-href="' + esc(href) + '">' +
          '<td>' + P.pessoa(c.nome, c.email, href) + '</td>' +
          '<td class="col-nowrap">' + esc(P.cpf(c.cpf)) + '</td>' +
          '<td>' + esc(P.ou(c.cidade)) + (c.uf ? '/' + esc(c.uf) : '') + '</td>' +
          '<td>' + P.selo(c.status) + '</td>' +
          '<td class="col-nowrap">' + (P.ehNumero(c.etapa_ativacao) ? esc(c.etapa_ativacao) + '/5' : '—') + '</td>' +
          '<td class="col-nowrap">' + esc(P.data(c.criado_em)) + '</td>' +
          '<td>' + (c.origem === 'app' ? '<span class="selo selo-app">App</span>' : '<span class="texto-suave">Fictício</span>') + '</td>' +
          '</tr>';
      }).join('') + '</tbody></table></div>';
  }

  P.tela('clientes', {
    titulo: 'Clientes',
    descricao: 'Busque, filtre e ordene a base. Clique no cliente para abrir a ficha completa.',
    montar: function (secao, _p, ctx) {
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao) + formularioFiltros() + '<div data-alvo="lista"></div>';
      var form = secao.querySelector('[data-form="filtros"]');
      var alvo = secao.querySelector('[data-alvo="lista"]');

      async function carregar() {
        alvo.innerHTML = P.htmlCarregando('Buscando clientes...');
        var q = Object.assign({}, filtros, { status_cliente: undefined });
        try {
          var p = P.normalizarPagina(await P.api('/v1/painel/clientes' + P.montarQuery(q)));
          if (!ctx.ativa()) return;
          alvo.innerHTML = tabela(p.data) + P.htmlPaginacao(p, p.total === 1 ? 'cliente' : 'clientes');
        } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        filtros = Object.assign({}, PADRAO, P.lerFormulario(form), { pagina: 1 });
        Object.keys(filtros).forEach(function (k) { if (filtros[k] === null) filtros[k] = ''; });
        carregar();
      });
      form.addEventListener('change', function (e) {
        if (e.target.tagName === 'SELECT') form.requestSubmit();
      });
      form.querySelector('[data-acao="limpar"]').addEventListener('click', function () {
        filtros = Object.assign({}, PADRAO);
        ctx.recarregar();
      });
      alvo.addEventListener('click', function (e) {
        var ordenar = e.target.closest('[data-ordenar]');
        if (ordenar) {
          var campo = ordenar.getAttribute('data-ordenar');
          filtros.ordem = filtros.ordenar_por === campo && filtros.ordem === 'asc' ? 'desc' : 'asc';
          filtros.ordenar_por = campo;
          filtros.pagina = 1;
          form.querySelector('[name="ordenar_por"]').value = campo;
          form.querySelector('[name="ordem"]').value = filtros.ordem;
          carregar();
          return;
        }
        var pag = e.target.closest('[data-pagina]');
        if (pag) { filtros.pagina = Number(pag.getAttribute('data-pagina')) || 1; carregar(); return; }
        if (e.target.closest('a, button')) return;
        var linha = e.target.closest('tr[data-href]');
        if (linha) window.location.hash = linha.getAttribute('data-href');
      });
      carregar();
    }
  });

  /* ======================= FICHA ======================= */

  function item(rotulo, valorHtml) { return '<div><dt>' + esc(rotulo) + '</dt><dd>' + valorHtml + '</dd></div>'; }

  function endereco(e) {
    if (!e) return '—';
    if (typeof e === 'string') return e;
    var linha1 = [e.logradouro, e.numero].filter(Boolean).join(', ') + (e.complemento ? ' - ' + e.complemento : '');
    var partes = [linha1, e.bairro, [e.cidade, e.uf].filter(Boolean).join('/'), e.cep ? 'CEP ' + P.cep(e.cep) : '']
      .filter(function (p) { return p && String(p).trim(); });
    return partes.length ? partes.join(' · ') : '—';
  }

  function ativacao(a, c) {
    if (!a) {
      return c && c.status === 'ativo'
        ? '<div class="aviso aviso-ok">Energia liberada: a jornada de ativação está concluída.</div>'
        : P.htmlVazio('Nenhuma jornada de ativação registrada.');
    }
    var atual = Math.max(1, Math.min(5, Number(a.etapa_atual) || 1));
    var etapas = Array.isArray(a.etapas) && a.etapas.length ? a.etapas : P.NOMES_ETAPAS.map(function (nome, i) {
      var n = i + 1;
      return { numero: n, nome: nome, situacao: n < atual ? 'concluida' : (n === atual ? 'atual' : 'pendente') };
    });
    var eventos = Array.isArray(a.eventos) ? a.eventos : [];
    var pct = P.ehNumero(a.percentual_concluido) ? Number(a.percentual_concluido) : (atual - 1) * 25;
    var html = '<ol class="etapas" aria-label="Etapas da ativação">' + etapas.map(function (e) {
      var sit = e.situacao || 'pendente';
      return '<li class="etapa etapa-' + esc(sit === 'concluida' ? 'concluida' : sit === 'atual' ? 'atual' : 'pendente') + '">' +
        '<span class="etapa-bolinha">' + (sit === 'concluida' ? '✓' : esc(e.numero)) + '</span>' + esc(e.nome || P.NOMES_ETAPAS[e.numero - 1]) + '</li>';
    }).join('') + '</ol>' +
      '<div class="barra-progresso espaco-cima"><span data-largura="' + esc(pct) + '"></span></div>' +
      '<p class="texto-suave espaco-cima">' + esc(P.numero(pct)) + '% concluído · previsão ' + esc(P.data(a.previsao_conclusao)) +
        ' · ' + esc(P.numero(a.dias_desde_cadastro)) + ' de ' + esc(P.ou(a.prazo_ativacao_dias, 90)) + ' dias</p>';
    if (eventos.length) {
      html += '<ol class="linha-tempo">' + eventos.slice().reverse().map(function (ev) {
        return '<li><strong>Etapa ' + esc(ev.etapa) + ' · ' + esc(P.NOMES_ETAPAS[(Number(ev.etapa) || 1) - 1]) + '</strong>' +
          '<small>' + esc(P.dataHora(ev.ocorrido_em)) + (ev.observacao ? ' — ' + esc(ev.observacao) : '') + '</small></li>';
      }).join('') + '</ol>';
    }
    if (c && c.id_app) {
      html += '<form class="form-etapa" data-form="etapa">' +
        '<div class="campo"><label for="etapa-nova">Mudar etapa no app</label><select id="etapa-nova" name="etapa">' +
        P.NOMES_ETAPAS.map(function (n, i) { return '<option value="' + (i + 1) + '"' + (i + 1 === atual ? ' selected' : '') + '>' + (i + 1) + ' · ' + esc(n) + '</option>'; }).join('') +
        '</select></div><div class="campo campo-largo"><label for="etapa-obs">Observação (opcional)</label>' +
        '<input id="etapa-obs" name="observacao" maxlength="255" autocomplete="off" placeholder="Ex.: documentos conferidos"></div>' +
        '<button type="submit" class="botao botao-primario">Atualizar no app</button></form>';
    } else {
      html += '<p class="texto-suave espaco-cima">Cliente da base fictícia: a etapa só pode ser alterada para clientes do app.</p>';
    }
    return html;
  }

  function economia(e) {
    if (!e) return P.htmlVazio('Sem dados de economia.');
    return '<div class="mini-numeros">' +
      '<div><strong class="texto-ok">' + esc(P.moeda(e.economia_total)) + '</strong><span>economia total</span></div>' +
      '<div><strong>' + esc(P.moeda(e.economia_total_desconto)) + '</strong><span>em desconto</span></div>' +
      '<div><strong>' + esc(P.moeda(e.bonus_indicacao_total)) + '</strong><span>bônus de indicação</span></div>' +
      '<div><strong>' + esc(P.moeda(e.bonus_clube_total || 0)) + '</strong><span>bônus do Clube</span></div>' +
      '<div><strong>' + esc(P.numero(e.faturas_vencidas)) + '</strong><span>faturas vencidas</span></div>' +
      '<div><strong>' + esc(P.moeda(e.valor_em_aberto)) + '</strong><span>em aberto</span></div></div>';
  }

  function faturas(lista) {
    if (!Array.isArray(lista) || !lista.length) return P.htmlVazio('Nenhuma fatura emitida ainda.');
    var ordenadas = lista.slice().sort(function (a, b) { return String(a.mes_referencia).localeCompare(String(b.mes_referencia)); }).slice(-6);
    var grafico = G.colunas(ordenadas.map(function (f) { return P.mesCurto(f.mes_referencia); }), [
      { nome: 'Sem a Bulbe', valores: ordenadas.map(function (f) { return f.valor_sem_bulbe; }), cor: 5 },
      { nome: 'Com a Bulbe', valores: ordenadas.map(function (f) { return f.valor_total; }), cor: 3 }
    ], function (v) { return 'R$ ' + P.numero(Math.round(v)); });
    return grafico + '<div class="tabela-rolagem espaco-cima"><table class="tabela"><thead><tr><th>Mês</th><th class="col-numero">kWh</th>' +
      '<th class="col-numero">Sem Bulbe</th><th class="col-numero">Desconto</th><th class="col-numero">Bônus</th><th class="col-numero">Total</th>' +
      '<th>Vencimento</th><th>Situação</th></tr></thead><tbody>' + lista.map(function (f) {
        return '<tr><td class="col-nowrap">' + esc(P.mesReferencia(f.mes_referencia)) + '</td>' +
          '<td class="col-numero">' + esc(P.numero(f.consumo_kwh)) + '</td>' +
          '<td class="col-numero">' + esc(P.moeda(f.valor_sem_bulbe)) + '</td>' +
          '<td class="col-numero">' + esc(P.moeda(f.desconto)) + '</td>' +
          '<td class="col-numero">' + esc(P.moeda((Number(f.bonus_indicacao) || 0) + (Number(f.bonus_clube) || 0))) + '</td>' +
          '<td class="col-numero"><strong>' + esc(P.moeda(f.valor_total)) + '</strong></td>' +
          '<td class="col-nowrap">' + esc(P.data(f.vencimento)) + '</td><td>' + P.selo(f.situacao) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }

  function listaSimples(lista, vazio, linha) {
    if (!Array.isArray(lista) || !lista.length) return P.htmlVazio(vazio);
    return '<ul class="lista-compacta">' + lista.map(linha).join('') + '</ul>';
  }

  function indicacoes(ind) {
    if (!ind) return P.htmlVazio('Sem dados de indicação.');
    return '<p class="texto-suave">Código <code>' + esc(P.ou(ind.codigo_indicacao)) + '</code> · ' + esc(P.numero(ind.total)) +
      ' indicação(ões) · <strong>' + esc(P.moeda(ind.bonus_acumulado)) + '</strong> de bônus</p>' +
      listaSimples(ind.data, 'Nenhuma indicação feita ainda.', function (i) {
        return '<li><span>' + esc(P.ou(i.nome_indicado)) + ' <small class="texto-suave">' + esc(P.rotulo(i.canal)) + ' · ' + esc(P.data(i.criado_em)) + '</small></span>' + P.selo(i.situacao) + '</li>';
      });
  }

  function clube(c, cupons) {
    var html = '';
    if (c) {
      var meta = Number(c.meta_sequencia) || 5;
      var feitas = Math.max(0, Math.min(meta, Number(c.semanas_sequencia) || 0));
      html += '<p>Sequência: <strong>' + esc(feitas) + ' de ' + esc(meta) + '</strong> semanas · próxima carta em ' + esc(P.data(c.proxima_carta_em)) + '</p>' +
        '<div class="barra-progresso espaco-cima"><span class="leg-4" data-largura="' + (feitas * 100 / meta) + '"></span></div>';
    } else {
      html += P.htmlVazio('Ainda não participa do Clube Bulbe.');
    }
    return html + '<h3 class="subtitulo">Cupons</h3>' + listaSimples(cupons, 'Nenhum cupom liberado.', function (k) {
      return '<li><span>' + esc(P.ou(k.titulo)) + ' <small class="texto-suave">' + esc((k.parceiro && k.parceiro.nome) || '') +
        (k.codigo ? ' · ' + esc(k.codigo) : '') + (k.valido_ate ? ' · até ' + esc(P.data(k.valido_ate)) : '') + '</small></span>' + P.selo(k.situacao) + '</li>';
    });
  }

  function atendimentos(lista) {
    return listaSimples(lista, 'Nenhum atendimento registrado.', function (a) {
      return '<li><span><a href="#/atendimento/' + encodeURIComponent(a.id) + '">' + esc(P.ou(a.assunto)) + '</a> <small class="texto-suave">' +
        esc(P.rotulo(a.canal)) + ' · ' + esc(P.dataHora(a.criado_em)) + '</small></span>' + P.selo(a.status) + '</li>';
    });
  }

  function notificacoes(lista) {
    return listaSimples(lista, 'Nenhuma notificação enviada.', function (n) {
      return '<li><span>' + esc(P.ou(n.titulo)) + ' <small class="texto-suave">' + esc(P.rotulo(n.tipo)) + ' · ' + esc(P.dataHora(n.enviada_em)) + '</small></span>' +
        (n.lida ? P.seloTom('ok', 'Lida') : P.seloTom('neutro', 'Não lida')) + '</li>';
    });
  }

  function renderFicha(f) {
    var c = f.cliente || {};
    var usina = c.usina ? esc(c.usina.nome) + (c.usina.localizacao ? ' <span class="texto-suave">(' + esc(c.usina.localizacao) + ')</span>' : '') : '—';
    var cabecalho = '<div class="ficha-cabecalho"><div class="pessoa"><span class="avatar" aria-hidden="true">' + esc(P.iniciais(c.nome)) + '</span>' +
      '<div><h1 tabindex="-1">' + esc(P.ou(c.nome, 'Cliente')) + '</h1><div class="ficha-meta">' + P.selo(c.status) +
      (c.origem === 'app' ? '<span class="selo selo-app">App</span>' : '') +
      '<span>Cliente desde ' + esc(P.data(c.criado_em)) + '</span><span>ID ' + esc(c.id) + '</span></div></div></div>' +
      '<div class="tela-acoes"><a class="botao botao-secundario" href="#/clientes">← Voltar</a>' +
      '<button type="button" class="botao botao-primario" data-acao="perguntar">Perguntar ao assistente</button></div></div>';
    var dados = '<dl class="dados">' +
      item('E-mail', esc(P.ou(c.email))) + item('CPF', esc(P.cpf(c.cpf))) + item('Telefone', esc(P.telefone(c.telefone))) +
      item('Tipo', esc(P.rotulo(c.tipo))) + item('Endereço', esc(endereco(c.endereco))) + item('Distribuidora', esc(P.ou(c.distribuidora))) +
      item('Nº da instalação', esc(P.ou(c.numero_instalacao))) + item('Usina', usina) +
      item('Código de indicação', c.codigo_indicacao ? '<code>' + esc(c.codigo_indicacao) + '</code>' : '—') +
      item('Acesso ao app', esc(P.simNao(c.app_acesso_habilitado))) +
      item('Último login no app', esc(c.ultimo_login_app ? P.dataHora(c.ultimo_login_app) : 'Nunca acessou')) +
      '</dl>';
    return cabecalho + '<div class="grade grade-12">' +
      '<div class="col-7">' + P.cartao('Jornada de ativação', ativacao(f.ativacao, c), '5 etapas · até 90 dias') + '</div>' +
      '<div class="col-5">' + P.cartao('Dados cadastrais', dados) + '</div>' +
      '<div class="col-12">' + P.cartao('Economia', economia(f.economia)) + '</div>' +
      '<div class="col-12">' + P.cartao('Faturas', faturas(f.faturas), 'Quanto o cliente pagaria sem a Bulbe e quanto paga com ela') + '</div>' +
      '<div class="col-6">' + P.cartao('Clube Bulbe', clube(f.clube, f.cupons)) + '</div>' +
      '<div class="col-6">' + P.cartao('Indique e Ganhe', indicacoes(f.indicacoes), 'R$ 50 por indicação que aderir') + '</div>' +
      '<div class="col-6">' + P.cartao('Atendimentos', atendimentos(f.atendimentos)) + '</div>' +
      '<div class="col-6">' + P.cartao('Notificações', notificacoes(f.notificacoes)) + '</div>' +
      '</div>';
  }

  P.tela('ficha', {
    titulo: 'Ficha do cliente',
    montar: async function (secao, id, ctx) {
      secao.innerHTML = P.htmlCarregando('Carregando ficha do cliente...');
      P.estado.fichaAtual = null;
      async function carregar() {
        try {
          var ficha = await P.api('/v1/painel/clientes/' + encodeURIComponent(id));
          if (!ctx.ativa()) return;
          P.estado.fichaAtual = ficha && ficha.cliente;
          secao.innerHTML = renderFicha(ficha || {});
          P.aplicarLarguras(secao);
          document.title = (P.estado.fichaAtual ? P.estado.fichaAtual.nome + ' · ' : '') + 'Painel Bulbe';
        } catch (erro) {
          if (erro.status === 401) return;
          secao.innerHTML = P.cabecalhoTela(erro.status === 404 ? 'Cliente não encontrado' : 'Ficha do cliente') + P.htmlErro(erro) +
            '<p><a class="botao botao-secundario" href="#/clientes">← Voltar para clientes</a></p>';
        }
      }
      secao.addEventListener('click', function (e) {
        if (e.target.closest('[data-acao="perguntar"]') && P.assistente) P.assistente.perguntarSobreCliente();
      });
      secao.addEventListener('submit', async function (e) {
        var form = e.target.closest('[data-form="etapa"]');
        if (!form) return;
        e.preventDefault();
        var dados = P.lerFormulario(form);
        try {
          await P.comBotao(form.querySelector('button'), function () {
            return P.api('/v1/painel/clientes/' + encodeURIComponent(id) + '/ativacao', {
              metodo: 'PATCH', corpo: { etapa_atual: Number(dados.etapa), observacao: dados.observacao }
            });
          });
          P.toast('Etapa atualizada no app. O cliente já vê a mudança.', 'ok');
          carregar();
        } catch (erro) { P.toastErro(erro); }
      });
      await carregar();
    }
  });
})();
