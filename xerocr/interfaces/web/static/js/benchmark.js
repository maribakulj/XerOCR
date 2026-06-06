/* Lanceur « Banc d'essai » — JS léger, sans dépendance.
 *
 * Le corpus est préparé dans la Bibliothèque ; ici on le SÉLECTIONNE.
 *   POST /api/runs {engine, corpus_id?}    → lance un run (gardes côté serveur)
 *   POST /api/segmentation/run {corpus_id} → run de segmentation (même flux SSE)
 *   GET  /api/runs/{id}/events (SSE)        → progression → lien rapport
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
    var corpusSelect = document.getElementById("corpus-select");
    var segBtn = document.getElementById("segment-btn");
    var segStatus = document.getElementById("segment-status");
    if (!btn || !statusEl || !logEl || !resultEl) return;

    // Corpus actif = sélection (valeur vide ⇒ démonstration précalculée).
    function currentCorpusId() {
      return corpusSelect && corpusSelect.value ? corpusSelect.value : null;
    }

    // « Segmenter » exige un corpus sélectionné.
    function syncSeg() {
      if (segBtn) segBtn.disabled = !currentCorpusId();
    }
    if (corpusSelect) corpusSelect.addEventListener("change", syncSeg);
    syncSeg();

    // --- Lancement d'un run -----------------------------------------------
    btn.addEventListener("click", function () {
      btn.disabled = true;
      logEl.textContent = "";
      resultEl.textContent = "";
      statusEl.textContent = btn.dataset.launching || "…";

      var headers = { "Content-Type": "application/json" };
      headers[CSRF] = "1";
      var payload = { engine: engineEl ? engineEl.value : "precomputed" };
      var corpusId = currentCorpusId();
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

    // --- Run de segmentation ----------------------------------------------
    if (segBtn) {
      segBtn.addEventListener("click", function () {
        var corpusId = currentCorpusId();
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
