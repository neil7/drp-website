/* Admin dashboard: copy-to-clipboard for private links. */
(function () {
  "use strict";

  const toastEl = document.getElementById("toast");
  let timer;
  function toast(msg, isError) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.toggle("error", !!isError);
    toastEl.classList.add("show");
    clearTimeout(timer);
    timer = setTimeout(() => toastEl.classList.remove("show"), 2000);
  }

  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const text = btn.dataset.copy;
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied";
        setTimeout(() => (btn.textContent = "Copy"), 1500);
        toast("Link copied to clipboard");
      } catch {
        // Fallback for non-secure contexts
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          toast("Link copied to clipboard");
        } catch {
          toast("Could not copy — select the link manually.", true);
        }
        document.body.removeChild(ta);
      }
    });
  });
})();
