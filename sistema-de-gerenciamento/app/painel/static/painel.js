/* ============================================================
   PAINEL DE GESTÃO BULBE — aplicação de uma página
   - Autenticação: token Bearer guardado no sessionStorage (401 -> volta ao login).
   - Rotas por hash: #/visao-geral, #/clientes, #/cliente/<id>, #/adesoes, #/atendimentos,
     #/ativacoes, #/dicas, #/usinas, #/parceiros e, só para admin, #/auditoria e #/uso-assistente.
   - Listas paginadas no servidor ({data, pagina, por_pagina, total, total_paginas}).
   - Chat lateral com streaming (POST /v1/painel/chat/stream lido com fetch + ReadableStream,
     eventos SSE inicio/texto/ferramenta/fim/erro), conversas guardadas no servidor
     (conversa_id) e fallback para POST /v1/painel/chat se o stream falhar antes de começar.
   SEGURANÇA: todo dado vindo da API passa por esc() (ou textContent) antes de entrar no HTML.
   ============================================================ */
(function () {
  'use strict';

  /* ------------------------------------------------------------
     CONSTANTES
     ------------------------------------------------------------ */
  var CHAVE_TOKEN = 'bulbe_painel_token';
  var CHAVE_FUNCIONARIO = 'bulbe_painel_funcionario';
  var CHAVE_CHAT_ABERTO = 'bulbe_painel_chat_aberto';
  var CHAVE_CONVERSA = 'bulbe_painel_conversa_id';
  var MAX_HISTORICO = 20;
  var MAX_MENSAGEM = 2000;
  var TEMPO_LIMITE_PADRAO = 30000;
  var TEMPO_LIMITE_CHAT = 120000;
  var TEMPO_INATIVIDADE_STREAM = 90000;
  var ROTAS_ADMIN = ['auditoria', 'uso-assistente'];

  var ACOES_AUDITORIA = {
    login_ok: 'Login com sucesso', login_falha: 'Login com falha', login_bloqueado: 'Login bloqueado',
    alerta_email: 'Alerta por e-mail', ver_ficha: 'Abriu ficha', ver_auditoria: 'Consultou auditoria', expurgo: 'Expurgo'
  };
  var TONS_AUDITORIA = {
    login_ok: 'ok', login_falha: 'alerta', login_bloqueado: 'erro', alerta_email: 'erro',
    ver_ficha: 'info', ver_auditoria: 'neutro', expurgo: 'neutro'
  };

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
    carregadas: {},          // telas já carregadas uma vez (não recarrega ao voltar pelo menu)
    paginas: {},             // página atual de cada lista paginada
    seqFicha: 0,
    fichaAtual: null,
    chat: { historico: [], enviando: false, aberto: true, conversaId: null, conversasAbertas: false }
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
  var formatoDecimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });

  function moeda(v) { return ehNumero(v) ? formatoMoeda.format(Number(v)) : '—'; }
  function numero(v) { return ehNumero(v) ? formatoNumero.format(Number(v)) : '—'; }
  function decimal(v) { return ehNumero(v) ? formatoDecimal.format(Number(v)) : '—'; }
  /** Custo em dólar: valores pequenos (frações de centavo) ganham mais casas decimais. */
  function dolar(v) {
    if (!ehNumero(v)) return '—';
    var n = Number(v);
    var casas = n !== 0 && Math.abs(n) < 0.01 ? 4 : 2;
    return 'US$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }
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
  function gravarSessao(chave, valor) { try { sessionStorage.setItem(chave, valor); } catch (e) { /* ignora */ } }
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
    removerSessao(CHAVE_CONVERSA);
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
    'atendimentos': 'Atendimentos',
    'ativacoes': 'Ativações',
    'dicas': 'Dicas',
    'usinas': 'Usinas',
    'parceiros': 'Parceiros',
    'auditoria': 'Auditoria',
    'uso-assistente': 'Uso do assistente'
  };

  /** Tela -> {titulo (id do h1), carregar, sempre (recarrega toda vez que a tela é aberta)}. */
  var TELAS = {
    'visao-geral': { titulo: 'titulo-visao-geral', carregar: function () { carregarVisaoGeral(); }, sempre: true },
    'clientes': { titulo: 'titulo-clientes', carregar: function () { carregarLista('clientes'); } },
    'adesoes': { titulo: 'titulo-adesoes', carregar: function () { carregarLista('adesoes'); } },
    'atendimentos': { titulo: 'titulo-atendimentos', carregar: function () { carregarLista('atendimentos'); } },
    'ativacoes': { titulo: 'titulo-ativacoes', carregar: function () { carregarResumoAtivacoes(); carregarParados(); } },
    'dicas': { titulo: 'titulo-dicas', carregar: function () { carregarDicas(); } },
    'usinas': { titulo: 'titulo-usinas', carregar: function () { carregarUsinas(); } },
    'parceiros': { titulo: 'titulo-parceiros', carregar: function () { carregarParceiros(); } },
    'auditoria': { titulo: 'titulo-auditoria', carregar: function () { carregarLista('auditoria'); }, sempre: true },
    'uso-assistente': { titulo: 'titulo-uso-assistente', carregar: function () { carregarUsoAssistente(); }, sempre: true }
  };

  function ehAdmin() {
    return !!(estado.funcionario && estado.funcionario.perfil === 'admin');
  }

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

    if (rota.tela === 'ficha') {
      carregarFicha(rota.id);
      return;
    }
    var tela = TELAS[rota.tela];
    if (ROTAS_ADMIN.indexOf(rota.tela) !== -1 && estado.funcionario && !ehAdmin()) {
      // A API também recusa (403); aqui só evitamos a chamada e explicamos.
      var alvo = $(rota.tela === 'auditoria' ? 'auditoria-resultado' : 'uso-resultado');
      alvo.innerHTML = '<div class="aviso aviso-alerta" role="alert">Esta tela é restrita a administradores.</div>';
    } else if (tela.sempre || !estado.carregadas[rota.tela]) {
      estado.carregadas[rota.tela] = true;
      tela.carregar();
    }
    focarTitulo(tela.titulo);
  }

  /** Mostra os itens de gestão do menu só para o perfil admin. */
  function aplicarPerfilNoMenu() {
    var admin = ehAdmin();
    $('menu-admin').hidden = !admin;
    $('menu-secao-admin').hidden = !admin;
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
        'clientes em sequência · ' + numero(clube.cupons_ativos) + ' cupons ativos · ' + numero(clube.cupons_usados) + ' usados' +
        (ehNumero(clube.bonus_pagos) ? ' · ' + moeda(clube.bonus_pagos) + ' em bônus pagos' : ''), 'amarela') +
      cartaoMetrica('Adesões aguardando', numero(ades.enviada),
        numero(ades.aprovada) + ' aprovadas · ' + numero(ades.recusada) + ' recusadas · ' + numero(ades.rascunho) + ' rascunhos', 'amarela') +
      cartaoMetrica('Simulações (30 dias)', numero(m.simulacoes_30_dias), 'Simulador do app e do site') +
      cartaoMetrica('Acesso ao app', numero(app.clientes_com_acesso),
        numero(app.logins_ultimos_30_dias) + ' logins nos últimos 30 dias') +
      '</div>';

    // Na v2 a "etapa 5" da métrica são os clientes ATIVADOS nos últimos 30 dias (ativacao_etapa5_descricao).
    var itensEtapa = NOMES_ETAPAS.map(function (nome, i) {
      var n = i + 1;
      var valor = porEtapa[String(n)] !== undefined ? porEtapa[String(n)] : porEtapa[n];
      return {
        rotulo: n === 5 ? 'Ativados (30 dias)' : n + '. ' + nome,
        valor: valor || 0,
        tom: n === 5 ? 'verde' : (n >= 3 ? 'amarelo' : 'azul')
      };
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
        '<h2 class="cartao-titulo" id="t-ativacao-etapa">Ativação por etapa <span class="texto-suave">em ativação por etapa · ativados nos últimos 30 dias</span></h2>' +
        htmlBarras(itensEtapa) +
        '<p class="cartao-rodape"><a href="#/ativacoes">Ver resumo das ativações e clientes parados</a></p>' +
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
     LISTAS PAGINADAS (Clientes, Adesões, Atendimentos, Auditoria)
     ------------------------------------------------------------ */
  var LISTAS = {
    clientes: {
      alvo: 'clientes-resultado', url: '/v1/painel/clientes', carregando: 'Buscando clientes...',
      unidade: ['cliente', 'clientes'], dica: 'Clique na linha para abrir a ficha.',
      filtros: function () {
        return {
          termo: $('filtro-termo').value, status: $('filtro-status').value, cidade: $('filtro-cidade').value,
          etapa: $('filtro-etapa').value, por_pagina: $('filtro-limite').value
        };
      },
      render: function (lista) { return renderTabelaClientes(lista); }
    },
    adesoes: {
      alvo: 'adesoes-resultado', url: '/v1/painel/adesoes', carregando: 'Carregando adesões...',
      unidade: ['adesão', 'adesões'],
      filtros: function () {
        return { situacao: $('filtro-adesao-situacao').value, por_pagina: $('filtro-adesao-limite').value };
      },
      render: function (lista) { return renderTabelaAdesoes(lista); }
    },
    atendimentos: {
      alvo: 'atendimentos-resultado', url: '/v1/painel/atendimentos', carregando: 'Carregando atendimentos...',
      unidade: ['atendimento', 'atendimentos'],
      filtros: function () {
        return { status: $('filtro-atendimento-status').value, por_pagina: $('filtro-atendimento-limite').value };
      },
      render: function (lista) { return renderTabelaAtendimentos(lista); }
    },
    auditoria: {
      alvo: 'auditoria-resultado', url: '/v1/painel/auditoria', carregando: 'Carregando auditoria...',
      unidade: ['registro', 'registros'],
      filtros: function () {
        return {
          acao: $('filtro-auditoria-acao').value, funcionario_id: $('filtro-auditoria-funcionario').value,
          por_pagina: $('filtro-auditoria-limite').value
        };
      },
      render: function (lista) { return renderTabelaAuditoria(lista); }
    }
  };

  /** Aceita o formato paginado da v2 e, por compatibilidade, uma lista simples (v1). */
  function normalizarPagina(r) {
    if (Array.isArray(r)) return { data: r, pagina: 1, por_pagina: r.length, total: r.length, total_paginas: 1 };
    r = r || {};
    var dados = Array.isArray(r.data) ? r.data : [];
    var total = ehNumero(r.total) ? Number(r.total) : dados.length;
    var totalPaginas = ehNumero(r.total_paginas) ? Number(r.total_paginas) : 1;
    return {
      data: dados,
      pagina: Math.max(1, ehNumero(r.pagina) ? Number(r.pagina) : 1),
      por_pagina: ehNumero(r.por_pagina) ? Number(r.por_pagina) : dados.length,
      total: total,
      total_paginas: Math.max(totalPaginas, 1)
    };
  }

  function htmlPaginacao(nome, p) {
    var anterior = p.pagina > 1;
    var proxima = p.pagina < p.total_paginas;
    return '<nav class="paginacao" aria-label="' + esc('Paginação de ' + TITULOS[nome].toLowerCase()) + '">' +
      '<button type="button" class="botao botao-fantasma botao-pequeno" data-paginar="' + esc(nome) + '" data-pagina="' + esc(p.pagina - 1) + '"' +
        (anterior ? '' : ' disabled') + '>&larr; Anterior</button>' +
      '<span class="paginacao-info">Página <strong>' + esc(numero(p.pagina)) + '</strong> de <strong>' + esc(numero(p.total_paginas)) + '</strong></span>' +
      '<button type="button" class="botao botao-fantasma botao-pequeno" data-paginar="' + esc(nome) + '" data-pagina="' + esc(p.pagina + 1) + '"' +
        (proxima ? '' : ' disabled') + '>Próxima &rarr;</button>' +
      '</nav>';
  }

  /** Carrega uma lista paginada. pagina omitida = volta para a 1 (filtros novos). */
  async function carregarLista(nome, pagina, focarResumo) {
    var cfg = LISTAS[nome];
    var alvo = $(cfg.alvo);
    var paginaPedida = Math.max(1, Number(pagina) || 1);
    estado.paginas[nome] = paginaPedida;
    var seq = (cfg.seq = (cfg.seq || 0) + 1);
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando(cfg.carregando);
    var params = cfg.filtros();
    params.pagina = paginaPedida;
    try {
      var p = normalizarPagina(await api(cfg.url + montarQuery(params)));
      if (seq !== cfg.seq) return; // resposta de um pedido antigo
      // Página além do fim (ex.: filtro mudou o total): volta para a última existente.
      if (!p.data.length && p.total > 0 && paginaPedida > p.total_paginas) {
        carregarLista(nome, p.total_paginas, focarResumo);
        return;
      }
      if (!p.data.length) {
        alvo.innerHTML = htmlVazio('Nenhum registro encontrado com esses filtros.');
      } else {
        var inicio = (p.pagina - 1) * p.por_pagina + 1;
        var fim = inicio + p.data.length - 1;
        alvo.innerHTML = '<p class="tabela-resumo" id="resumo-' + esc(nome) + '" tabindex="-1">' +
          esc(numero(p.total) + ' ' + (p.total === 1 ? cfg.unidade[0] : cfg.unidade[1]) +
            ' · mostrando ' + numero(inicio) + '–' + numero(fim) + ' · página ' + numero(p.pagina) + ' de ' + numero(p.total_paginas) + '.') +
          (cfg.dica ? ' ' + esc(cfg.dica) : '') + '</p>' +
          cfg.render(p.data) +
          (p.total_paginas > 1 ? htmlPaginacao(nome, p) : '');
        if (focarResumo) {
          var resumo = $('resumo-' + nome);
          if (resumo) resumo.focus();
        }
      }
    } catch (erro) {
      if (seq !== cfg.seq) return;
      estado.carregadas[nome] = false; // tenta de novo ao voltar para a tela
      if (erro.status !== 401) {
        alvo.innerHTML = erro.status === 403
          ? '<div class="aviso aviso-alerta" role="alert">' + esc(erro.message || 'Acesso restrito a administradores.') + '</div>'
          : htmlErro(erro);
      }
    } finally {
      if (seq === cfg.seq) alvo.removeAttribute('aria-busy');
    }
  }

  /* ------------------------------------------------------------
     CLIENTES
     ------------------------------------------------------------ */
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
    return '<div class="tabela-rolagem"><table class="tabela">' +
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
      destaque('Bônus do Clube', moeda(ehNumero(e.bonus_clube_total) ? e.bonus_clube_total : 0)) +
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
        '<td class="col-numero">' + esc(moeda(ehNumero(f.bonus_clube) ? f.bonus_clube : 0)) + '</td>' +
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
      '<th scope="col" class="col-numero">Bônus indicação</th><th scope="col" class="col-numero">Bônus Clube</th>' +
      '<th scope="col" class="col-numero">Total</th>' +
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
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Adesões</caption>' +
      '<thead><tr><th scope="col">Nome</th><th scope="col">Telefone</th><th scope="col">Cidade</th>' +
      '<th scope="col" class="col-numero">Conta atual</th><th scope="col" class="col-numero">Economia/mês</th>' +
      '<th scope="col">Origem</th><th scope="col">Situação</th><th scope="col">Criada em</th><th scope="col">Cliente</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     ATENDIMENTOS
     ------------------------------------------------------------ */
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
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Atendimentos</caption>' +
      '<thead><tr><th scope="col">Aberto em</th><th scope="col">Cliente</th><th scope="col">Canal</th>' +
      '<th scope="col">Assunto</th><th scope="col">Status</th><th scope="col">Resolvido em</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     TELAS SIMPLES: carregamento com estado de "carregando" e erro
     ------------------------------------------------------------ */
  async function carregarEm(idAlvo, mensagem, buscar, renderizar, nomeTela) {
    var alvo = $(idAlvo);
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando(mensagem);
    try {
      var dados = await buscar();
      alvo.innerHTML = renderizar(dados);
      aplicarLarguras(alvo);
    } catch (erro) {
      if (nomeTela) estado.carregadas[nomeTela] = false;
      if (erro.status !== 401) {
        alvo.innerHTML = erro.status === 403
          ? '<div class="aviso aviso-alerta" role="alert">' + esc(erro.message || 'Acesso restrito a administradores.') + '</div>'
          : htmlErro(erro);
      }
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  /* ------------------------------------------------------------
     ATIVAÇÕES (resumo + clientes parados)
     ------------------------------------------------------------ */
  function carregarResumoAtivacoes() {
    return carregarEm('ativacoes-resumo', 'Carregando resumo das ativações...',
      function () { return api('/v1/painel/ativacoes/resumo'); }, renderResumoAtivacoes, 'ativacoes');
  }

  function valorPorChave(objeto, n) {
    if (!objeto) return undefined;
    return objeto[String(n)] !== undefined ? objeto[String(n)] : objeto[n];
  }

  function renderResumoAtivacoes(r) {
    r = r || {};
    var cartoes = '<div class="grade grade-metricas">' +
      cartaoMetrica('Em ativação', numero(r.em_ativacao), 'clientes na jornada de 5 etapas') +
      cartaoMetrica('Atrasados', numero(r.atrasados_90_dias), 'passaram dos 90 dias do cadastro', Number(r.atrasados_90_dias) > 0 ? 'vermelha' : '') +
      cartaoMetrica('Ativados (30 dias)', numero(r.ativados_30_dias), 'energia liberada nos últimos 30 dias', 'verde') +
      cartaoMetrica('Tempo médio de ativação', ehNumero(r.tempo_medio_ativacao_dias) ? decimal(r.tempo_medio_ativacao_dias) + ' dias' : '—',
        'do cadastro até a energia liberada', 'amarela') +
      '</div>';
    var etapas = [];
    for (var n = 1; n <= 5; n++) {
      var valor = valorPorChave(r.por_etapa, n);
      if (valor === undefined && n === 5) continue; // o resumo traz as etapas 1 a 4
      var dias = valorPorChave(r.dias_medios_na_etapa, n);
      etapas.push({
        rotulo: n + '. ' + NOMES_ETAPAS[n - 1],
        sub: ehNumero(dias) ? decimal(dias) + ' dias em média' : '',
        valor: valor || 0,
        tom: n >= 3 ? 'amarelo' : 'azul'
      });
    }
    return cartoes + '<section class="cartao" aria-labelledby="t-resumo-etapas">' +
      '<h2 class="cartao-titulo" id="t-resumo-etapas">Clientes por etapa <span class="texto-suave">com o tempo médio parado na etapa</span></h2>' +
      htmlBarras(etapas) + '</section>';
  }

  function carregarParados() {
    var dias = $('filtro-parados-dias').value;
    var query = montarQuery({
      etapa: $('filtro-parados-etapa').value,
      dias_minimos: ehNumero(dias) ? Math.max(0, Math.min(3650, Math.floor(Number(dias)))) : 30,
      limite: $('filtro-parados-limite').value
    });
    return carregarEm('parados-resultado', 'Buscando clientes parados...',
      function () { return api('/v1/painel/clientes/parados' + query); }, renderParados, 'ativacoes');
  }

  function renderParados(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return htmlVazio('Nenhum cliente parado com esses filtros.');
    var linhas = lista.map(function (c) {
      var href = hashCliente(c.cliente_id);
      var etapa = ehNumero(c.etapa_atual) ? c.etapa_atual + '. ' + ou(c.nome_etapa, NOMES_ETAPAS[Number(c.etapa_atual) - 1] || '') : '—';
      return '<tr class="linha-clicavel" data-href="' + esc(href) + '">' +
        '<td><a class="link-linha" href="' + esc(href) + '">' + esc(ou(c.nome)) + '</a></td>' +
        '<td>' + esc(ou(c.cidade)) + '</td>' +
        '<td>' + esc(etapa) + '</td>' +
        '<td class="col-numero"><strong>' + esc(numero(c.dias_na_etapa)) + '</strong></td>' +
        '<td class="col-numero">' + esc(numero(c.dias_desde_cadastro)) + '</td>' +
        '<td class="col-nowrap">' + esc(data(c.previsao_conclusao)) + '</td>' +
        '<td>' + (c.atrasado ? '<span class="selo selo-erro">Atrasado</span>' : '<span class="selo selo-ok">No prazo</span>') + '</td>' +
        '</tr>';
    }).join('');
    return '<p class="tabela-resumo">' + esc(numero(lista.length)) + ' cliente(s), do mais parado ao menos parado. Clique na linha para abrir a ficha.</p>' +
      '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Clientes parados na mesma etapa da ativação</caption>' +
      '<thead><tr><th scope="col">Nome</th><th scope="col">Cidade</th><th scope="col">Etapa atual</th>' +
      '<th scope="col" class="col-numero">Dias na etapa</th><th scope="col" class="col-numero">Dias desde o cadastro</th>' +
      '<th scope="col">Previsão</th><th scope="col">Prazo de 90 dias</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     DICAS, USINAS E PARCEIROS
     ------------------------------------------------------------ */
  function carregarDicas() {
    return carregarEm('dicas-resultado', 'Carregando dicas...', function () { return api('/v1/painel/dicas'); }, renderDicas, 'dicas');
  }

  function renderDicas(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return htmlVazio('Nenhuma dica cadastrada.');
    return '<div class="grade grade-3">' + lista.map(function (d, i) {
      var id = 't-dica-' + i;
      return '<section class="cartao cartao-dica" aria-labelledby="' + id + '">' +
        '<h2 class="cartao-titulo" id="' + id + '">' + esc(ou(d.titulo)) + '</h2>' +
        (d.descricao ? '<p class="dica-texto">' + esc(d.descricao) + '</p>' : '') +
        '<div class="destaques">' +
          destaque('Economia por mês', moeda(d.economia_mensal), 'verde') +
          destaque('Economia por ano', moeda(d.economia_anual), 'verde') +
        '</div></section>';
    }).join('') + '</div>';
  }

  function carregarUsinas() {
    return carregarEm('usinas-resultado', 'Carregando usinas...', function () { return api('/v1/painel/usinas'); }, renderTabelaUsinas, 'usinas');
  }

  function renderTabelaUsinas(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return htmlVazio('Nenhuma usina cadastrada.');
    var linhas = lista.map(function (u) {
      return '<tr>' +
        '<td><strong>' + esc(ou(u.nome)) + '</strong></td>' +
        '<td>' + esc(ou(u.localizacao)) + '</td>' +
        '<td class="col-numero">' + esc(numero(u.capacidade_geracao_kwh)) + ' kWh</td>' +
        '<td class="col-numero">' + esc(numero(u.clientes_ativos)) + '</td>' +
        '<td>' + selo(u.status) + '</td>' +
        '<td class="col-nowrap">' + esc(data(u.data_ativacao)) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Usinas da Bulbe</caption>' +
      '<thead><tr><th scope="col">Usina</th><th scope="col">Localização</th><th scope="col" class="col-numero">Capacidade</th>' +
      '<th scope="col" class="col-numero">Clientes ativos</th><th scope="col">Status</th><th scope="col">Ativa desde</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  function carregarParceiros() {
    var incluirInativos = $('filtro-parceiros-inativos').checked;
    return carregarEm('parceiros-resultado', 'Carregando parceiros...',
      function () { return api('/v1/painel/parceiros' + (incluirInativos ? '?apenas_ativos=false' : '')); },
      renderTabelaParceiros, 'parceiros');
  }

  function renderTabelaParceiros(lista) {
    lista = Array.isArray(lista) ? lista : [];
    if (!lista.length) return htmlVazio('Nenhum parceiro encontrado.');
    var linhas = lista.map(function (p) {
      return '<tr>' +
        '<td><strong>' + esc(ou(p.nome)) + '</strong></td>' +
        '<td>' + esc(ou(p.categoria)) + '</td>' +
        '<td>' + (p.ativo === false ? '<span class="selo selo-erro">Inativo</span>' : '<span class="selo selo-ok">Ativo</span>') + '</td>' +
        '<td class="col-nowrap">' + esc(data(p.criado_em)) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Parceiros do Clube Bulbe</caption>' +
      '<thead><tr><th scope="col">Parceiro</th><th scope="col">Categoria</th><th scope="col">Situação</th><th scope="col">Parceiro desde</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  /* ------------------------------------------------------------
     AUDITORIA E EXPURGO (admin)
     ------------------------------------------------------------ */
  function renderTabelaAuditoria(lista) {
    var linhas = lista.map(function (a) {
      var acao = a.acao || '';
      var tom = Object.prototype.hasOwnProperty.call(TONS_AUDITORIA, acao) ? TONS_AUDITORIA[acao] : 'neutro';
      var nomeAcao = Object.prototype.hasOwnProperty.call(ACOES_AUDITORIA, acao) ? ACOES_AUDITORIA[acao] : rotulo(acao);
      var quem = a.funcionario_nome
        ? esc(a.funcionario_nome) + (a.funcionario_id ? ' <span class="texto-suave">#' + esc(a.funcionario_id) + '</span>' : '')
        : (a.funcionario_id ? '#' + esc(a.funcionario_id) : '<span class="texto-suave">—</span>');
      var recurso = '—';
      if (a.recurso_tipo === 'cliente' && a.recurso_id) {
        recurso = '<a class="link-linha" href="' + esc(hashCliente(a.recurso_id)) + '">Cliente <code>' + esc(a.recurso_id) + '</code></a>';
      } else if (a.recurso_tipo || a.recurso_id) {
        recurso = esc([a.recurso_tipo, a.recurso_id].filter(Boolean).join(' '));
      }
      return '<tr>' +
        '<td class="col-nowrap">' + esc(dataHora(a.criado_em)) + '</td>' +
        '<td><span class="selo selo-' + tom + '">' + esc(nomeAcao) + '</span></td>' +
        '<td>' + quem + '</td>' +
        '<td>' + esc(ou(a.email_informado)) + '</td>' +
        '<td>' + recurso + '</td>' +
        '<td class="col-nowrap">' + esc(ou(a.ip)) + '</td>' +
        '<td class="col-detalhe">' + esc(ou(a.detalhe)) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="tabela-rolagem"><table class="tabela">' +
      '<caption class="visualmente-oculto">Registros de auditoria</caption>' +
      '<thead><tr><th scope="col">Quando</th><th scope="col">Ação</th><th scope="col">Funcionário</th>' +
      '<th scope="col">E-mail informado</th><th scope="col">Recurso</th><th scope="col">IP</th><th scope="col">Detalhe</th></tr></thead>' +
      '<tbody>' + linhas + '</tbody></table></div>';
  }

  async function executarExpurgo() {
    var botao = $('botao-expurgo');
    var alvo = $('expurgo-resultado');
    var ok = window.confirm('Apagar agora as conversas do assistente e os registros de auditoria mais antigos que o prazo de ' +
      'retenção configurado no servidor? Esta ação não pode ser desfeita.');
    if (!ok) return;
    botao.disabled = true;
    alvo.innerHTML = htmlCarregando('Expurgando dados antigos...');
    try {
      var r = await api('/v1/painel/admin/expurgo', { metodo: 'POST' }) || {};
      alvo.innerHTML = '<div class="aviso aviso-info" role="status">Expurgo concluído: ' +
        esc(numero(r.chat_historico || 0)) + ' registro(s) do histórico do chat, ' +
        esc(numero(r.chat_conversas || 0)) + ' conversa(s), ' +
        esc(numero(r.chat_mensagens || 0)) + ' mensagem(ns) e ' +
        esc(numero(r.auditoria || 0)) + ' registro(s) de auditoria removidos' +
        (ehNumero(r.dias_chat) ? ' (retenção: ' + esc(numero(r.dias_chat)) + ' dias para o chat e ' + esc(numero(r.dias_auditoria)) + ' para a auditoria)' : '') +
        '.</div>';
      carregarLista('auditoria', 1);
    } catch (erro) {
      if (erro.status !== 401) alvo.innerHTML = htmlErro(erro);
    } finally {
      botao.disabled = false;
    }
  }

  /* ------------------------------------------------------------
     USO DO ASSISTENTE (admin)
     ------------------------------------------------------------ */
  function carregarUsoAssistente() {
    var dias = $('filtro-uso-dias').value || '30';
    return carregarEm('uso-resultado', 'Carregando uso do assistente...',
      function () { return api('/v1/painel/uso-chatbot' + montarQuery({ dias: dias })); }, renderUsoAssistente, 'uso-assistente');
  }

  function renderUsoAssistente(u) {
    u = u || {};
    var duracao = ehNumero(u.duracao_media_ms) ? decimal(Number(u.duracao_media_ms) / 1000) + ' s' : '—';
    var html = '<div class="grade grade-metricas">' +
      cartaoMetrica('Perguntas', numero(u.perguntas), numero(u.conversas) + ' conversas · ' + numero(u.funcionarios_ativos) + ' funcionário(s)') +
      cartaoMetrica('Custo estimado', dolar(u.custo_estimado_usd), 'no período de ' + numero(u.periodo_dias) + ' dias', 'amarela') +
      cartaoMetrica('Custo médio por pergunta', dolar(u.custo_medio_por_pergunta_usd), 'estimativa pelos preços configurados', 'amarela') +
      cartaoMetrica('Tempo médio de resposta', duracao, 'do envio da pergunta ao fim da resposta') +
      cartaoMetrica('Tokens de entrada', numero(u.input_tokens), numero(u.cache_read_tokens) + ' lidos do cache', 'verde') +
      cartaoMetrica('Tokens de saída', numero(u.output_tokens), 'texto gerado pelo modelo', 'verde') +
      '</div>';

    var porFuncionario = Array.isArray(u.por_funcionario) ? u.por_funcionario : [];
    var tabelaFuncionarios = porFuncionario.length
      ? '<div class="tabela-rolagem"><table class="tabela"><caption class="visualmente-oculto">Uso por funcionário</caption>' +
        '<thead><tr><th scope="col">Funcionário</th><th scope="col" class="col-numero">Perguntas</th><th scope="col" class="col-numero">Custo estimado</th></tr></thead><tbody>' +
        porFuncionario.map(function (f) {
          return '<tr><td>' + esc(ou(f.nome)) + (f.funcionario_id ? ' <span class="texto-suave">#' + esc(f.funcionario_id) + '</span>' : '') + '</td>' +
            '<td class="col-numero">' + esc(numero(f.perguntas)) + '</td>' +
            '<td class="col-numero">' + esc(dolar(f.custo_estimado_usd)) + '</td></tr>';
        }).join('') + '</tbody></table></div>'
      : htmlVazio('Nenhuma pergunta no período.');

    var ferramentas = (Array.isArray(u.ferramentas_mais_usadas) ? u.ferramentas_mais_usadas : []).map(function (f) {
      return { rotulo: String(ou(f.nome, '')), valor: f.usos, tom: 'azul' };
    });

    var porDia = Array.isArray(u.por_dia) ? u.por_dia : [];
    var tabelaDias = porDia.length
      ? '<div class="tabela-rolagem tabela-rolagem-limitada"><table class="tabela"><caption class="visualmente-oculto">Uso por dia</caption>' +
        '<thead><tr><th scope="col">Dia</th><th scope="col" class="col-numero">Perguntas</th><th scope="col" class="col-numero">Custo estimado</th></tr></thead><tbody>' +
        porDia.map(function (d) {
          return '<tr><td class="col-nowrap">' + esc(data(d.data)) + '</td>' +
            '<td class="col-numero">' + esc(numero(d.perguntas)) + '</td>' +
            '<td class="col-numero">' + esc(dolar(d.custo_estimado_usd)) + '</td></tr>';
        }).join('') + '</tbody></table></div>'
      : htmlVazio('Nenhuma pergunta no período.');

    return html +
      '<div class="grade grade-2">' +
        '<section class="cartao" aria-labelledby="t-uso-func"><h2 class="cartao-titulo" id="t-uso-func">Por funcionário</h2>' + tabelaFuncionarios + '</section>' +
        '<section class="cartao" aria-labelledby="t-uso-ferr"><h2 class="cartao-titulo" id="t-uso-ferr">Ferramentas mais usadas <span class="texto-suave">consultas ao banco feitas pelo assistente</span></h2>' +
          (ferramentas.length ? htmlBarras(ferramentas) : htmlVazio('Nenhuma ferramenta usada no período.')) + '</section>' +
      '</div>' +
      '<section class="cartao" aria-labelledby="t-uso-dia"><h2 class="cartao-titulo" id="t-uso-dia">Por dia</h2>' + tabelaDias + '</section>' +
      '<p class="texto-suave">O custo é uma estimativa calculada pelo servidor a partir dos tokens de cada resposta e dos preços configurados; a fatura oficial é a do console da Anthropic.</p>';
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

  /** Rola até o fim só se o usuário já estava perto do fim (não atrapalha quem subiu para reler). */
  function rolarChatSeNoFim() {
    var caixa = $('chat-mensagens');
    if (caixa.scrollHeight - caixa.scrollTop - caixa.clientHeight < 120) caixa.scrollTop = caixa.scrollHeight;
  }

  /** Cria o elemento de uma mensagem (ainda fora da tela). */
  function criarMensagem(papel) {
    var msg = document.createElement('div');
    msg.className = 'msg msg-' + papel;
    var rotuloLeitor = document.createElement('span');
    rotuloLeitor.className = 'visualmente-oculto';
    rotuloLeitor.textContent = papel === 'assistente' ? 'Assistente: ' : 'Você: ';
    var balao = document.createElement('div');
    balao.className = 'msg-balao';
    msg.appendChild(rotuloLeitor);
    msg.appendChild(balao);
    return { msg: msg, balao: balao };
  }

  /**
   * Rodapé discreto da resposta: ferramentas consultadas e custo estimado.
   * Tudo via textContent (nomes de ferramentas e modelo vêm da API).
   */
  function preencherRodape(msg, ferramentas, modelo, uso, emAndamento) {
    var rodape = msg.querySelector('.msg-ferramentas');
    if (!rodape) {
      rodape = document.createElement('div');
      rodape.className = 'msg-ferramentas';
    }
    rodape.textContent = '';
    var lista = Array.isArray(ferramentas) ? ferramentas : [];
    if (lista.length) {
      var legenda = document.createElement('span');
      legenda.textContent = emAndamento ? 'Consultando:' : 'Consultou:';
      rodape.appendChild(legenda);
      lista.forEach(function (nome) {
        var code = document.createElement('code');
        code.textContent = String(nome);
        rodape.appendChild(code);
      });
    }
    if (uso && ehNumero(uso.custo_estimado_usd)) {
      var custo = document.createElement('span');
      custo.className = 'msg-custo';
      custo.textContent = 'custo ≈ ' + dolar(uso.custo_estimado_usd);
      custo.title = numero(uso.input_tokens || 0) + ' tokens de entrada · ' + numero(uso.output_tokens || 0) + ' de saída · ' +
        numero(uso.cache_read_tokens || 0) + ' lidos do cache';
      rodape.appendChild(custo);
    }
    rodape.title = modelo ? 'Modelo: ' + modelo : '';
    if (rodape.childNodes.length) {
      if (!rodape.parentNode) msg.appendChild(rodape);
    } else if (rodape.parentNode) {
      rodape.remove();
    }
  }

  function adicionarMensagem(papel, texto, ferramentas, modelo, uso) {
    var m = criarMensagem(papel);
    if (papel === 'assistente') {
      m.balao.innerHTML = formatarResposta(texto); // formatarResposta escapa o conteúdo
      preencherRodape(m.msg, ferramentas, modelo, uso, false);
    } else {
      m.balao.textContent = texto;
    }
    $('chat-mensagens').appendChild(m.msg);
    rolarChatParaFim();
    return m;
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

  function indicador(texto) {
    $('chat-digitando-texto').textContent = texto;
  }

  function definirEnviando(enviando) {
    estado.chat.enviando = enviando;
    if (enviando) indicador('Assistente pensando...');
    $('chat-digitando').hidden = !enviando;
    $('chat-enviar').disabled = enviando;
    $('botao-chat-limpar').disabled = enviando;
    $('botao-chat-conversas').disabled = enviando;
    $('chat-mensagens').setAttribute('aria-busy', enviando ? 'true' : 'false');
    $('chat-sugestoes').querySelectorAll('button').forEach(function (b) { b.disabled = enviando; });
    $('chat-conversas-lista').querySelectorAll('button').forEach(function (b) { b.disabled = enviando; });
    if (enviando) rolarChatParaFim();
  }

  /** Guarda o conversa_id (memória + sessionStorage, para reabrir a conversa ao recarregar a página). */
  function definirConversa(id) {
    estado.chat.conversaId = id ? String(id) : null;
    if (estado.chat.conversaId) gravarSessao(CHAVE_CONVERSA, estado.chat.conversaId);
    else removerSessao(CHAVE_CONVERSA);
    $('chat-conversas-lista').querySelectorAll('[data-conversa]').forEach(function (b) {
      if (b.getAttribute('data-conversa') === estado.chat.conversaId) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
  }

  /** Resposta do assistente sendo montada aos poucos (streaming). */
  function novaRespostaEmAndamento() {
    var r = { msg: null, balao: null, texto: '', ferramentas: [], agendado: false };
    r.garantir = function () {
      if (r.msg) return;
      var m = criarMensagem('assistente');
      r.msg = m.msg;
      r.balao = m.balao;
      r.msg.classList.add('msg-transmitindo');
      r.msg.setAttribute('aria-busy', 'true'); // leitores de tela anunciam só quando terminar
      $('chat-mensagens').appendChild(r.msg);
      rolarChatParaFim();
    };
    r.desenhar = function () {
      if (r.balao) r.balao.innerHTML = formatarResposta(r.texto); // escapa antes de formatar
      rolarChatSeNoFim();
    };
    r.adicionarTexto = function (delta) {
      r.garantir();
      r.texto += delta;
      if (r.agendado) return;
      r.agendado = true;
      window.requestAnimationFrame(function () { r.agendado = false; r.desenhar(); });
    };
    r.adicionarFerramenta = function (nome) {
      var texto = String(nome || '').trim();
      if (!texto) return;
      r.garantir();
      if (r.ferramentas.indexOf(texto) === -1) r.ferramentas.push(texto);
      if (!r.texto) r.balao.innerHTML = '<p class="msg-consultando">Consultando os dados...</p>';
      preencherRodape(r.msg, r.ferramentas, null, null, true);
      rolarChatSeNoFim();
    };
    r.finalizar = function (texto, ferramentas, modelo, uso) {
      r.garantir();
      if (typeof texto === 'string' && texto) r.texto = texto;
      r.desenhar();
      preencherRodape(r.msg, Array.isArray(ferramentas) ? ferramentas : r.ferramentas, modelo, uso, false);
      r.msg.classList.remove('msg-transmitindo');
      r.msg.setAttribute('aria-busy', 'false');
    };
    r.interromper = function () {
      if (!r.msg) return;
      if (!r.texto) { r.msg.remove(); r.msg = null; return; }
      r.desenhar();
      preencherRodape(r.msg, r.ferramentas, null, null, false);
      r.msg.classList.remove('msg-transmitindo');
      r.msg.classList.add('msg-interrompida');
      r.msg.setAttribute('aria-busy', 'false');
    };
    return r;
  }

  /** Lê um corpo text/event-stream: eventos "data: <json>" separados por linha em branco. */
  async function lerEventosSSE(corpo, aoEvento, aoReceber) {
    var leitor = corpo.getReader();
    var decodificador = new TextDecoder('utf-8');
    var buffer = '';
    var separador = /\r\n\r\n|\n\n|\r\r/;
    function processarBloco(bloco) {
      var dados = [];
      bloco.split(/\r\n|\r|\n/).forEach(function (linha) {
        if (linha.indexOf('data:') === 0) dados.push(linha.slice(5).replace(/^ /, ''));
      });
      if (!dados.length) return; // comentário (": ping") ou campo sem dados
      var evento;
      try { evento = JSON.parse(dados.join('\n')); } catch (e) { return; }
      if (evento && typeof evento === 'object') aoEvento(evento);
    }
    for (;;) {
      var parte = await leitor.read();
      if (parte.done) break;
      aoReceber();
      buffer += decodificador.decode(parte.value, { stream: true });
      var achou;
      while ((achou = separador.exec(buffer))) {
        processarBloco(buffer.slice(0, achou.index));
        buffer = buffer.slice(achou.index + achou[0].length);
      }
    }
    buffer += decodificador.decode();
    if (buffer.trim()) processarBloco(buffer);
  }

  /**
   * Conversa pelo stream (POST /v1/painel/chat/stream). Devolve {final} ou {fallback: true}
   * quando o stream falha antes de começar (rota inexistente, rede, resposta que não é SSE).
   * Erros definitivos (401, erro padronizado da API, evento "erro") viram ErroApi.
   */
  async function conversarComStream(corpo, resposta) {
    if (!window.ReadableStream || !window.TextDecoder || !window.AbortController) return { fallback: true };
    var controle = new AbortController();
    var temporizador = null;
    function reiniciarTempo() {
      clearTimeout(temporizador);
      temporizador = setTimeout(function () { controle.abort(); }, TEMPO_INATIVIDADE_STREAM);
    }
    var headers = { 'Accept': 'text/event-stream', 'Content-Type': 'application/json' };
    var token = lerSessao(CHAVE_TOKEN);
    if (token) headers['Authorization'] = 'Bearer ' + token;

    reiniciarTempo();
    var r;
    try {
      r = await fetch('/v1/painel/chat/stream', {
        method: 'POST', headers: headers, body: JSON.stringify(corpo),
        signal: controle.signal, cache: 'no-store', credentials: 'same-origin'
      });
    } catch (e) {
      clearTimeout(temporizador);
      return { fallback: true };
    }
    if (r.status === 401) {
      clearTimeout(temporizador);
      sair('expirada');
      throw new ErroApi('NAO_AUTENTICADO', 'Sessão expirada. Redirecionando para o login...', 401);
    }
    var tipo = (r.headers.get('content-type') || '').toLowerCase();
    if (!r.ok || tipo.indexOf('text/event-stream') === -1 || !r.body) {
      clearTimeout(temporizador);
      var dados = null;
      try { dados = await r.json(); } catch (e) { dados = null; }
      var padronizado = dados && ((dados.error && dados.error.code) || (dados.detail && dados.detail.error && dados.detail.error.code));
      if (!r.ok && padronizado) {
        var info = extrairErro(dados, r.status);
        throw new ErroApi(info.code, info.message, r.status);
      }
      return { fallback: true };
    }

    var iniciou = false;
    var final = null;
    var erroEvento = null;
    try {
      await lerEventosSSE(r.body, function (ev) {
        if (ev.tipo === 'inicio') {
          iniciou = true;
          if (ev.conversa_id) definirConversa(ev.conversa_id);
        } else if (ev.tipo === 'texto') {
          iniciou = true;
          if (typeof ev.delta === 'string' && ev.delta) {
            resposta.adicionarTexto(ev.delta);
            indicador('Assistente escrevendo...');
          }
        } else if (ev.tipo === 'ferramenta') {
          iniciou = true;
          resposta.adicionarFerramenta(ev.nome);
          indicador('Consultando ' + String(ev.nome || 'os dados') + '...');
        } else if (ev.tipo === 'fim') {
          final = ev;
        } else if (ev.tipo === 'erro') {
          erroEvento = ev.error || {};
        }
      }, reiniciarTempo);
    } catch (e) {
      // Conexão caiu ou ficou sem dados por muito tempo.
      if (!iniciou && !final && !erroEvento) return { fallback: true };
    } finally {
      clearTimeout(temporizador);
    }
    if (final) return { final: final };
    if (erroEvento) {
      throw new ErroApi(erroEvento.code || 'ERRO', erroEvento.message || 'Erro ao gerar a resposta.', Number(erroEvento.status) || 0);
    }
    if (!iniciou) return { fallback: true };
    throw new ErroApi('STREAM_INTERROMPIDO', 'a conexão caiu antes do fim da resposta', 0);
  }

  /** Fallback sem streaming: POST /v1/painel/chat (mesmo corpo). */
  async function conversarSemStream(corpo) {
    var r = await api('/v1/painel/chat', { metodo: 'POST', corpo: corpo, tempoLimite: TEMPO_LIMITE_CHAT }) || {};
    return {
      final: {
        resposta: typeof r.resposta === 'string' ? r.resposta : '',
        ferramentas_usadas: r.ferramentas_usadas, modelo: r.modelo, conversa_id: r.conversa_id, uso: r.uso
      }
    };
  }

  async function enviarPergunta(textoBruto) {
    var texto = String(textoBruto || '').trim();
    if (!texto || estado.chat.enviando) return;
    if (texto.length > MAX_MENSAGEM) texto = texto.slice(0, MAX_MENSAGEM);

    var entrada = $('chat-entrada');
    // Com conversa_id o servidor usa o histórico dele; o histórico em texto só vale para servidores sem conversas (v1).
    var corpo = { mensagem: texto, historico: estado.chat.historico.slice(-MAX_HISTORICO) };
    if (estado.chat.conversaId) corpo.conversa_id = estado.chat.conversaId;

    abrirChat(false);
    alternarConversas(false);
    adicionarMensagem('funcionario', texto);
    entrada.value = '';
    atualizarContador();
    mostrarSugestoes(false);
    definirEnviando(true);

    var resposta = novaRespostaEmAndamento();
    try {
      var resultado = await conversarComStream(corpo, resposta);
      if (resultado.fallback) {
        indicador('Assistente pensando...');
        resultado = await conversarSemStream(corpo);
      }
      var fim = resultado.final || {};
      var textoFinal = typeof fim.resposta === 'string' && fim.resposta ? fim.resposta : resposta.texto;
      resposta.finalizar(textoFinal, fim.ferramentas_usadas, fim.modelo, fim.uso);
      if (fim.conversa_id) definirConversa(fim.conversa_id);
      estado.chat.historico.push({ papel: 'funcionario', texto: texto });
      estado.chat.historico.push({ papel: 'assistente', texto: textoFinal });
      if (estado.chat.historico.length > MAX_HISTORICO) {
        estado.chat.historico = estado.chat.historico.slice(-MAX_HISTORICO);
      }
      if (fim.modelo) $('chat-modelo').textContent = 'Modelo: ' + fim.modelo + ' · somente leitura';
    } catch (erro) {
      resposta.interromper();
      if (erro.status === 401) return;
      if (erro.status === 503 || erro.code === 'CHATBOT_INDISPONIVEL') {
        adicionarAvisoChat('O assistente está indisponível: a chave da IA não foi configurada. ' +
          'Peça ao responsável técnico para configurar ANTHROPIC_API_KEY no servidor e reiniciar a API.', 'alerta');
      } else if (erro.status === 429) {
        adicionarAvisoChat('Muitas perguntas em sequência. Aguarde alguns segundos e tente de novo.', 'alerta');
      } else if (erro.status === 404 && estado.chat.conversaId) {
        definirConversa(null);
        estado.chat.historico = [];
        adicionarAvisoChat('A conversa não foi encontrada (pode ter sido apagada pela retenção de dados). ' +
          'Envie a pergunta de novo para começar uma nova conversa.', 'alerta');
      } else if (erro.code === 'STREAM_INTERROMPIDO') {
        adicionarAvisoChat('A resposta foi interrompida: ' + erro.message + '. Tente perguntar de novo.', 'alerta');
      } else {
        adicionarAvisoChat('Não foi possível obter a resposta: ' + (erro.message || 'erro inesperado') + '.');
      }
      if (!entrada.value) { entrada.value = texto; atualizarContador(); } // devolve a pergunta para reenviar
    } finally {
      if (!estado.saindo) {
        definirEnviando(false);
        if (!mediaTelaMenor.matches || estado.chat.aberto) entrada.focus();
      }
    }
  }

  function limparMensagensDaTela() {
    $('chat-mensagens').querySelectorAll('.msg').forEach(function (m) { m.remove(); });
  }

  /** "Nova conversa": esquece o conversa_id (a próxima pergunta cria outra conversa no servidor). */
  function novaConversa() {
    if (estado.chat.enviando) return;
    definirConversa(null);
    estado.chat.historico = [];
    limparMensagensDaTela();
    alternarConversas(false);
    mostrarSugestoes(true);
    $('chat-entrada').focus();
  }

  /* ---------- Conversas anteriores ---------- */
  function alternarConversas(abrir) {
    var painel = $('chat-conversas');
    var aberto = abrir === undefined ? painel.hidden : !!abrir;
    if (aberto === !painel.hidden) return;
    painel.hidden = !aberto;
    estado.chat.conversasAbertas = aberto;
    $('botao-chat-conversas').setAttribute('aria-expanded', aberto ? 'true' : 'false');
    if (aberto) carregarConversas();
  }

  async function carregarConversas() {
    var alvo = $('chat-conversas-lista');
    alvo.setAttribute('aria-busy', 'true');
    alvo.innerHTML = htmlCarregando('Carregando conversas...');
    try {
      var r = await api('/v1/painel/chat/conversas');
      var lista = r && Array.isArray(r.conversas) ? r.conversas : [];
      if (!lista.length) {
        alvo.innerHTML = htmlVazio('Nenhuma conversa anterior.');
        return;
      }
      alvo.innerHTML = '<ul class="lista-conversas">' + lista.map(function (c) {
        var atual = estado.chat.conversaId && String(c.id) === estado.chat.conversaId;
        return '<li><button type="button" class="conversa-item" data-conversa="' + esc(c.id) + '"' + (atual ? ' aria-current="true"' : '') + '>' +
          '<span class="conversa-titulo">' + esc(ou(c.titulo, 'Conversa sem título')) + '</span>' +
          '<span class="texto-suave">' + esc(dataHora(c.atualizado_em)) + ' · ' + esc(numero(c.total_mensagens)) + ' mensagem(ns)</span>' +
          '</button></li>';
      }).join('') + '</ul>';
      var primeiro = alvo.querySelector('button');
      if (primeiro && estado.chat.conversasAbertas) primeiro.focus();
    } catch (erro) {
      if (erro.status === 401) return;
      alvo.innerHTML = erro.status === 404
        ? htmlVazio('O histórico de conversas ainda não está disponível neste servidor.')
        : htmlErro(erro);
    } finally {
      alvo.removeAttribute('aria-busy');
    }
  }

  /** Reabre uma conversa do servidor (GET /v1/painel/chat/conversas/{id}). */
  async function abrirConversa(id, silencioso) {
    if (!id || estado.chat.enviando) return;
    try {
      var c = await api('/v1/painel/chat/conversas/' + encodeURIComponent(id)) || {};
      var mensagens = Array.isArray(c.mensagens) ? c.mensagens : [];
      limparMensagensDaTela();
      definirConversa(c.id || id);
      estado.chat.historico = [];
      mensagens.forEach(function (m) {
        var papel = m.papel === 'assistente' ? 'assistente' : 'funcionario';
        var texto = typeof m.texto === 'string' ? m.texto : '';
        if (!texto) return;
        adicionarMensagem(papel, texto);
        estado.chat.historico.push({ papel: papel, texto: texto });
      });
      estado.chat.historico = estado.chat.historico.slice(-MAX_HISTORICO);
      mostrarSugestoes(!mensagens.length);
      alternarConversas(false);
      if (!silencioso) {
        abrirChat(false);
        $('chat-entrada').focus();
      }
    } catch (erro) {
      if (erro.status === 401) return;
      if (erro.status === 404) {
        if (estado.chat.conversaId === String(id)) definirConversa(null);
        if (!silencioso) adicionarAvisoChat('Conversa não encontrada (pode ter sido apagada pela retenção de dados).', 'alerta');
      } else if (!silencioso) {
        adicionarAvisoChat('Não foi possível abrir a conversa: ' + (erro.message || 'erro inesperado') + '.');
      }
    }
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

    // Listas paginadas: filtros novos voltam para a página 1.
    function aoFiltrar(nome) {
      return function (e) { if (e && e.type === 'submit') e.preventDefault(); carregarLista(nome); };
    }
    $('form-clientes').addEventListener('submit', aoFiltrar('clientes'));
    $('form-clientes').addEventListener('reset', function () { window.setTimeout(function () { carregarLista('clientes'); }, 0); });
    $('filtro-status').addEventListener('change', aoFiltrar('clientes'));
    $('filtro-etapa').addEventListener('change', aoFiltrar('clientes'));
    $('filtro-limite').addEventListener('change', aoFiltrar('clientes'));
    $('form-adesoes').addEventListener('submit', aoFiltrar('adesoes'));
    $('filtro-adesao-situacao').addEventListener('change', aoFiltrar('adesoes'));
    $('filtro-adesao-limite').addEventListener('change', aoFiltrar('adesoes'));
    $('form-atendimentos').addEventListener('submit', aoFiltrar('atendimentos'));
    $('filtro-atendimento-status').addEventListener('change', aoFiltrar('atendimentos'));
    $('filtro-atendimento-limite').addEventListener('change', aoFiltrar('atendimentos'));
    $('form-auditoria').addEventListener('submit', aoFiltrar('auditoria'));
    $('form-auditoria').addEventListener('reset', function () { window.setTimeout(function () { carregarLista('auditoria'); }, 0); });
    $('filtro-auditoria-acao').addEventListener('change', aoFiltrar('auditoria'));
    $('filtro-auditoria-limite').addEventListener('change', aoFiltrar('auditoria'));
    $('botao-expurgo').addEventListener('click', executarExpurgo);

    // Ativações, parceiros e uso do assistente
    $('botao-atualizar-ativacoes').addEventListener('click', function () { carregarResumoAtivacoes(); carregarParados(); });
    $('form-parados').addEventListener('submit', function (e) { e.preventDefault(); carregarParados(); });
    $('filtro-parados-etapa').addEventListener('change', carregarParados);
    $('form-parceiros').addEventListener('submit', function (e) { e.preventDefault(); carregarParceiros(); });
    $('filtro-parceiros-inativos').addEventListener('change', carregarParceiros);
    $('filtro-uso-dias').addEventListener('change', carregarUsoAssistente);

    // Linhas clicáveis (o link dentro da linha continua sendo o caminho acessível por teclado).
    $('conteudo').addEventListener('click', function (e) {
      var acao = e.target.closest('[data-acao="perguntar-cliente"]');
      if (acao) { perguntarSobreCliente(); return; }
      var paginar = e.target.closest('button[data-paginar]');
      if (paginar) {
        if (!paginar.disabled) carregarLista(paginar.getAttribute('data-paginar'), Number(paginar.getAttribute('data-pagina')) || 1, true);
        return;
      }
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
    $('botao-chat-limpar').addEventListener('click', novaConversa);
    $('botao-chat-conversas').addEventListener('click', function () { alternarConversas(); });
    $('botao-conversas-fechar').addEventListener('click', function () {
      alternarConversas(false);
      $('botao-chat-conversas').focus();
    });
    $('chat-conversas-lista').addEventListener('click', function (e) {
      var item = e.target.closest('button[data-conversa]');
      if (item && !item.disabled) abrirConversa(item.getAttribute('data-conversa'), false);
    });
    $('botao-chat-fechar').addEventListener('click', fecharChat);
    $('botao-chat-abrir').addEventListener('click', function () { abrirChat(true); });
    $('botao-chat-alternar').addEventListener('click', function () {
      if (estado.chat.aberto) fecharChat(); else abrirChat(true);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (estado.chat.conversasAbertas) {
        alternarConversas(false);
        $('botao-chat-conversas').focus();
      } else if (estado.chat.aberto && mediaTelaMenor.matches) {
        fecharChat();
      }
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
      if (salvo && typeof salvo === 'object') {
        // Só para montar o menu sem esperar o /me; quem decide o acesso é a API (exigir_admin).
        estado.funcionario = salvo;
        mostrarFuncionario(salvo);
      }
    } catch (e) { /* ignora */ }

    ligarEventos();
    atualizarContador();
    aplicarPerfilNoMenu();
    navegar();

    try {
      var perfilAntes = estado.funcionario && estado.funcionario.perfil;
      estado.funcionario = await api('/v1/painel/me');
      mostrarFuncionario(estado.funcionario);
      aplicarPerfilNoMenu();
      if (perfilAntes !== estado.funcionario.perfil && ROTAS_ADMIN.indexOf(lerRota().tela) !== -1) navegar();
    } catch (e) {
      /* 401 já redireciona; outros erros aparecem nas telas */
    }
    carregarSugestoes();
    // Recarregou a página no meio de uma conversa: reabre a conversa guardada no servidor.
    var conversaSalva = lerSessao(CHAVE_CONVERSA);
    if (conversaSalva) abrirConversa(conversaSalva, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
