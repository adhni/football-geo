const DATA_URL = "./data/dashboard.json";
const COUNTRY_GEO_URL = "../data/countries.geojson";
const POPULATION_GEO_URLS = {
  1: "./data/population_hexes_r1.geojson",
  2: "./data/population_hexes_r2.geojson",
  3: "./data/population_hexes_r3.geojson",
};
const PLAYER_BATCH = 100;
const POPULATION_RATE_COLOURS = [[222, 241, 235], [166, 218, 204], [91, 178, 161], [27, 126, 122], [7, 66, 80]];

const state = {
  payload: null,
  conference: "all",
  division: "all",
  team: "all",
  country: "all",
  metric: "snaps",
  mapMode: "city",
  populationResolution: 3,
  placeQuery: "",
  search: "",
  playerLimit: PLAYER_BATCH,
  view: "map",
  map: null,
  baseLayer: null,
  populationBaseLayer: null,
  markerLayer: null,
  countryGeojson: null,
  countryLayer: null,
  populationGeojson: new Map(),
  populationPromises: new Map(),
  populationUnavailable: new Set(),
  populationLayer: null,
  placeMarkers: new Map(),
  countryLayers: new Map(),
  populationLayers: new Map(),
  populationRateStops: [],
  profileMap: null,
  profileOpener: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const number = new Intl.NumberFormat("en-US");
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function normalCountry(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalSearch(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function median(values) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function rowTeamSplits(row) {
  return row.teamSplits?.length ? row.teamSplits : [{
    team: row.team,
    teamCode: row.teamCode,
    conference: row.conference,
    division: row.division,
    games: row.games,
    snaps: row.snaps,
    offenseSnaps: row.offenseSnaps,
    defenseSnaps: row.defenseSnaps,
    specialTeamsSnaps: row.specialTeamsSnaps,
  }];
}

function matchingTeamSplits(row) {
  return rowTeamSplits(row).filter((split) =>
    (state.conference === "all" || split.conference === state.conference)
    && (state.division === "all" || split.division === state.division)
    && (state.team === "all" || split.team === state.team)
  );
}

function filteredRecords() {
  const teamFilterActive = state.conference !== "all" || state.division !== "all" || state.team !== "all";
  return state.payload.records.flatMap((row) => {
    if (state.country !== "all" && row.country !== state.country) return [];
    const splits = matchingTeamSplits(row);
    if (!splits.length) return [];
    if (!teamFilterActive) return [row];
    const primary = [...splits].sort((a, b) => b.snaps - a.snaps)[0];
    return [{
      ...row,
      team: primary.team,
      teamCode: primary.teamCode,
      teams: splits.map((split) => split.team),
      conference: primary.conference,
      division: primary.division,
      games: splits.reduce((sum, split) => sum + split.games, 0),
      snaps: splits.reduce((sum, split) => sum + split.snaps, 0),
      offenseSnaps: splits.reduce((sum, split) => sum + split.offenseSnaps, 0),
      defenseSnaps: splits.reduce((sum, split) => sum + split.defenseSnaps, 0),
      specialTeamsSnaps: splits.reduce((sum, split) => sum + split.specialTeamsSnaps, 0),
    }];
  });
}

function filteredTeamRecords() {
  return state.payload.records.flatMap((row) => {
    if (state.country !== "all" && row.country !== state.country) return [];
    return matchingTeamSplits(row).map((split) => ({ ...row, ...split, teams: [split.team] }));
  });
}

function metricLabel(metric = state.metric) {
  return { snaps: "snaps", players: "players", games: "games" }[metric];
}

function metricValue(item) { return item[state.metric] || 0; }
function isPopulationMode() { return state.mapMode === "population" || state.mapMode === "population-workload"; }
function populationMeasure() {
  return state.mapMode === "population-workload"
    ? { label: "snaps per 1M people", short: "snaps per 1M", workload: true }
    : { label: "players per 1M people", short: "players per 1M", workload: false };
}
function emptyState(message) { return `<div class="empty-state"><h3>No results here</h3><p>${escapeHtml(message)}</p><button type="button" class="empty-state-action" data-clear-filters>Clear filters</button></div>`; }

function prepareCountryMetadata() {
  const lookup = new Map();
  const fields = ["ADMIN", "NAME", "NAME_LONG", "SOVEREIGNT", "BRK_NAME", "FORMAL_EN"];
  (state.countryGeojson?.features || []).forEach((feature) => {
    const properties = feature.properties || {};
    const meta = { code: properties.ADM0_A3 || normalCountry(properties.ADMIN) };
    fields.forEach((field) => { if (properties[field]) lookup.set(normalCountry(properties[field]), meta); });
  });
  const aliases = { unitedstates: "unitedstatesofamerica" };
  state.payload.records.forEach((row) => {
    const key = normalCountry(row.country);
    row.countryCode = (lookup.get(key) || lookup.get(aliases[key]))?.code || key;
  });
}

function aggregatePlaces(records) {
  const places = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = `${row.lat}|${row.lon}|${row.place}`;
    if (!places.has(key)) places.set(key, { key, place: row.place, country: row.country, lat: row.lat, lon: row.lon, snaps: 0, games: 0, playerRows: new Map(), teams: new Set() });
    const place = places.get(key);
    place.snaps += row.snaps;
    place.games += row.games;
    place.playerRows.set(row.id, row);
    place.teams.add(row.team);
  });
  return [...places.values()].map((place) => ({ ...place, players: place.playerRows.size, playerList: [...place.playerRows.values()].sort((a, b) => b.snaps - a.snaps || a.name.localeCompare(b.name)), teams: [...place.teams].sort() }));
}

function aggregateCountries(records) {
  const countries = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = row.countryCode || normalCountry(row.country);
    if (!countries.has(key)) countries.set(key, { code: key, country: row.country, snaps: 0, games: 0, playerRows: new Map() });
    const country = countries.get(key);
    country.snaps += row.snaps;
    country.games += row.games;
    country.playerRows.set(row.id, row);
  });
  return [...countries.values()].map((country) => ({ ...country, players: country.playerRows.size }));
}

