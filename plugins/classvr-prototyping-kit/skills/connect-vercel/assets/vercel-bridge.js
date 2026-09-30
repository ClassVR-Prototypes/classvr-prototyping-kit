/* ClassVR Prototyping Kit — Vercel bridge (kit 0.40.1, bridge 4).
 *
 * Run in the built-in browser pane on a page of https://api.vercel.com (open
 * https://api.vercel.com/v2/user first — same origin, so no CORS and the token
 * stays in that origin's localStorage). It defines window.KV.
 *
 * /connect-vercel pastes this whole file. Every publish script carries the
 * parts it needs, written into it by vercel_payload.py: the core, plus the
 * @part:first block (a first publish) or the @part:deploy block (a deploy),
 * comments left out — visible in full in the script, never fetched from
 * anywhere. (0.39.0 fetched the bridge from the shared library and ran it; a
 * fresh session's permission check rightly refused running downloaded code in
 * the tab that holds the token.) Blocks between @setup-only markers are only
 * in the pasted copy. Checking a publish is live happens on the app's own
 * page (publish_prep.py's live check), so it needs no token and no bridge.
 *
 * The token is typed by the person into KV.setupBox() and lives only in this
 * browser profile's localStorage for api.vercel.com. No function here ever
 * returns it, logs it or puts it in the page, so it never reaches the chat.
 */
