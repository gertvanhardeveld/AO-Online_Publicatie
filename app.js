// Zoeken in de statische publicatie: laadt search-index.json en zoekt in de browser.
(function () {
  var ROOT = window.ROOT || '';
  var ms = null, docs = [], ready;

  function norm(t) {
    return t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }
  function highlight(text, terms) {
    var out = esc(text);
    terms.forEach(function (t) {
      if (t.length < 2) return;
      var re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[\\w\u00c0-\u00ff]*)', 'gi');
      out = out.replace(re, '<mark>$1</mark>');
    });
    return out;
  }

  ready = fetch(ROOT + 'search-index.json').then(function (r) {
    var len = r.headers.get('content-length');
    return r.text().then(function (txt) {
      var el = document.getElementById('idxsize');
      if (el) el.textContent = Math.round((len ? +len : txt.length) / 1024);
      return JSON.parse(txt);
    });
  }).then(function (d) {
    docs = d;
    if (window.MiniSearch) {
      ms = new MiniSearch({
        fields: ['title', 'text', 'functies', 'normen', 'context'],
        storeFields: ['title', 'type', 'path', 'context', 'snippet', 'hoofd'],
        processTerm: function (t) { t = norm(t); return t.length > 1 ? t : null; },
        searchOptions: { prefix: true, fuzzy: 0.2, boost: { title: 4, functies: 1.5, normen: 1.5 }, combineWith: 'AND' }
      });
      ms.addAll(docs);
    }
  }).catch(function () { docs = []; });

  function search(q, filter) {
    q = q.trim();
    if (!q) return [];
    var res;
    if (ms) {
      res = ms.search(q);
      if (!res.length) res = ms.search(q, { combineWith: 'OR' });
    } else {
      var terms = norm(q).split(/\s+/).filter(Boolean);
      res = docs.map(function (d) {
        var title = ' ' + norm(d.title), hay = ' ' + norm([d.title, d.text, d.functies, d.normen].join(' '));
        var score = 0;
        for (var i = 0; i < terms.length; i++) {
          var w = ' ' + terms[i];
          if (hay.indexOf(w) < 0 && hay.indexOf(terms[i]) < 0) return null;
          if (title.indexOf(w) > -1) score += 10; else if (title.indexOf(terms[i]) > -1) score += 5;
          score += hay.split(w).length - 1;
        }
        return { d: d, s: score };
      }).filter(Boolean).sort(function (a, b) { return b.s - a.s; }).map(function (x) { return x.d; });
    }
    if (filter) res = res.filter(filter);
    return res;
  }

  function hitHTML(r, terms) {
    return '<a class="hit" href="' + ROOT + r.path + '">' +
      '<span class="hit-type t-' + esc(r.type) + '">' + esc(r.type) + '</span>' +
      '<span class="hit-title">' + highlight(r.title, terms) + '</span>' +
      '<span class="hit-ctx">' + esc(r.context) + '</span>' +
      (r.snippet ? '<span class="hit-snip">' + highlight(r.snippet, terms) + '</span>' : '') + '</a>';
  }

  // zoekveld in de kopbalk
  var q = document.getElementById('q'), box = document.getElementById('results'), sel = -1;
  function renderTop() {
    ready.then(function () {
      var val = q.value, terms = norm(val).split(/\s+/);
      if (!val.trim()) { box.hidden = true; return; }
      var res = search(val).slice(0, 8);
      sel = -1;
      box.innerHTML = res.length ? res.map(function (r) { return hitHTML(r, terms); }).join('') :
        '<p class="nores">Niets gevonden voor "' + esc(val) + '". Probeer een ander woord.</p>';
      box.hidden = false;
    });
  }
  if (q) {
    q.addEventListener('input', renderTop);
    q.addEventListener('focus', function () { if (q.value.trim()) renderTop(); });
    q.addEventListener('keydown', function (ev) {
      var hits = box.querySelectorAll('.hit');
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
        ev.preventDefault();
        if (!hits.length) return;
        sel = (sel + (ev.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
        hits.forEach(function (h, i) { h.classList.toggle('sel', i === sel); });
        hits[sel].scrollIntoView({ block: 'nearest' });
      } else if (ev.key === 'Enter' && hits.length) {
        location.href = hits[Math.max(sel, 0)].getAttribute('href');
      } else if (ev.key === 'Escape') { box.hidden = true; q.blur(); }
    });
    document.addEventListener('click', function (ev) {
      if (!ev.target.closest('.search')) box.hidden = true;
    });
  }

  // grote zoekbalk op de startpagina
  var bq = document.getElementById('bq'), big = document.getElementById('bigresults'),
      land = document.getElementById('landscape'), fh = document.getElementById('fh');
  var type = '';
  function renderBig() {
    ready.then(function () {
      var val = bq.value, terms = norm(val).split(/\s+/), hf = fh.value;
      if (!val.trim()) { big.hidden = true; land.hidden = false; return; }
      var res = search(val, function (r) {
        return (!type || r.type === type) && (!hf || r.hoofd === hf);
      });
      big.innerHTML = '<p class="count">' + res.length + (res.length === 1 ? ' resultaat' : ' resultaten') + ' voor "' + esc(val) + '"</p>' +
        (res.length ? res.slice(0, 40).map(function (r) { return hitHTML(r, terms); }).join('') :
          '<p class="nores">Niets gevonden. Haal een filter weg of probeer een ander woord.</p>');
      big.hidden = false; land.hidden = true;
    });
  }
  if (bq) {
    bq.addEventListener('input', renderBig);
    fh.addEventListener('change', renderBig);
    document.querySelectorAll('.fchip').forEach(function (b) {
      b.addEventListener('click', function () {
        document.querySelectorAll('.fchip').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true'); type = b.dataset.type; renderBig();
      });
    });
    document.querySelectorAll('[data-try]').forEach(function (b) {
      b.addEventListener('click', function () { bq.value = b.dataset.try; renderBig(); bq.focus(); });
    });
  }

  // weergave processchema: schema of stappen (standaard stappen op een smal scherm)
  var narrow = window.matchMedia('(max-width: 760px)');
  var pref = null;
  try { pref = localStorage.getItem('ao-schemaweergave'); } catch (err) {}
  document.querySelectorAll('.flowsec').forEach(function (sec) {
    var btns = sec.querySelectorAll('[data-view]');
    function show(view, remember) {
      if (view) sec.dataset.view = view; else delete sec.dataset.view;
      var cur = view || (narrow.matches ? 'stappen' : 'schema');
      btns.forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.view === cur ? 'true' : 'false'); });
      if (remember) { try { localStorage.setItem('ao-schemaweergave', view); } catch (err) {} }
    }
    btns.forEach(function (b) { b.addEventListener('click', function () { show(b.dataset.view, true); }); });
    narrow.addEventListener && narrow.addEventListener('change', function () { show(sec.dataset.view || null); });
    show(pref);
  });

  // verbetervoorstel (prototype)
  document.querySelectorAll('[data-improve]').forEach(function (b) {
    b.addEventListener('click', function () { b.parentNode.querySelector('.improve-note').hidden = false; });
  });
})();
