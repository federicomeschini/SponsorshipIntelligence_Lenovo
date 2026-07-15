/* Dashboard — dataset di esempio. KPI, grafico a barre e tabella si ricalcolano dalle righe filtrate;
   donut e pannello metriche sono statici (sostituiscili coi tuoi). Rinomina in data.js coi dati reali. */
window.DASH = {
  brand: "oe", // "oe" | "civiqa" (per Civiqa: class="theme-civiqa" su <body>)
  titolo: "Cruscotto impatto territoriale",
  sottotitolo: "Aree intermedie · indicatori per macroarea · 2023",
  intro: "Sintesi degli impatti per macroarea: valore economico attivato, occupazione e comuni coinvolti. Il filtro in alto restringe l'analisi a una macroarea; KPI, grafico a barre e tabella si aggiornano di conseguenza.",
  filtro: { label:"Gruppo", campo:"gruppo", opzioni:["Tutte","Nord","Centro","Sud"], default:"Tutte" },
  righe: [
    { area:"Nord Ovest", gruppo:"Nord",   valore:842, occupazione:69, imprese:112, comuni:11 },
    { area:"Nord Est",   gruppo:"Nord",   valore:760, occupazione:71, imprese:118, comuni:9  },
    { area:"Centro",     gruppo:"Centro", valore:611, occupazione:65, imprese:104, comuni:12 },
    { area:"Sud",        gruppo:"Sud",    valore:438, occupazione:58, imprese:92,  comuni:11 },
    { area:"Isole",      gruppo:"Sud",    valore:196, occupazione:56, imprese:88,  comuni:7  }
  ],
  // KPI calcolati dalle righe filtrate: tipo "count" | "sum" | "avg" (campo) ; affix opzionale
  kpi: [
    { label:"Aree",               tipo:"count" },
    { label:"Valore attivato",    tipo:"sum", campo:"valore",       affix:"M€" },
    { label:"Occupazione media",  tipo:"avg", campo:"occupazione",  affix:"%"  },
    { label:"Comuni coinvolti",   tipo:"sum", campo:"comuni" }
  ],
  barre: { titolo:"Valore attivato per area (M€)", etichetta:"area", valore:"valore" },
  donut: { titolo:"Composizione per settore", labels:["Servizi","Manifattura","Turismo","ICT"], data:[38,27,20,15] },
  metriche: {
    titolo:"Moltiplicatori", range:"2023",
    righe:[
      { label:"PIL per € speso", valore:"1,47" },
      { label:"Valore produzione per € speso", valore:"2,93" },
      { label:"ETP per milione di €", valore:"19" },
      { label:"Impatto complessivo", valore:"3,8×" }
    ],
    nota:"Valori illustrativi di esempio."
  },
  tabella: {
    titolo:"Dettaglio per area",
    colonne:[
      { k:"area", l:"Area" }, { k:"gruppo", l:"Gruppo" },
      { k:"valore", l:"Valore M€", n:true }, { k:"occupazione", l:"Occup. %", n:true },
      { k:"imprese", l:"Imprese", n:true }, { k:"comuni", l:"Comuni", n:true }
    ]
  }
};
