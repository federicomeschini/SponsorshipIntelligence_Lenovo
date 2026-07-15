/* Dashboard: render di filtro, KPI, grafici, metriche e tabella.
   Il filtro ricalcola KPI + grafico a barre + tabella; donut e metriche sono statici. */
(function(){
  if(!window.DASH) return;
  const D = window.DASH, $ = s=>document.querySelector(s);
  const fmt = v => (typeof v==="number" && window.OE) ? OE.formatNumber(v) : String(v);
  document.querySelectorAll('[data-oe-year]').forEach(e=>e.textContent=new Date().getFullYear());

  // titoli
  $('#dash-title').textContent = D.titolo;
  $('#dash-sub').textContent   = D.sottotitolo;
  if(D.intro) $('#dash-intro').textContent = D.intro;
  $('#title-g1').textContent = D.barre.titolo;
  $('#title-g2').textContent = D.donut.titolo;
  if(D.tabella.titolo) $('#title-tbl').textContent = D.tabella.titolo;

  // filtro (segmented control)
  const tutte = D.filtro.opzioni[0];
  let current = D.filtro.default || tutte;
  const fc = $('#filters');
  D.filtro.opzioni.forEach(opt=>{
    const b=document.createElement('button');
    b.className='oe-segment__btn'+(opt===current?' is-active':'');
    b.type='button'; b.textContent=opt;
    b.addEventListener('click',()=>{
      current=opt;
      fc.querySelectorAll('.oe-segment__btn').forEach(x=>x.classList.toggle('is-active',x.textContent===opt));
      renderDynamic();
    });
    fc.appendChild(b);
  });
  const rows = ()=> current===tutte ? D.righe : D.righe.filter(r=>r[D.filtro.campo]===current);

  const arrow = dir => dir==='dn'
    ? '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12l7 7 7-7"/></svg>'
    : '<svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';

  function renderKpis(){
    const rs=rows();
    $('#kpis').innerHTML = D.kpi.map(k=>{
      let val;
      if(k.tipo==='count') val=rs.length;
      else if(k.tipo==='sum') val=rs.reduce((a,r)=>a+(+r[k.campo]||0),0);
      else if(k.tipo==='avg') val=rs.length?Math.round(rs.reduce((a,r)=>a+(+r[k.campo]||0),0)/rs.length):0;
      else val=k.valore;
      const affix=k.affix?`<span class="oe-kpi__affix">${k.affix}</span>`:'';
      const delta=k.delta?`<div class="kpi-delta ${k.dir||'up'}">${arrow(k.dir)}${k.delta}</div>`:'';
      return `<div class="oe-kpi"><div class="oe-kpi__value">${fmt(val)}${affix}</div><div class="oe-kpi__label">${k.label}</div>${delta}</div>`;
    }).join('');
  }

  let bar, donut;
  function renderBar(){
    const rs=rows();
    const labels=rs.map(r=>r[D.barre.etichetta]);
    const data=rs.map(r=>+r[D.barre.valore]||0);
    if(bar){ bar.data.labels=labels; bar.data.datasets[0].data=data; bar.update(); return; }
    bar=new Chart($('#g1'),{type:'bar',
      data:{labels,datasets:[{label:D.barre.titolo,data,backgroundColor:oeSeriesColor(0)}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
  }
  function renderDonut(){
    if(donut) return;
    donut=new Chart($('#g2'),{type:'doughnut',
      data:{labels:D.donut.labels,datasets:[{data:D.donut.data,backgroundColor:D.donut.labels.map((_,i)=>oeSeriesColor(i))}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}}}});
  }
  function renderMetrics(){
    const m=D.metriche, el=$('#metrics'); if(!m||!el) return;
    el.innerHTML =
      `<div class="oe-metrics__head"><span class="oe-metrics__title">${m.titolo}</span><span class="oe-metrics__range">${m.range||''}</span></div>`+
      m.righe.map(r=>`<div class="oe-metrics__row"><span class="oe-metrics__label">${r.label}${r.sub?`<span class="oe-metrics__sub">${r.sub}</span>`:''}</span><span class="oe-metrics__value">${r.valore}</span></div>`).join('')+
      (m.nota?`<div class="oe-metrics__link">${m.nota}</div>`:'');
  }
  function renderTable(){
    const rs=rows(), cols=D.tabella.colonne;
    $('#tbl').innerHTML =
      '<thead><tr>'+cols.map(c=>`<th${c.n?' class="num"':''}>${c.l}</th>`).join('')+'</tr></thead>'+
      '<tbody>'+rs.map(r=>'<tr>'+cols.map(c=>`<td${c.n?' class="num"':''}>${c.n?fmt(+r[c.k]):r[c.k]}</td>`).join('')+'</tr>').join('')+'</tbody>';
  }
  function renderDynamic(){ renderKpis(); renderBar(); renderTable(); }

  if(window.OE && typeof applyOEChartDefaults==='function') applyOEChartDefaults();
  renderKpis(); renderMetrics(); renderTable();
  if(typeof Chart!=='undefined'){ renderDonut(); renderBar(); }
})();
