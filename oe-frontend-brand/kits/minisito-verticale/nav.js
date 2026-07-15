/* ============================================================================
   KIT MINISITO VERTICALE — navigazione condivisa (una sola fonte per tutte le pagine)
   • 1° livello: menu delle PAGINE (config PAGES) con .active sulla pagina corrente.
   • 2° livello: ancore di SEZIONE della pagina, AUTO-generate da section[id][data-label]
     + scroll-spy (ancora attiva). Se la pagina non ha sezioni data-label, resta nascosto.
   • Footer condiviso. Brand: logo OE/Civiqa gestito via CSS (.theme-civiqa).
   Uso in ogni pagina: <div id="sitenav"></div> in cima, <div id="sitefooter"></div> in fondo,
   <script src="nav.js"></script> prima di </body>. Marca le sezioni con id + data-label="Etichetta".
   ============================================================================ */
(function () {
  /* ── CONFIG: le pagine del minisito (modifica qui) ───────────────────────── */
  var PAGES = [
    { href: 'index.html',            label: 'Home' },
    { href: 'pagina-contenuto.html', label: 'Sezione esempio' }
  ];
  var C = '../../ds-kit/components/';
  var cur = (location.pathname.split('/').pop() || 'index.html');

  /* ── NAV 1° livello ──────────────────────────────────────────────────────── */
  var mount = document.getElementById('sitenav');
  if (mount) {
    var links = PAGES.map(function (p) {
      return '<li><a href="' + p.href + '"' + (p.href === cur ? ' class="active"' : '') + '>' + p.label + '</a></li>';
    }).join('');
    mount.outerHTML =
      '<nav class="nav"><div class="nav__inner">' +
        '<a class="nav__logo" href="index.html" aria-label="Home">' +
          '<img class="logo-oe" src="' + C + 'logo-black.svg" alt="OpenEconomics">' +
          '<img class="logo-cv" src="' + C + 'logo-civiqa-black.svg" alt="Civiqa">' +
        '</a>' +
        '<ul class="nav__links">' + links + '</ul>' +
      '</div><div class="nav__sub" id="navSub"></div></nav>';
  }

  /* ── NAV 2° livello: auto da section[id][data-label] + scroll-spy ─────────── */
  var sub = document.getElementById('navSub');
  var sections = Array.prototype.slice.call(document.querySelectorAll('section[id][data-label]'));
  if (sub && sections.length) {
    var inner = document.createElement('div');
    inner.className = 'nav__sub-inner';
    sections.forEach(function (s) {
      var a = document.createElement('a');
      a.href = '#' + s.id; a.textContent = s.dataset.label; a.dataset.for = s.id;
      inner.appendChild(a);
    });
    sub.appendChild(inner);
    sub.classList.add('is-visible');
    var subLinks = inner.querySelectorAll('a');
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) {
          subLinks.forEach(function (a) { a.classList.toggle('active', a.dataset.for === e.target.id); });
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach(function (s) { spy.observe(s); });
  }

  /* ── FOOTER condiviso ────────────────────────────────────────────────────── */
  var f = document.getElementById('sitefooter');
  if (f) {
    f.outerHTML =
      '<footer class="footer"><div class="footer__inner">' +
        '<div class="footer__top">' +
          '<img class="logo-oe" src="' + C + 'logo-white.svg" alt="OpenEconomics" style="height:30px">' +
          '<img class="logo-cv" src="' + C + 'logo-civiqa-white.svg" alt="Civiqa" style="height:30px">' +
          '<p class="footer__tagline">Enabling adaptation. Empowering impact.</p>' +
        '</div>' +
        '<div class="footer__bar"><span>www.openeconomics.eu · © OpenEconomics Srl ' + (new Date().getFullYear()) + '</span>' +
          '<span>Privacy policy · Cookie policy</span></div>' +
      '</div></footer>';
  }

  /* ── reveal-on-scroll ────────────────────────────────────────────────────── */
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px', threshold: .08 });
  document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
})();
