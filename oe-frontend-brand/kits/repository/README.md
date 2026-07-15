# Kit — Repository

Scaffold per una libreria interna di asset, con filtri e download (rif.: Marketing Kit OE). Net-new.

## Come si compila
1. Copia la cartella `kits/repository/` nel progetto, insieme a `ds-kit/`.
2. In `data.example.js` (rinomina in `data.js`) metti l'elenco `asset` (titolo, brand, obiettivo, formato,
   `href` = file da scaricare) e le `facce` (le opzioni dei 3 filtri).
3. Metti i file scaricabili nella cartella del progetto e punta `href` ad essi (es. `files/brochure.pdf`).
4. `brand: "oe"` oppure `"civiqa"` (Civiqa richiede l'overlay del DS).
5. Apri `index.html`: ricerca + 3 filtri (brand/obiettivo/formato) restringono la griglia in tempo reale;
   ogni card ha il bottone **Scarica**.

## Carattere (spec §5.1)
- **Funzionale**: priorità a trovabilità (ricerca + filtri) e azione (download).
- Card asset **senza bordo** (superficie + ombra). Bottone download in **Bluette** (mai nero).
- Le select e la ricerca sono form input → hanno bordo (non sono card).

## Footer
Footer **slim** (barra copyright + policy), adatto a un tool interno.