function aggregatePopulationCells(records) {
  const players = new Map(records.filter((row) => row.mapped).map((row) => [row.id, row]));
  const geojson = state.populationGeojson.get(state.populationResolution);
  return (geojson?.features || []).map((feature) => {
    const selected = (feature.properties.player_ids || []).filter((playerId) => players.has(playerId));
    if (!selected.length) return null;
    const playerRows = selected.map((playerId) => players.get(playerId));
    const places = new Map();
    const countries = new Map();
    playerRows.forEach((row) => {
      places.set(row.place, (places.get(row.place) || 0) + 1);
      countries.set(row.country, (countries.get(row.country) || 0) + 1);
    });
    const population = feature.properties.population;
    const workload = playerRows.reduce((sum, row) => sum + row.snaps, 0);
    const value = populationMeasure().workload ? workload : selected.length;
    return {
      feature,
      hexId: feature.properties.hex_id,
      players: selected.length,
      workload,
      population,
      rate: population ? value / population * 1_000_000 : null,
      stable: selected.length >= 2 && population >= 100_000,
      label: [...places.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || feature.properties.label,
      country: [...countries.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || feature.properties.country,
    };
  }).filter(Boolean);
}

async function loadPopulationGeometry(resolution = state.populationResolution) {
  if (state.populationGeojson.has(resolution)) return state.populationGeojson.get(resolution);
  if (state.populationUnavailable.has(resolution)) throw new Error(`Population geometry is unavailable at H3 resolution ${resolution}`);
  if (!state.populationPromises.has(resolution)) {
    const promise = fetch(POPULATION_GEO_URLS[resolution])
      .then((response) => {
        if (!response.ok) throw new Error(`Population geometry request failed (${response.status})`);
        return response.json();
      })
      .then((geojson) => { state.populationGeojson.set(resolution, geojson); return geojson; })
      .catch((error) => { state.populationUnavailable.add(resolution); state.populationPromises.delete(resolution); throw error; });
    state.populationPromises.set(resolution, promise);
  }
  return state.populationPromises.get(resolution);
}

function populationRateColour(rate) {
  if (rate === null) return "#18263a";
  const stops = state.populationRateStops;
  const clamped = Math.max(0, Math.min(rate, stops.at(-1).value));
  const upperIndex = stops.findIndex((stop) => clamped <= stop.value);
  if (upperIndex <= 0) return `rgb(${stops[0].colour.join(",")})`;
  const lower = stops[upperIndex - 1];
  const upper = stops[upperIndex];
  const progress = upper.value === lower.value ? 1 : (clamped - lower.value) / (upper.value - lower.value);
  return `rgb(${lower.colour.map((channel, index) => Math.round(channel + (upper.colour[index] - channel) * progress)).join(",")})`;
}

function updatePopulationRateScale() {
  const cells = aggregatePopulationCells(state.payload.records);
  const allRates = cells.map((cell) => cell.rate).filter((rate) => rate !== null).sort((a, b) => a - b);
  const reliableRates = cells.filter((cell) => cell.stable).map((cell) => cell.rate).sort((a, b) => a - b);
  const rates = reliableRates.length >= 5 ? reliableRates : allRates;
  const quantile = (fraction) => rates[Math.min(rates.length - 1, Math.round((rates.length - 1) * fraction))] || 0;
  const values = [0, quantile(.25), quantile(.5), quantile(.75), quantile(.95)];
  state.populationRateStops = values.map((value, index) => ({ value, colour: POPULATION_RATE_COLOURS[index] }));
  const formatRate = (value, index) => `${value < 10 ? value.toFixed(1) : Math.round(value)}${index === values.length - 1 ? "+" : ""}`;
  $$("#population-scale b").forEach((label, index) => { label.textContent = index ? formatRate(values[index], index) : "0"; });
}

function populationResolutionLabel() {
  return { 1: "Very broad", 2: "Large", 3: "Regional" }[state.populationResolution];
}

function aggregateTeams(records) {
  const teams = new Map();
  records.forEach((row) => {
    if (!teams.has(row.team)) teams.set(row.team, { team: row.team, code: row.teamCode, conference: row.conference, division: row.division, snaps: 0, games: 0, players: new Set(), mapped: new Set(), countries: new Set() });
    const team = teams.get(row.team);
    team.snaps += row.snaps;
    team.games += row.games;
    team.players.add(row.id);
    if (row.mapped) { team.mapped.add(row.id); team.countries.add(row.country); }
  });
  return [...teams.values()].map((team) => ({ ...team, players: team.players.size, mapped: team.mapped.size, countries: team.countries.size, coverage: team.players.size ? team.mapped.size / team.players.size * 100 : 0 }));
}

function aggregateConferences(records) {
  return state.payload.meta.conferences.map((conference) => {
    const rows = records.filter((row) => row.conference === conference);
    const playerRows = new Map(rows.map((row) => [row.id, row]));
    const players = [...playerRows.values()];
    const mapped = players.filter((row) => row.mapped);
    const countries = new Map();
    mapped.forEach((row) => countries.set(row.country, (countries.get(row.country) || 0) + 1));
    const outsideUs = mapped.filter((row) => row.country !== "United States").length;
    return {
      conference,
      players: players.length,
      teams: new Set(rows.map((row) => row.team)).size,
      divisions: new Set(rows.map((row) => row.division)).size,
      mapped: mapped.length,
      countries: countries.size,
      snaps: rows.reduce((sum, row) => sum + row.snaps, 0),
      medianAge: median(players.map((row) => row.age)),
      outsideUsPct: mapped.length ? outsideUs / mapped.length * 100 : 0,
      topCountries: [...countries.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5),
    };
  }).filter((conference) => conference.players);
}

function initMap() {
  if (!window.L) throw new Error("The map library did not load");
  state.map = L.map("talent-map", { preferCanvas: true, zoomControl: false, worldCopyJump: true, minZoom: 1 }).setView([32, -35], 2);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  state.baseLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd", attribution: "&copy; OpenStreetMap contributors &copy; CARTO" }).addTo(state.map);
  state.populationBaseLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd", attribution: "&copy; OpenStreetMap contributors &copy; CARTO" });
  state.markerLayer = L.markerClusterGroup ? L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 42, showCoverageOnHover: false }) : L.layerGroup();
  state.markerLayer.addTo(state.map);
}

