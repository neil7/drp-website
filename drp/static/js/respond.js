/* Availability grid: click / drag-to-paint, whole-day toggles, week tabs, autosave. */
(function () {
  "use strict";

  const area = document.getElementById("grid-area");
  if (!area) return;

  const token = area.dataset.token;
  const cells = Array.from(area.querySelectorAll(".cell"));
  const dayButtons = Array.from(area.querySelectorAll(".grid-day[data-day]"));
  const weekTabs = Array.from(area.querySelectorAll(".week-tab"));
  const weekPanels = Array.from(area.querySelectorAll(".week-panel"));
  const prevBtn = document.getElementById("prev-week");
  const nextBtn = document.getElementById("next-week");
  const noteEl = document.getElementById("note");
  const countEl = document.getElementById("count");
  const progressEl = document.getElementById("progress");
  const lastSavedEl = document.getElementById("last-saved");
  const statusEl = document.getElementById("save-status");
  const statusText = statusEl ? statusEl.querySelector(".save-text") : null;
  const toastEl = document.getElementById("toast");
  const clearBtn = document.getElementById("clear-all");

  const totalSlots = cells.length;
  const selected = new Set(cells.filter((c) => c.classList.contains("on")).map((c) => c.dataset.key));

  // ---------- rendering helpers ----------
  function setCell(cell, on) {
    cell.classList.toggle("on", on);
    cell.setAttribute("aria-pressed", on ? "true" : "false");
    if (on) selected.add(cell.dataset.key);
    else selected.delete(cell.dataset.key);
  }

  function refreshSummary() {
    countEl.textContent = selected.size;
    progressEl.style.width = totalSlots ? Math.min(100, (selected.size / totalSlots) * 100) + "%" : "0%";

    // per-week counts on tabs
    const perWeek = {};
    cells.forEach((c) => {
      if (c.classList.contains("on")) perWeek[c.dataset.week] = (perWeek[c.dataset.week] || 0) + 1;
    });
    weekTabs.forEach((tab) => {
      const n = perWeek[tab.dataset.week] || 0;
      tab.querySelector(".week-tab-count").textContent = n ? n : "";
    });

    // day headers: mark days where everything is selected
    dayButtons.forEach((btn) => {
      const dayCells = cells.filter((c) => c.dataset.day === btn.dataset.day);
      btn.classList.toggle("all-on", dayCells.length > 0 && dayCells.every((c) => c.classList.contains("on")));
    });
  }

  function showLastSaved(iso) {
    if (!iso) return;
    const when = new Date(iso);
    if (isNaN(when)) return;
    lastSavedEl.textContent =
      "Last saved " + when.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }
  // Re-render the server's UTC timestamp in the visitor's local time zone.
  showLastSaved(lastSavedEl.dataset.updated);

  function setStatus(state, text) {
    if (!statusEl) return;
    statusEl.dataset.state = state;
    if (statusText) statusText.textContent = text;
  }

  let toastTimer;
  function toast(msg, isError) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.toggle("error", !!isError);
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 2400);
  }

  // ---------- autosave ----------
  let saveTimer = null;
  let inFlight = false;
  let queued = false;

  function scheduleSave(delay) {
    setStatus("saving", "Unsaved changes…");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, delay == null ? 700 : delay);
  }

  async function save() {
    saveTimer = null;
    if (inFlight) {
      queued = true;
      return;
    }
    inFlight = true;
    setStatus("saving", "Saving…");
    try {
      const res = await fetch("/api/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, slots: Array.from(selected), note: noteEl.value }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Save failed (" + res.status + ")");
      setStatus("saved", "Saved");
      showLastSaved(data.updated_at);
    } catch (err) {
      setStatus("error", "Not saved");
      toast(err.message || "Could not save. Check your connection and try again.", true);
    } finally {
      inFlight = false;
      if (queued) {
        queued = false;
        save();
      }
    }
  }

  function changed() {
    refreshSummary();
    scheduleSave();
  }

  // ---------- pointer interactions (click + drag-to-paint) ----------
  let painting = false;
  let paintValue = true;
  let moved = false;

  function cellFromPoint(x, y) {
    const el = document.elementFromPoint(x, y);
    return el ? el.closest(".cell") : null;
  }

  area.addEventListener("pointerdown", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell || e.button !== 0) return;
    e.preventDefault();
    painting = true;
    moved = false;
    paintValue = !cell.classList.contains("on");
    setCell(cell, paintValue);
    refreshSummary();
  });

  area.addEventListener("pointermove", (e) => {
    if (!painting) return;
    const cell = cellFromPoint(e.clientX, e.clientY);
    if (cell && cell.classList.contains("on") !== paintValue) {
      moved = true;
      setCell(cell, paintValue);
      refreshSummary();
    }
  });

  function endPaint() {
    if (!painting) return;
    painting = false;
    scheduleSave();
  }
  window.addEventListener("pointerup", endPaint);
  window.addEventListener("pointercancel", endPaint);

  // Keyboard accessibility: Enter/Space toggles via the native click (pointerdown doesn't fire).
  cells.forEach((cell) => {
    cell.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setCell(cell, !cell.classList.contains("on"));
        changed();
      }
    });
  });

  // Whole-day toggle
  dayButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const dayCells = cells.filter((c) => c.dataset.day === btn.dataset.day);
      const allOn = dayCells.every((c) => c.classList.contains("on"));
      dayCells.forEach((c) => setCell(c, !allOn));
      changed();
    });
  });

  clearBtn.addEventListener("click", () => {
    if (!selected.size) return;
    if (!confirm("Clear all selected blocks?")) return;
    cells.forEach((c) => setCell(c, false));
    changed();
    toast("Cleared all blocks");
  });

  // Note autosave (debounced)
  noteEl.addEventListener("input", () => scheduleSave(1200));

  // ---------- week tabs ----------
  let currentWeek = 0;
  function showWeek(i) {
    currentWeek = Math.max(0, Math.min(weekPanels.length - 1, i));
    weekTabs.forEach((t, idx) => t.classList.toggle("active", idx === currentWeek));
    weekPanels.forEach((p, idx) => p.classList.toggle("active", idx === currentWeek));
    prevBtn.disabled = currentWeek === 0;
    nextBtn.disabled = currentWeek === weekPanels.length - 1;
    weekTabs[currentWeek].scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  }
  weekTabs.forEach((t) => t.addEventListener("click", () => showWeek(Number(t.dataset.week))));
  prevBtn.addEventListener("click", () => showWeek(currentWeek - 1));
  nextBtn.addEventListener("click", () => showWeek(currentWeek + 1));

  // Warn if leaving mid-save
  window.addEventListener("beforeunload", (e) => {
    if (inFlight || saveTimer) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  refreshSummary();
  showWeek(0);
})();
