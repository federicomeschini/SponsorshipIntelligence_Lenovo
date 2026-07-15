/* Repository — libreria asset. I filtri (faccette) e la ricerca restringono l'elenco.
   Sostituisci asset/faccette coi tuoi dati. href = percorso del file da scaricare. */
window.REPO = {
  brand: "oe", // "oe" | "civiqa"
  titolo: "Marketing Kit",
  sottotitolo: "Libreria asset · filtra per brand, obiettivo, formato e scarica",
  facce: {
    brand:     ["Tutti","OpenEconomics","Civiqa","Sonar","Externalytics"],
    obiettivo: ["Tutti","Awareness","Lead gen","Vendite","Recruiting"],
    formato:   ["Tutti","PDF","PPTX","Immagine","Video","Word"]
  },
  asset: [
    { titolo:"Brochure istituzionale", brand:"OpenEconomics", obiettivo:"Awareness", formato:"PDF",      href:"#" },
    { titolo:"Company profile",        brand:"OpenEconomics", obiettivo:"Awareness", formato:"PPTX",     href:"#" },
    { titolo:"One-pager Sonar",        brand:"Sonar",         obiettivo:"Vendite",   formato:"PDF",      href:"#" },
    { titolo:"Case study Civiqa",      brand:"Civiqa",        obiettivo:"Lead gen",  formato:"PDF",      href:"#" },
    { titolo:"Social kit Externalytics",brand:"Externalytics",obiettivo:"Awareness", formato:"Immagine", href:"#" },
    { titolo:"Video manifesto",        brand:"OpenEconomics", obiettivo:"Awareness", formato:"Video",    href:"#" },
    { titolo:"Pitch deck Civiqa",      brand:"Civiqa",        obiettivo:"Vendite",   formato:"PPTX",     href:"#" },
    { titolo:"Template offerta",       brand:"OpenEconomics", obiettivo:"Vendite",   formato:"Word",     href:"#" },
    { titolo:"Locandina recruiting",   brand:"OpenEconomics", obiettivo:"Recruiting",formato:"Immagine", href:"#" }
  ]
};
