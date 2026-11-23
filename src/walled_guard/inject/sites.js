// Per-site selectors. Verified live against the real sites; adjust here if their DOM changes.
window.__WG_SITES = {
  chatgpt: {
    hosts: ["chatgpt.com"],
    composer: ["#prompt-textarea", "div.ProseMirror[contenteditable='true']", "textarea[aria-label='Chat with ChatGPT']", "#mobile-composer-prompt"],
    sendButton: ["button[data-testid='send-button']", "button[aria-label='Send message']", "button[aria-label*='Send' i]"],
    responseSelectors: ["[data-message-author-role='assistant']"],
  },
  perplexity: {
    hosts: ["www.perplexity.ai", "perplexity.ai"],
    composer: ["#ask-input", "div[contenteditable='true'][role='textbox']", "textarea"],
    sendButton: ["button[data-testid='submit-button']", "button[aria-label='Submit']", "button[aria-label*='Submit' i]"],
    responseSelectors: ["div[id^='markdown-content']", "div.prose"],
  },
  // Test page only: active when window.__WG_CONFIG.enableHarness is true.
  harness: {
    hosts: ["harness.local"],
    composer: ["#composer"],
    sendButton: ["#send"],
    responseSelectors: [".fake-assistant"],
  },
};

// Returns {key, ...siteConfig} for the current page, or null when this host is not guarded.
window.__wgResolveSite = function () {
  var cfg = window.__WG_CONFIG || {};
  var found = null;
  Object.keys(window.__WG_SITES).forEach(function (key) {
    if (key === "harness" && !cfg.enableHarness) return;
    var site = window.__WG_SITES[key];
    if (site.hosts.indexOf(location.hostname) !== -1) found = Object.assign({ key: key }, site);
  });
  return found;
};
