/* V7 — About the platform: causal chain, data credentials, how we measure. */
window.SCREENS = window.SCREENS || {};
window.SCREENS.about = function (root) {
  const C = COPY.about, { el } = UI;

  UI.screenHead(root, { kicker: C.kicker, title: C.title });

  const chain = el("div", "chain reveal");
  C.chain.forEach((n, i) => {
    if (i) chain.append(el("span", "chain-arrow", "→"));
    chain.append(el("div", "chain-node", n));
  });
  root.append(chain);
  root.append(el("p", "panel-note reveal", C.chainNote));

  const eyebrow = el("div", "reveal");
  eyebrow.append(el("span", "oe-eyebrow", "Evidence base"));
  root.append(eyebrow);
  const creds = el("div", "cred-row");
  C.sources.forEach(([b, s]) => {
    const c = el("div", "cred reveal");
    c.append(el("b", "", b));
    c.append(el("span", "", s));
    creds.append(c);
  });
  root.append(creds);

  const eyebrow2 = el("div", "reveal");
  eyebrow2.append(el("span", "oe-eyebrow", "How we measure"));
  root.append(eyebrow2);
  const prose = el("div", "prose reveal");
  C.how.forEach((p) => prose.append(el("p", "", p)));
  root.append(prose);
};
