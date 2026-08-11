const DATA_URL = "./data/dashboard.json";

const state = {
  payload: null,
  team: "all",
  years: new Set(),
  metric: "starts",
  view: "map",
  search: "",
  map: null,
  markerLayer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const formatNumber = new Intl.NumberFormat("en-US");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function metricLabel(metric = state.metric) {
  return { starts: "starts", starters: "unique starters", players: "players" }[metric];
}

function filteredRecords({ ignoreTeam = false } = {}) {
  return state.payload.records.filter((row) =>
    state.years.has(row.year) && (ignoreTeam || state.team === "all" || row.team === state.team)
  );
}

function aggregatePlaces(records) {
  const places = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = `${row.lat}|${row.lon}|${row.place ?? "Unknown"}`;
    if (!places.has(key)) {
      places.set(key, { place: row.place || "Unnamed place", country: row.country || "Country unavailable", lat: row.lat, lon: row.lon, starts: 0, players: new Set(), starters: new Set(), teams: new Set() });
    }
    const place = places.get(key);
    place.starts += row.starts;
    place.players.add(row.id);
    if (row.starts > 0) place.starters.add(row.id);
    place.teams.add(row.team);
  });
  return [...places.values()].map((place) => ({
    ...place,
    players: place.players.size,
    starters: place.starters.size,
    teams: [...place.teams].sort(),
  }));
}

function aggregatePlayers(records) {
  const players = new Map();
  records.forEach((row) => {
    if (!players.has(row.id)) {
      players.set(row.id, { id: row.id, name: row.name, teams: new Set(), years: new Set(), starts: 0, subs: 0, dob: row.dob, place: row.place, country: row.country, mapped: row.mapped });
    }
    const player = players.get(row.id);
    player.teams.add(row.team);
    player.years.add(row.year);
    player.starts += row.starts;
    player.subs += row.subs;
    if (row.mapped) { player.place = row.place; player.country = row.country; player.mapped = true; }
  });
  return [...players.values()];
}

function aggregateTeams(records) {
  const teams = new Map();
  records.forEach((row) => {
    if (!teams.has(row.team)) teams.set(row.team, { team: row.team, starts: 0, players: new Set(), starters: new Set(), mapped: new Set(), years: new Set() });
    const team = teams.get(row.team);
    team.starts += row.starts;
    team.players.add(row.id);
    if (row.starts > 0) team.starters.add(row.id);
    if (row.mapped) team.mapped.add(row.id);
    team.years.add(row.year);
  });
  return [...teams.values()].map((team) => ({
    team: team.team,
    starts: team.starts,
    players: team.players.size,
    starters: team.starters.size,
    mapped: team.mapped.size,
    years: team.years.size,
    coverage: team.players.size ? (team.mapped.size / team.players.size) * 100 : 0,
  }));
}

function selectedMetric(item) { return item[state.metric]; }

function updateKpis(records, places) {
  const players = aggregatePlayers(records);
  const teams = new Set(records.map((row) => row.team));
  const mapped = players.filter((player) => player.mapped).length;
  $("#kpi-teams").textContent = formatNumber.format(teams.size);
  $("#kpi-players").textContent = formatNumber.format(players.length);
  $("#kpi-starts").textContent = formatNumber.format(records.reduce((sum, row) => sum + row.starts, 0));
  $("#kpi-places").textContent = formatNumber.format(places.length);
  $("#kpi-coverage").textContent = players.length ? `${((mapped / players.length) * 100).toFixed(1)}%` : "—";
}

function initMap() {
  state.map = L.map("talent-map", { preferCanvas: true, zoomControl: false, worldCopyJump: true, minZoom: 1 }).setView([20, 4], 2);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    subdomains: "abcd",
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
  }).addTo(state.map);
  state.markerLayer = L.layerGroup().addTo(state.map);
}

