/* ============================================================
   TELA: Parceiros e cupons (Clube Bulbe / Vantagens do app)
   Cada cliente recebe, por semana, um cupom sorteado deste catálogo
   (o peso aumenta a chance). A carta especial da 5ª semana é sempre
   R$ 50 de desconto na fatura e não depende do catálogo.
   GET /v1/painel/parceiros?apenas_ativos=false · POST/PUT/DELETE /v1/painel/parceiros
   GET/POST/PATCH/DELETE /v1/painel/catalogo-cupons
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;

  function campo(id, rotulo, entrada) { return '<div class="campo"><label for="' + id + '">' + esc(rotulo) + '</label>' + entrada + '</div>'; }

  P.tela('parceiros', {
    titulo: 'Parceiros e cupons',
    descricao: 'Parceiros do Clube Bulbe e os cupons que entram no sorteio semanal da tela Vantagens do app.',
    montar: async function (secao, _p, ctx) {
      var admin = P.ehAdmin();
      secao.innerHTML = P.cabecalhoTela(this.titulo, this.descricao,
        admin ? '<button type="button" class="botao botao-primario" data-acao="novo-parceiro">+ Novo parceiro</button>' : '') +
        '<div class="aviso aviso-info"><strong>Como o app usa:</strong> toda semana cada cliente abre uma carta e ganha um cupom ' +
        '<strong>sorteado</strong> entre os cupons ativos abaixo (sem repetir o da semana anterior). Na 5ª semana seguida a carta é ' +
        '<strong>especial</strong>: sempre R$ 50 de desconto na fatura.</div>' +
        '<div data-alvo="conteudo">' + P.htmlCarregando('Carregando parceiros...') + '</div>';
      var alvo = secao.querySelector('[data-alvo="conteudo"]');
      var parceiros = [];
      var catalogo = [];
      var erroCatalogo = null;

      async function carregar() {
        try {
          var r = await Promise.all([
            P.api('/v1/painel/parceiros?apenas_ativos=false'),
            P.api('/v1/painel/catalogo-cupons').catch(function (e) { return e; })
          ]);
          if (!ctx.ativa()) return;
          parceiros = Array.isArray(r[0]) ? r[0] : [];
          erroCatalogo = Array.isArray(r[1]) ? null : r[1];
          catalogo = Array.isArray(r[1]) ? r[1] : [];
          desenhar();
        } catch (erro) { if (erro.status !== 401) alvo.innerHTML = P.htmlErro(erro); }
      }

      function cupom(m) {
        return '<li class="cupom-linha"><div><strong>' + esc(m.titulo) + '</strong>' +
          '<small>' + esc(m.descricao) + '</small>' +
          '<small>Código ' + esc(m.prefixo_codigo) + '-XXXX · vale ' + esc(m.validade_dias) + ' dias · peso ' + esc(m.peso) + ' · ' + esc(m.tag) + '</small></div>' +
          '<div class="dica-acoes">' + (m.ativo ? P.seloTom('ok', 'No sorteio') : P.seloTom('neutro', 'Pausado')) +
          (admin ? '<button type="button" class="botao botao-fantasma botao-pequeno" data-editar-cupom="' + esc(m.id) + '">Editar</button>' +
            '<button type="button" class="botao botao-fantasma botao-pequeno" data-alternar-cupom="' + esc(m.id) + '">' + (m.ativo ? 'Pausar' : 'Ativar') + '</button>' +
            '<button type="button" class="botao botao-fantasma botao-pequeno" data-excluir-cupom="' + esc(m.id) + '">Excluir</button>' : '') +
          '</div></li>';
      }

      function cartaoParceiro(p) {
        var cupons = p.id_app ? catalogo.filter(function (m) { return m.parceiro_id === p.id_app; }) : [];
        var logo = '<span class="avatar parceiro-logo" aria-hidden="true">' + esc(P.iniciais(p.nome)) + '</span>';
        return '<section class="cartao parceiro-card"><div class="parceiro-topo">' + logo +
          '<div class="pessoa-texto"><h2 class="cartao-titulo">' + esc(p.nome) + '</h2><small class="texto-suave">' + esc(P.ou(p.categoria)) + '</small></div>' +
          '<div class="dica-acoes empurrar">' + (p.ativo ? P.seloTom('ok', 'Ativo') : P.seloTom('erro', 'Inativo')) +
          (p.id_app ? '<span class="selo selo-app">App</span>' : P.seloTom('neutro', 'Fictício')) + '</div></div>' +
          (p.id_app
            ? '<ul class="lista-cupons">' + (cupons.length ? cupons.map(cupom).join('') : '<li>' + P.htmlVazio('Nenhum cupom cadastrado.') + '</li>') + '</ul>' +
              (admin ? '<div class="dica-acoes"><button type="button" class="botao botao-secundario botao-pequeno" data-novo-cupom="' + esc(p.id) + '">+ Novo cupom</button>' +
                '<button type="button" class="botao botao-fantasma botao-pequeno" data-editar-parceiro="' + esc(p.id) + '">Editar parceiro</button>' +
                '<button type="button" class="botao botao-fantasma botao-pequeno" data-alternar-parceiro="' + esc(p.id) + '">' + (p.ativo ? 'Desativar' : 'Reativar') + '</button></div>' : '')
            : '<p class="texto-suave">Parceiro só da base fictícia do painel (não aparece no app). Cadastre pelo botão “Novo parceiro” para ir ao app.</p>') +
          '</section>';
      }

      function desenhar() {
        var ativos = catalogo.filter(function (m) { return m.ativo; }).length;
        var doApp = parceiros.filter(function (p) { return p.id_app; });
        var outros = parceiros.filter(function (p) { return !p.id_app; });
        alvo.innerHTML = '<div class="grade grade-kpi">' +
          P.kpi('Parceiros no app', P.numero(doApp.length), P.numero(doApp.filter(function (p) { return p.ativo; }).length) + ' ativos', 'azul') +
          P.kpi('Cupons no sorteio', P.numero(ativos), P.numero(catalogo.length) + ' cadastrados', 'verde') +
          P.kpi('Carta especial', 'R$ 50', 'desconto fixo na fatura (5ª semana)', 'amarelo') + '</div>' +
          (erroCatalogo ? '<div class="aviso aviso-alerta">Não foi possível ler o catálogo de cupons do app: ' + esc(erroCatalogo.message) + '</div>' : '') +
          '<div class="grade grade-2">' + doApp.map(cartaoParceiro).join('') + '</div>' +
          (outros.length ? '<details class="cartao"><summary class="cartao-titulo">Parceiros da base fictícia (' + outros.length + ')</summary>' +
            '<div class="grade grade-3 espaco-cima">' + outros.map(cartaoParceiro).join('') + '</div></details>' : '');
      }

      function buscarParceiro(id) { return parceiros.find(function (p) { return String(p.id) === String(id); }); }
      function buscarCupom(id) { return catalogo.find(function (m) { return String(m.id) === String(id); }); }

      function formularioParceiro(p) {
        P.modal({
          titulo: p ? 'Editar parceiro' : 'Novo parceiro',
          html: '<form class="formulario">' +
            campo('pa-nome', 'Nome', '<input id="pa-nome" name="nome" required minlength="2" maxlength="100" value="' + esc(p ? p.nome : '') + '">') +
            campo('pa-cat', 'Categoria', '<input id="pa-cat" name="categoria" required minlength="2" maxlength="60" placeholder="Ex.: Farmácia, Banco, Lazer" value="' + esc(p ? p.categoria : '') + '">') +
            campo('pa-logo', 'Logo (caminho no app, opcional)', '<input id="pa-logo" name="logo_url" maxlength="255" placeholder="/icons_final/parceiros/exemplo.png" value="' + esc(p && p.logo_url ? p.logo_url : '') + '">') +
            '<label class="checkbox"><input type="checkbox" name="ativo"' + (!p || p.ativo ? ' checked' : '') + '> Ativo (aparece no app)</label>' +
            '<div class="formulario-acoes"><button type="button" class="botao botao-secundario" data-fechar>Cancelar</button>' +
            '<button type="submit" class="botao botao-primario">' + (p ? 'Salvar' : 'Cadastrar parceiro') + '</button></div></form>',
          aoAbrir: function (caixa, fechar) {
            var form = caixa.querySelector('form');
            form.addEventListener('submit', async function (e) {
              e.preventDefault();
              try {
                await P.comBotao(form.querySelector('[type="submit"]'), function () {
                  return P.api('/v1/painel/parceiros' + (p ? '/' + encodeURIComponent(p.id) : ''), { metodo: p ? 'PUT' : 'POST', corpo: P.lerFormulario(form) });
                });
                fechar();
                P.toast(p ? 'Parceiro atualizado no app.' : 'Parceiro cadastrado no app. Agora cadastre os cupons dele.', 'ok');
                carregar();
              } catch (erro) { P.toastErro(erro); }
            });
          }
        });
      }

      function formularioCupom(parceiro, m) {
        P.modal({
          titulo: m ? 'Editar cupom' : 'Novo cupom · ' + parceiro.nome,
          html: '<form class="formulario">' +
            campo('cu-titulo', 'Título (o que o cliente ganha)', '<input id="cu-titulo" name="titulo" required minlength="3" maxlength="120" placeholder="Ex.: 15% de desconto" value="' + esc(m ? m.titulo : '') + '">') +
            campo('cu-desc', 'Descrição / regras', '<textarea id="cu-desc" name="descricao" required minlength="5" maxlength="300">' + esc(m ? m.descricao : '') + '</textarea>') +
            '<div class="linha">' +
              campo('cu-pref', 'Prefixo do código', '<input id="cu-pref" name="prefixo_codigo" required pattern="[A-Z0-9]{3,12}" maxlength="12" placeholder="ARAUJO15" value="' + esc(m ? m.prefixo_codigo : '') + '">') +
              campo('cu-tag', 'Etiqueta', '<input id="cu-tag" name="tag" required minlength="3" maxlength="60" value="' + esc(m ? m.tag : 'PARCERIA BULBE') + '">') +
            '</div><div class="linha">' +
              campo('cu-val', 'Validade (dias)', '<input id="cu-val" name="validade_dias" type="number" min="1" max="90" required value="' + esc(m ? m.validade_dias : 14) + '">') +
              campo('cu-peso', 'Peso no sorteio (1 a 10)', '<input id="cu-peso" name="peso" type="number" min="1" max="10" required value="' + esc(m ? m.peso : 1) + '">') +
            '</div><label class="checkbox"><input type="checkbox" name="ativo"' + (!m || m.ativo ? ' checked' : '') + '> Participa do sorteio</label>' +
            '<p class="texto-suave">O código entregue ao cliente é o prefixo + 4 caracteres aleatórios (ex.: ARAUJO15-7KQ2).</p>' +
            '<div class="formulario-acoes"><button type="button" class="botao botao-secundario" data-fechar>Cancelar</button>' +
            '<button type="submit" class="botao botao-primario">' + (m ? 'Salvar' : 'Cadastrar cupom') + '</button></div></form>',
          aoAbrir: function (caixa, fechar) {
            var form = caixa.querySelector('form');
            var prefixo = form.querySelector('[name="prefixo_codigo"]');
            prefixo.addEventListener('input', function () { prefixo.value = prefixo.value.toUpperCase().replace(/[^A-Z0-9]/g, ''); });
            form.addEventListener('submit', async function (e) {
              e.preventDefault();
              var dados = P.lerFormulario(form);
              if (!m) dados.parceiro_id = parceiro.id;
              try {
                await P.comBotao(form.querySelector('[type="submit"]'), function () {
                  return P.api('/v1/painel/catalogo-cupons' + (m ? '/' + encodeURIComponent(m.id) : ''), { metodo: m ? 'PATCH' : 'POST', corpo: dados });
                });
                fechar();
                P.toast(m ? 'Cupom atualizado.' : 'Cupom cadastrado: já entra no sorteio da próxima carta.', 'ok');
                carregar();
              } catch (erro) { P.toastErro(erro); }
            });
          }
        });
      }

      secao.addEventListener('click', async function (e) {
        var b = e.target.closest('button');
        if (!b || b.disabled) return;
        try {
          if (b.getAttribute('data-acao') === 'novo-parceiro') formularioParceiro(null);
          else if (b.hasAttribute('data-editar-parceiro')) formularioParceiro(buscarParceiro(b.getAttribute('data-editar-parceiro')));
          else if (b.hasAttribute('data-novo-cupom')) formularioCupom(buscarParceiro(b.getAttribute('data-novo-cupom')), null);
          else if (b.hasAttribute('data-editar-cupom')) formularioCupom(null, buscarCupom(b.getAttribute('data-editar-cupom')));
          else if (b.hasAttribute('data-alternar-cupom')) {
            var m = buscarCupom(b.getAttribute('data-alternar-cupom'));
            await P.comBotao(b, function () { return P.api('/v1/painel/catalogo-cupons/' + encodeURIComponent(m.id), { metodo: 'PATCH', corpo: { ativo: !m.ativo } }); });
            P.toast(m.ativo ? 'Cupom pausado: sai do sorteio.' : 'Cupom ativado: volta ao sorteio.', 'ok');
            carregar();
          } else if (b.hasAttribute('data-excluir-cupom')) {
            var c = buscarCupom(b.getAttribute('data-excluir-cupom'));
            if (!(await P.confirmar('Excluir cupom', 'Excluir “' + c.titulo + '” do catálogo? Cupons já entregues aos clientes continuam valendo.', 'Excluir', true))) return;
            await P.api('/v1/painel/catalogo-cupons/' + encodeURIComponent(c.id), { metodo: 'DELETE' });
            P.toast('Cupom excluído do catálogo.', 'ok');
            carregar();
          } else if (b.hasAttribute('data-alternar-parceiro')) {
            var p = buscarParceiro(b.getAttribute('data-alternar-parceiro'));
            if (p.ativo && !(await P.confirmar('Desativar parceiro', 'Desativar “' + p.nome + '”? Ele some do app e os cupons dele saem do sorteio.', 'Desativar', true))) return;
            await P.comBotao(b, function () {
              return P.api('/v1/painel/parceiros/' + encodeURIComponent(p.id), {
                metodo: 'PUT', corpo: { nome: p.nome, categoria: p.categoria, logo_url: p.logo_url || null, ativo: !p.ativo }
              });
            });
            P.toast(p.ativo ? 'Parceiro desativado.' : 'Parceiro reativado.', 'ok');
            carregar();
          }
        } catch (erro) { P.toastErro(erro); }
      });

      await carregar();
    }
  });
})();
