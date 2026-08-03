const { handleCorsPreflight, proxyToOpenSky, describeError } = require("./_lib");

const STATES_CACHE_TTL_MS = 8 * 1000; // protege a cota (compartilhada por todos os visitantes do site)
const statesCache = new Map(); // bbox arredondado -> { body, status, expiresAt }

// bbox arredondado a ~0.1° (~11km): reduz fragmentação de cache por pequenos
// movimentos de pan/zoom, sem perder precisão relevante pra um mapa de tráfego
function roundedBbox(query) {
  const out = new URLSearchParams();
  for (const key of ["lamin", "lomin", "lamax", "lomax"]) {
    const v = parseFloat(query[key]);
    if (Number.isNaN(v)) return null;
    out.set(key, v.toFixed(1));
  }
  return out;
}

module.exports = async function handler(req, res) {
  if (handleCorsPreflight(req, res)) return;

  const bbox = roundedBbox(req.query);
  if (!bbox) {
    res.status(400).json({ error: "lamin/lomin/lamax/lomax obrigatórios" });
    return;
  }

  const cacheKey = bbox.toString();
  const cached = statesCache.get(cacheKey);
  if (cached && cached.expiresAt > Date.now()) {
    res.setHeader("Content-Type", "application/json");
    res.status(cached.status).send(cached.body);
    return;
  }

  try {
    const resp = await proxyToOpenSky("/states/all", bbox);
    const text = await resp.text();
    if (resp.ok) {
      statesCache.set(cacheKey, { body: text, status: resp.status, expiresAt: Date.now() + STATES_CACHE_TTL_MS });
    }
    res.setHeader("Content-Type", "application/json");
    res.status(resp.status).send(text);
  } catch (err) {
    res.status(502).json({ error: describeError(err) });
  }
};
