// YT Empire Autopilot — static dashboard on GitHub Pages (no Vercel, no secrets).
// Dashboard URL: https://kulbeer683-sketch.github.io/yt-empire-autopilot/
// OAuth cannot complete on a static Pages site (no backend callback).
// Real OAuth is done locally via http://localhost:8080/ (see README).
// Customize / Run Now run in GitHub Actions. This file only loads public
// repo data (niches + strategy_memory.json) for display.
const NICHE_URLS = [
  "./config/niches.json",
  "../config/niches.json",
  "https://raw.githubusercontent.com/kulbeer683-sketch/yt-empire-autopilot/main/config/niches.json",
];
const MEMORY_URLS = [
  "./strategy_memory.json",
  "../strategy_memory.json",
  "https://raw.githubusercontent.com/kulbeer683-sketch/yt-empire-autopilot/main/strategy_memory.json",
];

async function fetchFirst(urls) {
  for (const u of urls) {
    try {
      const r = await fetch(u);
      if (r.ok) return await r.json();
    } catch (e) { /* try next */ }
  }
  return null;
}

let niches = null;

async function loadNiches() {
  niches = await fetchFirst(NICHE_URLS);
  const sel = document.getElementById("nicheSelect");
  if (!niches) { sel.innerHTML = "<option>finance</option>"; return; }
  sel.innerHTML = Object.entries(niches)
    .map(([k, v]) => `<option value="${k}">${v.display_name}</option>`).join("");
  sel.value = "finance";
  showIdentity();
}

function showIdentity() {
  const key = document.getElementById("nicheSelect").value;
  const n = niches && niches[key];
  const el = document.getElementById("identityPreview");
  if (!n) { el.textContent = ""; return; }
  el.textContent =
    `Brand ideas: ${n.brand_name_ideas.slice(0, 3).join(" • ")}\n` +
    `Handles: ${n.handle_ideas.slice(0, 3).join(" • ")}\n` +
    `Palette: ${n.color_palette.primary} / ${n.color_palette.secondary} / ${n.color_palette.accent}\n` +
    `Playlists: ${n.playlists.map((p) => p.title).join(" • ")}`;
}

async function loadBrain() {
  const mem = await fetchFirst(MEMORY_URLS);
  const el = document.getElementById("brainLogs");
  if (!mem) { el.textContent = "strategy_memory.json not reachable yet — run the autopilot once (see README)."; return; }
  el.textContent = JSON.stringify(mem, null, 2);
  document.getElementById("winningFormats").textContent = (mem.winning_formats || []).join(", ") || "—";
  document.getElementById("losingTopics").textContent = (mem.losing_topics || []).join(", ") || "—";
}

document.getElementById("nicheSelect").addEventListener("change", showIdentity);
document.getElementById("refreshBrainBtn").addEventListener("click", loadBrain);
document.getElementById("customizeBtn").addEventListener("click", () => {
  alert("Auto-Customize runs server-side (channel_customizer.py / GitHub Actions). " +
        "Connect YouTube first, then use Run Now or the scheduled workflow. See README.md.");
});
document.getElementById("runNowBtn").addEventListener("click", () => {
  document.getElementById("runStatus").textContent =
    "Run Now triggers the GitHub Actions workflow (workflow_dispatch). See README for the exact steps.";
  alert("Run Now: in GitHub, go to Actions → Autopilot → Run workflow. No secrets are handled here.");
});
document.getElementById("autopilotToggle").addEventListener("change", (e) => {
  const badge = document.getElementById("statusBadge");
  badge.textContent = e.target.checked ? "● Autopilot ON" : "● Autopilot OFF";
  badge.classList.toggle("on", e.target.checked);
});

const connectBtn = document.getElementById("connectBtn");
if (connectBtn) connectBtn.addEventListener("click", () => {
  alert("YouTube OAuth cannot finish on this static GitHub Pages site — there is no backend callback. Run OAuth locally (http://localhost:8080/, see README > Google OAuth) to get a refresh token, then add it as a GitHub Secret. The dashboard itself is UI + logs only.");
});

loadNiches();
loadBrain();
