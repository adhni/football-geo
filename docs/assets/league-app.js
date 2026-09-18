const DATA_URL = "./data/dashboard.json";
const COUNTRY_GEO_URL = "../data/countries.geojson";
const POPULATION_GEO_URLS = {
  1: "./data/population_hexes_r1.geojson",
  2: "./data/population_hexes_r2.geojson",
  3: "./data/population_hexes_r3.geojson",
};
const DEFAULT_VIEW = "map";
const PLAYER_BATCH = 100;
const POPULATION_RATE_COLOURS = [[222, 241, 235], [166, 218, 204], [91, 178, 161], [27, 126, 122], [7, 66, 80]];
const EDITION = {
  name: "NBA",
  homeCountry: "United States",
  outsideHomeLabel: "Born outside US",
  allConferenceLabel: "Both conferences",
  conferenceLabel: "Conference",
  markerStroke: "#ffd2a8",
  markerFill: "#ff9b54",
  originMarkerFill: "#56a7c7",
  countryHue: 25,
  countrySaturation: 100,
  countryEmpty: "#30251d",
  workloadLabel: "minutes",
  workloadShort: "min",
  workloadField: "minutes",
  defaultMetric: "minutes",
  showWorkloadColumn: true,
  showConferenceColumn: true,
  singleGroupLabel: "League-wide",
  profileOriginField: "nationality",
  profileOriginFallback: "Nationality unavailable",
  teamSplitStats: ["goals", "assists", "points"],
  profileStats: ["games", "minutes", "points", "rebounds", "assists"],
  profileStatDecimals: {},
  locationLabel: "Birthplace",
  locationPlural: "birthplaces",
  countryGroupLabel: "birth countries",
  mixedLocationTypes: false,
  originLabel: "Football origin",
  qualityPlayerCoverageField: "player_coverage_pct",
  qualityMappedPlayersField: "mapped_players",
  qualityWorkloadCoverageField: "minute_coverage_pct",
  qualityMappedWorkloadField: "mapped_minutes",
  qualityTotalWorkloadField: "minutes",
  groupLabelPlural: "teams",
  participantLabelPlural: "players",
  tableGroupLabel: "Team",
  tableStatField: "games",
  tableStatLabel: "Games",
  positionValuesField: null,
  participantDetailField: "position",
  popupDetailField: null,
  showTeamFilter: true,
  comparisonHighlight: "outsideHome",
  showPopulationReferenceCells: false,
  ...window.TALENT_GEO_EDITION,
};
const TEAM_STYLES = window.TALENT_TEAM_COLOURS?.[EDITION.name] || null;

const state = {
  payload: null,
  conference: "all",
  team: "all",
  teams: [],
  teamMeta: [],
  country: "all",
  position: "all",
  metric: EDITION.defaultMetric,
  mapMode: "city",
  populationResolution: 3,
  placeQuery: "",
  search: "",
  playerLimit: PLAYER_BATCH,
  view: DEFAULT_VIEW,
  map: null,
  baseLayer: null,
  populationBaseLayer: null,
  markerLayer: null,
  teamMarkerLayer: null,
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
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalCountry(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalSearch(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function recordValues(row, field, fallbackField = null) {
  const value = field ? row[field] : fallbackField ? row[fallbackField] : null;
  const fallback = fallbackField && field !== fallbackField ? row[fallbackField] : null;
  const selected = value === null || value === undefined || value === "" ? fallback : value;
  return (Array.isArray(selected) ? selected : [selected]).filter(Boolean).map(String);
}

function positionValues(row) {
  return recordValues(row, EDITION.positionValuesField, "position");
}

function participantDetail(row) {
  const values = recordValues(row, EDITION.participantDetailField, "position");
  return values.length ? values.join(" · ") : "Position unavailable";
}

function matchesTeam(team) {
  return TEAM_STYLES ? state.teams.length === 0 || state.teams.includes(team) : state.team === "all" || state.team === team;
}

function hasTeamSelection() {
  return TEAM_STYLES ? state.teams.length > 0 : state.team !== "all";
}

function teamStyle(team) {
  const [colour = EDITION.markerFill, text = "#ffffff", code = team.slice(0, 3).toUpperCase()] = TEAM_STYLES?.[team] || [];
  return { colour, text, code };
}

function median(values) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function projectTeamSplits(row, splits) {
  const primary = [...splits].sort((a, b) => b.minutes - a.minutes || a.team.localeCompare(b.team))[0];
  const total = (key) => splits.reduce((sum, split) => sum + (split[key] || 0), 0);
  const projectedStats = Object.fromEntries(EDITION.teamSplitStats.map((key) => [key, total(key)]));
  const projectedMinimums = Object.fromEntries((EDITION.teamSplitMinStats || []).map((key) => [
    key,
    Math.min(...splits.map((split) => split[key]).filter(Number.isFinite)),
  ]));
  return {
    ...row,
    team: primary.team,
    teamCode: primary.teamCode,
    teams: [...new Set(splits.map((split) => split.team))],
    teamSplits: splits,
    conference: primary.conference,
    division: primary.division,
    games: total("games"),
    minutes: total("minutes"),
    ...projectedStats,
    ...projectedMinimums,
    rebounds: splits.some((split) => Number.isFinite(split.goals)) ? total("goals") : row.rebounds,
  };
}

function filteredRecords(conference = state.conference) {
  return state.payload.records.flatMap((row) => {
    if (state.country !== "all" && row.country !== state.country) return [];
    if (state.position !== "all" && !positionValues(row).includes(state.position)) return [];
    if (!row.teamSplits?.length) {
      return (conference === "all" || row.conference === conference)
        && matchesTeam(row.team) ? [row] : [];
    }
    const splits = row.teamSplits.filter((split) =>
      (conference === "all" || split.conference === conference)
      && matchesTeam(split.team)
    );
    if (!splits.length) return [];
    return conference === "all" && !hasTeamSelection() ? [row] : [projectTeamSplits(row, splits)];
  });
}

function filteredTeamRecords() {
  return state.payload.records.flatMap((row) => {
    if (state.country !== "all" && row.country !== state.country) return [];
    if (!row.teamSplits?.length) {
      return (state.conference === "all" || row.conference === state.conference)
        && matchesTeam(row.team) ? [row] : [];
    }
    return row.teamSplits
      .filter((split) => (state.conference === "all" || split.conference === state.conference) && matchesTeam(split.team))
      .map((split) => projectTeamSplits(row, [split]));
  });
}

function metricLabel(metric = state.metric) {
  return { minutes: EDITION.workloadLabel, players: EDITION.participantLabelPlural, games: "games" }[metric];
}

function metricValue(item) {
  return item[state.metric] || 0;
}

function isPopulationMode() {
  return state.mapMode === "population" || state.mapMode === "population-workload";
}

function populationMeasure() {
  return state.mapMode === "population-workload"
    ? { label: `${EDITION.workloadLabel} per 1M people`, short: `${EDITION.workloadShort} per 1M`, workload: true }
    : { label: `${EDITION.participantLabelPlural} per 1M people`, short: `${EDITION.participantLabelPlural} per 1M`, workload: false };
}

function emptyState(message) {
  return `<div class="empty-state"><h3>No results here</h3><p>${escapeHtml(message)}</p><button type="button" class="empty-state-action" data-clear-filters>Clear filters</button></div>`;
}

function prepareCountryMetadata() {
  const lookup = new Map();
  const fields = ["ADMIN", "NAME", "NAME_LONG", "SOVEREIGNT", "BRK_NAME", "FORMAL_EN"];
  (state.countryGeojson?.features || []).forEach((feature) => {
    const properties = feature.properties || {};
    const meta = { code: properties.ADM0_A3 || normalCountry(properties.ADMIN), name: properties.ADMIN || properties.NAME };
    fields.forEach((field) => {
      if (properties[field]) lookup.set(normalCountry(properties[field]), meta);
    });
  });
  const aliases = {
    unitedstates: "unitedstatesofamerica",
    peoplesrepublicofchina: "china",
    thebahamas: "bahamas",
    czechrepublic: "czechia",
  };
  state.payload.records.forEach((row) => {
    const key = normalCountry(row.country);
    const meta = lookup.get(key) || lookup.get(aliases[key]);
    row.countryCode = meta?.code || key;
  });
}

function aggregatePlaces(records) {
  const places = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = `${row.lat}|${row.lon}|${row.place}`;
    if (!places.has(key)) {
      places.set(key, { key, place: row.place || `Unnamed ${EDITION.locationLabel.toLowerCase()}`, country: row.country || "Country unavailable", lat: row.lat, lon: row.lon, minutes: 0, games: 0, playerRows: new Map(), teams: new Set(), hasOrigin: false, hasBirthplace: false });
    }
    const place = places.get(key);
    place.minutes += row.minutes || 0;
    place.games += row.games || 0;
    place.teams.add(row.team);
    place.playerRows.set(row.id, row);
    place.hasOrigin ||= row.locationType && row.locationType !== "birthplace";
    place.hasBirthplace ||= !row.locationType || row.locationType === "birthplace";
  });
  return [...places.values()].map((place) => ({
    ...place,
    players: place.playerRows.size,
    playerList: [...place.playerRows.values()].sort((a, b) => b.minutes - a.minutes || a.name.localeCompare(b.name)),
    teams: [...place.teams].sort(),
  }));
}

function aggregateCountries(records) {
  const countries = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = row.countryCode || normalCountry(row.country);
    if (!countries.has(key)) countries.set(key, { code: key, country: row.country, minutes: 0, games: 0, playerRows: new Map() });
    const country = countries.get(key);
    country.minutes += row.minutes || 0;
    country.games += row.games || 0;
    country.playerRows.set(row.id, row);
  });
  return [...countries.values()].map((country) => ({ ...country, players: country.playerRows.size }));
}

