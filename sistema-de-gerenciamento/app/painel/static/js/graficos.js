/* ============================================================
   PAINEL BULBE — gráficos em SVG/HTML feitos à mão
   Sem biblioteca externa (a CSP só aceita scripts do próprio painel).
   Cores por classe (serie-N / traco-N / leg-N, N = 1..5) para seguir os tokens do CSS.
   ============================================================ */
(function () {
  'use strict';

  var P = window.Painel;
  var esc = P.esc;
  var G = P.graficos = {};

  function cor(n) { var v = Number(n) || 1; return Math.max(1, Math.min(5, v)); }

  G.legenda = function (itens, formato) {
    return '<div class="legenda">' + itens.map(function (i) {
      return '<span><i class="leg-' + cor(i.cor) + '"></i>' + esc(i.rotulo) +
        (formato ? ' <strong>' + esc(formato(i.valor)) + '</strong>' : '') + '</span>';
    }).join('') + '</div>';
  };

  /** Barras horizontais (HTML). itens: [{rotulo, valor, sub, cor, href}] */
  G.barras = function (itens, opcoes) {
    opcoes = opcoes || {};
    var formato = opcoes.formato || P.numero;
    var maximo = opcoes.total || Math.max.apply(null, itens.map(function (i) { return Number(i.valor) || 0; }).concat([1]));
    return '<ul class="barras">' + itens.map(function (i) {
      var pct = maximo ? (Number(i.valor) || 0) * 100 / maximo : 0;
      var nome = i.href ? '<a href="' + esc(i.href) + '">' + esc(i.rotulo) + '</a>' : esc(i.rotulo);
      return '<li><div class="barras-topo"><span>' + nome + (i.sub ? ' <small>' + esc(i.sub) + '</small>' : '') + '</span>' +
        '<strong>' + esc(formato(i.valor)) + '</strong></div>' +
        '<div class="barra-progresso"><span class="leg-' + cor(i.cor) + '" data-largura="' + pct.toFixed(1) + '"></span></div></li>';
    }).join('') + '</ul>';
  };

  /** Rosca (SVG). itens: [{rotulo, valor, cor}] */
  G.rosca = function (itens, centro, sub) {
    var total = itens.reduce(function (s, i) { return s + (Number(i.valor) || 0); }, 0);
    var raio = 52;
    var circ = 2 * Math.PI * raio;
    var acumulado = 0;
    var fatias = total ? itens.map(function (i) {
      var parte = (Number(i.valor) || 0) / total * circ;
      var html = parte > 0 ? '<circle class="traco-' + cor(i.cor) + '" cx="70" cy="70" r="' + raio + '" fill="none" stroke-width="18"' +
        ' stroke-dasharray="' + parte.toFixed(2) + ' ' + (circ - parte).toFixed(2) + '"' +
        ' stroke-dashoffset="' + (-acumulado).toFixed(2) + '" transform="rotate(-90 70 70)"><title>' +
        esc(i.rotulo + ': ' + P.numero(i.valor)) + '</title></circle>' : '';
      acumulado += parte;
      return html;
    }).join('') : '';
    var descricao = itens.map(function (i) { return i.rotulo + ' ' + P.numero(i.valor); }).join(', ');
    return '<div class="rosca"><svg class="grafico grafico-rosca" viewBox="0 0 140 140" role="img" aria-label="' + esc(descricao) + '">' +
      '<circle cx="70" cy="70" r="' + raio + '" fill="none" stroke-width="18" class="traco-fundo"/>' + fatias +
      '<text x="70" y="70" text-anchor="middle" class="rosca-centro">' + esc(centro) + '</text>' +
      '<text x="70" y="88" text-anchor="middle">' + esc(sub || '') + '</text></svg>' +
      G.legenda(itens, P.numero) + '</div>';
  };

  function escala(maximo) {
    if (maximo <= 0) return { max: 1, passo: 1 };
    var bruto = maximo / 4;
    var potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
    var passo = [1, 2, 2.5, 5, 10].map(function (m) { return m * potencia; }).find(function (p) { return p >= bruto; }) || bruto;
    return { max: passo * 4, passo: passo };
  }

  /** Linhas com área (SVG). series: [{nome, valores, cor}] */
  G.linhas = function (rotulos, series, formato) {
    formato = formato || P.compacto;
    var L = 640, A = 230, esq = 52, dir = 16, topo = 14, base = 30;
    var w = L - esq - dir, h = A - topo - base;
    var todos = [];
    series.forEach(function (s) { todos = todos.concat(s.valores.map(Number)); });
    var e = escala(Math.max.apply(null, todos.concat([0])));
    var n = rotulos.length;
    function x(i) { return esq + (n > 1 ? w * i / (n - 1) : w / 2); }
    function y(v) { return topo + h - (Number(v) || 0) / e.max * h; }
    var grade = '';
    for (var k = 0; k <= 4; k++) {
      var valor = e.passo * k;
      grade += '<line class="grade-linha" x1="' + esq + '" x2="' + (L - dir) + '" y1="' + y(valor).toFixed(1) + '" y2="' + y(valor).toFixed(1) + '"/>' +
        '<text x="' + (esq - 8) + '" y="' + (y(valor) + 4).toFixed(1) + '" text-anchor="end">' + esc(formato(valor)) + '</text>';
    }
    var eixoX = rotulos.map(function (r, i) {
      return '<text x="' + x(i).toFixed(1) + '" y="' + (A - 8) + '" text-anchor="middle">' + esc(r) + '</text>';
    }).join('');
    var desenhos = series.map(function (s) {
      var pontos = s.valores.map(function (v, i) { return x(i).toFixed(1) + ',' + y(v).toFixed(1); });
      var area = 'M' + x(0).toFixed(1) + ',' + y(0).toFixed(1) + ' L' + pontos.join(' L') + ' L' + x(n - 1).toFixed(1) + ',' + y(0).toFixed(1) + ' Z';
      var bolinhas = s.valores.map(function (v, i) {
        return '<circle class="serie-' + cor(s.cor) + '" cx="' + x(i).toFixed(1) + '" cy="' + y(v).toFixed(1) + '" r="4">' +
          '<title>' + esc(rotulos[i] + ' · ' + s.nome + ': ' + formato(v)) + '</title></circle>';
      }).join('');
      return '<path class="area-' + cor(s.cor) + '" d="' + area + '"/>' +
        '<polyline class="traco-' + cor(s.cor) + '" fill="none" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="' + pontos.join(' ') + '"/>' + bolinhas;
    }).join('');
    var descricao = series.map(function (s) {
      return s.nome + ': ' + s.valores.map(function (v, i) { return rotulos[i] + ' ' + formato(v); }).join(', ');
    }).join('; ');
    return '<svg class="grafico" viewBox="0 0 ' + L + ' ' + A + '" role="img" aria-label="' + esc(descricao) + '">' +
      grade + eixoX + desenhos + '</svg>' +
      (series.length > 1 ? G.legenda(series.map(function (s) { return { rotulo: s.nome, cor: s.cor }; })) : '');
  };

  /** Colunas agrupadas (SVG). series: [{nome, valores, cor}] */
  G.colunas = function (rotulos, series, formato) {
    formato = formato || P.numero;
    var L = 640, A = 230, esq = 40, dir = 10, topo = 18, base = 30;
    var w = L - esq - dir, h = A - topo - base;
    var todos = [];
    series.forEach(function (s) { todos = todos.concat(s.valores.map(Number)); });
    var e = escala(Math.max.apply(null, todos.concat([0])));
    var grupo = w / Math.max(rotulos.length, 1);
    var larg = Math.min(26, (grupo * 0.7) / series.length);
    function y(v) { return topo + h - (Number(v) || 0) / e.max * h; }
    var grade = '';
    for (var k = 0; k <= 4; k++) {
      var valor = e.passo * k;
      grade += '<line class="grade-linha" x1="' + esq + '" x2="' + (L - dir) + '" y1="' + y(valor).toFixed(1) + '" y2="' + y(valor).toFixed(1) + '"/>' +
        '<text x="' + (esq - 6) + '" y="' + (y(valor) + 4).toFixed(1) + '" text-anchor="end">' + esc(formato(valor)) + '</text>';
    }
    var barras = rotulos.map(function (r, i) {
      var centro = esq + grupo * i + grupo / 2;
      var inicio = centro - (larg * series.length) / 2;
      return series.map(function (s, j) {
        var v = Number(s.valores[i]) || 0;
        var bx = inicio + j * larg;
        return '<rect class="serie-' + cor(s.cor) + '" x="' + (bx + 1).toFixed(1) + '" y="' + y(v).toFixed(1) + '" width="' + (larg - 2).toFixed(1) +
          '" height="' + Math.max(0, h + topo - y(v)).toFixed(1) + '" rx="3"><title>' + esc(r + ' · ' + s.nome + ': ' + formato(v)) + '</title></rect>' +
          (v ? '<text class="valor" x="' + (bx + larg / 2).toFixed(1) + '" y="' + (y(v) - 4).toFixed(1) + '" text-anchor="middle">' + esc(formato(v)) + '</text>' : '');
      }).join('') + '<text x="' + centro.toFixed(1) + '" y="' + (A - 8) + '" text-anchor="middle">' + esc(r) + '</text>';
    }).join('');
    var descricao = series.map(function (s) {
      return s.nome + ': ' + s.valores.map(function (v, i) { return rotulos[i] + ' ' + formato(v); }).join(', ');
    }).join('; ');
    return '<svg class="grafico" viewBox="0 0 ' + L + ' ' + A + '" role="img" aria-label="' + esc(descricao) + '">' + grade + barras + '</svg>' +
      (series.length > 1 ? G.legenda(series.map(function (s) { return { rotulo: s.nome, cor: s.cor }; })) : '');
  };
})();