function usePopulationBasemap(active) {
  const show = active ? state.populationBaseLayer : state.baseLayer;
  const hide = active ? state.baseLayer : state.populationBaseLayer;
  if (hide && state.map.hasLayer(hide)) state.map.removeLayer(hide);
  if (show && !state.map.hasLayer(show)) show.addTo(state.map);
}

function popupPlayers(rows, maximum = 8) {
  const visible = rows.slice(0, maximum).map((row) => `<button type="button" class="popup-player" data-player-id="${escapeHtml(row.id)}"><span>${escapeHtml(row.name)}</span><b>${number.format(row.snaps)} snaps</b></button>`).join("");
  const rest = rows.length - maximum;
  return `${visible}${rest > 0 ? `<small class="popup-rest">+ ${rest} more player${rest === 1 ? "" : "s"}</small>` : ""}`;
}

function renderCityMap(places) {
  usePopulationBasemap(false);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  if (!state.map.hasLayer(state.markerLayer)) state.markerLayer.addTo(state.map);
  state.markerLayer.clearLayers();
  state.placeMarkers.clear();
  const maximum = Math.max(...places.map(metricValue), 1);
  places.forEach((place) => {
    const radius = 5 + Math.sqrt(metricValue(place) / maximum) * 18;
    const marker = L.circleMarker([place.lat, place.lon], { radius, weight: 1, color: "#a6ddff", fillColor: "#55baff", fillOpacity: .68 });
    marker.bindTooltip(`${escapeHtml(place.place)}, ${escapeHtml(place.country)} · ${number.format(metricValue(place))} ${metricLabel()}`);
    marker.bindPopup(`<div class="map-popup"><strong>${escapeHtml(place.place)}</strong><small>${escapeHtml(place.country)} · ${place.players} player${place.players === 1 ? "" : "s"}</small>${popupPlayers(place.playerList)}</div>`, { maxWidth: 310 });
    state.markerLayer.addLayer(marker);
    state.placeMarkers.set(place.key, marker);
  });
}

function countryColour(value, maximum) {
  if (!value) return "#18263a";
  return `hsl(204 100% ${25 + Math.sqrt(value / Math.max(maximum, 1)) * 43}%)`;
}

function renderCountryMap(countries) {
  usePopulationBasemap(false);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  state.countryLayers.clear();
  if (!state.countryGeojson) return;
  const byCode = new Map(countries.map((country) => [country.code, country]));
  const maximum = Math.max(...countries.map(metricValue), 1);
  state.countryLayer = L.geoJSON(state.countryGeojson, {
    style(feature) {
      const country = byCode.get(feature.properties.ADM0_A3);
      return { color: "#385778", weight: .7, fillColor: countryColour(country ? metricValue(country) : 0, maximum), fillOpacity: country ? .82 : .3 };
    },
    onEachFeature(feature, layer) {
      const code = feature.properties.ADM0_A3;
      const country = byCode.get(code);
      state.countryLayers.set(code, layer);
      if (!country) return;
      layer.bindTooltip(`${escapeHtml(country.country)} · ${number.format(metricValue(country))} ${metricLabel()}`);
      layer.bindPopup(`<div class="map-popup"><strong>${escapeHtml(country.country)}</strong><small>${country.players} players · ${number.format(country.snaps)} snaps</small>${popupPlayers([...country.playerRows.values()].sort((a, b) => b.snaps - a.snaps))}</div>`, { maxWidth: 310 });
    },
  }).addTo(state.map);
}

function showPopulationLoading() {
  const measure = populationMeasure();
  usePopulationBasemap(true);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  $("#ranking-title").textContent = measure.label;
  $("#place-count").textContent = "Loading population data…";
  $("#place-ranking").innerHTML = `<li><div class="empty-state" role="status"><p>Preparing the population view…</p></div></li>`;
  $("#map-legend").classList.add("population");
  $("#map-explorer").classList.add("country-mode");
  $(".metric-control").hidden = true;
  $(".resolution-control").hidden = false;
  $("#population-scale").hidden = false;
  $("#legend-prefix").textContent = "Colour =";
  $("#legend-metric").textContent = measure.label;
}

