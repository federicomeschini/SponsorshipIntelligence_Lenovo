# Kit — Presentazione a scroll

Scaffold per una presentazione **scroll-telling** on-brand. Si **edita direttamente l'HTML** di `template.html`: si scelgono le slide dai blocchi pronti e si riempiono con testi essenziali. Rif.: "Progetti marketing AI" (OE), Accade investor (Civiqa).

## Carattere dell'archetipo
- **Sintetico**: una idea per sezione, testo essenziale (non muri di testo). Se il contenuto è lungo → sintetizzare o spostare su web report.
- **Interattivo**: sfrutta scroll-snap, **dot-nav con scroll-spy**, **reveal-on-scroll**, hover sulle card. È il valore aggiunto rispetto a una slide statica.
- Slide **immersive** (`min-height:92vh`) con snap: la sezione successiva "sbircia" e invita a scorrere.

## Come si compila
1. Copia `kits/presentazione-scroll/` nel progetto, insieme a `ds-kit/` (path `../../ds-kit/`).
2. **Brand**: OE → nessuna classe (default). Civiqa → aggiungi `class="theme-civiqa"` al `<body>` (accento → Blu; il logo Civiqa si attiva da solo).
3. Componi le slide scegliendo tra i blocchi: **hero fotografico**, **statement** (accento pieno + bullet), **cards** (con sub-chip es. Step N), **comparison**, **table**, **cta**. Ogni `<section>` ha un `id` → entra nel dot-nav.
4. **Hero**: imposta la foto in `.hero__bg` (`background-image:url('assets/hero.jpg')`); l'overlay accento (tematizzato via `color-mix`) garantisce la leggibilità del titolo. Senza foto resta il pattern a punti.
5. Testi essenziali; i dati tabellari → `table.tbl` (mai frammentati in card).
6. Esegui `references/checks.md`, poi apri `template.html` nel browser.

## Chip a due livelli
- **Capitolo (primaria):** `.chip-cap` = **lime** (anche in Civiqa, per gli eyebrow di sezione). Mono UPPERCASE.
- **Paragrafo/step (secondaria):** `.subchip` = accento di brand (Bluette OE / Blu Civiqa), testo bianco — es. "Step 1".
- `.chip` = variante di brand (lime OE → blu Civiqa) per pretitoli non-capitolo.

## Meccanica (già cablata nel JS)
- **scroll-snap** verticale (`proximity`).
- **dot-nav** a destra con **scroll-spy** (IntersectionObserver, dot attivo).
- **reveal-on-scroll**: aggiungi `class="reveal"` a una slide/elemento per animarne l'ingresso.

## Brand & token
Usa i token del DS (`--oe-bluette-*`, `--oe-lime-*`) via alias locali su `body` (`--accent`, `--pop`…), rimappati da `.theme-civiqa`. **Niente token custom paralleli** (es. `--c-*`): sempre agganciati al DS. Componenti riusabili in `ds-kit/components.css`.

## CTA
Arrow-tile con **icona DS** (SVG), mai freccia unicode `→`. Tile bianca + testo/arrow accento su fondo scuro/accento (contrasto in entrambi i brand). Gap 4px, altezza 52px.

## Footer
Logo (OE/Civiqa auto in base al brand) + tagline + barra legale. Per report/documenti usare invece la variante "analisi" (`ds-kit/footers/`).
