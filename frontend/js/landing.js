/* Landing page: platform title and the FIFA partner programmes (FE-009).
   Only the Lenovo programme is live; it opens the EROI case dashboard
   (lenovo.html). The others are shaded. Self-contained: no data files. */
(function () {
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const C = {
    title: "FIFA Partnership Intelligence",
    sub: "Measurement, causal proof and financial valuation for FIFA partner programmes. Select a programme to open its dashboard.",
    gridTitle: "Partner programmes",
    openLabel: "Open dashboard →",
    activeChip: "Live",
    brands: [
      { id: "lenovo", name: "Lenovo", category: "Technology partner", href: "lenovo.html" },
      { id: "adidas", name: "adidas", category: "Official partner" },
      { id: "cocacola", name: "Coca‑Cola", category: "Official partner" },
      { id: "visa", name: "Visa", category: "Payment technology partner" },
      { id: "hyundai", name: "Hyundai", category: "Mobility partner" },
      { id: "kia", name: "Kia", category: "Mobility partner" },
      { id: "qatarairways", name: "Qatar Airways", category: "Airline partner" },
      { id: "qatarenergy", name: "QatarEnergy", category: "Energy partner" },
      { id: "aramco", name: "Aramco", category: "Major worldwide partner" },
      { id: "bankofamerica", name: "Bank of America", category: "Tournament sponsor" },
      { id: "mcdonalds", name: "McDonald’s", category: "Tournament sponsor" },
      { id: "verizon", name: "Verizon", category: "Tournament sponsor" },
    ],
  };

  const page = el("section", "landing");
  const head = el("div", "landing__head reveal");
  const logo = el("img", "landing__logo"); logo.src = "ds-kit/components/logo-black.svg"; logo.alt = "OpenEconomics";
  const fifa = el("img", "landing__fifa"); fifa.src = "assets/logos/fifa.svg"; fifa.alt = "FIFA";
  head.append(logo, fifa);
  page.append(head);

  const intro = el("div", "landing__intro reveal");
  intro.append(el("h1", "landing__title", C.title), el("p", "landing__sub", C.sub));
  page.append(intro);

  const gridHead = el("div", "landing__grid-head reveal");
  gridHead.append(el("span", "oe-eyebrow", C.gridTitle));
  page.append(gridHead);

  const brandLogo = (b) => {
    const box = el("span", "brand-card__logo");
    const img = el("img"); img.src = "assets/logos/" + b.id + ".svg"; img.alt = b.name + " logo"; img.loading = "lazy";
    box.append(img);
    return box;
  };
  const grid = el("div", "landing-grid");
  C.brands.forEach((b) => {
    if (b.href) {
      const card = el("button", "brand-card brand-card--active reveal");
      card.type = "button";
      card.setAttribute("aria-label", b.name + " — " + C.openLabel);
      card.append(el("span", "brand-card__chip", C.activeChip), brandLogo(b), el("strong", "brand-card__name", b.name),
                  el("span", "brand-card__cat", b.category), el("span", "brand-card__action", C.openLabel));
      card.addEventListener("click", () => { location.href = b.href; });
      grid.append(card);
    } else {
      const card = el("div", "brand-card brand-card--off reveal");
      card.setAttribute("aria-disabled", "true");
      card.append(brandLogo(b), el("strong", "brand-card__name", b.name), el("span", "brand-card__cat", b.category));
      grid.append(card);
    }
  });
  page.append(grid);

  const foot = el("div", "landing__foot");
  foot.append(el("span", "", "Only the Lenovo programme is live · third-party marks belong to their owners"));
  foot.append(el("span", "", "www.openeconomics.eu · © OpenEconomics Srl " + new Date().getFullYear()));
  page.append(foot);
  document.getElementById("screen").append(page);

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  page.querySelectorAll(".reveal").forEach((n, i) => {
    if (reduced) { n.classList.add("is-in"); return; }
    setTimeout(() => n.classList.add("is-in"), Math.min(i * 70, 560));
  });
})();
