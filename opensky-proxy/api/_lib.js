/**
 * Lógica compartilhada pelas rotas do proxy (api/states.js, api/track.js etc).
 * Arquivos prefixados com "_" não viram rota própria no Vercel — só helper.
 *
 * Por que Vercel e não Cloudflare Workers: o servidor de autenticação do
 * OpenSky (auth.opensky-network.org) não responde a conexões vindas da rede
 * de saída do Cloudflare Workers (confirmado: a mesma requisição funciona
 * normalmente fora da rede do Cloudflare, e falha com timeout/522 de dentro
 * de um Worker, mesmo com um User-Agent de navegador). O Vercel roda as
 * funções serverless sobre infraestrutura AWS, com faixa de IP diferente.
 */

const OPENSKY_API_BASE = "https://opensky-network.org/api";
const OPENSKY_TOKEN_URL =
  "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token";
const TOKEN_TTL_MS = 25 * 60 * 1000; // 25 min — o token real do OpenSky dura ~30 min

// cache em memória do container "quente" da função. Não é persistente entre
// instâncias/execuções frias, mas cobre bem o caso comum (poll a cada ~13s
// tende a cair no mesmo container). Ver README.md para upgrade com Vercel KV
// se o tráfego crescer a ponto de valer a pena.
let tokenCache = null; // { accessToken, expiresAt }

function isOriginAllowed(origin, allowedOrigins) {
  if (!origin) return false;
  if (allowedOrigins.includes(origin)) return true;
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

function setCors(req, res) {
  const allowedOrigins = (process.env.ALLOWED_ORIGINS || "https://pabloeduardo89.github.io")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const origin = req.headers.origin;
  if (isOriginAllowed(origin, allowedOrigins)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Vary", "Origin");
}

// retorna true se a resposta já foi enviada (preflight ou método não permitido)
function handleCorsPreflight(req, res) {
  setCors(req, res);
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return true;
  }
  if (req.method !== "GET") {
    res.status(405).json({ error: "method not allowed" });
    return true;
  }
  return false;
}

async function fetchToken() {
  if (tokenCache && tokenCache.expiresAt > Date.now()) return tokenCache.accessToken;
  if (!process.env.OPENSKY_CLIENT_ID || !process.env.OPENSKY_CLIENT_SECRET) {
    throw new Error(
      "OPENSKY_CLIENT_ID/OPENSKY_CLIENT_SECRET não configurados (rode: vercel env add)"
    );
  }
  const body = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: process.env.OPENSKY_CLIENT_ID,
    client_secret: process.env.OPENSKY_CLIENT_SECRET,
  });
  const resp = await fetch(OPENSKY_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  if (!resp.ok) {
    throw new Error(`Falha ao obter token OAuth2 do OpenSky (HTTP ${resp.status})`);
  }
  const json = await resp.json();
  tokenCache = { accessToken: json.access_token, expiresAt: Date.now() + TOKEN_TTL_MS };
  return tokenCache.accessToken;
}

/**
 * Helper genérico: busca `path` na API do OpenSky autenticado. Adicionar uma
 * rota nova no futuro é só chamar isto com outro `path` a partir de um novo
 * arquivo em api/.
 */
async function proxyToOpenSky(path, searchParams) {
  const token = await fetchToken();
  const url = `${OPENSKY_API_BASE}${path}?${searchParams.toString()}`;
  let resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });

  if (resp.status === 401) {
    tokenCache = null;
    const freshToken = await fetchToken();
    resp = await fetch(url, { headers: { Authorization: `Bearer ${freshToken}` } });
  }
  return resp;
}

// undici (fetch do Node/Vercel) costuma jogar um erro genérico "fetch failed"
// com a causa real escondida em err.cause — sem isso, todo problema de rede
// parece igual e não dá pra diagnosticar
function describeError(err) {
  if (!err) return "unknown error";
  let msg = err.message || String(err);
  if (err.cause) {
    msg += ` (cause: ${err.cause.code || ""} ${err.cause.message || err.cause}`.trim() + ")";
  }
  return msg;
}

async function sendProxied(res, resp) {
  const text = await resp.text();
  res.setHeader("Content-Type", "application/json");
  res.status(resp.status).send(text);
}

// gera um handler de rota pronto para /flights/arrival e /flights/departure,
// que só diferem no path do OpenSky e nos parâmetros obrigatórios (iguais)
function makeFlightsHandler(openskyPath) {
  return async function handler(req, res) {
    if (handleCorsPreflight(req, res)) return;
    const { airport, begin, end } = req.query;
    if (!airport || !begin || !end) {
      res.status(400).json({ error: "airport, begin e end são obrigatórios" });
      return;
    }
    const params = new URLSearchParams({ airport, begin, end });
    try {
      const resp = await proxyToOpenSky(openskyPath, params);
      await sendProxied(res, resp);
    } catch (err) {
      res.status(502).json({ error: describeError(err) });
    }
  };
}

module.exports = { handleCorsPreflight, proxyToOpenSky, sendProxied, makeFlightsHandler, describeError };
