/* kit-qr - the Vercel route's on-page QR code.
   Loaded by every slim page the Vercel build makes. It draws a QR code of the
   page's own public address in the top-right corner, the same card the GitHub
   Pages builder adds, so a headset can scan the page straight off a screen.

   Nothing about the address is baked into this file: the page carries one
   line, <meta name="xr-kit-qr" content="url=https://<app>.vercel.app/">, and
   this script works the rest out when the page opens -
     * which host: the public address from that line. Any other *.vercel.app
       host the page might be opened from (the team-suffixed alias, a
       per-publish address) is password-protected and a headset cannot open
       it, so it is never put in the code. A custom domain is used as it is.
     * which path: "/" for the app, "/v/<N>/" on a version's own page, so
       scanning a version opens that exact version.
   Entering VR hides it (the headset never shows it); leaving VR brings it
   back. Click to fill the screen for scanning; click, Esc or the cross to
   shrink it again. The encoder is a line-for-line port of the one in
   share-xr-app/assets/pages/build_pages.py (byte mode, level M, versions
   1-40, all eight masks scored) and produces the same modules bit for bit. */
(function (root) {
  'use strict';

  // ------------------------------------------------------------- encoder
  var EC_M = [null,  // version -> [ec per block, g1 blocks, g1 data, g2 blocks, g2 data]
    [10, 1, 16, 0, 0], [16, 1, 28, 0, 0], [26, 1, 44, 0, 0], [18, 2, 32, 0, 0], [24, 2, 43, 0, 0],
    [16, 4, 27, 0, 0], [18, 4, 31, 0, 0], [22, 2, 38, 2, 39], [22, 3, 36, 2, 37], [26, 4, 43, 1, 44],
    [30, 1, 50, 4, 51], [22, 6, 36, 2, 37], [22, 8, 37, 1, 38], [24, 4, 40, 5, 41], [24, 5, 41, 5, 42],
    [28, 7, 45, 3, 46], [28, 10, 46, 1, 47], [26, 9, 43, 4, 44], [26, 3, 44, 11, 45], [26, 3, 41, 13, 42],
    [26, 17, 42, 0, 0], [28, 17, 46, 0, 0], [28, 4, 47, 14, 48], [28, 6, 45, 14, 46], [28, 8, 47, 13, 48],
    [28, 19, 46, 4, 47], [28, 22, 45, 3, 46], [28, 3, 45, 23, 46], [28, 21, 45, 7, 46], [28, 19, 47, 10, 48],
    [28, 2, 46, 29, 47], [28, 10, 46, 23, 47], [28, 14, 46, 21, 47], [28, 14, 46, 23, 47], [28, 12, 47, 26, 48],
    [28, 6, 47, 34, 48], [28, 29, 46, 14, 47], [28, 13, 46, 32, 47], [28, 40, 47, 7, 48], [28, 18, 47, 31, 48]];

  var EXP = [], LOG = [];
  (function () {
    var x = 1, i;
    for (i = 0; i < 256; i++) LOG[i] = 0;
    for (i = 0; i < 255; i++) {
      EXP[i] = x; LOG[x] = i; x <<= 1;
      if (x & 0x100) x ^= 0x11d;
    }
    for (i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  })();

  function zeros(n) { var a = []; for (var i = 0; i < n; i++) a.push(0); return a; }

  function polyMul(a, b) {
    var out = zeros(a.length + b.length - 1);
    for (var i = 0; i < a.length; i++) {
      if (!a[i]) continue;
      for (var j = 0; j < b.length; j++) if (b[j]) out[i + j] ^= EXP[LOG[a[i]] + LOG[b[j]]];
    }
    return out;
  }

  function rsEncode(data, nEc) {
    var gen = [1], i, j;
    for (i = 0; i < nEc; i++) gen = polyMul(gen, [1, EXP[i]]);
    var rem = data.concat(zeros(nEc));
    for (i = 0; i < data.length; i++) {
      var c = rem[i];
      if (c) for (j = 1; j < gen.length; j++) rem[i + j] ^= EXP[LOG[gen[j]] + LOG[c]];
    }
    return rem.slice(data.length);
  }

  function bitLength(n) { var b = 0; while (n > 0) { b++; n = Math.floor(n / 2); } return b; }

  function bch(value, poly, bits) {   // value shifted left by `bits`, BCH remainder appended
    var v = value << bits, top = bitLength(poly);
    for (var i = bitLength(v) - top; i >= 0; i--) if (v & (1 << (i + top - 1))) v ^= poly << i;
    return (value << bits) | v;
  }

  function alignmentPositions(version) {
    if (version === 1) return [];
    var n = Math.floor(version / 7) + 2, size = version * 4 + 17;
    var step = version === 32 ? 26 : Math.ceil((size - 13) / (2 * n - 2)) * 2;
    var positions = [6], pos = size - 7;
    for (var k = 0; k < n - 1; k++) { positions.splice(1, 0, pos); pos -= step; }
    return positions;
  }

  function utf8(text) {
    if (typeof TextEncoder !== 'undefined') return Array.prototype.slice.call(new TextEncoder().encode(text));
    var s = unescape(encodeURIComponent(text)), out = [];
    for (var i = 0; i < s.length; i++) out.push(s.charCodeAt(i));
    return out;
  }

  function qrMatrix(text) {
    var data = utf8(text), version, ec, g1, d1, g2, d2, capacity, cci, i, r, c;
    for (version = 1; version <= 40; version++) {
      ec = EC_M[version][0]; g1 = EC_M[version][1]; d1 = EC_M[version][2]; g2 = EC_M[version][3]; d2 = EC_M[version][4];
      capacity = g1 * d1 + g2 * d2;
      cci = version < 10 ? 8 : 16;
      if (4 + cci + 8 * data.length <= capacity * 8) break;
    }
    if (version > 40) throw new Error('text too long for a QR code');

    // data codewords
    var bits = [];
    function put(val, n) { for (var k = n - 1; k >= 0; k--) bits.push((val >> k) & 1); }
    put(4, 4);
    put(data.length, cci);
    for (i = 0; i < data.length; i++) put(data[i], 8);
    put(0, Math.min(4, capacity * 8 - bits.length));
    while (bits.length % 8) bits.push(0);
    var codewords = [];
    for (i = 0; i < bits.length; i += 8) {
      var byte = 0;
      for (var k = 0; k < 8; k++) byte = (byte << 1) | bits[i + k];
      codewords.push(byte);
    }
    for (i = 0; codewords.length < capacity; i++) codewords.push(i & 1 ? 0x11 : 0xEC);

    // blocks + error correction, then interleave
    var blocks = [], pos = 0, groups = [[g1, d1], [g2, d2]];
    groups.forEach(function (g) {
      for (var n = 0; n < g[0]; n++) { blocks.push(codewords.slice(pos, pos + g[1])); pos += g[1]; }
    });
    var ecs = blocks.map(function (b) { return rsEncode(b, ec); });
    var longest = 0, seq = [];
    blocks.forEach(function (b) { longest = Math.max(longest, b.length); });
    for (k = 0; k < longest; k++) blocks.forEach(function (b) { if (k < b.length) seq.push(b[k]); });
    for (k = 0; k < ec; k++) ecs.forEach(function (e) { seq.push(e[k]); });

    // the matrix: null = free, true/false = fixed pattern
    var size = version * 4 + 17, m = [];
    for (r = 0; r < size; r++) { m.push([]); for (c = 0; c < size; c++) m[r].push(null); }
    function finder(r0, c0) {
      for (var dr = -1; dr < 8; dr++) for (var dc = -1; dc < 8; dc++) {
        var rr = r0 + dr, cc = c0 + dc;
        if (rr < 0 || rr >= size || cc < 0 || cc >= size) continue;
        var edge = dr === -1 || dr === 7 || dc === -1 || dc === 7;
        var ring = dr === 0 || dr === 6 || dc === 0 || dc === 6;
        var core = dr >= 2 && dr <= 4 && dc >= 2 && dc <= 4;
        m[rr][cc] = !edge && (ring || core);
      }
    }
    finder(0, 0); finder(0, size - 7); finder(size - 7, 0);
    for (i = 8; i < size - 8; i++) m[6][i] = m[i][6] = (i % 2 === 0);     // timing
    var aps = alignmentPositions(version);
    aps.forEach(function (ar) {
      aps.forEach(function (ac) {
        if ((ar <= 8 && ac <= 8) || (ar <= 8 && ac >= size - 9) || (ar >= size - 9 && ac <= 8)) return;
        for (var dr = -2; dr <= 2; dr++) for (var dc = -2; dc <= 2; dc++)
          m[ar + dr][ac + dc] = Math.max(Math.abs(dr), Math.abs(dc)) !== 1;
      });
    });
    m[size - 8][8] = true;                                               // dark module
    for (i = 0; i < 9; i++) {                                            // format areas
      if (m[8][i] === null) m[8][i] = false;
      if (m[i][8] === null) m[i][8] = false;
    }
    for (i = size - 8; i < size; i++) m[8][i] = false;
    for (i = size - 7; i < size; i++) m[i][8] = false;
    if (version >= 7) {                                                  // version info
      var vinfo = bch(version, 0x1F25, 12);
      for (i = 0; i < 18; i++) {
        var vb = ((vinfo >> i) & 1) === 1;
        m[Math.floor(i / 3)][size - 11 + i % 3] = vb;
        m[size - 11 + i % 3][Math.floor(i / 3)] = vb;
      }
    }

    // place data in the zig-zag
    var fixed = m.map(function (row) { return row.map(function (cell) { return cell !== null; }); });
    var stream = [];
    seq.forEach(function (cw) { for (var b = 7; b >= 0; b--) stream.push((cw >> b) & 1); });
    var bi = 0, col = size - 1, upward = true;
    while (col > 0) {
      if (col === 6) col -= 1;
      for (var n = 0; n < size; n++) {
        r = upward ? size - 1 - n : n;
        for (var s = 0; s < 2; s++) {
          c = col - s;
          if (!fixed[r][c]) { m[r][c] = bi < stream.length ? stream[bi] === 1 : false; bi++; }
        }
      }
      col -= 2;
      upward = !upward;
    }

    // masks, scored
    var masks = [
      function (r, c) { return (r + c) % 2 === 0; },
      function (r) { return r % 2 === 0; },
      function (r, c) { return c % 3 === 0; },
      function (r, c) { return (r + c) % 3 === 0; },
      function (r, c) { return (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0; },
      function (r, c) { return (r * c) % 2 + (r * c) % 3 === 0; },
      function (r, c) { return ((r * c) % 2 + (r * c) % 3) % 2 === 0; },
      function (r, c) { return ((r + c) % 2 + (r * c) % 3) % 2 === 0; }];

    function apply(maskId) {
      var f = masks[maskId], out = [], rr, cc;
      for (rr = 0; rr < size; rr++) {
        out.push([]);
        for (cc = 0; cc < size; cc++) out[rr].push(fixed[rr][cc] ? m[rr][cc] : (m[rr][cc] !== f(rr, cc)));
      }
      var fmt = bch(maskId, 0x537, 10) ^ 0x5412;                         // level M = 00
      for (var q = 0; q < 15; q++) {
        var bit = ((fmt >> q) & 1) === 1;
        if (q < 6) out[q][8] = bit;
        else if (q < 8) out[q + 1][8] = bit;
        else out[size - 15 + q][8] = bit;
        if (q < 8) out[8][size - 1 - q] = bit;
        else if (q < 9) out[8][7] = bit;
        else out[8][14 - q] = bit;
      }
      return out;
    }

    function penalty(g) {
      var total = 0, rr, cc, lines = [g, []];
      for (cc = 0; cc < size; cc++) { lines[1].push([]); for (rr = 0; rr < size; rr++) lines[1][cc].push(g[rr][cc]); }
      lines.forEach(function (set) {
        set.forEach(function (line) {
          var run = 0, prev = null, str = '';
          line.forEach(function (v) {
            if (v === prev) run++;
            else { if (run >= 5) total += 3 + run - 5; run = 1; prev = v; }
            str += v ? '1' : '0';
          });
          if (run >= 5) total += 3 + run - 5;
          total += 40 * (str.split('10111010000').length - 1 + str.split('00001011101').length - 1);
        });
      });
      for (rr = 0; rr < size - 1; rr++) for (cc = 0; cc < size - 1; cc++)
        if (g[rr][cc] === g[rr][cc + 1] && g[rr][cc] === g[rr + 1][cc] && g[rr][cc] === g[rr + 1][cc + 1]) total += 3;
      var dark = 0;
      g.forEach(function (row) { row.forEach(function (v) { if (v) dark++; }); });
      total += 10 * Math.floor(Math.abs(Math.floor(dark * 100 / (size * size)) - 50) / 5);
      return total;
    }

    var best = 0, bestScore = Infinity;
    for (i = 0; i < 8; i++) { var score = penalty(apply(i)); if (score < bestScore) { bestScore = score; best = i; } }
    return apply(best);
  }

  function qrSvg(url) {   // quiet zone included, crisp at any size
    var matrix = qrMatrix(url), n = matrix.length, quiet = 4, size = n + 2 * quiet, runs = '';
    matrix.forEach(function (row, y) {
      for (var x = 0; x < n;) {
        if (row[x]) { var start = x; while (x < n && row[x]) x++; var w = x - start;
          runs += 'M' + (start + quiet) + ' ' + (y + quiet) + 'h' + w + 'v1h-' + w + 'z'; }
        else x++;
      }
    });
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + size + ' ' + size + '" shape-rendering="crispEdges" ' +
      'role="img" aria-label="QR code"><rect width="' + size + '" height="' + size + '" fill="#fff"/>' +
      '<path d="' + runs + '" fill="#111"/></svg>';
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { qrMatrix: qrMatrix, qrSvg: qrSvg };
  if (!root.document) return;

  // ------------------------------------------------------------- which address
  function isLocal(host) {
    return !host || host === 'localhost' || /^127\./.test(host) || host === '[::1]' || host === '0.0.0.0';
  }

  function address() {
    var meta = document.querySelector('meta[name="xr-kit-qr"]'), baked = null;
    if (meta) (meta.getAttribute('content') || '').split(';').forEach(function (part) {
      var kv = part.split('='), key = kv.shift().trim(), val = kv.join('=').trim();
      if (key === 'url' && /^https:\/\/[^\/]+/.test(val)) baked = val.match(/^https:\/\/[^\/]+/)[0];
    });
    var loc = root.location, host = loc.hostname, live = /^https?:$/.test(loc.protocol) && !isLocal(host);
    var origin;
    if (live && !/\.vercel\.app$/i.test(host)) origin = loc.protocol + '//' + loc.host;   // a custom domain
    else if (baked) origin = baked;                                                        // the public address
    else if (live) origin = loc.protocol + '//' + loc.host;
    else return null;                                                                      // a local file, never published
    var v = live ? loc.pathname.match(/^\/v\/(\d+)(?:\/|\/index\.html)?$/) : null;
    return { url: origin + (v ? '/v/' + v[1] + '/' : '/'), version: v ? parseInt(v[1], 10) : null };
  }

  // ------------------------------------------------------------- the card
  var CSS =
    '#kit-qr{position:fixed;top:12px;right:12px;z-index:9998;display:flex;align-items:center;gap:10px;' +
    'font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#40505f;' +
    'background:rgba(255,255,255,.92);border:1px solid rgba(64,80,95,.18);border-radius:10px;padding:8px 10px 8px 8px;' +
    'cursor:zoom-in;user-select:none;backdrop-filter:blur(4px);max-width:360px;transition:background .15s}' +
    '#kit-qr:hover{background:#fff}' +
    '#kit-qr svg{width:148px;height:148px;flex:none;border-radius:4px}' +
    '#kit-qr b{display:block;font-weight:600;font-size:13px;color:#1d2733}' +
    '#kit-qr span{display:block;color:#6c7d8e}' +
    '#kit-qr code{display:block;margin-top:4px;font:11px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;' +
    'color:#2f6f8f;word-break:break-all}' +
    '#kit-qr .hint{display:block;margin-top:6px;color:#8a98a6;font-size:11px}' +
    '#kit-qr .x{display:none}' +
    '#kit-qr.big{top:0;right:0;bottom:0;left:0;z-index:10002;max-width:none;border:0;border-radius:0;padding:24px;' +
    'flex-direction:column;justify-content:center;gap:18px;background:rgba(18,26,34,.82);cursor:zoom-out}' +
    '#kit-qr.big svg{width:min(72vmin,600px);height:min(72vmin,600px);border-radius:14px;' +
    'box-shadow:0 12px 48px rgba(0,0,0,.45)}' +
    '#kit-qr.big .t{display:block;text-align:center;max-width:90vw}' +
    '#kit-qr.big b{color:#fff;font-size:20px}#kit-qr.big span{color:#c9d3dc;font-size:14px}' +
    '#kit-qr.big code{color:#9fd3ff;font-size:14px;margin-top:8px}' +
    '#kit-qr.big .hint{color:#8a98a6;font-size:13px;margin-top:10px}' +
    '#kit-qr.big .x{display:block;position:fixed;top:14px;right:18px;width:44px;height:44px;border:0;border-radius:50%;' +
    'background:rgba(255,255,255,.16);color:#fff;font:26px/44px sans-serif;text-align:center;cursor:pointer}' +
    '#kit-qr.big .x:hover{background:rgba(255,255,255,.3)}' +
    '#kit-qr.kit-qr-vr{display:none}' +
    '@media (max-height:560px){#kit-qr.big svg{width:min(56vmin,600px);height:min(56vmin,600px)}#kit-qr.big{gap:10px}}' +
    '@media (max-width:700px),(max-height:520px){#kit-qr:not(.big){padding:6px;gap:0}' +
    '#kit-qr:not(.big) svg{width:96px;height:96px}#kit-qr:not(.big) .t{display:none}}';

  function show() {
    if (document.getElementById('kit-qr')) return;       // a Pages copy already has one
    var where = address();
    if (!where) return;
    var svg;
    try { svg = qrSvg(where.url); } catch (e) { console.warn('[xr-kit] QR code not drawn: ' + e.message); return; }

    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    var q = document.createElement('div');
    q.id = 'kit-qr';
    q.setAttribute('role', 'button');
    q.setAttribute('tabindex', '0');
    q.setAttribute('aria-label', 'QR code for ' + where.url + ' - click to enlarge for scanning');
    q.setAttribute('title', 'Click to enlarge for scanning');
    q.setAttribute('data-url', where.url);
    q.innerHTML = svg + '<div class="t"><b></b><span>Scan with the ClassVR scanner</span><code></code>' +
      '<span class="hint">Click to enlarge</span></div>' +
      '<button class="x" type="button" aria-label="Back to normal size">&times;</button>';
    q.querySelector('b').textContent = where.version ? 'Open version ' + where.version + ' on a headset' : 'Open on a headset';
    q.querySelector('code').textContent = where.url.replace(/^https?:\/\//, '');
    document.body.appendChild(q);

    var hint = q.querySelector('.hint');
    function set(on) {
      q.classList.toggle('big', on);
      hint.textContent = on ? 'Click anywhere, press Esc or the cross to shrink it again' : 'Click to enlarge';
      q.setAttribute('aria-expanded', on ? 'true' : 'false');
      if (!on) q.blur();
    }
    q.addEventListener('click', function (e) { e.stopPropagation(); set(!q.classList.contains('big')); });
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); set(!q.classList.contains('big')); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && q.classList.contains('big')) set(false); });

    // hidden while the headset is presenting (desktop fullscreen also fires
    // enter-vr, and there the card stays)
    var scene = document.querySelector('a-scene');
    if (scene) {
      scene.addEventListener('enter-vr', function () {
        setTimeout(function () {
          var xr = scene.renderer && scene.renderer.xr;
          if (xr && xr.isPresenting) { set(false); q.classList.add('kit-qr-vr'); }
        }, 0);
      });
      scene.addEventListener('exit-vr', function () { q.classList.remove('kit-qr-vr'); });
    }

    root.KIT_QR = { url: where.url, version: where.version, modules: svg.match(/viewBox="0 0 (\d+)/)[1] - 8 };
    console.info('[xr-kit] QR code on the page points at ' + where.url);
    if (Array.isArray(root.KIT_CHECKS)) root.KIT_CHECKS.push({
      name: 'the page shows a QR code of its address',
      run: function (t) {
        var card = document.getElementById('kit-qr');
        t.expect(!!card && !!card.querySelector('svg path'), 'the QR card is missing from the page');
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show);
  else show();
})(typeof window !== 'undefined' ? window : this);
