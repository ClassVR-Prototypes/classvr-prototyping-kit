/* mic-access — ask for the microphone once, first thing, and keep it for the
   whole visit (ClassVR Prototyping Kit, recipe "Microphone" in xr-app-rules).

   Why: on the ClassVR headset's browser (Wolvic, Chromium 124) a microphone
   permission is never remembered — not with "remember my choice", not within
   the same page. Every getUserMedia() call shows the prompt again, in the flat
   page and inside VR alike. A stream that was granted keeps working, though,
   including after Enter VR (Mic Test, 29 Sep 2026). So: ask ONCE, at page
   load, and keep that one stream open; never ask from a button press.

   Use: paste this file's text inside a <script> before <a-scene>, put
   <a-entity mic-access></a-entity> inside the scene, then in app code:
     window.KIT_MIC.ready()          true when the mic is open and live
     window.KIT_MIC.record()         start recording → handle, or null if not ready
       handle.stop()                 → Promise<Blob> (audio/webm, Opus)
     window.KIT_MIC.play(blob)       → Promise, plays a recording back
     window.KIT_MIC.stream           the open MediaStream (e.g. for Web Audio)
     scene events: 'mic-ready', 'mic-blocked'
   Everything it does is logged as "[mic] …" diary lines. */
AFRAME.registerComponent('mic-access', {
  schema: {
    askOnLoad: { default: true },     // ask as soon as the page opens
    askInVR:   { default: true },     // not allowed yet when VR starts? ask again (the prompt shows in VR too)
    notice:    { default: true }      // in-scene reminder when VR starts without the mic
  },
  init: function () {
    var self = this, data = this.data, scene = this.el.sceneEl, THREE = AFRAME.THREE;
    var md = navigator.mediaDevices, asking = null, ctx = null;
    function log() { try { console.log.apply(console, ['[mic]'].concat([].slice.call(arguments))); } catch (e) {} }
    function inVR() { return !!(scene.renderer && scene.renderer.xr && scene.renderer.xr.isPresenting); }
    function live() { return !!(MIC.stream && MIC.stream.getAudioTracks().some(function (t) { return t.readyState === 'live'; })); }
    function errText(e) { return e ? (e.name || 'Error') + (e.message ? ': ' + e.message : '') : 'unknown'; }

    var MIC = window.KIT_MIC = {
      state: 'idle',                  // idle | asking | ready | blocked | unsupported
      stream: null, error: null, asks: 0,
      ready: function () { return MIC.state === 'ready' && live(); },
      ask: ask,
      record: function () {
        if (!MIC.ready()) return null;                  // never ask from a press — see the recipe
        var chunks = [], rec;
        try { rec = new MediaRecorder(MIC.stream); } catch (e) { log('recorder failed:', errText(e)); return null; }
        rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        rec.start(200);
        return { stop: function () {
          return new Promise(function (resolve) {
            rec.onstop = function () { resolve(new Blob(chunks, { type: rec.mimeType || 'audio/webm' })); };
            try { rec.stop(); } catch (e) { resolve(new Blob(chunks, { type: 'audio/webm' })); }
          });
        } };
      },
      play: function (blob) {
        var url = URL.createObjectURL(blob), a = new Audio(url);
        a.onended = function () { URL.revokeObjectURL(url); };
        return a.play().catch(function (e) {                    // fall back to Web Audio
          log('audio element would not play:', errText(e), '— using Web Audio');
          var C = window.AudioContext || window.webkitAudioContext; if (!C) throw e;
          ctx = ctx || new C(); if (ctx.state === 'suspended') ctx.resume();
          return blob.arrayBuffer().then(function (b) { return ctx.decodeAudioData(b); }).then(function (buf) {
            var s = ctx.createBufferSource(); s.buffer = buf; s.connect(ctx.destination); s.start();
          });
        });
      }
    };

    // ---- the flat-page button: shown whenever the mic isn't open, hidden in VR ----
    var btn = document.createElement('button');
    btn.type = 'button'; btn.id = 'mic-allow';
    btn.style.cssText = 'position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:10000;' +
      'font:600 20px system-ui,sans-serif;color:#fff;background:#3f7fbf;border:0;border-radius:999px;' +
      'padding:16px 30px;box-shadow:0 3px 10px rgba(0,0,0,.18);cursor:pointer;display:none';
    btn.addEventListener('click', function () { ask('button'); });
    document.body.appendChild(btn);
    function refresh() {
      var show = MIC.state !== 'ready' && MIC.state !== 'unsupported' && !inVR();
      btn.style.display = show ? 'block' : 'none';
      btn.textContent = MIC.state === 'asking' ? 'Allow the microphone when asked…'
        : MIC.state === 'blocked' ? 'Microphone off — tap to ask again' : 'Allow microphone';
    }

    function ask(why) {
      if (asking) return asking;
      if (!md || !md.getUserMedia) {
        MIC.state = 'unsupported'; log('no getUserMedia here (secure page:', !!window.isSecureContext + ')'); refresh();
        return Promise.resolve(false);
      }
      if (live()) { MIC.state = 'ready'; refresh(); return Promise.resolve(true); }
      MIC.state = 'asking'; MIC.asks++; refresh();
      var t0 = performance.now();
      log('asking for the microphone (' + why + ', ' + (inVR() ? 'in VR' : 'before VR') + ')');
      asking = md.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } }).then(function (s) {
        MIC.stream = s; MIC.state = 'ready'; MIC.error = null; asking = null;
        log('microphone open after', Math.round(performance.now() - t0), 'ms (' + (inVR() ? 'in VR' : 'before VR') + ')');
        s.getAudioTracks().forEach(function (t) {
          t.addEventListener('ended', function () { log('microphone track ended'); MIC.state = 'idle'; MIC.stream = null; refresh(); });
          t.addEventListener('mute', function () { log('microphone muted by the system'); });
          t.addEventListener('unmute', function () { log('microphone unmuted'); });
        });
        refresh(); scene.emit('mic-ready'); hideNotice(); return true;
      }, function (e) {
        MIC.state = 'blocked'; MIC.error = errText(e); asking = null;
        log('microphone refused after', Math.round(performance.now() - t0), 'ms:', MIC.error);
        refresh(); scene.emit('mic-blocked', { error: MIC.error }); return false;
      });
      return asking;
    }

    // ---- in-scene reminder (the button is invisible in VR) ----------------------
    var notice = null;
    function showNotice(text) {
      if (!data.notice) return;
      var cam = scene.camera; if (!cam) return;
      if (!notice) {
        var c = document.createElement('canvas'); c.width = 1024; c.height = 256;
        var tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
        notice = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.2),
          new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false }));
        notice.position.set(0, -0.28, -1.2); notice.renderOrder = 9990; notice.userData.c = c; notice.userData.tex = tex;
        cam.add(notice);
      }
      var g = notice.userData.c.getContext('2d');
      g.clearRect(0, 0, 1024, 256); g.fillStyle = 'rgba(31,58,95,0.92)'; g.fillRect(0, 0, 1024, 256);
      g.fillStyle = '#fff'; g.font = 'bold 54px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(text, 512, 128); notice.userData.tex.needsUpdate = true; notice.visible = true;
    }
    function hideNotice() { if (notice) notice.visible = false; }

    scene.addEventListener('enter-vr', function () {
      if (!inVR()) return;                                   // desktop fullscreen, not a headset
      refresh();
      log('entered VR — microphone', MIC.ready() ? 'open' : MIC.state);
      if (MIC.ready()) return;
      if (data.askInVR) { ask('entered VR without it'); showNotice('Allow the microphone when asked'); }
      else showNotice('Microphone is off — leave VR and press Allow microphone');
    });
    scene.addEventListener('exit-vr', function () { hideNotice(); refresh(); });

    refresh();
    if (data.askOnLoad) ask('page load');
  }
});