function updateMap(places) {
  if (!state.map) initMap();
  state.markerLayer.clearLayers();
  const maxValue = Math.max(...places.map(selectedMetric), 1);
  const bounds = [];
  places.forEach((place) => {
    const value = selectedMetric(place);
    const scale = Math.log1p(value) / Math.log1p(maxValue);
    const marker = L.circleMarker([place.lat, place.lon], {
      radius: 3.5 + scale * 14,
      color: "rgba(217,255,87,.8)",
      weight: 1,
      fillColor: scale > .58 ? "#d9ff57" : "#5be3b1",
      fillOpacity: .26 + scale * .58,
    });
    marker.bindTooltip(`<strong>${escapeHtml(place.place)}</strong><br><span>${escapeHtml(place.country)}</span><br>${formatNumber.format(value)} ${escapeHtml(metricLabel())}`, { direction: "top", offset: [0, -6] });
    marker.bindPopup(`<strong>${escapeHtml(place.place)}, ${escapeHtml(place.country)}</strong><br>${formatNumber.format(place.starts)} starts · ${place.starters} starters · ${place.players} players<br><small>${escapeHtml(place.teams.join(", "))}</small>`);
    marker.addTo(state.markerLayer);
    bounds.push([place.lat, place.lon]);
  });
  if (state.team !== "all" && bounds.length > 1) state.map.fitBounds(bounds, { padding: [45, 45], maxZoom: 5 });
  else state.map.setView([20, 4], 2);
  $("#legend-metric").textContent = metricLabel();
  setTimeout(() => state.map.invalidateSize(), 80);
}

function updateRanking(places) {
  const sorted = [...places].sort((a, b) => selectedMetric(b) - selectedMetric(a));
  const top = sorted.slice(0, 10);
  const max = top.length ? selectedMetric(top[0]) : 1;
  $("#ranking-title").textContent = `By ${metricLabel()}`;
  $("#place-count").textContent = `${formatNumber.format(places.length)} places`;
  $("#place-ranking").innerHTML = top.map((place, index) => `
    <li class="place-row" style="--bar:${(selectedMetric(place) / max) * 100}%">
      <span class="place-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="place-name"><strong>${escapeHtml(place.place)}</strong><small>${escapeHtml(place.country)}</small></span>
      <span class="place-value">${formatNumber.format(selectedMetric(place))}</span>
    </li>`).join("") || `<li class="place-row"><span class="place-name"><strong>No mapped records</strong></span></li>`;
}

function updateTeamChart() {
  const teams = aggregateTeams(filteredRecords()).sort((a, b) => selectedMetric(b) - selectedMetric(a));
  const max = Math.max(...teams.map(selectedMetric), 1);
  $("#team-chart").innerHTML = teams.map((team) => `
    <div class="team-row">
      <div class="team-name"><strong>${escapeHtml(team.team)}</strong><small>${team.years} tournament${team.years === 1 ? "" : "s"}</small></div>
      <div class="team-track"><i style="width:${(selectedMetric(team) / max) * 100}%"></i></div>
      <div class="team-value">${formatNumber.format(selectedMetric(team))}<small>${team.coverage.toFixed(1)}% POB</small></div>
    </div>`).join("") || `<p>No teams match this selection.</p>`;
}

function updatePlayerTable() {
  const query = state.search.trim().toLowerCase();
  const players = aggregatePlayers(filteredRecords())
    .filter((player) => !query || [player.name, player.place, player.country, ...player.teams].some((value) => String(value ?? "").toLowerCase().includes(query)))
    .sort((a, b) => b.starts - a.starts || a.name.localeCompare(b.name));
  const visible = players.slice(0, 150);
  $("#player-table").innerHTML = visible.map((player) => `
    <tr><td><strong>${escapeHtml(player.name)}</strong><br><small>${escapeHtml(player.dob || "DOB unavailable")}</small></td>
    <td>${escapeHtml([...player.teams].sort().join(", "))}</td>
    <td>${player.mapped ? `${escapeHtml(player.place)}<br><small>${escapeHtml(player.country || "")}</small>` : `<span style="color:var(--danger)">QA pending</span>`}</td>
    <td>${[...player.years].sort().join(", ")}</td><td class="numeric">${formatNumber.format(player.starts)}</td><td class="numeric">${formatNumber.format(player.subs)}</td></tr>`).join("");
  $("#player-table-note").textContent = `Showing ${formatNumber.format(visible.length)} of ${formatNumber.format(players.length)} players in this selection`;
}

