/* ============================================================
   PAINEL BULBE — núcleo compartilhado (window.Painel)
   Formatação pt-BR, escape de HTML, chamada à API com token,
   toasts, modal, paginação e registro das telas.
   SEGURANÇA: todo dado vindo da API passa por esc() (ou textContent)
   antes de entrar no HTML. A CSP não permite script/style inline, então
   não há onclick="" nem style="" no HTML gerado (larguras via CSSOM).
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel = window.Painel || {};

  /* ---------------- constantes ---------------- */
  P.CHAVE_TOKEN = 'bulbe_painel_token';
  P.CHAVE_FUNCIONARIO = 'bulbe_painel_funcionario';
  P.CHAVE_CONVERSA = 'bulbe_painel_conversa_id';
  P.CHAVE_CHAT_ABERTO = 'bulbe_painel_chat_aberto';
  P.TEMPO_LIMITE_PADRAO = 30000;

  P.NOMES_ETAPAS = ['Cadastro', 'Documentos', 'Solicitação à CEMIG', 'Análise CEMIG', 'Energia liberada'];
  var MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  P.MESES = MESES;

  var ROTULOS = {
    ativo: 'Ativo', ativa: 'Ativa', em_ativacao: 'Em ativação', cancelado: 'Cancelado',
    em_manutencao: 'Em manutenção', inativa: 'Inativa', inativo: 'Inativo',
    paga: 'Paga', em_aberto: 'Em aberto', vencida: 'Vencida',
    pendente: 'Pendente', aderiu: 'Aderiu', expirada: 'Expirada', expirado: 'Expirado',
    rascunho: 'Rascunho', enviada: 'Enviada', aprovada: 'Aprovada', recusada: 'Recusada',
    aberto: 'Aberto', em_andamento: 'Em andamento', resolvido: 'Resolvido',
    bot: 'Com o assistente', aguardando_atendente: 'Aguardando atendente', em_atendimento: 'Em atendimento',
    salvo: 'Salvo', usado: 'Usado', descartado: 'Descartado',
    disponivel: 'Disponível', aberta: 'Aberta', bloqueada: 'Bloqueada', normal: 'Normal', especial: 'Especial',
    residencia: 'Residência', empresa: 'Empresa',
    whatsapp: 'WhatsApp', email: 'E-mail', app: 'App', site: 'Site', link: 'Link', ouvidoria: 'Ouvidoria',
    telefone: 'Telefone', ficticio: 'Fictício',
    vencimento: 'Vencimento', ativacao: 'Ativação', clube: 'Clube Bulbe', indicacao: 'Indicação', promocao: 'Promoção',
    admin: 'Administrador', atendimento: 'Atendimento',
    concluida: 'Concluída', atual: 'Etapa atual', visitante: 'Visitante', cliente: 'Cliente'
  };
  var TONS = {
    ativo: 'ok', ativa: 'ok', paga: 'ok', aderiu: 'ok', aprovada: 'ok', resolvido: 'ok', aberta: 'ok', concluida: 'ok',
    em_ativacao: 'alerta', em_manutencao: 'alerta', em_aberto: 'alerta', pendente: 'alerta', aberto: 'alerta',
    atual: 'alerta', aguardando_atendente: 'alerta', enviada: 'info', em_andamento: 'info', em_atendimento: 'info',
    salvo: 'info', disponivel: 'info', bot: 'neutro',
    cancelado: 'erro', inativa: 'erro', inativo: 'erro', vencida: 'erro', recusada: 'erro', expirado: 'erro'
  };

  /* ---------------- estado global ---------------- */
  P.estado = { funcionario: null, saindo: false, fichaAtual: null };

  /* ---------------- utilidades ---------------- */
  P.$ = function (id) { return document.getElementById(id); };

  P.esc = function (valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };
  var esc = P.esc;

  var fMoeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  var fNumero = new Intl.NumberFormat('pt-BR');
  var fDecimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
  var fCompacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });

  P.ehNumero = function (v) { return v !== null && v !== undefined && v !== '' && !isNaN(Number(v)); };
  P.moeda = function (v) { return P.ehNumero(v) ? fMoeda.format(Number(v)) : '—'; };
  P.numero = function (v) { return P.ehNumero(v) ? fNumero.format(Number(v)) : '—'; };
  P.decimal = function (v) { return P.ehNumero(v) ? fDecimal.format(Number(v)) : '—'; };
  P.compacto = function (v) { return P.ehNumero(v) ? fCompacto.format(Number(v)) : '—'; };
  P.dolar = function (v) {
    if (!P.ehNumero(v)) return '—';
    var n = Number(v);
    var casas = n !== 0 && Math.abs(n) < 0.01 ? 4 : 2;
    return 'US$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  };
  P.ou = function (v, padrao) { return (v === null || v === undefined || v === '') ? (padrao === undefined ? '—' : padrao) : v; };

  /** ISO -> Date. Datas puras ficam no fuso local; datetimes sem fuso são UTC. */
  P.paraData = function (valor) {
    if (!valor) return null;
    var texto = String(valor).trim();
    var soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
    if (soData) return new Date(Number(soData[1]), Number(soData[2]) - 1, Number(soData[3]));
    texto = texto.replace(' ', 'T');
    if (/T\d{2}:\d{2}/.test(texto) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(texto)) texto += 'Z';
    var d = new Date(texto);
    return isNaN(d.getTime()) ? null : d;
  };
  P.data = function (valor) { var d = P.paraData(valor); return d ? d.toLocaleDateString('pt-BR') : '—'; };
  P.dataHora = function (valor) {
    if (valor && /^\d{4}-\d{2}-\d{2}$/.test(String(valor))) return P.data(valor);
    var d = P.paraData(valor);
    return d ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
  };
  P.hora = function (valor) {
    var d = P.paraData(valor);
    return d ? d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '';
  };
  P.mesReferencia = function (valor) {
    var m = /^(\d{4})-(\d{2})/.exec(String(valor || ''));
    return m ? MESES[Number(m[2]) - 1] + '/' + m[1] : P.ou(valor);
  };
  P.mesCurto = function (valor) {
    var m = /^(\d{4})-(\d{2})/.exec(String(valor || ''));
    return m ? MESES[Number(m[2]) - 1] + '/' + m[1].slice(2) : String(valor || '');
  };
  P.relativo = function (valor) {
    var d = P.paraData(valor);
    if (!d) return '—';
    var seg = Math.round((Date.now() - d.getTime()) / 1000);
    if (seg < 60) return 'agora';
    if (seg < 3600) return 'há ' + Math.floor(seg / 60) + ' min';
    if (seg < 86400) return 'há ' + Math.floor(seg / 3600) + ' h';
    return 'há ' + Math.floor(seg / 86400) + ' dia(s)';
  };

  function soDigitos(v) { return String(v || '').replace(/\D/g, ''); }
  P.cpf = function (v) {
    var d = soDigitos(v);
    return d.length === 11 ? d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4') : P.ou(v);
  };
  P.telefone = function (v) {
    var d = soDigitos(v);
    if (d.length === 11) return d.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    if (d.length === 10) return d.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    return P.ou(v);
  };
  P.cep = function (v) { var d = soDigitos(v); return d.length === 8 ? d.replace(/(\d{5})(\d{3})/, '$1-$2') : P.ou(v); };
  P.rotulo = function (v) {
    if (v === null || v === undefined || v === '') return '—';
    if (Object.prototype.hasOwnProperty.call(ROTULOS, v)) return ROTULOS[v];
    var t = String(v).replace(/_/g, ' ');
    return t.charAt(0).toUpperCase() + t.slice(1);
  };
  P.selo = function (v, texto) {
    if (v === null || v === undefined || v === '') return '—';
    var tom = Object.prototype.hasOwnProperty.call(TONS, v) ? TONS[v] : 'neutro';
    return '<span class="selo selo-' + tom + '">' + esc(texto || P.rotulo(v)) + '</span>';
  };
  P.seloTom = function (tom, texto) { return '<span class="selo selo-' + esc(tom) + '">' + esc(texto) + '</span>'; };
  P.seloApp = function (origemOuIdApp) {
    return origemOuIdApp && origemOuIdApp !== 'ficticio'
      ? ' <span class="selo selo-app" title="Dados sincronizados com o app">App</span>' : '';
  };
  P.simNao = function (v) { return v ? 'Sim' : 'Não'; };
  P.iniciais = function (nome) {
    var partes = String(nome || '?').trim().split(/\s+/);
    var p = partes[0] ? partes[0].charAt(0) : '?';
    var u = partes.length > 1 ? partes[partes.length - 1].charAt(0) : '';
    return (p + u).toUpperCase();
  };
  P.hashCliente = function (id) { return '#/cliente/' + encodeURIComponent(String(id)); };
  P.pessoa = function (nome, sub, href) {
    var nomeHtml = href ? '<a class="link-linha" href="' + esc(href) + '">' + esc(P.ou(nome)) + '</a>' : '<strong>' + esc(P.ou(nome)) + '</strong>';
    return '<div class="pessoa"><span class="avatar" aria-hidden="true">' + esc(P.iniciais(nome)) + '</span>' +
      '<div class="pessoa-texto">' + nomeHtml + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</div></div>';
  };

  P.htmlVazio = function (msg) { return '<p class="vazio">' + esc(msg) + '</p>'; };
  P.htmlCarregando = function (msg) { return '<p class="carregando" role="status">' + esc(msg || 'Carregando...') + '</p>'; };
  P.htmlErro = function (erro) {
    var msg = (erro && erro.message) ? erro.message : 'Não foi possível carregar os dados.';
    var tipo = erro && erro.status === 403 ? 'alerta' : 'erro';
    return '<div class="aviso aviso-' + tipo + '" role="alert">' + esc(msg) + '</div>';
  };

  /** Larguras/alturas via CSSOM (a CSP não aceita style="" inline). */
  P.aplicarLarguras = function (raiz) {
    var elementos = (raiz || document).querySelectorAll('[data-largura]');
    window.requestAnimationFrame(function () {
      elementos.forEach(function (el) {
        var v = Math.max(0, Math.min(100, Number(el.getAttribute('data-largura')) || 0));
        el.style.width = v + '%';
      });
    });
  };

  P.kpi = function (rotuloTexto, valor, detalhe, cor) {
    return '<div class="kpi kpi-' + (cor || 'azul') + '"><span class="kpi-rotulo">' + esc(rotuloTexto) + '</span>' +
      '<span class="kpi-valor">' + esc(valor) + '</span>' +
      (detalhe ? '<span class="kpi-detalhe">' + esc(detalhe) + '</span>' : '') + '</div>';
  };
  P.cartao = function (titulo, conteudo, sub, extraCabecalho) {
    return '<section class="cartao"><div class="cartao-cabecalho"><div><h2 class="cartao-titulo">' + esc(titulo) + '</h2>' +
      (sub ? '<p class="cartao-sub">' + esc(sub) + '</p>' : '') + '</div>' + (extraCabecalho || '') + '</div>' + conteudo + '</section>';
  };

  /* ---------------- armazenamento ---------------- */
  P.lerSessao = function (k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } };
  P.gravarSessao = function (k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* ignora */ } };
  P.removerSessao = function (k) { try { sessionStorage.removeItem(k); } catch (e) { /* ignora */ } };
  P.lerPreferencia = function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } };
  P.gravarPreferencia = function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignora */ } };

  /* ---------------- sessão e API ---------------- */
  P.sair = function (motivo) {
    if (P.estado.saindo) return;
    P.estado.saindo = true;
    P.removerSessao(P.CHAVE_TOKEN);
    P.removerSessao(P.CHAVE_FUNCIONARIO);
    P.removerSessao(P.CHAVE_CONVERSA);
    window.location.replace('/painel/index.html?sessao=' + encodeURIComponent(motivo || 'encerrada'));
  };

  function ErroApi(code, message, status) {
    this.name = 'ErroApi'; this.code = code; this.message = message; this.status = status;
  }
  ErroApi.prototype = Object.create(Error.prototype);
  ErroApi.prototype.constructor = ErroApi;
  P.ErroApi = ErroApi;

  /** Aceita {"error": {...}}, {"detail": {"error": {...}}}, {"detail": "texto"} e o 422 do FastAPI. */
  P.extrairErro = function (dados, status) {
    var erro = null;
    if (dados && dados.error) erro = dados.error;
    else if (dados && dados.detail && dados.detail.error) erro = dados.detail.error;
    if (erro) return { code: erro.code || 'ERRO', message: erro.message || 'Erro inesperado.' };
    if (dados && typeof dados.detail === 'string') return { code: 'ERRO', message: dados.detail };
    if (status === 422) {
      var primeiro = dados && Array.isArray(dados.detail) && dados.detail[0];
      var campo = primeiro && Array.isArray(primeiro.loc) ? primeiro.loc[primeiro.loc.length - 1] : '';
      return { code: 'DADOS_INVALIDOS', message: 'Dados inválidos' + (campo ? ' no campo "' + campo + '"' : '') + '.' };
    }
    if (status === 404) return { code: 'NAO_ENCONTRADO', message: 'Recurso não encontrado.' };
    if (status >= 500) return { code: 'ERRO_SERVIDOR', message: 'Erro no servidor (' + status + '). Tente novamente.' };
    return { code: 'ERRO', message: 'Erro inesperado (' + status + ').' };
  };

  P.montarQuery = function (params) {
    var busca = new URLSearchParams();
    Object.keys(params || {}).forEach(function (chave) {
      var v = params[chave];
      if (v !== null && v !== undefined && String(v).trim() !== '') busca.append(chave, String(v).trim());
    });
    var texto = busca.toString();
    return texto ? '?' + texto : '';
  };

  /** fetch com token, tempo-limite e erro padronizado. opcoes: {metodo, corpo, tempoLimite}. */
  P.api = async function (caminho, opcoes) {
    opcoes = opcoes || {};
    var headers = { 'Accept': 'application/json' };
    var corpo;
    if (opcoes.corpo !== undefined) { headers['Content-Type'] = 'application/json'; corpo = JSON.stringify(opcoes.corpo); }
    var token = P.lerSessao(P.CHAVE_TOKEN);
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var controle = new AbortController();
    var temporizador = setTimeout(function () { controle.abort(); }, opcoes.tempoLimite || P.TEMPO_LIMITE_PADRAO);
    var resposta;
    try {
      resposta = await fetch(caminho, {
        method: opcoes.metodo || 'GET', headers: headers, body: corpo,
        signal: controle.signal, cache: 'no-store', credentials: 'same-origin'
      });
    } catch (e) {
      clearTimeout(temporizador);
      if (e && e.name === 'AbortError') throw new ErroApi('TEMPO_ESGOTADO', 'O servidor demorou demais para responder. Tente novamente.', 0);
      throw new ErroApi('SEM_CONEXAO', 'Sem conexão com o servidor. Verifique se a API está no ar.', 0);
    }
    clearTimeout(temporizador);
    var dados = null;
    if (resposta.status !== 204) { try { dados = await resposta.json(); } catch (e) { dados = null; } }
    if (resposta.status === 401) {
      P.sair('expirada');
      throw new ErroApi('NAO_AUTENTICADO', 'Sessão expirada. Redirecionando para o login...', 401);
    }
    if (!resposta.ok) {
      var info = P.extrairErro(dados, resposta.status);
      throw new ErroApi(info.code, info.message, resposta.status);
    }
    return dados;
  };

  P.ehAdmin = function () { return !!(P.estado.funcionario && P.estado.funcionario.perfil === 'admin'); };

  /* ---------------- toast ---------------- */
  P.toast = function (mensagem, tipo) {
    var caixa = P.$('toasts');
    if (!caixa) return;
    var t = document.createElement('div');
    t.className = 'toast' + (tipo ? ' toast-' + tipo : '');
    t.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
    t.textContent = mensagem;
    caixa.appendChild(t);
    setTimeout(function () { t.remove(); }, tipo === 'erro' ? 6000 : 3500);
  };
  /** Mostra o erro de uma ação (o 401 já redireciona para o login). */
  P.toastErro = function (erro) {
    if (erro && erro.status === 401) return;
    P.toast((erro && erro.message) || 'Não foi possível concluir a ação.', 'erro');
  };

  /* ---------------- modal ----------------
     P.modal({titulo, html, aoAbrir(caixa, fechar), largo}) -> fechar()
     Fecha com Esc, clique fora ou [data-fechar]. Devolve o foco a quem abriu. */
  P.modal = function (cfg) {
    var anterior = document.activeElement;
    var fundo = document.createElement('div');
    fundo.className = 'modal-fundo';
    fundo.innerHTML = '<div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">' +
      '<div class="modal-cabecalho"><h2 id="modal-titulo">' + esc(cfg.titulo) + '</h2>' +
      '<button type="button" class="botao-icone" data-fechar aria-label="Fechar">' +
      '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>' +
      '</button></div><div class="modal-corpo">' + (cfg.html || '') + '</div></div>';
    var caixa = fundo.querySelector('.modal');
    function fechar() {
      document.removeEventListener('keydown', aoTeclar);
      fundo.remove();
      if (anterior && anterior.focus) anterior.focus();
      if (cfg.aoFechar) cfg.aoFechar();
    }
    function aoTeclar(e) { if (e.key === 'Escape') fechar(); }
    fundo.addEventListener('click', function (e) {
      if (e.target === fundo || e.target.closest('[data-fechar]')) fechar();
    });
    document.addEventListener('keydown', aoTeclar);
    document.body.appendChild(fundo);
    if (cfg.aoAbrir) cfg.aoAbrir(caixa, fechar);
    var foco = caixa.querySelector('input, select, textarea, button:not([data-fechar])');
    if (foco) foco.focus();
    return fechar;
  };

  /** Confirmação no lugar do window.confirm (Promise<boolean>). */
  P.confirmar = function (titulo, texto, rotuloOk, perigo) {
    return new Promise(function (resolver) {
      var respondeu = false;
      P.modal({
        titulo: titulo,
        html: '<p>' + esc(texto) + '</p><div class="formulario-acoes">' +
          '<button type="button" class="botao botao-secundario" data-fechar>Cancelar</button>' +
          '<button type="button" class="botao ' + (perigo ? 'botao-perigo' : 'botao-primario') + '" data-ok>' + esc(rotuloOk || 'Confirmar') + '</button></div>',
        aoAbrir: function (caixa, fecharModal) {
          caixa.querySelector('[data-ok]').addEventListener('click', function () { respondeu = true; fecharModal(); });
        },
        aoFechar: function () { resolver(respondeu); }
      });
    });
  };

  /** Lê um <form> como objeto (campos vazios viram null). */
  P.lerFormulario = function (form) {
    var dados = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled) return;
      if (el.type === 'checkbox') dados[el.name] = el.checked;
      else if (el.type === 'radio') { if (el.checked) dados[el.name] = el.value; }
      else if (el.type === 'number') dados[el.name] = el.value === '' ? null : Number(el.value);
      else dados[el.name] = el.value.trim() === '' ? null : el.value.trim();
    });
    return dados;
  };

  /** Desabilita o botão enquanto a promessa roda. */
  P.comBotao = async function (botao, promessa) {
    if (botao) botao.disabled = true;
    try { return await promessa(); } finally { if (botao) botao.disabled = false; }
  };

  /* ---------------- listas paginadas ---------------- */
  P.normalizarPagina = function (r) {
    if (Array.isArray(r)) return { data: r, pagina: 1, por_pagina: r.length, total: r.length, total_paginas: 1 };
    r = r || {};
    var dados = Array.isArray(r.data) ? r.data : [];
    return {
      data: dados,
      pagina: Math.max(1, Number(r.pagina) || 1),
      por_pagina: Number(r.por_pagina) || dados.length,
      total: P.ehNumero(r.total) ? Number(r.total) : dados.length,
      total_paginas: Math.max(Number(r.total_paginas) || 1, 1)
    };
  };
  P.htmlPaginacao = function (p, unidade) {
    var inicio = p.total ? (p.pagina - 1) * p.por_pagina + 1 : 0;
    var fim = inicio ? inicio + p.data.length - 1 : 0;
    return '<div class="paginacao"><span class="texto-suave">' +
      esc(P.numero(p.total) + ' ' + unidade + (p.total ? ' · ' + P.numero(inicio) + '–' + P.numero(fim) : '')) + '</span>' +
      (p.total_paginas > 1 ? '<div class="paginacao-botoes">' +
        '<button type="button" class="botao botao-secundario botao-pequeno" data-pagina="' + (p.pagina - 1) + '"' + (p.pagina > 1 ? '' : ' disabled') + '>&larr; Anterior</button>' +
        '<span class="texto-suave">Página ' + esc(p.pagina) + ' de ' + esc(p.total_paginas) + '</span>' +
        '<button type="button" class="botao botao-secundario botao-pequeno" data-pagina="' + (p.pagina + 1) + '"' + (p.pagina < p.total_paginas ? '' : ' disabled') + '>Próxima &rarr;</button>' +
        '</div>' : '') + '</div>';
  };

  /* ---------------- registro das telas ----------------
     P.tela(nome, {titulo, descricao, menu, admin, montar(secao, parametro, ctx)})
     ctx.aoSair(fn): limpeza ao trocar de tela (timers de polling etc.). */
  P.telas = P.telas || {};
  P.tela = function (nome, definicao) { P.telas[nome] = definicao; };

  P.cabecalhoTela = function (titulo, descricao, acoesHtml) {
    return '<div class="tela-cabecalho"><div><h1 class="tela-titulo" tabindex="-1">' + esc(titulo) + '</h1>' +
      (descricao ? '<p class="tela-descricao">' + esc(descricao) + '</p>' : '') + '</div>' +
      (acoesHtml ? '<div class="tela-acoes">' + acoesHtml + '</div>' : '') + '</div>';
  };
})();
