# Intake — domande guidate (linguaggio per il collega: "tipo di asset web")

Poni le domande con `AskUserQuestion`. Salta quelle a cui l'utente ha già risposto.

## Domande base
1. **Per quale brand?** → OpenEconomics / Civiqa *(default: OpenEconomics)*
   - **Civiqa** → applica la classe **`.theme-civiqa`** sulla root (`<body class="theme-civiqa">`):
     rimappa in automatico l'accento (Bluette + Lime) → **Blu Civiqa `#0000FF`** su tutti i componenti.
     Usa il **logo Civiqa** (`ds-kit/components/logo-civiqa-white.svg` / `-black.svg`), MAI il logo OE.
     Regola DS: *Civiqa non usa il Lime* (l'accento "pop" diventa blu). **Eccezione**: il **lime resta ammesso
     per le chip di capitolo** negli artefatti complessi (vedi "Chip a due livelli" sotto).
2. **Che tipo di asset web?** → Analisi one-page · Minisito verticale · Web report · Presentazione a scroll · Dashboard · Repository
3. **Titolo e tema** del progetto.
4. **Vuoi solo i titoli di sezione o anche i pretitoli (chip)?** Vedi "Chip a due livelli" sotto.
5. **Quali sono i titoli (e gli eventuali pretitoli) delle sezioni?**
   Convenzione: PRETITOLO/CHIP IN STAMPATELLO MAIUSCOLO / Titolo in sentence case.
   Le **voci di menu/nav** invece in **sentence case** (es. "Introduzione"), mai tutto maiuscolo.
6. **Materiali disponibili?** Vedi "Input testi vs riferimento" sotto.
7. **Footer** → default per tipo (Analisi → footer analisi; gli altri → footer standard); sovrascrivibile.

## Input testi vs riferimento (REGOLA — non confondere le fonti)
- **Fonte dei testi = un file di testo**: `.md` / `.docx` / Excel / `.pptx` / testo incollato. I testi vanno presi **VERBATIM** da qui (nessuna parafrasi/riordino).
- **PDF e immagini = SOLO riferimento di layout/grafica** (struttura, chip, impaginazione, posizione delle figure). **Non** usare il PDF come fonte testuale: l'estrazione da PDF è **inaffidabile** (spaziatura inter-lettera, ordine di lettura scrambolato che separa chip e titoli dai corpi).
- Se l'utente fornisce **solo un PDF**: estrai il testo, **normalizzalo** (ricomponi parole/ordine) e **chiedi conferma** della fedeltà prima di impaginare; meglio ancora, chiedi un `.md`/`.docx`.

## Chip a due livelli
- **Chip di capitolo (primaria)** — sopra un H1/H2 di sezione/capitolo. Default = **lime** (OE e anche Civiqa, come eccezione ammessa per artefatti complessi e chaptered). Mono UPPERCASE.
- **Chip di paragrafo (secondaria / sub-chip)** — dentro una sezione, etichetta un blocco/paragrafo. = **accento di brand** (Bluette per OE, Blu per Civiqa), testo bianco. Mono UPPERCASE.
- Per artefatti **semplici** (non chaptered): usa solo la chip di brand di default (lime→blu sotto Civiqa, da DS). Il lime di capitolo è opt-in, **da prompt** quando serve la gerarchia capitolo+paragrafo.

## Domande condizionali per tipo
- **Analisi / Dashboard** →
  - "Dove sono i dati?" (Excel/CSV/incollati/.pptx/.md) + "Quali KPI/grafici principali?"
  - **"Come saranno i grafici?"** *(chiedi sempre)* → **(a) Chart.js nativo** (default per analisi/dashboard, HTML-native, on-brand via `chart-preset.js`) · **(b) embed Flourish** · **(c) immagini statiche** (PNG @2x). Si può **mischiare** per figura. Nota: nelle *analisi* spesso i grafici sono HTML-native (Chart.js/SVG), non Flourish.
  - **Se si REPLICA una pagina esistente:** analizza prima l'**artefatto originale** e **replica la soluzione adottata** (Flourish vs HTML-native vs immagini), invece di assumere una modalità.
  - *(Dashboard)* "Serve la shell app (sidebar nav + topbar + filtri) o un layout a sezioni?" → usa `.oe-shell`/`.oe-dashnav`/`.oe-topbar` da `components.css`.
- **Web report** →
  - "C'è un documento fonte di verità (`.md`/`.docx`)?" → testi VERBATIM.
  - **"Come saranno i grafici/mappe?"** *(G10 — chiedi sempre)* → **(a) embed Flourish** · **(b) immagini statiche** (PNG @2x) · **(c) Chart.js nativo**. Si può mischiare per figura. Nota: Flourish richiede internet; per offline totale usare immagini o Chart.js.
  - "Nav: TOC laterale (consigliata su desktop largo) o top-nav orizzontale?"
- **Minisito verticale / Presentazione** → "Quali macro-sezioni/messaggi?"
- **Repository** → "Quali asset, e con quale tassonomia (brand/obiettivo/formato)?"

## Immagini
- Le immagini le fornisce il collega; in mancanza, si attinge a `Brand Identity/.../06. IMG DATABASE`.
- Dove manca un'immagine, inserisci uno **slot con caricamento** (`ds-kit/image-slot.js`).
- Trattamento brand (gradiente Bluette / pixel) proposto caso per caso, mai forzato.
- Icone: sempre dalla libreria DS, mai casuali o emoji.
- **Logo:** OE → `ds-kit/components/logo-white.svg`/`logo-black.svg`; Civiqa → `logo-civiqa-white.svg`/`logo-civiqa-black.svg` (bianco su fondi scuri, nero su fondi chiari).
