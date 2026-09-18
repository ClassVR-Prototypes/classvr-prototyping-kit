/* kit-relay — the Vercel route's diary delivery.
   Loaded by the slim page right after the kit's diary (window.KIT). Posts the
   diary to /api/log on this same origin, whose function prints it into Vercel's
   runtime log, where the Vercel connector reads it (get_runtime_logs). One
   route for the headset, a desktop browser and a shared link alike — nothing
   for the player to do, no log to fetch. Each post carries only the diary
   entries added since the previous one (`d`), plus the app's state. */
(function () {
  var KIT = window.KIT;
  if (!KIT || typeof KIT.report !== 'function') return;
  var ENDPOINT = '/api/log';
  var session = (KIT.logbook && KIT.logbook().session) || (KIT.mailbox && KIT.mailbox().session)
                || ('s' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7));
  var upTo = 0, seq = 0, lastAt = 0, timer = null, everPresented = false, sent = 0;

  function compact(e) {
    var out = [e.i, e.t, e.kind, e.text];
    if (e.code) out.push(e.code);
    if (e.n) out.push('x' + e.n);
    return out;
  }
  function envelope(reason) {
    var r = KIT.report();
    if (r.presenting) everPresented = true;
    var fresh = (r.diary || []).filter(function (d) { return d.i > upTo; }), dropped = 0;
    if (fresh.length > 40) { dropped = fresh.length - 40; fresh = fresh.slice(-40); }
    if (r.diary && r.diary.length) upTo = r.diary[r.diary.length - 1].i;
    var body = {
      v: 1, session: session, n: ++seq, app: document.title, build: r.build, k: reason, t: r.secondsRunning,
      level: r.errors ? 'error' : (r.flags && r.flags.length) ? 'warning' : 'info',
      st: r.errors ? 'errors' : (r.flags && r.flags.length) ? 'flagged' : (r.sceneLoaded ? 'ok' : 'loading'),
      vr: r.presenting, ev: everPresented, fps: r.fps, c: r.controllers, p: r.presses, tn: r.turns,
      e: r.errors, f: (r.flags || []).length, firstCode: (r.errorList && r.errorList[0] && r.errorList[0].code) || null,
      d: fresh.map(compact)
    };
    if (r.dof) body.dof = r.dof;
    if (r.lock) body.lk = [r.lock.moved, r.lock.held, r.lock.frames];
    if (dropped) body.dropped = dropped;
    if (reason === 'start' || reason === 'boot') {
      body.url = r.url; body.secure = r.secure; body.webxr = r.webxr; body.ua = (navigator.userAgent || '').slice(0, 160);
    }
    return body;
  }
  function send(reason, force) {
    var wait = 2000 - (Date.now() - lastAt);
    if (!force && wait > 0) {                                   // at most one post per 2 s unless forced
      if (!timer) timer = setTimeout(function () { timer = null; send(reason, true); }, wait);
      return;
    }
    lastAt = Date.now();
    var text; try { text = JSON.stringify(envelope(reason)); } catch (e) { return; }
    var done = false;
    if (reason === 'end' && navigator.sendBeacon) {             // the page is going away: fire-and-forget
      try { done = navigator.sendBeacon(ENDPOINT, new Blob([text], { type: 'application/json' })); } catch (e) {}
    }
    if (!done) {
      try { fetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text, keepalive: true }).catch(function () {}); } catch (e) {}
    }
    sent++;
  }
  KIT.on('error', function (entry, count) { send('error', count === 1); });   // first error goes at once
  KIT.on('flag', function () { send('flag', true); });
  KIT.on('checks', function () { send('checks', true); });
  document.addEventListener('enter-vr', function () { setTimeout(function () { send('vr', true); }, 1500); });
  document.addEventListener('exit-vr', function () { send('vr', true); });
  document.addEventListener('visibilitychange', function () { if (document.hidden) send('end', true); });
  window.addEventListener('pagehide', function () { send('end', true); });
  window.addEventListener('load', function () { setTimeout(function () { send('start', true); }, 4000); });
  setInterval(function () { send('beat', true); }, 30000);
  KIT.relay = function () { return { on: true, sent: sent, session: session, endpoint: ENDPOINT }; };
})();
