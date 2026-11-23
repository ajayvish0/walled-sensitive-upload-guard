// Prompt interception. Capture-phase listeners block the original event, ask Python to inspect
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

  window.__wgDebug = function () {
    var info = {
      siteKey: site.key,
      composerFound: !!getComposer(),
      sendButtonFound: !!findSendButton(),
      responseCount: document.querySelectorAll(site.responseSelectors.join(",")).length,
      styleTagPresent: !!document.getElementById("__wg_style"),
      fileInputCount: document.querySelectorAll("input[type=file]").length,
      pending: pendingPrompt,
    };
    log("debug", JSON.stringify(info));
    return info;
  };
})();
