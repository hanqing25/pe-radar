const state = {
  view: "radar",
  query: "",
  region: "All",
  sizeOnly: false,
  selectedId: null,
  targets: [],
  signals: [],
  sectors: [],
  sources: [],
  sync: {},
  fundSources: [],
  sponsorUniverse: [],
  fundSync: {},
  creditSources: [],
  credit: { verified_instruments: [], directory_matches: [] },
  creditSync: {},
  generatedAt: null,
};

const viewTitles = { radar: "Radar", pipeline: "Pipeline", universe: "Fund universe", credit: "Credit", sectors: "Sectors", sources: "Sources" };
const statusMeta = {
  active_watch: ["Watching", "blue"], sale_signal: ["Sale signal", "red"],
  late_exit_signal: ["Late process", "amber"], hsg_precedent: ["HSG precedent", "violet"],
  completed_transaction: ["Completed", "gray"], below_size_watch: ["Below size", "blue"],
};
const actionabilityMeta = {
  live_process: ["Live process", "red"],
  proactive_watch: ["Priority watch", "green"],
  precedent: ["Thesis anchor", "violet"],
};
const signalMeta = {
  sale_process: ["Sale process", "red"], continuation_vehicle: ["Continuation", "amber"],
  valuation_marker: ["Valuation", "violet"], exit_completed: ["Exit", "gray"],
  ipo_prep: ["IPO prep", "blue"], add_on: ["Add-on", "green"],
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const icon = (name, size = 16) => `<i data-lucide="${name}" style="width:${size}px;height:${size}px"></i>`;

function sizeLabel(value) {
  if (value == null) return "Size open";
  return value >= 1000 ? `$${(value / 1000).toFixed(value % 1000 ? 1 : 0)}bn` : `$${value}m`;
}

function dateLabel(value) {
  if (!value) return "Open";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function timeAgo(value) {
  if (!value) return "Not available";
  const seconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
}

async function loadData() {
  const payload = await fetch("./data/radar.json", { cache: "no-store" }).then((response) => response.json());
  Object.assign(state, {
    targets: payload.targets || [],
    signals: payload.signals || [],
    sectors: payload.sectors || [],
    sources: payload.sources || [],
    sync: payload.sync || {},
    fundSources: payload.fund_sources || [],
    sponsorUniverse: payload.sponsor_universe || [],
    fundSync: payload.fund_sync || {},
    creditSources: payload.credit_sources || [],
    credit: payload.credit || { verified_instruments: [], directory_matches: [] },
    creditSync: payload.credit_sync || {},
    generatedAt: payload.generated_at,
  });
  state.selectedId = state.targets.find((target) => !target.exclude_from_shortlist)?.company_name || state.targets[0]?.company_name || null;
  render();
}

function targetScore(target) { return target.scores?.total ?? 0; }
function filteredTargets() {
  const query = state.query.trim().toLowerCase();
  return state.targets.filter((target) => {
    const text = [target.company_name, target.current_owner, target.country, target.sector, target.sub_sector].join(" ").toLowerCase();
    const regionMatch = state.region === "All" || target.region === state.region;
    const sizeMatch = !state.sizeOnly || (target.estimated_ev_usd_m >= 800 && target.estimated_ev_usd_m <= 1200);
    return (!query || text.includes(query)) && regionMatch && sizeMatch;
  });
}

function renderMetrics() {
  const active = state.targets.filter((target) => !target.exclude_from_shortlist).length;
  const actionable = state.signals.filter((signal) => ["sale_process", "continuation_vehicle"].includes(signal.signal_type)).length;
  const priorityTargets = state.targets.filter((target) => target.user_priority && !target.exclude_from_shortlist).length;
  const liveProcesses = state.targets.filter((target) => target.actionability === "live_process" && !target.exclude_from_shortlist).length;
  const verifiedBonds = state.credit.verified_instruments?.length || 0;
  $("#metrics").innerHTML = [
    ["ACTIVE TARGETS", active, "ranked universe"],
    ["PRIORITY TARGETS", priorityTargets, "explicit HSG interest"],
    ["LIVE PROCESSES", liveProcesses, "assess now"],
    ["OFFICIAL UNIVERSE", state.sponsorUniverse.length, `${state.fundSources.length} sponsor sites`],
    ["VERIFIED BONDS", verifiedBonds, `${state.creditSources.length} credit venues`],
    ["LAST REFRESH", timeAgo(state.generatedAt), `${state.signals.length} signals retained`],
  ].map(([label, value, note]) => `<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join("");
  $("#signal-badge").textContent = actionable;
  $("#credit-badge").textContent = verifiedBonds;
}

function renderRadar() {
  const targets = filteredTargets();
  if (!targets.some((target) => target.company_name === state.selectedId)) state.selectedId = targets[0]?.company_name || null;
  const selected = targets.find((target) => target.company_name === state.selectedId);
  const rows = targets.map((target) => {
    const [label, tone] = actionabilityMeta[target.actionability] || statusMeta[target.status] || ["Watching", "blue"];
    const score = targetScore(target);
    const initials = target.company_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("");
    return `<button class="target-row ${target.company_name === state.selectedId ? "selected" : ""}" data-target="${escapeHtml(target.company_name)}">
      <span class="company-cell"><b>${escapeHtml(initials)}</b><span><strong>${escapeHtml(target.company_name)}</strong><small>${escapeHtml(target.country)} · ${escapeHtml(target.sub_sector)}</small></span></span>
      <span class="owner-cell"><strong>${escapeHtml(target.current_owner)}</strong><small>${target.hold_years == null ? "Entry date open" : `${Number(target.hold_years).toFixed(1)} yrs held`}</small></span>
      <span class="size-cell"><strong>${sizeLabel(target.estimated_ev_usd_m)}</strong><small>${target.estimated_ev_usd_m == null ? "Needs work" : target.estimated_ev_usd_m >= 800 && target.estimated_ev_usd_m <= 1200 ? "In band" : "Outside band"}</small></span>
      <span class="score-cell"><strong>${score}</strong><span><i style="width:${score}%"></i></span></span>
      <span><em class="pill ${tone}">${label}</em></span>${icon("chevron-right", 15)}
    </button>`;
  }).join("");

  $("#content").innerHTML = `<div class="radar-layout">
    <section class="target-panel">
      <div class="panel-toolbar"><div><h2>Target universe</h2><small>${targets.length} companies</small></div><div class="filters">
        <label>${icon("globe-2", 15)}<select id="region-filter"><option value="All">All regions</option><option value="Europe" ${state.region === "Europe" ? "selected" : ""}>Europe</option><option value="Asia" ${state.region === "Asia" ? "selected" : ""}>Asia</option></select></label>
        <button id="size-filter" class="${state.sizeOnly ? "active" : ""}">${icon("filter", 15)}$800m-$1.2bn</button>
      </div></div>
      <div class="table-head"><span>COMPANY</span><span>OWNER / HOLD</span><span>SIZE</span><span>SCORE</span><span>STATUS</span><span></span></div>
      <div class="target-list">${rows || `<div class="empty">${icon("search", 20)}<span>No matching targets</span></div>`}</div>
    </section>
    ${renderDetail(selected)}
  </div>`;

  $("#region-filter")?.addEventListener("change", (event) => { state.region = event.target.value; renderRadar(); refreshIcons(); });
  $("#size-filter")?.addEventListener("click", () => { state.sizeOnly = !state.sizeOnly; renderRadar(); refreshIcons(); });
  document.querySelectorAll("[data-target]").forEach((button) => button.addEventListener("click", () => { state.selectedId = button.dataset.target; renderRadar(); refreshIcons(); }));
}

function renderDetail(target) {
  if (!target) return `<aside class="detail-panel"><div class="empty">${icon("target", 22)}<span>Select a target</span></div></aside>`;
  const scores = target.scores || {};
  const related = state.signals.filter((signal) => signal.company_name === target.company_name).slice(0, 4);
  const evidence = [...(target.evidence || [])].slice(0, 3);
  const scoreRows = [["Availability", scores.availability], ["Business quality", scores.business_quality], ["HSG fit", scores.hsg_fit], ["PE suitability", scores.pe_suitability]];
  return `<aside class="detail-panel">
    <div class="detail-heading"><span class="detail-avatar">${escapeHtml(target.company_name.slice(0, 2).toUpperCase())}</span><span><small>${escapeHtml((target.tracking_tier || "Selected target").toUpperCase())}</small><h2>${escapeHtml(target.company_name)}</h2><p>${escapeHtml(target.sub_sector)}</p></span><strong>${targetScore(target)}<small>/100</small></strong></div>
    <div class="detail-facts"><div><span>Owner</span><strong>${escapeHtml(target.current_owner)}</strong></div><div><span>Hold</span><strong>${target.hold_years == null ? "Open" : `${Number(target.hold_years).toFixed(1)} yrs`}</strong></div><div><span>Est. EV</span><strong>${sizeLabel(target.estimated_ev_usd_m)}</strong></div></div>
    <section class="detail-section"><h3>Current read</h3><p>${escapeHtml(target.recommendation)}</p></section>
    ${target.next_action ? `<section class="detail-section action-section"><h3>Next action</h3><p>${escapeHtml(target.next_action)}</p></section>` : ""}
    <section class="detail-section"><h3>Score anatomy</h3>${scoreRows.map(([name, value]) => `<div class="score-row"><span>${name}</span><div><i style="width:${value || 0}%"></i></div><strong>${value || 0}</strong></div>`).join("")}</section>
    <section class="detail-section"><h3>Investment markers</h3><div class="tag-row">${(target.tags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></section>
    ${(target.watch_triggers || []).length ? `<section class="detail-section"><h3>Watch triggers</h3><div class="trigger-list">${target.watch_triggers.map((trigger) => `<span>${icon("radar", 12)}${escapeHtml(trigger)}</span>`).join("")}</div></section>` : ""}
    <section class="detail-section"><div class="section-title"><h3>Evidence</h3><span>${evidence.length + related.length} items</span></div>
      ${evidence.map((item) => `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${icon("circle-dot", 14)}<span><strong>${escapeHtml(item.note)}</strong><small>${escapeHtml(item.source)} · ${dateLabel(item.date)}</small></span>${icon("external-link", 13)}</a>`).join("")}
      ${related.map((item) => `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">${icon("activity", 14)}<span><strong>${escapeHtml(item.excerpt)}</strong><small>${escapeHtml(item.source_name)} · ${dateLabel(item.created_at)}</small></span>${icon("external-link", 13)}</a>`).join("")}
    </section>
  </aside>`;
}

function stageFor(target) {
  if (target.exclude_from_shortlist) return "precedent";
  if (target.actionability === "live_process") return "deep_dive";
  if (target.actionability === "proactive_watch") return "outreach";
  if (target.status === "sale_signal") return "deep_dive";
  if (target.status === "active_watch") return "outreach";
  return "watching";
}

function renderPipeline() {
  const stages = [["watching", "Watching", "blue"], ["deep_dive", "Deep dive", "green"], ["outreach", "Outreach", "amber"], ["precedent", "Precedents", "violet"]];
  $("#content").innerHTML = `<section class="page-view"><div class="view-heading"><span><small>WORKFLOW</small><h2>Investment pipeline</h2></span><em>${state.targets.length} tracked decisions</em></div><div class="pipeline-grid">${stages.map(([id, label, tone]) => {
    const items = state.targets.filter((target) => stageFor(target) === id);
    return `<section class="pipeline-column"><header><i class="dot ${tone}"></i><strong>${label}</strong><em>${items.length}</em></header><div>${items.map((target) => `<button data-pipeline-target="${escapeHtml(target.company_name)}"><span><strong>${escapeHtml(target.company_name)}</strong><small>${escapeHtml(target.current_owner)} · ${escapeHtml(target.sector)}</small></span><b>${targetScore(target)}</b>${icon("chevron-right", 14)}</button>`).join("")}</div></section>`;
  }).join("")}</div></section>`;
  document.querySelectorAll("[data-pipeline-target]").forEach((button) => button.addEventListener("click", () => { state.selectedId = button.dataset.pipelineTarget; setView("radar"); }));
}

function renderSectors() {
  $("#content").innerHTML = `<section class="page-view"><div class="view-heading"><span><small>CATEGORY MEMORY</small><h2>PE ownership map</h2></span><em>Control-investment suitability</em></div><div class="sector-list">${state.sectors.map((sector, index) => `<article><b>0${index + 1}</b><span><strong>${escapeHtml(sector.sector)}</strong><small>${escapeHtml((sector.top_assets || []).join(" · "))}</small></span><div><small>Composite</small><strong>${Math.round(sector.avg_total)}</strong></div><div><small>PE suitability</small><strong>${Math.round(sector.avg_pe_suitability)}</strong></div><div><small>HSG fit</small><strong>${Math.round(sector.avg_hsg_fit)}</strong></div><i><span style="width:${sector.avg_total}%"></span></i></article>`).join("")}</div></section>`;
}

function renderUniverse() {
  const query = state.query.trim().toLowerCase();
  const rows = state.sponsorUniverse.filter((item) => !query || [item.company_name, item.sponsor, item.region].join(" ").toLowerCase().includes(query));
  const sponsorCount = new Set(rows.map((item) => item.sponsor)).size;
  $("#content").innerHTML = `<section class="page-view"><div class="view-heading"><span><small>OFFICIAL PORTFOLIOS</small><h2>Sponsor-owned company universe</h2></span><em>${rows.length} candidates · ${sponsorCount} sponsors</em></div>
    <div class="universe-wrap"><section class="universe-table"><header><span>COMPANY</span><span>SPONSOR</span><span>REGION</span><span>SCOPE</span><span>VERIFICATION</span></header>
      ${rows.map((item) => `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer"><span><b>${escapeHtml(item.company_name)}</b><small>${escapeHtml(item.source_name || "Official portfolio")}</small></span><strong>${escapeHtml(item.sponsor)}</strong><span>${escapeHtml(item.region || "Global")}</span><span>${escapeHtml((item.portfolio_scope || "portfolio").replaceAll("_", " "))}</span><em class="source-state"><i></i>Website candidate${icon("external-link", 13)}</em></a>`).join("") || `<div class="empty">${icon("building-2", 22)}<span>No official portfolio candidates matched</span></div>`}
    </section></div></section>`;
}

function renderCredit() {
  const instruments = state.credit.verified_instruments || [];
  const matches = state.credit.directory_matches || [];
  $("#content").innerHTML = `<section class="page-view"><div class="view-heading"><span><small>CREDIT OVERLAY</small><h2>PE-backed traded debt</h2></span><em>${instruments.length} verified instruments · ${matches.length} pending matches</em></div>
    <div class="credit-layout"><section class="credit-table"><header><span>COMPANY / ISSUER</span><span>IDENTIFIER</span><span>COUPON / MATURITY</span><span>PRICE / YTW</span><span>SOURCE</span></header>
      ${instruments.map((item) => { const price = item.last_price ?? item.reference_price; return `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer"><span><b>${escapeHtml(item.company_name)}</b><small>${escapeHtml(item.legal_issuer_name || item.issuer_name || "Issuer open")}</small></span><strong>${escapeHtml(item.isin || item.cusip || "Open")}</strong><span>${item.coupon_pct == null ? "Open" : `${item.coupon_pct}%`}<small>${dateLabel(item.maturity_date)} · ${escapeHtml(item.coupon_type || "")}</small></span><span>${price == null ? "Open" : Number(price).toFixed(2)}<small>${item.ytw_pct == null ? escapeHtml(item.price_type || "YTW open") : `${item.ytw_pct}% YTW`}</small></span><em>${escapeHtml(item.source_name || "Verified record")}${icon("external-link", 13)}</em></a>`; }).join("") || `<div class="credit-empty">${icon("shield-check", 24)}<strong>No verified instruments yet</strong><span>Issuer and ISIN/CUSIP evidence is required before a bond enters this table.</span></div>`}
    </section><aside class="venue-panel"><h3>Market coverage</h3>${state.creditSources.map((source) => {
      const failed = (state.creditSync.errors || []).some((error) => error.name === source.name || error.url === source.url);
      return `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer"><b>${icon(failed ? "triangle-alert" : "landmark", 15)}</b><span><strong>${escapeHtml(source.name)}</strong><small>${escapeHtml(source.identifier || "Identifier open")} · ${escapeHtml((source.price_capability || source.source_type || "directory").replaceAll("_", " "))}</small></span><em class="${failed ? "failed" : ""}">${failed ? "Blocked" : "Monitored"}</em></a>`;
    }).join("")}</aside></div></section>`;
}

function renderSources() {
  $("#content").innerHTML = `<section class="page-view"><div class="view-heading"><span><small>INGESTION</small><h2>Source operations</h2></span><em>Last build ${timeAgo(state.generatedAt)}</em></div><div class="source-layout"><section class="source-table"><header><span>SOURCE</span><span>REGION</span><span>TIER</span><span>STATE</span></header>${state.sources.map((source) => {
    const failed = (state.sync.errors || []).some((error) => error.source_name === source.name);
    return `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer"><span><b>${icon("globe-2", 16)}</b><strong>${escapeHtml(source.name)}</strong></span><span>${escapeHtml(source.region || "Global")}</span><span>${escapeHtml(source.tier || "Research")}</span><span class="source-state ${failed ? "failed" : ""}"><i></i>${failed ? "Blocked" : "Active"}${icon("external-link", 13)}</span></a>`;
  }).join("")}</section><aside class="run-card"><h3>Latest run</h3><div><b>${icon(state.sync.errors?.length ? "triangle-alert" : "check", 17)}</b><span><strong>${state.sync.new_signal_count || 0} new signals</strong><small>${state.sync.fetched?.length || 0} sources reached</small></span></div><dl><dt>Retained signals</dt><dd>${state.sync.total_signal_count || state.signals.length}</dd><dt>Source errors</dt><dd>${state.sync.errors?.length || 0}</dd><dt>Generated</dt><dd>${dateLabel(state.sync.generated_at)}</dd></dl></aside></div></section>`;
}

function render() {
  renderMetrics();
  if (state.view === "radar") renderRadar();
  if (state.view === "pipeline") renderPipeline();
  if (state.view === "universe") renderUniverse();
  if (state.view === "credit") renderCredit();
  if (state.view === "sectors") renderSectors();
  if (state.view === "sources") renderSources();
  refreshIcons();
}

function setView(view) {
  state.view = view;
  $("#view-title").textContent = viewTitles[view];
  document.querySelectorAll("nav [data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $("#sidebar").classList.remove("open");
  $("#scrim").classList.remove("show");
  render();
}

document.querySelectorAll("nav [data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
$("#search").addEventListener("input", (event) => {
  state.query = event.target.value;
  if (state.view === "universe") renderUniverse();
  else if (state.view !== "radar") setView("radar");
  else renderRadar();
  refreshIcons();
});
$("#refresh").addEventListener("click", () => window.location.reload());
$("#open-nav").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#scrim").classList.add("show"); });
$("#close-nav").addEventListener("click", () => { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); });
$("#scrim").addEventListener("click", () => { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); });

refreshIcons();
loadData().catch((error) => {
  $("#content").innerHTML = `<div class="fatal">${icon("circle-alert", 22)}<strong>Unable to load radar data</strong><span>${escapeHtml(error.message)}</span></div>`;
  refreshIcons();
});
