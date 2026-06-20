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

  /* 6) Routeur MAÎTRE/DÉTAIL (profil moteur, détail document) : chaque onglet a
   *    une vue maître (.tab-master : liste/comparaison) et une vue détail
   *    (.tab-detail : fiches). Cliquer un moteur/document ÉCHANGE les deux (vraie
   *    « page », ≠ ancre dans le même défilement) : on cache le maître, on montre
   *    le détail avec UNE seule fiche, on remonte en haut. Le fil d'Ariane
   *    (.drill-back) rétablit le maître et ramène au déclencheur cliqué. Sans JS :
   *    maître + détail empilés, la fiche ciblée s'ouvre via :target. */
  var drillPanels = Array.prototype.slice.call(
    document.querySelectorAll(".drill-panel"),
  );
  if (drillPanels.length) {
    /* Au chargement : masquer toutes les vues détail → seul le maître s'affiche. */
    Array.prototype.forEach.call(
      document.querySelectorAll(".tab-detail"),
      function (d) {
        d.hidden = true;
      },
    );
    /* Déclencheur initial (nom de moteur / carte document) mémorisé par onglet,
       pour y ramener au retour. Les liens préc./suiv. (dans une fiche) n'écrasent
       pas le déclencheur. */
    var lastTrigger = {};
    function openDetail(id, link) {
      var panel = document.getElementById(id);
      if (!panel) return;
      var tabPanel = panel.closest(".tab-panel") || document;
      var master = tabPanel.querySelector
        ? tabPanel.querySelector(".tab-master")
        : null;
      var detail = panel.closest(".tab-detail");
      /* une seule fiche visible dans la vue détail de cet onglet */
      if (detail) {
        Array.prototype.forEach.call(
          detail.querySelectorAll(".drill-panel"),
          function (p) {
            p.hidden = p.id !== id;
          },
        );
        detail.hidden = false;
      }
      if (master) master.hidden = true;
      if (link && tabPanel.id) lastTrigger[tabPanel.id] = link;
      var top = detail || panel;
      if (top.scrollIntoView) top.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    function closeDetail(backLink) {
      var tabPanel = backLink.closest(".tab-panel");
      if (!tabPanel) return;
      var master = tabPanel.querySelector(".tab-master");
      var detail = tabPanel.querySelector(".tab-detail");
      if (detail) detail.hidden = true;
      if (master) master.hidden = false;
      var trig = lastTrigger[tabPanel.id];
      if (trig) trig.scrollIntoView({ behavior: "smooth", block: "center" });
      else if (master) master.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    document.addEventListener("click", function (e) {
      var link = e.target.closest && e.target.closest("a");
      if (!link) return;
      if (link.classList.contains("drill-back")) {
        e.preventDefault();
        closeDetail(link);
        return;
      }
      var href = link.getAttribute("href") || "";
      if (href.charAt(0) === "#" && href.length > 1) {
        var target = document.getElementById(href.slice(1));
        if (target && target.classList.contains("drill-panel")) {
          e.preventDefault();
          openDetail(href.slice(1), link.closest(".drill-panel") ? null : link);
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

  /* 7b) Filtre par strate (galerie documents) : un chip montre les cartes de la
   *     strate choisie (ou toutes pour "*") et masque les autres, dans la grille
   *     sœur. Sans JS, les chips sont inertes et toutes les cartes restent
   *     visibles. On ne masque/affiche que des cartes déjà rendues. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".doc-filter"),
    function (group) {
      var scope = group.parentNode;
      var btns = group.querySelectorAll(".df-btn");
      Array.prototype.forEach.call(btns, function (btn) {
        btn.addEventListener("click", function () {
          var want = btn.getAttribute("data-stratum");
          Array.prototype.forEach.call(btns, function (b) {
            var on = b === btn;
            b.classList.toggle("on", on);
            b.setAttribute("aria-pressed", on ? "true" : "false");
          });
          Array.prototype.forEach.call(
            scope.querySelectorAll(".doc-card"),
            function (card) {
              card.hidden =
                want !== "*" && card.getAttribute("data-stratum") !== want;
            },
          );
        });
      });
    },
  );

  /* 8) Sélecteur de moteur du diff pleine page (détail document) : un bouton
   *    montre le bloc .dd-fulldiff du moteur, cache les autres (scopé au wrap).
   *    Sans JS, les blocs sont empilés et tous visibles. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".dd-engine-tabs"),
    function (tabs) {
      var wrap = tabs.parentNode;
      var btns = tabs.querySelectorAll(".dd-eng-btn");
      function show(engine) {
        Array.prototype.forEach.call(btns, function (b) {
          b.classList.toggle("on", b.getAttribute("data-engine") === engine);
        });
        Array.prototype.forEach.call(
          wrap.querySelectorAll(".dd-fulldiff"),
          function (d) {
            d.hidden = d.getAttribute("data-engine") !== engine;
          },
        );
      }
      Array.prototype.forEach.call(btns, function (btn) {
        btn.addEventListener("click", function () {
          show(btn.getAttribute("data-engine"));
        });
      });
    },
  );

  /* 9) Fac-similé zoomable/pan (détail document) : molette = zoom, glisser =
   *    déplacer, boutons +/−/⤢. Chaque image garde son propre état (zoom z,
   *    décalage ox/oy). Sans JS, l'image s'affiche à taille medium, statique. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".dd-fac-zoom"),
    function (box) {
      var img = box.querySelector(".dd-fac-img");
      if (!img) return;
      var z = 1,
        ox = 0,
        oy = 0,
        drag = null;
      function apply() {
        img.style.transform =
          "scale(" + z + ") translate(" + ox + "px," + oy + "px)";
        box.style.cursor = z > 1 ? "grab" : "zoom-in";
      }
      function zoom(factor) {
        z = Math.max(1, Math.min(5, z * factor));
        if (z === 1) {
          ox = 0;
          oy = 0;
        }
        apply();
      }
      box.addEventListener(
        "wheel",
        function (e) {
          e.preventDefault();
          zoom(e.deltaY < 0 ? 1.15 : 0.87);
        },
        { passive: false },
      );
      box.addEventListener("mousedown", function (e) {
        if (z <= 1 || (e.target.closest && e.target.closest("[data-zoom]"))) return;
        e.preventDefault();
        drag = { x: e.clientX - ox * z, y: e.clientY - oy * z };
        box.style.cursor = "grabbing";
      });
      document.addEventListener("mousemove", function (e) {
        if (!drag) return;
        ox = (e.clientX - drag.x) / z;
        oy = (e.clientY - drag.y) / z;
        apply();
      });
      document.addEventListener("mouseup", function () {
        if (drag) {
          drag = null;
          apply();
        }
      });
      Array.prototype.forEach.call(
        box.querySelectorAll("[data-zoom]"),
        function (btn) {
          btn.addEventListener("click", function () {
            var k = btn.getAttribute("data-zoom");
            if (k === "in") zoom(1.25);
            else if (k === "out") zoom(0.8);
            else {
              z = 1;
              ox = 0;
              oy = 0;
              apply();
            }
          });
        },
      );
      apply();
    },
  );
})();
