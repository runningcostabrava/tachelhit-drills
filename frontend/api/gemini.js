// Egress proxy for the Gemini API.
//
// Render's free-tier shared IP is blocked by Google (HTTP 403 "Sorry"), so the
// backend can't call generativelanguage.googleapis.com directly. It forwards
// its generateContent calls here instead — Vercel's IP is not blocked. The API
// key lives on Vercel (GEMINI_API_KEY); a shared secret (PROXY_SECRET, matched
// by the backend's GEMINI_PROXY_SECRET) keeps this public endpoint from abuse.
//
// Request body: { "model": "gemini-2.5-flash", "payload": { ...generateContent body... } }
// Response: Google's JSON, verbatim, with the same status code.
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }
  const expected = process.env.PROXY_SECRET;
  if (expected && req.headers['x-proxy-secret'] !== expected) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    res.status(500).json({ error: 'GEMINI_API_KEY not configured on the proxy' });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const model = body && body.model;
  const payload = body && body.payload;
  if (!model || !payload) {
    res.status(400).json({ error: 'model and payload are required' });
    return;
  }

  try {
    const r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${key}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
    );
    const text = await r.text();
    res.setHeader('Content-Type', 'application/json');
    res.status(r.status).send(text);
  } catch (e) {
    res.status(502).json({ error: String(e).slice(0, 300) });
  }
}
