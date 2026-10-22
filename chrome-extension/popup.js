async function load() {
  const { baseUrl } = await chrome.storage.sync.get({ baseUrl: "http://localhost:8000" });
  document.getElementById("baseUrl").value = baseUrl;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const title = document.title || "";
        const url = location.href;
        let company = "";
        const og = document.querySelector('meta[property="og:site_name"]');
        if (og) company = og.content || "";
        const text = (document.body && document.body.innerText) || "";
        return { title, url, company, description: text.slice(0, 8000) };
      },
    });
    if (result) {
      document.getElementById("title").value = result.title || "";
      document.getElementById("url").value = result.url || "";
      document.getElementById("company").value = result.company || "";
      document.getElementById("description").value = result.description || "";
    }
  } catch (e) {
    document.getElementById("msg").textContent = "Could not read page – paste manually.";
    document.getElementById("msg").className = "err";
  }
}

document.getElementById("saveSettings").addEventListener("click", async () => {
  const baseUrl = document.getElementById("baseUrl").value.replace(/\/$/, "");
  await chrome.storage.sync.set({ baseUrl });
  document.getElementById("msg").textContent = "Saved.";
  document.getElementById("msg").className = "ok";
});

document.getElementById("clip").addEventListener("click", async () => {
  const baseUrl = document.getElementById("baseUrl").value.replace(/\/$/, "") || "http://localhost:8000";
  await chrome.storage.sync.set({ baseUrl });
  const q = new URLSearchParams({
    title: document.getElementById("title").value,
    url: document.getElementById("url").value,
    description: document.getElementById("description").value.slice(0, 8000),
  });
  // company is entered on the import page if empty
  chrome.tabs.create({ url: `${baseUrl}/jobs/clip?${q.toString()}` });
});

load();
