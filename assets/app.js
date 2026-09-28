document.addEventListener('DOMContentLoaded',()=>{
  const b=document.querySelector('.menu'),n=document.querySelector('.nav');
  if(b&&n)b.addEventListener('click',()=>{n.classList.toggle('nav-open');b.setAttribute('aria-expanded',n.classList.contains('nav-open')?'true':'false')});
  const q=document.getElementById('agent-search'),c=document.getElementById('agent-search-clear');
  const category=document.getElementById('filter-category'),audience=document.getElementById('filter-audience'),provider=document.getElementById('filter-provider'),counter=document.getElementById('filter-count');
  const cards=[...document.querySelectorAll('.agent-list-card')];
  if(provider){[...new Set(cards.map(x=>x.dataset.provider).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'de')).forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=cards.find(x=>x.dataset.provider===v)?.querySelector('.pillrow .pill:nth-child(2)')?.textContent||v;provider.appendChild(o)})}
  function f(){
    const v=(q?.value||'').trim().toLowerCase(),cv=category?.value||'',av=audience?.value||'',pv=provider?.value||'';let visible=0;
    cards.forEach(x=>{const show=(!v||(x.dataset.search||'').includes(v))&&(!cv||x.dataset.category===cv)&&(!av||(x.dataset.audience||'').split(' ').includes(av))&&(!pv||x.dataset.provider===pv);x.classList.toggle('hide',!show);if(show)visible++});
    if(counter)counter.textContent=`${visible} von ${cards.length}`;
  }
  [q,category,audience,provider].forEach(x=>x&&x.addEventListener(x===q?'input':'change',f));
  if(c)c.addEventListener('click',()=>{if(q)q.value='';if(category)category.value='';if(audience)audience.value='';if(provider)provider.value='';f();q?.focus()});
  f();
});