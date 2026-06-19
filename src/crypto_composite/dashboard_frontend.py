from __future__ import annotations


def render_dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crypto Composite Data Health</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #07111f;
      color: #e6edf7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 12% 4%, rgba(41, 121, 255, 0.18), transparent 28rem),
        radial-gradient(circle at 88% 2%, rgba(20, 184, 166, 0.12), transparent 24rem),
        #07111f;
    }
    main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0 64px; }
    header { display: grid; gap: 14px; margin-bottom: 28px; }
    h1 { margin: 0; max-width: 760px; font-size: clamp(2.2rem, 6vw, 4.6rem); line-height: 0.98; letter-spacing: -0.055em; }
    h2 { margin: 0; font-size: 1.05rem; letter-spacing: -0.01em; }
    p { margin: 0; color: #9fb0c7; line-height: 1.6; }
    .eyebrow { color: #6ee7d8; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; }
    .header-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
    .badge { display: inline-flex; align-items: center; gap: 7px; width: fit-content; padding: 7px 11px; border: 1px solid #304158; border-radius: 999px; color: #b8c5d8; background: rgba(10, 22, 38, 0.8); font-size: 0.78rem; font-weight: 750; }
    .badge::before { width: 7px; height: 7px; border-radius: 50%; background: #64748b; content: ""; }
    .badge.ok { color: #a7f3d0; border-color: rgba(52, 211, 153, 0.35); }
    .badge.ok::before { background: #34d399; box-shadow: 0 0 12px #34d399; }
    .badge.error { color: #fecaca; border-color: rgba(248, 113, 113, 0.4); }
    .badge.error::before { background: #f87171; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 24px 0; }
    .card, .panel { border: 1px solid rgba(148, 163, 184, 0.18); background: rgba(10, 22, 38, 0.78); box-shadow: 0 20px 70px rgba(0, 0, 0, 0.18); backdrop-filter: blur(16px); }
    .card { min-height: 120px; padding: 18px; border-radius: 16px; }
    .card span { color: #8395ad; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    .card strong { display: block; margin-top: 14px; font-size: 1.8rem; font-variant-numeric: tabular-nums; }
    .panel { margin-top: 14px; padding: 20px; border-radius: 18px; overflow: hidden; }
    .panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
    .panel-head p { font-size: 0.82rem; }
    .table-wrap { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    th, td { padding: 12px 10px; border-bottom: 1px solid rgba(148, 163, 184, 0.12); text-align: left; vertical-align: middle; }
    th { color: #8395ad; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; }
    td { color: #d7e1ef; }
    td.path { min-width: 280px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.8rem; }
    button { border: 1px solid #334761; border-radius: 9px; padding: 7px 10px; color: #dbeafe; background: #13243a; cursor: pointer; font: inherit; font-size: 0.78rem; font-weight: 700; }
    button:hover { border-color: #5b7ca5; background: #19304e; }
    pre { min-height: 150px; max-height: 480px; margin: 0; padding: 16px; overflow: auto; border-radius: 12px; color: #b9d8ff; background: #050c16; font-size: 0.78rem; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
    .empty { padding: 18px 10px; color: #8395ad; text-align: center; }
    .boundary { margin-top: 18px; padding: 14px 16px; border-left: 3px solid #2dd4bf; color: #9fb0c7; background: rgba(20, 184, 166, 0.07); font-size: 0.82rem; }
    @media (max-width: 820px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } main { padding-top: 30px; } }
    @media (max-width: 480px) { .grid { grid-template-columns: 1fr; } .panel { padding: 14px; } }
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">Read-only artifact inspection</p>
    <h1>Crypto Composite Data Health</h1>
    <p>Inspect generated JSON coverage, validation context, and artifact files from the local dashboard API.</p>
    <div class="header-row"><span id="service-state" class="badge">Connecting</span></div>
  </header>

  <section class="grid" aria-label="Artifact summary">
    <article class="card"><span>Artifacts</span><strong id="artifact-count">-</strong></article>
    <article class="card"><span>Total size</span><strong id="total-size">-</strong></article>
    <article class="card"><span>Quality files</span><strong id="quality-count">-</strong></article>
    <article class="card"><span>Known roots</span><strong id="known-count">-</strong></article>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>Data quality</h2><p>Reported by generated data_quality.json files</p></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Artifact</th><th>Timeframe</th><th>Status</th><th>Overall quality</th><th>Venue coverage</th></tr></thead>
        <tbody id="quality-body"><tr><td class="empty" colspan="5">Loading data-quality artifacts...</td></tr></tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>Artifact manifest</h2><p>JSON files exposed by /api/artifacts</p></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Path</th><th>Size</th><th>Inspect</th></tr></thead>
        <tbody id="artifact-body"><tr><td class="empty" colspan="3">Loading artifact index...</td></tr></tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>JSON inspector</h2><p id="inspector-path">Select an artifact</p></div>
    <pre id="inspector">No artifact selected.</pre>
  </section>

  <p class="boundary">Data-quality inspection only. No trading signals, asset rankings, order execution, position sizing, predictions, or financial advice.</p>
</main>
<script>
  const serviceState = document.getElementById("service-state");
  const artifactCount = document.getElementById("artifact-count");
  const totalSize = document.getElementById("total-size");
  const qualityCount = document.getElementById("quality-count");
  const knownCount = document.getElementById("known-count");
  const artifactBody = document.getElementById("artifact-body");
  const qualityBody = document.getElementById("quality-body");
  const inspector = document.getElementById("inspector");
  const inspectorPath = document.getElementById("inspector-path");

  function formatBytes(value) {
    if (!Number.isFinite(value) || value < 0) return "unknown";
    if (value < 1024) return `${value} B`;
    if (value < 1048576) return `${(value / 1024).toFixed(1)} KiB`;
    return `${(value / 1048576).toFixed(1)} MiB`;
  }

  function addCell(row, value, className) {
    const cell = document.createElement("td");
    cell.textContent = String(value);
    if (className) cell.className = className;
    row.appendChild(cell);
    return cell;
  }

  async function getJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  async function inspectArtifact(path) {
    inspectorPath.textContent = path;
    inspector.textContent = "Loading...";
    try {
      const payload = await getJson(`/api/artifact?path=${encodeURIComponent(path)}`);
      inspector.textContent = JSON.stringify(payload, null, 2);
    } catch (error) {
      inspector.textContent = `Artifact read failed: ${error.message}`;
    }
  }

  function renderArtifacts(items) {
    artifactBody.replaceChildren();
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = addCell(row, "No JSON artifacts found.", "empty");
      cell.colSpan = 3;
      artifactBody.appendChild(row);
      return;
    }
    for (const item of items) {
      const row = document.createElement("tr");
      addCell(row, item.path, "path");
      addCell(row, formatBytes(item.size_bytes));
      const actionCell = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "View JSON";
      button.addEventListener("click", () => inspectArtifact(item.path));
      actionCell.appendChild(button);
      row.appendChild(actionCell);
      artifactBody.appendChild(row);
    }
  }

  async function renderQuality(items) {
    qualityBody.replaceChildren();
    let rows = 0;
    for (const item of items) {
      try {
        const payload = await getJson(`/api/artifact?path=${encodeURIComponent(item.path)}`);
        if (!payload || typeof payload !== "object" || Array.isArray(payload)) continue;
        for (const [timeframe, report] of Object.entries(payload)) {
          if (!report || typeof report !== "object" || Array.isArray(report)) continue;
          const requested = Array.isArray(report.venues_requested) ? report.venues_requested.length : 0;
          const available = Array.isArray(report.venues_ok) ? report.venues_ok.length : 0;
          const coverage = requested ? `${available}/${requested}` : "unknown";
          const row = document.createElement("tr");
          addCell(row, item.path, "path");
          addCell(row, timeframe);
          addCell(row, report.status ?? "unknown");
          addCell(row, report.overall_quality ?? "unknown");
          addCell(row, coverage);
          qualityBody.appendChild(row);
          rows += 1;
        }
      } catch (error) {
        const row = document.createElement("tr");
        const cell = addCell(row, `${item.path}: ${error.message}`, "empty");
        cell.colSpan = 5;
        qualityBody.appendChild(row);
        rows += 1;
      }
    }
    if (!rows) {
      const row = document.createElement("tr");
      const cell = addCell(row, "No readable data-quality rows found.", "empty");
      cell.colSpan = 5;
      qualityBody.appendChild(row);
    }
  }

  async function loadDashboard() {
    try {
      const [health, index] = await Promise.all([getJson("/api/health"), getJson("/api/artifacts")]);
      if (health.status !== "OK") throw new Error("dashboard health is not OK");
      const items = Array.isArray(index.artifacts) ? index.artifacts : [];
      serviceState.textContent = "Service healthy";
      serviceState.className = "badge ok";
      artifactCount.textContent = String(index.artifact_count ?? items.length);
      totalSize.textContent = formatBytes(items.reduce((sum, item) => sum + Number(item.size_bytes || 0), 0));
      const qualityItems = items.filter((item) => item.path === "data_quality.json" || item.path.endsWith("/data_quality.json"));
      qualityCount.textContent = String(qualityItems.length);
      const known = index.well_known && typeof index.well_known === "object" ? Object.values(index.well_known).filter(Boolean).length : 0;
      knownCount.textContent = String(known);
      renderArtifacts(items);
      await renderQuality(qualityItems);
    } catch (error) {
      serviceState.textContent = "Service error";
      serviceState.className = "badge error";
      inspector.textContent = `Dashboard load failed: ${error.message}`;
    }
  }

  loadDashboard();
</script>
</body>
</html>
"""
