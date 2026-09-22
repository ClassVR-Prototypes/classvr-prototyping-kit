// /api/log — the kit's diary receiver on Vercel.
// kit-relay.js in the page POSTs a JSON envelope here. Every post is printed
// as one line in the project's runtime log, tagged [kit-diary], at the level
// the envelope asks for; the Vercel connector reads those lines back
// (get_runtime_logs, query "kit-diary"; get_runtime_errors for the errors).
// Runtime logs are kept for an hour on Hobby and a day on Pro, so the posts
// marked `full` — one when the player leaves VR, one when the page closes —
// are also written to Blob storage, one file per session, never rewritten.
// /api/reports reads those back weeks later. Without a Blob store connected
// to the project the function still works; it just keeps no history.
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') { res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); return res.status(204).end(); }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = { raw: body.slice(0, 2000) }; } }
  if (!body || typeof body !== 'object') body = { raw: String(body).slice(0, 2000) };
  const ua = String(req.headers['user-agent'] || '').slice(0, 160);
  const record = { at: new Date().toISOString(), ua, ...body };
  const line = '[kit-diary] ' + JSON.stringify(record);
  if (body.level === 'error') console.error(line);
  else if (body.level === 'warning') console.warn(line);
  else console.log(line);

  let kept = false;
  if (body.full && process.env.BLOB_READ_WRITE_TOKEN) {
    try {
      const { put } = await import('@vercel/blob');
      const session = String(body.session || 'unknown').replace(/[^A-Za-z0-9_-]/g, '').slice(0, 40) || 'unknown';
      const day = record.at.slice(0, 10);
      const n = Number(body.n) || 0;
      await put(`reports/${day}/${session}-${n}.json`, JSON.stringify(record), {
        access: 'private', contentType: 'application/json',
        addRandomSuffix: false, allowOverwrite: true
      });
      kept = true;
    } catch (e) {
      console.warn('[kit-diary] history not kept: ' + (e && e.message ? e.message : e));
    }
  }
  return res.status(200).json({ ok: true, kept });
}
