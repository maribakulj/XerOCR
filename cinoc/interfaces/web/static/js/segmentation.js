/* Segmentation & transcription hybride — lancement d'un run depuis /segmentation.
 *
 * La page reste rendue serveur : ce script ne fait que révéler les champs du
 * segmenteur distant (endpoint/jeton) selon le choix, poster sur l'endpoint de
 * run, attendre la fin du job, puis agir selon le formulaire :
 *  - segmentation → recharge (le HTML serveur, dernier layout persisté, fait foi) ;
 *  - hybride      → révèle le lien de téléchargement de l'ALTO assemblé.
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

  function pollJob(jobId, status, button, onDone) {
    fetchJson("/api/runs/" + encodeURIComponent(jobId)).then(function (res) {
      var state = res.body && res.body.state;
      if (state === "done") {
        onDone();
        return;
      }
      if (state === "failed" || state === "cancelled" || !res.ok) {
        var msg = res.body && res.body.error ? res.body.error : errorText(res);
        if (status) status.textContent = msg;
        if (button) button.disabled = false;
        return;
      }
      window.setTimeout(function () {
        pollJob(jobId, status, button, onDone);
      }, POLL_MS);
    });
  }

  /* Câble un formulaire de lancement (segmentation ou hybride). ``onDone`` reçoit
   * le corps de la réponse de lancement (``{job_id, run_id}``) à la fin du job. */
  function wireForm(opts) {
    var form = document.getElementById(opts.formId);
    if (!form) return;
    var engine = document.getElementById(opts.engineId);
    var ocr = opts.ocrId ? document.getElementById(opts.ocrId) : null;
    var endpointField = document.getElementById(opts.endpointFieldId);
    var tokenField = document.getElementById(opts.tokenFieldId);
    var promptField = opts.promptFieldId
      ? document.getElementById(opts.promptFieldId)
      : null;
    var status = document.getElementById(opts.statusId);
    var button = document.getElementById(opts.buttonId);

    function syncRemoteFields() {
      var isRemote = engine && engine.value === "remote_segmenter";
      if (endpointField) endpointField.hidden = !isRemote;
      if (tokenField) tokenField.hidden = !isRemote;
    }
    function syncPromptField() {
      // Le champ prompt n'a de sens que pour un reconnaisseur VLM (zero-shot).
      if (!promptField || !ocr) return;
      var opt = ocr.options[ocr.selectedIndex];
      var isVlm = opt && opt.getAttribute("data-vlm") === "1";
      promptField.hidden = !isVlm;
    }
    if (engine) engine.addEventListener("change", syncRemoteFields);
    if (ocr) ocr.addEventListener("change", syncPromptField);
    syncRemoteFields();
    syncPromptField();

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
      if (opts.extra) opts.extra(payload, form);
      var headers = { "Content-Type": "application/json" };
      headers[CSRF] = "1";
      if (button) button.disabled = true;
      if (status) {
        status.textContent = status.getAttribute("data-running") || "";
      }
      fetchJson(opts.url, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload),
      }).then(function (res) {
        if (!res.ok) {
          if (status) status.textContent = errorText(res);
          if (button) button.disabled = false;
          return;
        }
        pollJob(res.body.job_id, status, button, function () {
          opts.onDone(res.body, status, button);
        });
      });
    });
  }

  ready(function () {
    // Segmentation : recharge pour afficher le dernier layout persisté.
    wireForm({
      formId: "seg-run-form",
      engineId: "seg-engine",
      endpointFieldId: "seg-endpoint-field",
      tokenFieldId: "seg-token-field",
      statusId: "seg-run-status",
      buttonId: "segment-btn",
      url: "/api/segmentation/run",
      onDone: function () {
        window.location.reload();
      },
    });
    // Hybride : reconnaissance par bloc (OCR réel ou VLM zero-shot) → ALTO.
    // Révèle le lien de téléchargement (le LAYOUT est aussi persisté → visible
    // en rechargeant la page).
    wireForm({
      formId: "hyb-run-form",
      engineId: "hyb-engine",
      ocrId: "hyb-ocr",
      promptFieldId: "hyb-prompt-field",
      endpointFieldId: "hyb-endpoint-field",
      tokenFieldId: "hyb-token-field",
      statusId: "hyb-run-status",
      buttonId: "hybrid-btn",
      url: "/api/hybrid/run",
      extra: function (payload, form) {
        var ocr = document.getElementById("hyb-ocr");
        payload.ocr = ocr ? ocr.value : "tesseract";
        var promptField = document.getElementById("hyb-prompt-field");
        if (promptField && !promptField.hidden && form.elements.prompt) {
          var p = (form.elements.prompt.value || "").trim();
          if (p) payload.prompt = p;
        }
      },
      onDone: function (body, status, button) {
        if (button) button.disabled = false;
        if (status) status.textContent = status.getAttribute("data-done") || "";
        var link = document.getElementById("hyb-download");
        if (link && body && body.run_id) {
          link.href = "/reports/" + encodeURIComponent(body.run_id) + "/alto.zip";
          link.hidden = false;
        }
      },
    });
  });
})();
