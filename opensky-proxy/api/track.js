const { handleCorsPreflight, proxyToOpenSky, sendProxied, describeError } = require("./_lib");

module.exports = async function handler(req, res) {
  if (handleCorsPreflight(req, res)) return;

  const { icao24, time } = req.query;
  if (!icao24 || !time) {
    res.status(400).json({ error: "icao24 e time são obrigatórios" });
    return;
  }

  const params = new URLSearchParams({ icao24, time });
  try {
    const resp = await proxyToOpenSky("/tracks/all", params);
    await sendProxied(res, resp);
  } catch (err) {
    res.status(502).json({ error: describeError(err) });
  }
};
