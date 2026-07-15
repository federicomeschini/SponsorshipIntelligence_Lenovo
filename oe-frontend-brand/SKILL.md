---
name: oe-frontend-brand
description: >
  Crea oggetti web HTML standalone on-brand per OpenEconomics, guidando colleghi con
  competenze eterogenee. Sei tipi di asset web (analisi one-page, minisito verticale,
  web report, presentazione a scroll, dashboard, repository) per i brand OE e Civiqa.
  USA QUESTA SKILL quando l'utente chiede di creare un asset web, minisito, landing,
  one-pager, presentazione, dashboard, report web o pagina HTML in contesto OE.
---

# oe-frontend-brand

Costruisci oggetti web **HTML standalone** (si aprono nel browser, nessun build) sul design system
OpenEconomics. Il kit consumabile è la **copia pinnata embeddata in `ds-kit/`** (`colors_and_type.css`,
`components.css`, `fonts/`, `chart-preset.js`, `image-slot.js`, loghi): i kit la linkano con percorsi
relativi `../../ds-kit/`. È **pinnata dal DS v4.0 (v0.4.0, dal `src/`)** — fonte di verità upstream in
`Design System/design-system v4.0/` (da consultare solo per **aggiornare** l'embeddato, non a runtime).
Nessun codice prima dell'approvazione delle sezioni.

> **APPENA INVOCATA — prima di tutto (Fase 1, intake):** NON scrivere codice e non scegliere un
> archetipo da solo. Poni subito le domande con **`AskUserQuestion`** — anzitutto **(1) brand**
> (OpenEconomics / Civiqa) e **(2) "Che tipo di asset web?"** tra i 6 tipi (analisi one-page ·
> minisito verticale · web report · presentazione a scroll · dashboard · repository). Segui
> `references/intake.md`. Solo dopo le risposte procedi con mappa sezioni → build.

## Principio — token semantici

I componenti usano **solo token semantici**, mai i colori brand diretti. Hardcodare
`--oe-bluette-700` o `--oe-lime-400` in un componente è un errore: il tema Civiqa non
funzionerebbe. Usa sempre:

| Ruolo | Token semantico |
|---|---|
| Accento primario (fill) | `--oe-accent` |
| Accento scuro / hover | `--oe-accent-strong` |
| Testo su accento | `--oe-accent-on` |
| "Pop" lime (fill) | `--oe-pop` |
| Testo su pop | `--oe-pop-on` |
| Accento come testo su scuro | `--oe-on-dark-accent` |
| Fondo scuro (footer, dark sections) | `--oe-bg-dark` |

## Regole non negoziabili (verifica SEMPRE prima di consegnare)

1. **`font-weight: 300` (Light) come default del body.** Il peso dominante è Light, non Regular.
   Sbagliare questo rende tutto "troppo pesante" rispetto al brand.
2. **Chip sopra un h1/h2 = SEMPRE lime.** Usa `.oe-tag-chip--lime` / `<Tag tone="lime">`.
   Mai chip default o bluette come kicker di titolo principale.
3. **Eyebrow = Atkinson sans; chip = Atkinson Mono.** Ruoli distinti e non intercambiabili.
   L'eyebrow (pretitolo generico) è `.oe-eyebrow` (sans, uppercase). Il chip è mono.
4. **Spigolo vivo ovunque per card e CTA.** `border-radius: 0`. Eccezioni ammesse solo:
   2px (chip), 4px (card feature con foto), 16px (blocco foto). Vocabolario: 0 / 2 / 4 / 16.
5. **CTA "arrow tile + label"** — il pattern signature OE: due tile affiancate, 4px di gap,
   stesso sfondo. Su fondo bianco/chiaro: sfondo Bluette, testo bianco. Su fondo scuro:
   variante `inverse` (bianco su accento). Vedi `ui_kits/website/CtaButton.jsx`.
6. **Sezioni scure = `--oe-bg-dark` (`#270065`).** Mai nero puro come sfondo. No gradient violenti.
7. **Icone Lucide, monoline, 1.5–2px stroke, 42×42 px** dentro un tile 62×62. Mai glifi unicode,
   mai emoji. `stroke-linecap: round; stroke-linejoin: round`.
8. **Font minimo 12px** (≥16px fuori dashboard). **Hedvig Letters Serif solo per H1/display grandi.**
   Da H2 in giù → Atkinson. Tabelle e dati: sempre Atkinson (mai Hedvig per i numeri).
9. **Token semantici nei componenti** (vedi Principio). Mai `--oe-bluette-*`/`--oe-lime-*` hardcoded.
10. **Esegui `references/checks.md` prima di consegnare.** Apri nel browser, poi ZIP con
    data+orario nel nome (`NomeAsset_YYYYMMDD_HHMM.zip`).

## Componenti canonici (classi CSS v4)

Usa le classi `.oe-*` da `src/components/components.css` (incluso nel kit via `_ds_bundle.js`):

| Componente | Classe / elemento |
|---|---|
| Button | `.oe-btn --primary / --accent / --secondary / --ghost / inverse` |
| Chip / Tag | `.oe-tag-chip --lime / --default / --on-dark` |
| KPI card | `.oe-kpi` + `.oe-kpi__value / __label / __icon / __note` |
| Tabella | `.oe-table` (+ `--numeric` per colonne dati) dentro `.oe-table__wrap` |
| Badge stato | `.oe-badge --success / --warning / --danger / --info / --neutral` |
| Griglia | `.oe-grid` + `.oe-col-1..12` (responsive 12/8/4 col, container query) |
| Tabs | `.oe-tabs` + `.oe-tab` |
| Figure label | `.oe-figure-label` (mono, uppercase: GRAFICO 1 / TABELLA 1) |
| Header sito | `.oe-header` |
| Footer | `Footer variant="standard"` o `"analisi"` |
| Numeri | `.oe-num` (Atkinson sans, tabular-nums; colore segue sfondo) |

## Flusso a 4 fasi

1. **Intake** — segui `references/intake.md` (usa `AskUserQuestion`). Chiedi sempre il brand
   (OE o Civiqa) prima di qualsiasi scelta di colore. Linguaggio per il collega: "tipo di asset
   web", mai "archetipo".
2. **Mappa pagine** *(solo asset multi-pagina, es. minisito verticale)* → attendi approvazione.
3. **Mappa sezioni** (per pagina: chip pretitolo + titolo + componente + sfondo) → attendi approvazione.
4. **Build + check + consegna:**
   - Linka dal kit: `colors_and_type.css` + `components.css` (o `_ds_bundle.js` se standalone).
   - Parti dai componenti in `ui_kits/website/` (sito) o `ui_kits/dashboard/` (dashboard).
   - Applica il footer (`variant="standard"` o `"analisi"`).
   - Esegui `references/checks.md` PRIMA di consegnare.
   - Apri nel browser (`open <file>`), itera, poi crea lo ZIP (`NomeAsset_YYYYMMDD_HHMM.zip`).

## Archetipi — regole specifiche per tipo

**Altezza/forma HERO — per archetipo (linee guida a range, non pixel fissi):**
- **Editoriali immersivi** (web report, presentazione a scroll, minisito verticale): hero **IMMERSIVA** `min-height` ≈ **88–100svh** (dove c'è nav, `calc(100svh − nav[− subnav])`), contenuti centrati.
- **Analisi one-page STANDALONE**: hero **a 2 COLONNE** (testo sx su pannello accento + meta-grid Fonti/Modello/Aggiornamenti · immagine dx). Se l'analisi è **dentro un minisito** → hero immersiva del minisito.
- **Strumentali/tecnici** (dashboard, repository): hero **COMPATTA** (`min-height` ≈ 26–36svh o `auto`); area tecnica subito above-the-fold. Dashboard = topbar app-shell.

### Minisito verticale
Multi-pagina editoriale persuasivo. Struttura obbligatoria:
- **Architettura multi-file:** nav sticky e footer sono iniettati via `render.js`; i contenuti di tutte le pagine vivono in `content.js` (`SITE.pagine`); ogni pagina HTML chiama `renderPage('chiave')`.
- **Hero:** foto di background + doppio overlay gradient Bluette; `min-height: 72vh`; `padding-top: 104px` per clearance nav. Chip lime sopra H1, H1 in Hedvig.
- **Pagina brief / contatti:** fuori dalla nav principale — non compare nell'alberatura del menu. Accessibile solo tramite CTA button nel corpo del sito (es. "Scrivici", "Contattaci").
- **Nav sticky:** IntersectionObserver per highlight voce attiva; voci in sentence case; nessuna voce "Contattaci" nel menu.
- Sezioni tipiche: hero-home, hero-section, info-stats, cards, text, cta-banner.
- Tono editoriale persuasivo, non verbatim: sintetizzare e riformulare.

### Presentazione a scroll
Una sola idea per sezione — sembra una presentazione, sfrutta il web.
- **Densità testo:** minima. Ogni sezione ha un messaggio, non un paragrafo. Se il contenuto originale è lungo → schematizzarlo (lista, tabella, confronto). Mai riversare testo verbatim.
- **Interattività obbligatoria:** hover reveal, animazioni on-scroll (IntersectionObserver), tabelle interattive. Il vantaggio rispetto a un PDF sta tutto qui: sfruttarlo.
- **Navigazione:** dot-nav laterale o indicatori di progresso.
- **Sezioni:** full-viewport o quasi (`min-height: 90vh`), fondo alternato (bianco / `--oe-bg-dark`).
- Regola pratica: se si può stampare e sembrare un documento Word → ha troppo testo. Sforbiciare.

### Web report
Testi verbatim — fedeltà al contenuto originale, interattività come supporto.
- **Hero immersiva**: `min-height ~1100px` (≈ full-viewport su laptop), contenuti centrati; effetto immersivo, NON above-the-fold. Full-bleed a fondo accento con visual a destra (default) o copertina 2-col su bianco.
- **TOC laterale** con scroll-spy (IntersectionObserver); voci in sentence case; sezioni con `id`.
- **Accordion** per sezioni espandibili; **callout** per citazioni/dati chiave.
- Embed Flourish nativo (`figure-flourish`; `embed.js` incluso una volta sola).
- Footer variante **"analisi"** (con blocco CONDIZIONI D'USO).
- Overlay Civiqa via `.theme-civiqa` sulla root.

### Analisi one-page
Il dato parla da solo — testo essenziale.
- KPI in prima fila (`.oe-kpi`), grafici Chart.js, commento sintetico sotto ogni chart.
- Figure label obbligatoria (`.oe-figure-label`: GRAFICO 1, TABELLA 1, ecc.).
- Numeri in locale IT (`useGrouping: "always"`; migliaia `.`, decimale `,`).
- Footer variante "analisi".

### Dashboard
App-like, scansione istantanea.
- Filtri che ricalcolano KPI + grafici + tabella in tempo reale; tabella ordinabile.
- Numeri KPI SEMPRE **neri** (`--oe-black`), mai Bluette (vedi checks.md #k).
- Font minimo 12px ammesso (unico archetipo con questa eccezione).
- Nessun elemento decorativo: zero fronzoli, zero hero, zero cta-banner.

### Repository
Trovabilità prima di tutto.
- Ricerca full-text + filtri combinabili (brand / obiettivo / formato).
- CTA download in Bluette (`.oe-btn --primary`), mai in nero.
- Card asset senza bordo (ombra DS), con tipo, formato e data visibili immediatamente.

## Tipi di asset web e kit di riferimento

| Tipo | Kit / scaffold | Natura |
|---|---|---|
| Analisi one-page | `kits/analisi-one-page/` | data-driven (Chart.js) |
| Minisito verticale | `kits/minisito-verticale/` | editoriale multi-sezione |
| Web report | `kits/web-report/` | editoriale verbatim |
| Presentazione a scroll | `kits/presentazione-scroll/` | narrativo |
| Dashboard | `ui_kits/dashboard/` (v4) | data-driven |
| Repository | `kits/repository/` | elenco asset + download |

## Brand

**OE (default)** — nessuna classe extra. Accenti: Bluette + Lime via token semantici.

**Civiqa** — applica `class="theme-civiqa"` sulla root (`<body>` o `<html>`). Rimappa
automaticamente tutti i token `--oe-accent*`, `--oe-pop*` e `--oe-bg-*` → scala Blu Civiqa
(`#0000FF`). Non servono override per-componente. Logo: `logo-civiqa-white.svg` / `-black.svg`
(in `ds-kit/components/`); mai il logo OE in un asset Civiqa.

## Dove vivono le cose

**Consumabile (ciò che i kit linkano) — `ds-kit/` embeddato**, copia pinnata dal DS v4.0 (v0.4.0, `src/`):
```
Skill/oe-frontend-brand/ds-kit/
├── colors_and_type.css   ← token --oe-* e --cv-* + .theme-civiqa (da src/styles)
├── components.css        ← stili componenti .oe-* (da src/components)
├── fonts.css + fonts/    ← Atkinson Next/Mono, Hedvig
├── components/           ← loghi OE + Civiqa (white/black)
├── chart-preset.js · image-slot.js · tokens.js
└── footers/              ← footer standard + analisi
```
**Fonte upstream (solo per aggiornare l'embeddato, NON a runtime):** `Design System/design-system v4.0/`
(`src/styles/colors_and_type.css`, `src/components/components.css`, `CHANGELOG.md`). `public/kit/` è il kit
Figma **congelato** (senza `theme-civiqa`) → non usarlo come consumabile.