window.KV = (function () {
  'use strict';
  var KEY = 'classvr-kit.vercel';
  var VERSION = 4;
  var K = { setupResult: null, version: VERSION };

  function cfg() { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }

  function save(c) { localStorage.setItem(KEY, JSON.stringify(c)); }

  function onVercelApi() { return location.origin === 'https://api.vercel.com'; }

  function need() {
    if (!onVercelApi()) throw new Error('KV: open https://api.vercel.com/v2/user in the browser pane first');
    var c = cfg();
    if (!c || !c.token) throw new Error('KV: not connected — run the connect-vercel skill');
    return c;
  }

  function withTeam(path, c) {
    if (!c.teamId || /[?&](teamId|slug)=/.test(path)) return path;
    return path + (path.indexOf('?') < 0 ? '?' : '&') + 'teamId=' + encodeURIComponent(c.teamId);
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  async function raw(path, opts, token) {
    opts = opts || {};
    var h = { Authorization: 'Bearer ' + token };
    if (opts.body !== undefined) h['Content-Type'] = 'application/json';
    var r = await fetch(path, { method: opts.method || (opts.body !== undefined ? 'POST' : 'GET'), headers: h,
      body: opts.body === undefined ? undefined : (typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body)) });
    var text = await r.text(), body;
    try { body = JSON.parse(text); } catch (e) { body = text; }
    return { status: r.status, ok: r.ok, body: body };
  }

  // Any REST call. path like '/v9/projects/foo'; teamId is added for you.
  async function api(path, opts) { var c = need(); return raw(withTeam(path, c), opts, c.token); }

  async function sha1(s) {
    var b = await crypto.subtle.digest('SHA-1', typeof s === 'string' ? new TextEncoder().encode(s) : s);
    return Array.from(new Uint8Array(b)).map(function (x) { return x.toString(16).padStart(2, '0'); }).join('');
  }

  // What is stored, minus the token.
  function status() {
    var c = cfg();
    if (!c || !c.token) return { connected: false };
    return { connected: true, username: c.username, teamId: c.teamId, teamSlug: c.teamSlug,
             savedAt: c.savedAt, tokenEnds: c.token.slice(-4), bridge: VERSION };
  }
  K.status = status; K.api = api; K.sha1 = sha1;

  // The tab's own page is Vercel's raw "missing authentication token" reply,
  // which looks alarming in the browser panel. Cover it with a calm card.
  function cover() {
    if (!onVercelApi() || !document.body || document.getElementById('kv-cover')) return;
    var d = document.createElement('div'); d.id = 'kv-cover';
    d.innerHTML =
      '<style>#kv-cover{position:fixed;inset:0;background:#f4f6f8;display:flex;align-items:center;justify-content:center;font:16px/1.45 system-ui,Segoe UI,sans-serif;z-index:99998;color:#1e1e1e}' +
      '#kv-cover .c{background:#fff;border:1px solid #dde2e8;border-radius:12px;padding:28px;max-width:440px;width:calc(100% - 32px);box-shadow:0 6px 24px rgba(0,0,0,.08)}' +
      '#kv-cover h1{font-size:20px;margin:0 0 8px}#kv-cover p{margin:0;color:#555}</style>' +
      '<div class="c"><h1>Claude is connecting to Vercel</h1>' +
      '<p>Claude uses this tab to publish your apps. You don’t need to do anything here — you can go back to the chat.</p></div>';
    document.body.appendChild(d);
  }
  cover();
  K.cover = cover;

  /* @setup-only */
  // Check the stored token still works (expired / revoked tokens show up here).
  async function check() {
    var c = need();
    var u = await raw('/v2/user', {}, c.token);
    if (!u.ok) return { ok: false, status: u.status, reason: (u.body && u.body.error && u.body.error.message) || 'token refused' };
    var p = await raw(withTeam('/v9/projects?limit=1', c), {}, c.token);
    return { ok: p.ok, status: p.status, username: u.body.user.username, teamId: c.teamId,
             canSeeProjects: p.ok, reason: p.ok ? null : ((p.body && p.body.error && p.body.error.message) || 'no project access') };
  }

  // Draw a paste box on the page. The person pastes their token and presses
  // Save; the box verifies it and reports in plain words. Poll KV.setupResult.
  function setupBox() {
    if (!onVercelApi()) throw new Error('KV: open https://api.vercel.com/v2/user first');
    var old = document.getElementById('kv-setup'); if (old) old.remove();
    window.KV.setupResult = { state: 'waiting' };
    var d = document.createElement('div'); d.id = 'kv-setup';
    d.innerHTML =
      '<style>#kv-setup{position:fixed;inset:0;background:#f4f6f8;display:flex;align-items:center;justify-content:center;font:16px/1.45 system-ui,Segoe UI,sans-serif;z-index:99999;color:#1e1e1e}' +
      '#kv-setup .c{background:#fff;border:1px solid #dde2e8;border-radius:12px;padding:28px;max-width:440px;width:calc(100% - 32px);box-shadow:0 6px 24px rgba(0,0,0,.08)}' +
      '#kv-setup h1{font-size:20px;margin:0 0 8px}#kv-setup p{margin:0 0 16px;color:#555}' +
      '#kv-setup input{width:100%;box-sizing:border-box;font:15px ui-monospace,Consolas,monospace;padding:10px 12px;border:1px solid #c8cfd8;border-radius:8px}' +
      '#kv-setup button{margin-top:14px;font:600 15px system-ui,sans-serif;padding:10px 18px;border:0;border-radius:8px;background:#1f6feb;color:#fff;cursor:pointer}' +
      '#kv-setup .m{margin-top:14px;min-height:1.4em}#kv-setup .ok{color:#1a7f37}#kv-setup .bad{color:#b42318}</style>' +
      '<div class="c"><h1>Connect your Vercel account</h1>' +
      '<p>Paste the token you just created in Vercel, then press Save. It is kept in this browser only.</p>' +
      '<input id="kv-token" type="password" autocomplete="off" spellcheck="false" placeholder="Paste your token here">' +
      '<button id="kv-save">Save</button><div class="m" id="kv-msg"></div></div>';
    document.body.appendChild(d);
    var msg = d.querySelector('#kv-msg');
    d.querySelector('#kv-save').onclick = async function () {
      var t = d.querySelector('#kv-token').value.trim();
      if (!t) { msg.className = 'm bad'; msg.textContent = 'Paste the token first.'; return; }
      msg.className = 'm'; msg.textContent = 'Checking…';
      try {
        var u = await raw('/v2/user', {}, t);
        if (!u.ok) { msg.className = 'm bad'; msg.textContent = 'Vercel did not accept that token. Check you copied all of it.'; window.KV.setupResult = { state: 'refused', status: u.status }; return; }
        var user = u.body.user, teamId = user.defaultTeamId || null, slug = null;
        var tm = await raw('/v2/teams?limit=20', {}, t);
        var teams = (tm.ok && tm.body.teams) || [];
        if (teams.length) { var pick = teams.find(function (x) { return x.id === teamId; }) || teams[0]; teamId = pick.id; slug = pick.slug; }
        var p = await raw('/v9/projects?limit=1' + (teamId ? '&teamId=' + teamId : ''), {}, t);
        if (!p.ok) { msg.className = 'm bad'; msg.textContent = 'That token can’t see your projects. Make a new one with the scope set to your account.'; window.KV.setupResult = { state: 'no-projects', status: p.status }; return; }
        save({ v: VERSION, token: t, username: user.username, teamId: teamId, teamSlug: slug, teams: teams.length, savedAt: new Date().toISOString() });
        d.querySelector('#kv-token').value = '';
        msg.className = 'm ok'; msg.textContent = 'Connected as ' + user.username + '. You can go back to Claude now.';
        window.KV.setupResult = { state: 'connected', username: user.username, teamId: teamId, teamSlug: slug, teams: teams.length };
      } catch (e) { msg.className = 'm bad'; msg.textContent = 'Something went wrong: ' + e.message; window.KV.setupResult = { state: 'error', error: String(e.message) }; }
    };
    return 'setup box shown';
  }

  function forget() { localStorage.removeItem(KEY); return { connected: false }; }

  // Short history of a project's publishes.
  async function deployments(projectId, limit) {
    var r = await api('/v6/deployments?projectId=' + projectId + '&limit=' + (limit || 5));
    return (r.ok ? r.body.deployments : []).map(function (d) {
      return { id: d.uid, url: d.url, target: d.target, state: d.state, created: new Date(d.created).toISOString() };
    });
  }
  K.check = check; K.setupBox = setupBox; K.forget = forget; K.deployments = deployments;
  /* @end-setup-only */

  /* @part:first */
  // Make sure a project exists (framework: none) and return its public address.
  // Call BEFORE the first build so the page's QR code carries the real address:
  // Vercel shortens long names (e.g. classvr-token-test-scene-lukemosele.vercel.app).
  async function ensureProject(name) {
    var g = await api('/v9/projects/' + encodeURIComponent(name));
    var created = false;
    if (g.status === 404) {
      var c = await api('/v10/projects', { body: { name: name, framework: null } });
      if (!c.ok) return { ok: false, status: c.status, error: c.body && c.body.error };
      g = await api('/v9/projects/' + c.body.id); created = true;
    }
    if (!g.ok) return { ok: false, status: g.status, error: g.body && g.body.error };
    var d = await api('/v9/projects/' + g.body.id + '/domains');
    var doms = ((d.ok && d.body.domains) || []).map(function (x) { return x.name; });
    var pub = doms.filter(function (n) { return /\.vercel\.app$/.test(n); })
                  .sort(function (a, b) { return a.length - b.length; })[0] || null;
    return { ok: true, created: created, projectId: g.body.id, name: g.body.name,
             url: pub ? 'https://' + pub : null, domains: doms };
  }

  // Blob store for play history, created and connected in one call.
  async function createStore(name, projectId) {
    var r = await api('/v1/storage/stores/blob', { body: { name: name, access: 'private', region: 'lhr1', projectId: projectId } });
    var env = await api('/v10/projects/' + projectId + '/env');
    var keys = ((env.ok && env.body.envs) || []).map(function (e) { return e.key; });
    return { ok: r.ok, status: r.status, storeId: r.ok ? r.body.store.id : null,
             tokenSet: keys.indexOf('BLOB_READ_WRITE_TOKEN') >= 0, error: r.ok ? null : r.body && r.body.error };
  }

  // First publish of an app, in one call: work out the project name from the
  // app's slug and the account's username, create the project (or find it
  // again on a re-run), learn its real public address, and give it a play
  // history store — all before the first build, so the first deploy is the
  // only deploy.
  async function firstPublish(slug, opts) {
    opts = opts || {};
    var c = need();
    var user = (c.username || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    var s = String(slug || 'app').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'app';
    var tail = (user ? '-' + user : '') + (opts.suffix ? '-' + opts.suffix : '');
    var room = 63 - 'classvr-'.length - tail.length;
    if (s.length > room) s = s.slice(0, Math.max(1, room)).replace(/-+$/, '');
    var name = opts.name || ('classvr-' + s + tail);
    var p = await ensureProject(name);
    if (!p.ok) return { ok: false, stage: 'project', name: name, status: p.status, error: p.error };
    var host = p.url ? p.url.replace(/^https:\/\//, '').replace(/\.vercel\.app$/, '') : '';
    var expected = !!host && name.indexOf(host) === 0;      // the name, or Vercel's shortened form of it
    var store = { skipped: true };
    if (expected && opts.store !== false) {
      var env = await api('/v10/projects/' + p.projectId + '/env');
      var has = ((env.ok && env.body.envs) || []).some(function (e) { return e.key === 'BLOB_READ_WRITE_TOKEN'; });
      store = has ? { ok: true, existing: true, tokenSet: true } : await createStore(name.slice(0, 24).replace(/-+$/, '') + '-history', p.projectId);
    }
    return { ok: expected, stage: expected ? 'ready' : 'address', name: p.name, created: p.created, projectId: p.projectId,
             url: p.url, expectedAddress: expected, teamId: c.teamId || null, username: c.username, store: store };
  }
  K.ensureProject = ensureProject; K.createStore = createStore; K.firstPublish = firstPublish;
  /* @end-part */

  /* @part:deploy */
  // Deploy. spec = { name, target, projectSettings?, files: [ {file,data} | {file,sha,size} ],
  //                  expect: { '<file>': '<sha1>' } }  — every inline file is checked
  // against expect before anything is sent, so a copying slip can never go live.
  async function deploy(spec) {
    var c = need();
    var files = spec.files.map(function (f) { return f.data !== undefined ? { file: f.file, data: f.data, encoding: 'utf-8' } : f; });
    var expect = spec.expect || {};
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      if (f.data === undefined) continue;
      var got = await sha1(f.data);
      if (!expect[f.file]) return { ok: false, stage: 'check', reason: 'no expected fingerprint for ' + f.file };
      if (got !== expect[f.file]) return { ok: false, stage: 'check', file: f.file, got: got, want: expect[f.file] };
    }
    var body = { name: spec.name, target: spec.target || 'production', files: files };
    if (spec.projectSettings) body.projectSettings = spec.projectSettings;
    if (spec.project) body.project = spec.project;
    var r = await raw(withTeam('/v13/deployments?skipAutoDetectionConfirmation=1', c), { body: body }, c.token);
    // missing_files: Vercel does not hold some fingerprints yet (a new account,
    // or a support file that changed with a kit release). Files named in
    // spec.sources have a public copy with the same bytes (the shared
    // library): fetch it, check its SHA-1, upload it, and deploy again — so
    // this no longer needs a second pass through the chat.
    var uploaded = [];
    if (!r.ok && r.body && r.body.error && r.body.error.code === 'missing_files') {
      var missing = r.body.error.missing || [];
      var names = files.filter(function (f) { return f.sha && missing.indexOf(f.sha) >= 0; }).map(function (f) { return f.file; });
      var src = spec.sources || {};
      var unresolved = names.filter(function (n) { return !src[n]; });
      if (unresolved.length) return { ok: false, stage: 'missing_files', missingFiles: unresolved, missing: missing };
      for (var k = 0; k < names.length; k++) {
        var want = files.filter(function (f) { return f.file === names[k]; })[0];
        var up = await uploadFrom(src[names[k]], want.sha, c);
        if (!up.ok) return { ok: false, stage: 'missing_files', file: names[k], reason: up.reason, missingFiles: names };
        uploaded.push(names[k]);
      }
      r = await raw(withTeam('/v13/deployments?skipAutoDetectionConfirmation=1', c), { body: body }, c.token);
    }
    if (!r.ok) return { ok: false, stage: 'deploy', status: r.status, error: r.body && r.body.error,
                        missingFiles: (r.body && r.body.error && r.body.error.code === 'missing_files')
                          ? files.filter(function (f) { return f.sha && (r.body.error.missing || []).indexOf(f.sha) >= 0; }).map(function (f) { return f.file; })
                          : undefined };
    var id = r.body.id, j = r.body;
    for (var n = 0; n < 60 && ['READY', 'ERROR', 'CANCELED'].indexOf(j.readyState) < 0; n++) {
      await sleep(3000);
      var s = await raw(withTeam('/v13/deployments/' + id, c), {}, c.token);
      if (s.ok) j = s.body;
    }
    return { ok: j.readyState === 'READY', id: id, readyState: j.readyState, projectId: j.projectId,
             alias: j.alias || [], url: j.url, error: j.errorMessage || null, uploaded: uploaded };
  }

  // Fetch a public file, check it is the bytes Vercel is asking for, and
  // upload it so a deploy can reference it by fingerprint.
  async function uploadFrom(url, sha, c) {
    var g = await fetch(url, { cache: 'no-store' });
    if (!g.ok) return { ok: false, reason: 'could not read ' + url + ' (' + g.status + ')' };
    var buf = await g.arrayBuffer();
    if ((await sha1(buf)) !== sha) return { ok: false, reason: url + ' does not match the fingerprint' };
    var u = await fetch(withTeam('/v2/files', c), { method: 'POST', body: buf,
      headers: { Authorization: 'Bearer ' + c.token, 'Content-Type': 'application/octet-stream', 'x-vercel-digest': sha } });
    return { ok: u.ok, reason: u.ok ? null : 'upload refused (' + u.status + ')' };
  }
  K.deploy = deploy; K.uploadFrom = uploadFrom;
  /* @end-part */

  return K;
})();
'KV ready — ' + JSON.stringify(window.KV.status());