function aggregatePopulationCells(records) {
  const players = new Map(records.filter((row) => row.mapped && (!row.locationType || row.locationType === "birthplace")).map((row) => [row.id, row]));
  const geojson = state.populationGeojson.get(state.populationResolution);
  return (geojson?.features || []).map((feature) => {
    const selected = (feature.properties.player_ids || []).filter((playerId) => players.has(playerId));
    if (!selected.length && !EDITION.showPopulationReferenceCells) return null;
    const playerRows = selected.map((playerId) => players.get(playerId));
    const places = new Map();
    const countries = new Map();
    playerRows.forEach((row) => {
      const placeName = row.place || feature.properties.label || "Mapped area";
      const countryName = row.country || feature.properties.country || "Country unavailable";
      places.set(placeName, (places.get(placeName) || 0) + 1);
      countries.set(countryName, (countries.get(countryName) || 0) + 1);
    });
    const population = feature.properties.population;
    const workload = playerRows.reduce((sum, row) => sum + row.minutes, 0);
    const value = populationMeasure().workload ? workload : selected.length;
    return {
      feature,
      hexId: feature.properties.hex_id,
      players: selected.length,
      workload,
      population,
      rate: population ? value / population * 1_000_000 : null,
      reference: !selected.length,
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
  if (rate === null) return "#30251d";
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
  const allRates = cells.filter((cell) => !cell.reference).map((cell) => cell.rate).filter((rate) => rate !== null).sort((a, b) => a - b);
  const reliableRates = cells.filter((cell) => cell.stable).map((cell) => cell.rate).sort((a, b) => a - b);
  const rates = reliableRates.length >= 5 ? reliableRates : allRates;
  const quantile = (fraction) => rates[Math.min(rates.length - 1, Math.round((rates.length - 1) * fraction))] || 0;
  const values = [0, quantile(.25), quantile(.5), quantile(.75), quantile(.95)];
  state.populationRateStops = values.map((value, index) => ({ value, colour: POPULATION_RATE_COLOURS[index] }));
  const formatRate = (value, index) => `${value < 10 ? value.toFixed(1) : compact.format(value)}${index === values.length - 1 ? "+" : ""}`;
  $$("#population-scale b").forEach((label, index) => { label.textContent = index ? formatRate(values[index], index) : "0"; });
}

function populationResolutionLabel() {
  return { 1: "Very broad", 2: "Large", 3: "Regional" }[state.populationResolution];
}

function aggregateTeams(records) {
  const teams = new Map();
  records.forEach((row) => {
    if (!teams.has(row.team)) teams.set(row.team, { team: row.team, code: row.teamCode, conference: row.conference, minutes: 0, games: 0, players: new Set(), mapped: new Set(), countries: new Set() });
    const team = teams.get(row.team);
    team.minutes += row.minutes || 0;
    team.games += row.games || 0;
    team.players.add(row.id);
    if (row.mapped) {
      team.mapped.add(row.id);
      team.countries.add(row.country);
    }
  });
  return [...teams.values()].map((team) => ({
    ...team,
    players: team.players.size,
    mapped: team.mapped.size,
    countries: team.countries.size,
    coverage: team.players.size ? team.mapped.size / team.players.size * 100 : 0,
  }));
}

function aggregateConferences() {
  const conferences = state.conference === "all" ? state.payload.meta.conferences : [state.conference];
  return conferences.map((conference) => {
    const rows = filteredRecords(conference);
    const mapped = rows.filter((row) => row.mapped);
    const countries = new Map();
    mapped.forEach((row) => countries.set(row.country, (countries.get(row.country) || 0) + 1));
    const outsideHome = mapped.filter((row) => row.country !== EDITION.homeCountry).length;
    return {
      conference,
      players: rows.length,
      teams: new Set(rows.flatMap((row) => row.teams || [row.team])).size,
      mapped: mapped.length,
      countries: countries.size,
      minutes: rows.reduce((sum, row) => sum + row.minutes, 0),
      medianAge: median(rows.map((row) => row.age)),
      outsideHomePct: mapped.length ? outsideHome / mapped.length * 100 : 0,
      topCountries: [...countries.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5),
    };
  }).filter((conference) => conference.players);
}

function initMap() {
  if (!window.L) throw new Error("The map library did not load");
  state.map = L.map("talent-map", { preferCanvas: true, zoomControl: false, worldCopyJump: true, minZoom: 1 }).setView([25, -15], 2);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  state.baseLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    subdomains: "abcd",
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
  }).addTo(state.map);
  state.populationBaseLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd", attribution: "&copy; OpenStreetMap contributors &copy; CARTO" });
  state.markerLayer = L.markerClusterGroup
    ? L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 42, showCoverageOnHover: false })
    : L.layerGroup();
  state.markerLayer.addTo(state.map);
  state.teamMarkerLayer = L.layerGroup();
  state.map.on("zoomend", () => {
    if (TEAM_STYLES && state.mapMode === "city" && state.teams.length) renderTeamCityMap(filteredTeamRecords());
  });
}

function usePopulationBasemap(active) {
  const show = active ? state.populationBaseLayer : state.baseLayer;
  const hide = active ? state.baseLayer : state.populationBaseLayer;
  if (hide && state.map.hasLayer(hide)) state.map.removeLayer(hide);
  if (show && !state.map.hasLayer(show)) show.addTo(state.map);
}

function popupPlayers(rows, maximum = 8) {
  const visible = rows.slice(0, maximum);
  const items = visible.map((row) => { const detail = recordValues(row, EDITION.popupDetailField).join(" · "); return `<button type="button" class="popup-player" data-player-id="${escapeHtml(row.id)}"><span>${escapeHtml(row.name)}${detail ? `<small class="popup-player-detail">${escapeHtml(detail)}</small>` : ""}${EDITION.mixedLocationTypes ? `<small class="location-kind ${row.locationType && row.locationType !== "birthplace" ? "origin" : "birthplace"}">${row.locationType && row.locationType !== "birthplace" ? escapeHtml(EDITION.originLabel) : "Birthplace"}</small>` : ""}</span><b>${number.format(row.minutes)} ${escapeHtml(EDITION.workloadShort)}</b></button>`; }).join("");
  const rest = rows.length - visible.length;
  return `${items}${rest > 0 ? `<small class="popup-rest">+ ${rest} more ${escapeHtml(EDITION.participantLabelPlural)}</small>` : ""}`;
}

function revealPlaceMarker(marker) {
  if (!marker) return;
  const placeKey = marker.talentPlaceKey;
  const reveal = () => {
    state.map.setView(marker.getLatLng(), 6, { animate: false });
    (placeKey ? state.placeMarkers.get(placeKey) : marker)?.openPopup();
  };
  if (state.map.hasLayer(state.markerLayer) && state.markerLayer.zoomToShowLayer) state.markerLayer.zoomToShowLayer(marker, reveal);
  else reveal();
}

function aggregateTeamPlaces(records) {
  const places = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = `${row.lat}|${row.lon}|${row.place}`;
    if (!places.has(key)) places.set(key, { key, place: row.place || `Unnamed ${EDITION.locationLabel.toLowerCase()}`, country: row.country || "Country unavailable", lat: row.lat, lon: row.lon, teams: new Map() });
    const place = places.get(key);
    if (!place.teams.has(row.team)) place.teams.set(row.team, { team: row.team, minutes: 0, games: 0, playerRows: new Map() });
    const team = place.teams.get(row.team);
    team.minutes += row.minutes || 0;
    team.games += row.games || 0;
    team.playerRows.set(row.id, row);
  });
  return [...places.values()].map((place) => ({
    ...place,
    teamBubbles: [...place.teams.values()].map((team) => ({ ...team, players: team.playerRows.size, playerList: [...team.playerRows.values()].sort((a, b) => b.minutes - a.minutes || a.name.localeCompare(b.name)) })).sort((a, b) => a.team.localeCompare(b.team)),
  }));
}

