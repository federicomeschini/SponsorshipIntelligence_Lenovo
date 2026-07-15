# Kit — Minisito verticale (multi-pagina)

Scaffold per un **minisito verticale** on-brand (rif.: Minisito Difesa & Aerospazio). Oggetto **complesso, multi-pagina**, con **navigazione a due livelli**. Si editano direttamente le pagine HTML; nav e footer sono **condivisi** via `nav.js`.

## File del kit
- `site.css` — stili condivisi (nav 2 livelli, hero, sezioni, card/KPI, CTA, footer).
- `nav.js` — **nav + footer condivisi** (una sola fonte per tutte le pagine).
- `index.html` — pagina **landing** (home).
- `pagina-contenuto.html` — pagina **di contenuto** con sezioni ancorate.

## ⭐ Navigazione a due livelli
- **1° livello (pagine):** menu del minisito. Si configura in **un solo punto** — l'array `PAGES` in `nav.js`. La pagina corrente prende `.active` in automatico.
- **2° livello (ancore di sezione):** **auto-generato** dalle sezioni della pagina marcate con `id` + `data-label`:
  ```html
  <section id="sintesi" data-label="Sintesi" class="section section--white"> … </section>
  ```
  Ogni sezione così marcata diventa una voce della sub-nav, con **scroll-spy** (voce attiva mentre si scorre). Se la pagina non ha sezioni `data-label` (es. home), la sub-nav resta **nascosta**.

## Come si crea una pagina
1. Copia `index.html` o `pagina-contenuto.html`.
2. In testa: `<div id="sitenav"></div>` · in fondo: `<div id="sitefooter"></div>` + `<script src="nav.js"></script>`.
3. Aggiorna l'array `PAGES` in `nav.js` con le pagine del minisito.
4. Marca le sezioni navigabili con `id` + `data-label="Etichetta"`.
5. Linka `site.css` + il `ds-kit` (`fonts.css`, `colors_and_type.css`, `components.css`).

## Brand
OE default. **Civiqa** → `class="theme-civiqa"` sul `<body>` (accento → Blu; il logo Civiqa si attiva da solo via CSS). Token via alias di brand su `body` + `.theme-civiqa`. Niente token custom paralleli.

## Hero
**Immersiva** (archetipo editoriale): occupa ~lo schermo di un PC medio (`min-height: calc(100svh − nav − subnav)`). Foto in `.hero__bg` (`background-image:url('assets/hero.jpg')`) + overlay accento tematizzato; senza foto resta il pattern a punti.

## Componenti pronti
Chip a 2 livelli (`.chip` capitolo lime / `.subchip`), `.kpi-card` (numeri neri), `.card` (hover), `.cta-btn` (arrow-tile **icona DS**, no unicode; variante `--ghost`), `.update-strip`, `.section--white/--tint`, `.reveal` (reveal-on-scroll). Per componenti aggiuntivi: `ds-kit/components.css`.
