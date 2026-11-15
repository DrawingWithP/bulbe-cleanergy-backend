// ============================================================
// TELAS NOVAS: Entrar, Primeiro acesso, Abrir conta e Indicações
// Usa os contratos da API (BulbeAPI.request) e a navegação do
// final.js (navigateTo / data-nav). Dados digitados pelo usuário
// e vindos da API entram no DOM só por textContent.
// ============================================================
(function () {
  'use strict';

  const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
  const $$ = (seletor, raiz = document) => Array.from(raiz.querySelectorAll(seletor));
  const digitos = (valor) => String(valor || '').replace(/\D/g, '');

  // ------------------------------------------------------------
  // Máscaras e validações
  // ------------------------------------------------------------
  function mascaraCPF(valor) {
    const d = digitos(valor).slice(0, 11);
    return d
      .replace(/^(\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1-$2');
  }

  function mascaraTelefone(valor) {
    const d = digitos(valor).slice(0, 11);
    if (d.length <= 2) return d ? `(${d}` : '';
    if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
    if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }

  function mascaraCEP(valor) {
    const d = digitos(valor).slice(0, 8);
    return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
  }

  function cpfValido(valor) {
    const d = digitos(valor);
    if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
    const digito = (quantidade) => {
      let soma = 0;
      for (let i = 0; i < quantidade; i += 1) soma += Number(d[i]) * (quantidade + 1 - i);
      const resto = (soma * 10) % 11;
      return resto === 10 ? 0 : resto;
    };
    return digito(9) === Number(d[9]) && digito(10) === Number(d[10]);
  }

  const emailValido = (valor) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(valor || '').trim());

  function valorEmReais(texto) {
    const limpo = String(texto || '').replace(/[^\d,.]/g, '');
    if (!limpo) return NaN;
    // "1.234,56" -> 1234.56 ; "250,5" -> 250.5 ; "250.50" -> 250.5
    const normalizado = limpo.includes(',')
      ? limpo.replace(/\./g, '').replace(',', '.')
      : limpo;
    return Number(normalizado);
  }

  const reais = (valor) => Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  function aplicarMascara(input, mascara) {
    input.addEventListener('input', () => {
      input.value = mascara(input.value);
    });
  }

  // ------------------------------------------------------------
  // Mensagens de erro nos formulários
  // ------------------------------------------------------------
  function limparErro(form) {
    const erro = $('.cad-erro', form);
    if (erro) {
      erro.hidden = true;
      erro.textContent = '';
    }
    $$('[aria-invalid="true"]', form).forEach((campo) => campo.removeAttribute('aria-invalid'));
  }

  function mostrarErro(form, mensagem, campo) {
    const erro = $('.cad-erro', form);
    if (erro) {
      erro.textContent = mensagem;
      erro.hidden = false;
    }
    if (campo) {
      campo.setAttribute('aria-invalid', 'true');
      campo.focus();
    }
  }

  // Ao corrigir um campo marcado, o aviso some (volta no próximo envio se ainda houver erro).
  document.addEventListener('input', (evento) => {
    const campo = evento.target;
    if (!(campo instanceof HTMLElement) || campo.getAttribute('aria-invalid') !== 'true') return;
    campo.removeAttribute('aria-invalid');
    const form = campo.closest('form');
    if (form && !$('[aria-invalid="true"]', form)) {
      const erro = $('.cad-erro', form);
      if (erro) erro.hidden = true;
    }
  });

  // Valida uma lista de regras [campo, condição, mensagem]; para na primeira que falhar.
  function validar(form, regras) {
    limparErro(form);
    for (const [campo, ok, mensagem] of regras) {
      if (!ok) {
        mostrarErro(form, mensagem, campo);
        return false;
      }
    }
    return true;
  }

  async function enviando(botao, tarefa) {
    const textoOriginal = botao.textContent;
    botao.disabled = true;
    botao.textContent = 'Aguarde...';
    try {
      return await tarefa();
    } finally {
      botao.disabled = false;
      botao.textContent = textoOriginal;
    }
  }

  function limparHistorico() {
    // history é a pilha de telas do final.js (não o window.history do navegador)
    if (typeof history !== 'undefined' && Array.isArray(history)) history.length = 0;
  }

  // ------------------------------------------------------------
  // Sessão: botão Entrar, menu lateral e "Sair"
  // ------------------------------------------------------------
  const botaoEntrar = $('#screen-inicio .primary-button');
  const itemIndique = $$('#menu-lateral .ml-nav-item').find((item) => item.textContent.trim() === 'Indique e ganhe');
  if (itemIndique) itemIndique.dataset.nav = 'screen-indicacoes';

  const itemSair = document.createElement('button');
  itemSair.type = 'button';
  itemSair.className = 'ml-nav-item ml-nav-sair';
  const iconeSair = document.createElement('img');
  iconeSair.src = 'icons_final/ml-fechar.svg';
  iconeSair.alt = '';
  const textoSair = document.createElement('span');
  textoSair.textContent = 'Sair da conta';
  itemSair.append(iconeSair, textoSair);
  const navMenu = $('#menu-lateral .ml-nav');
  if (navMenu) navMenu.appendChild(itemSair);

  function atualizarSessao() {
    const logado = Boolean(BulbeAPI.sessao.clienteId());
    if (botaoEntrar) botaoEntrar.dataset.nav = logado ? 'screen-status' : 'screen-entrar';
    itemSair.classList.toggle('oculto', !logado);
  }

  itemSair.addEventListener('click', () => {
    BulbeAPI.sessao.sair();
    atualizarSessao();
    $('#menu-lateral').classList.remove('open');
    navigateTo('screen-inicio');
    limparHistorico();
  });

  function irParaConta() {
    navigateTo('screen-status');
    limparHistorico();
  }

  // ------------------------------------------------------------
  // ENTRAR e PRIMEIRO ACESSO (mesmo fluxo: CPF -> código)
  // ------------------------------------------------------------
  function configurarAcesso(tela) {
    const modo = tela.dataset.acesso; // "entrar" | "primeiro-acesso"
    const formCPF = $('[data-passo="cpf"]', tela);
    const formCodigo = $('[data-passo="codigo"]', tela);
    const sucesso = $('[data-passo="sucesso"]', tela);
    const rodape = $('.acs-rodape', tela);
    const inputCPF = $('[name="cpf"]', formCPF);
    const inputCodigo = $('[name="codigo"]', formCodigo);
    let verificacaoId = null;

    aplicarMascara(inputCPF, mascaraCPF);
    inputCodigo.addEventListener('input', () => {
      inputCodigo.value = digitos(inputCodigo.value).slice(0, 6);
    });

    function mostrarPasso(passo) {
      formCPF.classList.toggle('oculto', passo !== 'cpf');
      formCodigo.classList.toggle('oculto', passo !== 'codigo');
      if (sucesso) sucesso.classList.toggle('oculto', passo !== 'sucesso');
      if (rodape) rodape.classList.toggle('oculto', passo === 'sucesso');
    }

    function reiniciar() {
      verificacaoId = null;
      formCPF.reset();
      formCodigo.reset();
      limparErro(formCPF);
      limparErro(formCodigo);
      $('.acs-demo', formCodigo).classList.add('oculto');
      mostrarPasso('cpf');
    }

    formCPF.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      if (!validar(formCPF, [
        [inputCPF, digitos(inputCPF.value).length === 11, 'Digite os 11 números do CPF.'],
        [inputCPF, cpfValido(inputCPF.value), 'Esse CPF não é válido. Confira os números.'],
      ])) return;

      try {
        const resposta = await enviando($('button[type="submit"]', formCPF), () => BulbeAPI.request(
          '/v1/primeiro-acesso/verificacoes',
          { method: 'POST', body: JSON.stringify({ cpf: digitos(inputCPF.value) }) },
        ));
        verificacaoId = resposta.verificacao_id;
        $('[data-campo="destino"]', formCodigo).textContent = resposta.destino_mascarado || 'seu telefone';
        const demo = $('.acs-demo', formCodigo);
        if (resposta.codigo_demonstracao) {
          $('[data-campo="codigo-demo"]', demo).textContent = resposta.codigo_demonstracao;
          demo.classList.remove('oculto');
        } else {
          demo.classList.add('oculto');
        }
        mostrarPasso('codigo');
        inputCodigo.focus();
      } catch (erro) {
        const mensagem = erro.status === 404
          ? 'Não encontramos esse CPF entre os clientes Bulbe. Se ainda não é cliente, abra sua conta.'
          : erro.message;
        mostrarErro(formCPF, mensagem, inputCPF);
      }
    });

    formCodigo.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      if (!validar(formCodigo, [
        [inputCodigo, /^\d{6}$/.test(inputCodigo.value), 'O código tem 6 números.'],
      ])) return;

      try {
        const resposta = await enviando($('button[type="submit"]', formCodigo), () => BulbeAPI.request(
          '/v1/primeiro-acesso/confirmacoes',
          { method: 'POST', body: JSON.stringify({ verificacao_id: verificacaoId, codigo: inputCodigo.value }) },
        ));
        BulbeAPI.sessao.entrar(resposta.cliente_id);
        atualizarSessao();
        if (modo === 'entrar') {
          irParaConta();
          reiniciar();
        } else {
          mostrarPasso('sucesso');
        }
      } catch (erro) {
        if (erro.status === 410 || erro.code === 'CODIGO_JA_UTILIZADO') {
          reiniciar();
          mostrarErro(formCPF, 'Esse código não vale mais. Peça um novo código.', inputCPF);
          return;
        }
        const mensagem = erro.code === 'CODIGO_INVALIDO'
          ? 'Código incorreto. Confira e tente de novo.'
          : erro.message;
        mostrarErro(formCodigo, mensagem, inputCodigo);
      }
    });

    $('[data-acao="trocar-cpf"]', formCodigo).addEventListener('click', reiniciar);

    // "Ir para minha conta" (sucesso do primeiro acesso)
    if (sucesso) {
      $('[data-nav="screen-status"]', sucesso).addEventListener('click', () => {
        setTimeout(() => { limparHistorico(); reiniciar(); }, 0);
      });
    }

    return { reiniciar, sucessoVisivel: () => sucesso && !sucesso.classList.contains('oculto') };
  }

  const acessos = {};
  $$('[data-acesso]').forEach((tela) => { acessos[tela.id] = configurarAcesso(tela); });

  // Preparação síncrona das telas (chamada pelo navigateTo antes de mostrar a tela).
  const preparar = {};
  Object.keys(acessos).forEach((telaId) => {
    preparar[telaId] = () => {
      if (!acessos[telaId].sucessoVisivel()) acessos[telaId].reiniciar();
    };
  });
  window._antesDeMostrar = (telaId) => preparar[telaId]?.();

  // ------------------------------------------------------------
  // ABRIR CONTA (adesão em 3 passos)
  // ------------------------------------------------------------
  (function () {
    const tela = $('#screen-abrir-conta');
    if (!tela) return;
    const passos = $$('form[data-ade-passo]', tela);
    const sucesso = $('[data-ade-passo="sucesso"]', tela);
    const progresso = $('#ade-progresso', tela);
    const campo = (nome) => $(`[name="${nome}"]`, tela);
    let passoAtual = 1;

    aplicarMascara(campo('cpf'), mascaraCPF);
    aplicarMascara(campo('telefone'), mascaraTelefone);
    aplicarMascara(campo('cep'), mascaraCEP);
    campo('numero').addEventListener('input', () => { campo('numero').value = digitos(campo('numero').value).slice(0, 6); });
    campo('numero_instalacao').addEventListener('input', () => {
      campo('numero_instalacao').value = digitos(campo('numero_instalacao').value).slice(0, 20);
    });
    campo('uf').addEventListener('input', () => {
      campo('uf').value = campo('uf').value.replace(/[^a-zA-Z]/g, '').toUpperCase().slice(0, 2);
    });

    const estimativa = $('#ade-estimativa', tela);
    campo('valor_conta_atual').addEventListener('input', () => {
      const valor = valorEmReais(campo('valor_conta_atual').value);
      estimativa.classList.toggle('oculto', !(valor > 0));
      if (valor > 0) $('#ade-estimativa-valor', tela).textContent = reais(valor * 0.15);
    });

    function mostrarPasso(numero) {
      passoAtual = numero;
      passos.forEach((form) => form.classList.toggle('oculto', Number(form.dataset.adePasso) !== numero));
      sucesso.classList.add('oculto');
      progresso.classList.remove('oculto');
      const form = passos[numero - 1];
      $('#ade-passo-num', tela).textContent = String(numero);
      $('#ade-passo-nome', tela).textContent = form.dataset.nome;
      $('#ade-progresso-preenchido', tela).style.width = `${Math.round((numero / 3) * 100)}%`;
      $('[role="progressbar"]', progresso).setAttribute('aria-valuenow', String(numero));
      $('.sim-scroll', tela).scrollTop = 0;
    }

    function reiniciar() {
      passos.forEach((form) => { form.reset(); limparErro(form); });
      estimativa.classList.add('oculto');
      mostrarPasso(1);
    }

    const regras = {
      1: () => [
        [campo('nome'), campo('nome').value.trim().length >= 3, 'Digite o nome completo do titular.'],
        [campo('email'), emailValido(campo('email').value), 'Digite um e-mail válido, como nome@email.com.'],
        [campo('cpf'), cpfValido(campo('cpf').value), 'Esse CPF não é válido. Confira os números.'],
        [campo('telefone'), [10, 11].includes(digitos(campo('telefone').value).length), 'Digite o celular com DDD.'],
      ],
      2: () => [
        [campo('cep'), digitos(campo('cep').value).length === 8, 'O CEP tem 8 números.'],
        [campo('numero'), Number(campo('numero').value) > 0, 'Digite o número do endereço.'],
        [campo('logradouro'), campo('logradouro').value.trim().length >= 4, 'Digite a rua ou avenida.'],
        [campo('bairro'), campo('bairro').value.trim().length >= 3, 'Digite o bairro.'],
        [campo('cidade'), campo('cidade').value.trim().length >= 3, 'Digite a cidade.'],
        [campo('uf'), /^[A-Z]{2}$/.test(campo('uf').value), 'Digite a sigla do estado, como MG.'],
      ],
      3: () => [
        [campo('numero_instalacao'), digitos(campo('numero_instalacao').value).length >= 5,
          'Digite o número da instalação que aparece na conta da CEMIG.'],
        [campo('valor_conta_atual'), valorEmReais(campo('valor_conta_atual').value) > 0,
          'Digite o valor médio da sua conta de luz.'],
      ],
    };

    function dadosDaAdesao() {
      return {
        nome: campo('nome').value.trim(),
        email: campo('email').value.trim(),
        cpf: digitos(campo('cpf').value),
        telefone: digitos(campo('telefone').value),
        cep: digitos(campo('cep').value),
        logradouro: campo('logradouro').value.trim(),
        numero: Number(campo('numero').value),
        bairro: campo('bairro').value.trim(),
        cidade: campo('cidade').value.trim(),
        uf: campo('uf').value.trim().toUpperCase(),
        distribuidora: campo('distribuidora').value,
        numero_instalacao: digitos(campo('numero_instalacao').value),
        valor_conta_atual: Math.round(valorEmReais(campo('valor_conta_atual').value) * 100) / 100,
      };
    }

    passos.forEach((form) => {
      const numero = Number(form.dataset.adePasso);
      form.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        if (!validar(form, regras[numero]())) return;
        if (numero < 3) {
          mostrarPasso(numero + 1);
          return;
        }
        try {
          const adesao = await enviando($('button[type="submit"]', form), () => BulbeAPI.request(
            '/v1/adesoes',
            { method: 'POST', body: JSON.stringify(dadosDaAdesao()) },
          ));
          $('#ade-protocolo', tela).textContent = `#${adesao.id}`;
          passos.forEach((f) => f.classList.add('oculto'));
          progresso.classList.add('oculto');
          sucesso.classList.remove('oculto');
          $('.sim-scroll', tela).scrollTop = 0;
        } catch (erro) {
          const mensagem = erro.code === 'CPF_JA_CADASTRADO'
            ? 'Já existe uma adesão com este CPF. Fale com a Bulbe para acompanhar o pedido.'
            : erro.message;
          mostrarErro(form, mensagem);
        }
      });
      const voltar = $('[data-acao="ade-voltar"]', form);
      if (voltar) voltar.addEventListener('click', () => mostrarPasso(numero - 1));
    });

    $('[data-acao="ade-inicio"]', sucesso).addEventListener('click', () => {
      navigateTo('screen-inicio');
      limparHistorico();
      setTimeout(reiniciar, 300);
    });

    preparar['screen-abrir-conta'] = () => {
      if (!sucesso.classList.contains('oculto')) reiniciar();
    };
  }());

  // ------------------------------------------------------------
  // INDICAÇÕES
  // ------------------------------------------------------------
  (function () {
    const tela = $('#screen-indicacoes');
    if (!tela) return;
    const form = $('#ind-form', tela);
    const lista = $('#ind-lista', tela);
    const avisoSucesso = $('#ind-sucesso', tela);
    const ROTULOS = { pendente: 'Pendente', aderiu: 'Virou cliente', cancelada: 'Cancelada' };

    function iniciais(nome) {
      const partes = String(nome || '').trim().split(/\s+/).filter(Boolean);
      return ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
    }

    function renderizar(indicacoes) {
      const aderiram = indicacoes.filter((i) => i.situacao === 'aderiu');
      $('#ind-total', tela).textContent = String(indicacoes.length);
      $('#ind-aderiram', tela).textContent = String(aderiram.length);
      $('#ind-ganho', tela).textContent = reais(aderiram.reduce((soma, i) => soma + Number(i.bonus || 0), 0))
        .replace(',00', '');

      lista.replaceChildren();
      if (!indicacoes.length) {
        const vazio = document.createElement('li');
        vazio.className = 'ind-vazio';
        vazio.textContent = 'Você ainda não indicou ninguém. Comece pelo formulário acima!';
        lista.appendChild(vazio);
        return;
      }
      indicacoes.slice().reverse().forEach((indicacao) => {
        const item = document.createElement('li');
        item.className = 'ind-item';
        const avatar = document.createElement('span');
        avatar.className = 'ind-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = iniciais(indicacao.nome);
        const texto = document.createElement('div');
        texto.className = 'ind-item-texto';
        const nome = document.createElement('strong');
        nome.textContent = indicacao.nome;
        const contato = document.createElement('span');
        contato.textContent = indicacao.contato;
        texto.append(nome, contato);
        const selo = document.createElement('span');
        const situacao = ROTULOS[indicacao.situacao] ? indicacao.situacao : 'pendente';
        selo.className = `ind-selo ind-selo-${situacao}`;
        selo.textContent = ROTULOS[situacao];
        item.append(avatar, texto, selo);
        lista.appendChild(item);
      });
    }

    async function carregar() {
      const logado = Boolean(BulbeAPI.clienteId());
      $('#ind-sem-login', tela).classList.toggle('oculto', logado);
      $('#ind-conteudo', tela).classList.toggle('oculto', !logado);
      if (!logado) return;
      try {
        renderizar(await BulbeAPI.request(`${BulbeAPI.clientePath()}/indicacoes`));
      } catch (erro) {
        BulbeAPI.report(erro);
      }
    }

    const nome = $('[name="nome"]', form);
    const contato = $('[name="contato"]', form);

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      avisoSucesso.classList.add('oculto');
      const valorContato = contato.value.trim();
      const ehEmail = valorContato.includes('@');
      if (!validar(form, [
        [nome, nome.value.trim().length >= 3, 'Digite o nome do seu amigo.'],
        [contato, ehEmail ? emailValido(valorContato) : [10, 11].includes(digitos(valorContato).length),
          'Digite um e-mail válido ou um WhatsApp com DDD.'],
      ])) return;

      try {
        await enviando($('button[type="submit"]', form), () => BulbeAPI.request('/v1/indicacoes', {
          method: 'POST',
          body: JSON.stringify({
            cliente_id: BulbeAPI.clienteId(),
            nome: nome.value.trim(),
            contato: ehEmail ? valorContato.toLowerCase() : mascaraTelefone(valorContato),
          }),
        }));
        avisoSucesso.textContent = `Pronto! Avisamos você quando ${nome.value.trim().split(/\s+/)[0]} virar cliente Bulbe.`;
        avisoSucesso.classList.remove('oculto');
        form.reset();
        await carregar();
      } catch (erro) {
        const mensagem = erro.code === 'INDICACAO_DUPLICADA'
          ? 'Essa pessoa já foi indicada. Indique outro amigo!'
          : erro.message;
        mostrarErro(form, mensagem, erro.code === 'INDICACAO_DUPLICADA' ? contato : null);
      }
    });

    window._onIndicacoes = () => {
      avisoSucesso.classList.add('oculto');
      limparErro(form);
      carregar();
    };
  }());

  atualizarSessao();
}());
