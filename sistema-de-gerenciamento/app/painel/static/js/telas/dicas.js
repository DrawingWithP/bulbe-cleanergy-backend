/* ============================================================
   TELA: Dicas — vitrine de 5 (o carrossel do app) + acervo
   Arraste os cards para montar a vitrine; nada muda no app até clicar
   em "Confirmar alterações" (PUT /v1/painel/app/dicas/vitrine, 5 ids na ordem).
   Também dá para usar só o teclado: botões ← → / Tirar / Exibir em cada card.
   GET /v1/painel/app/dicas -> {dicas, icones} · POST/PUT/DELETE /v1/painel/app/dicas
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;
  var TAMANHO = 5;
  var NOMES_ICONES = {
    lampada_led: 'Lâmpada LED', lampada_apagada: 'Lâmpada apagada', chuveiro: 'Chuveiro', maquina_lavar: 'Máquina de lavar',
    cofrinho: 'Cofrinho', geladeira: 'Geladeira', ar_condicionado: 'Ar-condicionado', tomada: 'Tomada',
    televisao: 'Televisão', ferro_passar: 'Ferro de passar', sol: 'Sol', ventilador: 'Ventilador'
  };

  function icone(nome) { return '/painel/icones-dicas/' + encodeURIComponent(nome || 'lampada_led') + '.svg'; }

  P.tela('dicas', {
    titulo: 'Dicas',
    descricao: 'Escolha as 5 dicas de economia que aparecem no app e cadastre novas.',
    montar: async function (secao, _p, ctx) {
      var admin = P.ehAdmin();
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        admin ? '<button type="button" class="botao botao-primario" data-acao="nova">+ Nova dica</button>' : '') +
        '<div data-alvo="conteudo">' + P.htmlCarregando('Carregando dicas do app...') + '</div>';
      var alvo = secao.querySelector('[data-alvo="conteudo"]');

      var dicas = {};
      var icones = Object.keys(NOMES_ICONES);
      var original = [];
      var vitrine = [];

      async function carregar() {
        try {
          var r = await P.api('/v1/painel/app/dicas');
          if (!ctx.ativa()) return;
          dicas = {};
          (r.dicas || []).forEach(function (d) { dicas[d.id] = d; });
          if (Array.isArray(r.icones) && r.icones.length) icones = r.icones;
          original = (r.dicas || []).filter(function (d) { return d.em_exibicao; })
            .sort(function (a, b) { return (a.ordem || 0) - (b.ordem || 0); }).map(function (d) { return d.id; });
          vitrine = original.slice();
          desenhar();
        } catch (erro) {
          if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro) +
            '<p class="texto-suave espaco-cima">As dicas são lidas direto do app: confira se a API do app está no ar.</p>';
        }
      }

      function mudou() { return vitrine.join(',') !== original.join(','); }

      function card(d, posicao) {
        var naVitrine = posicao !== null;
        var acoes = '';
        if (admin) {
          acoes = naVitrine
            ? '<button type="button" class="botao-icone" data-mover="-1" data-id="' + d.id + '" aria-label="Mover para a esquerda"' + (posicao === 0 ? ' disabled' : '') + '>←</button>' +
              '<button type="button" class="botao botao-fantasma botao-pequeno" data-tirar="' + d.id + '">Tirar</button>' +
              '<button type="button" class="botao-icone" data-mover="1" data-id="' + d.id + '" aria-label="Mover para a direita"' + (posicao === vitrine.length - 1 ? ' disabled' : '') + '>→</button>'
            : '<button type="button" class="botao botao-secundario botao-pequeno" data-exibir="' + d.id + '"' + (vitrine.length >= TAMANHO ? ' disabled' : '') + '>Exibir</button>' +
              '<button type="button" class="botao botao-fantasma botao-pequeno" data-editar="' + d.id + '">Editar</button>' +
              '<button type="button" class="botao botao-fantasma botao-pequeno" data-excluir="' + d.id + '">Excluir</button>';
        }
        return '<article class="dica-card" draggable="' + admin + '" data-dica="' + d.id + '" aria-label="' + esc(d.titulo) + '">' +
          (naVitrine ? '<span class="dica-posicao">' + (posicao + 1) + '</span>' : '') +
          '<img src="' + esc(icone(d.icone)) + '" alt="" width="64" height="64">' +
          '<strong>' + esc(d.titulo) + '</strong><small>' + esc(P.moeda(d.economia)) + '/mês</small>' +
          '<small class="dica-descricao">' + esc(d.descricao) + '</small>' +
          (acoes ? '<div class="dica-acoes">' + acoes + '</div>' : '') + '</article>';
      }

      function desenhar() {
        var vagas = '';
        for (var i = vitrine.length; i < TAMANHO; i++) vagas += '<div class="vaga" data-vaga="' + i + '">Arraste uma dica para cá</div>';
        var acervo = Object.keys(dicas).map(Number).filter(function (id) { return vitrine.indexOf(id) === -1; })
          .map(function (id) { return card(dicas[id], null); }).join('');
        var completo = vitrine.length === TAMANHO;
        alvo.innerHTML =
          '<section class="cartao"><div class="cartao-cabecalho"><div><h2 class="cartao-titulo">Vitrine do app <span class="texto-suave">(' + vitrine.length + '/5)</span></h2>' +
          '<p class="cartao-sub">Estas 5 dicas aparecem no carrossel da tela inicial do app, nesta ordem.</p></div>' +
          (completo ? P.seloTom('ok', 'Vitrine completa') : P.seloTom('alerta', 'Faltam ' + (TAMANHO - vitrine.length))) + '</div>' +
          '<div class="vitrine" data-zona="vitrine">' + vitrine.map(function (id, pos) { return card(dicas[id], pos); }).join('') + vagas + '</div></section>' +
          '<section class="cartao"><div class="cartao-cabecalho"><div><h2 class="cartao-titulo">Acervo</h2>' +
          '<p class="cartao-sub">Dicas cadastradas que não estão aparecendo no app. Arraste para a vitrine para exibir.</p></div></div>' +
          '<div class="acervo" data-zona="acervo">' + (acervo || P.htmlVazio('Todas as dicas estão na vitrine.')) + '</div></section>' +
          (admin && mudou() ? '<div class="barra-confirmar" role="status"><span>' +
            (completo ? 'Alterações ainda não enviadas: o app só muda depois de confirmar.' : 'A vitrine precisa ter exatamente 5 dicas para confirmar.') +
            '</span><div class="tela-acoes"><button type="button" class="botao botao-secundario" data-acao="desfazer">Desfazer</button>' +
            '<button type="button" class="botao botao-sucesso" data-acao="confirmar"' + (completo ? '' : ' disabled') + '>Confirmar alterações</button></div></div>' : '') +
          (admin ? '' : '<div class="aviso aviso-info">Somente administradores podem alterar a vitrine e cadastrar dicas.</div>');
      }

      /* ---------- regras de troca (arrastar ou teclado) ---------- */
      function soltar(idArrastado, alvoId, zona) {
        var deVitrine = vitrine.indexOf(idArrastado);
        var posAlvo = alvoId !== null ? vitrine.indexOf(alvoId) : -1;
        if (zona === 'acervo') {
          if (deVitrine !== -1) vitrine.splice(deVitrine, 1);
        } else if (posAlvo !== -1 && posAlvo !== deVitrine) {
          if (deVitrine !== -1) {           // reordenar dentro da vitrine: troca de lugar
            vitrine[deVitrine] = alvoId;
            vitrine[posAlvo] = idArrastado;
          } else {                          // do acervo sobre um card: substitui (o outro volta ao acervo)
            vitrine[posAlvo] = idArrastado;
          }
        } else if (posAlvo === -1 && deVitrine === -1 && vitrine.length < TAMANHO) {
          vitrine.push(idArrastado);        // do acervo para uma vaga livre
        }
        desenhar();
      }

      var arrastado = null;
      alvo.addEventListener('dragstart', function (e) {
        var c = e.target.closest('.dica-card');
        if (!c || !admin) return;
        arrastado = Number(c.getAttribute('data-dica'));
        c.classList.add('arrastando');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(arrastado));
      });
      alvo.addEventListener('dragend', function () {
        arrastado = null;
        alvo.querySelectorAll('.arrastando, .zona-ativa').forEach(function (el) { el.classList.remove('arrastando', 'zona-ativa'); });
      });
      alvo.addEventListener('dragover', function (e) {
        var zona = e.target.closest('[data-zona]');
        if (!zona || arrastado === null) return;
        e.preventDefault();
        alvo.querySelectorAll('.zona-ativa').forEach(function (el) { if (el !== zona) el.classList.remove('zona-ativa'); });
        zona.classList.add('zona-ativa');
      });
      alvo.addEventListener('drop', function (e) {
        var zona = e.target.closest('[data-zona]');
        if (!zona || arrastado === null) return;
        e.preventDefault();
        var sobre = e.target.closest('.dica-card');
        var alvoId = sobre ? Number(sobre.getAttribute('data-dica')) : null;
        soltar(arrastado, alvoId === arrastado ? null : alvoId, zona.getAttribute('data-zona'));
      });

      alvo.addEventListener('click', async function (e) {
        var b = e.target.closest('button');
        if (!b || b.disabled) return;
        if (b.hasAttribute('data-mover')) {
          var id = Number(b.getAttribute('data-id'));
          var i = vitrine.indexOf(id), j = i + Number(b.getAttribute('data-mover'));
          if (j >= 0 && j < vitrine.length) { vitrine[i] = vitrine[j]; vitrine[j] = id; desenhar(); }
        } else if (b.hasAttribute('data-tirar')) {
          vitrine.splice(vitrine.indexOf(Number(b.getAttribute('data-tirar'))), 1); desenhar();
        } else if (b.hasAttribute('data-exibir')) {
          if (vitrine.length < TAMANHO) { vitrine.push(Number(b.getAttribute('data-exibir'))); desenhar(); }
        } else if (b.hasAttribute('data-editar')) {
          abrirFormulario(dicas[Number(b.getAttribute('data-editar'))]);
        } else if (b.hasAttribute('data-excluir')) {
          var d = dicas[Number(b.getAttribute('data-excluir'))];
          if (!(await P.confirmar('Excluir dica', 'Excluir “' + d.titulo + '” do acervo? Esta ação não pode ser desfeita.', 'Excluir', true))) return;
          try {
            await P.api('/v1/painel/app/dicas/' + d.id, { metodo: 'DELETE' });
            P.toast('Dica excluída.', 'ok');
            carregar();
          } catch (erro) { P.toastErro(erro); }
        } else if (b.getAttribute('data-acao') === 'desfazer') {
          vitrine = original.slice(); desenhar();
        } else if (b.getAttribute('data-acao') === 'confirmar') {
          try {
            await P.comBotao(b, function () { return P.api('/v1/painel/app/dicas/vitrine', { metodo: 'PUT', corpo: { dicas: vitrine } }); });
            P.toast('Vitrine atualizada: o app já mostra as novas dicas.', 'ok');
            carregar();
          } catch (erro) { P.toastErro(erro); }
        }
      });

      /* ---------- nova dica / editar ---------- */
      function abrirFormulario(dica) {
        var atual = (dica && dica.icone) || icones[0];
        P.modal({
          titulo: dica ? 'Editar dica' : 'Nova dica',
          html: '<form class="formulario" data-form="dica">' +
            '<div class="campo"><label for="d-titulo">Título</label><input id="d-titulo" name="titulo" required minlength="3" maxlength="100" value="' + esc(dica ? dica.titulo : '') + '"></div>' +
            '<div class="campo"><label for="d-desc">Descrição</label><textarea id="d-desc" name="descricao" required minlength="3" maxlength="250">' + esc(dica ? dica.descricao : '') + '</textarea></div>' +
            '<div class="campo"><label for="d-eco">Economia estimada por mês (R$)</label><input id="d-eco" name="economia" type="number" min="0.01" max="10000" step="0.01" required value="' + esc(dica ? dica.economia : '') + '"></div>' +
            '<fieldset class="campo"><legend class="rotulo">Ícone</legend><div class="seletor-icones">' + icones.map(function (nome) {
              return '<label title="' + esc(NOMES_ICONES[nome] || nome) + '"><input type="radio" name="icone" value="' + esc(nome) + '"' + (nome === atual ? ' checked' : '') + '>' +
                '<img src="' + esc(icone(nome)) + '" alt="' + esc(NOMES_ICONES[nome] || nome) + '" width="52" height="52"></label>';
            }).join('') + '</div></fieldset>' +
            '<div class="formulario-acoes"><button type="button" class="botao botao-secundario" data-fechar>Cancelar</button>' +
            '<button type="submit" class="botao botao-primario">' + (dica ? 'Salvar' : 'Cadastrar dica') + '</button></div></form>',
          aoAbrir: function (caixa, fechar) {
            var form = caixa.querySelector('form');
            form.addEventListener('submit', async function (e) {
              e.preventDefault();
              var dados = P.lerFormulario(form);
              try {
                await P.comBotao(form.querySelector('[type="submit"]'), function () {
                  return P.api('/v1/painel/app/dicas' + (dica ? '/' + dica.id : ''), { metodo: dica ? 'PUT' : 'POST', corpo: dados });
                });
                fechar();
                P.toast(dica ? 'Dica atualizada.' : 'Dica cadastrada no acervo. Arraste para a vitrine para exibir no app.', 'ok');
                carregar();
              } catch (erro) { P.toastErro(erro); }
            });
          }
        });
      }
      var botaoNova = secao.querySelector('[data-acao="nova"]');
      if (botaoNova) botaoNova.addEventListener('click', function () { abrirFormulario(null); });

      await carregar();
    }
  });
})();
