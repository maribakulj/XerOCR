/* Bibliothèque — préparation de corpus (upload ZIP + import distant).
 *
 *   POST /api/corpus (multipart, CSRF)            → téléverse une archive ZIP
 *   POST /api/corpus/import/{source} (JSON, CSRF) → importe un corpus distant
 * À la réussite, on recharge la page : la liste « Mes corpus » (rendue serveur)
 * reflète le nouveau corpus. Le serveur fait foi (403/409/413/422).
 *
 * `fetchJson` est volontairement répété (≈ benchmark.js) : ces fichiers JS ne
 * sont pas exécutés en CI (pas de navigateur) → on évite tout couplage de
 * chargement entre eux (un helper partagé serait une dépendance non testée).
 * C'est du boilerplate de transport, pas de la logique.
 */
(function () {
  "use strict";
  var CSRF = "X-XeroCR-CSRF";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var fileEl = document.getElementById("corpus-file");
    var uploadBtn = document.getElementById("upload");
    var statusEl = document.getElementById("corpus-status");
    var dropzone = document.getElementById("dropzone");

    // --- Upload ZIP (bouton + glisser-déposer) ----------------------------
    function upload(file) {
      if (!file) return;
      var headers = {};
      headers[CSRF] = "1";
      var form = new FormData();
      form.append("file", file);
      if (uploadBtn) uploadBtn.disabled = true;
      if (statusEl) statusEl.textContent = "…";
      fetchJson("/api/corpus", { method: "POST", headers: headers, body: form })
        .then(function (r) {
          if (uploadBtn) uploadBtn.disabled = false;
          if (!r.ok) {
            if (statusEl) statusEl.textContent = r.body.detail || "HTTP " + r.status;
            return;
          }
          window.location.reload();
        })
        .catch(function () {
          if (uploadBtn) uploadBtn.disabled = false;
          if (statusEl) statusEl.textContent = "error";
        });
    }

    if (uploadBtn && fileEl) {
      uploadBtn.addEventListener("click", function () {
        upload(fileEl.files && fileEl.files[0]);
      });
    }

    if (dropzone) {
      ["dragenter", "dragover"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.add("is-dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.remove("is-dragover");
        });
      });
      dropzone.addEventListener("drop", function (e) {
        var dt = e.dataTransfer;
        var file = dt && dt.files && dt.files[0];
        if (file) upload(file);
      });
    }

    // --- Import d'un corpus distant ---------------------------------------
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
              importStatus.textContent = r.body.detail || "HTTP " + r.status;
              return;
            }
            window.location.reload();
          })
          .catch(function () {
            importBtn.disabled = false;
            importStatus.textContent = "error";
          });
      });
    }

    // --- Suppression d'un corpus ------------------------------------------
    var delButtons = document.querySelectorAll(".c-del");
    for (var d = 0; d < delButtons.length; d++) bindDelete(delButtons[d]);

    function bindDelete(btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-corpus");
        if (!id) return;
        var headers = {};
        headers[CSRF] = "1";
        btn.disabled = true;
        fetchJson("/api/corpus/" + encodeURIComponent(id), {
          method: "DELETE",
          headers: headers,
        })
          .then(function (r) {
            if (r.ok) window.location.reload();
            else btn.disabled = false;
          })
          .catch(function () {
            btn.disabled = false;
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
