/* ============================================================
   PAINEL BULBE — assistente interno (chat lateral com streaming)
   POST /v1/painel/chat/stream lido com fetch + ReadableStream (eventos SSE
   inicio/texto/ferramenta/fim/erro), conversas guardadas no servidor
   (conversa_id) e fallback para POST /v1/painel/chat se o stream falhar.
   Somente leitura: o assistente consulta, não altera dados.
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var $ = P.$, esc = P.esc, api = P.api, ehNumero = P.ehNumero, numero = P.numero, dolar = P.dolar,
    ou = P.ou, dataHora = P.dataHora, htmlCarregando = P.htmlCarregando, htmlVazio = P.htmlVazio,
    htmlErro = P.htmlErro, lerSessao = P.lerSessao, gravarSessao = P.gravarSessao,
    removerSessao = P.removerSessao, lerPreferencia = P.lerPreferencia, gravarPreferencia = P.gravarPreferencia,
    sair = P.sair, ErroApi = P.ErroApi, extrairErro = P.extrairErro;

  var CHAVE_CONVERSA = P.CHAVE_CONVERSA;
  var CHAVE_CHAT_ABERTO = P.CHAVE_CHAT_ABERTO;
  var CHAVE_TOKEN = P.CHAVE_TOKEN;
  var MAX_HISTORICO = 20;
  var MAX_MENSAGEM = 2000;
  var TEMPO_LIMITE_CHAT = 120000;
  var TEMPO_INATIVIDADE_STREAM = 90000;

  var estado = { chat: { historico: [], enviando: false, aberto: true, conversaId: null, conversasAbertas: false } };

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
      if (!P.estado.saindo) {
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
    var c = P.estado.fichaAtual;
    if (!c) return;
    abrirChat(false);
    var entrada = $('chat-entrada');
    entrada.value = 'Faça um resumo do cliente ' + (c.nome || '') + ' (id ' + c.id + '): situação da ativação, ' +
      'faturas em aberto ou vencidas, indicações, Clube Bulbe e atendimentos recentes.';
    atualizarContador();
    entrada.focus();
    entrada.setSelectionRange(entrada.value.length, entrada.value.length);
  }

  function ligarEventos() {
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
      if (e.key !== 'Escape' || document.querySelector('.modal-fundo')) return;
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
  }

  function iniciar() {
    ligarEventos();
    atualizarContador();
    carregarSugestoes();
    // Recarregou a página no meio de uma conversa: reabre a conversa guardada no servidor.
    var conversaSalva = lerSessao(CHAVE_CONVERSA);
    if (conversaSalva) abrirConversa(conversaSalva, true);
  }

  P.assistente = { iniciar: iniciar, perguntarSobreCliente: perguntarSobreCliente, abrir: abrirChat };
})();
