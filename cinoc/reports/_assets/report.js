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
  var hasDocTemplates = !!document.querySelector("template[data-doc]");
  if (drillPanels.length || hasDocTemplates) {
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
    function modeKey(scope) {
      var m = scope && scope.closest ? scope.closest(".mode") : null;
      return m && m.id ? m.id : "_";
    }
    function swap(scope, master, detail, link, fromInside) {
      if (detail) detail.hidden = false;
      if (master) master.hidden = true;
      if (link && !fromInside && scope) lastTrigger[modeKey(scope)] = link;
      var top = detail || master;
      if (top && top.scrollIntoView)
        top.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    /* Profil MOTEUR : fiches pré-rendues (peu nombreuses) → on révèle par id. */
    function openDetail(id, link) {
      var panel = document.getElementById(id);
      if (!panel) return;
      var scope = panel.closest(".drill-scope") || document;
      var master = scope.querySelector
        ? scope.querySelector(".tab-master")
        : null;
      var detail = panel.closest(".tab-detail");
      if (detail) {
        Array.prototype.forEach.call(
          detail.querySelectorAll(".drill-panel"),
          function (p) {
            p.hidden = p.id !== id;
          },
        );
      }
      swap(scope, master, detail, link, !!link.closest(".drill-panel"));
    }
    /* Détail DOCUMENT : fiche rendue par le serveur dans un <template> inerte,
       CLONÉE à la demande dans un unique conteneur vivant → DOM borné même à
       5000 docs, fac-similés chargés seulement à l'ouverture. On recâble les
       comportements internes de la fiche (sélecteur de moteur, zoom) après clonage. */
    function openDocDetail(idx, link) {
      var tpl = document.querySelector('template[data-doc="' + idx + '"]');
      var live = document.querySelector(".doc-detail-live");
      if (!tpl || !live) return;
      live.replaceChildren(tpl.content.cloneNode(true));
      wireEngineTabs(live);
      wireFacZoom(live);
      var detail = live.closest(".tab-detail");
      var scope = detail ? detail.closest(".drill-scope") : null;
      var master = scope ? scope.querySelector(".tab-master") : null;
      var fromInside = !!(
        link.closest(".doc-detail-live") || link.closest(".drill-panel")
      );
      swap(scope, master, detail, link, fromInside);
    }
    function closeDetail(backLink) {
      var scope = backLink.closest(".drill-scope");
      if (!scope) return;
      var master = scope.querySelector(".tab-master");
      var detail = scope.querySelector(".tab-detail");
      if (detail) detail.hidden = true;
      var live = detail && detail.querySelector(".doc-detail-live");
      if (live) live.replaceChildren(); /* libère la fiche clonée */
      if (master) master.hidden = false;
      var trig = lastTrigger[modeKey(scope)];
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
      if (href.charAt(0) !== "#" || href.length <= 1) return;
      var id = href.slice(1);
      /* lien document #doc-N → clone du <template> correspondant */
      if (
        /^doc-\d+$/.test(id) &&
        document.querySelector('template[data-doc="' + id.slice(4) + '"]')
      ) {
        e.preventDefault();
        openDocDetail(id.slice(4), link);
        return;
      }
      var target = document.getElementById(id);
      if (target && target.classList.contains("drill-panel")) {
        e.preventDefault();
        openDetail(id, link);
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

  /* 7b) Filtres galerie à FACETTES qui COMPOSENT (strate · anomalie). Chaque
   *     groupe .doc-filter porte data-facet = l'attribut data-<facet> lu sur la
   *     carte ; pour "anom" la carte porte une LISTE de tokens (appartenance). On
   *     mémorise la sélection active de chaque facette (partagée par scope) et on
   *     recompose data-filtered = ET des facettes ; le paginateur sœur réaffiche
   *     la page 1 du sous-ensemble. Sans paginateur (dégradé), on masque direct.
   *     Sans JS, chips inertes, toutes cartes visibles. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".doc-filter"),
    function (group) {
      var scope = group.parentNode;
      var grid = scope.querySelector(".doc-grid");
      var facet = group.getAttribute("data-facet") || "stratum";
      scope._facets = scope._facets || {};
      scope._facets[facet] = "*";
      var btns = group.querySelectorAll(".df-btn");
      function matches(card, f, want) {
        if (want === "*") return true;
        var v = card.getAttribute("data-" + f) || "";
        if (f === "anom") return (" " + v + " ").indexOf(" " + want + " ") >= 0;
        return v === want;
      }
      function apply() {
        Array.prototype.forEach.call(
          scope.querySelectorAll(".doc-card"),
          function (card) {
            var keep = true;
            for (var f in scope._facets)
              if (!matches(card, f, scope._facets[f])) {
                keep = false;
                break;
              }
            card.setAttribute("data-filtered", keep ? "0" : "1");
          },
        );
        if (grid && grid._paginator) grid._paginator.reset();
        else
          Array.prototype.forEach.call(
            scope.querySelectorAll(".doc-card"),
            function (card) {
              card.hidden = card.getAttribute("data-filtered") === "1";
            },
          );
      }
      Array.prototype.forEach.call(btns, function (btn) {
        btn.addEventListener("click", function () {
          scope._facets[facet] = btn.getAttribute("data-" + facet);
          Array.prototype.forEach.call(btns, function (b) {
            var on = b === btn;
            b.classList.toggle("on", on);
            b.setAttribute("aria-pressed", on ? "true" : "false");
          });
          apply();
        });
      });
    },
  );

  /* 10) Pagination des longues listes (galerie, tables) — SANS rien retirer :
   *     [data-paginate=N] garde tous les items dans le document mais n'en affiche
   *     que N à la fois (page courante) + un pager. Compose avec le filtre par
   *     strate (items data-filtered="1" exclus de la pagination). Sans JS, pas de
   *     pager → tout reste visible (autonome, imprimable). On ne masque/affiche
   *     que des items déjà rendus. */
  function makePaginator(host) {
    var size = parseInt(host.getAttribute("data-paginate"), 10) || 60;
    var isTable = !!host.tBodies && host.tBodies[0];
    function items() {
      var kids = isTable ? host.tBodies[0].rows : host.children;
      return Array.prototype.filter.call(kids, function (el) {
        return el.nodeType === 1 && !el.classList.contains("pager");
      });
    }
    var page = 0;
    var pager = document.createElement("div");
    pager.className = "pager";
    pager.style.cssText =
      "display:flex;gap:.5rem;align-items:center;justify-content:center;" +
      "margin:.75rem 0;flex-wrap:wrap";
    var prev = document.createElement("button");
    var next = document.createElement("button");
    var label = document.createElement("span");
    prev.type = next.type = "button";
    prev.className = next.className = "df-btn";
    prev.textContent = "‹";
    next.textContent = "›";
    label.className = "muted";
    pager.appendChild(prev);
    pager.appendChild(label);
    pager.appendChild(next);
    host.parentNode.insertBefore(pager, host.nextSibling);
    function render() {
      var all = items();
      var active = all.filter(function (el) {
        return el.getAttribute("data-filtered") !== "1";
      });
      var pages = Math.max(1, Math.ceil(active.length / size));
      page = Math.min(Math.max(page, 0), pages - 1);
      var start = page * size;
      all.forEach(function (el) {
        if (el.getAttribute("data-filtered") === "1") {
          el.hidden = true;
          return;
        }
        var ai = active.indexOf(el);
        el.hidden = !(ai >= start && ai < start + size);
      });
      label.textContent = "page " + (page + 1) + " / " + pages + " · " + active.length;
      prev.disabled = page === 0;
      next.disabled = page >= pages - 1;
      pager.hidden = active.length <= size;
    }
    function go(delta) {
      page += delta;
      render();
      if (host.scrollIntoView)
        host.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    prev.addEventListener("click", function () {
      go(-1);
    });
    next.addEventListener("click", function () {
      go(1);
    });
    render();
    return {
      render: render,
      reset: function () {
        page = 0;
        render();
      },
    };
  }
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-paginate]"),
    function (host) {
      host._paginator = makePaginator(host);
    },
  );

  /* 8) Sélecteur de moteur du diff pleine page (détail document) : un bouton
   *    montre le bloc .dd-fulldiff du moteur, cache les autres (scopé au wrap).
   *    Sans JS, les blocs sont empilés et tous visibles. Fonction (re)câblable
   *    sur une racine : appelée au chargement, puis sur chaque fiche clonée. */
  function wireEngineTabs(root) {
    Array.prototype.forEach.call(
    root.querySelectorAll(".dd-engine-tabs"),
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
  }

  /* 9) Fac-similé zoomable/pan (détail document) : molette = zoom, glisser =
   *    déplacer, boutons +/−/⤢. Chaque image garde son propre état (zoom z,
   *    décalage ox/oy). Sans JS, l'image s'affiche à taille medium, statique.
   *    Fonction (re)câblable sur une racine (chargement, puis fiche clonée). */
  function wireFacZoom(root) {
    Array.prototype.forEach.call(
    root.querySelectorAll(".dd-fac-zoom"),
    function (box) {
      var img = box.querySelector(".dd-fac-img");
      if (!img) return;
      // Zoom par **taille réelle** (px) et non par ``transform: scale`` : le
      // navigateur re-rasterise depuis le bitmap natif → net jusqu'à la
      // résolution native (≠ scale sur calque GPU, qui agrandit un raster déjà
      // réduit → flou). Panoramique par scroll du conteneur (overflow:auto).
      var z = 1,
        drag = null;
      function fitWidth() {
        // largeur affichée à z=1 (``object-fit: contain`` émulé) : bornée par la
        // plus contraignante des deux dimensions du conteneur.
        var bw = box.clientWidth,
          bh = box.clientHeight,
          nw = img.naturalWidth,
          nh = img.naturalHeight;
        if (!nw || !nh) return bw;
        return Math.min(bw, bh * (nw / nh));
      }
      function apply() {
        if (z <= 1) {
          z = 1;
          img.style.maxWidth = "100%";
          img.style.maxHeight = "100%";
          img.style.width = "";
          img.style.height = "";
          box.style.cursor = "zoom-in";
          return;
        }
        // jamais au-delà du natif (pas d'upscale flou) : on plafonne à la
        // largeur native du bitmap.
        var want = fitWidth() * z;
        if (img.naturalWidth) want = Math.min(want, img.naturalWidth);
        img.style.maxWidth = "none";
        img.style.maxHeight = "none";
        img.style.width = Math.round(want) + "px";
        img.style.height = "auto";
        box.style.cursor = "grab";
      }
      function zoom(factor) {
        z = Math.max(1, Math.min(16, z * factor));
        apply();
      }
      box.addEventListener(
        "wheel",
        function (e) {
          e.preventDefault();
          zoom(e.deltaY < 0 ? 1.2 : 0.83);
        },
        { passive: false },
      );
      box.addEventListener("mousedown", function (e) {
        if (z <= 1 || (e.target.closest && e.target.closest("[data-zoom]"))) return;
        e.preventDefault();
        drag = {
          x: e.clientX,
          y: e.clientY,
          sl: box.scrollLeft,
          st: box.scrollTop,
        };
        box.style.cursor = "grabbing";
      });
      document.addEventListener("mousemove", function (e) {
        if (!drag) return;
        box.scrollLeft = drag.sl - (e.clientX - drag.x);
        box.scrollTop = drag.st - (e.clientY - drag.y);
      });
      document.addEventListener("mouseup", function () {
        if (drag) {
          drag = null;
          box.style.cursor = z > 1 ? "grab" : "zoom-in";
        }
      });
      Array.prototype.forEach.call(
        box.querySelectorAll("[data-zoom]"),
        function (btn) {
          btn.addEventListener("click", function () {
            var k = btn.getAttribute("data-zoom");
            if (k === "in") zoom(1.3);
            else if (k === "out") zoom(0.77);
            else {
              z = 1;
              apply();
              box.scrollTop = 0;
              box.scrollLeft = 0;
            }
          });
        },
      );
      apply();
    },
    );
  }

  /* 11) Scroll-spy du sommaire collant (spine) : surligne le lien du groupe en
     cours de lecture. On observe les sous-titres (.tab-subhead[id]) ; l'actif est
     le dernier dont le haut a franchi une bande sous le spine. Enrichissement
     progressif (sans JS / sans IntersectionObserver : liens normaux, rien de
     cassé). Seuls les sous-titres du mode VISIBLE comptent (offsetParent non nul
     → un mode caché en display:none est ignoré). */
  if (window.IntersectionObserver) {
    var spineLinks = {};
    Array.prototype.forEach.call(
      document.querySelectorAll(".spine-link"),
      function (a) {
        var href = a.getAttribute("href") || "";
        if (href.charAt(0) === "#") spineLinks[href.slice(1)] = a;
      },
    );
    var subheads = Array.prototype.slice.call(
      document.querySelectorAll(".tab-subhead[id]"),
    );
    if (subheads.length && Object.keys(spineLinks).length) {
      var markActive = function () {
        var activeId = null;
        subheads.forEach(function (h) {
          if (h.offsetParent === null) return; /* mode caché → ignoré */
          if (h.getBoundingClientRect().top <= 80) activeId = h.id;
        });
        if (activeId === null) {
          /* aucun franchi (haut de page) : le premier visible fait l'actif */
          for (var i = 0; i < subheads.length; i++) {
            if (subheads[i].offsetParent !== null) {
              activeId = subheads[i].id;
              break;
            }
          }
        }
        Object.keys(spineLinks).forEach(function (id) {
          spineLinks[id].classList.toggle("on", id === activeId);
        });
      };
      var spy = new IntersectionObserver(markActive, {
        threshold: [0, 1],
      });
      subheads.forEach(function (h) {
        spy.observe(h);
      });
      markActive();
    }
  }

  /* Câblage initial des comportements de fiche sur le document (les fiches
     document, en <template>, seront recâblées à l'ouverture par openDocDetail). */
  wireEngineTabs(document);
  wireFacZoom(document);
})();
