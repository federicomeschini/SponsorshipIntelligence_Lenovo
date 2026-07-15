/* Struttura dati per l'archetipo Analisi one-page. Sostituire i valori coi dati reali. */
window.ANALISI = {
  titolo: "Titolo dell'analisi",
  pretitolo: "OBIETTIVI ANALISI",
  kpi: [
    { label: "PIL attivato", valore: 1234, suffix: " M€" },
    { label: "Occupazione", valore: 5678, suffix: " ULA" }
  ],
  grafici: [
    {
      id: "grafico1", tipo: "bar", titolo: "Andamento",
      labels: ["2023","2024","2025"],
      serie: [{ nome: "Valore", dati: [10,20,30] }]
    }
  ]
};
