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

  /* 5) Tables vivantes : clic sur un <th class="sortable"> réordonne les <tr>
   *    du corps par la valeur data-sort de la colonne (cellIndex). On DÉPLACE
   *    des lignes déjà rendues — aucune donnée reconstruite (cf. discipline). */
  function sortNumber(cell) {
    var v = cell ? parseFloat(cell.getAttribute("data-sort")) : NaN;
    return isNaN(v) ? Infinity : v; /* valeurs absentes → en fin de tri */
  }
  Array.prototype.forEach.call(
    document.querySelectorAll("table.sortable"),
    function (table) {
      var heads = table.querySelectorAll("thead th.sortable");
      Array.prototype.forEach.call(heads, function (th) {
        th.addEventListener("click", function () {
          var tbody = table.tBodies[0];
          if (!tbody) return;
          var col = th.cellIndex;
          var asc = th.getAttribute("aria-sort") !== "ascending";
          var rows = Array.prototype.slice.call(tbody.rows);
          rows.sort(function (a, b) {
            var x = sortNumber(a.cells[col]);
            var y = sortNumber(b.cells[col]);
            return asc ? x - y : y - x;
          });
          rows.forEach(function (r) {
            tbody.appendChild(r);
          });
          Array.prototype.forEach.call(heads, function (h) {
            h.setAttribute("aria-sort", "none");
          });
          th.setAttribute("aria-sort", asc ? "ascending" : "descending");
          /* renuméroter la colonne de rang (#) selon le nouvel ordre */
          var n = 1;
          Array.prototype.forEach.call(tbody.rows, function (r) {
            var rk = r.querySelector("td.rank");
            if (rk) rk.textContent = String(n++);
          });
        });
      });
    },
  );

  /* 6) Drill-in générique (profil moteur, détail document) : un lien dont la
   *    cible est un .drill-panel le révèle et masque les autres ; « ← retour »
   *    (.drill-back) les masque tous. Sans JS, le panneau s'affiche via :target. */
  var drillPanels = Array.prototype.slice.call(
    document.querySelectorAll(".drill-panel"),
  );
  if (drillPanels.length) {
    function showDrill(id) {
      drillPanels.forEach(function (p) {
        p.hidden = p.id !== id;
      });
      var open = document.getElementById(id);
      if (open) open.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    document.addEventListener("click", function (e) {
      var link = e.target.closest && e.target.closest("a");
      if (!link) return;
      if (link.classList.contains("drill-back")) {
        e.preventDefault();
        drillPanels.forEach(function (p) {
          p.hidden = true;
        });
        return;
      }
      var href = link.getAttribute("href") || "";
      if (href.charAt(0) === "#" && href.length > 1) {
        var target = document.getElementById(href.slice(1));
        if (target && target.classList.contains("drill-panel")) {
          e.preventDefault();
          showDrill(href.slice(1));
        }
      }
    });
  }

  /* 7) Bascule galerie ⇄ liste (vue Documents). Sans JS, la grille (entrée) est
   *    visible et la liste cachée ; un bouton montre l'une, cache l'autre. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".view-toggle"),
    function (group) {
      var scope = group.parentNode;
      var btns = group.querySelectorAll(".vt-btn");
      Array.prototype.forEach.call(btns, function (btn) {
        btn.addEventListener("click", function () {
          var want = btn.getAttribute("data-view");
          Array.prototype.forEach.call(btns, function (b) {
            var on = b === btn;
            b.classList.toggle("on", on);
            b.setAttribute("aria-pressed", on ? "true" : "false");
          });
          Array.prototype.forEach.call(
            scope.querySelectorAll(".doc-view"),
            function (v) {
              v.hidden = v.getAttribute("data-view") !== want;
            },
          );
        });
      });
    },
  );
})();
