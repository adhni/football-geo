const DATA_URL = "./data/dashboard.json";

const state = {
  payload: null,
  league: "all",
  team: "all",
  country: "all",
  placeQuery: "",
  years: new Set(),
  metric: "starts",
  view: "map",
  search: "",
  map: null,
  markerLayer: null,
  placeMarkers: new Map(),
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
    state.years.has(row.year)
    && (state.league === "all" || row.league === state.league)
    && (state.country === "all" || row.country === state.country)
    && (ignoreTeam || state.team === "all" || row.team === state.team)
  );
}

function aggregatePlaces(records) {
  const places = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = `${row.lat}|${row.lon}|${row.place ?? "Unknown"}`;
    if (!places.has(key)) {
      places.set(key, { place: row.place || "Unnamed place", country: row.country || "Country unavailable", lat: row.lat, lon: row.lon, starts: 0, playerRows: new Map(), starters: new Set(), teams: new Set() });
    }
    const place = places.get(key);
    place.starts += row.starts;
    if (!place.playerRows.has(row.id)) place.playerRows.set(row.id, { name: row.name, starts: 0, teams: new Set() });
    const player = place.playerRows.get(row.id);
    player.starts += row.starts;
    player.teams.add(row.team);
    if (row.starts > 0) place.starters.add(row.id);
    place.teams.add(row.team);
  });
  return [...places.values()].map((place) => ({
    ...place,
    players: place.playerRows.size,
    playerList: [...place.playerRows.values()]
      .map((player) => ({ ...player, teams: [...player.teams].sort() }))
      .sort((a, b) => b.starts - a.starts || a.name.localeCompare(b.name)),
    starters: place.starters.size,
    teams: [...place.teams].sort(),
  }));
}

function aggregatePlayers(records) {
  const players = new Map();
  records.forEach((row) => {
    if (!players.has(row.id)) {
      players.set(row.id, { id: row.id, name: row.name, teams: new Set(), leagues: new Set(), years: new Set(), starts: 0, subs: 0, apps: 0, minutes: 0, goals: 0, assists: 0, dob: row.dob, birthYear: row.birthYear, place: row.place, country: row.country, mapped: row.mapped });
    }
    const player = players.get(row.id);
    player.teams.add(row.team);
    if (row.league) player.leagues.add(row.league);
    player.years.add(row.year);
    player.starts += row.starts;
    player.subs += row.subs;
    player.apps += row.apps || 0;
    player.minutes += row.minutes || 0;
    player.goals += row.goals || 0;
    player.assists += row.assists || 0;
    if (row.mapped) { player.place = row.place; player.country = row.country; player.mapped = true; }
  });
  return [...players.values()];
}

