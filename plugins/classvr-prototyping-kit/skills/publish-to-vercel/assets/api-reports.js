// /api/reports — the play history this app has kept.
// Every session that reached VR or closed the page left one file in the
// project's Blob store (written by /api/log). This reads them back, newest
// first, long after Vercel's runtime log has rolled over. Fetch it through
// the Vercel connector (web_fetch_vercel_url) — no browser needed.
//
//   /api/reports                     the most recent sessions, one line each
//   /api/reports?limit=50            more of them (default 25, max 200)
//   /api/reports?day=2026-09-21      one day only
//   /api/reports?session=<id>        one session in full, every diary entry
//
// The store is private, so these files are not readable by URL; this function
// is the only way in, and it is read-only.
async function readJson(blob) {
  const { get } = await import('@vercel/blob');
  const r = await get(blob.pathname, { access: 'private' });
  if (!r || r.statusCode !== 200 || !r.stream) return null;
  const chunks = [];
  const reader = r.stream.getReader();
  try {
    for (;;) { const { done, value } = await reader.read(); if (done) break; chunks.push(value); }
  } finally { reader.releaseLock(); }
  let total = 0; for (const c of chunks) total += c.length;
  const flat = new Uint8Array(total); let at = 0;
  for (const c of chunks) { flat.set(c, at); at += c.length; }
  try { return JSON.parse(new TextDecoder().decode(flat)); } catch (e) { return null; }
}

function summarise(r) {
  return {
    session: r.session, at: r.at, app: r.app, build: r.build, seconds: r.t,
    state: r.st, enteredVR: !!r.ev, fps: r.fps, controllers: r.c, presses: r.p,
    errors: r.e, flags: r.f, firstCode: r.firstCode || null, dof: r.dof,
    entries: Array.isArray(r.d) ? r.d.length : 0, ua: r.ua
  };
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' });
  if (!process.env.BLOB_READ_WRITE_TOKEN)
    return res.status(200).json({ ok: false, reason: 'no history store connected to this project', sessions: [] });
  const q = req.query || {};
  const day = typeof q.day === 'string' ? q.day.replace(/[^0-9-]/g, '') : '';
  const wanted = typeof q.session === 'string' ? q.session.replace(/[^A-Za-z0-9_-]/g, '') : '';
  const limit = Math.min(Math.max(parseInt(q.limit, 10) || 25, 1), 200);
  try {
    const { list } = await import('@vercel/blob');
    const { blobs } = await list({ prefix: day ? `reports/${day}/` : 'reports/', limit: 1000 });
    blobs.sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt));
    if (wanted) {
      // the highest-numbered file for that session is the fullest one
      const mine = blobs.filter(b => b.pathname.includes(`/${wanted}-`));
      if (!mine.length) return res.status(404).json({ ok: false, error: 'no such session' });
      mine.sort((a, b) => (parseInt(b.pathname.match(/-(\d+)\.json$/)?.[1] || 0, 10)) -
                          (parseInt(a.pathname.match(/-(\d+)\.json$/)?.[1] || 0, 10)));
      const full = await readJson(mine[0]);
      if (!full) return res.status(502).json({ ok: false, error: 'could not read that session' });
      return res.status(200).json({ ok: true, session: full });
    }
    // one entry per session: the newest file each session left
    const seen = new Set(), picked = [];
    for (const b of blobs) {
      const id = (b.pathname.split('/').pop() || '').replace(/-\d+\.json$/, '');
      if (seen.has(id)) continue;
      seen.add(id); picked.push(b);
      if (picked.length >= limit) break;
    }
    const sessions = [];
    for (const b of picked) {
      const r = await readJson(b);
      if (r) sessions.push(summarise(r));
    }
    return res.status(200).json({ ok: true, total: seen.size, shown: sessions.length, sessions });
  } catch (e) {
    return res.status(500).json({ ok: false, error: String((e && e.message) || e) });
  }
}
