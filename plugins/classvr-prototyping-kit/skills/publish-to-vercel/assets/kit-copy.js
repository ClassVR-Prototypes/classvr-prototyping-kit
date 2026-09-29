/* kit-copy.js — "Make my own copy" on the history page (kit 0.33).

   Inlined into the library's history viewer (history-<ver>.html). Next to
   every version it puts a button that does in the browser what /copy-xr-app
   does in a chat: fetch that version's page, check it against the
   fingerprint in history.json, put the kit's plumbing back inline from the
   library the page names, and hand the person an editable app folder —
   index.html, aframe.min.js, xr-project.json, README.md, CHANGELOG.md (and
   any extra library the app bundles). They connect that folder to a Claude
   Cowork task and carry on with ordinary prompts.

   Saving: one click. Chrome and Edge on a computer open a folder picker and
   write the app folder where the person chooses (showDirectoryPicker);
   browsers without one (Firefox, Safari, phones) get a .zip download.

   This is a port of vercel_build.py --unslim --as-copy and
   appdocs.fork_changelog — keep the three in step (kit 0.33 checked the
   button's folder byte for byte against the chat route's). Everything a Vercel app serves is readable from another site
   (Vercel sends Access-Control-Allow-Origin: * on static files, and the
   library's own vercel.json does for .js/.css).
*/
(function (root) {
  'use strict';

  var BUNDLED_COMMENT = '<!-- Libraries are bundled beside this file, never loaded from a CDN. -->';
  var DOC_IDS = { readme: 'xr-kit-readme', changelog: 'xr-kit-changelog' };
  var CHANGELOG_HEAD = '# Changelog\n\n' +
    'Everything that changed in this app, newest first.\n\n' +
    'The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).\n' +
    "Version numbers are the app's own: version 3 is the third saved version (on\n" +
    'Vercel it stays playable at `/v/3/`). Claude keeps this file up to date as the\n' +
    'app is changed; lines under Unreleased become the next version when it is\n' +
    'published.\n';

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function rstripNl(s) { return s.replace(/\n+$/, ''); }
  function stripNl(s) { return s.replace(/^\n+/, '').replace(/\n+$/, ''); }

  function hex(buf) {
    return Array.prototype.map.call(new Uint8Array(buf), function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
  }
  function sha1(bytes) { return crypto.subtle.digest('SHA-1', bytes).then(hex); }

  function get(url, asBytes) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' → ' + r.status);
      return asBytes ? r.arrayBuffer() : r.text();
    });
  }

  // ------------------------------------------------------------ README / changelog (appdocs.py)

  function extractDocs(page) {
    var d = {};
    Object.keys(DOC_IDS).forEach(function (k) {
      var m = new RegExp('<script type="text/markdown" id="' + DOC_IDS[k] + '">\\n?([\\s\\S]*?)\\n?</script>').exec(page);
      if (m) d[k] = m[1].split('<\\!--').join('<!--').split('<\\/').join('</') + '\n';
    });
    return d;
  }

  function stripDocs(page) {
    Object.keys(DOC_IDS).forEach(function (k) {
      page = page.replace(new RegExp('<script type="text/markdown" id="' + DOC_IDS[k] + '">[\\s\\S]*?</script>\\n?', 'g'), '');
    });
    return page;
  }

  var REF = /^\[[^\]]+\]:\s+\S/;
  var VER = /^##\s+\[([^\]]+)\](.*)$/;

  function splitSections(text) {
    var lines = rstripNl(text || '').split('\n'), refs = [];
    while (lines.length && (REF.test(lines[lines.length - 1]) || (!lines[lines.length - 1].trim() && refs.length))) {
      var l = lines.pop();
      if (l.trim()) refs.unshift(l);
    }
    var head = [], sections = [], cur = null;
    lines.forEach(function (l) {
      if (l.indexOf('## ') === 0) { cur = [l, []]; sections.push(cur); }
      else if (!cur) head.push(l);
      else cur[1].push(l);
    });
    return { head: rstripNl(head.join('\n')), sections: sections.map(function (s) { return [s[0], stripNl(s[1].join('\n'))]; }), refs: refs };
  }

  function forkChangelog(text, url, version, fingerprint, name) {
    url = (url || '').replace(/\/+$/, '').replace(/\/v\/\d+$/, '');
    var what = name ? '"' + name + '" ' : '';
    var fp = fingerprint ? ', fingerprint ' + fingerprint.slice(0, 8) : '';
    var where = url ? '<' + url + '/v/' + version + '/>' : 'the original';
    var entry = '- Made this copy of ' + what + 'version ' + version + ' (' + where + fp + ').';
    var parts = splitSections(text || ''), refmap = {};
    parts.refs.forEach(function (r) { var m = /^\[([^\]]+)\]:\s+(\S+)/.exec(r); if (m) refmap[m[1]] = m[2]; });
    var before = [];
    parts.sections.forEach(function (s) {
      var h = s[0], b = s[1], m = VER.exec(h);
      if (m && m[1].trim().toLowerCase() === 'unreleased') return;
      if (m) {
        var label = m[1].trim(), rest = m[2];
        var link = refmap[label] || (url && /^\d+$/.test(label) ? url + '/v/' + label + '/' : null);
        h = '### ' + (link ? '[Version ' + label + '](' + link + ')' : 'Version ' + label) + rest;
      } else {
        h = '#' + h;
      }
      b = b.split('\n').map(function (l) { return l.charAt(0) === '#' ? '#' + l : l; }).join('\n');
      before.push(h + (b.trim() ? '\n\n' + b : ''));
    });
    var out = rstripNl(CHANGELOG_HEAD) + '\n\n## [Unreleased]\n\n### Added\n\n' + entry + '\n';
    if (before.length) {
      out = rstripNl(out) + '\n\n## Before this copy\n\nThe history of the original app' +
        (url ? ' at <' + url + '/>' : '') + ', up to the version this copy was made from.\n\n' + before.join('\n\n') + '\n';
    }
    return out;
  }

  // ------------------------------------------------------------ the source (vercel_build.py --unslim)

  // getLib(base, name) → Promise<text>. Returns { source, info, kit, name, docs, extraLibs }.
  function unslim(page, getLib) {
    var docs = extractDocs(page);
    page = stripDocs(page);
    var info = {};
    var mm = /<meta name="xr-kit-source" content="([^"]*)">\s*/.exec(page);
    if (mm) {
      mm[1].split(';').forEach(function (part) {
        var i = part.indexOf('=');
        if (i >= 0) info[part.slice(0, i).trim()] = part.slice(i + 1).trim();
      });
      page = page.slice(0, mm.index) + page.slice(mm.index + mm[0].length);
    }
    var ver = info.kit || ((/xr-kit-diary-([0-9a-f]{6,})\.js/.exec(page)) || [])[1];
    if (!ver) return Promise.reject(new Error('not a kit page'));
    var base = info.lib || (((/src="([^"]*)\/xr-kit-diary-/.exec(page)) || [])[1]);
    var names = ['xr-kit-diary-' + ver + '.js', 'xr-kit-' + ver + '.css', 'xr-kit-' + ver + '.js', 'xr-kit-panel-' + ver + '.js'];
    return Promise.all(names.map(function (n) { return getLib(base, n); })).then(function (lib) {
      var diary = rstripNl(lib[0]), css = rstripNl(lib[1]), xrkit = rstripNl(lib[2]),
          panel = rstripNl(lib[3]).split('(shared library)').join('(bundled)');
      function one(re, replacement, what) {
        var m = re.exec(page);
        if (!m) throw new Error('could not find the ' + what + ' reference in this page');
        page = page.slice(0, m.index) + replacement + page.slice(m.index + m[0].length);
      }
      page = page.replace(/\n?<script src="[^"]*\/kit-relay(?:-[0-9a-f]{6,})?\.js"><\/script>/, '');
      page = page.replace(/<meta name="xr-kit-qr" content="[^"]*">\s*/, '');
      page = page.replace(/<script src="[^"]*\/kit-qr(?:-[0-9a-f]{6,})?\.js"><\/script>\n?/, '');
      var v = esc(ver);
      one(new RegExp('<script src="[^"]*/xr-kit-panel-' + v + '\\.js"></script>'), '<script>\n' + panel + '\n</script>', 'status panel');
      one(new RegExp('<script src="[^"]*/xr-kit-' + v + '\\.js"></script>'), '<script>\n' + xrkit + '\n</script>', 'xr-kit component');
      one(new RegExp('<link rel="stylesheet" href="[^"]*/xr-kit-' + v + '\\.css">'), '<style>\n' + css + '\n</style>', 'stylesheet');
      one(/<script src="https:\/\/aframe\.io\/releases\/[^"]+\/aframe\.min\.js"><\/script>/, '<script src="./aframe.min.js"></script>', 'A-Frame');
      one(new RegExp('<script src="[^"]*/xr-kit-diary-' + v + '\\.js"></script>'), '<script>\n' + diary + '\n</script>', 'diary');
      var extra = [];
      page = page.replace(/<script src="https?:\/\/[^"]*\/([A-Za-z0-9._-]+\.js)"><\/script>/g, function (_, n) {
        extra.push(n); return '<script src="./' + n + '"></script>';
      });
      var cm = /<!-- Vercel build:[^>]*-->/.exec(page);
      if (cm) page = page.slice(0, cm.index) + BUNDLED_COMMENT + page.slice(cm.index + cm[0].length);
      var t = /<title>([^<]*)<\/title>/.exec(page);
      return { source: page, info: info, kit: ver, lib: base, docs: docs, extraLibs: extra,
               name: t ? decodeEntities(t[1].trim()) : null };
    });
  }

  function decodeEntities(s) {
    var ta = document.createElement('textarea'); ta.innerHTML = s; return ta.value;
  }

  function slugify(name) { return (name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')) || 'xr-app'; }

  function nowIso() { return new Date().toISOString().replace(/\.\d+Z$/, 'Z'); }

  function manifest(name, source, fork, extraLibs) {
    var dof = /<a-scene xr-kit="dof:\s*(\d)/.exec(source);
    var libs = ['aframe'];
    if (extraLibs.some(function (n) { return /cannon/i.test(n); })) libs.push('cannon');
    return {
      kit: 'classvr-prototyping-kit',
      name: name,
      slug: slugify(name),
      concept: null,
      dof: dof ? +dof[1] : 6,
      created: nowIso(),
      build: 1,
      sourceHash: null,
      libraries: libs,
      classcloud: { organizationId: null, playlistId: null, playlistName: 'XR Prototypes', activityId: null,
                    lastPublished: null, lastUrl: null, qrPayload: null },
      artifact: { url: null, owner: null, build: null, lastShared: null },
      pages: { url: null, repo: null, build: null, lastShared: null },
      forkedFrom: fork
    };
  }

  // A-Frame: the bundled file is the npm package's dist/aframe-v<X>.min.js
  // (checked byte for byte for 1.7.1), which jsDelivr serves to any site; the
  // page's own aframe.io copy is the fallback. If neither can be reached the
  // copy goes without it and Claude puts the kit's own copy in on first use.
  function fetchAframe(v) {
    var tries = ['https://cdn.jsdelivr.net/npm/aframe@' + v + '/dist/aframe-v' + v + '.min.js',
                 'https://aframe.io/releases/' + v + '/aframe.min.js'];
    var i = 0;
    function next() {
      if (i >= tries.length) return Promise.resolve(null);
      return get(tries[i++], true).then(function (b) {
        var head = new TextDecoder().decode(new Uint8Array(b, 0, Math.min(b.byteLength, 400000)));
        if (b.byteLength < 200000 || head.indexOf('AFRAME') < 0) return next();
        return b;
      }, next);
    }
    return next();
  }

  // Build every file of the copy. entry = the history.json entry for the version.
  function buildCopy(app, doc, entry, progress) {
    var say = progress || function () {};
    var pageUrl = app + '/v/' + entry.version + '/';
    say('Fetching version ' + entry.version + '…');
    return get(pageUrl, true).then(function (bytes) {
      return sha1(bytes).then(function (fp) {
        if (entry.sha1 && fp !== entry.sha1.toLowerCase()) {
          var e = new Error('fingerprint'); e.kind = 'fingerprint'; throw e;
        }
        var page = new TextDecoder('utf-8').decode(bytes);
        say('Putting the kit back in…');
        return unslim(page, function (base, n) {
          return get(base.replace(/\/+$/, '') + '/' + n).catch(function () {
            var e = new Error('library'); e.kind = 'library'; throw e;
          });
        }).then(function (u) {
          var original = u.name || doc.app || doc.slug || 'App';
          var name = original + ' copy';
          var source = u.source.replace(/window\.BUILD\s*=\s*\d+\s*;/, 'window.BUILD = 1;');
          var fork = { url: app, version: entry.version, sha1: fp, lib: u.kit, at: nowIso().slice(0, 10), via: 'history page' };
          var files = [
            { path: 'index.html', data: source },
            { path: 'xr-project.json', data: JSON.stringify(manifest(name, source, fork, u.extraLibs), null, 2) + '\n' },
            { path: 'CHANGELOG.md', data: forkChangelog(u.docs.changelog, app, entry.version, fp, original) }
          ];
          if (u.docs.readme) files.push({ path: 'README.md', data: u.docs.readme });
          say('Fetching A-Frame…');
          var extras = u.extraLibs.map(function (n) {
            return get(u.lib.replace(/\/+$/, '') + '/' + n, true).then(function (b) { files.push({ path: n, data: new Uint8Array(b) }); },
                                                                   function () { /* Claude restores it from the kit */ });
          });
          return Promise.all([fetchAframe(u.info.aframe || '1.7.1')].concat(extras)).then(function (r) {
            if (r[0]) files.push({ path: 'aframe.min.js', data: new Uint8Array(r[0]) });
            return { name: name, original: original, fingerprint: fp, files: files, aframe: !!r[0] };
          });
        });
      });
    });
  }

  // ------------------------------------------------------------ saving

  var CRC = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(u8) { var c = 0xFFFFFFFF; for (var i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }

  function bytesOf(d) { return typeof d === 'string' ? new TextEncoder().encode(d) : d; }

  // A plain (stored) zip: every file inside one folder, so "Extract All" gives
  // the app folder straight away.
  function zip(folder, files) {
    var enc = new TextEncoder(), parts = [], central = [], offset = 0;
    var d = new Date(), time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
        date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    files.forEach(function (f) {
      var name = enc.encode(folder + '/' + f.path), data = bytesOf(f.data), crc = crc32(data);
      var h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, 0, true);
      h.setUint16(10, time, true); h.setUint16(12, date, true); h.setUint32(14, crc, true);
      h.setUint32(18, data.length, true); h.setUint32(22, data.length, true); h.setUint16(26, name.length, true); h.setUint16(28, 0, true);
      parts.push(h.buffer, name, data);
      var c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint16(10, 0, true); c.setUint16(12, time, true); c.setUint16(14, date, true); c.setUint32(16, crc, true);
      c.setUint32(20, data.length, true); c.setUint32(24, data.length, true); c.setUint16(28, name.length, true);
      c.setUint32(42, offset, true);
      central.push(c.buffer, name);
      offset += 30 + name.length + data.length;
    });
    var size = central.reduce(function (s, p) { return s + (p.byteLength || p.length); }, 0);
    var e = new DataView(new ArrayBuffer(22));
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
    e.setUint32(12, size, true); e.setUint32(16, offset, true);
    return new Blob(parts.concat(central, [e.buffer]), { type: 'application/zip' });
  }

  function download(blob, filename) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = filename;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 60000);
  }

  function canPickFolder() { return typeof root.showDirectoryPicker === 'function' && root.isSecureContext; }

  function writeFolder(parent, name, files) {
    function free(n, i) {
      var tryName = i ? n + ' ' + (i + 1) : n;
      return parent.getDirectoryHandle(tryName).then(function () { return free(n, i + 1); }, function () { return tryName; });
    }
    return free(name, 0).then(function (folderName) {
      return parent.getDirectoryHandle(folderName, { create: true }).then(function (dir) {
        return files.reduce(function (p, f) {
          return p.then(function () {
            return dir.getFileHandle(f.path, { create: true }).then(function (h) {
              return h.createWritable().then(function (w) { return w.write(bytesOf(f.data)).then(function () { return w.close(); }); });
            });
          });
        }, Promise.resolve()).then(function () { return folderName; });
      });
    });
  }

  // ------------------------------------------------------------ the dialog

  var CSS =
    '.kc-btn{font:inherit;font-size:.9rem;padding:5px 12px;border-radius:8px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;margin-top:8px}' +
    '.kc-btn:hover{background:var(--accent);color:var(--card)}' +
    '.kc-btn.primary{background:var(--accent);color:var(--card)}.kc-btn.primary:hover{filter:brightness(1.1)}' +
    '.kc-btn[disabled]{opacity:.5;cursor:default}' +
    'dialog.kc{max-width:520px;width:calc(100% - 32px);border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--fg);padding:20px 22px}' +
    'dialog.kc::backdrop{background:rgba(0,0,0,.45)}dialog.kc h2{font-size:1.15rem;margin:0 0 8px}' +
    'dialog.kc p{margin:0 0 10px}dialog.kc .row{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}' +
    'dialog.kc .status{color:var(--muted);font-size:.92rem;min-height:1.3em;margin-top:10px}' +
    'dialog.kc .done{border-left:3px solid var(--now);padding:2px 0 2px 12px}';

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  // One click: Chrome and Edge open the folder picker straight away (the
  // click is still "fresh", which the browser requires); every other browser
  // downloads a .zip. A small window then shows progress and what to do next.
  function open(app, doc, entry) {
    var name = doc.app || doc.slug || 'this app';
    var dlg = null, status = null, row = null;

    function show() {
      dlg = el('dialog', 'kc');
      dlg.appendChild(el('h2', null, 'Your own copy of version ' + entry.version));
      status = el('div', 'status', 'Making your copy…');
      row = el('div', 'row');
      dlg.appendChild(status); dlg.appendChild(row);
      document.body.appendChild(dlg);
      dlg.showModal();
      dlg.addEventListener('close', function () { dlg.remove(); });
    }
    function button(text) {
      var b = el('button', 'kc-btn primary', text); b.onclick = function () { dlg.close(); }; row.appendChild(b);
    }
    function fail(e) {
      status.textContent = e && e.kind === 'fingerprint'
        ? 'This version didn’t match its fingerprint, so nothing was saved. Reload the page and try again.'
        : e && e.kind === 'library'
        ? 'The kit files this version was built with are no longer online, so it can’t be copied here. Claude can still start a fresh app for you.'
        : 'Something went wrong making the copy, so nothing was saved. You can also ask Claude: “make me my own copy of ' + app + '/v/' + entry.version + '/”.';
      if (root.console) console.warn('[kit-copy]', e);
      button('Close');
    }
    function done(where, isZip, folder) {
      status.textContent = '';
      var ok = el('div', 'done');
      ok.appendChild(el('p', null, isZip
        ? 'Saved to your downloads as “' + folder + '.zip”. Open it and extract it first (Windows: right-click → Extract All; Mac: double-click).'
        : 'Saved as the folder “' + folder + '”' + (where ? ' in ' + where : '') + '.'));
      ok.appendChild(el('p', null, 'Next: open Claude, start a Cowork task and add ' + (isZip ? 'the extracted' : 'that') +
        ' folder. You can then begin making changes, your copy won’t be published anywhere until you ask.'));
      dlg.insertBefore(ok, status);
      button('Done');
    }
    function build() {
      return buildCopy(app, doc, entry, function (t) { status.textContent = t; });
    }

    if (canPickFolder()) {
      root.showDirectoryPicker({ id: 'kit-copy', mode: 'readwrite', startIn: 'documents' }).then(function (parent) {
        show();
        return build().then(function (c) {
          status.textContent = 'Saving…';
          return writeFolder(parent, c.name, c.files);
        }).then(function (folder) { done(parent.name, false, folder); }, fail);
      }, function (e) {
        // closed the picker: nothing to do. Anything else (a browser that
        // has the picker but refuses it here) falls back to the .zip.
        if (!e || e.name !== 'AbortError') viaZip();
      });
    } else {
      viaZip();
    }
    function viaZip() {
      show();
      build().then(function (c) {
        download(zip(c.name, c.files), c.name + '.zip');
        done(null, true, c.name);
      }, fail);
    }
  }

  if (typeof document !== 'undefined' && document.head) {
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  }

  root.KitCopy = { open: open, css: CSS, buildCopy: buildCopy, unslim: unslim, forkChangelog: forkChangelog,
                   extractDocs: extractDocs, zip: zip };
})(typeof window !== 'undefined' ? window : this);
