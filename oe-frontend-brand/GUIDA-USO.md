# Guida d'uso — skill `oe-frontend-brand`

Crea **asset web on-brand OpenEconomics** (HTML che si apre nel browser, senza installare nulla), guidandoti passo passo. Pensata anche per chi non è tecnico.

---

## Quando usarla
Quando devi creare — o **allineare al brand** — un oggetto web. Sei tipi di asset:

| Tipo di asset web | Quando |
|---|---|
| **Analisi one-page** | mostrare un'analisi con dati e grafici |
| **Presentazione a scroll** | una presentazione che scorre, sintetica e d'impatto |
| **Web report** | la versione web di un report (testi fedeli + interattività) |
| **Minisito verticale** | un mini-sito multi-pagina (marketing/verticale) |
| **Dashboard** | cruscotto con KPI, grafici e filtri |
| **Repository** | libreria di asset con ricerca, filtri e download |

## Due modi di usarla
1. **Crea nuovo** — parti da zero: la skill ti fa qualche domanda e costruisce l'asset.
2. **Allinea al brand** — hai già un oggetto web e vuoi portarlo nello stile OE: fornisci il **codice
   sorgente** e chiedi di applicare il design system (font, colori, regole).

## Come si chiede bene (struttura del prompt)
> Voglio **[creare / allineare al brand]** un **[tipo di asset web]** per **[OpenEconomics / Civiqa]**.
> Titolo/tema: **[…]**.
> Sezioni (PRETITOLO MAIUSCOLO | Titolo con la sola iniziale maiuscola): **[…]**.
> Materiali: allego **[testi / Excel / PDF / immagini / dati / codice]**.
> [Se analisi/dashboard:] i dati sono in **[file]**; i KPI/grafici principali sono **[…]**.
> [Se web report:] usa i testi **verbatim** dal documento allegato.

Più sei specifico su sezioni, dati e materiali, migliore è il risultato. La skill comunque ti guida con
domande quando manca qualcosa.

## Cosa fornire
- **Brand**: OpenEconomics (default) o Civiqa o Sonar o Externalytics.
- **Contenuti**: testi, dati (Excel/CSV/.pptx/.md), immagini, logo. Per allineare un asset esistente: il **codice**.
- Dove manca un'immagine, la skill mette un **segnaposto** in cui caricarla.

## Come rivedere il risultato (checklist veloce)
- Titoli grandi in serif (Hedvig); pretitoli = box verde TUTTO MAIUSCOLO; titoli con sola iniziale maiuscola.
- Si usano viola (Bluette) e verde (Lime, solo accento); niente colori fuori brand.
- Le **card non hanno bordo** (solo ombra leggera).
- I bottoni (CTA) **non sono mai neri**: verde lime (testo nero) o viola Bluette (testo bianco).
- Le voci di menu hanno **solo la prima lettera maiuscola** (non tutto maiuscolo).
- Niente testo sotto i 16px (eccetto le **dashboard**, dove i **numeri sono neri**).
- Presentazioni: poco testo per sezione, sintetico.

(La checklist completa è in `references/checklist.md`; i controlli tecnici in `references/checks.md`.)

## Buono a sapersi
- Gli output si **aprono con doppio clic** e si pubblicano trascinando la cartella su Netlify Drop.
- I **grafici** (Chart.js) e gli **embed Flourish** caricano da internet; testi e layout funzionano anche offline.
- La variante **Civiqa** (colori blu) è già pronta: si attiva con `class="theme-civiqa"` (lo fa la skill).

## Dove vivono le cose nella skill
- `ds-kit/` — il design system (token, font, componenti): la fonte di verità visiva.
- `kits/` — un modello pronto per ciascuno dei 6 tipi di asset.
- `references/` — intake (le domande), checks (controlli), checklist (revisione), prompt-template.