function updateTeamColourLegend(teams) {
  let legend = $("#team-colour-legend");
  if (!legend) {
    legend = document.createElement("div");
    legend.id = "team-colour-legend";
    legend.className = "team-colour-legend";
    $("#population-scale").before(legend);
  }
  legend.hidden = teams.length === 0;
  legend.innerHTML = teams.map((team) => { const style = teamStyle(team); return `<span><i style="--team-colour:${style.colour}"></i><b>${escapeHtml(style.code)}</b>${escapeHtml(team)}</span>`; }).join("");
  $(".legend-size").hidden = teams.length > 0;
}

function renderTeamCityMap(records) {
  usePopulationBasemap(false);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (!state.map.hasLayer(state.teamMarkerLayer)) state.teamMarkerLayer.addTo(state.map);
  state.teamMarkerLayer.clearLayers();
  state.placeMarkers.clear();
  const places = aggregateTeamPlaces(records);
  const bubbles = places.flatMap((place) => place.teamBubbles);
  const maximum = Math.max(...bubbles.map(metricValue), 1);
  places.forEach((place) => {
    const centre = state.map.latLngToLayerPoint([place.lat, place.lon]);
    const sizes = place.teamBubbles.map((team) => Math.max(18, Math.round(9 + Math.sqrt(metricValue(team) / maximum) * 23)));
    const offsetRadius = place.teamBubbles.length > 1 ? Math.max(...sizes) / 2 + 5 : 0;
    place.teamBubbles.forEach((team, index) => {
      const angle = -Math.PI / 2 + index * Math.PI * 2 / place.teamBubbles.length;
      const point = L.point(centre.x + Math.cos(angle) * offsetRadius, centre.y + Math.sin(angle) * offsetRadius);
      const destination = state.map.layerPointToLatLng(point);
      const style = teamStyle(team.team);
      if (offsetRadius) L.polyline([[place.lat, place.lon], destination], { color: style.colour, weight: 1, opacity: .42, interactive: false }).addTo(state.teamMarkerLayer);
      const size = sizes[index];
      const marker = L.marker(destination, {
        bubblingMouseEvents: false,
        keyboard: true,
        icon: L.divIcon({ className: "team-rosette-icon", html: `<span style="--team-colour:${style.colour};--team-text:${style.text};--marker-size:${size}px">${escapeHtml(style.code)}</span>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] }),
      });
      marker.bindTooltip(`<strong>${escapeHtml(team.team)}</strong><br>${escapeHtml(place.place)}, ${escapeHtml(place.country)}<br>${number.format(metricValue(team))} ${metricLabel()} · ${team.players} ${escapeHtml(EDITION.participantLabelPlural)}`, { direction: "top" });
      marker.bindPopup(`<div class="map-popup"><strong>${escapeHtml(team.team)}</strong><small>${escapeHtml(place.place)}, ${escapeHtml(place.country)}</small><p>${number.format(metricValue(team))} ${metricLabel()} · ${team.players} ${escapeHtml(EDITION.participantLabelPlural)}</p>${popupPlayers(team.playerList)}</div>`, { maxWidth: 320 });
      marker.talentPlaceKey = place.key;
      marker.addTo(state.teamMarkerLayer);
      if (!state.placeMarkers.has(place.key)) state.placeMarkers.set(place.key, marker);
    });
  });
  updateTeamColourLegend(state.teams);
}

function renderCityMap(places) {
  usePopulationBasemap(false);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  if (state.teamMarkerLayer && state.map.hasLayer(state.teamMarkerLayer)) state.map.removeLayer(state.teamMarkerLayer);
  if (!state.map.hasLayer(state.markerLayer)) state.markerLayer.addTo(state.map);
  state.markerLayer.clearLayers();
  state.placeMarkers.clear();
  const values = places.map(metricValue);
  const maximum = Math.max(...values, 1);
  places.forEach((place) => {
    const radius = 5 + Math.sqrt(metricValue(place) / maximum) * 18;
    const marker = L.circleMarker([place.lat, place.lon], {
      radius,
      weight: 1,
      color: EDITION.markerStroke,
      fillColor: place.hasOrigin && !place.hasBirthplace ? EDITION.originMarkerFill : EDITION.markerFill,
      fillOpacity: .68,
    });
    marker.bindTooltip(`${escapeHtml(place.place)}, ${escapeHtml(place.country)} · ${number.format(metricValue(place))} ${metricLabel()}`);
    marker.bindPopup(`<div class="map-popup"><strong>${escapeHtml(place.place)}</strong><small>${escapeHtml(place.country)} · ${place.players} ${escapeHtml(EDITION.participantLabelPlural)}</small>${popupPlayers(place.playerList)}</div>`, { maxWidth: 310 });
    marker.talentPlaceKey = place.key;
    state.markerLayer.addLayer(marker);
    state.placeMarkers.set(place.key, marker);
  });
  updateTeamColourLegend([]);
}

function countryColour(value, maximum) {
  if (!value) return EDITION.countryEmpty;
  const intensity = Math.sqrt(value / Math.max(maximum, 1));
  const lightness = 26 + intensity * 40;
  return `hsl(${EDITION.countryHue} ${EDITION.countrySaturation}% ${lightness}%)`;
}

function renderCountryMap(countries) {
  usePopulationBasemap(false);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.teamMarkerLayer && state.map.hasLayer(state.teamMarkerLayer)) state.map.removeLayer(state.teamMarkerLayer);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  state.countryLayers.clear();
  updateTeamColourLegend([]);
  if (!state.countryGeojson) return;
  const byCode = new Map(countries.map((country) => [country.code, country]));
  const maximum = Math.max(...countries.map(metricValue), 1);
  state.countryLayer = L.geoJSON(state.countryGeojson, {
    style(feature) {
      const code = feature.properties.ADM0_A3;
      const country = byCode.get(code);
      return { color: "#594538", weight: .7, fillColor: countryColour(country ? metricValue(country) : 0, maximum), fillOpacity: country ? .82 : .32 };
    },
    onEachFeature(feature, layer) {
      const code = feature.properties.ADM0_A3;
      const country = byCode.get(code);
      state.countryLayers.set(code, layer);
      if (!country) return;
      layer.bindTooltip(`${escapeHtml(country.country)} · ${number.format(metricValue(country))} ${metricLabel()}`);
      layer.bindPopup(`<div class="map-popup"><strong>${escapeHtml(country.country)}</strong><small>${country.players} ${escapeHtml(EDITION.participantLabelPlural)} · ${number.format(country.minutes)} ${escapeHtml(EDITION.workloadLabel)}</small>${popupPlayers([...country.playerRows.values()].sort((a, b) => b.minutes - a.minutes))}</div>`, { maxWidth: 310 });
    },
  }).addTo(state.map);
}

function showPopulationLoading() {
  const measure = populationMeasure();
  usePopulationBasemap(true);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.teamMarkerLayer && state.map.hasLayer(state.teamMarkerLayer)) state.map.removeLayer(state.teamMarkerLayer);
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
  updateTeamColourLegend([]);
}

function renderPopulationMap(records) {
  const measure = populationMeasure();
  usePopulationBasemap(true);
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.teamMarkerLayer && state.map.hasLayer(state.teamMarkerLayer)) state.map.removeLayer(state.teamMarkerLayer);
  if (state.countryLayer && state.map.hasLayer(state.countryLayer)) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer && state.map.hasLayer(state.populationLayer)) state.map.removeLayer(state.populationLayer);
  const cells = aggregatePopulationCells(records);
  updatePopulationRateScale();
  const byId = new Map(cells.map((cell) => [cell.hexId, cell]));
  state.populationLayers.clear();
  state.populationLayer = L.geoJSON({ type: "FeatureCollection", features: cells.map((cell) => cell.feature) }, {
    style(feature) {
      const cell = byId.get(feature.properties.hex_id);
      const regional = state.populationResolution === 3;
      if (cell.reference) return { color: "#66817a", weight: regional ? .18 : .35, fillColor: populationRateColour(0), fillOpacity: .13 };
      return { color: cell.stable ? "#94c8b4" : "#62877d", weight: regional ? (cell.stable ? .55 : .4) : (cell.stable ? .8 : .65), dashArray: cell.stable ? null : "3 3", fillColor: populationRateColour(cell.rate), fillOpacity: cell.stable ? .82 : .42 };
    },
    onEachFeature(feature, layer) {
      const cell = byId.get(feature.properties.hex_id);
      if (cell.reference) {
        const country = cell.country || "Populated land";
        layer.bindTooltip(`<strong>${escapeHtml(country)} reference area</strong><br>No mapped ${escapeHtml(EDITION.participantLabelPlural)} in this selection<br>population ${compact.format(cell.population)}`, { sticky: true });
        layer.bindPopup(`<div class="map-popup"><strong>${escapeHtml(country)} reference area</strong><small>No mapped ${escapeHtml(EDITION.participantLabelPlural)} in this selection</small><p>${number.format(cell.population)} residents · WorldPop 2025</p></div>`, { maxWidth: 320 });
        state.populationLayers.set(cell.hexId, layer);
        return;
      }
      const rateLabel = cell.rate === null ? "Population estimate unavailable" : `${compact.format(cell.rate)} ${measure.short}`;
      const caution = cell.stable ? "" : " · small sample";
      layer.bindTooltip(`<strong>${escapeHtml(cell.label)} area</strong><br>${escapeHtml(cell.country)}<br>${rateLabel}<br>${cell.players} ${escapeHtml(EDITION.participantLabelPlural)}${measure.workload ? ` · ${number.format(cell.workload)} ${escapeHtml(EDITION.workloadShort)}` : ""} · population ${cell.population ? compact.format(cell.population) : "unavailable"}${caution}`, { sticky: true });
      layer.bindPopup(`<div class="map-popup"><strong>${escapeHtml(cell.label)} area</strong><small>${rateLabel}</small><p>${cell.players} mapped ${escapeHtml(EDITION.participantLabelPlural)}${measure.workload ? ` · ${number.format(cell.workload)} ${escapeHtml(EDITION.workloadLabel)}` : ""} · ${cell.population ? `${number.format(cell.population)} residents` : "population unavailable"}</p>${cell.stable ? "" : `<small class="popup-rest">Interpret carefully: fewer than two ${escapeHtml(EDITION.participantLabelPlural)} or fewer than 100,000 residents.</small>`}</div>`, { maxWidth: 320 });
      state.populationLayers.set(cell.hexId, layer);
    },
  }).addTo(state.map);
  $("#ranking-title").textContent = measure.label;
  const activeCount = cells.filter((cell) => !cell.reference).length;
  const referenceCount = cells.length - activeCount;
  $("#place-count").textContent = referenceCount ? `${number.format(activeCount)} active · ${number.format(referenceCount)} reference` : `${number.format(activeCount)} ${populationResolutionLabel().toLowerCase()} areas`;
  const ranked = cells.filter((cell) => !cell.reference && cell.rate !== null).sort((a, b) => Number(b.stable) - Number(a.stable) || b.rate - a.rate).slice(0, 12);
  const maximum = Math.max(...ranked.map((cell) => cell.rate), 1);
  $("#place-ranking").innerHTML = ranked.length ? ranked.map((cell, index) => `<li class="place-row" style="--bar:${cell.rate / maximum * 100}%"><button class="place-jump" type="button" data-hex-id="${escapeHtml(cell.hexId)}"><span class="place-rank">${String(index + 1).padStart(2, "0")}</span><span class="place-name"><strong>${escapeHtml(cell.label)} area</strong><small>${escapeHtml(cell.country)} · ${cell.players} ${escapeHtml(EDITION.participantLabelPlural)}${measure.workload ? ` · ${number.format(cell.workload)} ${escapeHtml(EDITION.workloadShort)}` : ""} / ${compact.format(cell.population)} people</small></span><span class="place-value">${compact.format(cell.rate)}</span></button></li>`).join("") : `<li>${emptyState("Try widening the current selection.")}</li>`;
  $("#map-legend").classList.add("population");
  $("#population-scale").hidden = false;
  $("#legend-prefix").textContent = "Colour =";
  $("#legend-metric").textContent = measure.label;
  updateTeamColourLegend([]);
}

function renderRanking(items) {
  const sorted = [...items].sort((a, b) => metricValue(b) - metricValue(a) || (a.place || a.country).localeCompare(b.place || b.country));
  const visible = sorted.slice(0, 12);
  const maximum = Math.max(...visible.map(metricValue), 1);
  $("#ranking-title").textContent = `By ${metricLabel()}`;
  $("#place-count").textContent = `${number.format(items.length)} ${state.mapMode === "city" ? EDITION.locationPlural : "countries"}`;
  $("#place-ranking").innerHTML = visible.length ? visible.map((item, index) => {
    const name = item.place || item.country;
    const detail = state.mapMode === "city" ? `${item.country} · ${item.players} ${EDITION.participantLabelPlural}` : `${item.players} ${EDITION.participantLabelPlural}`;
    const target = state.mapMode === "city" ? `data-place-key="${escapeHtml(item.key)}"` : `data-country-code="${escapeHtml(item.code)}"`;
    return `<li class="place-row" style="--bar:${metricValue(item) / maximum * 100}%"><button class="place-jump" type="button" ${target}><span class="place-rank">${String(index + 1).padStart(2, "0")}</span><span class="place-name"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(detail)}</small></span><span class="place-value">${compact.format(metricValue(item))}</span></button></li>`;
  }).join("") : `<li>${emptyState("Try widening the current selection.")}</li>`;
}

function updateMap() {
  const records = filteredRecords();
  const teamRecords = filteredTeamRecords();
  const places = aggregatePlaces(records);
  const countries = aggregateCountries(records);
  if (isPopulationMode()) {
    // A previously loaded population layer skips showPopulationLoading(), so
    // restore its controls here as well when returning from another map mode.
    $(".resolution-control").hidden = false;
    if (!state.populationGeojson.has(state.populationResolution)) { showPopulationLoading(); return; }
    renderPopulationMap(records);
    $("#map-explorer").classList.add("country-mode");
    $(".metric-control").hidden = true;
    return;
  }
  if (state.mapMode === "country" && state.countryGeojson) renderCountryMap(countries);
  else if (TEAM_STYLES && state.teams.length) renderTeamCityMap(teamRecords);
  else renderCityMap(places);
  renderRanking(state.mapMode === "city" ? places : countries);
  $("#map-legend").classList.remove("population");
  $("#population-scale").hidden = true;
  $("#legend-prefix").textContent = TEAM_STYLES && state.teams.length && state.mapMode === "city" ? "Team colour · bubble size =" : state.mapMode === "city" ? "Circle size =" : "Colour intensity =";
  $("#legend-metric").textContent = metricLabel();
  $("#map-legend").classList.toggle("country", state.mapMode === "country");
  $("#map-explorer").classList.toggle("country-mode", state.mapMode !== "city");
  $(".metric-control").hidden = false;
  $(".resolution-control").hidden = true;
}

function updateKpis() {
  const records = filteredRecords();
  const mapped = records.filter((row) => row.mapped).length;
  $("#kpi-players").textContent = number.format(records.length);
  $("#kpi-minutes").textContent = compact.format(records.reduce((sum, row) => sum + row.minutes, 0));
  $("#kpi-coverage").textContent = records.length ? `${(mapped / records.length * 100).toFixed(1)}%` : "—";
}

function updateConferenceComparison() {
  const conferences = aggregateConferences();
  $("#conference-comparison").innerHTML = conferences.map((conference, index) => `
    <article class="league-card" style="--order:${index}">
      <header><div><span>0${index + 1}</span><h3>${escapeHtml(conference.conference)}</h3></div><strong>${EDITION.comparisonHighlight === "coverage" ? (conference.mapped / conference.players * 100).toFixed(0) : conference.outsideHomePct.toFixed(0)}%<small>${escapeHtml(EDITION.comparisonHighlight === "coverage" ? "birthplace mapped" : EDITION.outsideHomeLabel.toLowerCase())}</small></strong></header>
      <div class="league-primary"><div><b>${conference.players}</b><span>${escapeHtml(EDITION.participantLabelPlural)}</span></div><div><b>${compact.format(conference.minutes)}</b><span>${escapeHtml(EDITION.workloadShort)}</span></div><div><b>${conference.countries}</b><span>${escapeHtml(EDITION.countryGroupLabel)}</span></div></div>
      <div class="domestic-track"><i style="width:${EDITION.comparisonHighlight === "coverage" ? conference.mapped / conference.players * 100 : conference.outsideHomePct}%"></i></div>
      <div class="league-detail"><div><span class="card-label">Leading ${escapeHtml(EDITION.countryGroupLabel)}</span><ol>${conference.topCountries.map(([country, count]) => `<li><span>${escapeHtml(country)}</span><b>${count}</b></li>`).join("")}</ol></div></div>
      <div class="league-footer">Median age ${conference.medianAge?.toFixed(1) ?? "—"} · ${number.format(conference.minutes)} total ${escapeHtml(EDITION.workloadLabel)} · ${conference.mapped} of ${conference.players} ${escapeHtml(EDITION.participantLabelPlural)} mapped</div>
    </article>`).join("") || emptyState("No conference matches the current selection.");
}

function updateTeamChart() {
  const teams = aggregateTeams(filteredTeamRecords()).sort((a, b) => b.minutes - a.minutes || a.team.localeCompare(b.team));
  const maximum = Math.max(...teams.map((team) => team.minutes), 1);
  $("#team-chart").innerHTML = teams.length ? teams.map((team) => `
    <div class="team-row"><div class="team-name"><strong>${escapeHtml(team.team)}</strong><small>${escapeHtml(team.conference.replace(" Conference", ""))} · ${team.players} ${escapeHtml(EDITION.participantLabelPlural)}</small></div><div class="team-track"><i style="width:${team.minutes / maximum * 100}%"></i></div><div class="team-value">${number.format(team.minutes)}<small>${team.coverage.toFixed(1)}% mapped</small></div></div>`).join("") : emptyState("No teams match the current selection.");
}

function updateAgeAndCountry() {
  const records = filteredRecords();
  const birthplaceRecords = EDITION.mixedLocationTypes ? records.filter((row) => !row.locationType || row.locationType === "birthplace") : records;
  const ages = records.map((row) => row.age).filter(Number.isFinite);
  const outsideHome = birthplaceRecords.filter((row) => row.mapped && row.country !== EDITION.homeCountry).length;
  const mapped = birthplaceRecords.filter((row) => row.mapped).length;
  const representedCountries = new Set(records.map((row) => row.representedCountry).filter(Boolean)).size;
  $("#age-overview").innerHTML = `
    <article><span>Median age</span><strong>${median(ages)?.toFixed(1) ?? "—"}</strong><small>${escapeHtml(EDITION.participantLabelPlural)} in snapshot</small></article>
    <article><span>Under 23</span><strong>${number.format(ages.filter((age) => age < 23).length)}</strong><small>${ages.length ? (ages.filter((age) => age < 23).length / ages.length * 100).toFixed(1) : 0}% of ${escapeHtml(EDITION.participantLabelPlural)}</small></article>
    <article><span>Age 30+</span><strong>${number.format(ages.filter((age) => age >= 30).length)}</strong><small>${ages.length ? (ages.filter((age) => age >= 30).length / ages.length * 100).toFixed(1) : 0}% of ${escapeHtml(EDITION.participantLabelPlural)}</small></article>
    <article><span>${escapeHtml(EDITION.comparisonHighlight === "coverage" ? "Represented countries" : EDITION.outsideHomeLabel)}</span><strong>${EDITION.comparisonHighlight === "coverage" ? number.format(representedCountries) : `${mapped ? (outsideHome / mapped * 100).toFixed(1) : 0}%`}</strong><small>${EDITION.comparisonHighlight === "coverage" ? "ranking nationalities" : `of mapped ${escapeHtml(EDITION.participantLabelPlural)}`}</small></article>`;
  const countries = aggregateCountries(birthplaceRecords);
  const byPlayers = [...countries].sort((a, b) => b.players - a.players || a.country.localeCompare(b.country)).slice(0, 10);
  const byMinutes = [...countries].sort((a, b) => b.minutes - a.minutes || a.country.localeCompare(b.country)).slice(0, 10);
  const panel = (title, label, items, value) => {
    const maximum = Math.max(...items.map(value), 1);
    return `<article class="country-panel"><span class="card-label">Birth-country comparison</span><h3>${title}</h3><ol class="country-list">${items.map((country) => `<li style="--bar:${value(country) / maximum * 100}%"><span>${escapeHtml(country.country)}</span><b>${label(country)}</b></li>`).join("")}</ol></article>`;
  };
  $("#country-comparison").innerHTML = countries.length
    ? `${panel(`By ${EDITION.participantLabelPlural}`, (country) => number.format(country.players), byPlayers, (country) => country.players)}${panel(`By ${EDITION.workloadLabel}`, (country) => compact.format(country.minutes), byMinutes, (country) => country.minutes)}`
    : emptyState("No mapped birth countries match the current selection.");
  $("#age-scope").textContent = `${number.format(records.length)} ${EDITION.participantLabelPlural} in the current selection`;
}

function updatePlayerTable() {
  const query = normalSearch(state.search.trim());
  const players = filteredRecords()
    .filter((row) => !query || [row.name, row.team, ...(row.teams || []), row.place, row.country, ...positionValues(row)].some((value) => normalSearch(value).includes(query)))
    .sort((a, b) => b.minutes - a.minutes || a.name.localeCompare(b.name));
  const visible = players.slice(0, state.playerLimit);
  $("#player-table").innerHTML = visible.map((row) => `
    <tr class="player-row"><td data-label="Player"><button type="button" class="player-open-button" data-player-id="${escapeHtml(row.id)}" aria-label="Open profile for ${escapeHtml(row.name)}"><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(participantDetail(row))}</small></button></td><td data-label="${escapeHtml(EDITION.tableGroupLabel)}">${escapeHtml((row.teams || [row.team]).join(", "))}</td>${EDITION.showConferenceColumn ? `<td data-label="${escapeHtml(EDITION.conferenceLabel)}">${escapeHtml(row.conference.replace(" Conference", ""))}</td>` : ""}<td data-label="${escapeHtml(EDITION.locationLabel)}">${row.mapped ? `${escapeHtml(row.place)}<br><small>${escapeHtml(row.country)}</small>${EDITION.mixedLocationTypes ? `<span class="location-kind ${row.locationType && row.locationType !== "birthplace" ? "origin" : "birthplace"}">${row.locationType && row.locationType !== "birthplace" ? escapeHtml(EDITION.originLabel) : "Birthplace"}</span>` : ""}` : `<span style="color:var(--danger)">Awaiting QA</span>`}</td><td class="numeric" data-label="${escapeHtml(EDITION.tableStatLabel)}">${number.format(row[EDITION.tableStatField])}</td>${EDITION.showWorkloadColumn ? `<td class="numeric" data-label="${escapeHtml(EDITION.workloadLabel)}">${number.format(row.minutes)}</td>` : ""}</tr>`).join("");
  const empty = $("#player-empty-state");
  empty.hidden = players.length > 0;
  empty.innerHTML = players.length ? "" : `<h3>No ${escapeHtml(EDITION.participantLabelPlural)} found</h3><p>${escapeHtml(query ? "Try another search or clear the current filters." : `This selection has no ${EDITION.participantLabelPlural}.`)}</p><button type="button" class="empty-state-action" data-clear-filters>Clear filters</button>`;
  $("#player-table").closest("table").hidden = players.length === 0;
  $("#player-table-note").textContent = players.length ? `Showing ${number.format(visible.length)} of ${number.format(players.length)} ${EDITION.participantLabelPlural} · sorted by ${EDITION.workloadLabel}` : `No ${EDITION.participantLabelPlural} to show`;
  const remaining = Math.max(0, players.length - visible.length);
  const loadMore = $("#load-more-players");
  loadMore.hidden = remaining === 0;
  loadMore.textContent = remaining ? `Show ${number.format(Math.min(PLAYER_BATCH, remaining))} more` : "Show more players";
}

function updateQuality() {
  const { summary, unresolved } = state.payload;
  const playerCoverage = summary[EDITION.qualityPlayerCoverageField];
  const workloadCoverage = summary[EDITION.qualityWorkloadCoverageField];
  $("#quality-player-coverage").textContent = `${playerCoverage}%`;
  $("#quality-minute-coverage").textContent = `${workloadCoverage}%`;
  $("#quality-player-bar").style.width = `${playerCoverage}%`;
  $("#quality-minute-bar").style.width = `${workloadCoverage}%`;
  $("#quality-mapped-players").textContent = `${number.format(summary[EDITION.qualityMappedPlayersField])} mapped`;
  $("#quality-unresolved").textContent = `${number.format(summary.unresolved_players)} unresolved`;
  $("#quality-mapped-minutes").textContent = `${number.format(summary[EDITION.qualityMappedWorkloadField])} mapped ${EDITION.workloadLabel}`;
  $("#quality-total-minutes").textContent = `${number.format(summary[EDITION.qualityTotalWorkloadField])} total`;
  $("#unresolved-count").textContent = `${number.format(summary.unresolved_players)} ${EDITION.participantLabelPlural}`;
  $("#unresolved-list").innerHTML = unresolved.length ? unresolved.map((row) => `<div class="unresolved-row"><span>${escapeHtml(row.name)}</span><span>${escapeHtml(row.status)}</span></div>`).join("") : `<p>No unresolved ${escapeHtml(EDITION.participantLabelPlural)}.</p>`;
}

function updateFilterUi() {
  const filters = [
    state.conference !== "all" && { key: "conference", label: state.conference.replace(" Conference", "") },
    TEAM_STYLES ? state.teams.length > 0 && { key: "teams", label: state.teams.length === 1 ? state.teams[0] : `${state.teams.length} ${EDITION.groupLabelPlural}` } : state.team !== "all" && { key: "team", label: state.team },
    state.country !== "all" && { key: "country", label: `${EDITION.mixedLocationTypes ? "Located" : "Born"} in ${state.country}` },
    state.position !== "all" && { key: "position", label: state.position },
  ].filter(Boolean);
  const container = $("#active-filters");
  container.innerHTML = filters.map((filter) => `<button type="button" class="filter-chip" data-clear-filter="${filter.key}" aria-label="Remove ${escapeHtml(filter.label)} filter"><span>${escapeHtml(filter.label)}</span><span aria-hidden="true">×</span></button>`).join("");
  container.hidden = filters.length === 0;
  const moreFilterCount = Number(state.country !== "all") + Number(state.position !== "all");
  $("#more-filter-count").textContent = moreFilterCount ? String(moreFilterCount) : "";
  $("#reset-filters").disabled = filters.length === 0 && !state.search && !state.placeQuery && state.metric === EDITION.defaultMetric && state.mapMode === "city";
  const conference = state.conference === "all" ? EDITION.allConferenceLabel : state.conference.replace(" Conference", "");
  const team = TEAM_STYLES ? state.teams.length ? (state.teams.length === 1 ? state.teams[0] : `${state.teams.length} ${EDITION.groupLabelPlural}`) : `All ${EDITION.groupLabelPlural}` : state.team === "all" ? `All ${EDITION.groupLabelPlural}` : state.team;
  const country = state.country === "all" ? `All ${EDITION.countryGroupLabel}` : `${EDITION.mixedLocationTypes ? "Located" : "Born"} in ${state.country}`;
  $("#filter-summary").textContent = [conference, EDITION.showTeamFilter && team, country].filter(Boolean).join(" · ");
}

function updateTeamPicker(allowedTeams = null) {
  if (!TEAM_STYLES) return;
  const allowed = allowedTeams || new Set(state.teamMeta.map((team) => team.name));
  const query = normalSearch($("#team-search")?.value || "");
  $$("#team-options .team-option").forEach((option) => {
    const checkbox = option.querySelector("input");
    const selected = state.teams.includes(checkbox.value);
    const available = allowed.has(checkbox.value);
    option.hidden = !available || Boolean(query && !normalSearch(option.dataset.search).includes(query));
    checkbox.checked = selected;
    checkbox.disabled = !selected && state.teams.length >= 6;
  });
  $$("#team-options .team-option-group").forEach((group) => { group.hidden = !group.querySelector(".team-option:not([hidden])"); });
  const selected = state.teamMeta.filter((team) => state.teams.includes(team.name));
  $("#team-picker-summary").textContent = selected.length === 0 ? `All ${EDITION.groupLabelPlural}` : selected.length === 1 ? selected[0].name : `${selected.length} ${EDITION.groupLabelPlural} selected`;
  const chips = $("#selected-team-chips");
  chips.hidden = selected.length === 0;
  chips.innerHTML = selected.map((team) => { const style = teamStyle(team.name); return `<button type="button" data-remove-team="${escapeHtml(team.name)}" title="Remove ${escapeHtml(team.name)}"><i style="--team-colour:${style.colour}"></i><span>${escapeHtml(style.code)}</span><b aria-hidden="true">×</b></button>`; }).join("");
}

function buildTeamPicker() {
  if (!TEAM_STYLES) return;
  state.teamMeta = state.payload.meta.teams.map((name) => {
    const record = state.payload.records.find((row) => row.team === name || row.teamSplits?.some((split) => split.team === name));
    const split = record?.teamSplits?.find((item) => item.team === name);
    return { name, conference: split?.conference || record?.conference || EDITION.singleGroupLabel };
  });
  const control = $(".team-control");
  control.querySelector(".select-wrap").hidden = true;
  const label = control.querySelector("label")?.textContent || "Teams";
  control.querySelector("label")?.remove();
  control.insertAdjacentHTML("afterbegin", `<span class="control-label">${escapeHtml(label)}</span><details class="team-picker" id="team-picker"><summary id="team-picker-summary">All ${escapeHtml(EDITION.groupLabelPlural)}</summary><div class="team-picker-panel"><label class="team-search"><span class="sr-only">Search ${escapeHtml(EDITION.groupLabelPlural)}</span><input id="team-search" type="search" placeholder="Find a ${escapeHtml(EDITION.groupLabelPlural.slice(0, -1))}…" autocomplete="off" /></label><div class="team-options" id="team-options" role="group" aria-label="Choose up to six ${escapeHtml(EDITION.groupLabelPlural)}"></div><div class="team-picker-footer"><span>Choose up to 6</span><button id="clear-teams" type="button">All ${escapeHtml(EDITION.groupLabelPlural)}</button></div></div></details><div class="selected-team-chips" id="selected-team-chips" hidden></div>`);
  const groups = new Map();
  state.teamMeta.forEach((team) => { if (!groups.has(team.conference)) groups.set(team.conference, []); groups.get(team.conference).push(team); });
  $("#team-options").innerHTML = [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([conference, teams]) => `<section class="team-option-group"><strong>${escapeHtml(conference.replace(" Conference", ""))}</strong>${teams.sort((a, b) => a.name.localeCompare(b.name)).map((team) => { const style = teamStyle(team.name); return `<label class="team-option" data-search="${escapeHtml(`${team.name} ${style.code} ${team.conference}`)}"><input type="checkbox" value="${escapeHtml(team.name)}" /><i style="--team-colour:${style.colour}"></i><span>${escapeHtml(team.name)}</span><b>${escapeHtml(style.code)}</b></label>`; }).join("")}</section>`).join("");
  updateTeamPicker();
}

function updateSnapshotCopy() {
  const { meta, summary } = state.payload;
  const generated = new Date(meta.generated_at);
  const updated = Number.isNaN(generated.getTime()) ? "" : generated.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric", timeZone: "Australia/Melbourne" });
  if (updated) $(".status-pill").innerHTML = `<i aria-hidden="true"></i> ${escapeHtml(meta.season)} · Updated ${escapeHtml(updated)}`;
  $(".hero-statline").innerHTML = `<strong>${number.format(summary.players)} ${escapeHtml(EDITION.participantLabelPlural)}</strong><span>${number.format(summary.teams)} ${escapeHtml(EDITION.groupLabelPlural)}</span><span>${number.format(summary.birth_countries)} birth countries</span>`;
}

function populateFilters() {
  const addOptions = (selector, values) => {
    const select = $(selector);
    values.forEach((value) => select.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`));
  };
  addOptions("#conference-filter", state.payload.meta.conferences);
  addOptions("#team-filter", state.payload.meta.teams);
  addOptions("#country-filter", [...new Set(state.payload.records.filter((row) => row.mapped).map((row) => row.country))].sort());
  if ($("#position-filter")) addOptions("#position-filter", [...new Set(state.payload.records.flatMap(positionValues))].sort());
  const places = aggregatePlaces(state.payload.records).sort((a, b) => a.place.localeCompare(b.place));
  $("#place-options").innerHTML = places.map((place) => `<option value="${escapeHtml(place.place)}, ${escapeHtml(place.country)}"></option>`).join("");
  buildTeamPicker();
}

function syncTeamOptions() {
  if (TEAM_STYLES) {
    const allowed = new Set(state.teamMeta.filter((team) => state.conference === "all" || team.conference === state.conference).map((team) => team.name));
    state.teams = state.teams.filter((team) => allowed.has(team));
    updateTeamPicker(allowed);
    return;
  }
  const options = [...$("#team-filter").options];
  options.forEach((option) => {
    if (option.value === "all") return;
    const record = state.payload.records.find((row) => row.team === option.value || row.teamSplits?.some((split) => split.team === option.value));
    const conference = record?.teamSplits?.find((split) => split.team === option.value)?.conference || record?.conference;
    option.hidden = state.conference !== "all" && conference !== state.conference;
  });
  if (state.team !== "all" && $("#team-filter").selectedOptions[0]?.hidden) {
    state.team = "all";
    $("#team-filter").value = "all";
  }
}

function render() {
  syncTeamOptions();
  updateFilterUi();
  updateKpis();
  updateMap();
  updateConferenceComparison();
  updateTeamChart();
  updateAgeAndCountry();
  updatePlayerTable();
}

function openPlayerProfile(playerId, opener = document.activeElement) {
  const player = filteredRecords().find((row) => row.id === playerId)
    || state.payload.records.find((row) => row.id === playerId);
  if (!player) return;
  const conferences = [...new Set((player.teamSplits || []).map((split) => split.conference))];
  const profileOrigin = player[EDITION.profileOriginField] || EDITION.profileOriginFallback;
  $("#profile-name").textContent = player.name;
  $("#profile-meta").textContent = `${participantDetail(player)} · ${profileOrigin}`;
  $("#profile-team").textContent = (player.teams || [player.team]).join(" · ");
  $("#profile-conference").textContent = (conferences.length ? conferences : [player.conference]).join(" · ");
  ["#profile-games", "#profile-minutes", "#profile-points", "#profile-rebounds", "#profile-assists"].forEach((selector, index) => {
    const key = EDITION.profileStats[index];
    const digits = EDITION.profileStatDecimals[key];
    $(selector).textContent = digits === undefined
      ? number.format(player[key] || 0)
      : Number(player[key] || 0).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  });
  const fightLog = $("#profile-fight-log");
  const eventLog = $("#profile-event-log") || fightLog;
  if (eventLog && EDITION.profileLogType === "volleyball") {
    const rows = player.matchLog || [];
    eventLog.innerHTML = rows.length ? `<h3>${escapeHtml(EDITION.profileLogTitle || "Match log")}</h3><ol>${rows.map((match) => `<li><b>${number.format(match.sets || 0)}</b><span>vs ${escapeHtml(match.opponent)}<br><small>${escapeHtml(match.round || "VNL")} · ${escapeHtml(match.date)}</small></span><span>${number.format(match.points || 0)} points<br><small>${escapeHtml(match.team)}</small></span></li>`).join("")}</ol>` : "";
  } else if (eventLog && EDITION.profileLogType === "race") {
    const rows = player.raceLog || [];
    const statusLabels = { INSTND: "Classified", OUTSTND: "Not classified", RET: "Retired", DSQ: "Disqualified" };
    eventLog.innerHTML = rows.length ? `<h3>${escapeHtml(EDITION.profileLogTitle || "Race log")}</h3><ol>${rows.map((race) => { const rawStatus = String(race.status || ""); const status = statusLabels[rawStatus] || (/^\d+$/.test(rawStatus) ? "Classified" : rawStatus || "Classified"); return `<li><b>${race.position ? `P${number.format(race.position)}` : "—"}</b><span>${escapeHtml(race.event)}<br><small>${escapeHtml(race.series)} · ${escapeHtml(race.session)}</small></span><span>${number.format(race.laps || 0)} laps<br><small>${escapeHtml(race.team)} · ${escapeHtml(status)}</small></span></li>`; }).join("")}</ol>` : "";
  } else if (eventLog && EDITION.profileLogType === "athletics") {
    const rows = player.eventLog || [];
    eventLog.innerHTML = rows.length ? `<h3>${escapeHtml(EDITION.profileLogTitle || "Championship events")}</h3><ol>${rows.map((event) => `<li><b>${event.medal ? escapeHtml(event.medal) : event.bestPlace ? `P${number.format(event.bestPlace)}` : "—"}</b><span>${escapeHtml(event.event)}<br><small>${escapeHtml(event.discipline)} · ${escapeHtml(event.gender)}</small></span><span>${number.format(event.rounds || 0)} result ${event.rounds === 1 ? "round" : "rounds"}<br><small>${escapeHtml(player.team)}</small></span></li>`).join("")}</ol>` : "";
  } else if (fightLog) {
    const rows = player.fightLog || [];
    fightLog.innerHTML = rows.length ? `<h3>2025 fight log</h3><ol>${rows.map((fight) => `<li><b class="${fight.result === "W" ? "win" : fight.result === "L" ? "loss" : ""}">${escapeHtml(fight.result)}</b><span>${escapeHtml(fight.opponent)}<br><small>${escapeHtml(fight.event)} · ${escapeHtml(fight.division)}</small></span><span>${escapeHtml(fight.method)}<br><small>R${number.format(fight.round)} ${escapeHtml(fight.time)}</small></span></li>`).join("")}</ol>` : "";
  }
  const profileLocationLabel = $("#profile-location-label");
  if (profileLocationLabel) profileLocationLabel.textContent = player.locationType && player.locationType !== "birthplace" ? `${EDITION.originLabel} (birthplace unavailable)` : "Place of birth";
  $("#profile-birthplace").textContent = player.mapped ? `${player.place}, ${player.country}` : `${EDITION.locationLabel} awaiting QA`;
  $("#profile-dob").textContent = player.dob || "Unavailable";
  $("#profile-age").textContent = Number.isFinite(player.age) ? `${player.age} years old` : "Age unavailable";
  state.profileOpener = opener instanceof HTMLElement ? opener : null;
  [$(".site-header"), $("main"), $("footer")].forEach((element) => { if (element) element.inert = true; });
  const modal = $("#player-modal");
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
  $("#profile-map-empty").textContent = `Map unavailable until this ${EDITION.locationLabel.toLowerCase()} clears QA.`;
  $("#profile-map-empty").hidden = player.mapped;
  $("#player-mini-map").hidden = !player.mapped;
  if (player.mapped) {
    setTimeout(() => {
      if (!modal.classList.contains("open")) return;
      state.profileMap = L.map("player-mini-map", { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false }).setView([player.lat, player.lon], 6);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd" }).addTo(state.profileMap);
      L.circleMarker([player.lat, player.lon], { radius: 8, color: EDITION.markerStroke, fillColor: player.locationType && player.locationType !== "birthplace" ? EDITION.originMarkerFill : EDITION.markerFill, fillOpacity: .8 }).addTo(state.profileMap);
    }, 80);
  }
  $("#close-player-modal").focus();
}

function closePlayerProfile() {
  const modal = $("#player-modal");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  [$(".site-header"), $("main"), $("footer")].forEach((element) => { if (element) element.inert = false; });
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
  const target = state.profileOpener?.isConnected ? state.profileOpener : $(`.view-tabs button[data-view="${state.view}"]`);
  state.profileOpener = null;
  target?.focus({ preventScroll: true });
}

function handleModalKeydown(event) {
  const modal = $("#player-modal");
  if (!modal.classList.contains("open")) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closePlayerProfile();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...modal.querySelectorAll('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')].filter((element) => !element.hidden);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function setView(view, { focus = false, updateHash = true } = {}) {
  const target = $(`.view-tabs button[data-view="${view}"]`) ? view : DEFAULT_VIEW;
  state.view = target;
  $$(".view-tabs button").forEach((button) => {
    const active = button.dataset.view === target;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
    if (active && focus) button.focus();
  });
  $$(".view-panel").forEach((panel) => {
    const active = panel.id === `view-${target}`;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  if (updateHash) history.replaceState(null, "", `#${target}`);
  if (target === "map") setTimeout(() => state.map?.invalidateSize(), 50);
}

function applyMapHandoff() {
  const handoff = window.TalentGeoNavigation?.readMapState();
  if (!handoff) return null;
  state.mapMode = handoff.mode;
  state.populationResolution = handoff.resolution;
  state.metric = handoff.measure === "people" ? "players" : EDITION.defaultMetric;
  const countryExists = [...$("#country-filter").options].some((option) => option.value === handoff.country);
  state.country = countryExists ? handoff.country : "all";
  $("#country-filter").value = state.country;
  $$("#metric-control button").forEach((button) => {
    const active = button.dataset.metric === state.metric;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $$("#map-mode button").forEach((button) => {
    const active = button.dataset.mapMode === state.mapMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $$("#resolution-control button").forEach((button) => {
    const active = Number(button.dataset.resolution) === state.populationResolution;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  return handoff;
}

function currentMapHandoff() {
  const center = state.map?.getCenter().wrap();
  return {
    mode: state.mapMode,
    measure: state.metric === "players" ? "people" : "workload",
    resolution: state.populationResolution,
    country: state.country,
    viewport: center ? { lat: center.lat, lon: center.lng, zoom: state.map.getZoom() } : null,
  };
}

function resetAll() {
  state.conference = "all";
  state.team = "all";
  state.teams = [];
  state.country = "all";
  state.position = "all";
  state.metric = EDITION.defaultMetric;
  state.mapMode = "city";
  state.populationResolution = 3;
  state.search = "";
  state.placeQuery = "";
  state.playerLimit = PLAYER_BATCH;
  $("#conference-filter").value = "all";
  $("#team-filter").value = "all";
  $("#country-filter").value = "all";
  if ($("#position-filter")) $("#position-filter").value = "all";
  $("#player-search").value = "";
  $("#place-search").value = "";
  if ($("#team-search")) $("#team-search").value = "";
  if ($("#team-picker")) $("#team-picker").open = false;
  $("#clear-place-search").hidden = true;
  $$("#metric-control button").forEach((button) => {
    const active = button.dataset.metric === state.metric;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $$("#map-mode button").forEach((button) => {
    const active = button.dataset.mapMode === state.mapMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $$("#resolution-control button").forEach((button) => {
    const active = Number(button.dataset.resolution) === state.populationResolution;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  render();
}

function bindEvents() {
  $("#conference-filter").addEventListener("change", (event) => { state.conference = event.target.value; state.playerLimit = PLAYER_BATCH; render(); });
  $("#team-filter").addEventListener("change", (event) => { state.team = event.target.value; state.playerLimit = PLAYER_BATCH; render(); });
  if (TEAM_STYLES) {
    $("#team-options").addEventListener("change", (event) => {
      const checkbox = event.target.closest('input[type="checkbox"]');
      if (!checkbox) return;
      if (checkbox.checked && !state.teams.includes(checkbox.value) && state.teams.length < 6) state.teams.push(checkbox.value);
      if (!checkbox.checked) state.teams = state.teams.filter((team) => team !== checkbox.value);
      state.playerLimit = PLAYER_BATCH;
      updateTeamPicker();
      render();
    });
    $("#team-search").addEventListener("input", () => updateTeamPicker());
    $("#clear-teams").addEventListener("click", () => { state.teams = []; $("#team-search").value = ""; updateTeamPicker(); render(); });
    $("#team-picker").addEventListener("keydown", (event) => { if (event.key === "Escape") { event.preventDefault(); $("#team-picker").open = false; $("#team-picker-summary").focus(); } });
  }
  $("#country-filter").addEventListener("change", (event) => { state.country = event.target.value; state.playerLimit = PLAYER_BATCH; render(); });
  $("#position-filter")?.addEventListener("change", (event) => { state.position = event.target.value; state.playerLimit = PLAYER_BATCH; render(); });
  $("#reset-filters").addEventListener("click", resetAll);
  $("#metric-control").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-metric]");
    if (!button) return;
    state.metric = button.dataset.metric;
    $$("#metric-control button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
    updateFilterUi();
    updateMap();
  });
  $("#map-mode").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-map-mode]");
    if (!button || button.disabled) return;
    state.mapMode = button.dataset.mapMode;
    $$("#map-mode button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
    updateFilterUi();
    updateMap();
    if (isPopulationMode() && !state.populationGeojson.has(state.populationResolution)) {
      loadPopulationGeometry().then(() => { if (isPopulationMode()) updateMap(); }).catch((error) => {
        console.warn(error);
        state.mapMode = "city";
        $("#map-mode button[data-map-mode='city']").click();
        $("#error-toast").textContent = "The population view is unavailable. Birthplace and country views still work.";
        $("#error-toast").classList.add("show");
      });
    }
  });
  $("#resolution-control").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-resolution]");
    if (!button) return;
    state.populationResolution = Number(button.dataset.resolution);
    $$("#resolution-control button").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
    showPopulationLoading();
    loadPopulationGeometry().then(() => { if (isPopulationMode()) updateMap(); }).catch((error) => {
      console.warn(error);
      $("#error-toast").textContent = `${populationResolutionLabel()} population areas are unavailable. Try another size.`;
      $("#error-toast").classList.add("show");
    });
  });
  $("#place-search").addEventListener("change", (event) => {
    state.placeQuery = event.target.value.trim();
    $("#clear-place-search").hidden = !state.placeQuery;
    const query = state.placeQuery.toLowerCase();
    const place = aggregatePlaces(filteredRecords()).find((item) => `${item.place}, ${item.country}`.toLowerCase() === query || item.place.toLowerCase() === query);
    if (!place) return;
    if (state.mapMode !== "city") $("#map-mode button[data-map-mode='city']").click();
    setTimeout(() => {
      revealPlaceMarker(state.placeMarkers.get(place.key));
    }, 40);
    updateFilterUi();
  });
  $("#clear-place-search").addEventListener("click", () => { state.placeQuery = ""; $("#place-search").value = ""; $("#clear-place-search").hidden = true; updateFilterUi(); });
  $("#player-search").addEventListener("input", (event) => { state.search = event.target.value; state.playerLimit = PLAYER_BATCH; updatePlayerTable(); updateFilterUi(); });
  $("#load-more-players").addEventListener("click", () => { state.playerLimit += PLAYER_BATCH; updatePlayerTable(); });
  $(".view-tabs").addEventListener("click", (event) => { const button = event.target.closest("button[data-view]"); if (button) setView(button.dataset.view); });
  $(".view-tabs").addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const tabs = $$(".view-tabs button[data-view]");
    const current = tabs.indexOf(document.activeElement);
    if (current < 0) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    setView(tabs[next].dataset.view, { focus: true });
  });
  document.addEventListener("click", (event) => {
    if (TEAM_STYLES && !event.target.closest("#team-picker")) $("#team-picker").open = false;
    const playerButton = event.target.closest("[data-player-id]");
    if (playerButton) { openPlayerProfile(playerButton.dataset.playerId, playerButton); return; }
    const clear = event.target.closest("[data-clear-filters]");
    if (clear) { resetAll(); return; }
    const chip = event.target.closest("[data-clear-filter]");
    if (chip) {
      const key = chip.dataset.clearFilter;
      if (key === "teams") { state.teams = []; updateTeamPicker(); }
      else { state[key] = "all"; $(`#${key}-filter`).value = "all"; }
      render();
      return;
    }
    const removeTeam = event.target.closest("[data-remove-team]");
    if (removeTeam) { state.teams = state.teams.filter((team) => team !== removeTeam.dataset.removeTeam); updateTeamPicker(); render(); return; }
    const placeButton = event.target.closest("[data-place-key]");
    if (placeButton) {
      revealPlaceMarker(state.placeMarkers.get(placeButton.dataset.placeKey));
      return;
    }
    const countryButton = event.target.closest("[data-country-code]");
    if (countryButton) {
      const layer = state.countryLayers.get(countryButton.dataset.countryCode);
      if (layer) { state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 5 }); layer.openPopup(); }
      return;
    }
    const populationButton = event.target.closest("[data-hex-id]");
    if (populationButton) {
      const layer = state.populationLayers.get(populationButton.dataset.hexId);
      if (layer) { state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 7 }); layer.openPopup(); }
    }
  });
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink); $("#methodology").scrollIntoView({ behavior: "smooth" }); }));
  $("#close-player-modal").addEventListener("click", closePlayerProfile);
  $("#player-modal").addEventListener("click", (event) => { if (event.target === $("#player-modal")) closePlayerProfile(); });
  document.addEventListener("keydown", handleModalKeydown);
  window.addEventListener("hashchange", () => setView(location.hash.slice(1), { updateHash: false }));
}