function renderPopulationMap(records) {
  const measure = populationMeasure();
  usePopulationBasemap(true);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  const cells = aggregatePopulationCells(records);
  updatePopulationRateScale();
  const byId = new Map(cells.map((cell) => [cell.hexId, cell]));
  state.populationLayers.clear();
  state.populationLayer = L.geoJSON({ type: "FeatureCollection", features: cells.map((cell) => cell.feature) }, {
    style(feature) {
      const cell = byId.get(feature.properties.hex_id);
      return { color: cell.stable ? "#94c8b4" : "#62877d", weight: cell.stable ? .8 : .65, dashArray: cell.stable ? null : "3 3", fillColor: populationRateColour(cell.rate), fillOpacity: cell.stable ? .82 : .42 };
    },
    onEachFeature(feature, layer) {
      const cell = byId.get(feature.properties.hex_id);
      const rateLabel = cell.rate === null ? "Population estimate unavailable" : `${compact.format(cell.rate)} ${measure.short}`;
      const caution = cell.stable ? "" : " · small sample";
      layer.bindTooltip(`<strong>${escapeHtml(cell.label)} area</strong><br>${escapeHtml(cell.country)}<br>${rateLabel}<br>${cell.players} players${measure.workload ? ` · ${number.format(cell.workload)} snaps` : ""} · population ${cell.population ? compact.format(cell.population) : "unavailable"}${caution}`, { sticky: true });
      layer.bindPopup(`<div class="map-popup"><strong>${escapeHtml(cell.label)} area</strong><small>${rateLabel}</small><p>${cell.players} mapped players${measure.workload ? ` · ${number.format(cell.workload)} snaps` : ""} · ${cell.population ? `${number.format(cell.population)} residents` : "population unavailable"}</p>${cell.stable ? "" : '<small class="popup-rest">Interpret carefully: fewer than two players or fewer than 100,000 residents.</small>'}</div>`, { maxWidth: 320 });
      state.populationLayers.set(cell.hexId, layer);
    },
  }).addTo(state.map);
  $("#ranking-title").textContent = measure.label;
  $("#place-count").textContent = `${number.format(cells.length)} ${populationResolutionLabel().toLowerCase()} areas`;
  const ranked = cells.filter((cell) => cell.rate !== null).sort((a, b) => Number(b.stable) - Number(a.stable) || b.rate - a.rate).slice(0, 12);
  const maximum = Math.max(...ranked.map((cell) => cell.rate), 1);
  $("#place-ranking").innerHTML = ranked.length ? ranked.map((cell, index) => `<li class="place-row" style="--bar:${cell.rate / maximum * 100}%"><button class="place-jump" type="button" data-hex-id="${escapeHtml(cell.hexId)}"><span class="place-rank">${String(index + 1).padStart(2, "0")}</span><span class="place-name"><strong>${escapeHtml(cell.label)} area</strong><small>${escapeHtml(cell.country)} · ${cell.players} players${measure.workload ? ` · ${number.format(cell.workload)} snaps` : ""} / ${compact.format(cell.population)} people</small></span><span class="place-value">${compact.format(cell.rate)}</span></button></li>`).join("") : `<li>${emptyState("Try widening the current selection.")}</li>`;
  $("#map-legend").classList.add("population");
  $("#population-scale").hidden = false;
  $("#legend-prefix").textContent = "Colour =";
  $("#legend-metric").textContent = measure.label;
}

function renderRanking(items) {
  const sorted = [...items].sort((a, b) => metricValue(b) - metricValue(a) || (a.place || a.country).localeCompare(b.place || b.country));
  const visible = sorted.slice(0, 12);
  const maximum = Math.max(...visible.map(metricValue), 1);
  $("#ranking-title").textContent = `By ${metricLabel()}`;
  $("#place-count").textContent = `${number.format(items.length)} ${state.mapMode === "city" ? "places" : "countries"}`;
  $("#place-ranking").innerHTML = visible.length ? visible.map((item, index) => {
    const name = item.place || item.country;
    const detail = state.mapMode === "city" ? `${item.country} · ${item.players} players` : `${item.players} players`;
    const target = state.mapMode === "city" ? `data-place-key="${escapeHtml(item.key)}"` : `data-country-code="${escapeHtml(item.code)}"`;
    return `<li class="place-row" style="--bar:${metricValue(item) / maximum * 100}%"><button class="place-jump" type="button" ${target}><span class="place-rank">${String(index + 1).padStart(2, "0")}</span><span class="place-name"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(detail)}</small></span><span class="place-value">${compact.format(metricValue(item))}</span></button></li>`;
  }).join("") : `<li>${emptyState("Try widening the current selection.")}</li>`;
}

function updateMap() {
  const records = filteredRecords();
  const places = aggregatePlaces(records);
  const countries = aggregateCountries(records);
  if (isPopulationMode()) {
    if (!state.populationGeojson.has(state.populationResolution)) { showPopulationLoading(); return; }
    renderPopulationMap(records);
    $("#map-explorer").classList.add("country-mode");
    $(".metric-control").hidden = true;
    $(".resolution-control").hidden = false;
    return;
  }
  if (state.mapMode === "country" && state.countryGeojson) renderCountryMap(countries); else renderCityMap(places);
  renderRanking(state.mapMode === "city" ? places : countries);
  $("#map-legend").classList.remove("population");
  $("#population-scale").hidden = true;
  $("#legend-prefix").textContent = state.mapMode === "city" ? "Circle size =" : "Colour intensity =";
  $("#legend-metric").textContent = metricLabel();
  $("#map-explorer").classList.toggle("country-mode", state.mapMode === "country");
  $(".metric-control").hidden = false;
  $(".resolution-control").hidden = true;
}

