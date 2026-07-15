# Kit — Dashboard

Scaffold per una dashboard HTML interattiva on-brand (net-new).

## Come si compila
1. Copia la cartella `kits/dashboard/` nel progetto, insieme a `ds-kit/`.
2. In `data.example.js` (rinomina in `data.js`) metti il tuo **dataset di righe**, la definizione del
   **filtro** (campo + opzioni), i **KPI** (count/avg/sum), i **grafici** (campo) e le colonne tabella.
3. Brand: **OE** = nessuna classe; **Civiqa** = `class="theme-civiqa"` su `<body>` (accento → blu, automatico).
4. Apri `index.html`: i filtri ricalcolano KPI, grafici e tabella in tempo reale; le intestazioni
   tabella ordinano i dati.

## App-shell del DS (preferibile per dashboard vere)
Per dashboard con navigazione laterale usa i componenti di `components.css`: **`.oe-shell`** (sidebar + contenuti),
**`.oe-dashnav`** (nav laterale — voci in **sentence case**), **`.oe-topbar`** (barra alta + filtri),
**`.oe-kpi`**, **`.oe-table`** (+ `--kpi`/`--capex`/`--moltipl`), **`.oe-panel`** (grafico + commento), `.oe-badge`.
Il `dashboard.css` di questo kit è la versione minima a sezioni; per shell complete attingi ai componenti DS.

## Carattere (spec §5.1)
- **Scansione rapida, zero fronzoli**: numeri e grafici leggibili a colpo d'occhio.
- È l'UNICO tipo che può usare **font < 16px** (qui 14-15px) per densità — **mai sotto 12px**.
- KPI e pannelli **senza bordo** (superficie + ombra). Filtro attivo in Bluette.
- **Numeri KPI NERI** (`--oe-black`): `.oe-kpi__value` nel DS è Bluette → fai l'override nelle dashboard.
- **Mai il nero come sfondo** (sezioni scure = Bluette 900). **Icone** dalla libreria DS, mai glifi/emoji.
- Contenuto ibrido (testo + dati): mix di blocchi **discorsivi** (card/prose) e **visivi** (KPI/grafici/tabelle).

## Dati e grafici
- I grafici sono **Chart.js** (colori dalla palette OE). Richiede internet per Chart.js da CDN.
- KPI calcolati dalle righe filtrate (`count`/`avg`/`sum`). Formattazione numeri IT via `OE.formatNumber`.

## Footer
Footer **slim** (barra copyright + policy), adatto al contesto app — non la tagline marketing.
