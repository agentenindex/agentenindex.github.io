document.addEventListener('DOMContentLoaded', async () => {
  const root=document.querySelector('[data-agentenfit]'); if(!root)return;
  const category=root.querySelector('#fit-category'), audience=root.querySelector('#fit-audience');
  const requirements=[...root.querySelectorAll('[data-fit-path]')], run=root.querySelector('#fit-run'), reset=root.querySelector('#fit-reset');
  const results=root.querySelector('#fit-results'), status=root.querySelector('#fit-status'), more=root.querySelector('#fit-more');
  let agents=[], deepBy={}, shown=6;
  const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const deDate=v=>{if(!v)return '—'; const d=new Date(v+'T12:00:00'); return Number.isNaN(d.valueOf())?v:new Intl.DateTimeFormat('de-DE',{day:'2-digit',month:'short',year:'numeric'}).format(d)};
  const selectedPaths=()=>requirements.filter(x=>x.checked).map(x=>({path:x.dataset.fitPath,label:x.dataset.fitLabel}));
  const claimMap=id=>Object.fromEntries((deepBy[id]?.claims||[]).map(c=>[c.path,c]));
  function stateFor(map, req){
    const c=map[req.path];
    if(!c)return {state:'unknown',label:'Unbekannt',claim:null};
    if(c.value===false)return {state:'false',label:'Explizit nicht dokumentiert',claim:c};
    return {state:'confirmed',label:'Bestätigt',claim:c};
  }
  function evaluate(a, selected){
    if(a.lifecycle_status==='discontinued')return null;
    if(category.value && a.category!==category.value)return null;
    if(audience.value && !(a.filters?.audience||[]).includes(audience.value))return null;
    const map=claimMap(a.profile_id), rows=selected.map(r=>({...r,...stateFor(map,r)}));
    const confirmed=rows.filter(r=>r.state==='confirmed').length;
    const contradicted=rows.filter(r=>r.state==='false').length;
    const unknown=rows.filter(r=>r.state==='unknown').length;
    const evidence=selected.length?Math.round(((confirmed+contradicted)/selected.length)*100):0;
    return {a,rows,confirmed,contradicted,unknown,evidence};
  }
  function evidenceLink(row){
    const e=row.claim?.evidence?.[0]; if(!e)return '';
    return '<a href="'+esc(e.url)+'" target="_blank" rel="noopener noreferrer">'+esc(e.title||'Primärquelle')+' ↗</a>';
  }
  function card(x, selectedCount){
    const a=x.a;
    const summary=x.contradicted?x.contradicted+' ausdrücklich widersprochen':x.unknown?x.unknown+' unbekannt':'alle ausgewählten Anforderungen dokumentiert';
    return '<article class="fit-result-card">'+
      '<div class="fit-result-head"><div><span class="fit-agent-id">'+esc(a.profile_id)+'</span><h3><a href="/agenten/'+esc(a.slug)+'/">'+esc(a.name)+'</a></h3><p>'+esc(a.provider)+' · '+esc(a.category_name||a.category)+'</p></div>'+
      '<div class="fit-score"><b>'+x.confirmed+'/'+selectedCount+'</b><span>bestätigt</span></div></div>'+
      '<div class="fit-result-stats"><span class="fit-ok">✓ '+x.confirmed+' bestätigt</span><span class="fit-no">− '+x.contradicted+' widersprochen</span><span class="fit-unknown">? '+x.unknown+' unbekannt</span><span>'+x.evidence+'% Evidenzabdeckung</span></div>'+
      '<p class="fit-result-summary">'+esc(summary)+'. Reihenfolge nur nach deiner Auswahl, keine allgemeine Qualitätsnote.</p>'+
      '<details><summary>Anforderungen & Evidenz anzeigen</summary><div class="fit-evidence-list">'+x.rows.map(r=>'<div class="fit-evidence-row" data-state="'+r.state+'"><div><b>'+esc(r.label)+'</b><span>'+esc(r.label==='Verschlüsselung at rest'||r.label==='Verschlüsselung in transit'?(r.claim?.value||r.label):r.label)+'</span></div><div><strong>'+esc(r.state==='confirmed'?(typeof r.claim.value==='boolean'?'Bestätigt':String(r.claim.value)):r.state==='false'?'Explizit false':'Unknown')+'</strong>'+evidenceLink(r)+'</div></div>').join('')+'</div></details>'+
      '<div class="fit-result-bottom"><span>Profil geprüft '+esc(deDate(a.last_verified))+'</span><a href="/agenten/'+esc(a.slug)+'/">AgentenProfil öffnen →</a></div>'+
    '</article>';
  }
  function render(){
    const selected=selectedPaths();
    if(!selected.length){status.textContent='Mindestens eine Anforderung auswählen'; results.innerHTML='<div class="finder-empty"><b>Noch keine Fit-Anforderungen gewählt.</b><p>Wähle mindestens ein dokumentierbares Kriterium. Unknown wird niemals als Nein gewertet.</p></div>'; more.hidden=true; return;}
    const ranked=agents.map(a=>evaluate(a,selected)).filter(Boolean).sort((x,y)=>x.contradicted-y.contradicted||y.confirmed-x.confirmed||x.unknown-y.unknown||x.a.name.localeCompare(y.a.name,'de'));
    const visible=ranked.slice(0,shown);
    results.innerHTML=visible.map(x=>card(x,selected.length)).join('');
    status.textContent=ranked.length+' aktive Agenten geprüft · '+selected.length+' Anforderungen';
    more.hidden=ranked.length<=shown; more.dataset.total=ranked.length;
  }
  run.addEventListener('click',()=>{shown=6;render()});
  more.addEventListener('click',()=>{shown+=6;render()});
  reset.addEventListener('click',()=>{requirements.forEach(x=>x.checked=false);category.value='';audience.value='';shown=6;status.textContent='Auswahl zurückgesetzt';results.innerHTML='<div class="finder-placeholder"><span>01</span><b>Anforderungen auswählen</b><p>AgentenFit vergleicht anschließend nur feldgenau belegte Merkmale.</p></div>';more.hidden=true;});
  try{
    const [aRes,dRes]=await Promise.all([fetch('/data/agents.json',{cache:'no-store'}),fetch('/data/agent-deep-evidence.json',{cache:'no-store'})]);
    if(!aRes.ok||!dRes.ok)throw new Error('Daten nicht verfügbar');
    const aDoc=await aRes.json(),dDoc=await dRes.json();
    agents=Array.isArray(aDoc.agents)?aDoc.agents:[]; deepBy=Object.fromEntries((dDoc.agents||[]).map(x=>[x.agent_id,x]));
    status.textContent=agents.filter(a=>a.lifecycle_status!=='discontinued').length+' aktive Agenten bereit'; run.disabled=false;
  }catch(e){status.textContent='AgentenFit konnte nicht geladen werden';results.innerHTML='<div class="finder-empty"><b>Daten konnten nicht geladen werden.</b><p>Bitte nutze vorübergehend die AgentenProfile.</p></div>';}
});