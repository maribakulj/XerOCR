/* Banc d'essai — composeur de benchmark et suivi SSE.
 *
 * Un seul brouillon de concurrent alimente une file visible. Le serveur reste
 * la source de vérité pour le lancement et les erreurs ; le client ne traduit
 * que les états HTTP en messages lisibles.
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

  ready(function () {
    var launchBtn = document.getElementById("launch");
    var statusEl = document.getElementById("run-status");
    var resultEl = document.getElementById("run-result");
    var logEl = document.getElementById("run-log");
    var logShell = document.getElementById("run-log-shell");
    var progressWrap = document.getElementById("run-progress");
    var progressBar = document.getElementById("run-progress-bar");
    var progressText = document.getElementById("run-progress-text");
    var corpusSelect = document.getElementById("corpus-select");
    var normalization = document.getElementById("normalization");
    var addBtn = document.getElementById("add-competitor");
    var queueTpl = document.getElementById("queue-row-tpl");
    var queueList = document.getElementById("queue-list");
    var queueEmpty = document.getElementById("queue-empty");
    if (!launchBtn || !statusEl || !resultEl || !queueList || !queueTpl) return;

    var queue = [];
    var activeMode = "ocr_only";
    var modeButtons = document.querySelectorAll("[data-mode]");
    var draftFields = document.querySelectorAll("[data-show]");
    var draftOcr = document.getElementById("draft-ocr");
    var draftLlm = document.getElementById("draft-llm");
    var draftVlm = document.getElementById("draft-vlm");
    var draftModel = document.getElementById("draft-model");
    var draftPrompt = document.getElementById("draft-prompt");
    var draftPromptCurated = document.getElementById("draft-prompt-curated");
    var queueLabels = {
      ocr: queueList.getAttribute("data-label-ocr") || "OCR",
      ocrLlm: queueList.getAttribute("data-label-ocr-llm") || "OCR → LLM",
      ocrVlm: queueList.getAttribute("data-label-ocr-vlm") || "OCR → VLM",
      vlm: queueList.getAttribute("data-label-vlm") || "VLM",
    };

    function currentCorpusId() {
      return corpusSelect && corpusSelect.value ? corpusSelect.value : null;
    }

    function applyQueryCorpus() {
      var corpusId = new URLSearchParams(window.location.search).get("corpus");
      if (corpusId && corpusSelect) corpusSelect.value = corpusId;
    }

    // Le champ « Modèle » pointe vers la datalist du fournisseur sélectionné
    // (ollama / mistral), qui n'existe que si le serveur a renvoyé des modèles.
    // Sinon : saisie libre. Rien de hardcodé — les options viennent du serveur.
    function updateModelList() {
      if (!draftModel) return;
      var provider =
        activeMode === "text_only"
          ? draftLlm && draftLlm.value
          : activeMode === "text_and_image" || activeMode === "zero_shot"
          ? draftVlm && draftVlm.value
          : "";
      var listId =
        provider === "ollama"
          ? "ollama-models"
          : provider === "mistral"
          ? "mistral-models"
          : "";
      var dl = listId ? document.getElementById(listId) : null;
      if (dl) draftModel.setAttribute("list", listId);
      else draftModel.removeAttribute("list");
      var hint = document.getElementById("model-hint");
      if (hint) {
        hint.textContent = dl
          ? dl.children.length + " modèle(s) — clique pour choisir"
          : "";
      }
    }

    function setMode(mode) {
      activeMode = mode;
      for (var i = 0; i < modeButtons.length; i++) {
        var isActive = modeButtons[i].getAttribute("data-mode") === mode;
        modeButtons[i].classList.toggle("on", isActive);
        modeButtons[i].setAttribute("aria-selected", isActive ? "true" : "false");
      }
      for (var j = 0; j < draftFields.length; j++) {
        var shown = draftFields[j].getAttribute("data-show").split(" ");
        draftFields[j].hidden = shown.indexOf(mode) < 0;
      }
      updateModelList();
    }

    function summarize(entry) {
      if (entry.mode === "ocr_only") {
        return {
          label: queueLabels.ocr,
          meta: entry.engine,
        };
      }
      if (entry.mode === "text_only") {
        return {
          label: queueLabels.ocrLlm,
          meta: entry.engine + " → " + entry.llm + (entry.model ? " · " + entry.model : ""),
        };
      }
      if (entry.mode === "text_and_image") {
        return {
          label: queueLabels.ocrVlm,
          meta: entry.engine + " → " + entry.llm + (entry.model ? " · " + entry.model : ""),
        };
      }
      return {
        label: queueLabels.vlm,
        meta: entry.engine + (entry.model ? " · " + entry.model : ""),
      };
    }

    function renderQueue() {
      queueList.textContent = "";
      if (queueEmpty) queueEmpty.hidden = queue.length > 0;
      for (var i = 0; i < queue.length; i++) {
        var node = queueTpl.content.firstElementChild.cloneNode(true);
        var summary = summarize(queue[i]);
        node.querySelector(".queue-id").textContent = "C0" + (i + 1);
        node.querySelector(".queue-label").textContent = summary.label;
        node.querySelector(".queue-meta").textContent = summary.meta;
        bindRemove(node.querySelector(".queue-remove"), i);
        queueList.appendChild(node);
      }
    }

    function bindRemove(button, index) {
      if (!button) return;
      button.addEventListener("click", function () {
        queue.splice(index, 1);
        renderQueue();
      });
    }

    function buildDraft() {
      var model = draftModel && draftModel.value ? draftModel.value.trim() : "";
      var prompt = draftPrompt && draftPrompt.value ? draftPrompt.value.trim() : "";
      // Texte libre prioritaire : s'il est saisi, on ignore le prompt curé (le
      // serveur refuse d'ailleurs les deux à la fois).
      var promptName =
        !prompt && draftPromptCurated ? draftPromptCurated.value : "";
      if (activeMode === "ocr_only") {
        return { engine: draftOcr.value, mode: "ocr_only" };
      }
      if (activeMode === "text_only") {
        return {
          engine: draftOcr.value,
          mode: "text_only",
          llm: draftLlm.value,
          model: model,
          prompt: prompt,
          promptName: promptName,
        };
      }
      if (activeMode === "text_and_image") {
        return {
          engine: draftOcr.value,
          mode: "text_and_image",
          llm: draftVlm.value,
          model: model,
          prompt: prompt,
          promptName: promptName,
        };
      }
      return {
        engine: draftVlm.value,
        mode: "zero_shot",
        model: model,
        prompt: prompt,
        promptName: promptName,
      };
    }

    function payloadCompetitors() {
      var out = [];
      for (var i = 0; i < queue.length; i++) {
        var entry = {};
        entry.engine = queue[i].engine;
        if (queue[i].mode !== "ocr_only") entry.mode = queue[i].mode;
        if (queue[i].llm) entry.llm = queue[i].llm;
        if (queue[i].model) entry.model = queue[i].model;
        if (queue[i].prompt) entry.prompt = queue[i].prompt;
        else if (queue[i].promptName) entry.prompt_name = queue[i].promptName;
        out.push(entry);
      }
      return out;
    }

    function errorText(response) {
      var detail = response && response.body && response.body.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      var specific = resultEl.getAttribute("data-error-" + response.status);
      return specific || resultEl.dataset.errorFallback || ("HTTP " + response.status);
    }

    function resetRunFeedback(launchingText) {
      statusEl.textContent = launchingText || "…";
      resultEl.textContent = "";
      if (logEl) logEl.textContent = "";
      if (logShell) {
        logShell.hidden = false;
        logShell.open = true;
      }
    }

    function appendLog(state, job) {
      if (!logEl) return;
      var line = document.createElement("div");
      line.textContent = (job.updated_at || "—") + "  ·  " + state;
      logEl.appendChild(line);
    }

    function updateProgress(job) {
      if (!progressWrap || !progressBar) return;
      var total = job.total || 0;
      var doneN = job.done || 0;
      if (total <= 0) return;
      progressWrap.hidden = false;
      var pct = Math.round((doneN / total) * 100);
      progressBar.style.width = pct + "%";
      if (progressText) progressText.textContent = doneN + " / " + total;
    }

    function resetProgress() {
      if (progressBar) progressBar.style.width = "0%";
      if (progressText) progressText.textContent = "";
      if (progressWrap) progressWrap.hidden = true;
    }

    function subscribe(jobId, onTerminal) {
      var es = new EventSource("/api/runs/" + encodeURIComponent(jobId) + "/events");
      var finished = false;

      function done(state, job) {
        if (finished) return;
        finished = true;
        es.close();
        onTerminal(state, job || {});
      }

      STATES.forEach(function (state) {
        es.addEventListener(state, function (ev) {
          var job = JSON.parse(ev.data);
          statusEl.textContent = state;
          appendLog(state, job);
          updateProgress(job);
          if (TERMINAL[state]) done(state, job);
        });
      });

      es.onerror = function () {
        if (es.readyState === EventSource.CLOSED) done("failed", {});
      };
    }

    function reportTerminal(state, job) {
      launchBtn.disabled = false;
      if (state === "done" && job.report_name) {
        var link = document.createElement("a");
        link.href = "/reports/" + encodeURIComponent(job.report_name);
        link.className = "btn btn-primary";
        link.textContent = resultEl.dataset.open || "report";
        resultEl.appendChild(link);
        return;
      }
      resultEl.textContent = job.error || (resultEl.dataset.errorFallback || "failed");
    }

    for (var i = 0; i < modeButtons.length; i++) {
      modeButtons[i].addEventListener("click", function () {
        setMode(this.getAttribute("data-mode"));
      });
    }
    // Changer de fournisseur LLM/VLM met à jour la datalist du champ « Modèle ».
    if (draftLlm) draftLlm.addEventListener("change", updateModelList);
    if (draftVlm) draftVlm.addEventListener("change", updateModelList);
    setMode(activeMode);

    if (addBtn) {
      addBtn.addEventListener("click", function () {
        queue.push(buildDraft());
        renderQueue();
      });
    }
    renderQueue();

    applyQueryCorpus();

    launchBtn.addEventListener("click", function () {
      launchBtn.disabled = true;
      resetRunFeedback(launchBtn.dataset.launching);
      resetProgress();
      var headers = { "Content-Type": "application/json" };
      headers[CSRF] = "1";
      var payload = { competitors: payloadCompetitors() };
      var corpusId = currentCorpusId();
      if (corpusId) payload.corpus_id = corpusId;
      if (normalization && normalization.value) payload.normalization = normalization.value;
      fetchJson("/api/runs", {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload),
      })
        .then(function (response) {
          if (!response.ok) {
            statusEl.textContent = "HTTP " + response.status;
            resultEl.textContent = errorText(response);
            launchBtn.disabled = false;
            return;
          }
          subscribe(response.body.job_id, reportTerminal);
        })
        .catch(function () {
          statusEl.textContent = resultEl.dataset.neterror || "HTTP 0";
          resultEl.textContent = resultEl.dataset.errorFallback || "HTTP 0";
          launchBtn.disabled = false;
        });
    });

  });
})();
