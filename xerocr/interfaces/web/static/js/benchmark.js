/* Lanceur « Banc d'essai » (S2) — JS léger, sans dépendance.
 *
 * Pilote les endpoints existants :
 *   POST /api/corpus (multipart, CSRF)  → upload d'un corpus ZIP → corpus_id
 *   POST /api/runs {engine, corpus_id}  → lance un run (gardes côté serveur)
 *   GET  /api/runs/{id}/events (SSE)     → progression en direct → lien rapport
 * Le serveur fait foi (403/409/404/422) ; on affiche son message d'erreur.
 */
(function () {
  "use strict";
  var CSRF = "X-XeroCR-CSRF";
  var STATES = ["pending", "running", "done", "failed", "cancelled"];
  var TERMINAL = { done: 1, failed: 1, cancelled: 1 };

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var btn = document.getElementById("launch");
    var statusEl = document.getElementById("run-status");
    var logEl = document.getElementById("run-log");
    var resultEl = document.getElementById("run-result");
    var engineEl = document.getElementById("engine");
    var fileEl = document.getElementById("corpus-file");
    var uploadBtn = document.getElementById("upload");
    var corpusEl = document.getElementById("corpus-status");
    var segBtn = document.getElementById("segment-btn");
    var segStatus = document.getElementById("segment-status");
    if (!btn || !statusEl || !logEl || !resultEl) return;

    var corpusId = null;

    // Active le bouton « Segmenter » dès qu'un corpus est sélectionné.
    function enableSeg() {
      if (segBtn) segBtn.disabled = false;
    }

    // --- Upload d'un corpus ZIP -------------------------------------------
    if (uploadBtn && fileEl && corpusEl) {
      uploadBtn.addEventListener("click", function () {
        var file = fileEl.files && fileEl.files[0];
        if (!file) return;
        var headers = {};
        headers[CSRF] = "1";
        var form = new FormData();
        form.append("file", file);
        uploadBtn.disabled = true;
        fetchJson("/api/corpus", { method: "POST", headers: headers, body: form })
          .then(function (r) {
            uploadBtn.disabled = false;
            if (!r.ok) {
              corpusId = null;
              corpusEl.textContent = r.body.detail || "HTTP " + r.status;
              return;
            }
            corpusId = r.body.corpus_id;
            corpusEl.textContent = r.body.name + " — " + r.body.n_documents + " doc";
            enableSeg();
          })
          .catch(function () {
            uploadBtn.disabled = false;
            corpusEl.textContent = resultEl.dataset.neterror || "error";
          });
      });
    }

    // --- Import d'un corpus distant (S6) ----------------------------------
    // POST /api/corpus/import/{source} (JSON, CSRF) → corpus_id, qui devient
    // le corpus actif du lancement (même flux que l'upload ZIP).
    var importSource = document.getElementById("import-source");
    var importBtn = document.getElementById("import-btn");
    var importStatus = document.getElementById("import-status");
    if (importSource && importBtn && importStatus) {
      var groups = document.querySelectorAll(".import-fields");

      importSource.addEventListener("change", function () {
        for (var i = 0; i < groups.length; i++) {
          groups[i].hidden =
            groups[i].getAttribute("data-source") !== importSource.value;
        }
      });

      importBtn.addEventListener("click", function () {
        var group = document.querySelector(
          '.import-fields[data-source="' + importSource.value + '"]'
        );
        if (!group) return;
        var payload = {};
        var fields = group.querySelectorAll("input[name]");
        for (var i = 0; i < fields.length; i++) collectField(payload, fields[i]);
        collectField(payload, document.getElementById("import-limit"));
        collectField(payload, document.getElementById("import-name"));

        var headers = { "Content-Type": "application/json" };
        headers[CSRF] = "1";
        importBtn.disabled = true;
        importStatus.textContent = "…";
        fetchJson("/api/corpus/import/" + importSource.value, {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        })
          .then(function (r) {
            importBtn.disabled = false;
            if (!r.ok) {
              corpusId = null;
              importStatus.textContent = r.body.detail || "HTTP " + r.status;
              return;
            }
            corpusId = r.body.corpus_id;
            importStatus.textContent =
              r.body.name + " — " + r.body.n_documents + " doc";
            if (corpusEl) corpusEl.textContent = importStatus.textContent;
            enableSeg();
          })
          .catch(function () {
            importBtn.disabled = false;
            importStatus.textContent = resultEl.dataset.neterror || "error";
          });
      });
    }

    // Ajoute la valeur d'un champ au payload : case→bool, nombre coercé, texte
    // non vide tel quel ; un champ optionnel vide est ignoré.
    function collectField(payload, el) {
      if (!el || !el.name) return;
      if (el.type === "checkbox") {
        payload[el.name] = el.checked;
        return;
      }
      var v = (el.value || "").trim();
      if (v === "") return;
      payload[el.name] = el.type === "number" ? parseInt(v, 10) : v;
    }

    // --- Lancement d'un run -----------------------------------------------
    btn.addEventListener("click", function () {
      btn.disabled = true;
      logEl.textContent = "";
      resultEl.textContent = "";
      statusEl.textContent = btn.dataset.launching || "…";

      var headers = { "Content-Type": "application/json" };
      headers[CSRF] = "1";
      var payload = { engine: engineEl ? engineEl.value : "precomputed" };
      if (corpusId) payload.corpus_id = corpusId;

      fetchJson("/api/runs", {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload),
      })
        .then(function (r) {
          if (!r.ok) {
            statusEl.textContent = "HTTP " + r.status;
            resultEl.textContent = r.body.detail || "";
            btn.disabled = false;
            return;
          }
          subscribe(r.body.job_id, reportTerminal);
        })
        .catch(function () {
          statusEl.textContent = resultEl.dataset.neterror || "error";
          btn.disabled = false;
        });
    });

    // --- Run de segmentation (S6/T2) --------------------------------------
    // POST /api/segmentation/run {corpus_id} → suit le MÊME flux SSE que les
    // runs OCR (un seul exécuteur) ; à la fin, lien vers /segmentation.
    if (segBtn) {
      segBtn.addEventListener("click", function () {
        if (!corpusId) return;
        segBtn.disabled = true;
        resultEl.textContent = "";
        statusEl.textContent = segBtn.dataset.launching || "…";
        var headers = { "Content-Type": "application/json" };
        headers[CSRF] = "1";
        fetchJson("/api/segmentation/run", {
          method: "POST",
          headers: headers,
          body: JSON.stringify({ corpus_id: corpusId }),
        })
          .then(function (r) {
            if (!r.ok) {
              statusEl.textContent = "HTTP " + r.status;
              if (segStatus) segStatus.textContent = r.body.detail || "";
              segBtn.disabled = false;
              return;
            }
            subscribe(r.body.job_id, segTerminal);
          })
          .catch(function () {
            statusEl.textContent = resultEl.dataset.neterror || "error";
            segBtn.disabled = false;
          });
      });
    }

    // Suit un job par SSE ; `onTerminal(state, job)` gère l'état final (lien).
    function subscribe(jobId, onTerminal) {
      var es = new EventSource("/api/runs/" + encodeURIComponent(jobId) + "/events");
      var finished = false;
      function done(state, job) {
        if (finished) return;
        finished = true;
        es.close();
        onTerminal(state, job);
      }
      STATES.forEach(function (state) {
        es.addEventListener(state, function (ev) {
          var job = JSON.parse(ev.data);
          statusEl.textContent = state;
          var line = document.createElement("div");
          line.textContent = job.updated_at + "  ·  " + state;
          logEl.appendChild(line);
          if (TERMINAL[state]) done(state, job);
        });
      });
      es.onerror = function () {
        if (es.readyState === EventSource.CLOSED) done("failed", {});
      };
    }

    function reportTerminal(state, job) {
      btn.disabled = false;
      if (state === "done" && job.report_name) {
        var a = document.createElement("a");
        a.href = "/reports/" + encodeURIComponent(job.report_name);
        a.className = "btn btn-primary";
        a.textContent = resultEl.dataset.open || "report";
        resultEl.appendChild(a);
      } else if (job.error) {
        resultEl.textContent = job.error;
      }
    }

    function segTerminal(state, job) {
      segBtn.disabled = false;
      if (state === "done") {
        var a = document.createElement("a");
        a.href = "/segmentation";
        a.className = "btn btn-primary";
        a.textContent = segBtn.dataset.open || "segmentation";
        resultEl.appendChild(a);
      } else if (job && job.error) {
        resultEl.textContent = job.error;
      }
    }

    // Renvoie {ok, status, body} en parsant le JSON quel que soit le code.
    function fetchJson(url, opts) {
      return fetch(url, opts).then(function (res) {
        return res.json().then(
          function (body) {
            return { ok: res.ok, status: res.status, body: body };
          },
          function () {
            return { ok: res.ok, status: res.status, body: {} };
          }
        );
      });
    }
  });
})();
