# Kit — Web report

Scaffold per un report one-page HTML on-brand (rif.: Minireport Lombardia / Civiqa).
Si **edita direttamente l'HTML** di `template.html` (non più un oggetto dati JS): si scelgono i
blocchi-layout dal vocabolario sotto e li si riempie coi testi verbatim.

## Come si compila
1. Copia `kits/web-report/` nel progetto, insieme a `ds-kit/` (i path nel template sono `../../ds-kit/`).
2. **Testi**: prendi i contenuti VERBATIM dalla fonte testuale (`.md`/`.docx`). Il **PDF è solo riferimento di layout** (vedi `references/intake.md`).
3. **Brand**:
   - **OE** → rimuovi `class="theme-civiqa"` dal `<body>`. Logo OE già nel markup.
   - **Civiqa** → lascia `class="theme-civiqa"` (rimappa accento → Blu `#0000FF`). Logo Civiqa già nel markup (si attiva da solo con la classe).
4. Componi le sezioni scegliendo i **layout** dal vocabolario. Ogni sezione ha un `id` → entra nella nav/TOC.
5. **Figure**: di default `<image-slot>` (caricabili). Sostituisci secondo la modalità scelta in intake → vedi "Grafici".
6. Esegui `references/checks.md`, poi apri `template.html` nel browser.

## Vocabolario di layout (scegli per sezione)
| Layout | Classe / blocco | Quando |
|---|---|---|
| Colonna singola (testo) | `.text-col` + `.lead` | prosa, prefazione |
| Griglia di card | `.grid-3` / `.grid-2` + `.card` (`.neg` = hover negativo) | sintesi, profili, distretti |
| Intro a colonne con sub-chip | `.intro-grid` + `.subchip` | problema/strumento/risposte |
| Split testo + figura | `.split` | tabella accanto a mappa/grafico |
| Due figure affiancate | `.maps-2` | due mappe a confronto |
| Mappa + card | `.prov` + `.area-stack` | mappa con profili territoriali |
| Celle bordate 2 col | `.bord-2` + `.bord-cell` | due profili contrapposti |
| Matrice 2×2 | `.matrix` + `.mcell` (`.mcell--hi` = evidenziata) | segmentazioni E1×E2 |
| Tabella | `table.data` (header accento, `td.r` numerici) | **ogni dato tabellare** — MAI frammentato in card |
| Callout | `.callout` | frase-chiave |
| Sezione full-bleed | `.s-tint` / `.s-accent` / `.s-dark` | ritmo cromatico |

## Chip a due livelli
- **Capitolo (primaria):** `.chip-cap` = **lime** (anche in Civiqa, eccezione ammessa per artefatti chaptered).
- **Paragrafo (secondaria):** `.subchip` = accento di brand (Bluette OE / Blu Civiqa), testo bianco.
- Artefatto **semplice** (non chaptered): usa `.chip` (accento di brand: lime OE → blu Civiqa) al posto di `.chip-cap`.

## Navigazione
- **TOC laterale** (≥1240px, consigliata): pannello `#tocrail`, scroll-spy, auto-hide su hero/footer; il contenuto si sposta a destra.
- **Top-nav** (`#navlinks`): fallback sotto 1240px. Voci in **sentence case**.
- Tieni le voci delle due nav **allineate** alle sezioni con `id`.

## Interattività (G5)
Già cablata: barra di **progresso** di lettura, **read-more** (`.more-btn`+`.more-hidden`), **accordion** (`<details class="acc">`), **hover** su card/righe-tabella/figure/callout, **reveal-on-scroll** (`.reveal`).

## Grafici / mappe (chiedi la modalità in intake — G10)
- **(a) Immagine statica** → sostituisci `<image-slot>` con `<img src="…">` (usa @2x per nitidezza).
- **(b) Chart.js nativo** → aggiungi `<script src="https://cdn.jsdelivr.net/npm/chart.js@4">` + `../../ds-kit/chart-preset.js`, e un `<canvas>` nella `.figure`.
- **(c) Embed Flourish** → `<div class="flourish-embed" data-src="visualisation/ID"></div>` + `embed.js` **una sola volta** in fondo. ⚠️ richiede internet (no offline).
- `<image-slot>` resta per le immagini che l'utente caricherà a mano.

## Hero — IMMERSIVA (spec dell'archetipo report)
> **Regola archetipo:** la hero di un web report è **immersiva** — `min-height ~1100px` (≈ full-viewport su laptop), contenuti **centrati verticalmente**. **Non** ridurla all'above-the-fold: per i report vogliamo l'effetto immersivo (grande campo cromatico, la prima sezione "sbircia" dopo lo scroll). Rif.: *Minireport Shock Energetico Italia*.

- **Full-bleed a fondo accento (default nel template):** fondo accento di brand (blu Civiqa / viola OE), titolo Hedvig bianco, **visual a destra** (`.hero-grid` + `.hero-img`: `<image-slot>` da sostituire con la mappa/visual), pattern a punti. È la hero immersiva ~1100px.
- **Copertina 2 colonne su bianco (variante):** stessa struttura `.hero-grid`, ma fondo **bianco** con titolo scuro e domanda in accento. Per usarla, sostituisci il CSS `.hero*` con:
  ```css
  .hero{background:#fff;color:var(--oe-fg);min-height:clamp(760px,92vh,1040px);display:flex;align-items:center;padding:72px 0}
  .hero .wrap{width:100%}
  .hero h1{color:var(--oe-fg)} .hero-q{color:var(--accent)} .hero-lead{color:var(--oe-gray-600)}
  ```
  (mantieni comunque l'altezza immersiva). Per una foto di copertina full-bleed: `background-image` con overlay accento.

## Footer
Brand + tagline + colonne + barra legale. Variante "analisi" (con CONDIZIONI D'USO) per report/documenti: vedi `ds-kit/footers/`.