async function boot() {
  try {
    const dataResponse = await fetch(DATA_URL);
    if (!dataResponse.ok) throw new Error(`${EDITION.name} data request failed (${dataResponse.status})`);
    state.payload = await dataResponse.json();
    const workloadField = EDITION.workloadField;
    state.payload.meta.conferences ||= [EDITION.singleGroupLabel];
    state.payload.records.forEach((row) => {
      row.conference ||= EDITION.singleGroupLabel;
      row.minutes = Number(row[workloadField] || 0);
      (row.teamSplits || []).forEach((split) => {
        split.conference ||= row.conference;
        split.minutes = Number(split[workloadField] || 0);
      });
    });
    if (workloadField !== "minutes") {
      state.payload.summary.minutes = Number(state.payload.summary[workloadField] || 0);
      state.payload.summary.mapped_minutes = Number(state.payload.summary[`mapped_${workloadField}`] || 0);
      state.payload.summary.minute_coverage_pct = Number(state.payload.summary[`${workloadField.slice(0, -1)}_coverage_pct`] || 0);
    }
    try {
      const countryResponse = await fetch(COUNTRY_GEO_URL);
      if (!countryResponse.ok) throw new Error(`Country geometry request failed (${countryResponse.status})`);
      state.countryGeojson = await countryResponse.json();
    } catch (error) {
      console.warn(error);
      const countryButton = $("#map-mode button[data-map-mode='country']");
      countryButton.disabled = true;
      countryButton.title = "Country boundaries are unavailable";
      $("#error-toast").textContent = "The birthplace map is ready; country boundaries could not load.";
      $("#error-toast").classList.add("show");
    }
    prepareCountryMetadata();
    populateFilters();
    const mapHandoff = applyMapHandoff();
    if (state.mapMode === "country" && !state.countryGeojson) state.mapMode = "city";
    initMap();
    bindEvents();
    updateSnapshotCopy();
    updateQuality();
    setView(location.hash.slice(1) || DEFAULT_VIEW, { updateHash: false });
    if (isPopulationMode()) {
      try {
        await loadPopulationGeometry();
      } catch (error) {
        console.warn(error);
        state.mapMode = "city";
      }
    }
    render();
    if (mapHandoff?.viewport) state.map.setView([mapHandoff.viewport.lat, mapHandoff.viewport.lon], mapHandoff.viewport.zoom);
    window.TalentGeoNavigation?.mountMapSwitcher(currentMapHandoff);
    $("#loading-screen").classList.add("hidden");
  } catch (error) {
    console.error(error);
    $("#loading-screen").classList.add("hidden");
    $("#error-toast").innerHTML = `${escapeHtml(EDITION.name)} data could not load. <button type="button" onclick="location.reload()">Retry</button>`;
    $("#error-toast").classList.add("show");
  }
}

boot();
