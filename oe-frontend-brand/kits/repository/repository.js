/* Repository: ricerca + 3 filtri faccetta; la griglia si ricalcola in tempo reale. */
(function(){
  if(!window.REPO) return;
  document.documentElement.setAttribute('data-brand', REPO.brand||'oe');
  const state = { brand:'Tutti', obiettivo:'Tutti', formato:'Tutti', q:'' };
  document.getElementById('repo-title').textContent = REPO.titolo||'Repository';
  document.getElementById('repo-sub').textContent = REPO.sottotitolo||'';

  const cap = s => s.charAt(0).toUpperCase()+s.slice(1);
  const mkSelect = key => `<label class="fld"><span>${cap(key)}</span><select data-facet="${key}">${REPO.facce[key].map(o=>`<option>${o}</option>`).join('')}</select></label>`;
  document.getElementById('filters').innerHTML =
    `<input id="q" class="search" type="search" placeholder="Cerca un asset…" aria-label="Cerca">`+
    mkSelect('brand')+mkSelect('obiettivo')+mkSelect('formato');

  const match = a =>
    (state.brand==='Tutti'    || a.brand===state.brand) &&
    (state.obiettivo==='Tutti'|| a.obiettivo===state.obiettivo) &&
    (state.formato==='Tutti'  || a.formato===state.formato) &&
    (!state.q || a.titolo.toLowerCase().includes(state.q.toLowerCase()));

  function render(){
    const list = REPO.asset.filter(match);
    document.getElementById('count').textContent = list.length===1 ? '1 asset' : `${list.length} asset`;
    document.getElementById('grid').innerHTML = list.length ? list.map(a=>
      `<div class="acard"><span class="fmt">${a.formato}</span><h3>${a.titolo}</h3>`+
      `<div class="ameta">${a.brand} · ${a.obiettivo}</div>`+
      `<a class="dl" href="${a.href||'#'}" download><span class="tile">↓</span><span class="label">Scarica</span></a></div>`
    ).join('') : `<p class="empty">Nessun asset trovato.</p>`;
  }

  const filters = document.getElementById('filters');
  filters.addEventListener('change', e=>{ const s=e.target.closest('select'); if(s){ state[s.dataset.facet]=s.value; render(); } });
  filters.addEventListener('input', e=>{ if(e.target.id==='q'){ state.q=e.target.value; render(); } });
  render();
  document.querySelectorAll('[data-oe-year]').forEach(el=>el.textContent=new Date().getFullYear());
})();
