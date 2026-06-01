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
    if (!btn || !statusEl || !logEl || !resultEl) return;

    var corpusId = null;

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
          })
          .catch(function () {
            uploadBtn.disabled = false;
            corpusEl.textContent = resultEl.dataset.neterror || "error";
          });
      });
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
          subscribe(r.body.job_id);
        })
        .catch(function () {
          statusEl.textContent = resultEl.dataset.neterror || "error";
          btn.disabled = false;
        });
    });

    function subscribe(jobId) {
      var es = new EventSource("/api/runs/" + encodeURIComponent(jobId) + "/events");
      STATES.forEach(function (state) {
        es.addEventListener(state, function (ev) {
          var job = JSON.parse(ev.data);
          statusEl.textContent = state;
          var line = document.createElement("div");
          line.textContent = job.updated_at + "  ·  " + state;
          logEl.appendChild(line);
          if (TERMINAL[state]) {
            es.close();
            btn.disabled = false;
            finish(state, job);
          }
        });
      });
      es.onerror = function () {
        if (es.readyState === EventSource.CLOSED) btn.disabled = false;
      };
    }

    function finish(state, job) {
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
