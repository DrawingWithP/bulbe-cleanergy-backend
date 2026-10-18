/* ============================================================
   PAINEL DE GESTÃO BULBE — aplicação de uma página
   - Autenticação: token Bearer guardado no sessionStorage (401 -> volta ao login).
   - Rotas por hash: #/visao-geral, #/clientes, #/cliente/<id>, #/adesoes, #/atendimentos.
   - Chat lateral com o assistente (POST /v1/painel/chat), histórico só em memória.
   SEGURANÇA: todo dado vindo da API passa por esc() antes de entrar no HTML.
   ============================================================ */
(function () {
  'use strict';

  /* ------------------------------------------------------------
     CONSTANTES
     ------------------------------------------------------------ */
  var CHAVE_TOKEN = 'bulbe_painel_token';
  var CHAVE_FUNCIONARIO = 'bulbe_painel_funcionario';
  var CHAVE_CHAT_ABERTO = 'bulbe_painel_chat_aberto';
  var MAX_HISTORICO = 20;
  var MAX_MENSAGEM = 2000;
  var TEMPO_LIMITE_PADRAO = 30000;
  var TEMPO_LIMITE_CHAT = 120000;

  var NOMES_ETAPAS = ['Cadastro', 'Documentos', 'Solicitação à CEMIG', 'Análise CEMIG', 'Energia liberada'];
  var MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

  var ROTULOS = {
    ativo: 'Ativo', ativa: 'Ativa', em_ativacao: 'Em ativação', cancelado: 'Cancelado',
    em_manutencao: 'Em manutenção', inativa: 'Inativa',
    paga: 'Paga', em_aberto: 'Em aberto', vencida: 'Vencida',
    pendente: 'Pendente', aderiu: 'Aderiu', expirada: 'Expirada', expirado: 'Expirado',
    rascunho: 'Rascunho', enviada: 'Enviada', aprovada: 'Aprovada', recusada: 'Recusada',
    aberto: 'Aberto', em_andamento: 'Em andamento', resolvido: 'Resolvido',
    salvo: 'Salvo', usado: 'Usado', descartado: 'Descartado',
    disponivel: 'Disponível', aberta: 'Aberta', normal: 'Normal', especial: 'Especial',
    residencia: 'Residência', empresa: 'Empresa',
    whatsapp: 'WhatsApp', email: 'E-mail', app: 'App', site: 'Site', link: 'Link', ouvidoria: 'Ouvidoria',
    vencimento: 'Vencimento', ativacao: 'Ativação', clube: 'Clube Bulbe', indicacao: 'Indicação', promocao: 'Promoção',
    admin: 'Administrador', atendimento: 'Atendimento',
    concluida: 'Concluída', atual: 'Etapa atual', visitante: 'Visitante', cliente: 'Cliente'
  };

  var TONS = {
    ativo: 'ok', ativa: 'ok', paga: 'ok', aderiu: 'ok', aprovada: 'ok', resolvido: 'ok', aberta: 'ok', concluida: 'ok',
    em_ativacao: 'alerta', em_manutencao: 'alerta', em_aberto: 'alerta', pendente: 'alerta', aberto: 'alerta', atual: 'alerta',
    enviada: 'info', em_andamento: 'info', salvo: 'info', disponivel: 'info',
    cancelado: 'erro', inativa: 'erro', vencida: 'erro', recusada: 'erro'
  };

  var ICONE_CHECK = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>';

  /* ------------------------------------------------------------
     ESTADO
     ------------------------------------------------------------ */
  var estado = {
    saindo: false,
    funcionario: null,
    clientesCarregados: false,
    adesoesCarregadas: false,
    atendimentosCarregados: false,
    seqFicha: 0,
    fichaAtual: null,
    chat: { historico: [], enviando: false, aberto: true }
  };

  /* ------------------------------------------------------------
     UTILIDADES: escape e formatação pt-BR
     ------------------------------------------------------------ */
  function $(id) { return document.getElementById(id); }

  /** Escapa qualquer valor para uso seguro em HTML (texto e atributos). */
  function esc(valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  var formatoMoeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  var formatoNumero = new Intl.NumberFormat('pt-BR');

  function ehNumero(v) {
    return v !== null && v !== undefined && v !== '' && !isNaN(Number(v));
  }
  function moeda(v) { return ehNumero(v) ? formatoMoeda.format(Number(v)) : '—'; }
  function numero(v) { return ehNumero(v) ? formatoNumero.format(Number(v)) : '—'; }
  function ou(v, padrao) { return (v === null || v === undefined || v === '') ? (padrao === undefined ? '—' : padrao) : v; }

  /** Converte string ISO em Date. Datas puras (AAAA-MM-DD) ficam no fuso local; datetimes sem fuso são UTC. */
  function paraData(valor) {
    if (!valor) return null;
    var texto = String(valor).trim();
    var soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
    if (soData) return new Date(Number(soData[1]), Number(soData[2]) - 1, Number(soData[3]));
    texto = texto.replace(' ', 'T');
    if (/T\d{2}:\d{2}/.test(texto) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(texto)) texto += 'Z';
    var d = new Date(texto);
    return isNaN(d.getTime()) ? null : d;
  }
  function data(valor) {
    var d = paraData(valor);
    return d ? d.toLocaleDateString('pt-BR') : '—';
  }
  function dataHora(valor) {
    if (valor && /^\d{4}-\d{2}-\d{2}$/.test(String(valor))) return data(valor);
    var d = paraData(valor);
    return d ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
  }
  function mesReferencia(valor) {
    var m = /^(\d{4})-(\d{2})/.exec(String(valor || ''));
    return m ? MESES[Number(m[2]) - 1] + '/' + m[1] : ou(valor);
  }
  function soDigitos(v) { return String(v || '').replace(/\D/g, ''); }
  function cpf(v) {
    var d = soDigitos(v);
    return d.length === 11 ? d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4') : ou(v);
  }
  function telefone(v) {
    var d = soDigitos(v);
    if (d.length === 11) return d.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    if (d.length === 10) return d.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    return ou(v);
  }
  function cep(v) {
    var d = soDigitos(v);
    return d.length === 8 ? d.replace(/(\d{5})(\d{3})/, '$1-$2') : ou(v);
  }
  function rotulo(v) {
    if (v === null || v === undefined || v === '') return '—';
    if (Object.prototype.hasOwnProperty.call(ROTULOS, v)) return ROTULOS[v];
    var t = String(v).replace(/_/g, ' ');
    return t.charAt(0).toUpperCase() + t.slice(1);
  }
  function selo(v) {
    if (v === null || v === undefined || v === '') return '—';
    var tom = Object.prototype.hasOwnProperty.call(TONS, v) ? TONS[v] : 'neutro';
    return '<span class="selo selo-' + tom + '">' + esc(rotulo(v)) + '</span>';
  }
  function simNao(v) { return v ? 'Sim' : 'Não'; }
  function iniciais(nome) {
    var partes = String(nome || '?').trim().split(/\s+/);
    var p = partes[0] ? partes[0].charAt(0) : '?';
    var u = partes.length > 1 ? partes[partes.length - 1].charAt(0) : '';
    return (p + u).toUpperCase();
  }
  function hashCliente(id) { return '#/cliente/' + encodeURIComponent(String(id)); }

  function htmlVazio(msg) { return '<p class="vazio">' + esc(msg) + '</p>'; }
  function htmlCarregando(msg) { return '<p class="carregando" role="status">' + esc(msg || 'Carregando...') + '</p>'; }
  function htmlErro(erro) {
    var msg = (erro && erro.message) ? erro.message : 'Não foi possível carregar os dados.';
    return '<div class="aviso aviso-erro" role="alert">' + esc(msg) + '</div>';
  }

  /** Aplica larguras via CSSOM (compatível com a CSP sem 'unsafe-inline'). */
  function aplicarLarguras(raiz) {
    var elementos = raiz.querySelectorAll('[data-largura]');
    window.requestAnimationFrame(function () {
      elementos.forEach(function (el) {
        var v = Math.max(0, Math.min(100, Number(el.getAttribute('data-largura')) || 0));
        el.style.width = v + '%';
      });
    });
  }

  function lerSessao(chave) { try { return sessionStorage.getItem(chave); } catch (e) { return null; } }
  function removerSessao(chave) { try { sessionStorage.removeItem(chave); } catch (e) { /* ignora */ } }
  function lerPreferencia(chave) { try { return localStorage.getItem(chave); } catch (e) { return null; } }
  function gravarPreferencia(chave, valor) { try { localStorage.setItem(chave, valor); } catch (e) { /* ignora */ } }

  /* ------------------------------------------------------------
     SESSÃO E API
     ------------------------------------------------------------ */
  function sair(motivo) {
    if (estado.saindo) return;
    estado.saindo = true;
    removerSessao(CHAVE_TOKEN);
    removerSessao(CHAVE_FUNCIONARIO);
    window.location.replace('/painel/index.html?sessao=' + encodeURIComponent(motivo || 'encerrada'));
  }

  function ErroApi(code, message, status) {
    this.name = 'ErroApi';
    this.code = code;
    this.message = message;
    this.status = status;
  }
  ErroApi.prototype = Object.create(Error.prototype);
  ErroApi.prototype.constructor = ErroApi;

  /** Aceita {"error": {...}}, {"detail": {"error": {...}}}, {"detail": "texto"} e erros 422 do FastAPI. */
  function extrairErro(dados, status) {
    var erro = null;
    if (dados && dados.error) erro = dados.error;
    else if (dados && dados.detail && dados.detail.error) erro = dados.detail.error;
    if (erro) return { code: erro.code || 'ERRO', message: erro.message || 'Erro inesperado.' };
    if (dados && typeof dados.detail === 'string') return { code: 'ERRO', message: dados.detail };
    if (status === 422) return { code: 'DADOS_INVALIDOS', message: 'Dados inválidos na requisição.' };
    if (status === 404) return { code: 'NAO_ENCONTRADO', message: 'Recurso não encontrado.' };
    if (status >= 500) return { code: 'ERRO_SERVIDOR', message: 'Erro no servidor (' + status + '). Tente novamente.' };
    return { code: 'ERRO', message: 'Erro inesperado (' + status + ').' };
  }

  function montarQuery(params) {
    var busca = new URLSearchParams();
    Object.keys(params).forEach(function (chave) {
      var v = params[chave];
      if (v !== null && v !== undefined && String(v).trim() !== '') busca.append(chave, String(v).trim());
    });
    var texto = busca.toString();
    return texto ? '?' + texto : '';
  }

  async function api(caminho, opcoes) {
    opcoes = opcoes || {};
    var token = lerSessao(CHAVE_TOKEN);
    var headers = { 'Accept': 'application/json' };
    var corpo;
    if (opcoes.corpo !== undefined) {
      headers['Content-Type'] = 'application/json';
      corpo = JSON.stringify(opcoes.corpo);
    }
    if (token) headers['Authorization'] = 'Bearer ' + token;

    var controle = new AbortController();
    var temporizador = setTimeout(function () { controle.abort(); }, opcoes.tempoLimite || TEMPO_LIMITE_PADRAO);
    var resposta;
    try {
      resposta = await fetch(caminho, {
        method: opcoes.metodo || 'GET',
        headers: headers,
        body: corpo,
        signal: controle.signal,
        cache: 'no-store',
        credentials: 'same-origin'
      });
    } catch (e) {
      clearTimeout(temporizador);
      if (e && e.name === 'AbortError') {
        throw new ErroApi('TEMPO_ESGOTADO', 'O servidor demorou demais para responder. Tente novamente.', 0);
      }
      throw new ErroApi('SEM_CONEXAO', 'Sem conexão com o servidor. Verifique se a API está no ar.', 0);
    }
    clearTimeout(temporizador);

    var dados = null;
    try { dados = await resposta.json(); } catch (e) { dados = null; }

    if (resposta.status === 401) {
      sair('expirada');
      throw new ErroApi('NAO_AUTENTICADO', 'Sessão expirada. Redirecionando para o login...', 401);
    }
    if (!resposta.ok) {
      var info = extrairErro(dados, resposta.status);
      throw new ErroApi(info.code, info.message, resposta.status);
    }
    return dados;
  }

  /* ------------------------------------------------------------
     ROTEAMENTO
     ------------------------------------------------------------ */
  var TITULOS = {
    'visao-geral': 'Visão geral',
    'clientes': 'Clientes',
    'ficha': 'Ficha do cliente',
    'adesoes': 'Adesões',
    'atendimentos': 'Atendimentos'
  };

  function lerRota() {
    var hash = window.location.hash || '';
    var m = /^#\/cliente\/(.+)$/.exec(hash);
    if (m) {
      var id;
      try { id = decodeURIComponent(m[1]); } catch (e) { id = m[1]; }
      return { tela: 'ficha', id: id };
    }
    var nome = hash.replace(/^#\//, '');
    return { tela: Object.prototype.hasOwnProperty.call(TITULOS, nome) && nome !== 'ficha' ? nome : 'visao-geral' };
  }

  function navegar() {
    var rota = lerRota();
    document.querySelectorAll('.tela').forEach(function (tela) {
      tela.hidden = tela.getAttribute('data-tela') !== rota.tela;
    });
    var menuAtivo = rota.tela === 'ficha' ? 'clientes' : rota.tela;
    document.querySelectorAll('.menu-item').forEach(function (item) {
      if (item.getAttribute('data-rota') === menuAtivo) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
    $('barra-titulo').textContent = TITULOS[rota.tela];
    document.title = TITULOS[rota.tela] + ' · Painel Bulbe';
    window.scrollTo(0, 0);

    if (rota.tela === 'visao-geral') {
      carregarVisaoGeral();
      focarTitulo('titulo-visao-geral');
    } else if (rota.tela === 'clientes') {
      if (!estado.clientesCarregados) carregarClientes();
      focarTitulo('titulo-clientes');
    } else if (rota.tela === 'ficha') {
      carregarFicha(rota.id);
    } else if (rota.tela === 'adesoes') {
      if (!estado.adesoesCarregadas) carregarAdesoes();
      focarTitulo('titulo-adesoes');
    } else if (rota.tela === 'atendimentos') {
      if (!estado.atendimentosCarregados) carregarAtendimentos();
      focarTitulo('titulo-atendimentos');
    }
  }

  function focarTitulo(id) {
    var el = $(id);
    if (el) el.focus({ preventScroll: true });
  }

  /* ------------------------------------------------------------
     VISÃO GERAL
     ------------------------------------------------------------ */
  function cartaoMetrica(rotuloTexto, valor, detalhe, tom) {
    return '<div class="metrica' + (tom ? ' metrica-' + tom : '') + '">' +
      '<span class="metrica-rotulo">' + esc(rotuloTexto) + '</span>' +
      '<span class="metrica-valor">' + esc(valor) + '</span>' +
      (detalhe ? '<span class="metrica-detalhe">' + esc(detalhe) + '</span>' : '') +
      '</div>';
  }

  /** itens: [{rotulo, sub, valor, tom}] — barra proporcional ao maior valor (ou ao total informado). */
  function htmlBarras(itens, base) {
    var maior = base || itens.reduce(function (m, i) { return Math.max(m, Number(i.valor) || 0); }, 0);
    return '<ul class="barras">' + itens.map(function (i) {
      var v = Number(i.valor) || 0;
      var pct = maior > 0 ? (v / maior) * 100 : 0;
      return '<li class="barra-linha">' +
        '<span class="barra-rotulo">' + esc(i.rotulo) + (i.sub ? ' <small>' + esc(i.sub) + '</small>' : '') + '</span>' +
        '<span class="barra-trilho" role="img" aria-label="' + esc(i.rotulo + ': ' + numero(v)) + '">' +
        '<span class="barra-preenchimento tom-' + esc(i.tom || 'azul') + '" data-largura="' + pct.toFixed(1) + '"></span></span>' +
        '<span class="barra-valor">' + esc(numero(v)) + '</span>' +
        '</li>';
    }).join('') + '</ul>';
  }

  async function carregarVisaoGeral() {
    var alvo = $('visao-geral-conteudo');
    alvo.setAttribute('aria-busy', 'true');
    if (!alvo.innerHTML) alvo.innerHTML = htmlCarregando('Carregando indicadores...');
    try {
      var resultados = await Promise.all([
        api('/v1/painel/metricas'),
        api('/v1/painel/usinas').catch(function () { return null; }),
        api('/v1/painel/parceiros').catch(function () { return null; })
      ]);
      alvo.innerHTML = renderVisaoGeral(resultados[0] || {}, resultados[1], resultados[2]);
      aplicarLarguras(alvo);
    } catch (erro) {
      if (erro.status !== 401) alvo.innerHTML = htmlErro(erro);
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  function renderVisaoGeral(m, usinas, parceiros) {
    var cli = m.clientes || {};
    var fat = m.faturas || {};
    var ind = m.indicacoes || {};
    var clube = m.clube || {};
    var ades = m.adesoes || {};
    var app = m.app || {};
    var porEtapa = m.ativacao_por_etapa || {};

    var html = '<div class="grade grade-metricas">' +
      cartaoMetrica('Clientes', numero(cli.total),
        numero(cli.ativo) + ' ativos · ' + numero(cli.em_ativacao) + ' em ativação · ' + numero(cli.cancelado) + ' cancelados') +
      cartaoMetrica('Economia gerada', moeda(m.economia_total_gerada), 'Desconto de 15% + bônus de indicação', 'verde') +
      cartaoMetrica('Faturas vencidas', numero(fat.vencidas),
        moeda(fat.valor_vencido) + ' em atraso · ' + numero(fat.em_aberto) + ' em aberto', 'vermelha') +
      cartaoMetrica('Indicações', numero(ind.total),
        numero(ind.aderiu) + ' aderiram · ' + numero(ind.pendente) + ' pendentes', 'verde') +
      cartaoMetrica('Clube Bulbe', numero(clube.clientes_com_sequencia),
        'clientes em sequência · ' + numero(clube.cupons_ativos) + ' cupons ativos · ' + numero(clube.cupons_usados) + ' usados', 'amarela') +
      cartaoMetrica('Adesões aguardando', numero(ades.enviada),
        numero(ades.aprovada) + ' aprovadas · ' + numero(ades.recusada) + ' recusadas · ' + numero(ades.rascunho) + ' rascunhos', 'amarela') +
      cartaoMetrica('Simulações (30 dias)', numero(m.simulacoes_30_dias), 'Simulador do app e do site') +
      cartaoMetrica('Acesso ao app', numero(app.clientes_com_acesso),
        numero(app.logins_ultimos_30_dias) + ' logins nos últimos 30 dias') +
      '</div>';

    var itensEtapa = NOMES_ETAPAS.map(function (nome, i) {
      var n = i + 1;
      var valor = porEtapa[String(n)] !== undefined ? porEtapa[String(n)] : porEtapa[n];
      return { rotulo: n + '. ' + nome, valor: valor || 0, tom: n === 5 ? 'verde' : (n >= 3 ? 'amarelo' : 'azul') };
    });
    var itensStatus = [
      { rotulo: 'Ativos', valor: cli.ativo, tom: 'verde' },
      { rotulo: 'Em ativação', valor: cli.em_ativacao, tom: 'amarelo' },
      { rotulo: 'Cancelados', valor: cli.cancelado, tom: 'cinza' }
    ];
    var itensAdesao = [
      { rotulo: 'Rascunho', valor: ades.rascunho, tom: 'cinza' },
      { rotulo: 'Enviada', valor: ades.enviada, tom: 'azul' },
      { rotulo: 'Aprovada', valor: ades.aprovada, tom: 'verde' },
      { rotulo: 'Recusada', valor: ades.recusada, tom: 'vermelho' }
    ];

    html += '<div class="grade grade-2">' +
      '<section class="cartao" aria-labelledby="t-ativacao-etapa">' +
        '<h2 class="cartao-titulo" id="t-ativacao-etapa">Ativação por etapa <span class="texto-suave">clientes em cada etapa da jornada (até 90 dias)</span></h2>' +
        htmlBarras(itensEtapa) +
      '</section>' +
      '<section class="cartao" aria-labelledby="t-status-clientes">' +
        '<h2 class="cartao-titulo" id="t-status-clientes">Clientes por status</h2>' +
        htmlBarras(itensStatus, Number(cli.total) || 0) +
        '<h2 class="cartao-titulo cartao-titulo-espaco" id="t-adesoes-sit">Adesões por situação</h2>' +
        htmlBarras(itensAdesao) +
      '</section>' +
      '</div>';

    html += '<div class="grade grade-2">' +
      '<section class="cartao" aria-labelledby="t-usinas"><h2 class="cartao-titulo" id="t-usinas">Usinas</h2>' +
        renderUsinas(usinas) + '</section>' +
      '<section class="cartao" aria-labelledby="t-parceiros"><h2 class="cartao-titulo" id="t-parceiros">Parceiros do Clube Bulbe</h2>' +
        renderParceiros(parceiros) + '</section>' +
      '</div>';

    return html;
  }

  function renderUsinas(usinas) {
    if (!Array.isArray(usinas)) return htmlVazio('Não foi possível carregar as usinas.');
    if (!usinas.length) return htmlVazio('Nenhuma usina cadastrada.');
    return '<ul class="lista-itens">' + usinas.map(function (u) {
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(u.nome) + '</span>' + selo(u.status) + '</div>' +
        '<span class="texto-suave">' + esc(ou(u.localizacao)) + ' · ' + esc(numero(u.capacidade_geracao_kwh)) + ' kWh' +
        (u.data_ativacao ? ' · ativa desde ' + esc(data(u.data_ativacao)) : '') + '</span></li>';
    }).join('') + '</ul>';
  }

  function renderParceiros(parceiros) {
    if (!Array.isArray(parceiros)) return htmlVazio('Não foi possível carregar os parceiros.');
    if (!parceiros.length) return htmlVazio('Nenhum parceiro ativo.');
    return '<ul class="lista-itens">' + parceiros.map(function (p) {
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(p.nome) + '</span>' +
        (p.ativo === false ? selo('inativa') : '') + '</div>' +
        '<span class="texto-suave">' + esc(ou(p.categoria)) + '</span></li>';
    }).join('') + '</ul>';
  }

  /* ------------------------------------------------------------
     CLIENTES
     ------------------------------------------------------------ */
  async function carregarClientes() {
    var alvo = $('clientes-resultado');
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando('Buscando clientes...');
    var query = montarQuery({
      termo: $('filtro-termo').value,
      status: $('filtro-status').value,
      cidade: $('filtro-cidade').value,
      limite: $('filtro-limite').value
    });
    try {
      var lista = await api('/v1/painel/clientes' + query);
      estado.clientesCarregados = true;
      alvo.innerHTML = renderTabelaClientes(Array.isArray(lista) ? lista : []);
    } catch (erro) {
      if (erro.status !== 401) alvo.innerHTML = htmlErro(erro);
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  function renderTabelaClientes(lista) {
    if (!lista.length) return htmlVazio('Nenhum cliente encontrado com esses filtros.');
    var linhas = lista.map(function (c) {
      var href = hashCliente(c.id);
      return '<tr class="linha-clicavel" data-href="' + esc(href) + '">' +
        '<td><a class="link-linha" href="' + esc(href) + '">' + esc(c.nome) + '</a></td>' +
        '<td>' + esc(ou(c.email)) + '</td>' +
        '<td class="col-nowrap">' + esc(cpf(c.cpf)) + '</td>' +
        '<td>' + esc(ou(c.cidade)) + (c.uf ? '/' + esc(c.uf) : '') + '</td>' +
        '<td>' + selo(c.status) + '</td>' +
        '<td class="col-numero">' + (ehNumero(c.etapa_ativacao) ? esc(c.etapa_ativacao) + '/5' : '—') + '</td>' +
        '<td class="col-nowrap">' + esc(data(c.criado_em)) + '</td>' +
        '</tr>';
    }).join('');
    return '<p class="tabela-resumo">' + esc(lista.length) + ' cliente(s). Clique na linha para abrir a ficha.</p>' +
      '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Resultado da busca de clientes</caption>' +
      '<thead><tr><th scope="col">Nome</th><th scope="col">E-mail</th><th scope="col">CPF</th><th scope="col">Cidade</th>' +
      '<th scope="col">Status</th><th scope="col" class="col-numero">Etapa</th><th scope="col">Cliente desde</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     FICHA DO CLIENTE
     ------------------------------------------------------------ */
  async function carregarFicha(id) {
    var alvo = $('ficha-conteudo');
    var seq = ++estado.seqFicha;
    estado.fichaAtual = null;
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando('Carregando ficha do cliente...');
    try {
      var ficha = await api('/v1/painel/clientes/' + encodeURIComponent(id));
      if (seq !== estado.seqFicha) return; // resposta antiga: o usuário já navegou
      estado.fichaAtual = ficha && ficha.cliente ? ficha.cliente : null;
      alvo.innerHTML = renderFicha(ficha || {});
      aplicarLarguras(alvo);
      document.title = (estado.fichaAtual ? estado.fichaAtual.nome + ' · ' : '') + 'Painel Bulbe';
      focarTitulo('titulo-ficha');
    } catch (erro) {
      if (seq !== estado.seqFicha || erro.status === 401) return;
      alvo.innerHTML = erro.status === 404
        ? '<h1 class="tela-titulo" id="titulo-ficha" tabindex="-1">Cliente não encontrado</h1>' +
          '<div class="aviso aviso-alerta" role="alert">Não existe cliente com o id <code>' + esc(id) + '</code>.</div>'
        : '<h1 class="tela-titulo" id="titulo-ficha" tabindex="-1">Ficha do cliente</h1>' + htmlErro(erro);
      focarTitulo('titulo-ficha');
    } finally {
      if (seq === estado.seqFicha) alvo.removeAttribute('aria-busy');
    }
  }

  function cartao(id, titulo, conteudo, complemento) {
    return '<section class="cartao" aria-labelledby="' + id + '">' +
      '<h2 class="cartao-titulo" id="' + id + '">' + esc(titulo) +
      (complemento ? ' <span class="texto-suave">' + esc(complemento) + '</span>' : '') + '</h2>' +
      conteudo + '</section>';
  }

  function itemDado(rotuloTexto, valorHtml) {
    return '<div><dt>' + esc(rotuloTexto) + '</dt><dd>' + valorHtml + '</dd></div>';
  }

  function formatarEndereco(e) {
    if (!e) return '—';
    if (typeof e === 'string') return e;
    var linha1 = [e.logradouro, e.numero].filter(Boolean).join(', ') + (e.complemento ? ' - ' + e.complemento : '');
    var cidade = [e.cidade, e.uf].filter(Boolean).join('/');
    var partes = [linha1, e.bairro, cidade, e.cep ? 'CEP ' + cep(e.cep) : ''].filter(function (p) { return p && String(p).trim(); });
    return partes.length ? partes.join(' · ') : '—';
  }

  function renderFicha(f) {
    var c = f.cliente || {};
    var cabecalho = '<div class="ficha-cabecalho">' +
      '<div class="ficha-identidade">' +
        '<div class="ficha-avatar" aria-hidden="true">' + esc(iniciais(c.nome)) + '</div>' +
        '<div><h1 class="ficha-nome" id="titulo-ficha" tabindex="-1">' + esc(ou(c.nome, 'Cliente')) + '</h1>' +
        '<div class="ficha-meta">' + selo(c.status) +
          '<span>ID <code>' + esc(c.id) + '</code></span>' +
          '<span>Cliente desde ' + esc(data(c.criado_em)) + '</span></div></div>' +
      '</div>' +
      '<div class="ficha-acoes">' +
        '<button type="button" class="botao botao-destaque" data-acao="perguntar-cliente">Perguntar ao assistente sobre este cliente</button>' +
      '</div></div>';

    var usina = c.usina ? esc(c.usina.nome) + (c.usina.localizacao ? ' <span class="texto-suave">(' + esc(c.usina.localizacao) + ')</span>' : '') : '—';
    var dados = '<dl class="dados">' +
      itemDado('E-mail', esc(ou(c.email))) +
      itemDado('CPF', esc(cpf(c.cpf))) +
      itemDado('Telefone', esc(telefone(c.telefone))) +
      itemDado('Tipo', esc(rotulo(c.tipo))) +
      itemDado('Endereço', esc(formatarEndereco(c.endereco))) +
      itemDado('Distribuidora', esc(ou(c.distribuidora))) +
      itemDado('Nº da instalação', esc(ou(c.numero_instalacao))) +
      itemDado('Usina', usina) +
      itemDado('Código de indicação', c.codigo_indicacao ? '<code>' + esc(c.codigo_indicacao) + '</code>' : '—') +
      itemDado('Acesso ao app', esc(simNao(c.app_acesso_habilitado))) +
      itemDado('Último login no app', esc(c.ultimo_login_app ? dataHora(c.ultimo_login_app) : 'Nunca acessou')) +
      itemDado('Atualizado em', esc(dataHora(c.atualizado_em))) +
      '</dl>';

    return cabecalho +
      '<div class="grade grade-2">' +
        cartao('f-dados', 'Dados cadastrais', dados) +
        cartao('f-ativacao', 'Jornada de ativação', renderAtivacao(f.ativacao, c), '5 etapas · até 90 dias') +
      '</div>' +
      '<div class="grade grade-2">' +
        cartao('f-economia', 'Economia', renderEconomia(f.economia)) +
        cartao('f-indicacoes', 'Indique e Ganhe', renderIndicacoes(f.indicacoes), 'R$ 50 por indicação') +
      '</div>' +
      cartao('f-faturas', 'Faturas', renderFaturas(f.faturas), 'últimos 12 meses') +
      '<div class="grade grade-2">' +
        cartao('f-clube', 'Clube Bulbe', renderClube(f.clube)) +
        cartao('f-cupons', 'Cupons', renderCupons(f.cupons)) +
      '</div>' +
      '<div class="grade grade-2">' +
        cartao('f-notificacoes', 'Notificações', renderNotificacoes(f.notificacoes)) +
        cartao('f-atendimentos', 'Atendimentos', renderAtendimentosCliente(f.atendimentos)) +
      '</div>';
  }

  function renderAtivacao(a, cliente) {
    if (!a) {
      return cliente && cliente.status === 'ativo'
        ? '<div class="aviso aviso-info">Cliente ativo: a energia já foi liberada e a jornada de ativação está concluída.</div>'
        : htmlVazio('Nenhuma jornada de ativação registrada para este cliente.');
    }
    var total = Number(a.total_etapas) || 5;
    var atual = Math.max(1, Math.min(total, Number(a.etapa_atual) || 1));
    var pct = ehNumero(a.percentual_concluido) ? Number(a.percentual_concluido) : 0;
    var etapas = Array.isArray(a.etapas) && a.etapas.length ? a.etapas : NOMES_ETAPAS.map(function (nome, i) {
      var n = i + 1;
      return { numero: n, nome: nome, titulo: nome, situacao: n < atual ? 'concluida' : (n === atual ? 'atual' : 'pendente') };
    });
    var eventosPorEtapa = {};
    (Array.isArray(a.eventos) ? a.eventos : []).forEach(function (ev) {
      var chave = String(ev.etapa);
      (eventosPorEtapa[chave] = eventosPorEtapa[chave] || []).push(ev);
    });

    // Até onde a linha verde vai: última etapa concluída ou atual.
    var ultimaAlcancada = 1;
    etapas.forEach(function (e) {
      if (e.situacao === 'concluida' || e.situacao === 'atual') ultimaAlcancada = Math.max(ultimaAlcancada, Number(e.numero) || 1);
    });
    var larguraLinha = total > 1 ? 80 * (ultimaAlcancada - 1) / (total - 1) : 0;

    var status = '<div class="jornada-status">' +
      '<span class="jornada-etapa-selo">Etapa ' + esc(atual) + ' de ' + esc(total) + '</span>' +
      '<h4>' + esc(ou(a.titulo || a.nome_etapa, NOMES_ETAPAS[atual - 1])) + '</h4>' +
      (a.descricao ? '<p>' + esc(a.descricao) + '</p>' : '') +
      '<div class="jornada-progresso" role="progressbar" aria-label="Progresso da ativação" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + esc(pct) + '">' +
        '<div class="jornada-progresso-preenchido" data-largura="' + esc(pct) + '"></div></div>' +
      '<div class="jornada-numeros">' +
        '<span><strong>' + esc(numero(pct)) + '%</strong> concluído</span>' +
        '<span>Previsão: <strong>' + esc(data(a.previsao_conclusao)) + '</strong></span>' +
        '<span>' + esc(numero(a.dias_desde_cadastro)) + ' de ' + esc(ou(a.prazo_ativacao_dias, 90)) + ' dias</span>' +
      '</div></div>';

    var circulos = '<div class="jornada-trilha">' +
      '<span class="jornada-linha-fundo" aria-hidden="true"></span>' +
      '<span class="jornada-linha" aria-hidden="true" data-largura="' + larguraLinha.toFixed(1) + '"></span>' +
      '<ol class="jornada-circulos" aria-label="Etapas da ativação">' +
      etapas.map(function (e) {
        var sit = e.situacao || 'pendente';
        return '<li class="etapa-' + esc(sit) + '" aria-label="' + esc('Etapa ' + e.numero + ': ' + (e.nome || '') + ' (' + rotulo(sit) + ')') + '">' +
          '<span class="jornada-bolinha" aria-hidden="true">' + (sit === 'concluida' ? ICONE_CHECK : esc(e.numero)) + '</span>' +
          '<span class="jornada-rotulo" aria-hidden="true">' + esc(e.nome || NOMES_ETAPAS[(Number(e.numero) || 1) - 1]) + '</span></li>';
      }).join('') + '</ol></div>';

    var linhaTempo = '<ol class="linha-tempo">' + etapas.map(function (e) {
      var sit = e.situacao || 'pendente';
      var eventos = eventosPorEtapa[String(e.numero)] || [];
      return '<li class="etapa-' + esc(sit) + '">' +
        '<h4>' + esc(e.titulo || e.nome) + '</h4>' +
        '<small>' + esc(sit === 'pendente' ? 'Aguardando' : rotulo(sit)) + '</small>' +
        eventos.map(function (ev) {
          return '<small>' + esc(dataHora(ev.ocorrido_em)) + ' — ' + esc(ou(ev.observacao, '')) + '</small>';
        }).join('') +
        '</li>';
    }).join('') + '</ol>';

    return '<div class="jornada">' + status + circulos + linhaTempo + '</div>';
  }

  function destaque(rotuloTexto, valor, tom) {
    return '<div class="destaque' + (tom ? ' destaque-' + tom : '') + '"><span>' + esc(rotuloTexto) + '</span><strong>' + esc(valor) + '</strong></div>';
  }

  function renderEconomia(e) {
    if (!e) return htmlVazio('Sem dados de economia.');
    return '<div class="destaques">' +
      destaque('Economia total', moeda(e.economia_total), 'verde') +
      destaque('Desconto acumulado', moeda(e.economia_total_desconto)) +
      destaque('Bônus de indicação', moeda(e.bonus_indicacao_total)) +
      destaque('Meses faturados', numero(e.meses_faturados)) +
      destaque('Faturas vencidas', numero(e.faturas_vencidas), Number(e.faturas_vencidas) > 0 ? 'amarelo' : '') +
      destaque('Valor em aberto', moeda(e.valor_em_aberto), Number(e.valor_em_aberto) > 0 ? 'amarelo' : '') +
      '</div>';
  }

  function renderFaturas(faturas) {
    if (!Array.isArray(faturas) || !faturas.length) return htmlVazio('Nenhuma fatura emitida ainda.');
    var linhas = faturas.map(function (f) {
      return '<tr>' +
        '<td class="col-nowrap">' + esc(mesReferencia(f.mes_referencia)) + '</td>' +
        '<td class="col-numero">' + esc(numero(f.consumo_kwh)) + '</td>' +
        '<td class="col-numero">' + esc(moeda(f.valor_sem_bulbe)) + '</td>' +
        '<td class="col-numero">' + esc(moeda(f.desconto)) + '</td>' +
        '<td class="col-numero">' + esc(moeda(f.bonus_indicacao)) + '</td>' +
        '<td class="col-numero"><strong>' + esc(moeda(f.valor_total)) + '</strong></td>' +
        '<td class="col-nowrap">' + esc(data(f.vencimento)) + '</td>' +
        '<td>' + selo(f.situacao) + '</td>' +
        '<td class="col-nowrap">' + esc(f.pago_em ? data(f.pago_em) : '—') + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Faturas do cliente</caption>' +
      '<thead><tr><th scope="col">Mês</th><th scope="col" class="col-numero">Consumo (kWh)</th>' +
      '<th scope="col" class="col-numero">Sem Bulbe</th><th scope="col" class="col-numero">Desconto</th>' +
      '<th scope="col" class="col-numero">Bônus</th><th scope="col" class="col-numero">Total</th>' +
      '<th scope="col">Vencimento</th><th scope="col">Situação</th><th scope="col">Pago em</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  function renderIndicacoes(ind) {
    if (!ind) return htmlVazio('Sem dados de indicação.');
    var lista = Array.isArray(ind.data) ? ind.data : [];
    var html = '<div class="destaques">' +
      destaque('Código', ou(ind.codigo_indicacao)) +
      destaque('Indicações', numero(ind.total)) +
      destaque('Bônus acumulado', moeda(ind.bonus_acumulado), 'verde') +
      '</div>';
    if (!lista.length) return html + htmlVazio('Nenhuma indicação feita ainda.');
    return html + '<ul class="lista-itens">' + lista.map(function (i) {
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(ou(i.nome_indicado)) + '</span>' + selo(i.situacao) + '</div>' +
        '<span class="texto-suave">' + esc(rotulo(i.canal)) +
        (i.contato_indicado ? ' · ' + esc(i.contato_indicado) : '') +
        ' · indicado em ' + esc(data(i.criado_em)) +
        (i.creditado_em ? ' · ' + esc(moeda(i.bonus)) + ' creditado em ' + esc(data(i.creditado_em)) : '') +
        '</span></li>';
    }).join('') + '</ul>';
  }

  function renderClube(clube) {
    if (!clube) return htmlVazio('O cliente ainda não participa do Clube Bulbe.');
    var meta = Number(clube.meta_sequencia) || 5;
    var feitas = Math.max(0, Math.min(meta, Number(clube.semanas_sequencia) || 0));
    var bolinhas = '';
    for (var s = 1; s <= meta; s++) {
      bolinhas += '<li class="' + (s <= feitas ? 'feita' : '') + '">' + s + '</li>';
    }
    var cartas = Array.isArray(clube.cartas_recentes) ? clube.cartas_recentes : [];
    return '<p class="texto-suave">Sequência semanal: <strong>' + esc(feitas) + ' de ' + esc(meta) + '</strong> semanas</p>' +
      '<ol class="sequencia" aria-label="' + esc(feitas + ' de ' + meta + ' semanas seguidas') + '">' + bolinhas + '</ol>' +
      '<div class="destaques">' +
        destaque('Próxima carta', data(clube.proxima_carta_em)) +
        destaque('Bônus especial (R$ 50)', clube.bonus_especial_pendente ? 'Pendente' : 'Não', clube.bonus_especial_pendente ? 'amarelo' : '') +
      '</div>' +
      (cartas.length ? '<ul class="lista-itens">' + cartas.map(function (c) {
        return '<li><div class="lista-item-topo"><span class="lista-item-titulo">Semana ' + esc(ou(c.semana)) + ' · carta ' + esc(rotulo(c.tipo).toLowerCase()) + '</span>' + selo(c.situacao) + '</div>' +
          '<span class="texto-suave">Disponível em ' + esc(data(c.disponivel_em)) +
          (c.aberta_em ? ' · aberta em ' + esc(dataHora(c.aberta_em)) : '') + '</span></li>';
      }).join('') + '</ul>' : htmlVazio('Nenhuma carta recente.'));
  }

  function renderCupons(cupons) {
    if (!Array.isArray(cupons) || !cupons.length) return htmlVazio('Nenhum cupom liberado.');
    return '<ul class="lista-itens">' + cupons.map(function (c) {
      var parceiro = c.parceiro || {};
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(ou(c.titulo)) + '</span>' + selo(c.situacao) + '</div>' +
        (c.descricao ? '<span>' + esc(c.descricao) + '</span>' : '') +
        '<span class="texto-suave">' + esc(ou(parceiro.nome)) + (parceiro.categoria ? ' · ' + esc(parceiro.categoria) : '') +
        (c.codigo ? ' · código <code>' + esc(c.codigo) + '</code>' : '') +
        (c.valido_ate ? ' · válido até ' + esc(data(c.valido_ate)) : '') +
        (c.usado_em ? ' · usado em ' + esc(data(c.usado_em)) : '') + '</span></li>';
    }).join('') + '</ul>';
  }

  function renderNotificacoes(lista) {
    if (!Array.isArray(lista) || !lista.length) return htmlVazio('Nenhuma notificação enviada.');
    return '<ul class="lista-itens">' + lista.map(function (n) {
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(ou(n.titulo)) + '</span>' +
        '<span class="selo selo-neutro">' + esc(rotulo(n.tipo)) + '</span></div>' +
        (n.mensagem ? '<span>' + esc(n.mensagem) + '</span>' : '') +
        '<span class="texto-suave">' + esc(rotulo(n.canal)) + ' · ' + esc(dataHora(n.enviada_em)) + ' · ' + (n.lida ? 'lida' : 'não lida') + '</span></li>';
    }).join('') + '</ul>';
  }

  function renderAtendimentosCliente(lista) {
    if (!Array.isArray(lista) || !lista.length) return htmlVazio('Nenhum atendimento registrado.');
    return '<ul class="lista-itens">' + lista.map(function (a) {
      return '<li><div class="lista-item-topo"><span class="lista-item-titulo">' + esc(ou(a.assunto)) + '</span>' + selo(a.status) + '</div>' +
        (a.descricao ? '<span>' + esc(a.descricao) + '</span>' : '') +
        '<span class="texto-suave">' + esc(rotulo(a.canal)) + ' · aberto em ' + esc(dataHora(a.criado_em)) +
        (a.resolvido_em ? ' · resolvido em ' + esc(dataHora(a.resolvido_em)) : '') + '</span></li>';
    }).join('') + '</ul>';
  }

  /* ------------------------------------------------------------
     ADESÕES
     ------------------------------------------------------------ */
  async function carregarAdesoes() {
    var alvo = $('adesoes-resultado');
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando('Carregando adesões...');
    var query = montarQuery({ situacao: $('filtro-adesao-situacao').value, limite: $('filtro-adesao-limite').value });
    try {
      var lista = await api('/v1/painel/adesoes' + query);
      estado.adesoesCarregadas = true;
      alvo.innerHTML = renderTabelaAdesoes(Array.isArray(lista) ? lista : []);
    } catch (erro) {
      if (erro.status !== 401) alvo.innerHTML = htmlErro(erro);
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  function renderTabelaAdesoes(lista) {
    if (!lista.length) return htmlVazio('Nenhuma adesão encontrada.');
    var linhas = lista.map(function (a) {
      var clienteLink = a.cliente_id
        ? '<a class="link-linha" href="' + esc(hashCliente(a.cliente_id)) + '">Ver ficha</a>'
        : '<span class="texto-suave">—</span>';
      return '<tr>' +
        '<td><strong>' + esc(ou(a.nome)) + '</strong><br><span class="texto-suave">' + esc(ou(a.email)) + '</span></td>' +
        '<td class="col-nowrap">' + esc(telefone(a.telefone)) + '</td>' +
        '<td>' + esc(ou(a.cidade)) + (a.uf ? '/' + esc(a.uf) : '') + '</td>' +
        '<td class="col-numero">' + esc(moeda(a.valor_conta_atual)) + '</td>' +
        '<td class="col-numero">' + esc(moeda(a.economia_mensal_estimada)) + '</td>' +
        '<td>' + esc(rotulo(a.origem)) + '</td>' +
        '<td>' + selo(a.situacao) + '</td>' +
        '<td class="col-nowrap">' + esc(data(a.criado_em)) + '</td>' +
        '<td>' + clienteLink + '</td>' +
        '</tr>';
    }).join('');
    return '<p class="tabela-resumo">' + esc(lista.length) + ' adesão(ões).</p>' +
      '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Adesões</caption>' +
      '<thead><tr><th scope="col">Nome</th><th scope="col">Telefone</th><th scope="col">Cidade</th>' +
      '<th scope="col" class="col-numero">Conta atual</th><th scope="col" class="col-numero">Economia/mês</th>' +
      '<th scope="col">Origem</th><th scope="col">Situação</th><th scope="col">Criada em</th><th scope="col">Cliente</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     ATENDIMENTOS
     ------------------------------------------------------------ */
  async function carregarAtendimentos() {
    var alvo = $('atendimentos-resultado');
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando('Carregando atendimentos...');
    var query = montarQuery({ status: $('filtro-atendimento-status').value, limite: $('filtro-atendimento-limite').value });
    try {
      var lista = await api('/v1/painel/atendimentos' + query);
      estado.atendimentosCarregados = true;
      alvo.innerHTML = renderTabelaAtendimentos(Array.isArray(lista) ? lista : []);
    } catch (erro) {
      if (erro.status !== 401) alvo.innerHTML = htmlErro(erro);
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  function renderTabelaAtendimentos(lista) {
    if (!lista.length) return htmlVazio('Nenhum atendimento encontrado.');
    var linhas = lista.map(function (a) {
      var nomeCliente = a.cliente_nome || a.nome_cliente || (a.cliente && a.cliente.nome) || 'Ver ficha';
      var cliente = a.cliente_id
        ? '<a class="link-linha" href="' + esc(hashCliente(a.cliente_id)) + '">' + esc(nomeCliente) + '</a>'
        : '—';
      var classe = a.cliente_id ? ' class="linha-clicavel" data-href="' + esc(hashCliente(a.cliente_id)) + '"' : '';
      return '<tr' + classe + '>' +
        '<td class="col-nowrap">' + esc(dataHora(a.criado_em)) + '</td>' +
        '<td>' + cliente + '</td>' +
        '<td>' + esc(rotulo(a.canal)) + '</td>' +
        '<td><strong>' + esc(ou(a.assunto)) + '</strong>' + (a.descricao ? '<br><span class="texto-suave">' + esc(a.descricao) + '</span>' : '') + '</td>' +
        '<td>' + selo(a.status) + '</td>' +
        '<td class="col-nowrap">' + esc(a.resolvido_em ? dataHora(a.resolvido_em) : '—') + '</td>' +
        '</tr>';
    }).join('');
    return '<p class="tabela-resumo">' + esc(lista.length) + ' atendimento(s).</p>' +
      '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Atendimentos</caption>' +
      '<thead><tr><th scope="col">Aberto em</th><th scope="col">Cliente</th><th scope="col">Canal</th>' +
      '<th scope="col">Assunto</th><th scope="col">Status</th><th scope="col">Resolvido em</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     CHAT COM O ASSISTENTE
     ------------------------------------------------------------ */
  var mediaTelaMenor = window.matchMedia('(max-width: 1200px)');

  /** Converte a resposta em HTML seguro: escapa tudo e só então aplica **negrito**, listas "- " e quebras de linha. */
  function formatarResposta(texto) {
    function inline(t) {
      return esc(t).replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>');
    }
    var linhas = String(texto || '').replace(/\r\n?/g, '\n').split('\n');
    var html = '';
    var paragrafo = [];
    var emLista = false;
    function fecharParagrafo() {
      if (paragrafo.length) { html += '<p>' + paragrafo.join('<br>') + '</p>'; paragrafo = []; }
    }
    function fecharLista() {
      if (emLista) { html += '</ul>'; emLista = false; }
    }
    linhas.forEach(function (bruta) {
      var linha = bruta.replace(/\s+$/, '');
      var item = /^\s*[-•]\s+(.*)$/.exec(linha);
      if (item) {
        fecharParagrafo();
        if (!emLista) { html += '<ul>'; emLista = true; }
        html += '<li>' + inline(item[1]) + '</li>';
        return;
      }
      if (!linha.trim()) { fecharParagrafo(); fecharLista(); return; }
      fecharLista();
      paragrafo.push(inline(linha));
    });
    fecharParagrafo();
    fecharLista();
    return html || '<p>(resposta vazia)</p>';
  }

  function rolarChatParaFim() {
    var caixa = $('chat-mensagens');
    caixa.scrollTop = caixa.scrollHeight;
  }

  function adicionarMensagem(papel, texto, ferramentas, modelo) {
    var caixa = $('chat-mensagens');
    var msg = document.createElement('div');
    msg.className = 'msg msg-' + papel;

    var balao = document.createElement('div');
    balao.className = 'msg-balao';
    if (papel === 'assistente') {
      balao.innerHTML = formatarResposta(texto); // formatarResposta escapa o conteúdo
    } else {
      balao.textContent = texto;
    }
    var rotuloLeitor = document.createElement('span');
    rotuloLeitor.className = 'visualmente-oculto';
    rotuloLeitor.textContent = papel === 'assistente' ? 'Assistente: ' : 'Você: ';
    msg.appendChild(rotuloLeitor);
    msg.appendChild(balao);

    if (papel === 'assistente' && Array.isArray(ferramentas) && ferramentas.length) {
      var rodape = document.createElement('div');
      rodape.className = 'msg-ferramentas';
      var legenda = document.createElement('span');
      legenda.textContent = 'Consultou:';
      rodape.appendChild(legenda);
      ferramentas.forEach(function (nome) {
        var code = document.createElement('code');
        code.textContent = String(nome);
        rodape.appendChild(code);
      });
      if (modelo) rodape.title = 'Modelo: ' + modelo;
      msg.appendChild(rodape);
    }
    caixa.appendChild(msg);
    rolarChatParaFim();
  }

  function adicionarAvisoChat(texto, tipo) {
    var caixa = $('chat-mensagens');
    var msg = document.createElement('div');
    msg.className = 'msg msg-sistema';
    var aviso = document.createElement('div');
    aviso.className = 'aviso aviso-' + (tipo || 'erro');
    aviso.setAttribute('role', 'alert');
    aviso.textContent = texto;
    msg.appendChild(aviso);
    caixa.appendChild(msg);
    rolarChatParaFim();
  }

  function atualizarContador() {
    var entrada = $('chat-entrada');
    $('chat-contador').textContent = entrada.value.length + '/' + MAX_MENSAGEM;
    entrada.style.height = 'auto';
    entrada.style.height = Math.min(entrada.scrollHeight + 2, 180) + 'px';
  }

  function mostrarSugestoes(mostrar) {
    var caixa = $('chat-sugestoes');
    caixa.hidden = !mostrar || !caixa.children.length;
  }

  async function carregarSugestoes() {
    try {
      var r = await api('/v1/painel/chat/sugestoes');
      var lista = r && Array.isArray(r.sugestoes) ? r.sugestoes : [];
      var caixa = $('chat-sugestoes');
      caixa.innerHTML = '';
      lista.slice(0, 8).forEach(function (texto) {
        var chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip';
        chip.textContent = String(texto);
        chip.addEventListener('click', function () { enviarPergunta(String(texto)); });
        caixa.appendChild(chip);
      });
      mostrarSugestoes(estado.chat.historico.length === 0);
    } catch (e) {
      $('chat-sugestoes').hidden = true; // sem sugestões, o chat continua funcionando
    }
  }

  function definirEnviando(enviando) {
    estado.chat.enviando = enviando;
    $('chat-digitando').hidden = !enviando;
    $('chat-enviar').disabled = enviando;
    $('chat-mensagens').setAttribute('aria-busy', enviando ? 'true' : 'false');
    $('chat-sugestoes').querySelectorAll('button').forEach(function (b) { b.disabled = enviando; });
    if (enviando) rolarChatParaFim();
  }

  async function enviarPergunta(textoBruto) {
    var texto = String(textoBruto || '').trim();
    if (!texto || estado.chat.enviando) return;
    if (texto.length > MAX_MENSAGEM) texto = texto.slice(0, MAX_MENSAGEM);

    var entrada = $('chat-entrada');
    var historicoEnviado = estado.chat.historico.slice(-MAX_HISTORICO);

    abrirChat(false);
    adicionarMensagem('funcionario', texto);
    entrada.value = '';
    atualizarContador();
    mostrarSugestoes(false);
    definirEnviando(true);

    try {
      var r = await api('/v1/painel/chat', {
        metodo: 'POST',
        corpo: { mensagem: texto, historico: historicoEnviado },
        tempoLimite: TEMPO_LIMITE_CHAT
      });
      var resposta = r && typeof r.resposta === 'string' ? r.resposta : '';
      adicionarMensagem('assistente', resposta, r && r.ferramentas_usadas, r && r.modelo);
      estado.chat.historico.push({ papel: 'funcionario', texto: texto });
      estado.chat.historico.push({ papel: 'assistente', texto: resposta });
      if (estado.chat.historico.length > MAX_HISTORICO) {
        estado.chat.historico = estado.chat.historico.slice(-MAX_HISTORICO);
      }
      if (r && r.modelo) $('chat-modelo').textContent = 'Modelo: ' + r.modelo + ' · somente leitura';
    } catch (erro) {
      if (erro.status === 401) return;
      if (erro.status === 503 || erro.code === 'CHATBOT_INDISPONIVEL') {
        adicionarAvisoChat('O assistente está indisponível: a chave da IA não foi configurada. ' +
          'Peça ao responsável técnico para configurar ANTHROPIC_API_KEY no servidor e reiniciar a API.', 'alerta');
      } else if (erro.status === 429) {
        adicionarAvisoChat('Muitas perguntas em sequência. Aguarde alguns segundos e tente de novo.', 'alerta');
      } else {
        adicionarAvisoChat('Não foi possível obter a resposta: ' + (erro.message || 'erro inesperado') + '.');
      }
      if (!entrada.value) { entrada.value = texto; atualizarContador(); } // devolve a pergunta para reenviar
    } finally {
      definirEnviando(false);
      if (!mediaTelaMenor.matches || estado.chat.aberto) entrada.focus();
    }
  }

  function limparConversa() {
    if (estado.chat.enviando) return;
    estado.chat.historico = [];
    var caixa = $('chat-mensagens');
    caixa.querySelectorAll('.msg').forEach(function (m) { m.remove(); });
    mostrarSugestoes(true);
    $('chat-entrada').focus();
  }

  function aplicarEstadoChat() {
    var aberto = estado.chat.aberto;
    $('layout').classList.toggle('chat-recolhido', !aberto);
    $('botao-chat-abrir').hidden = aberto;
    $('botao-chat-alternar').setAttribute('aria-expanded', aberto ? 'true' : 'false');
    $('botao-chat-alternar').textContent = aberto ? 'Recolher assistente' : 'Assistente';
  }

  function abrirChat(focar) {
    estado.chat.aberto = true;
    aplicarEstadoChat();
    if (!mediaTelaMenor.matches) gravarPreferencia(CHAVE_CHAT_ABERTO, '1');
    if (focar !== false) $('chat-entrada').focus();
  }

  function fecharChat() {
    estado.chat.aberto = false;
    aplicarEstadoChat();
    if (!mediaTelaMenor.matches) gravarPreferencia(CHAVE_CHAT_ABERTO, '0');
    $('botao-chat-abrir').focus();
  }

  function perguntarSobreCliente() {
    var c = estado.fichaAtual;
    if (!c) return;
    abrirChat(false);
    var entrada = $('chat-entrada');
    entrada.value = 'Faça um resumo do cliente ' + (c.nome || '') + ' (id ' + c.id + '): situação da ativação, ' +
      'faturas em aberto ou vencidas, indicações, Clube Bulbe e atendimentos recentes.';
    atualizarContador();
    entrada.focus();
    entrada.setSelectionRange(entrada.value.length, entrada.value.length);
  }

  /* ------------------------------------------------------------
     INICIALIZAÇÃO
     ------------------------------------------------------------ */
  function mostrarFuncionario(f) {
    var alvo = $('funcionario-info');
    if (!f || !f.nome) { alvo.textContent = ''; return; }
    alvo.innerHTML = '<strong>' + esc(f.nome) + '</strong>' + esc(rotulo(f.perfil));
  }

  function ligarEventos() {
    $('botao-sair').addEventListener('click', function () { sair('encerrada'); });
    $('botao-atualizar-metricas').addEventListener('click', carregarVisaoGeral);

    $('form-clientes').addEventListener('submit', function (e) { e.preventDefault(); carregarClientes(); });
    $('form-clientes').addEventListener('reset', function () { window.setTimeout(carregarClientes, 0); });
    $('form-adesoes').addEventListener('submit', function (e) { e.preventDefault(); carregarAdesoes(); });
    $('filtro-adesao-situacao').addEventListener('change', carregarAdesoes);
    $('form-atendimentos').addEventListener('submit', function (e) { e.preventDefault(); carregarAtendimentos(); });
    $('filtro-atendimento-status').addEventListener('change', carregarAtendimentos);
    $('filtro-status').addEventListener('change', carregarClientes);

    // Linhas clicáveis (o link dentro da linha continua sendo o caminho acessível por teclado).
    $('conteudo').addEventListener('click', function (e) {
      var acao = e.target.closest('[data-acao="perguntar-cliente"]');
      if (acao) { perguntarSobreCliente(); return; }
      if (e.target.closest('a, button, input, select, textarea')) return;
      var linha = e.target.closest('tr.linha-clicavel[data-href]');
      if (linha) window.location.hash = linha.getAttribute('data-href');
    });

    // Chat
    $('chat-form').addEventListener('submit', function (e) {
      e.preventDefault();
      enviarPergunta($('chat-entrada').value);
    });
    $('chat-entrada').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        enviarPergunta($('chat-entrada').value);
      }
    });
    $('chat-entrada').addEventListener('input', atualizarContador);
    $('botao-chat-limpar').addEventListener('click', limparConversa);
    $('botao-chat-fechar').addEventListener('click', fecharChat);
    $('botao-chat-abrir').addEventListener('click', function () { abrirChat(true); });
    $('botao-chat-alternar').addEventListener('click', function () {
      if (estado.chat.aberto) fecharChat(); else abrirChat(true);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && estado.chat.aberto && mediaTelaMenor.matches) fecharChat();
    });
    var aoMudarTela = function () {
      // Em telas menores o chat é uma gaveta: começa recolhido para não cobrir o conteúdo.
      estado.chat.aberto = mediaTelaMenor.matches ? false : lerPreferencia(CHAVE_CHAT_ABERTO) !== '0';
      aplicarEstadoChat();
    };
    if (mediaTelaMenor.addEventListener) mediaTelaMenor.addEventListener('change', aoMudarTela);
    else if (mediaTelaMenor.addListener) mediaTelaMenor.addListener(aoMudarTela);
    aoMudarTela();

    window.addEventListener('hashchange', navegar);
  }

  async function iniciar() {
    if (!lerSessao(CHAVE_TOKEN)) {
      window.location.replace('/painel/index.html');
      return;
    }
    try {
      var salvo = JSON.parse(lerSessao(CHAVE_FUNCIONARIO) || 'null');
      if (salvo) mostrarFuncionario(salvo);
    } catch (e) { /* ignora */ }

    ligarEventos();
    atualizarContador();
    navegar();

    try {
      estado.funcionario = await api('/v1/painel/me');
      mostrarFuncionario(estado.funcionario);
    } catch (e) {
      /* 401 já redireciona; outros erros aparecem nas telas */
    }
    carregarSugestoes();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
