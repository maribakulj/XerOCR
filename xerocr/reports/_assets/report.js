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

  /* 3) Onglets (enrichissement progressif). Le serveur rend TOUS les panneaux
   *    (sans JS : empilés et visibles, les onglets sont de simples ancres). Ici
   *    on n'affiche qu'un panneau à la fois et on câble la navigation ARIA. */
  var tablist = document.querySelector(".report-tabs");
  if (tablist) {
    var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (t) {
      return document.getElementById(t.getAttribute("aria-controls"));
    });

    function activate(index, focusTab) {
      tabs.forEach(function (t, j) {
        var on = j === index;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.classList.toggle("on", on);
        t.tabIndex = on ? 0 : -1;
        if (panels[j]) panels[j].hidden = !on;
      });
      if (focusTab && tabs[index]) tabs[index].focus();
    }

    /* Onglet initial : celui désigné par le hash (#panel-x), sinon le premier. */
    var initial = 0;
    var hash = (window.location.hash || "").slice(1);
    tabs.forEach(function (t, j) {
      if (t.getAttribute("aria-controls") === hash) initial = j;
    });
    activate(initial, false);

    tabs.forEach(function (t, i) {
      t.addEventListener("click", function (e) {
        e.preventDefault();
        activate(i, false);
      });
      t.addEventListener("keydown", function (e) {
        var n = null;
        if (e.key === "ArrowRight") n = (i + 1) % tabs.length;
        else if (e.key === "ArrowLeft") n = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") n = 0;
        else if (e.key === "End") n = tabs.length - 1;
        if (n !== null) {
          e.preventDefault();
          activate(n, true);
        }
      });
    });
  }

  /* 4) Glossaire : le lien-ancre du chrome ouvre le <dialog> en MODALE (showModal,
   *    Échap + ::backdrop natifs). Sans JS, l'ancre déclenche le repli :target
   *    (panneau centré). Fermeture : bouton [data-close] ou clic sur le fond. */
  var glossaryDialog = document.getElementById("glossary-dialog");
  if (glossaryDialog && typeof glossaryDialog.showModal === "function") {
    var glossaryLink = document.querySelector('[href="#glossary-dialog"]');
    if (glossaryLink) {
      glossaryLink.addEventListener("click", function (e) {
        e.preventDefault();
        glossaryDialog.showModal();
      });
    }
    glossaryDialog.querySelectorAll("[data-close]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        glossaryDialog.close();
      });
    });
    glossaryDialog.addEventListener("click", function (e) {
      if (e.target === glossaryDialog) glossaryDialog.close();
    });
  }
})();
