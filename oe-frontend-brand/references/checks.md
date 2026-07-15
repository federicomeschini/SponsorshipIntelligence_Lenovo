# Check automatici — eseguire PRIMA di consegnare

Esegui ogni controllo. Se uno fallisce, correggi e ripeti.

- [ ] **o) AGGANCIO AL DS (il più importante).** Il file linka `colors_and_type.css` + `components.css` + `fonts.css` dal **`ds-kit/` embeddato della skill** (percorsi relativi `../../ds-kit/`) — copia **pinnata** dal DS v4.0 (v0.4.0, `src/`). **NON** usare `public/kit/` (kit Figma congelato, **senza** `theme-civiqa`). **NON** esiste un sistema di token parallelo (`--r`, `--serif`, `--c-*`…) né font/colori/componenti ridefiniti a mano. Se è off-DS, rifare l'aggancio: è la radice di quasi tutti gli altri difetti.
- [ ] **TOKEN) Token semantici nei componenti.** I componenti usano SOLO `--oe-accent`, `--oe-accent-strong`, `--oe-pop`, `--oe-pop-on`, `--oe-on-dark-accent`, `--oe-bg-dark`, ecc. MAI `--oe-bluette-700`, `--oe-lime-400` o altri token di scala hardcoded in un componente. Sbagliare questo rompe il tema Civiqa.
- [ ] **PESO) `font-weight: 300` come default del body.** Il peso dominante è Light (300), non Regular (400). Controllare che `body { font-weight: 300; }` sia presente e non sovrascritto dai componenti.
- [ ] **p) Mai il nero come sfondo.** Sezioni/blocchi scuri = `--oe-bg-dark` (`#270065`). Niente gradienti violenti: fondi piatti, toni della palette ufficiale.
- [ ] **q) Eyebrow/pretitolo generico = `.oe-eyebrow` (Atkinson sans).** Il **Mono** è riservato SOLO a chip e figure-label. (Diverso dalla chip lime: vedi b.)
- [ ] **r) Icone dalla libreria DS (Lucide monoline).** Mai glifi unicode (↑ ◈ ★ ⬆ ✓ ›) né emoji. Stroke: `1.5–2px`, `stroke-linecap: round; stroke-linejoin: round`.
- [ ] **a) Hedvig solo per H1 display grandi.** Da H2 in giù → Atkinson Hyperlegible Next. Non usare Hedvig su titoli piccoli (≈18px). **Tabelle e numeri: sempre Atkinson** (mai Hedvig per i dati).
- [ ] **b) Chip sopra h1/h2 = SEMPRE lime.** `.oe-tag-chip--lime` / `<Tag tone="lime">`. Mai chip default (bluette/accento) come kicker di titolo principale. Due livelli: chip capitolo (lime) e chip paragrafo (accento brand); non renderle come titoli.
- [ ] **c) Rapporto pretitolo → titolo:** PRETITOLO uppercase (chip o eyebrow) / Titolo sentence case (solo prima lettera maiuscola).
- [ ] **d) CTA "arrow tile + label"** — pattern signature OE: label tile + arrow tile, 4px gap, stesso sfondo, 52px height. Su fondo chiaro: sfondo Bluette (accento), testo bianco. Su fondo scuro: variante inverse.
- [ ] **e) Mai sotto 16px** per testi (dashboard: minimo 12px).
- [ ] **f) Carattere dell'archetipo rispettato.** Presentazione a scroll: sezioni sintetiche, una idea per sezione; se troppo testo → sintetizzare. Web report: verbatim, TOC laterale con scroll-spy.
- [ ] **g) Card senza bordo.** Le card usano superficie bianca + ombra DS (shadow-1), hover con elevazione (shadow-2). MAI bordo 1px sulle card.
- [ ] **h) Radii vocabulary: 0 / 2 / 4 / 16 px.** Default = 0 (spigolo vivo). Eccezioni ammesse: 2px (chip), 4px (card feature con foto), 16px (blocco foto). Nessun valore intermedio.
- [ ] **i) Voci di menu/nav in sentence case** (solo prima lettera maiuscola), MAI tutto maiuscolo.
- [ ] **j) Allineamento contenuti.** Contenuto hero allineato a sinistra, sulla stessa colonna di nav e sezioni (gutter coerente). In `display:flex`: wrapper interno con `width:100%`.
- [ ] **k) Dashboard — numeri neri.** Nelle dashboard i valori KPI sono SEMPRE `--oe-black`, mai Bluette. (Negli asset presentazionali i numeri possono seguire il tema.)
- [ ] **l) Brand via tema DS.** Civiqa = `class="theme-civiqa"` sulla root (`<body>` o `<html>`); OE = nessuna classe. NON hardcodare colori brand: usa i token `--oe-*` (li rimappa il tema). *Civiqa non usa il Lime*, salvo chip di capitolo (vedi b). Componenti Civiqa-specifici: `.cv-chip`, `.cv-btn`, `.cv-nav`, `.cv-footer`.
- [ ] **m) Logo corretto per brand.** Civiqa → `logo-civiqa-white/black.svg`; OE → `logo-white/black.svg`. Bianco su fondi scuri, nero su fondi chiari. MAI il logo OE in un asset Civiqa.
- [ ] **n) Nav ancorata (web report/minisito).** Menu (TOC laterale o top-nav) con anchor alle sezioni + scroll-spy (IntersectionObserver); voci in sentence case; sezioni con `id`. CTA "Contattaci" fuori dalla nav se non è una pagina del sito (accessibile solo via CTA button).
- [ ] **s) Altezza HERO per famiglia di archetipo.** Due famiglie:
      • **Editoriali/narrativi → hero IMMERSIVA** (web report, presentazione a scroll, minisito verticale): `min-height` ≈ **88–100svh** (dove c'è nav, `calc(100svh − nav[− subnav])`), contenuti centrati, effetto "riempi lo schermo di un PC medio". NON ridurla all'above-the-fold.
      • **Analisi one-page STANDALONE → hero a 2 COLONNE** (testo a sinistra su pannello accento: chip + titolo + sub + meta-grid Fonti/Modello/Aggiornamenti; **immagine a destra**). Se invece l'analisi è **inserita in un minisito** → vale la hero immersiva del minisito.
      • **Strumentali/tecnici → hero COMPATTA** (dashboard, repository): header snello, `min-height` ≈ **26–36svh** o `auto` (solo pretitolo + titolo + eventuali filtri/azioni), così l'area tecnica (KPI/tabella/griglia asset) è subito **above-the-fold**. Per la dashboard vale la topbar app-shell, non una hero grande.
      Linee guida a range, non pixel fissi.

## Verifica finale
Apri il file nel browser (OE e, se serve, con `class="theme-civiqa"` per Civiqa) e controlla la resa
prima di consegnare. (Nessun lint automatico incluso: la config oxlint di aderenza non è distribuita nel DS.)
