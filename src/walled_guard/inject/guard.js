// Prompt and file interception. Capture-phase listeners block the original event, ask Python to inspect
// the content, and re-fire the original action only if Python answers "allow".
(function () {
  "use strict";
  if (window !== window.top || window.__wgInstalled) return;
  var site = window.__wgResolveSite();
  if (!site) return;
  window.__wgInstalled = true;

  var allowOnce = false;
  var pendingPrompt = false;

  function log() {
    console.debug.apply(console, ["[WG]"].concat([].slice.call(arguments)));
  }

  function firstMatch(selectors, filter) {
    for (var i = 0; i < selectors.length; i++) {
      var list = document.querySelectorAll(selectors[i]);
      for (var j = 0; j < list.length; j++) {
        if (!filter || filter(list[j])) return list[j];
      }
    }
    return null;
  }

  function getComposer() { return firstMatch(site.composer); }

  function getText(el) {
    if (!el) return "";
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") return el.value;
    return el.innerText || el.textContent || "";
  }

  function closestOf(target, selectors) {
    if (!target || !target.closest) return null;
    for (var i = 0; i < selectors.length; i++) {
      var hit = target.closest(selectors[i]);
      if (hit) return hit;
    }
    return null;
  }

  function isInComposer(target) { return !!closestOf(target, site.composer); }

  function findSendButton() {
    return firstMatch(site.sendButton, function (b) {
      return !b.disabled && b.getAttribute("aria-disabled") !== "true";
    });
  }

  function hasText() { return getText(getComposer()).trim().length > 0; }

  function block(e) {
    e.preventDefault();
    e.stopImmediatePropagation();
  }

  function refire(btn, composer) {
    var form = composer && composer.closest && composer.closest("form");
    var target = btn && btn.isConnected ? btn : findSendButton();
    if (target) { target.click(); return; }
    if (form && form.requestSubmit) { form.requestSubmit(); return; }
    ["keydown", "keypress", "keyup"].forEach(function (type) {
      composer.dispatchEvent(new KeyboardEvent(type, {
        key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true,
      }));
    });
  }

  async function startPromptFlow(btn) {
    if (pendingPrompt) return;
    pendingPrompt = true;
    var composer = getComposer();
    var res = { action: "allow" };
    try {
      var text = getText(composer);
      if (typeof window.__wg_inspect_prompt !== "function") throw new Error("binding missing");
      res = await window.__wg_inspect_prompt({ site: site.key, text: text });
    } catch (err) {
      log("prompt inspection failed, allowing", String(err));
      res = { action: "allow" };
    } finally {
      pendingPrompt = false;
    }
    if (res && res.action === "block") {
      log("prompt blocked");
      if (composer && composer.focus) composer.focus();
      return;
    }
    allowOnce = true;
    try { refire(btn, composer); } finally { allowOnce = false; }
  }

  window.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.shiftKey || e.isComposing || allowOnce) return;
    if (!isInComposer(e.target) || !hasText()) return;
    block(e);
    startPromptFlow(null);
  }, true);

  window.addEventListener("click", function (e) {
    if (allowOnce) return;
    var btn = closestOf(e.target, site.sendButton);
    if (!btn || !hasText()) return;
    block(e);
    startPromptFlow(btn);
  }, true);

  window.addEventListener("submit", function (e) {
    if (allowOnce) return;
    var composer = getComposer();
    if (!composer || !e.target.contains || !e.target.contains(composer) || !hasText()) return;
    block(e);
    startPromptFlow(null);
  }, true);


  // ---------------------------------------------------------------- file interception
  var busyFiles = 0;
  var fileQueue = Promise.resolve();

  function enqueue(job) {
    busyFiles++;
    fileQueue = fileQueue.then(job).catch(function (err) {
      log("file flow failed", String(err));
    }).then(function () { busyFiles--; });
  }

  function toBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var url = String(reader.result);
        resolve(url.slice(url.indexOf(",") + 1));
      };
      reader.onerror = function () { reject(reader.error); };
      reader.readAsDataURL(file);
    });
  }

  // Inspects files one at a time (one dialog at a time); returns the files that may proceed.
  async function fileFlow(files) {
    var allowed = [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      var res = { action: "allow" };
      if (f.size > (window.__WG_CONFIG.maxFileBytes || Infinity)) {
        console.warn("[WG] file too large to inspect, allowing:", f.name);
      } else {
        try {
          if (typeof window.__wg_inspect_file !== "function") throw new Error("binding missing");
          var b64 = await toBase64(f);
          res = await window.__wg_inspect_file({
            site: site.key, name: f.name, type: f.type, size: f.size, b64: b64,
          });
        } catch (err) {
          log("file inspection failed, allowing", String(err));
          res = { action: "allow" };
        }
      }
      if (!res || res.action !== "block") allowed.push(f);
    }
    return allowed;
  }

  function toDataTransfer(files) {
    var dt = new DataTransfer();
    files.forEach(function (f) { dt.items.add(f); });
    return dt;
  }

  function redispatch(fn) {
    allowOnce = true;
    try { fn(); } finally { allowOnce = false; }
  }

  function isFileInput(t) {
    return !!t && t.tagName === "INPUT" && t.type === "file";
  }

  function onFileInputEvent(e) {
    if (allowOnce || !isFileInput(e.target)) return;
    e.stopImmediatePropagation();
    if (e.type !== "change") return;
    var input = e.target;
    var picked = Array.prototype.slice.call(input.files || []);
    enqueue(async function () {
      var allowed = picked.length ? await fileFlow(picked) : [];
      if (picked.length && allowed.length === 0) { input.value = ""; return; }
      if (allowed.length !== picked.length) input.files = toDataTransfer(allowed).files;
      redispatch(function () {
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    });
  }
  window.addEventListener("input", onFileInputEvent, true);
  window.addEventListener("change", onFileInputEvent, true);

  window.addEventListener("drop", function (e) {
    if (allowOnce || !e.dataTransfer || e.dataTransfer.files.length === 0) return;
    block(e);
    var dropped = Array.prototype.slice.call(e.dataTransfer.files);
    var target = e.target, x = e.clientX, y = e.clientY;
    enqueue(async function () {
      var allowed = await fileFlow(dropped);
      if (allowed.length === 0) return;
      redispatch(function () {
        target.dispatchEvent(new DragEvent("drop", {
          bubbles: true, cancelable: true, dataTransfer: toDataTransfer(allowed), clientX: x, clientY: y,
        }));
      });
    });
  }, true);

  window.addEventListener("paste", function (e) {
    var cd = e.clipboardData;
    if (allowOnce || !cd || cd.files.length === 0) return;
    block(e);
    var pasted = Array.prototype.slice.call(cd.files);
    var plain = cd.getData("text/plain"), html = cd.getData("text/html");
    var target = e.target;
    enqueue(async function () {
      var allowed = await fileFlow(pasted);
      if (allowed.length === 0 && !plain && !html) return;
      var dt = toDataTransfer(allowed);
      if (plain) dt.setData("text/plain", plain);
      if (html) dt.setData("text/html", html);
      redispatch(function () {
        target.dispatchEvent(new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: dt }));
      });
    });
  }, true);

  window.__wgDebug = function () {
    var info = {
      siteKey: site.key,
      composerFound: !!getComposer(),
      sendButtonFound: !!findSendButton(),
      responseCount: document.querySelectorAll(site.responseSelectors.join(",")).length,
      styleTagPresent: !!document.getElementById("__wg_style"),
      fileInputCount: document.querySelectorAll("input[type=file]").length,
      pending: pendingPrompt || busyFiles > 0,
    };
    log("debug", JSON.stringify(info));
    return info;
  };
})();
