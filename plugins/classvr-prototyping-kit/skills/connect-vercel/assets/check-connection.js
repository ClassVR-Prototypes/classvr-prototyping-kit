/* ClassVR Prototyping Kit — Vercel connection check (kit 0.49.0).
 * Run with javascript_tool on a tab at https://api.vercel.com/v2/user, pasted
 * verbatim. Returns only a state and the username — never the token.
 *   connected      → { state, username }
 *   not-connected  → no token stored in this browser
 *   refused        → a token is stored but Vercel no longer accepts it, or it
 *                    can no longer reach the projects (seen 2 Oct 2026: the
 *                    account check passed, then publishing was refused)
 *   wrong-page     → the tab is not on api.vercel.com
 */
await (async function () {
  if (location.origin !== 'https://api.vercel.com') return { state: 'wrong-page' };
  if (document.body && !document.getElementById('kv-cover')) {   // hide Vercel's raw reply behind a calm card
    var d = document.createElement('div'); d.id = 'kv-cover';
    d.innerHTML = '<div style="position:fixed;inset:0;background:#f4f6f8;display:flex;align-items:center;justify-content:center;font:16px/1.45 system-ui,Segoe UI,sans-serif;z-index:99998;color:#1e1e1e">'
      + '<div style="background:#fff;border:1px solid #dde2e8;border-radius:12px;padding:28px;max-width:440px;width:calc(100% - 32px);box-shadow:0 6px 24px rgba(0,0,0,.08)">'
      + '<h1 style="font-size:20px;margin:0 0 8px">Claude is connecting to Vercel</h1>'
      + '<p style="margin:0;color:#555">Claude uses this tab to publish your apps. You don’t need to do anything here — you can go back to the chat.</p></div></div>';
    document.body.appendChild(d);
  }
  var c = null;
  try { c = JSON.parse(localStorage.getItem('classvr-kit.vercel') || 'null'); } catch (e) { c = null; }
  if (!c || !c.token) return { state: 'not-connected' };
  var r = await fetch('/v2/user', { headers: { Authorization: 'Bearer ' + c.token } });
  if (!r.ok) return { state: 'refused', status: r.status };
  var u = (await r.json()).user || {};
  var p = await fetch('/v9/projects?limit=1' + (c.teamId ? '&teamId=' + encodeURIComponent(c.teamId) : ''), { headers: { Authorization: 'Bearer ' + c.token } });
  if (!p.ok) return { state: 'refused', status: p.status, reason: 'cannot reach projects' };
  return { state: 'connected', username: u.username || c.username };
})();