function aggregateTeams(records) {
  const teams = new Map();
  records.forEach((row) => {
    if (!teams.has(row.team)) teams.set(row.team, { team: row.team, starts: 0, players: new Set(), starters: new Set(), mapped: new Set(), years: new Set(), leagues: new Set() });
    const team = teams.get(row.team);
    team.starts += row.starts;
    team.players.add(row.id);
    if (row.starts > 0) team.starters.add(row.id);
    if (row.mapped) team.mapped.add(row.id);
    team.years.add(row.year);
    if (row.league) team.leagues.add(row.league);
  });
  return [...teams.values()].map((team) => ({
    team: team.team,
    starts: team.starts,
    players: team.players.size,
    starters: team.starters.size,
    mapped: team.mapped.size,
    years: team.years.size,
    leagues: [...team.leagues].sort(),
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
  state.markerLayer = L.markerClusterGroup
    ? L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 42, showCoverageOnHover: false })
    : L.layerGroup();
  state.markerLayer.addTo(state.map);
}

function updateMap(places) {
  if (!state.map) initMap();
  state.markerLayer.clearLayers();
  state.placeMarkers = new Map();
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
    const visiblePlayers = place.playerList.slice(0, 12);
    const playerRows = visiblePlayers.map((player) => `<li><span>${escapeHtml(player.name)}</span><small>${escapeHtml(player.teams.join(", "))} · ${formatNumber.format(player.starts)} starts</small></li>`).join("");
    const overflow = place.playerList.length > visiblePlayers.length ? `<p class="popup-overflow">+${place.playerList.length - visiblePlayers.length} more players</p>` : "";
    marker.bindPopup(`<div class="place-popup"><strong>${escapeHtml(place.place)}, ${escapeHtml(place.country)}</strong><p>${formatNumber.format(place.starts)} starts · ${place.players} players</p><ul>${playerRows}</ul>${overflow}</div>`, { maxWidth: 340, minWidth: 250 });
    marker.addTo(state.markerLayer);
    state.placeMarkers.set(`${place.lat}|${place.lon}`, marker);
    bounds.push([place.lat, place.lon]);
  });
  if ((state.team !== "all" || state.country !== "all" || state.placeQuery) && bounds.length > 1) state.map.fitBounds(bounds, { padding: [45, 45], maxZoom: 6 });
  else if (bounds.length === 1) state.map.setView(bounds[0], 7);
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
    <li class="place-row" style="--bar:${(selectedMetric(place) / max) * 100}%"><button class="place-jump" data-lat="${place.lat}" data-lon="${place.lon}" aria-label="Zoom to ${escapeHtml(place.place)}">
      <span class="place-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="place-name"><strong>${escapeHtml(place.place)}</strong><small>${escapeHtml(place.country)}</small></span>
      <span class="place-value">${formatNumber.format(selectedMetric(place))}</span>
    </button></li>`).join("") || `<li class="place-row"><span class="place-name"><strong>No mapped records</strong></span></li>`;
  $$(".place-jump").forEach((button) => button.addEventListener("click", () => {
    const lat = Number(button.dataset.lat);
    const lon = Number(button.dataset.lon);
    state.map.setView([lat, lon], 8);
    const marker = state.placeMarkers.get(`${lat}|${lon}`);
    if (marker && state.markerLayer.zoomToShowLayer) state.markerLayer.zoomToShowLayer(marker, () => marker.openPopup());
    else if (marker) setTimeout(() => marker.openPopup(), 250);
  }));
}

function updateTeamChart() {
  const teams = aggregateTeams(filteredRecords()).sort((a, b) => selectedMetric(b) - selectedMetric(a));
  const max = Math.max(...teams.map(selectedMetric), 1);
  $("#team-chart").innerHTML = teams.map((team) => `
    <div class="team-row">
      <div class="team-name"><strong>${escapeHtml(team.team)}</strong><small>${escapeHtml(team.leagues.join(", "))}</small></div>
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
    <tr><td><strong>${escapeHtml(player.name)}</strong><br><small>${escapeHtml(player.dob || player.birthYear || "DOB unavailable")}</small></td>
    <td>${escapeHtml([...player.teams].sort().join(", "))}</td>
    <td>${escapeHtml([...player.leagues].sort().join(", "))}</td>
    <td>${player.mapped ? `${escapeHtml(player.place)}<br><small>${escapeHtml(player.country || "")}</small>` : `<span style="color:var(--danger)">QA pending</span>`}</td>
    <td class="numeric">${formatNumber.format(player.apps)}</td><td class="numeric">${formatNumber.format(player.starts)}</td></tr>`).join("");
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
  $("#quality-total-starts").textContent = `${formatNumber.format(summary.starts)} total`;
  $("#unresolved-count").textContent = `${formatNumber.format(summary.unresolved_players)} players`;
  $("#unresolved-list").innerHTML = unresolved.slice(0, 120).map((row) => `<div class="unresolved-row"><span>${escapeHtml(row.name)}</span><span>${escapeHtml(row.status)}</span></div>`).join("");
}

function updateFilterSummary() {
  const league = state.league === "all" ? "All five leagues" : state.league;
  const team = state.team === "all" ? "All clubs" : state.team;
  const country = state.country === "all" ? "All birth countries" : `Born in ${state.country}`;
  $("#filter-summary").textContent = `${league} · ${team} · ${country}`;
}

function filteredPlaces() {
  const query = state.placeQuery.trim().toLowerCase();
  return aggregatePlaces(filteredRecords()).filter((place) =>
    !query || `${place.place} ${place.country}`.toLowerCase().includes(query)
  );
}

function renderMapExplorer() {
  const places = filteredPlaces();
  updateMap(places);
  updateRanking(places);
}

function render() {
  const records = filteredRecords();
  const allPlaces = aggregatePlaces(records);
  const query = state.placeQuery.trim().toLowerCase();
  const places = allPlaces.filter((place) => !query || `${place.place} ${place.country}`.toLowerCase().includes(query));
  updateKpis(records, allPlaces);
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
  $("#league-filter").addEventListener("change", (event) => {
    state.league = event.target.value;
    state.team = "all";
    populateTeamOptions();
    render();
  });
  $("#team-filter").addEventListener("change", (event) => { state.team = event.target.value; render(); });
  $("#country-filter").addEventListener("change", (event) => { state.country = event.target.value; render(); });
  $("#place-search").addEventListener("input", (event) => { state.placeQuery = event.target.value; renderMapExplorer(); });
  $("#clear-place-search").addEventListener("click", () => {
    state.placeQuery = "";
    $("#place-search").value = "";
    renderMapExplorer();
  });
  $("#metric-control").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-metric]");
    if (!button) return;
    state.metric = button.dataset.metric;
    $$("#metric-control button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
  $("#reset-filters").addEventListener("click", () => {
    state.league = "all";
    state.team = "all";
    state.country = "all";
    state.placeQuery = "";
    state.years = new Set(state.payload.meta.years);
    state.metric = "starts";
    $("#league-filter").value = "all";
    populateTeamOptions();
    $("#team-filter").value = "all";
    $("#country-filter").value = "all";
    $("#place-search").value = "";
    $$("#metric-control button").forEach((button) => button.classList.toggle("active", button.dataset.metric === "starts"));
    render();
  });
  $$(".view-tabs button").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink); }));
  $("#player-search").addEventListener("input", (event) => { state.search = event.target.value; updatePlayerTable(); });
}

function populateTeamOptions() {
  const teams = [...new Set(state.payload.records
    .filter((row) => state.league === "all" || row.league === state.league)
    .map((row) => row.team))].sort();
  $("#team-filter").innerHTML = `<option value="all">All ${teams.length} clubs</option>${teams.map((team) => `<option value="${escapeHtml(team)}">${escapeHtml(team)}</option>`).join("")}`;
}

function populateControls() {
  const { meta } = state.payload;
  state.years = new Set(meta.years);
  $("#league-filter").insertAdjacentHTML("beforeend", meta.leagues.map((league) => `<option value="${escapeHtml(league)}">${escapeHtml(league)}</option>`).join(""));
  const mapped = state.payload.records.filter((row) => row.mapped);
  const countries = [...new Set(mapped.map((row) => row.country).filter(Boolean))].sort();
  const places = [...new Set(mapped.map((row) => row.place).filter(Boolean))].sort();
  $("#country-filter").insertAdjacentHTML("beforeend", countries.map((country) => `<option value="${escapeHtml(country)}">${escapeHtml(country)}</option>`).join(""));
  $("#place-options").innerHTML = places.map((place) => `<option value="${escapeHtml(place)}"></option>`).join("");
  populateTeamOptions();
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
