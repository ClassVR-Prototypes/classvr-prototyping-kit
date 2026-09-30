/* ClassVR Prototyping Kit — Vercel connection check (kit 0.40.0).
 * Run with javascript_tool on a tab at https://api.vercel.com/v2/user, pasted
 * verbatim. Returns only a state and the username — never the token.
 *   connected      → { state, username }
 *   not-connected  → no token stored in this browser
 *   refused        → a token is stored but Vercel no longer accepts it
 *   wrong-page     → the tab is not on api.vercel.com
 */
await (async function () {
  if (location.origin !== 'https://api.vercel.com') return { state: 'wrong-page' };
  var c = null;
  try { c = JSON.parse(localStorage.getItem('classvr-kit.vercel') || 'null'); } catch (e) { c = null; }
  if (!c || !c.token) return { state: 'not-connected' };
  var r = await fetch('/v2/user', { headers: { Authorization: 'Bearer ' + c.token } });
  if (!r.ok) return { state: 'refused', status: r.status };
  var u = (await r.json()).user || {};
  return { state: 'connected', username: u.username || c.username };
})();
