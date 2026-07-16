/* Home — landing page: platform title and the FIFA partner programmes.
   Only the Lenovo programme is live in this demo; the others are shaded. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.home = function (root) {
  const C = COPY.home, { el } = UI;

  const page = el("section", "landing");

  const head = el("div", "landing__head reveal");
  const logo = el("img", "landing__logo");
  logo.src = "ds-kit/components/logo-black.svg";
  logo.alt = "OpenEconomics";
  head.append(logo);
  const fifa = el("img", "landing__fifa");
  fifa.src = "assets/logos/fifa.svg";
  fifa.alt = "FIFA";
  head.append(fifa);
  page.append(head);

  const intro = el("div", "landing__intro reveal");
  intro.append(el("h1", "landing__title", C.title));
  intro.append(el("p", "landing__sub", C.sub));
  page.append(intro);

  const gridHead = el("div", "landing__grid-head reveal");
  gridHead.append(el("span", "oe-eyebrow", C.gridTitle));
  page.append(gridHead);

  const brandLogo = (b) => {
    const box = el("span", "brand-card__logo");
    const img = el("img");
    img.src = "assets/logos/" + b.id + ".svg";
    img.alt = b.name + " logo";
    img.loading = "lazy";
    box.append(img);
    return box;
  };

  const grid = el("div", "landing-grid");
  C.brands.forEach((b) => {
    if (b.active) {
      const card = el("button", "brand-card brand-card--active reveal");
      card.type = "button";
      card.setAttribute("aria-label", b.name + " — " + C.openLabel);
      card.append(el("span", "brand-card__chip", C.activeChip));
      card.append(brandLogo(b));
      card.append(el("strong", "brand-card__name", b.name));
      card.append(el("span", "brand-card__cat", b.category));
      card.append(el("span", "brand-card__action", C.openLabel));
      card.addEventListener("click", () => (location.hash = "#/overview"));
      grid.append(card);
    } else {
      const card = el("div", "brand-card brand-card--off reveal");
      card.setAttribute("aria-disabled", "true");
      card.append(brandLogo(b));
      card.append(el("strong", "brand-card__name", b.name));
      card.append(el("span", "brand-card__cat", b.category));
      grid.append(card);
    }
  });
  page.append(grid);

  const foot = el("div", "landing__foot");
  foot.append(el("span", "", COPY.demoNotice + " · third-party marks belong to their owners"));
  foot.append(el("span", "", "www.openeconomics.eu · © OpenEconomics Srl " + new Date().getFullYear()));
  page.append(foot);

  root.append(page);
};