function updateKpis() {
  const records = filteredRecords();
  const mapped = records.filter((row) => row.mapped).length;
  $("#kpi-players").textContent = number.format(records.length);
  $("#kpi-snaps").textContent = compact.format(records.reduce((sum, row) => sum + row.snaps, 0));
  $("#kpi-coverage").textContent = records.length ? `${(mapped / records.length * 100).toFixed(1)}%` : "—";
}

function updateConferenceComparison() {
  const conferences = aggregateConferences(filteredTeamRecords());
  $("#conference-comparison").innerHTML = conferences.map((conference, index) => `<article class="league-card" style="--order:${index}"><header><div><span>0${index + 1}</span><h3>${conference.conference}</h3></div><strong>${conference.outsideUsPct.toFixed(1)}%<small>born outside US</small></strong></header><div class="league-primary"><div><b>${conference.players}</b><span>players</span></div><div><b>${conference.teams}</b><span>teams</span></div><div><b>${conference.countries}</b><span>birth countries</span></div></div><div class="domestic-track"><i style="width:${conference.outsideUsPct}%"></i></div><div class="league-detail"><div><span class="card-label">Leading birth countries</span><ol>${conference.topCountries.map(([country, count]) => `<li><span>${escapeHtml(country)}</span><b>${count}</b></li>`).join("")}</ol></div></div><div class="league-footer">Median age ${conference.medianAge?.toFixed(1) ?? "—"} · ${number.format(conference.snaps)} total snaps · ${conference.mapped} of ${conference.players} players mapped</div></article>`).join("") || emptyState("No conference matches the current selection.");
}

function updateTeamChart() {
  const teams = aggregateTeams(filteredTeamRecords()).sort((a, b) => b.snaps - a.snaps || a.team.localeCompare(b.team));
  const maximum = Math.max(...teams.map((team) => team.snaps), 1);
  $("#team-chart").innerHTML = teams.length ? teams.map((team) => `<div class="team-row"><div class="team-name"><strong>${escapeHtml(team.team)}</strong><small>${escapeHtml(team.division)} · ${team.players} players</small></div><div class="team-track"><i style="width:${team.snaps / maximum * 100}%"></i></div><div class="team-value">${number.format(team.snaps)}<small>${team.coverage.toFixed(1)}% mapped</small></div></div>`).join("") : emptyState("No teams match the current selection.");
}

function updateAgeAndCountry() {
  const records = filteredRecords();
  const ages = records.map((row) => row.age).filter(Number.isFinite);
  const mapped = records.filter((row) => row.mapped);
  const outsideUs = mapped.filter((row) => row.country !== "United States").length;
  $("#age-overview").innerHTML = `<article><span>Median age</span><strong>${median(ages)?.toFixed(1) ?? "—"}</strong><small>at the end of the season</small></article><article><span>Under 25</span><strong>${number.format(ages.filter((age) => age < 25).length)}</strong><small>${ages.length ? (ages.filter((age) => age < 25).length / ages.length * 100).toFixed(1) : 0}% of players</small></article><article><span>Age 30+</span><strong>${number.format(ages.filter((age) => age >= 30).length)}</strong><small>${ages.length ? (ages.filter((age) => age >= 30).length / ages.length * 100).toFixed(1) : 0}% of players</small></article><article><span>Born outside US</span><strong>${mapped.length ? (outsideUs / mapped.length * 100).toFixed(1) : 0}%</strong><small>of mapped players</small></article>`;
  const countries = aggregateCountries(records);
  const byPlayers = [...countries].sort((a, b) => b.players - a.players || a.country.localeCompare(b.country)).slice(0, 10);
  const bySnaps = [...countries].sort((a, b) => b.snaps - a.snaps || a.country.localeCompare(b.country)).slice(0, 10);
  const panel = (title, items, value, label) => { const maximum = Math.max(...items.map(value), 1); return `<article class="country-panel"><span class="card-label">Birth-country comparison</span><h3>${title}</h3><ol class="country-list">${items.map((country) => `<li style="--bar:${value(country) / maximum * 100}%"><span>${escapeHtml(country.country)}</span><b>${label(country)}</b></li>`).join("")}</ol></article>`; };
  $("#country-comparison").innerHTML = countries.length ? `${panel("By players", byPlayers, (country) => country.players, (country) => number.format(country.players))}${panel("By snaps", bySnaps, (country) => country.snaps, (country) => compact.format(country.snaps))}` : emptyState("No mapped birth countries match the current selection.");
  $("#age-scope").textContent = `${number.format(records.length)} players in the current selection`;
}

