from __future__ import annotations

import json
from typing import Any


def _embedded_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).replace("<", "\\u003c")


def render_dashboard_html(
    embedded_snapshot: dict[str, Any] | None = None,
    embedded_index: dict[str, Any] | None = None,
    artifact_base_url: str | None = None,
) -> str:
    html = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Observed Market Structure</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #071019; color: #e7edf5;
      --surface: rgba(13, 27, 41, .92); --line: rgba(148, 163, 184, .18);
      --muted: #8fa1b5; --cyan: #57d8cc; --blue: #72a7ff; --amber: #f4bf67;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 8% 0, #123153 0, transparent 30rem), radial-gradient(circle at 92% 8%, #103b3b 0, transparent 28rem), #071019; }
    main { width: min(1280px, calc(100% - 32px)); margin: 0 auto; padding: 34px 0 60px; }
    header { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: end; margin-bottom: 22px; }
    h1 { margin: 5px 0 10px; font-size: clamp(2rem, 5vw, 4.2rem); line-height: .98; letter-spacing: -.055em; }
    h2 { margin: 0; font-size: 1rem; letter-spacing: -.01em; }
    p { margin: 0; color: var(--muted); line-height: 1.55; }
    .eyebrow { color: var(--cyan); font-size: .72rem; font-weight: 850; letter-spacing: .16em; text-transform: uppercase; }
    .badge { display: inline-flex; align-items: center; gap: 8px; margin-top: 14px; padding: 7px 11px; border: 1px solid var(--line); border-radius: 999px; color: #b8c7d9; background: #0a1724; font-size: .76rem; font-weight: 750; }
    .badge::before { width: 7px; height: 7px; border-radius: 50%; background: #6b7d91; content: ""; }
    .badge.ok::before { background: var(--cyan); box-shadow: 0 0 12px var(--cyan); }
    .badge.error::before { background: #ff8290; }
    .source-note { max-width: 760px; margin-top: 9px; color: #f4bf67; font-size: .78rem; }
    .source-note[hidden] { display: none; }
    .filters { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: .68rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    select, button { border: 1px solid #31475d; border-radius: 9px; color: #e4edf7; background: #102236; font: inherit; }
    select { min-width: 136px; padding: 9px 32px 9px 10px; }
    button { padding: 7px 10px; cursor: pointer; font-size: .76rem; font-weight: 750; }
    button:hover { border-color: #6482a0; }
    .cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 11px; margin: 18px 0; }
    .card, .panel, .flow-item { border: 1px solid var(--line); background: var(--surface); box-shadow: 0 20px 60px rgba(0, 0, 0, .2); }
    .card { min-height: 116px; padding: 17px; border-radius: 15px; }
    .card span, .metric-label { color: var(--muted); font-size: .69rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
    .card strong { display: block; margin-top: 13px; font-size: 1.65rem; font-variant-numeric: tabular-nums; }
    .card small { display: block; margin-top: 5px; color: #8498ae; }
    .flow { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 11px; margin-bottom: 11px; }
    .flow-item { position: relative; min-height: 112px; padding: 16px 17px; border-radius: 14px; overflow: hidden; }
    .flow-item::after { position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); content: ""; }
    .flow-item:nth-child(2)::after { background: var(--cyan); } .flow-item:nth-child(3)::after { background: var(--amber); } .flow-item:nth-child(4)::after { background: #c79cff; }
    .flow-item strong { display: block; margin: 10px 0 4px; font-size: .95rem; }
    .flow-item p { font-size: .81rem; }
    .layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(350px, .85fr); gap: 11px; }
    .panel { min-width: 0; padding: 18px; border-radius: 16px; overflow: hidden; }
    .panel.full { grid-column: 1 / -1; }
    .panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
    .panel-head p { font-size: .77rem; }
    svg { display: block; width: 100%; min-height: 250px; overflow: visible; }
    .axis { fill: #8194a9; font-size: 10px; } .gridline { stroke: rgba(148, 163, 184, .13); stroke-width: 1; }
    .table-wrap { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: .81rem; }
    th, td { padding: 11px 9px; border-bottom: 1px solid rgba(148, 163, 184, .12); text-align: left; vertical-align: middle; }
    th { color: var(--muted); font-size: .65rem; letter-spacing: .08em; text-transform: uppercase; }
    td { color: #d8e2ee; font-variant-numeric: tabular-nums; }
    .pill { display: inline-flex; padding: 4px 7px; border: 1px solid #3a526a; border-radius: 999px; font-size: .65rem; font-weight: 850; letter-spacing: .04em; }
    .pill.corroborated { color: #9bf0e4; border-color: #276c68; } .pill.concentrated { color: #ffd58c; border-color: #72552c; } .pill.limited { color: #c9d3df; }
    .insight-grid { display: grid; grid-template-columns: 1.35fr 1fr 1fr; gap: 10px; margin: 0 0 13px; }
    .insight-card { min-height: 102px; padding: 13px 14px; border: 1px solid rgba(148, 163, 184, .15); border-radius: 13px; background: rgba(5, 12, 19, .35); }
    .insight-card span { color: var(--muted); font-size: .64rem; font-weight: 850; letter-spacing: .08em; text-transform: uppercase; }
    .insight-card strong { display: block; margin: 8px 0 5px; color: #eff6ff; font-size: .9rem; }
    .insight-card p { font-size: .77rem; }
    .empty { padding: 18px 8px; color: var(--muted); text-align: center; }
    .callout { margin-top: 12px; padding: 12px 14px; border-left: 3px solid var(--amber); color: #b7c4d2; background: rgba(244, 191, 103, .07); font-size: .78rem; line-height: 1.5; }
    details { margin-top: 11px; } summary { color: #c9d8e7; cursor: pointer; font-size: .82rem; font-weight: 750; }
    pre { max-height: 380px; margin: 12px 0 0; padding: 14px; overflow: auto; border-radius: 10px; color: #b9d8ff; background: #050c13; font-size: .73rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
    .manifest-path { min-width: 260px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .73rem; }
    .boundary { margin-top: 14px; padding: 14px 16px; border: 1px solid rgba(87, 216, 204, .24); border-radius: 13px; color: #9db1c5; background: rgba(87, 216, 204, .055); font-size: .78rem; }
    @media (max-width: 940px) { header { grid-template-columns: 1fr; } .filters { justify-content: flex-start; } .layout { grid-template-columns: 1fr; } .panel.full { grid-column: auto; } .flow { grid-template-columns: repeat(2, minmax(0, 1fr)); } .insight-grid { grid-template-columns: 1fr; } }
    @media (max-width: 720px) { .cards { grid-template-columns: repeat(2, 1fr); } .flow { grid-template-columns: 1fr; } }
    @media (max-width: 460px) { main { width: min(100% - 20px, 1280px); padding-top: 22px; } .cards { grid-template-columns: 1fr; } .panel { padding: 14px; } select { min-width: 0; max-width: 145px; } }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="eyebrow">Dashboard V3 / practical monitoring brief</p>
      <h1>Observed Market Structure</h1>
      <p>Composite price, public depth, and practical zones derived from generated artifacts.</p>
      <span id="service-state" class="badge">Connecting</span>
      <p id="profile-note" class="source-note" hidden></p>
      <p id="source-note" class="source-note" hidden></p>
    </div>
    <div class="filters" aria-label="Dashboard filters">
      <label>Asset<select id="asset-select"></select></label>
      <label>Timeframe<select id="timeframe-select"></select></label>
      <label>Market<select id="market-select"></select></label>
    </div>
  </header>

  <section class="cards" aria-label="Current composite context">
    <article class="card"><span>Reference price</span><strong id="reference-price">-</strong><small id="price-status">No context</small></article>
    <article class="card"><span>Venue coverage</span><strong id="coverage">-</strong><small id="coverage-status">No context</small></article>
    <article class="card"><span>Price dispersion</span><strong id="dispersion">-</strong><small>Latest composite bar</small></article>
    <article class="card"><span>Artifact freshness</span><strong id="freshness">-</strong><small id="generated-at">No timestamp</small></article>
  </section>

  <section class="flow" aria-label="Practical monitoring brief">
    <article class="flow-item"><span class="metric-label">DID / Past</span><strong id="past-title">Unavailable</strong><p id="past-detail">At least two composite bars are required.</p></article>
    <article class="flow-item"><span class="metric-label">DOING / Now</span><strong id="now-title">Unavailable</strong><p id="now-detail">No orderbook context loaded.</p></article>
    <article class="flow-item"><span class="metric-label">NEXT evidence</span><strong id="next-title">Unavailable</strong><p id="next-detail">No evidence check available.</p></article>
    <article class="flow-item"><span class="metric-label">Confidence / Risk</span><strong id="confidence-title">Unavailable</strong><p id="confidence-detail">No evidence quality context loaded.</p></article>
  </section>

  <section class="layout">
    <article class="panel">
      <div class="panel-head"><div><h2>Composite price context</h2><p>Close series with observed orderbook bands</p></div><p id="price-chart-note"></p></div>
      <svg id="price-chart" viewBox="0 0 760 280" role="img" aria-label="Composite close chart"></svg>
    </article>
    <article class="panel">
      <div class="panel-head"><div><h2>Public depth profile</h2><p>Quote depth by observed price bucket</p></div><p id="depth-imbalance"></p></div>
      <svg id="depth-chart" viewBox="0 0 520 280" role="img" aria-label="Public depth profile"></svg>
    </article>

    <article class="panel full">
      <div class="panel-head"><div><h2>Observed zones</h2><p>Practical filtering: concentration and maximum-vacuum bucket per side</p></div><p id="zone-count"></p></div>
      <div class="insight-grid" id="zone-readout" aria-label="Observed zone readout">
        <section class="insight-card"><span>Zone map</span><strong id="zone-readout-title">Loading zone map</strong><p id="zone-readout-detail">Waiting for public-depth evidence.</p></section>
        <section class="insight-card"><span>Next check</span><strong>After refresh</strong><p id="zone-readout-next">Refresh artifacts before comparing zone evidence.</p></section>
        <section class="insight-card"><span>Limit</span><strong>Snapshot only</strong><p id="zone-readout-limit">No future-reaction or hidden-liquidity inference.</p></section>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Zone</th><th>Range</th><th>Location</th><th>Distance</th><th>Depth quote</th><th>Venues</th><th>HHI</th><th>Persistence proxy</th><th>Vacuum</th><th>Evidence</th></tr></thead>
        <tbody id="zone-body"><tr><td class="empty" colspan="10">Loading observed zones...</td></tr></tbody>
      </table></div>
      <p class="callout" id="zone-note">Zone evidence describes the current public snapshot. It does not establish support, resistance, hidden liquidity, or future reaction.</p>
    </article>

    <article class="panel">
      <div class="panel-head"><div><h2>Spot / perpetual context</h2><p>Observed composite-close band</p></div></div>
      <div id="dislocation" class="empty">Both spot and perpetual composite bars are required.</div>
    </article>
    <article class="panel">
      <div class="panel-head"><div><h2>Methodology</h2><p>Source-backed interpretation limits</p></div></div>
      <p id="methodology">Loading methodology...</p>
      <details><summary>Evidence-grade definitions</summary><pre id="evidence-method"></pre></details>
    </article>

    <article class="panel full">
      <div class="panel-head"><div><h2>Artifact manifest</h2><p>Read-only JSON source inspection</p></div><p id="artifact-summary"></p></div>
      <details><summary>Open artifact browser</summary>
        <div class="table-wrap"><table><thead><tr><th>Path</th><th>Size</th><th>Inspect</th></tr></thead><tbody id="artifact-body"></tbody></table></div>
        <pre id="inspector">No artifact selected.</pre>
      </details>
    </article>
  </section>

  <p class="boundary">Observed public-data context only. No trading signal, prediction, asset recommendation, position sizing, order execution, or financial advice. Persistence and spoof-risk fields are artifact proxies, not proof of intent.</p>
</main>
<script>
  const embeddedSnapshot = __EMBEDDED_SNAPSHOT__;
  const embeddedIndex = __EMBEDDED_INDEX__;
  const staticArtifactBase = __ARTIFACT_BASE_URL__;
  const byId = (id) => document.getElementById(id);
  const state = { snapshot: null, index: null };
  const assetSelect = byId("asset-select");
  const timeframeSelect = byId("timeframe-select");
  const marketSelect = byId("market-select");
  const NS = "http://www.w3.org/2000/svg";

  function numeric(value) {
    if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }
  function fmt(value, digits = 2) {
    const number = numeric(value);
    if (number === null) return "unavailable";
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(number);
  }
  function pct(value, digits = 2) { const number = numeric(value); return number === null ? "unavailable" : `${fmt(number * 100, digits)}%`; }
  function signedPercent(value, digits = 3) { const number = numeric(value); return number === null ? "unavailable" : `${number > 0 ? "+" : ""}${fmt(number, digits)}%`; }
  function price(value) { const number = numeric(value); return number === null ? "unavailable" : fmt(number, Math.abs(number) < 10 ? 5 : 2); }
  function bytes(value) { const n = numeric(value); return n === null ? "unknown" : n < 1024 ? `${n} B` : n < 1048576 ? `${fmt(n / 1024, 1)} KiB` : `${fmt(n / 1048576, 1)} MiB`; }
  function relationLabel(value) { return value === "BELOW_REFERENCE" ? "below reference" : value === "ABOVE_REFERENCE" ? "above reference" : value === "CONTAINS_REFERENCE" ? "contains reference" : "unavailable"; }
  function zoneSummary(zone) { return zone ? `${price(zone.price_low)} - ${price(zone.price_high)} / ${zone.evidence_grade || "LIMITED"}` : "unavailable"; }
  function svg(tag, attrs = {}, text = "") { const node = document.createElementNS(NS, tag); for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value); if (text) node.textContent = text; return node; }
  async function getJson(url) {
    if (url === "/api/dashboard-snapshot" && embeddedSnapshot) return embeddedSnapshot;
    if (url === "/api/artifacts" && embeddedIndex) return embeddedIndex;
    if (url === "/api/health" && embeddedSnapshot) return { status: "OK", service: "crypto-composite-dashboard-export" };
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }
  function options(select, values, selected) { select.replaceChildren(); for (const value of values) { const option = document.createElement("option"); option.value = value; option.textContent = value; option.selected = value === selected; select.appendChild(option); } }
  function context() {
    const asset = (state.snapshot?.assets || []).find((item) => String(item.asset) === assetSelect.value);
    const timeframe = asset?.timeframes?.find((item) => item.timeframe === timeframeSelect.value);
    const market = timeframe?.markets?.find((item) => item.market_type === marketSelect.value);
    return { asset, timeframe, market };
  }
  function syncFilters(level) {
    const assets = state.snapshot?.assets || [];
    const assetValue = level === "asset" ? assetSelect.value : (assetSelect.value || String(assets[0]?.asset || ""));
    options(assetSelect, assets.map((item) => String(item.asset)), assetValue);
    const asset = assets.find((item) => String(item.asset) === assetSelect.value) || assets[0];
    const timeframes = asset?.timeframes || [];
    const primary = state.snapshot?.profile?.primary_timeframe;
    const preferredTimeframe = timeframes.some((item) => item.timeframe === primary) ? primary : timeframes[0]?.timeframe;
    const timeframeValue = level === "timeframe" ? timeframeSelect.value : (timeframeSelect.value || preferredTimeframe || "");
    options(timeframeSelect, timeframes.map((item) => item.timeframe), timeframeValue);
    const timeframe = timeframes.find((item) => item.timeframe === timeframeSelect.value) || timeframes[0];
    const markets = timeframe?.markets || [];
    options(marketSelect, markets.map((item) => item.market_type), marketSelect.value || markets[0]?.market_type || "");
  }
  function renderCards(market) {
    const latest = market?.latest_bar || {};
    const book = market?.orderbook || {};
    const generated = numeric(market?.generated_at_ms);
    byId("reference-price").textContent = price(book.reference_price ?? latest.close);
    byId("price-status").textContent = market?.ohlcv_status || "OHLCV unavailable";
    byId("coverage").textContent = pct(book.coverage ?? latest.coverage, 0);
    byId("coverage-status").textContent = book.status || "Orderbook unavailable";
    byId("dispersion").textContent = numeric(latest.price_dispersion_pct) === null ? "unavailable" : `${fmt(latest.price_dispersion_pct, 4)}%`;
    if (generated !== null) {
      const age = Date.now() - generated;
      byId("freshness").textContent = age < 0 ? "clock mismatch" : age < 60000 ? `${Math.floor(age / 1000)}s` : age < 3600000 ? `${Math.floor(age / 60000)}m` : age < 86400000 ? `${Math.floor(age / 3600000)}h` : `${Math.floor(age / 86400000)}d`;
      byId("generated-at").textContent = new Date(generated).toLocaleString();
    } else { byId("freshness").textContent = "unavailable"; byId("generated-at").textContent = "No timestamp"; }
  }
  function renderFlow(market) {
    const brief = market?.monitoring_brief; const past = brief?.past; const now = brief?.now;
    if (numeric(past?.close_change_pct) !== null) {
      byId("past-title").textContent = `Composite close ${signedPercent(past.close_change_pct)}`;
      byId("past-detail").textContent = `Observed over the latest ${past.timeframe} interval from ${past.bar_count} available composite bars; no forward inference.`;
    } else { byId("past-title").textContent = "History unavailable"; byId("past-detail").textContent = "At least two valid composite closes are required."; }

    const bid = now?.nearest_bid_concentration; const ask = now?.nearest_ask_concentration;
    const nearest = [bid ? `Bid ${fmt(bid.distance_to_reference_pct, 3)}% ${relationLabel(bid.reference_relation)}` : null, ask ? `Ask ${fmt(ask.distance_to_reference_pct, 3)}% ${relationLabel(ask.reference_relation)}` : null].filter(Boolean);
    byId("now-title").textContent = nearest.length ? nearest.join(" / ") : "Concentration unavailable";
    const book = now?.book; const zoneText = [bid ? `Bid ${zoneSummary(bid)}` : null, ask ? `Ask ${zoneSummary(ask)}` : null].filter(Boolean).join("; ");
    const imbalance = numeric(book?.depth_imbalance);
    const depthText = book ? `Depth bid ${fmt(book.bid_depth_total, 0)} vs ask ${fmt(book.ask_depth_total, 0)}; imbalance ${imbalance === null ? "unavailable" : signedPercent(imbalance * 100)}.` : "No composite book context.";
    byId("now-detail").textContent = `${zoneText || "No practical concentration range."} ${depthText}`;

    const next = brief?.next_evidence_check;
    byId("next-title").textContent = next?.condition || "Evidence check unavailable";
    byId("next-detail").textContent = next?.observe || "Generate a new artifact snapshot before comparison.";

    const confidence = brief?.confidence_risk; const counts = confidence?.evidence_grade_counts || {};
    const qualityStates = [confidence?.ohlcv_status, confidence?.book_status].filter(Boolean);
    byId("confidence-title").textContent = qualityStates.length ? qualityStates.join(" / ") : "Quality unavailable";
    byId("confidence-detail").textContent = `${pct(confidence?.book_coverage)} book coverage / ${counts.CORROBORATED || 0}/${confidence?.zone_count || 0} zones corroborated. ${confidence?.snapshot_limit || "Snapshot limitations unavailable."}`;
  }
  function renderPriceChart(market) {
    const chart = byId("price-chart"); chart.replaceChildren();
    const bars = market?.bars || []; const zones = market?.observed_zones || [];
    if (!bars.length) { chart.appendChild(svg("text", { x: 380, y: 140, "text-anchor": "middle", class: "axis" }, "No composite bars")); return; }
    const closes = bars.map((bar) => numeric(bar.close)).filter((value) => value !== null);
    const zoneValues = zones.flatMap((zone) => [numeric(zone.price_low), numeric(zone.price_high)]).filter((value) => value !== null);
    if (!closes.length) { chart.appendChild(svg("text", { x: 380, y: 140, "text-anchor": "middle", class: "axis" }, "Composite closes unavailable")); return; }
    let min = Math.min(...closes, ...zoneValues), max = Math.max(...closes, ...zoneValues); if (min === max) { min *= .999; max *= 1.001; }
    const pad = (max - min) * .08; min -= pad; max += pad;
    const x = (i) => 54 + i * 670 / Math.max(bars.length - 1, 1); const y = (value) => 230 - (value - min) / (max - min) * 190;
    for (let i = 0; i <= 4; i++) { const yy = 40 + i * 47.5; chart.appendChild(svg("line", { x1: 54, x2: 724, y1: yy, y2: yy, class: "gridline" })); chart.appendChild(svg("text", { x: 48, y: yy + 4, "text-anchor": "end", class: "axis" }, price(max - i * (max - min) / 4))); }
    for (const zone of zones) { const low = numeric(zone.price_low), high = numeric(zone.price_high); if (low === null || high === null) continue; const top = y(high), bottom = y(low); const color = zone.side === "bid" ? "#72a7ff" : "#f4bf67"; chart.appendChild(svg("rect", { x: 54, y: Math.min(top, bottom), width: 670, height: Math.max(Math.abs(bottom - top), 2), fill: color, opacity: .11 })); }
    const points = closes.map((value, i) => `${x(i)},${y(value)}`).join(" ");
    chart.appendChild(svg("polyline", { points, fill: "none", stroke: "#57d8cc", "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    chart.appendChild(svg("circle", { cx: x(closes.length - 1), cy: y(closes[closes.length - 1]), r: 4, fill: "#57d8cc" }));
    byId("price-chart-note").textContent = `${bars.length} bar${bars.length === 1 ? "" : "s"}`;
  }
  function renderDepthChart(market) {
    const chart = byId("depth-chart"); chart.replaceChildren(); const book = market?.orderbook;
    const levels = [...(book?.bid_levels || []), ...(book?.ask_levels || [])]
      .filter((level) => numeric(level.depth_quote) > 0 && numeric(level.price_mid) !== null)
      .sort((a, b) => numeric(b.price_mid) - numeric(a.price_mid)).slice(0, 16);
    if (!levels.length) { chart.appendChild(svg("text", { x: 260, y: 140, "text-anchor": "middle", class: "axis" }, "No ladder levels")); byId("depth-imbalance").textContent = ""; return; }
    const maxDepth = Math.max(...levels.map((level) => numeric(level.depth_quote))); const row = 238 / levels.length;
    chart.appendChild(svg("line", { x1: 260, x2: 260, y1: 18, y2: 262, class: "gridline" }));
    levels.forEach((level, index) => { const width = numeric(level.depth_quote) / maxDepth * 190; const yy = 18 + index * row; const bid = level.side === "bid"; chart.appendChild(svg("rect", { x: bid ? 252 - width : 268, y: yy, width, height: Math.max(row - 3, 2), rx: 2, fill: bid ? "#72a7ff" : "#f4bf67", opacity: .72 })); chart.appendChild(svg("text", { x: 260, y: yy + row - 5, "text-anchor": "middle", class: "axis" }, price(level.price_mid))); });
    byId("depth-imbalance").textContent = numeric(book.depth_imbalance) === null ? "" : `imbalance ${fmt(book.depth_imbalance, 3)}`;
  }
  function addCell(row, value, className) { const cell = document.createElement("td"); cell.textContent = String(value); if (className) cell.className = className; row.appendChild(cell); return cell; }
  function renderZones(market) {
    const body = byId("zone-body"); body.replaceChildren(); const zones = market?.observed_zones || []; byId("zone-count").textContent = `${zones.length} shown`;
    const readout = market?.zone_readout || {};
    byId("zone-readout-title").textContent = readout.title || "Zone map unavailable";
    byId("zone-readout-detail").textContent = readout.detail || "Generate or refresh a composite orderbook ladder before comparing public-depth zones.";
    byId("zone-readout-next").textContent = readout.next_check || "Refresh artifacts before comparing zone evidence.";
    byId("zone-readout-limit").textContent = readout.limitation || "Single generated snapshot; no future-reaction or hidden-liquidity inference.";
    if (!zones.length) { const row = document.createElement("tr"); const cell = addCell(row, "No qualifying ladder buckets are present in this artifact.", "empty"); cell.colSpan = 10; body.appendChild(row); return; }
    for (const zone of zones) { const row = document.createElement("tr"); addCell(row, zone.label); addCell(row, `${price(zone.price_low)} - ${price(zone.price_high)}`); addCell(row, relationLabel(zone.reference_relation)); addCell(row, `${fmt(zone.distance_to_reference_pct, 3)}%`); addCell(row, fmt(zone.depth_quote, 0)); addCell(row, zone.venue_count ?? "unavailable"); addCell(row, fmt(zone.hhi, 3)); addCell(row, fmt(zone.persistence_proxy, 3)); addCell(row, fmt(zone.vacuum_score, 3)); const cell = document.createElement("td"); const pill = document.createElement("span"); pill.className = `pill ${String(zone.evidence_grade || "limited").toLowerCase()}`; pill.textContent = zone.evidence_grade || "LIMITED"; pill.title = zone.evidence_definition || ""; cell.appendChild(pill); row.appendChild(cell); body.appendChild(row); }
  }
  function renderDislocation(timeframe) {
    const node = byId("dislocation"); node.replaceChildren(); const band = timeframe?.spot_perp_dislocation;
    if (!band) { node.className = "empty"; node.textContent = "Both spot and perpetual composite bars are required."; return; }
    node.className = ""; const title = document.createElement("strong"); title.textContent = `${price(band.price_low)} - ${price(band.price_high)}`; const detail = document.createElement("p"); detail.textContent = `Observed basis ${fmt(band.basis_pct, 4)}%. ${band.interpretation}`; node.append(title, detail);
  }
  function renderCurrent() { const { timeframe, market } = context(); const sourceNote = byId("source-note"); sourceNote.textContent = timeframe?.source_note || ""; sourceNote.hidden = !timeframe?.source_note; renderCards(market); renderFlow(market); renderPriceChart(market); renderDepthChart(market); renderZones(market); renderDislocation(timeframe); }
  async function inspect(path) { const output = byId("inspector"); output.textContent = "Loading..."; try { const url = staticArtifactBase ? `${staticArtifactBase}/${path.split("/").map(encodeURIComponent).join("/")}` : `/api/artifact?path=${encodeURIComponent(path)}`; output.textContent = JSON.stringify(await getJson(url), null, 2); } catch (error) { output.textContent = `Artifact read failed: ${error.message}`; } }
  function renderManifest() { const body = byId("artifact-body"); body.replaceChildren(); const items = state.index?.artifacts || []; byId("artifact-summary").textContent = `${items.length} JSON / ${bytes(items.reduce((sum, item) => sum + Number(item.size_bytes || 0), 0))}`; for (const item of items) { const row = document.createElement("tr"); addCell(row, item.path, "manifest-path"); addCell(row, bytes(item.size_bytes)); const cell = document.createElement("td"); const button = document.createElement("button"); button.type = "button"; button.textContent = "View JSON"; button.addEventListener("click", () => inspect(item.path)); cell.appendChild(button); row.appendChild(cell); body.appendChild(row); } }
  async function load() {
    try {
      const [health, snapshot, index] = await Promise.all([getJson("/api/health"), getJson("/api/dashboard-snapshot"), getJson("/api/artifacts")]);
      if (health.status !== "OK") throw new Error("dashboard health is not OK"); state.snapshot = snapshot; state.index = index;
      if (!snapshot.assets?.length) throw new Error("no composite artifact contexts found");
      const profile = snapshot.profile || {};
      const profileNote = byId("profile-note");
      const profileParts = [profile.primary_timeframe ? `Primary ${profile.primary_timeframe}` : null, profile.timeframes?.length ? `MTF ${profile.timeframes.join(",")}` : null, profile.refresh_seconds ? `Refresh profile ${profile.refresh_seconds}s` : null].filter(Boolean);
      profileNote.textContent = profileParts.join(" / ");
      profileNote.hidden = !profileParts.length;
      byId("service-state").textContent = profile.refresh_seconds ? `Observed artifact context loaded / ${profile.refresh_seconds}s profile` : "Observed artifact context loaded"; byId("service-state").className = "badge ok";
      syncFilters(); renderCurrent(); renderManifest();
      byId("methodology").textContent = `${snapshot.methodology.zone_selection} ${snapshot.methodology.snapshot_limit} ${snapshot.methodology.cross_venue_limit}`;
      byId("evidence-method").textContent = Object.entries(snapshot.methodology.evidence_grades).map(([grade, definition]) => `${grade}: ${definition}`).join("\n\n");
    } catch (error) { byId("service-state").textContent = "Dashboard unavailable"; byId("service-state").className = "badge error"; byId("methodology").textContent = error.message; }
  }
  assetSelect.addEventListener("change", () => { syncFilters("asset"); renderCurrent(); });
  timeframeSelect.addEventListener("change", () => { syncFilters("timeframe"); renderCurrent(); });
  marketSelect.addEventListener("change", renderCurrent);
  load();
</script>
</body>
</html>
"""
    return (
        html.replace("__EMBEDDED_SNAPSHOT__", _embedded_json(embedded_snapshot))
        .replace("__EMBEDDED_INDEX__", _embedded_json(embedded_index))
        .replace("__ARTIFACT_BASE_URL__", _embedded_json(artifact_base_url))
    )
