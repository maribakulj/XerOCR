/* Lanceur « Banc d'essai » (TU2.f) — JS léger, sans dépendance.
 *
 * Pilote les endpoints existants : POST /api/runs (avec en-tête CSRF) lance la
 * démo ; on s'abonne ensuite à GET /api/runs/{id}/events (SSE) pour afficher la
 * progression en direct, puis on propose le rapport produit. Le SSE émet des
 * événements NOMMÉS (un par état) → on enregistre un écouteur par état.
 */
(function () {
  "use strict";
  var CSRF_HEADER = "X-XeroCR-CSRF";
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
    if (!btn || !statusEl || !logEl || !resultEl) return;

    btn.addEventListener("click", function () {
      btn.disabled = true;
      logEl.textContent = "";
      resultEl.textContent = "";
      statusEl.textContent = btn.dataset.launching || "…";

      var headers = { "Content-Type": "application/json" };
      headers[CSRF_HEADER] = "1";

      fetch("/api/runs", { method: "POST", headers: headers, body: "{}" })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then(function (data) {
          subscribe(data.job_id);
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
        // La fin normale ferme déjà le flux ; sinon on évite une reconnexion folle.
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
  });
})();
