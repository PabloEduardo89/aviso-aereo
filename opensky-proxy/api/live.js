/**
 * Proxy simples pra API pública do adsb.lol (agregador comunitário de ADS-B,
 * mesma família de software do airplanes.live — mesmo formato de resposta,
 * mesmas rotas /point, /callsign, /hex, /reg). Existe porque o adsb.lol não
 * envia cabeçalho Access-Control-Allow-Origin, então o navegador bloqueia a
 * chamada direta (CORS) mesmo sem exigir nenhuma autenticação — diferente do
 * OpenSky (api/_lib.js), aqui não tem client_id/client_secret nenhum, é só
 * repassar a chamada com o cabeçalho de CORS que falta.
 *
 * Usado pela aba "Mapa ao Vivo" desde que o airplanes.live passou a exigir
 * contato/autorização prévia (ver opensky-proxy/README.md).
 */

const { handleCorsPreflight, describeError } = require("./_lib.js");

const ADSBLOL_BASE = "https://api.adsb.lol/v2";

// o adsb.lol bloqueia User-Agent genérico ("User-Agent too generic; include
// valid contact info") — o fetch padrão do Node/Vercel cai nesse bloqueio;
// precisa se identificar com um UA próprio e um jeito de contato
const REQUEST_USER_AGENT = "AvisoAereoApp/1.0 (+https://github.com/PabloEduardo89/aviso-aereo)";

// só deixa passar os formatos de caminho que a aba "Mapa ao Vivo" realmente usa —
// evita que este proxy vire um jeito de bater em qualquer URL através do nosso domínio
const ALLOWED_PATH = new RegExp(
  "^(" +
    "point/-?\\d{1,3}(\\.\\d+)?/-?\\d{1,3}(\\.\\d+)?/\\d{1,3}(\\.\\d+)?" +
    "|callsign/[A-Za-z0-9]{1,10}" +
    "|hex/[0-9a-fA-F]{6}" +
    "|reg/[A-Za-z0-9-]{1,10}" +
    ")$"
);

module.exports = async function handler(req, res) {
  if (handleCorsPreflight(req, res)) return;

  const p = req.query.p;
  if (!p || Array.isArray(p) || !ALLOWED_PATH.test(p)) {
    res.status(400).json({ error: "parâmetro p ausente ou em formato inválido" });
    return;
  }

  try {
    const resp = await fetch(`${ADSBLOL_BASE}/${p}`, {
      headers: { "User-Agent": REQUEST_USER_AGENT },
    });
    const text = await resp.text();
    res.setHeader("Content-Type", "application/json");
    res.status(resp.status).send(text);
  } catch (err) {
    res.status(502).json({ error: describeError(err) });
  }
};
