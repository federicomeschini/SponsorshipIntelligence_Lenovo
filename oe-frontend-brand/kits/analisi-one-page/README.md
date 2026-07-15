# Kit — Analisi one-page

Scaffold per un'analisi data-driven (rif. Progetto Eni).

## Come si compila
1. Copia l'intera cartella `kits/analisi-one-page/` nella cartella del nuovo progetto, insieme a `ds-kit/`.
2. Riempi `data.example.js` (rinominalo `data.js`) coi dati reali: titolo, pretitolo, KPI, grafici.
3. Aggiungi le sezioni di testo/analisi alternando bianco / `.s-grey` (mai due uguali consecutive).
4. Footer analisi già incluso inline; logo OE bianco da `ds-kit/components/`.
5. Esegui i check in `references/checks.md`, poi apri `template.html` nel browser.

## Note (allineato al DS 260620)
- Linka `components.css` (oltre a fonts/colors): usa i componenti DS, niente token paralleli.
- **Grafici:** default **Chart.js** nativo (`chart-preset.js`, colori/font on-brand) con `fig-label` mono. In alternativa **embed Flourish** o **immagini**: chiedi la modalità in intake; se replichi una pagina esistente, replica la soluzione dell'originale.
- **KPI numeri NERI** (sans tabulari); **chip** lime mono (non clobberare `.oe-eyebrow`, che è sans).
- **Tabelle** branded (`.oe-table`, colonne numeriche `.num`): tieni i dati come tabella, non frammentarli in card.
- **CTA** "tile + label" con gap 4px. Mai nero come sfondo.
- Per le immagini mancanti usa gli slot di `image-slot.js`.
- Carattere: il dato prima di tutto, testo di supporto essenziale.

---

> `image-slot.js` usa un file di stato opzionale `.image-slots.state.json` (sidecar); se assente, gli slot funzionano comunque senza persistenza.
