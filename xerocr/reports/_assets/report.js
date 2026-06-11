/* Rapport autonome — interactivité légère : navigation clavier + palette.
 *
 * Script STATIQUE (son sha256 est épinglé dans la CSP des réponses /reports/).
 * Zéro réseau, zéro dépendance. Tout est progressif : sans JS, le rapport reste
 * lisible (le sommaire à ancres natives suffit à naviguer). */
(function () {
  "use strict";

  /* 1) Palette daltonien : ?palette=cb → classe sur <html>. Les accents pilotés
   *    par variables CSS (data-bars, verdicts, deltas) basculent vers une paire
   *    bleu/orange distinguable ; les badges moteur portent déjà une LETTRE, donc
   *    restent identifiables sans couleur. */
  try {
    var pal = new URLSearchParams(window.location.search).get("palette");
    if (pal === "cb" || pal === "daltonien") {
      document.documentElement.classList.add("palette-cb");
    }
  } catch (e) {
    /* URLSearchParams indisponible (très vieux navigateur) : on ignore. */
  }

  /* 2) Navigation clavier (vim) : j = section suivante, k = précédente.
   *    Volontairement PAS les flèches — elles doivent rester le défilement natif. */
  var blocks = Array.prototype.slice.call(document.querySelectorAll(".r-block"));
  if (!blocks.length) return;
  var current = -1;

  function focusBlock(index) {
    current = index < 0 ? 0 : index > blocks.length - 1 ? blocks.length - 1 : index;
    var block = blocks[current];
    block.scrollIntoView({ behavior: "smooth", block: "start" });
    var head = block.querySelector("h1, h2, h3");
    if (head) {
      head.setAttribute("tabindex", "-1");
      head.focus({ preventScroll: true });
    }
  }

  document.addEventListener("keydown", function (e) {
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "j") {
      focusBlock(current + 1);
      e.preventDefault();
    } else if (e.key === "k") {
      focusBlock(current - 1);
      e.preventDefault();
    }
  });
})();
