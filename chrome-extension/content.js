// Optional page helpers for LinkedIn / Greenhouse title cleanup
(function () {
  window.__jobAgentClip = function () {
    return {
      title: document.title,
      url: location.href,
      text: (document.body && document.body.innerText || "").slice(0, 8000),
    };
  };
})();
