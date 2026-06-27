/* Segmentation — lancement d'un run depuis la page /segmentation.
 *
 * La page reste rendue serveur : ce script ne fait que révéler les champs du
 * segmenteur distant (endpoint/jeton) selon le choix, poster sur l'endpoint de
 * run existant, attendre la fin du job, puis recharger pour que le HTML serveur
 * (le dernier layout persisté) reste la source de vérité.
 */
(function () {
  "use strict";

  var CSRF = "X-Cinoc-CSRF";
  var POLL_MS = 1500;

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

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

  function errorText(response) {
    var detail = response && response.body && response.body.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    return "HTTP " + response.status;
  }

  ready(function () {
    var form = document.getElementById("seg-run-form");
    if (!form) return;
    var engine = document.getElementById("seg-engine");
    var endpointField = document.getElementById("seg-endpoint-field");
    var tokenField = document.getElementById("seg-token-field");
    var status = document.getElementById("seg-run-status");
    var button = document.getElementById("segment-btn");

    function syncRemoteFields() {
      var isRemote = engine && engine.value === "remote_segmenter";
      if (endpointField) endpointField.hidden = !isRemote;
      if (tokenField) tokenField.hidden = !isRemote;
    }
    if (engine) engine.addEventListener("change", syncRemoteFields);
    syncRemoteFields();

    function strings() {
      return {
        running: status ? status.getAttribute("data-running") : "",
        done: status ? status.getAttribute("data-done") : "",
      };
    }

    function poll(jobId) {
      fetchJson("/api/runs/" + encodeURIComponent(jobId)).then(function (res) {
        var state = res.body && res.body.state;
        if (state === "done") {
          window.location.reload();
          return;
        }
        if (state === "failed" || state === "cancelled" || !res.ok) {
          var msg = res.body && res.body.error ? res.body.error : errorText(res);
          if (status) status.textContent = msg;
          if (button) button.disabled = false;
          return;
        }
        window.setTimeout(function () {
          poll(jobId);
        }, POLL_MS);
      });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var payload = { corpus_id: form.elements.corpus_id.value };
      var segmenter = engine ? engine.value : "pp_doclayout";
      payload.segmenter = segmenter;
      if (segmenter === "remote_segmenter") {
        var ep = (form.elements.endpoint.value || "").trim();
        if (ep) payload.endpoint = ep;
        var tok = (form.elements.token.value || "").trim();
        if (tok) payload.token = tok;
      }
      var headers = { "Content-Type": "application/json" };
      headers[CSRF] = "1";
      if (button) button.disabled = true;
      if (status) status.textContent = strings().running;
      fetchJson("/api/segmentation/run", {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload),
      }).then(function (res) {
        if (!res.ok) {
          if (status) status.textContent = errorText(res);
          if (button) button.disabled = false;
          return;
        }
        poll(res.body.job_id);
      });
    });
  });
})();
