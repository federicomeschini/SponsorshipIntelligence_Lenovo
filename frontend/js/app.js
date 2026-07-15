/* App shell: FIFA-first hash router, chapter navigation and topbar. */
(function () {
  const { el } = UI;
  const NAV_ICONS = {
    overview: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    return: '<path d="M12 2v20M17 7a4 4 0 0 0-4-2h-2a4 4 0 0 0 0 8h2a4 4 0 0 1 0 8h-2a4 4 0 0 1-4-2"/>',
    proof: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="12" r="3"/><path d="M9 6h4a6 6 0 0 1 2 3.5M9 18h4a6 6 0 0 0 2-3.5"/>',
    reach: '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19 5a10 10 0 0 1 0 14M5 19A10 10 0 0 1 5 5"/>',
    attention: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    perception: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="3"/>',
    about: '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/>',
  };
  const SUBS = {
    overview: "Lenovo \u00d7 FIFA \u00b7 Executive decision case",
    return: "Financial value \u00b7 scenarios & ROI",
    proof: "Counterfactual test \u00b7 without-FIFA baseline",
    reach: "FIFA exposure delivered",
    attention: "Search & media salience",
    perception: "Brand Index & audience funnel",
    about: "Method, data status & evidence base",
  };

  const nav = document.getElementById("nav");
  COPY.nav.forEach((n) => {
    if (n.group) nav.append(el("div", "oe-dashnav__title", n.group));
    const b = el("button", "oe-dashnav__item",
      `<svg viewBox="0 0 24 24" aria-hidden="true">${NAV_ICONS[n.id]}</svg><span>${n.label}</span>`);
    b.type = "button";
    b.dataset.screen = n.id;
    b.addEventListener("click", () => (location.hash = "#/" + n.id));
    nav.append(b);
  });

  const body = document.getElementById("screen");
  const title = document.getElementById("topbar-title");
  const sub = document.getElementById("topbar-sub");

  function route() {
    const id = (location.hash.replace(/^#\/?/, "") || "overview").split("?")[0];
    const screen = window.SCREENS[id] ? id : "overview";
    document.querySelectorAll(".oe-dashnav__item").forEach((b) =>
      b.classList.toggle("is-active", b.dataset.screen === screen));
    const navItem = COPY.nav.find((n) => n.id === screen);
    title.textContent = navItem.label;
    sub.textContent = SUBS[screen];
    CH.destroyAll();
    body.innerHTML = "";
    window.SCREENS[screen](body);
    UI.animateIn(body);
    document.querySelector(".dash-main").scrollTo?.(0, 0);
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", route);
  route();
})();