function updatePlayerTable() {
  const query = normalSearch(state.search.trim());
  const players = filteredRecords().filter((row) => !query || [row.name, row.team, row.division, row.place, row.country, row.college].some((value) => normalSearch(value).includes(query))).sort((a, b) => b.snaps - a.snaps || a.name.localeCompare(b.name));
  const visible = players.slice(0, state.playerLimit);
  $("#player-table").innerHTML = visible.map((row) => `<tr class="player-row"><td data-label="Player"><button type="button" class="player-open-button" data-player-id="${escapeHtml(row.id)}" aria-label="Open profile for ${escapeHtml(row.name)}"><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.position || "Position unavailable")}</small></button></td><td data-label="Team">${escapeHtml(row.team)}</td><td data-label="Division">${escapeHtml(row.division)}</td><td data-label="Birthplace">${row.mapped ? `${escapeHtml(row.place)}<br><small>${escapeHtml(row.country)}</small>` : `<span style="color:var(--danger)">Awaiting QA</span>`}</td><td class="numeric" data-label="Games">${number.format(row.games)}</td><td class="numeric" data-label="Snaps">${number.format(row.snaps)}</td></tr>`).join("");
  const empty = $("#player-empty-state");
  empty.hidden = players.length > 0;
  empty.innerHTML = players.length ? "" : `<h3>No players found</h3><p>${escapeHtml(query ? "Try another search or clear the current filters." : "This selection has no players.")}</p><button type="button" class="empty-state-action" data-clear-filters>Clear filters</button>`;
  $("#player-table").closest("table").hidden = players.length === 0;
  $("#player-table-note").textContent = players.length ? `Showing ${number.format(visible.length)} of ${number.format(players.length)} players · sorted by snaps` : "No players to show";
  const remaining = Math.max(0, players.length - visible.length);
  $("#load-more-players").hidden = remaining === 0;
  $("#load-more-players").textContent = remaining ? `Show ${number.format(Math.min(PLAYER_BATCH, remaining))} more` : "Show more players";
}

function updateQuality() {
  const { summary, unresolved } = state.payload;
  $("#quality-player-coverage").textContent = `${summary.player_coverage_pct}%`;
  $("#quality-snap-coverage").textContent = `${summary.snap_coverage_pct}%`;
  $("#quality-player-bar").style.width = `${summary.player_coverage_pct}%`;
  $("#quality-snap-bar").style.width = `${summary.snap_coverage_pct}%`;
  $("#quality-mapped-players").textContent = `${number.format(summary.mapped_players)} mapped`;
  $("#quality-unresolved").textContent = `${number.format(summary.unresolved_players)} unresolved`;
  $("#quality-mapped-snaps").textContent = `${number.format(summary.mapped_snaps)} mapped snaps`;
  $("#quality-total-snaps").textContent = `${number.format(summary.snaps)} total`;
  $("#unresolved-count").textContent = `${number.format(summary.unresolved_players)} players`;
  $("#unresolved-list").innerHTML = unresolved.map((row) => `<div class="unresolved-row"><span>${escapeHtml(row.name)}</span><span>${escapeHtml(row.status)}</span></div>`).join("");
}

function syncOptions() {
  const splits = state.payload.records.flatMap(rowTeamSplits);
  const allowedDivisions = new Set(splits.filter((split) => state.conference === "all" || split.conference === state.conference).map((split) => split.division));
  [...$("#division-filter").options].forEach((option) => { if (option.value !== "all") option.hidden = !allowedDivisions.has(option.value); });
  if (state.division !== "all" && !allowedDivisions.has(state.division)) { state.division = "all"; $("#division-filter").value = "all"; }
  const allowedTeams = new Set(splits.filter((split) => (state.conference === "all" || split.conference === state.conference) && (state.division === "all" || split.division === state.division)).map((split) => split.team));
  [...$("#team-filter").options].forEach((option) => { if (option.value !== "all") option.hidden = !allowedTeams.has(option.value); });
  if (state.team !== "all" && !allowedTeams.has(state.team)) { state.team = "all"; $("#team-filter").value = "all"; }
}

function updateFilterUi() {
  const filters = [state.conference !== "all" && { key: "conference", label: state.conference }, state.division !== "all" && { key: "division", label: state.division }, state.team !== "all" && { key: "team", label: state.team }, state.country !== "all" && { key: "country", label: `Born in ${state.country}` }].filter(Boolean);
  const container = $("#active-filters");
  container.innerHTML = filters.map((filter) => `<button type="button" class="filter-chip" data-clear-filter="${filter.key}" aria-label="Remove ${escapeHtml(filter.label)} filter"><span>${escapeHtml(filter.label)}</span><span aria-hidden="true">×</span></button>`).join("");
  container.hidden = filters.length === 0;
  const more = Number(state.division !== "all") + Number(state.country !== "all");
  $("#more-filter-count").textContent = more ? String(more) : "";
  $("#reset-filters").disabled = filters.length === 0 && !state.search && !state.placeQuery && state.metric === "snaps" && state.mapMode === "city";
  $("#filter-summary").textContent = `${state.conference === "all" ? "Both conferences" : state.conference} · ${state.team === "all" ? "All teams" : state.team} · ${state.country === "all" ? "All birth countries" : `Born in ${state.country}`}`;
}

function updateSnapshotCopy() {
  const { meta, summary } = state.payload;
  const generated = new Date(meta.generated_at);
  const updated = Number.isNaN(generated.getTime()) ? "" : generated.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric", timeZone: "Australia/Melbourne" });
  if (updated) $(".status-pill").innerHTML = `<i aria-hidden="true"></i> ${meta.season} · Updated ${escapeHtml(updated)}`;
  $(".hero-statline").innerHTML = `<strong>${number.format(summary.players)} players</strong><span>${number.format(summary.teams)} teams</span><span>${number.format(summary.birthplaces)} birthplaces</span>`;
}

function populateFilters() {
  const add = (selector, values) => values.forEach((value) => $(selector).insertAdjacentHTML("beforeend", `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`));
  add("#conference-filter", state.payload.meta.conferences);
  add("#division-filter", state.payload.meta.divisions);
  add("#team-filter", state.payload.meta.teams);
  add("#country-filter", [...new Set(state.payload.records.filter((row) => row.mapped).map((row) => row.country))].sort());
  $("#place-options").innerHTML = aggregatePlaces(state.payload.records).sort((a, b) => a.place.localeCompare(b.place)).map((place) => `<option value="${escapeHtml(place.place)}, ${escapeHtml(place.country)}"></option>`).join("");
}

