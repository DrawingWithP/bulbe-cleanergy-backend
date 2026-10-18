/* ============================================================
   Painel Bulbe — tela de login
   Guarda o token no sessionStorage e segue para /painel/painel.html.
   ============================================================ */
(function () {
  'use strict';

  var CHAVE_TOKEN = 'bulbe_painel_token';
  var CHAVE_FUNCIONARIO = 'bulbe_painel_funcionario';

  var form = document.getElementById('form-login');
  var campoEmail = document.getElementById('login-email');
  var campoSenha = document.getElementById('login-senha');
  var botao = document.getElementById('login-botao');
  var caixaErro = document.getElementById('login-erro');
  var caixaAviso = document.getElementById('login-aviso');

  function lerSessao(chave) {
    try { return sessionStorage.getItem(chave); } catch (e) { return null; }
  }

  function gravarSessao(chave, valor) {
    try { sessionStorage.setItem(chave, valor); return true; } catch (e) { return false; }
  }

  function mostrarErro(texto) {
    caixaErro.textContent = texto;
    caixaErro.hidden = !texto;
  }

  function extrairMensagem(dados, padrao) {
    if (dados && dados.error && dados.error.message) return dados.error.message;
    if (dados && dados.detail) {
      if (dados.detail.error && dados.detail.error.message) return dados.detail.error.message;
      if (typeof dados.detail === 'string') return dados.detail;
    }
    return padrao;
  }

  // Aviso quando o usuário volta por sessão expirada ou logout.
  var params = new URLSearchParams(window.location.search);
  if (params.get('sessao') === 'expirada') {
    caixaAviso.textContent = 'Sua sessão expirou. Entre novamente.';
    caixaAviso.hidden = false;
  } else if (params.get('sessao') === 'encerrada') {
    caixaAviso.textContent = 'Você saiu do painel.';
    caixaAviso.hidden = false;
  }

  // Já logado? Vai direto para o painel (o painel valida o token em /me).
  if (lerSessao(CHAVE_TOKEN) && !params.get('sessao')) {
    window.location.replace('/painel/painel.html');
    return;
  }

  form.addEventListener('submit', async function (evento) {
    evento.preventDefault();
    mostrarErro('');

    var email = campoEmail.value.trim();
    var senha = campoSenha.value;
    if (!email || !senha) {
      mostrarErro('Informe e-mail e senha.');
      (email ? campoSenha : campoEmail).focus();
      return;
    }

    botao.disabled = true;
    botao.textContent = 'Entrando...';
    try {
      var resposta = await fetch('/v1/painel/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ email: email, senha: senha })
      });
      var dados = null;
      try { dados = await resposta.json(); } catch (e) { dados = null; }

      if (!resposta.ok || !dados || !dados.token) {
        var padrao = resposta.status === 401 ? 'E-mail ou senha incorretos.'
          : resposta.status === 422 ? 'Dados de login inválidos.'
          : 'Não foi possível entrar agora. Tente novamente.';
        mostrarErro(extrairMensagem(dados, padrao));
        campoSenha.value = '';
        campoSenha.focus();
        return;
      }

      if (!gravarSessao(CHAVE_TOKEN, dados.token)) {
        mostrarErro('O navegador bloqueou o armazenamento da sessão. Habilite o sessionStorage.');
        return;
      }
      gravarSessao(CHAVE_FUNCIONARIO, JSON.stringify(dados.funcionario || {}));
      window.location.replace('/painel/painel.html');
    } catch (erro) {
      mostrarErro('Sem conexão com o servidor. Verifique se a API está no ar.');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Entrar';
    }
  });
})();
