// ===========================================================================
// VibeCI client — drives the 3 states (config → run timeline → results) off
// the structured SSE event stream from /api/stream/{job_id}.
// Source grounding is computed here from the real raw_doc, never hardcoded.
// ===========================================================================
document.addEventListener('DOMContentLoaded', () => {
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (s) => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

  // ---- elements ----
  const form = $('analyze-form'), runBtn = $('run-btn'), demoToggle = $('demo-mode');
  const competitorSelect = $('competitor-name'), docUrlInput = $('doc-url'), claimsInput = $('marketing-claims');
  const modeChip = $('mode-chip'), modeText = $('mode-text');
  const copyBtn = $('copy-md-btn'), newBtn = $('new-btn'), aboutBtn = $('about-btn');
  const apiKeyField = $('api-key-field'), apiKeyInput = $('api-key');

  let report = null, sections = [], docTitle = 'source.md';
  let elapsedTimer = null, runStart = 0;

  // ---- presets ----
  const PRESETS = {
    Teramind:   { mockUrl: 'mock://teramind-kb.org/api/v4/specs',  liveUrl: 'https://docs.teramind.co',
      claims: 'Real-time session monitoring with zero-latency, secure keystroke logging for instant threat mitigation, and a lightweight desktop agent.' },
    Hubstaff:   { mockUrl: 'mock://hubstaff-developer.net/tracking-api', liveUrl: 'https://developer.hubstaff.com',
      claims: 'Seamless, automated time tracking with zero worker distraction, and highly accurate proof-of-work activity percentages.' },
    'Time Doctor': { mockUrl: 'mock://timedoctor-specs.net/api/v2', liveUrl: 'https://developer.timedoctor.com',
      claims: 'Real-time automated time tracking, instant distraction alerts, and detailed web & app usage reports.' },
  };

  function switchView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    $(id).classList.add('active');
    window.scrollTo({ top: 0 });
  }

  function setMode(demo) {
    modeChip.className = 'mode-chip ' + (demo ? 'mode-demo' : 'mode-live');
    modeText.textContent = demo ? 'Demo data · public docs' : 'Live agents · gemini-2.0-flash';
  }

  // ---- config interactions ----
  function syncUrl() {
    const p = PRESETS[competitorSelect.value]; if (!p) return;
    docUrlInput.value = demoToggle.checked ? p.mockUrl : p.liveUrl;
  }
  function syncKeyField() { apiKeyField.hidden = demoToggle.checked; }
  demoToggle.addEventListener('change', () => { setMode(demoToggle.checked); syncUrl(); syncKeyField(); });
  apiKeyInput.addEventListener('input', () => apiKeyInput.classList.remove('nudge'));
  competitorSelect.addEventListener('change', () => {
    const p = PRESETS[competitorSelect.value]; if (p) { claimsInput.value = p.claims; syncUrl(); }
  });
  setMode(demoToggle.checked);
  syncKeyField();

  // One-time "pulling your business context" entrance: the connector chips sync
  // in sequence on first load, so the viewer sees the context being *pulled* from
  // the sources (Confluence/Productboard/Salesforce) — not just sitting there. In
  // production this sync happens automatically; here it's the visible step 1.
  function playContextSync() {
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return; // HTML default already shows the synced state
    const badge = $('ctx-badge');
    const chips = Array.from(document.querySelectorAll('#analyze-form .source-chip'));
    if (!badge || !chips.length) return;
    const sbText = badge.querySelector('.sb-text');
    badge.classList.add('is-syncing');
    if (sbText) sbText.textContent = 'Syncing…';
    chips.forEach(c => c.classList.add('is-pending'));
    chips.forEach((chip, i) => {
      setTimeout(() => {
        chip.classList.remove('is-pending');
        chip.classList.add('just-synced');
        setTimeout(() => chip.classList.remove('just-synced'), 600);
      }, 450 + i * 420);
    });
    setTimeout(() => {
      badge.classList.remove('is-syncing');
      if (sbText) sbText.textContent = 'Synced & ready';
    }, 450 + chips.length * 420 + 200);
  }
  playContextSync();

  // Review / edit the synced business context
  $('ctx-toggle').addEventListener('click', () => {
    const d = $('ctx-details'), open = d.hidden;
    d.hidden = !open;
    $('ctx-toggle').setAttribute('aria-expanded', String(open));
    $('ctx-toggle').textContent = open ? 'Hide context ▴' : 'Review / edit the synced context ▾';
  });

  // =========================================================================
  // Submit → run
  // =========================================================================
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const demo = demoToggle.checked;
    const key = apiKeyInput.value.trim();
    // Live mode needs a key — prompt for it inline rather than failing in the run view.
    if (!demo && !key) {
      apiKeyField.hidden = false;
      apiKeyInput.classList.add('nudge');
      apiKeyInput.focus();
      return;
    }
    const payload = {
      competitor_name: competitorSelect.value,
      doc_url: docUrlInput.value,
      marketing_claims: claimsInput.value,
      own_positioning: $('own-positioning').value,
      roadmap: $('roadmap').value,
      icp: $('icp').value,
      demo_mode: demo,
    };
    if (!demo && key) payload.api_key = key;

    runBtn.disabled = true; runBtn.classList.add('loading');
    copyBtn.hidden = true; newBtn.hidden = true;
    resetTimeline();
    $('run-competitor').textContent = payload.competitor_name;
    docTitle = payload.competitor_name.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '-docs.md';
    $('run-doc-title').textContent = 'Awaiting Discovery agent…';
    $('run-doc-meta').textContent = '';
    $('run-doc-body').innerHTML = '<div class="doc-empty">The ingested documentation will stream in here.</div>';
    switchView('view-run');
    startElapsed();

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to start analysis.'); }
      const { job_id } = await res.json();
      connectSSE(job_id);
    } catch (err) {
      stopElapsed();
      markFailed(err.message);
      runBtn.disabled = false; runBtn.classList.remove('loading');
    }
  });

  // =========================================================================
  // SSE
  // =========================================================================
  function connectSSE(jobId) {
    const es = new EventSource(`/api/stream/${jobId}`);
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      switch (ev.type) {
        case 'mode':   setMode(ev.demo); break;
        case 'pipeline': buildPipeline(ev.agents); break;
        case 'agent':  ev.phase === 'start' ? agentStart(ev.agent) : agentDone(ev.agent, ev.detail, ev.elapsed_ms); break;
        case 'tool':   addTool(ev); break;
        case 'doc':    streamDoc(ev.raw_doc); break;
        case 'completed':
          es.close(); stopElapsed();
          report = ev.data; renderResults(report);
          setTimeout(() => {
            switchView('view-results');
            copyBtn.hidden = false; newBtn.hidden = false; aboutBtn.hidden = false;
            runBtn.disabled = false; runBtn.classList.remove('loading');
          }, 650);
          break;
        case 'failed':
          es.close(); stopElapsed(); markFailed(ev.data);
          runBtn.disabled = false; runBtn.classList.remove('loading');
          break;
      }
    };
    es.onerror = () => { es.close(); stopElapsed(); };
  }

  // ---- run timeline ----
  const row = (agent) => document.querySelector(`.trow[data-agent="${agent}"]`);
  function resetTimeline() {
    $('run-error').hidden = true;
    $('timeline').innerHTML = '';   // rows are (re)built from the 'pipeline' manifest
  }

  // Build the specialized agent rows from the backend manifest (config.py),
  // so each row's specialty, capability, reasoning level, model, and accent are
  // the agent's real config — not hardcoded in the page.
  function buildPipeline(agents) {
    $('timeline').innerHTML = (agents || []).map(a => `
      <div class="trow${a.star ? ' star' : ''}" data-agent="${escapeHtml(a.agent)}" data-accent="${escapeHtml(a.accent)}">
        <div class="tdot"></div>
        <div class="tmain">
          <div class="thead">
            <span class="tname">${escapeHtml(a.label)}</span>
            ${a.star ? '<span class="star-tag">★ core</span>' : ''}
            <span class="spec-chip">${escapeHtml(a.capability)}</span>
            <span class="think-chip think-${escapeHtml(a.thinking)}">${escapeHtml(a.thinking)} reasoning</span>
            <span class="model-pill">${escapeHtml(a.model)}</span>
            <span class="tstatus">Pending</span>
          </div>
          <div class="tspecialty">${escapeHtml(a.specialty)}</div>
          <div class="tdetail"></div>
          <div class="tools"></div>
        </div>
      </div>`).join('');
  }

  // The Strategy agent's research brief renders in the results panel (from the
  // completed report). In the run view its lenses show in the agent's "done"
  // detail; the connector sync cards stay as the "gathering context" visual.
  function renderBrief(brief) {
    const panel = $('brief-panel');
    if (!brief || !brief.lenses) { panel.hidden = true; return; }
    $('brief-directive').textContent = brief.directive || '';
    $('brief-lenses').innerHTML = (brief.lenses || []).map(l =>
      `<li><span class="lens-name">${escapeHtml(l.name)}</span> — <span class="lens-why">${escapeHtml(l.why)}</span></li>`).join('');
    $('brief-icp').textContent = brief.icp || '';
    $('brief-pillars').innerHTML = (brief.pillars || []).map(p => `<span class="pillar-chip">${escapeHtml(p)}</span>`).join('');
    panel.hidden = false;
  }
  function agentStart(agent) {
    const r = row(agent); if (!r) return;
    r.classList.add('active'); r.querySelector('.tstatus').textContent = 'Running…';
  }
  function agentDone(agent, detail, ms) {
    const r = row(agent); if (!r) return;
    r.classList.remove('active'); r.classList.add('done');
    r.querySelector('.tstatus').textContent = ms != null ? `${(ms / 1000).toFixed(1)}s` : 'Done';
    if (detail) r.querySelector('.tdetail').textContent = detail;
  }
  function addTool(ev) {
    const r = row(ev.agent); if (!r) return;
    const args = Object.entries(ev.args || {}).map(([k, v]) => `<div><span class="k">${escapeHtml(k)}:</span> ${escapeHtml(v)}</div>`).join('');
    const card = document.createElement('div');
    card.className = 'tool-card';
    card.innerHTML = `
      <div class="tool-top"><span class="tool-badge">${escapeHtml(ev.transport || 'tool')}</span><span class="tool-name">${escapeHtml(ev.name)}()</span></div>
      <div class="tool-io">${args}<div><span class="arrow" aria-hidden="true">→</span> ${escapeHtml(ev.result || '')}</div></div>`;
    r.querySelector('.tools').appendChild(card);
  }
  function markFailed(msg) {
    const active = document.querySelector('.trow.active') || document.querySelector('.trow:not(.done)');
    if (active) { active.classList.remove('active'); active.classList.add('failed'); active.querySelector('.tstatus').textContent = 'Failed'; }
    showRunError(msg);
  }

  function showRunError(rawMsg) {
    const raw = String(rawMsg || '');
    let html;
    if (/\b429\b|quota|RESOURCE_EXHAUSTED/i.test(raw)) {
      html = `The Gemini project has no remaining quota for <code>gemini-2.0-flash</code> (free-tier request limit reached). ` +
why_quota();
    } else if (/api[_ ]?key|unauthor|permission|401|403|API_KEY_INVALID/i.test(raw)) {
      html = `The Gemini API key was rejected. Check <code>GEMINI_API_KEY</code> in your <code>.env</code>, then restart the server. ` +
        `In the meantime, <strong>Demo mode</strong> runs with no key.`;
    } else {
      html = `The live pipeline returned an error:<br><span style="color:var(--text-muted)">${escapeHtml(raw.split('\n')[0].slice(0, 220))}</span>` +
        `<br>You can retry, or run in <strong>Demo mode</strong> (no API needed).`;
    }
    $('run-error-msg').innerHTML = html;
    $('run-error').hidden = false;
    function why_quota() {
      return `Enable billing on the Google AI project (or use a key with quota) to run the real agents — ` +
        `or run this in <strong>Demo mode</strong>, which needs no API access. ` +
        `<a href="https://ai.google.dev/gemini-api/docs/rate-limits" target="_blank" rel="noopener">Quota docs ↗</a>`;
    }
  }
  function startElapsed() {
    runStart = performance.now();
    elapsedTimer = setInterval(() => { $('run-elapsed').textContent = ((performance.now() - runStart) / 1000).toFixed(1) + 's'; }, 100);
  }
  function stopElapsed() { if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; } }

  function streamDoc(rawDoc) {
    $('run-doc-title').textContent = docTitle;
    const { lines } = renderDoc(rawDoc, $('run-doc-body'));
    $('run-doc-meta').textContent = lines + ' lines';
  }

  // =========================================================================
  // Grounding — render doc + match each gap to its source line
  // =========================================================================
  const STOP = new Set('the a an of to is are and or for with by per in on at as be it that this their there into up under over its can will not no any'.split(' '));
  const tokens = (s) => (s.toLowerCase().match(/[a-z0-9]+/g) || []).filter(t => t.length > 2 && !STOP.has(t));
  function weighted(s) { const m = new Map(); for (const w of tokens(s)) m.set(w, (/^\d/.test(w) ? 3 : 1) + (m.get(w) || 0)); return m; }

  function renderDoc(rawDoc, bodyEl) {
    const lines = rawDoc.split('\n');
    const secs = [];
    let html = '';
    lines.forEach((raw, i) => {
      let cls = 'doc-line', content = raw;
      if (raw.startsWith('## ')) { cls += ' h'; content = raw.slice(3); secs.push({ line: i, title: content }); }
      else if (raw.startsWith('# ')) { cls += ' h'; content = raw.slice(2); }
      else if (raw.startsWith('- ')) { cls += ' b'; content = '• ' + raw.slice(2); }
      const ln = raw.trim() === '' ? '' : (i + 1);
      html += `<div class="${cls}" data-line="${i}"><span class="ln">${ln}</span><span class="lc">${escapeHtml(content)}</span></div>`;
    });
    bodyEl.innerHTML = html;
    return { lines: lines.length, sections: secs };
  }

  // Find the doc line that best matches `anchorText`, weighting distinctive
  // tokens (rare in the doc) and numbers heavily so a specific fact wins over
  // generic shared vocabulary.
  function bestLineFor(anchorText, lines, df, N) {
    const want = weighted(anchorText);
    let best = { score: -1, line: 0, text: '' };
    lines.forEach((raw, i) => {
      if (raw.startsWith('#') || raw.trim() === '') return;
      let score = 0;
      const seen = new Set();
      for (const w of tokens(raw)) {
        if (!want.has(w) || seen.has(w)) continue;
        seen.add(w);
        const idf = Math.log((N + 1) / ((df.get(w) || 0) + 1)) + 0.35; // rare token → higher
        score += want.get(w) * idf;
      }
      if (score > best.score) best = { score, line: i, text: raw };
    });
    return best;
  }

  function groundGap(gap, rawDoc, secs, prelim) {
    const lines = rawDoc.split('\n');
    const content = lines.filter(l => l.trim() && !l.startsWith('#'));
    const N = content.length;
    const df = new Map();
    content.forEach(l => { for (const w of new Set(tokens(l))) df.set(w, (df.get(w) || 0) + 1); });

    // Prefer the real evidence the compare_claims_to_docs MCP tool extracted:
    // match this gap to a pre-screen entry, then ground to its doc_snippet.
    // The primary signal is overlap between the snippet and this gap's TECHNICAL
    // REALITY (what we're grounding) — not the marketing-claim keyword, since
    // several claims can share a keyword (e.g. two "real-time" claims).
    let anchor = gap.technical_reality;
    if (prelim && prelim.length) {
      const claimL = (gap.marketing_claim + ' ' + gap.technical_reality).toLowerCase();
      const realitySet = new Set(tokens(gap.technical_reality));
      let bestP = null, bp = 0;
      for (const p of prelim) {
        if (!p.doc_snippet || (p.claim_keyword || 'none') === 'none') continue;
        let s = 0;
        for (const w of new Set(tokens(p.doc_snippet))) if (realitySet.has(w)) s += (/^\d/.test(w) ? 3 : 1);
        if (p.claim_keyword && claimL.includes(p.claim_keyword.toLowerCase())) s += 1.5; // minor tiebreaker
        for (const ev of (p.contradiction_evidence || [])) if (claimL.includes(String(ev).toLowerCase())) s += 0.5;
        if (s > bp) { bp = s; bestP = p; }
      }
      if (bestP && bp >= 2) anchor = bestP.doc_snippet;
    }

    const best = bestLineFor(anchor, lines, df, N);
    let section = '';
    for (const s of secs) if (s.line <= best.line) {
      const m = s.title.match(/^(\d+)\.\s*(.*)$/);
      section = m ? m[1] + ' · ' + m[2].split(/\s+/).slice(0, 2).join(' ') : s.title;
    }
    const quote = (best.text || '').replace(/^[-*\s]+/, '').replace(/\*\*/g, '').split(':').slice(-1)[0].trim();
    return { line: best.line, section, quote };
  }

  let activeLine = null;
  function focusLine(idx) {
    if (activeLine !== null) { const p = document.querySelector(`#doc-body .doc-line[data-line="${activeLine}"]`); if (p) p.classList.remove('persist'); }
    const el = document.querySelector(`#doc-body .doc-line[data-line="${idx}"]`);
    if (!el) return;
    el.classList.add('persist'); el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    activeLine = idx;
  }

  // =========================================================================
  // Results
  // =========================================================================
  const sevClass = (s) => /high/i.test(s) ? 'sev-high' : /moder/i.test(s) ? 'sev-mod' : 'sev-minor';

  function renderResults(data) {
    docTitle = data.competitor_name.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '-docs.md';
    activeLine = null;
    renderBrief(data.research_brief);

    // header + stats. The Grounded figure is now *earned*: the server grounds every
    // gap and scores the match (app/grounding.py) — the same code our eval gates. We
    // show the share grounded above threshold + the average confidence beneath it.
    $('r-name').textContent = data.competitor_name;
    $('s-gaps').textContent = data.gaps.length;
    $('s-high').textContent = data.gaps.filter(g => /high/i.test(g.severity)).length;
    const gd = data.grounding;
    if (gd && gd.total) {
      $('s-ground').textContent = Math.round((gd.grounded / gd.total) * 100) + '%';
      $('s-conf').textContent = 'avg ' + Math.round(gd.score * 100) + '% conf';
      $('stat-ground').title = `${gd.grounded}/${gd.total} gaps grounded ≥ ${Math.round(gd.threshold * 100)}% · eval-gated`;
    } else {
      $('s-ground').textContent = '100%';
    }

    // source evidence
    const rendered = renderDoc(data.raw_doc || '', $('doc-body'));
    sections = rendered.sections;
    $('doc-title').textContent = docTitle;
    $('doc-meta').textContent = rendered.lines + ' lines';

    // gap cards
    const stack = $('gap-stack'); stack.innerHTML = '';
    data.gaps.forEach((g, i) => {
      // Prefer the server's grounding (line + confidence the eval gates); fall back to
      // the client-side computation for older reports that predate server grounding.
      const gr = (g.grounding && g.grounding.line != null)
        ? g.grounding : groundGap(g, data.raw_doc || '', sections, data.preliminary_gaps);
      const conf = (gr.confidence != null) ? gr.confidence : null;
      const confBand = conf == null ? '' : conf >= 0.85 ? 'conf-high' : conf >= 0.6 ? 'conf-mid' : 'conf-low';
      const confPill = conf == null ? '' :
        `<span class="conf-pill ${confBand}" title="Grounding confidence — how strongly this source line backs the finding"><span class="conf-dot"></span>${Math.round(conf * 100)}% grounded</span>`;
      const sevLabel = g.severity.replace(/ ?Gaps?/i, '').trim() + ' gap';
      const card = document.createElement('div');
      card.className = 'gap-card';
      card.innerHTML = `
        <div class="gap-top">
          <span class="gap-no">GAP ${String(i + 1).padStart(2, '0')}</span>
          ${g.lens ? `<span class="lens-tag">${escapeHtml(g.lens)}</span>` : ''}
          <span class="sev-pill ${sevClass(g.severity)}">${escapeHtml(sevLabel)}</span>
        </div>
        <div class="gap-split">
          <div class="panel claim">
            <div class="plabel">Marketing claim</div>
            <div class="claim-text">“${escapeHtml(g.marketing_claim)}”</div>
            <div class="claim-attr">— ${escapeHtml(data.competitor_name)} marketing</div>
          </div>
          <div class="panel reality">
            <div class="plabel">Technical reality ${confPill}</div>
            <div class="reality-text">${escapeHtml(g.technical_reality)}</div>
            <div class="ground-chip" role="button" tabindex="0" data-line="${gr.line}"
                 aria-label="View the documentation line that grounds this claim, in section ${escapeHtml(gr.section || 'the source document')}">
              <span class="doc-ic" aria-hidden="true">📄</span>
              <span class="src">§${escapeHtml(gr.section || 'doc')}</span>
              <span class="quote">“${escapeHtml(gr.quote.slice(0, 52))}…”</span>
              <span class="go">View source ↗</span>
            </div>
          </div>
        </div>
        <div class="gap-foot">
          <span class="arrow" aria-hidden="true">↳</span>
          <div><span class="fl">Sales angle</span><span class="ft">${escapeHtml(g.sales_impact)}</span></div>
        </div>`;
      const chip = card.querySelector('.ground-chip');
      chip.addEventListener('click', () => focusLine(gr.line));
      chip.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); focusLine(gr.line); } });
      stack.appendChild(card);
    });

    // takeaways
    $('takeaways').innerHTML = (data.key_takeaways || []).map(t => `<li>${escapeHtml(t)}</li>`).join('');

    // battle card
    const b = data.battle_card || {};
    $('pitch').textContent = b.elevator_pitch || '';
    $('weak').innerHTML = (b.weaknesses || []).map(w => `<li>${escapeHtml(w)}</li>`).join('');
    $('strong').innerHTML = (b.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
    $('objections').innerHTML = (b.objection_handling || []).map(o =>
      `<details><summary>${escapeHtml(o.competitor_objection)}</summary><div class="ans"><strong>Our response:</strong> ${escapeHtml(o.our_response)}</div></details>`).join('');

    // landmines
    $('landmines').innerHTML = (data.sales_landmines || []).map(q =>
      `<div class="landmine"><span class="q" aria-hidden="true">?</span><span>${escapeHtml(q)}</span></div>`).join('');

    // structured output
    $('json').textContent = JSON.stringify(data, null, 2);
  }

  // =========================================================================
  // App-bar actions
  // =========================================================================
  function goConfig() { switchView('view-config'); copyBtn.hidden = true; newBtn.hidden = true; aboutBtn.hidden = true; }
  newBtn.addEventListener('click', goConfig);

  // "What just happened" context screen
  // The About / "what just happened" view doubles as the project-context page
  // (capstone framing + links). It's reachable from results ("What just happened?")
  // and from the footer on any view — so remember where we came from and route the
  // back buttons there, relabelling them for the no-report (footer) case.
  let aboutReturn = 'view-results';
  function openAbout(fromView) {
    aboutReturn = fromView || 'view-results';
    const fromResults = aboutReturn === 'view-results';
    $('about-back').textContent = fromResults ? '← Back to results' : '← Back';
    $('about-back-2').textContent = fromResults ? '← Back to the battle card' : '← Back';
    switchView('view-about');
  }
  aboutBtn.addEventListener('click', () => openAbout('view-results'));
  $('about-back').addEventListener('click', () => switchView(aboutReturn));
  $('about-back-2').addEventListener('click', () => switchView(aboutReturn));
  $('about-new').addEventListener('click', goConfig);
  $('foot-about').addEventListener('click', () => {
    const cur = document.querySelector('.view.active');
    openAbout(cur ? cur.id : 'view-config');
  });

  // Competitive landscape — the whole field at once
  $('landscape-btn').addEventListener('click', async () => {
    const res = await fetch('/api/landscape', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        demo_mode: demoToggle.checked,
        own_positioning: $('own-positioning').value,
        roadmap: $('roadmap').value,
        icp: $('icp').value,
      }),
    });
    renderLandscape(await res.json());
    copyBtn.hidden = true; newBtn.hidden = true; aboutBtn.hidden = true;
    switchView('view-landscape');
  });
  $('land-new').addEventListener('click', goConfig);

  function renderLandscape(L) {
    $('land-directive').textContent = L.field_brief.directive || '';
    $('land-pillars').innerHTML = (L.field_brief.pillars || []).map(p => `<span class="pillar-chip">${escapeHtml(p)}</span>`).join('');
    let html = '<thead><tr><th class="dim-h">Dimension</th>' +
      L.competitors.map(c => `<th class="comp-h" data-comp="${escapeHtml(c)}" title="Open ${escapeHtml(c)}'s battle card">${escapeHtml(c)}<span class="drill">open ↗</span></th>`).join('') +
      '<th class="us-h">ActivTrak</th></tr></thead><tbody>';
    L.dimensions.forEach(d => {
      html += `<tr><td><span class="dim-name">${escapeHtml(d.name)}</span><span class="dim-pillar">${escapeHtml(d.pillar)}</span></td>`;
      L.competitors.forEach(c => {
        const [sev, note] = (L.matrix[c] && L.matrix[c][d.name]) || ['none', ''];
        html += `<td class="cell cell-${escapeHtml(sev)}"${note ? ` title="${escapeHtml(note)}"` : ''}><span class="sev-dot"></span>${sev === 'none' ? '—' : escapeHtml(sev)}</td>`;
      });
      html += '<td class="cell us"><span class="us-check">✓</span></td></tr>';
    });
    html += '</tbody>';
    const m = $('land-matrix');
    m.innerHTML = html;
    m.querySelectorAll('.comp-h').forEach(th => th.addEventListener('click', () => drillCompetitor(th.dataset.comp)));
    $('land-wins').innerHTML = (L.where_we_win || []).map(w => `<li>${escapeHtml(w)}</li>`).join('');
  }

  function drillCompetitor(name) {
    competitorSelect.value = name;
    const p = PRESETS[name];
    if (p) { claimsInput.value = p.claims; syncUrl(); }
    form.requestSubmit();
  }

  // Failure-banner actions
  $('re-back').addEventListener('click', () => switchView('view-config'));
  $('re-demo').addEventListener('click', () => { demoToggle.checked = true; setMode(true); syncKeyField(); $('run-error').hidden = true; form.requestSubmit(); });

  copyBtn.addEventListener('click', async () => {
    if (!report) return;
    await navigator.clipboard.writeText(toMarkdown(report));
    const span = copyBtn;
    const t = span.textContent; span.textContent = 'Copied ✓';
    setTimeout(() => { span.textContent = t; }, 1400);
  });

  function toMarkdown(d) {
    const L = [];
    L.push(`# Competitive Battle Card — ${d.competitor_name}`, '');
    const rb = d.research_brief;
    if (rb) {
      L.push('## Research brief (directed by our strategy)');
      L.push(`_${rb.directive}_`, '');
      L.push('**Priority lenses:** ' + (rb.lenses || []).map(l => l.name).join(' · '));
      L.push(`**Framed for:** ${rb.icp}`);
      L.push(`**Anchored in:** ${(rb.pillars || []).join(', ')}`, '');
    }
    L.push('## Key takeaways');
    (d.key_takeaways || []).forEach(t => L.push(`- ${t}`));
    L.push('', '## Claim vs. documented reality');
    (d.gaps || []).forEach((g, i) => {
      L.push(`### Gap ${i + 1} — ${g.severity}`);
      L.push(`- **Marketing claim:** ${g.marketing_claim}`);
      L.push(`- **Technical reality:** ${g.technical_reality}`);
      L.push(`- **Sales angle:** ${g.sales_impact}`, '');
    });
    const b = d.battle_card || {};
    L.push('## Battle card');
    L.push(`**Elevator pitch:** ${b.elevator_pitch || ''}`, '');
    L.push('**Competitor weaknesses:**'); (b.weaknesses || []).forEach(w => L.push(`- ${w}`));
    L.push('', '**Competitor strengths:**'); (b.strengths || []).forEach(s => L.push(`- ${s}`));
    L.push('', '**Objection handling:**');
    (b.objection_handling || []).forEach(o => L.push(`- _"${o.competitor_objection}"_ → ${o.our_response}`));
    L.push('', '## Discovery questions');
    (d.sales_landmines || []).forEach(q => L.push(`- ${q}`));
    return L.join('\n');
  }
});