function render() {
  syncOptions(); updateFilterUi(); updateKpis(); updateMap(); updateConferenceComparison(); updateTeamChart(); updateAgeAndCountry(); updatePlayerTable();
}

function openPlayerProfile(playerId, opener = document.activeElement) {
  const player = state.payload.records.find((row) => row.id === playerId);
  if (!player) return;
  $("#profile-name").textContent = player.name;
  $("#profile-meta").textContent = `${player.position || "Position unavailable"} · ${player.college || "College unavailable"}`;
  $("#profile-team").textContent = rowTeamSplits(player).map((split) => `${split.team} (${number.format(split.snaps)} snaps)`).join(" · ");
  $("#profile-division").textContent = rowTeamSplits(player).length > 1 ? "Season totals shown · team contributions above" : `${player.conference} · ${player.division}`;
  $("#profile-games").textContent = number.format(player.games);
  $("#profile-snaps").textContent = number.format(player.snaps);
  $("#profile-offense").textContent = number.format(player.offenseSnaps);
  $("#profile-defense").textContent = number.format(player.defenseSnaps);
  $("#profile-special").textContent = number.format(player.specialTeamsSnaps);
  $("#profile-birthplace").textContent = player.mapped ? `${player.place}, ${player.country}` : "Birthplace awaiting QA";
  $("#profile-dob").textContent = player.dob || "Unavailable";
  $("#profile-age").textContent = Number.isFinite(player.age) ? `${player.age} years at season end` : "Age unavailable";
  state.profileOpener = opener instanceof HTMLElement ? opener : null;
  [$(".site-header"), $("main"), $("footer")].forEach((element) => { if (element) element.inert = true; });
  const modal = $("#player-modal"); modal.classList.add("open"); modal.setAttribute("aria-hidden", "false"); document.body.classList.add("modal-open");
  if (state.profileMap) state.profileMap.remove(); state.profileMap = null;
  $("#profile-map-empty").hidden = player.mapped; $("#player-mini-map").hidden = !player.mapped;
  if (player.mapped) setTimeout(() => { if (!modal.classList.contains("open")) return; state.profileMap = L.map("player-mini-map", { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false }).setView([player.lat, player.lon], 6); L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd" }).addTo(state.profileMap); L.circleMarker([player.lat, player.lon], { radius: 8, color: "#a6ddff", fillColor: "#55baff", fillOpacity: .8 }).addTo(state.profileMap); }, 80);
  $("#close-player-modal").focus();
}

function closePlayerProfile() {
  const modal = $("#player-modal"); modal.classList.remove("open"); modal.setAttribute("aria-hidden", "true"); document.body.classList.remove("modal-open");
  [$(".site-header"), $("main"), $("footer")].forEach((element) => { if (element) element.inert = false; });
  if (state.profileMap) state.profileMap.remove(); state.profileMap = null;
  const target = state.profileOpener?.isConnected ? state.profileOpener : $(`.view-tabs button[data-view="${state.view}"]`); state.profileOpener = null; target?.focus({ preventScroll: true });
}

function handleModalKeydown(event) {
  const modal = $("#player-modal"); if (!modal.classList.contains("open")) return;
  if (event.key === "Escape") { event.preventDefault(); closePlayerProfile(); return; }
  if (event.key !== "Tab") return;
  const focusable = [...modal.querySelectorAll('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')].filter((element) => !element.hidden);
  if (!focusable.length) return;
  const first = focusable[0], last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function setView(view, { focus = false, updateHash = true } = {}) {
  const target = $(`.view-tabs button[data-view="${view}"]`) ? view : "map"; state.view = target;
  $$(".view-tabs button").forEach((button) => { const active = button.dataset.view === target; button.classList.toggle("active", active); button.setAttribute("aria-selected", String(active)); button.tabIndex = active ? 0 : -1; if (active && focus) button.focus(); });
  $$(".view-panel").forEach((panel) => { const active = panel.id === `view-${target}`; panel.classList.toggle("active", active); panel.hidden = !active; });
  if (updateHash) history.replaceState(null, "", `#${target}`);
  if (target === "map") setTimeout(() => state.map?.invalidateSize(), 50);
}

function resetAll() {
  Object.assign(state, { conference: "all", division: "all", team: "all", country: "all", metric: "snaps", mapMode: "city", populationResolution: 3, search: "", placeQuery: "", playerLimit: PLAYER_BATCH });
  ["conference", "division", "team", "country"].forEach((key) => { $(`#${key}-filter`).value = "all"; });
  $("#player-search").value = ""; $("#place-search").value = ""; $("#clear-place-search").hidden = true;
  $$("#metric-control button").forEach((button) => { const active = button.dataset.metric === state.metric; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
  $$("#map-mode button").forEach((button) => { const active = button.dataset.mapMode === state.mapMode; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
  $$("#resolution-control button").forEach((button) => { const active = Number(button.dataset.resolution) === state.populationResolution; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
  render();
}

function bindEvents() {
  ["conference", "division", "team", "country"].forEach((key) => $(`#${key}-filter`).addEventListener("change", (event) => { state[key] = event.target.value; state.playerLimit = PLAYER_BATCH; render(); }));
  $("#reset-filters").addEventListener("click", resetAll);
  $("#metric-control").addEventListener("click", (event) => { const button = event.target.closest("button[data-metric]"); if (!button) return; state.metric = button.dataset.metric; $$("#metric-control button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); }); updateFilterUi(); updateMap(); });
  $("#map-mode").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-map-mode]"); if (!button || button.disabled) return;
    state.mapMode = button.dataset.mapMode;
    $$("#map-mode button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
    updateFilterUi(); updateMap();
    if (isPopulationMode() && !state.populationGeojson.has(state.populationResolution)) {
      loadPopulationGeometry().then(() => { if (isPopulationMode()) updateMap(); }).catch((error) => {
        console.warn(error); state.mapMode = "city"; $("#map-mode button[data-map-mode='city']").click();
        $("#error-toast").textContent = "The population view is unavailable. Birthplace and country views still work."; $("#error-toast").classList.add("show");
      });
    }
  });
  $("#resolution-control").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-resolution]"); if (!button) return;
    state.populationResolution = Number(button.dataset.resolution);
    $$("#resolution-control button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
    showPopulationLoading();
    loadPopulationGeometry().then(() => { if (isPopulationMode()) updateMap(); }).catch((error) => {
      console.warn(error); $("#error-toast").textContent = `${populationResolutionLabel()} population areas are unavailable. Try another size.`; $("#error-toast").classList.add("show");
    });
  });
  $("#place-search").addEventListener("change", (event) => { state.placeQuery = event.target.value.trim(); $("#clear-place-search").hidden = !state.placeQuery; const query = normalSearch(state.placeQuery); const place = aggregatePlaces(filteredRecords()).find((item) => normalSearch(`${item.place}, ${item.country}`) === query || normalSearch(item.place) === query); if (!place) return; if (state.mapMode !== "city") $("#map-mode button[data-map-mode='city']").click(); setTimeout(() => { state.map.setView([place.lat, place.lon], 6); const marker = state.placeMarkers.get(place.key); if (marker) state.markerLayer.zoomToShowLayer ? state.markerLayer.zoomToShowLayer(marker, () => marker.openPopup()) : marker.openPopup(); }, 40); updateFilterUi(); });
  $("#clear-place-search").addEventListener("click", () => { state.placeQuery = ""; $("#place-search").value = ""; $("#clear-place-search").hidden = true; updateFilterUi(); });
  $("#player-search").addEventListener("input", (event) => { state.search = event.target.value; state.playerLimit = PLAYER_BATCH; updatePlayerTable(); updateFilterUi(); });
  $("#load-more-players").addEventListener("click", () => { state.playerLimit += PLAYER_BATCH; updatePlayerTable(); });
  $(".view-tabs").addEventListener("click", (event) => { const button = event.target.closest("button[data-view]"); if (button) setView(button.dataset.view); });
  $(".view-tabs").addEventListener("keydown", (event) => { if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return; const tabs = $$(".view-tabs button[data-view]"); const current = tabs.indexOf(document.activeElement); if (current < 0) return; event.preventDefault(); const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length; setView(tabs[next].dataset.view, { focus: true }); });
  document.addEventListener("click", (event) => {
    const player = event.target.closest("[data-player-id]"); if (player) { openPlayerProfile(player.dataset.playerId, player); return; }
    if (event.target.closest("[data-clear-filters]")) { resetAll(); return; }
    const chip = event.target.closest("[data-clear-filter]"); if (chip) { const key = chip.dataset.clearFilter; state[key] = "all"; $(`#${key}-filter`).value = "all"; render(); return; }
    const placeButton = event.target.closest("[data-place-key]"); if (placeButton) { const marker = state.placeMarkers.get(placeButton.dataset.placeKey); if (marker) state.markerLayer.zoomToShowLayer ? state.markerLayer.zoomToShowLayer(marker, () => { state.map.setView(marker.getLatLng(), 6); marker.openPopup(); }) : marker.openPopup(); return; }
    const countryButton = event.target.closest("[data-country-code]"); if (countryButton) { const layer = state.countryLayers.get(countryButton.dataset.countryCode); if (layer) { state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 5 }); layer.openPopup(); } return; }
    const populationButton = event.target.closest("[data-hex-id]"); if (populationButton) { const layer = state.populationLayers.get(populationButton.dataset.hexId); if (layer) { state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 7 }); layer.openPopup(); } }
  });
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink); $("#methodology").scrollIntoView({ behavior: "smooth" }); }));
  $("#close-player-modal").addEventListener("click", closePlayerProfile); $("#player-modal").addEventListener("click", (event) => { if (event.target === $("#player-modal")) closePlayerProfile(); }); document.addEventListener("keydown", handleModalKeydown); window.addEventListener("hashchange", () => setView(location.hash.slice(1), { updateHash: false }));
}

async function boot() {
  try {
    const response = await fetch(DATA_URL); if (!response.ok) throw new Error(`NFL data request failed (${response.status})`); state.payload = await response.json();
    try { const countries = await fetch(COUNTRY_GEO_URL); if (!countries.ok) throw new Error(`Country geometry request failed (${countries.status})`); state.countryGeojson = await countries.json(); } catch (error) { console.warn(error); const button = $("#map-mode button[data-map-mode='country']"); button.disabled = true; button.title = "Country boundaries are unavailable"; $("#error-toast").textContent = "The birthplace map is ready; country boundaries could not load."; $("#error-toast").classList.add("show"); }
    prepareCountryMetadata(); populateFilters(); initMap(); bindEvents(); updateSnapshotCopy(); updateQuality(); setView(location.hash.slice(1) || "map", { updateHash: false }); render(); $("#loading-screen").classList.add("hidden");
  } catch (error) { console.error(error); $("#loading-screen").classList.add("hidden"); $("#error-toast").innerHTML = `NFL data could not load. <button type="button" onclick="location.reload()">Retry</button>`; $("#error-toast").classList.add("show"); }
}

boot();
