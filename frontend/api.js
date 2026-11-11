/*
 * Comunicação com os contratos existentes.
 * Não contém regras de negócio ou dados simulados.
 */

window.BulbeAPI = (() => {
  const config = window.BULBE_CONFIG || {};

  const base = (config.apiBase || "").replace(/\/$/, "");

  const money = (value) => Number(value).toLocaleString(
    "pt-BR",
    {
      style: "currency",
      currency: "BRL",
    },
  );

  const escape = (value) => String(value ?? "").replace(
    /[&<>"']/g,
    (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character],
  );

  function report(error) {
    window.alert(
      error.message
      || "Não foi possível comunicar com a API.",
    );
  }

  function clientePath() {
    if (!config.clienteId) {
      throw new Error(
        "Configure um cliente de teste em "
        + "BULBE_FRONTEND_CLIENTE_ID. "
        + "O frontend original não possui formulário de login.",
      );
    }

    return (
      "/v1/clientes/"
      + encodeURIComponent(config.clienteId)
    );
  }

  async function request(path, options = {}) {
    let response;

    const headers = {
      Accept: "application/json",
      ...(options.body
        ? {"Content-Type": "application/json"}
        : {}),
      ...(options.headers || {}),
    };

    try {
      response = await fetch(
        base + path,
        {
          ...options,
          headers,
          signal: (
            options.signal
            || AbortSignal.timeout(15000)
          ),
        },
      );
    } catch {
      throw new Error(
        "Não foi possível comunicar com a API. "
        + "Verifique a conexão e tente novamente.",
      );
    }

    if (response.status === 204) {
      return null;
    }

    const body = await response
      .json()
      .catch(() => null);

    if (!response.ok) {
      const detail = Array.isArray(body?.detail)
        ? body.detail
          .map(
            (item) => (
              `${item.loc.join(".")}: ${item.msg}`
            ),
          )
          .join("; ")
        : body?.detail;

      const error = new Error(
        body?.error?.message
        || detail
        || `Erro HTTP ${response.status}`,
      );

      error.status = response.status;

      throw error;
    }

    if (body === null) {
      throw new Error(
        "A API retornou uma resposta JSON inválida.",
      );
    }

    return body;
  }

  async function all(path) {
    const items = [];

    for (let page = 1; ; page += 1) {
      const separator = path.includes("?")
        ? "&"
        : "?";

      const result = await request(
        `${path}${separator}limit=100&page=${page}`,
      );

      items.push(...result.data);

      if (
        items.length >= result.total
        || !result.data.length
      ) {
        return items;
      }
    }
  }

  const empty = () => ({
    diaSimulado: 0,
    diaProximaCarta: 0,
    semanaStreak: 0,
    especialPendente: false,
    cartaAtualAberta: false,
    recompensaAtual: null,
    cupons: [],
    cartas: [],
    parceiros: [],
    proximaData: null,
  });

  let state = empty();
  let situation = null;
  let opening = null;

  /*
   * O contrato de cupons não oferece a logo.
   * Por isso, são reutilizados somente os assets
   * originais conhecidos pelo frontend.
   */
  function partnerLogo(partner) {
    const name = partner.nome.toLowerCase();

    if (name.includes("livelo")) {
      return "img_final/van-livelo.svg";
    }

    if (name.includes("inter")) {
      return "img_final/van-image26.png";
    }

    if (name.includes("ara")) {
      return "img_final/van-image25.png";
    }

    return "icons_final/van-carta.svg";
  }

  function adapt(cupom) {
    const situacoesDisponiveis = [
      "ativo",
      "salvo",
    ];

    return {
      ...cupom,
      empresa: cupom.parceiro.nome,
      logo: partnerLogo(cupom.parceiro),
      diaExpiracao: situacoesDisponiveis.includes(
        cupom.situacao,
      )
        ? cupom.dias_restantes
        : 0,
      dataVencimento: (
        `${cupom.valido_ate}T12:00:00`
      ),
      especial: false,
    };
  }

  async function refresh() {
    const path = clientePath();

    try {
      const [
        clube,
        cupons,
        cartas,
        parceiros,
      ] = await Promise.all([
        request(`${path}/clube`),
        all(`${path}/cupons`),
        all(`${path}/cartas`),
        all("/v1/parceiros"),
      ]);

      situation = clube;

      state = {
        ...state,
        semanaStreak: clube.semanas_sequencia,
        especialPendente: (
          clube.bonus_especial_pendente
        ),
        diaProximaCarta: (
          clube.proxima_carta?.dias_restantes
          || 0
        ),
        proximaData: (
          clube.proxima_carta?.disponivel_em
          || null
        ),
        cupons: cupons.map(adapt),
        cartas,
        parceiros: parceiros.filter(
          (partner) => partner.ativo,
        ),
      };

      return state;
    } catch (error) {
      state = empty();
      situation = null;

      throw error;
    }
  }

  async function abrirCarta() {
    if (opening) {
      return opening;
    }

    opening = (async () => {
      /*
       * Reconsulta o estado para evitar abrir
       * uma carta consumida em outra aba.
       */
      await refresh();

      if (
        !situation?.carta_disponivel
        || !situation?.proxima_carta
      ) {
        throw new Error(
          "Nenhuma carta disponível na API.",
        );
      }

      const cartaId = encodeURIComponent(
        situation.proxima_carta.carta_id,
      );

      const result = await request(
        `/v1/cartas/${cartaId}/abertura`,
        {
          method: "POST",
        },
      );

      const reward = adapt(result.cupom);

      state.recompensaAtual = reward;
      state.cartaAtualAberta = true;
      state.semanaStreak = (
        result.semanas_sequencia
      );

      situation.carta_disponivel = false;

      state.cupons = [
        reward,
        ...state.cupons.filter(
          (cupom) => cupom.id !== reward.id,
        ),
      ];

      return reward;
    })();

    try {
      return await opening;
    } finally {
      opening = null;
    }
  }

  async function salvarCupom(situacao) {
    const cupom = state.recompensaAtual;

    if (!cupom) {
      throw new Error(
        "Nenhum cupom selecionado.",
      );
    }

    const cupomId = encodeURIComponent(
      cupom.id,
    );

    const result = await request(
      `/v1/cupons/${cupomId}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          situacao,
        }),
      },
    );

    state.recompensaAtual = adapt(result);

    state.cupons = [
      state.recompensaAtual,
      ...state.cupons.filter(
        (item) => item.id !== result.id,
      ),
    ];

    return result;
  }

  async function selecionarCupom(id) {
    const cupomId = encodeURIComponent(id);

    const cupom = adapt(
      await request(
        `/v1/cupons/${cupomId}`,
      ),
    );

    state.recompensaAtual = cupom;

    return cupom;
  }

  function fecharCarta() {
    state.recompensaAtual = null;
    state.cartaAtualAberta = false;
  }

  const clube = {
    getState: () => state,
    refresh,
    abrirCarta,
    salvarCupom,
    selecionarCupom,
    fecharCarta,
    isCartaDisponivel: () => (
      Boolean(situation?.carta_disponivel)
    ),
    getDiasRestantes: (cupom) => (
      cupom.diaExpiracao
    ),
  };

  return {
    request,
    clientePath,
    report,
    money,
    escape,
    partnerLogo,
    clube,
  };
})();