function updateQuality() {
  const { summary, unresolved } = state.payload;
  $("#quality-player-coverage").textContent = `${summary.player_coverage_pct}%`;
  $("#quality-start-coverage").textContent = `${summary.start_coverage_pct}%`;
  $("#quality-player-bar").style.width = `${summary.player_coverage_pct}%`;
  $("#quality-start-bar").style.width = `${summary.start_coverage_pct}%`;
  $("#quality-mapped-players").textContent = `${formatNumber.format(summary.mapped_players)} mapped`;
  $("#quality-unresolved").textContent = `${formatNumber.format(summary.unresolved_players)} unresolved`;
  $("#quality-mapped-starts").textContent = `${formatNumber.format(summary.mapped_starts)} mapped starts`;
  $("#unresolved-list").innerHTML = unresolved.map((row) => `<div class="unresolved-row"><span>${escapeHtml(row.name)}</span><span>${escapeHtml(row.status)}</span></div>`).join("");
}

function updateFilterSummary() {
  const team = state.team === "all" ? "All teams" : state.team;
  const years = [...state.years].sort();
  const yearText = years.length === state.payload.meta.years.length ? "All tournaments" : years.join(", ");
  $("#filter-summary").textContent = `${team} · ${yearText}`;
}

function render() {
  const records = filteredRecords();
  const places = aggregatePlaces(records);
  updateKpis(records, places);
  updateFilterSummary();
  updateMap(places);
  updateRanking(places);
  updateTeamChart();
  updatePlayerTable();
  updateQuality();
}

function setView(view) {
  state.view = view;
  $$(".view-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $$(".view-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `view-${view}`));
  if (view === "map" && state.map) setTimeout(() => state.map.invalidateSize(), 100);
  document.querySelector(".view-tabs").scrollIntoView({ behavior: "smooth", block: "start" });
}

function bindControls() {
  $("#team-filter").addEventListener("change", (event) => { state.team = event.target.value; render(); });
  $("#year-chips").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-year]");
    if (!button) return;
    const year = Number(button.dataset.year);
    if (state.years.has(year) && state.years.size > 1) state.years.delete(year); else state.years.add(year);
    button.classList.toggle("active", state.years.has(year));
    render();
  });
  $("#metric-control").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-metric]");
    if (!button) return;
    state.metric = button.dataset.metric;
    $$("#metric-control button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
  $("#reset-filters").addEventListener("click", () => {
    state.team = "all";
    state.years = new Set(state.payload.meta.years);
    state.metric = "starts";
    $("#team-filter").value = "all";
    $$("#year-chips button").forEach((button) => button.classList.add("active"));
    $$("#metric-control button").forEach((button) => button.classList.toggle("active", button.dataset.metric === "starts"));
    render();
  });
  $$(".view-tabs button").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink); }));
  $("#player-search").addEventListener("input", (event) => { state.search = event.target.value; updatePlayerTable(); });
}

function populateControls() {
  const { meta } = state.payload;
  state.years = new Set(meta.years);
  $("#team-filter").insertAdjacentHTML("beforeend", meta.teams.map((team) => `<option value="${escapeHtml(team)}">${escapeHtml(team)}</option>`).join(""));
  $("#year-chips").innerHTML = meta.years.map((year) => `<button class="active" data-year="${year}" aria-pressed="true">${year}</button>`).join("");
}

function showError(message) {
  const toast = $("#error-toast");
  toast.textContent = message;
  toast.classList.add("show");
  $("#loading-screen").classList.add("hidden");
}

async function boot() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`Dataset request failed (${response.status})`);
    state.payload = await response.json();
    populateControls();
    bindControls();
    render();
    $("#loading-screen").classList.add("hidden");
  } catch (error) {
    console.error(error);
    showError("The dashboard data could not be loaded. Please refresh or try again shortly.");
  }
}

boot();
