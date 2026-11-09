/* Comunicação com os contratos existentes. Não contém regras de negócio ou dados simulados. */
window.BulbeAPI = (() => {
  const config = window.BULBE_CONFIG || {};
  const base = (config.apiBase || '').replace(/\/$/, '');
  const money = n => Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  function report(error) { window.alert(error.message || 'Não foi possível comunicar com a API.'); }
  function clientePath() {
    if (!config.clienteId) throw new Error('Configure um cliente de teste em BULBE_FRONTEND_CLIENTE_ID. O frontend original não possui formulário de login.');
    return '/v1/clientes/' + encodeURIComponent(config.clienteId);
  }
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(base + path, {
        ...options,
        headers: { Accept: 'application/json', ...(options.body ? {'Content-Type':'application/json'} : {}), ...options.headers },
        signal: options.signal || AbortSignal.timeout(15000)
      });
    } catch { throw new Error('Não foi possível comunicar com a API. Verifique a conexão e tente novamente.'); }
    if (response.status === 204) return null;
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = Array.isArray(body?.detail)
        ? body.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('; ')
        : body?.detail;
      const error = new Error(body?.error?.message || detail || `Erro HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    if (body === null) throw new Error('A API retornou uma resposta JSON inválida.');
    return body;
  }
  async function all(path) {
    const items = [];
    for (let page = 1; ; page++) {
      const result = await request(`${path}?limit=100&page=${page}`);
      items.push(...result.data);
      if (items.length >= result.total || !result.data.length) return items;
    }
  }
  const empty = () => ({diaSimulado:0, diaProximaCarta:0, semanaStreak:0, especialPendente:false,
    cartaAtualAberta:false, recompensaAtual:null, cupons:[], cartas:[], parceiros:[], proximaData:null});
  let state = empty();
  let situation = null;
  let opening = null;
  // O contrato de cupons não oferece logo. Reutilizamos somente os assets originais conhecidos.
  function partnerLogo(partner) {
    const name = partner.nome.toLowerCase();
    if (name.includes('livelo')) return 'img_final/van-livelo.svg';
    if (name.includes('inter')) return 'img_final/van-image26.png';
    if (name.includes('ara')) return 'img_final/van-image25.png';
    return 'icons_final/van-carta.svg';
  }
  function adapt(cupom) {
    return {...cupom, empresa:cupom.parceiro.nome, logo:partnerLogo(cupom.parceiro),
      diaExpiracao: ['ativo', 'salvo'].includes(cupom.situacao) ? cupom.dias_restantes : 0,
      dataVencimento: cupom.valido_ate + 'T12:00:00', especial:false};
  }
  async function refresh() {
    const path = clientePath();
    try {
      const [clube, cupons, cartas, parceiros] = await Promise.all([
        request(path + '/clube'), all(path + '/cupons'), all(path + '/cartas'), all('/v1/parceiros')
      ]);
      situation = clube;
      state = {...state, semanaStreak:clube.semanas_sequencia,
        especialPendente:clube.bonus_especial_pendente,
        diaProximaCarta:clube.proxima_carta?.dias_restantes || 0,
        proximaData:clube.proxima_carta?.disponivel_em || null,
        cupons:cupons.map(adapt), cartas, parceiros:parceiros.filter(p => p.ativo)};
      return state;
    } catch (error) {
      state = empty(); situation = null;
      throw error;
    }
  }
  async function abrirCarta() {
    if (opening) return opening;
    opening = (async () => {
      // Reconsultar evita abrir uma carta que foi consumida em outra aba.
      await refresh();
      if (!situation.carta_disponivel || !situation.proxima_carta) throw new Error('Nenhuma carta disponível na API.');
      const result = await request('/v1/cartas/' + encodeURIComponent(situation.proxima_carta.carta_id) + '/abertura', {method:'POST'});
      const reward = adapt(result.cupom);
      state.recompensaAtual = reward; state.cartaAtualAberta = true;
      situation.carta_disponivel = false;
      state.semanaStreak = result.semanas_sequencia;
      state.cupons = [reward, ...state.cupons.filter(c => c.id !== reward.id)];
      return reward;
    })();
    try { return await opening; } finally { opening = null; }
  }
  async function salvarCupom(situacao) {
    const cupom = state.recompensaAtual;
    if (!cupom) throw new Error('Nenhum cupom selecionado.');
    const result = await request('/v1/cupons/' + encodeURIComponent(cupom.id), {method:'PATCH', body:JSON.stringify({situacao})});
    state.recompensaAtual = adapt(result);
    return result;
  }
  const clube = {getState:()=>state, refresh, abrirCarta, salvarCupom,
    selecionarCupom:async id=>{ const cupom = adapt(await request('/v1/cupons/' + encodeURIComponent(id))); state.recompensaAtual = cupom; return cupom; },
    fecharCarta:()=>{state.recompensaAtual=null; state.cartaAtualAberta=false;},
    isCartaDisponivel:()=>!!situation?.carta_disponivel,
    getDiasRestantes:cupom=>cupom.diaExpiracao};
  return {request, clientePath, report, money, escape, partnerLogo, clube};
})();
