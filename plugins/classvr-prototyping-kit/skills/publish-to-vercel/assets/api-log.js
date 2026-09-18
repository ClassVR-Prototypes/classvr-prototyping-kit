// /api/log — the kit's diary receiver on Vercel.
// kit-relay.js in the page POSTs a JSON envelope here; this prints it as one
// line in the project's runtime log, tagged [kit-diary], at the level the
// envelope asks for. The Vercel connector reads those lines back
// (get_runtime_logs, query "kit-diary"; get_runtime_errors for the errors).
// No storage, no dependencies: retention is Vercel's runtime-log window.
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') { res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); return res.status(204).end(); }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = { raw: body.slice(0, 2000) }; } }
  if (!body || typeof body !== 'object') body = { raw: String(body).slice(0, 2000) };
  const ua = String(req.headers['user-agent'] || '').slice(0, 160);
  const line = '[kit-diary] ' + JSON.stringify({ at: new Date().toISOString(), ua, ...body });
  if (body.level === 'error') console.error(line);
  else if (body.level === 'warning') console.warn(line);
  else console.log(line);
  return res.status(200).json({ ok: true });
}
