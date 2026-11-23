// Response text colour: injects CSS for the assistant-message selectors of the current site.
(function () {
  "use strict";
  if (window !== window.top || window.__wgStyleInstalled) return;
  var site = window.__wgResolveSite();
  if (!site) return;
  window.__wgStyleInstalled = true;

  var color = (window.__WG_CONFIG || {}).color;
  var css = site.responseSelectors.map(function (s) {
    return s + ", " + s + " * { color: " + color + " !important; -webkit-text-fill-color: " + color + " !important; }";
  }).join("\n");

  function ensureStyle() {
    var root = document.head || document.documentElement;
    if (!root || document.getElementById("__wg_style")) return;
    var el = document.createElement("style");
    el.id = "__wg_style";
    el.textContent = css;
    root.appendChild(el);
  }

  ensureStyle();
  new MutationObserver(ensureStyle).observe(document, { childList: true, subtree: true });
})();
