document.addEventListener('DOMContentLoaded', async () => {
  const root = document.querySelector('[data-finder]');
  if (!root) return;

  const categoryButtons = [...root.querySelectorAll('[data-finder-category]')];
  const audienceButtons = [...root.querySelectorAll('[data-finder-audience]')];
  const queryInput = root.querySelector('#finder-query');
  const providerSelect = root.querySelector('#finder-provider');
  const submit = root.querySelector('#finder-submit');
  const reset = root.querySelector('#finder-reset');
  const results = root.querySelector('#finder-results');
  const status = root.querySelector('#finder-status');
  const more = root.querySelector('#finder-more');

  const focusLabels = {
    'recherche': 'Recherche & Analyse',
    'coding': 'Code & Tools',
    'automatisierung': 'Automatisierung',
    'unternehmen': 'Enterprise & Prozesse',
    'service-sales': 'Service & Sales',
    'recht': 'Legal & Professional'
  };
  const tones = ['mint','blue','peach','lilac','sky','gold'];
  const stopwords = new Set(['und','oder','mit','für','der','die','das','den','dem','ein','eine','einer','einem','einen','ich','wir','sie','auf','von','zu','im','in','am','an','ist','soll','sollen','agent','agenten','ki']);

  let agents = [];
  let shown = 3;
  const state = { category: '', audience: '', provider: '', query: '' };

  const norm = value => String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/ß/g, 'ss')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();

  const esc = value => String(value ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');

  const tokens = value => [...new Set(norm(value).split(/\s+/).filter(x => x.length >= 3 && !stopwords.has(x)))];

  const deDate = value => {
    if (!value) return '—';
    const d = new Date(value + 'T12:00:00');
    return Number.isNaN(d.valueOf()) ? value : new Intl.DateTimeFormat('de-DE',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  };

  const toneFor = slug => tones[[...slug].reduce((n,c)=>n+c.charCodeAt(0),0) % tones.length];

  function updatePressed(buttons, value) {
    buttons.forEach(btn => btn.setAttribute('aria-pressed', btn.dataset.value === value ? 'true' : 'false'));
  }

  function refreshProviders() {
    const current = state.provider;
    const available = agents
      .filter(a => !state.category || a.category === state.category)
      .map(a => a.provider)
      .filter(Boolean);
    const providers = [...new Set(available)].sort((a,b)=>a.localeCompare(b,'de'));
    providerSelect.innerHTML = '<option value="">Alle Anbieter</option>' + providers.map(p => '<option value="'+esc(p)+'">'+esc(p)+'</option>').join('');
    if (providers.includes(current)) providerSelect.value = current;
    else { state.provider = ''; providerSelect.value = ''; }
  }

  function scoreAgent(a) {
    const filters = a.filters || {};
    if (state.category && a.category !== state.category) return null;
    if (state.audience && !(filters.audience || []).includes(state.audience)) return null;
    if (state.provider && a.provider !== state.provider) return null;

    let score = 0;
    const reasons = [];
    if (state.category) { score += 20; reasons.push(a.category_name || focusLabels[a.category] || a.category); }
    if (state.audience) { score += 8; reasons.push(state.audience === 'unternehmen' ? 'für Unternehmen' : 'für Privatpersonen'); }
    if (state.provider) { score += 8; reasons.push(a.provider); }

    const qTokens = tokens(state.query);
    let textMatches = 0;
    const useMatches = [];
    if (qTokens.length) {
      const name = norm([a.name,a.provider].join(' '));
      const type = norm([a.type,a.category_name].join(' '));
      const uses = (a.uses || []).map(x => ({raw:x,norm:norm(x)}));
      const strengths = norm((a.strengths || []).join(' '));
      const summary = norm(a.summary);
      const access = norm(a.access);
      for (const t of qTokens) {
        let matched = false;
        if (name.includes(t)) { score += 7; matched = true; }
        if (type.includes(t)) { score += 5; matched = true; }
        const matchedUses = uses.filter(x => x.norm.includes(t));
        if (matchedUses.length) {
          score += 6;
          matched = true;
          matchedUses.forEach(x => { if (!useMatches.includes(x.raw)) useMatches.push(x.raw); });
        }
        if (strengths.includes(t)) { score += 3; matched = true; }
        if (summary.includes(t)) { score += 2; matched = true; }
        if (access.includes(t)) { score += 1; matched = true; }
        if (matched) textMatches++;
      }
      if (!state.category && !state.provider && textMatches === 0) return null;
      if (textMatches) {
        reasons.push(...useMatches.slice(0,2));
        if (!useMatches.length) reasons.push('Treffer im AgentenProfil');
      }
    }

    if (!state.category && !state.provider && !qTokens.length) return null;
    return { a, score, reasons:[...new Set(reasons)].slice(0,4), textMatches };
  }

  function resultCard(item) {
    const a = item.a;
    const sourceCount = Number(a.source_count || 0);
    const sourceLabel = sourceCount === 1 ? '1 Primärquelle' : sourceCount + ' Primärquellen';
    const uses = (a.uses || []).slice(0,3);
    const reasonText = item.reasons.length ? item.reasons.join(' · ') : 'Strukturierter Treffer im AgentenIndex';
    return `
      <a class="ai-agent-card finder-result-card" data-tone="${toneFor(a.slug)}" href="/agenten/${esc(a.slug)}/">
        <span class="ai-card-logo" aria-hidden="true"><img src="${esc(a.provider_logo)}" alt="" loading="lazy" decoding="async" width="38" height="38"/></span>
        <div class="ai-card-top"><span class="ai-card-verified">✓ geprüft</span><span class="ai-card-category">${esc(a.category_name)}</span></div>
        <div class="ai-card-heading"><h3>${esc(a.name)}</h3><small>${esc(a.provider)}</small></div>
        <p class="ai-card-summary">${esc(a.summary)}</p>
        <div class="finder-match"><small>Warum vorgeschlagen</small><b>${esc(reasonText)}</b></div>
        <div class="ai-card-chips">${uses.map(x=>'<span>'+esc(x)+'</span>').join('')}</div>
        <div class="ai-card-meta">
          <div><small>Fokus</small><b>${esc(focusLabels[a.category] || a.category_name)}</b></div>
          <div><small>Zielgruppe</small><b>${esc(a.audience_short || '—')}</b></div>
          <div><small>Quellen</small><b>${esc(sourceLabel)}</b></div>
        </div>
        <div class="ai-card-bottom"><span>Geprüft ${esc(deDate(a.last_verified))} · Profil ${esc(a.profile_version || '2.0')}</span><b>AgentenProfil öffnen →</b></div>
      </a>`;
  }

  function runFinder() {
    state.query = queryInput.value.trim();
    state.provider = providerSelect.value;
    const ranked = agents.map(scoreAgent).filter(Boolean)
      .sort((x,y) => y.score - x.score || x.a.name.localeCompare(y.a.name,'de'));

    if (!ranked.length) {
      results.innerHTML = '<div class="finder-empty"><b>Keine eindeutigen Treffer.</b><p>Formuliere die Aufgabe etwas allgemeiner oder entferne einen Filter. Du kannst alternativ alle 111 AgentenProfile durchsuchen.</p><a href="/agenten/">Alle Agenten durchsuchen →</a></div>';
      status.textContent = 'Keine eindeutigen Treffer';
      more.hidden = true;
      return;
    }

    const visible = ranked.slice(0, shown);
    results.innerHTML = visible.map(resultCard).join('');
    status.textContent = ranked.length + ' passende Treffer · ' + Math.min(visible.length,ranked.length) + ' angezeigt';
    more.hidden = ranked.length <= shown;
    more.dataset.total = String(ranked.length);
  }

  categoryButtons.forEach(btn => btn.addEventListener('click', () => {
    state.category = state.category === btn.dataset.value ? '' : btn.dataset.value;
    updatePressed(categoryButtons,state.category);
    refreshProviders();
  }));

  audienceButtons.forEach(btn => btn.addEventListener('click', () => {
    state.audience = state.audience === btn.dataset.value ? '' : btn.dataset.value;
    updatePressed(audienceButtons,state.audience);
  }));

  providerSelect.addEventListener('change',()=>{ state.provider = providerSelect.value; });
  submit.addEventListener('click',()=>{ shown=3; runFinder(); });
  queryInput.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); shown=3; runFinder(); }});
  more.addEventListener('click',()=>{ shown += 3; runFinder(); });
  reset.addEventListener('click',()=>{
    state.category=''; state.audience=''; state.provider=''; state.query='';
    queryInput.value='';
    updatePressed(categoryButtons,'');
    updatePressed(audienceButtons,'');
    refreshProviders();
    results.innerHTML='<div class="finder-placeholder"><span>01</span><b>Aufgabe wählen oder beschreiben</b><p>Der Finder durchsucht anschließend die 111 strukturierten AgentenProfile.</p></div>';
    status.textContent='Noch keine Auswahl';
    more.hidden=true;
  });

  try {
    const res = await fetch('/data/agents.json',{cache:'no-store'});
    if (!res.ok) throw new Error('Agentendaten konnten nicht geladen werden.');
    const data = await res.json();
    agents = Array.isArray(data.agents) ? data.agents : [];
    refreshProviders();
    status.textContent = agents.length + ' geprüfte AgentenProfile bereit';
    submit.disabled = false;
  } catch (err) {
    status.textContent = 'Finder konnte nicht geladen werden';
    results.innerHTML = '<div class="finder-empty"><b>Die Agentendaten sind gerade nicht verfügbar.</b><p>Das vollständige Verzeichnis bleibt erreichbar.</p><a href="/agenten/">Zu allen Agenten →</a></div>';
  }
});