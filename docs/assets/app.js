const DATA_URL = "./data/dashboard.json";
const COUNTRY_GEO_URL = "./data/countries.geojson";
const POPULATION_GEO_URL = "./data/population_hexes.geojson";
const AGE_AS_OF = new Date("2026-06-30T00:00:00Z");
const AGE_BANDS = [
  { id: "u21", label: "Under 21", min: 0, max: 20 },
  { id: "21-24", label: "21–24", min: 21, max: 24 },
  { id: "25-29", label: "25–29", min: 25, max: 29 },
  { id: "30-34", label: "30–34", min: 30, max: 34 },
  { id: "35plus", label: "35+", min: 35, max: 99 },
];
const LEAGUE_HOSTS = {
  "Premier League": "GBR",
  "La Liga": "ESP",
  Bundesliga: "DEU",
  "Serie A": "ITA",
  "Ligue 1": "FRA",
};
const POPULATION_RATE_STOPS = [
  { value: 0, colour: [51, 34, 136] },
  { value: 2, colour: [17, 112, 170] },
  { value: 5, colour: [68, 170, 153] },
  { value: 10, colour: [238, 190, 72] },
  { value: 25, colour: [238, 93, 80] },
];

const state = {
  payload: null,
  league: "all",
  team: "all",
  country: "all",
  ageBand: "all",
  ageChartMode: "distribution",
  ageGroupMode: "league",
  placeQuery: "",
  mapMode: "city",
  years: new Set(),
  metric: "starts",
  view: "map",
  search: "",
  playerLimit: 150,
  map: null,
  markerLayer: null,
  placeMarkers: new Map(),
  countryGeojson: null,
  countryMetadataAvailable: false,
  countryLayer: null,
  countryLayers: new Map(),
  populationGeojson: null,
  populationPromise: null,
  populationUnavailable: false,
  populationLayer: null,
  populationLayers: new Map(),
  profileMap: null,
  profileOpener: null,
  profilePlayerId: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const formatNumber = new Intl.NumberFormat("en-US");
const formatCompact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

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

function ageAtSeasonEnd(row) {
  if (row.dob) {
    const birth = new Date(`${row.dob}T00:00:00Z`);
    if (!Number.isNaN(birth.getTime())) {
      let age = AGE_AS_OF.getUTCFullYear() - birth.getUTCFullYear();
      if (AGE_AS_OF.getUTCMonth() < birth.getUTCMonth() || (AGE_AS_OF.getUTCMonth() === birth.getUTCMonth() && AGE_AS_OF.getUTCDate() < birth.getUTCDate())) age -= 1;
      return { age, exact: true };
    }
  }
  return row.birthYear ? { age: AGE_AS_OF.getUTCFullYear() - row.birthYear, exact: false } : { age: null, exact: false };
}

function matchesAgeBand(age, bandId = state.ageBand) {
  if (bandId === "all") return true;
  const band = AGE_BANDS.find((item) => item.id === bandId);
  return age !== null && band && age >= band.min && age <= band.max;
}

function median(values) {
  const sorted = values.filter((value) => value !== null).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function quantile(sortedValues, probability) {
  if (!sortedValues.length) return null;
  const index = (sortedValues.length - 1) * probability;
  const lower = Math.floor(index);
  const fraction = index - lower;
  return sortedValues[lower + 1] === undefined
    ? sortedValues[lower]
    : sortedValues[lower] + fraction * (sortedValues[lower + 1] - sortedValues[lower]);
}

function densityBandwidth(values) {
  if (values.length < 2) return 1.2;
  const sorted = [...values].sort((a, b) => a - b);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const deviation = Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1));
  const iqr = quantile(sorted, .75) - quantile(sorted, .25);
  const robustSpread = iqr > 0 ? Math.min(deviation, iqr / 1.34) : deviation;
  const bandwidth = .9 * (robustSpread || 1.5) * values.length ** (-.2);
  return Math.max(.75, Math.min(2.5, bandwidth));
}

function ageComparisonGroups(records) {
  if (state.ageGroupMode === "league") {
    const leagues = state.league === "all" ? state.payload.meta.leagues : [state.league];
    return leagues.map((league) => {
      const players = aggregatePlayers(records.filter((row) => row.league === league)).filter((player) => player.age !== null);
      return { name: league, detail: "League", players, ages: players.map((player) => player.age) };
    }).filter((group) => group.players.length);
  }
  const clubs = [...new Set(records.map((row) => row.team))].sort((a, b) => a.localeCompare(b));
  return clubs.map((club) => {
    const clubRecords = records.filter((row) => row.team === club);
    const players = aggregatePlayers(clubRecords).filter((player) => player.age !== null);
    return { name: club, detail: clubRecords[0]?.league || "Club", players, ages: players.map((player) => player.age) };
  }).filter((group) => group.players.length)
    .sort((a, b) => median(a.ages) - median(b.ages) || a.name.localeCompare(b.name));
}

function densitySeries(ages, minimum, maximum) {
  const bandwidth = densityBandwidth(ages);
  const points = Array.from({ length: 81 }, (_, index) => {
    const age = minimum + (maximum - minimum) * index / 80;
    const density = ages.reduce((sum, value) => {
      const scaled = (age - value) / bandwidth;
      return sum + Math.exp(-.5 * scaled ** 2) / Math.sqrt(2 * Math.PI);
    }, 0) / (ages.length * bandwidth);
    return { age, density };
  });
  return { bandwidth, points };
}

function prepareCountryMetadata() {
  const lookup = new Map();
  const fields = ["ADMIN", "NAME", "NAME_LONG", "SOVEREIGNT", "BRK_NAME", "FORMAL_EN"];
  (state.countryGeojson?.features || []).forEach((feature) => {
    const properties = feature.properties;
    const meta = { code: properties.ADM0_A3, continent: properties.CONTINENT, name: properties.ADMIN };
    fields.forEach((field) => { if (properties[field]) lookup.set(normalCountry(properties[field]), meta); });
  });
  state.countryMetadataAvailable = lookup.size > 0;
  const manualContinents = { faroeislands: "Europe", guernsey: "Europe", monaco: "Europe" };
  state.payload.records.forEach((row) => {
    const normalized = normalCountry(row.country);
    const meta = lookup.get(normalized);
    row.countryCode = meta?.code || normalized;
    row.continent = meta?.continent || manualContinents[normalized] || "Unclassified";
    const age = ageAtSeasonEnd(row);
    row.age = age.age;
    row.ageExact = age.exact;
  });
}

function metricLabel(metric = state.metric) {
  return { starts: "starts", starters: "players with 1+ start", players: "players" }[metric];
}

function emptyState(message, action = "Clear filters") {
  return `<div class="empty-state"><p>${escapeHtml(message)}</p><button type="button" class="empty-state-action" data-clear-filters>${escapeHtml(action)}</button></div>`;
}

function filteredRecords({ ignoreTeam = false, ignoreAge = false } = {}) {
  return state.payload.records.filter((row) =>
    state.years.has(row.year)
    && (state.league === "all" || row.league === state.league)
    && (state.country === "all" || row.country === state.country)
    && (ignoreAge || matchesAgeBand(row.age))
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
    if (!place.playerRows.has(row.id)) place.playerRows.set(row.id, { id: row.id, name: row.name, starts: 0, teams: new Set() });
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
      players.set(row.id, { id: row.id, name: row.name, teams: new Set(), leagues: new Set(), positions: new Set(), years: new Set(), starts: 0, subs: 0, apps: 0, minutes: 0, goals: 0, assists: 0, dob: row.dob, birthYear: row.birthYear, age: row.age, ageExact: row.ageExact, nation: row.nation, place: row.place, country: row.country, continent: row.continent, lat: row.lat, lon: row.lon, mapped: row.mapped });
    }
    const player = players.get(row.id);
    player.teams.add(row.team);
    if (row.league) player.leagues.add(row.league);
    if (row.position) player.positions.add(row.position);
    player.years.add(row.year);
    player.starts += row.starts;
    player.subs += row.subs;
    player.apps += row.apps || 0;
    player.minutes += row.minutes || 0;
    player.goals += row.goals || 0;
    player.assists += row.assists || 0;
    if (row.mapped) { player.place = row.place; player.country = row.country; player.continent = row.continent; player.lat = row.lat; player.lon = row.lon; player.mapped = true; }
  });
  return [...players.values()];
}

function aggregateCountries(records) {
  const countries = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    const key = row.countryCode || normalCountry(row.country);
    if (!countries.has(key)) countries.set(key, { code: key, country: row.country, continent: row.continent, starts: 0, players: new Set(), starters: new Set() });
    const country = countries.get(key);
    country.starts += row.starts;
    country.players.add(row.id);
    if (row.starts > 0) country.starters.add(row.id);
  });
  return [...countries.values()].map((country) => ({ ...country, players: country.players.size, starters: country.starters.size }));
}

function aggregatePopulationCells(records) {
  const players = new Map();
  records.filter((row) => row.mapped).forEach((row) => {
    if (!players.has(row.id)) players.set(row.id, row);
  });
  return (state.populationGeojson?.features || []).map((feature) => {
    const selected = (feature.properties.player_ids || []).filter((playerId) => players.has(playerId));
    if (!selected.length) return null;
    const places = new Map();
    const countries = new Map();
    selected.forEach((playerId) => {
      const row = players.get(playerId);
      if (row.place) places.set(row.place, (places.get(row.place) || 0) + 1);
      if (row.country) countries.set(row.country, (countries.get(row.country) || 0) + 1);
    });
    const leadingPlace = [...places.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || feature.properties.label;
    const leadingCountry = [...countries.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || feature.properties.country;
    const population = feature.properties.population;
    return {
      feature,
      hexId: feature.properties.hex_id,
      players: selected.length,
      population,
      rate: population ? selected.length / population * 1_000_000 : null,
      stable: selected.length >= 2 && population >= 100_000,
      label: leadingPlace,
      country: leadingCountry,
    };
  }).filter(Boolean);
}

async function loadPopulationGeometry() {
  if (state.populationGeojson) return state.populationGeojson;
  if (state.populationUnavailable) throw new Error("Population geometry is unavailable");
  if (!state.populationPromise) {
    state.populationPromise = fetch(POPULATION_GEO_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`Population geometry request failed (${response.status})`);
        return response.json();
      })
      .then((geojson) => {
        state.populationGeojson = geojson;
        return geojson;
      })
      .catch((error) => {
        state.populationUnavailable = true;
        state.populationPromise = null;
        throw error;
      });
  }
  return state.populationPromise;
}

function populationRateColour(rate) {
  if (rate === null) return "#26352f";
  const clamped = Math.max(0, Math.min(rate, POPULATION_RATE_STOPS.at(-1).value));
  const upperIndex = POPULATION_RATE_STOPS.findIndex((stop) => clamped <= stop.value);
  if (upperIndex <= 0) return `rgb(${POPULATION_RATE_STOPS[0].colour.join(",")})`;
  const lower = POPULATION_RATE_STOPS[upperIndex - 1];
  const upper = POPULATION_RATE_STOPS[upperIndex];
  const progress = (clamped - lower.value) / (upper.value - lower.value);
  const colour = lower.colour.map((channel, index) => Math.round(channel + (upper.colour[index] - channel) * progress));
  return `rgb(${colour.join(",")})`;
}

function aggregateLeagues(records) {
  const leagues = new Map();
  records.forEach((row) => {
    if (!leagues.has(row.league)) leagues.set(row.league, { league: row.league, players: new Set(), playerCountries: new Map(), playerAges: new Map() });
    const league = leagues.get(row.league);
    league.players.add(row.id);
    if (row.age !== null && !league.playerAges.has(row.id)) league.playerAges.set(row.id, row.age);
    if (row.mapped && !league.playerCountries.has(row.id)) {
      league.playerCountries.set(row.id, { code: row.countryCode, country: row.country, continent: row.continent });
    }
  });
  return [...leagues.values()].map((league) => {
    const countryCounts = new Map();
    const continentCounts = new Map();
    let domestic = 0;
    league.playerCountries.forEach((birth) => {
      countryCounts.set(birth.country, (countryCounts.get(birth.country) || 0) + 1);
      continentCounts.set(birth.continent, (continentCounts.get(birth.continent) || 0) + 1);
      if (birth.code === LEAGUE_HOSTS[league.league]) domestic += 1;
    });
    const mapped = league.playerCountries.size;
    const ages = [...league.playerAges.values()];
    const probabilities = [...countryCounts.values()].map((count) => count / mapped);
    const entropy = probabilities.length > 1
      ? -probabilities.reduce((sum, probability) => sum + probability * Math.log(probability), 0) / Math.log(probabilities.length)
      : 0;
    return {
      league: league.league,
      players: league.players.size,
      mapped,
      domesticPct: mapped ? (domestic / mapped) * 100 : 0,
      countries: countryCounts.size,
      continents: continentCounts.size,
      diversity: entropy * 100,
      medianAge: median(ages),
      under21Pct: ages.length ? ages.filter((age) => age < 21).length / ages.length * 100 : 0,
      over30Pct: ages.length ? ages.filter((age) => age >= 30).length / ages.length * 100 : 0,
      topCountries: [...countryCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4),
      continentCounts: [...continentCounts.entries()].sort((a, b) => b[1] - a[1]),
    };
  }).sort((a, b) => b.diversity - a.diversity);
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
  if ($("#kpi-teams")) $("#kpi-teams").textContent = formatNumber.format(teams.size);
  if ($("#kpi-players")) $("#kpi-players").textContent = formatNumber.format(players.length);
  if ($("#kpi-starts")) $("#kpi-starts").textContent = formatNumber.format(records.reduce((sum, row) => sum + row.starts, 0));
  if ($("#kpi-places")) $("#kpi-places").textContent = formatNumber.format(places.length);
  if ($("#kpi-coverage")) $("#kpi-coverage").textContent = players.length ? `${((mapped / players.length) * 100).toFixed(1)}%` : "—";

  const startsCard = $("#kpi-starts")?.closest(".kpi");
  const coverageCard = $("#kpi-coverage")?.closest(".kpi");
  if (startsCard?.querySelector("span")) startsCard.querySelector("span").textContent = "Starts";
  if (coverageCard?.querySelector("span")) coverageCard.querySelector("span").textContent = "Birthplace coverage";
  if (coverageCard?.querySelector("small")) coverageCard.querySelector("small").textContent = "players in selection";
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

function syncMapModeControls() {
  $$("#map-mode button").forEach((button) => {
    const active = button.dataset.mapMode === state.mapMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    if (button.dataset.mapMode === "country") button.disabled = !state.countryGeojson;
    if (button.dataset.mapMode === "population") button.disabled = state.populationUnavailable;
  });
  $("#map-explorer")?.classList.toggle("country-mode", state.mapMode !== "city");
  const metricControl = $("#metric-control");
  if (metricControl) {
    const unavailable = state.mapMode === "population";
    metricControl.classList.toggle("metric-unavailable", unavailable);
    const metricGroup = metricControl.closest(".metric-control");
    metricGroup?.classList.toggle("metric-unavailable", unavailable);
    if (metricGroup) metricGroup.hidden = unavailable;
    else metricControl.hidden = unavailable;
    metricControl.querySelectorAll("button").forEach((button) => { button.disabled = unavailable; });
  }
}

function showPopulationLoading() {
  if (state.map?.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.map && state.countryLayer) state.map.removeLayer(state.countryLayer);
  if (state.map && state.populationLayer) state.map.removeLayer(state.populationLayer);
  if ($("#ranking-title")) $("#ranking-title").textContent = "Players per 1M people";
  if ($("#place-count")) $("#place-count").textContent = "Loading population data…";
  if ($("#place-ranking")) $("#place-ranking").innerHTML = `<li><div class="empty-state" role="status"><p>Preparing the population view…</p></div></li>`;
  if ($("#map-legend")) $("#map-legend").classList.add("population");
  if ($("#population-scale")) $("#population-scale").hidden = false;
  if ($("#legend-prefix")) $("#legend-prefix").textContent = "Hex colour =";
  if ($("#legend-metric")) $("#legend-metric").textContent = "players per 1M people";
}

function updateCityMap(places) {
  if (!state.map) initMap();
  if (state.countryLayer) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer) state.map.removeLayer(state.populationLayer);
  if (!state.map.hasLayer(state.markerLayer)) state.markerLayer.addTo(state.map);
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
    const playerRows = visiblePlayers.map((player) => `<li><button type="button" class="popup-player" data-player-id="${escapeHtml(player.id)}"><span>${escapeHtml(player.name)}</span><small>${escapeHtml(player.teams.join(", "))} · ${formatNumber.format(player.starts)} starts</small></button></li>`).join("");
    const overflow = place.playerList.length > visiblePlayers.length ? `<p class="popup-overflow">+${place.playerList.length - visiblePlayers.length} more players</p>` : "";
    marker.bindPopup(`<div class="place-popup"><strong>${escapeHtml(place.place)}, ${escapeHtml(place.country)}</strong><p>${formatNumber.format(place.starts)} starts · ${place.players} players</p><ul>${playerRows}</ul>${overflow}</div>`, { maxWidth: 340, minWidth: 250 });
    marker.on("popupopen", (event) => {
      event.popup.getElement()?.querySelectorAll(".popup-player[data-player-id]").forEach((button) => {
        button.addEventListener("click", (clickEvent) => {
          clickEvent.preventDefault();
          clickEvent.stopPropagation();
          openPlayerProfile(button.dataset.playerId, button);
        });
      });
    });
    marker.addTo(state.markerLayer);
    state.placeMarkers.set(`${place.lat}|${place.lon}`, marker);
    bounds.push([place.lat, place.lon]);
  });
  if ((state.team !== "all" || state.country !== "all" || state.placeQuery) && bounds.length > 1) state.map.fitBounds(bounds, { padding: [45, 45], maxZoom: 6 });
  else if (bounds.length === 1) state.map.setView(bounds[0], 7);
  else state.map.setView([20, 4], 2);
  $("#map-legend").classList.remove("population");
  $("#population-scale").hidden = true;
  $("#legend-prefix").textContent = "Circle size =";
  $("#legend-metric").textContent = metricLabel();
  setTimeout(() => state.map.invalidateSize(), 80);
}

function updateCountryMap(records) {
  if (!state.map) initMap();
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.countryLayer) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer) state.map.removeLayer(state.populationLayer);
  const countries = aggregateCountries(records);
  const byCode = new Map(countries.map((country) => [country.code, country]));
  const maxValue = Math.max(...countries.map(selectedMetric), 1);
  state.countryLayers = new Map();
  state.countryLayer = L.geoJSON(state.countryGeojson, {
    style: (feature) => {
      const country = byCode.get(feature.properties.ADM0_A3);
      const scale = country ? Math.sqrt(selectedMetric(country) / maxValue) : 0;
      return { color: "#3c544b", weight: .65, fillColor: country ? "#d9ff57" : "#13251f", fillOpacity: country ? .15 + scale * .72 : .12 };
    },
    onEachFeature: (feature, layer) => {
      const code = feature.properties.ADM0_A3;
      const country = byCode.get(code);
      const name = country?.country || feature.properties.ADMIN;
      const detail = country ? `${formatNumber.format(selectedMetric(country))} ${metricLabel()} · ${country.players} players` : "No mapped players";
      layer.bindTooltip(`<strong>${escapeHtml(name)}</strong><br>${escapeHtml(detail)}`, { sticky: true });
      layer.on("click", () => state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 5 }));
      state.countryLayers.set(code, layer);
    },
  }).addTo(state.map);
  const selected = countries.find((country) => country.country === state.country);
  if (selected && state.countryLayers.has(selected.code)) state.map.fitBounds(state.countryLayers.get(selected.code).getBounds(), { padding: [35, 35], maxZoom: 5 });
  else state.map.setView([20, 4], 2);
  $("#map-legend").classList.remove("population");
  $("#population-scale").hidden = true;
  $("#legend-prefix").textContent = "Country colour =";
  $("#legend-metric").textContent = metricLabel();
  setTimeout(() => state.map.invalidateSize(), 80);
}

function updatePopulationMap(records) {
  if (!state.map) initMap();
  if (state.map.hasLayer(state.markerLayer)) state.map.removeLayer(state.markerLayer);
  if (state.countryLayer) state.map.removeLayer(state.countryLayer);
  if (state.populationLayer) state.map.removeLayer(state.populationLayer);
  const cells = aggregatePopulationCells(records);
  const byId = new Map(cells.map((cell) => [cell.hexId, cell]));
  state.populationLayers = new Map();
  state.populationLayer = L.geoJSON({ type: "FeatureCollection", features: cells.map((cell) => cell.feature) }, {
    style: (feature) => {
      const cell = byId.get(feature.properties.hex_id);
      return { color: cell.stable ? "#75958a" : "#51645d", weight: cell.stable ? .8 : .55, dashArray: cell.stable ? null : "3 3", fillColor: populationRateColour(cell.rate), fillOpacity: cell.stable ? .72 : .24 };
    },
    onEachFeature: (feature, layer) => {
      const cell = byId.get(feature.properties.hex_id);
      const rateLabel = cell.rate === null ? "Population estimate unavailable" : `${cell.rate.toFixed(1)} players per 1M`;
      const caution = cell.stable ? "" : "<br><em>Small-sample cell</em>";
      layer.bindTooltip(`<strong>${escapeHtml(cell.label)} area</strong><br>${escapeHtml(cell.country)}<br>${rateLabel}<br>${cell.players} players · population ${cell.population ? formatCompact.format(cell.population) : "unavailable"}${caution}`, { sticky: true });
      layer.bindPopup(`<div class="place-popup"><strong>${escapeHtml(cell.label)} area</strong><p>${rateLabel}</p><ul><li><span>${cell.players} mapped players</span><small>Current dashboard selection</small></li><li><span>${cell.population ? `${formatNumber.format(cell.population)} residents` : "Population unavailable"}</span><small>WorldPop 2025 · 1 km grid</small></li></ul>${cell.stable ? "" : '<p class="popup-overflow">Interpret carefully: fewer than two players, fewer than 100,000 residents, or no population estimate.</p>'}</div>`, { maxWidth: 320, minWidth: 250 });
      layer.on("click", () => state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 7 }));
      state.populationLayers.set(cell.hexId, layer);
    },
  }).addTo(state.map);
  if ((state.league !== "all" || state.team !== "all" || state.country !== "all" || state.ageBand !== "all") && cells.length) {
    state.map.fitBounds(state.populationLayer.getBounds(), { padding: [35, 35], maxZoom: 6 });
  } else state.map.setView([20, 4], 2);
  $("#map-legend").classList.add("population");
  $("#population-scale").hidden = false;
  $("#legend-prefix").textContent = "Hex colour =";
  $("#legend-metric").textContent = "players per 1M people";
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
    </button></li>`).join("") || `<li>${emptyState("No birthplaces match this selection.")}</li>`;
  $$(".place-jump").forEach((button) => button.addEventListener("click", () => {
    const lat = Number(button.dataset.lat);
    const lon = Number(button.dataset.lon);
    state.map.setView([lat, lon], 8);
    const marker = state.placeMarkers.get(`${lat}|${lon}`);
    if (marker && state.markerLayer.zoomToShowLayer) state.markerLayer.zoomToShowLayer(marker, () => marker.openPopup());
    else if (marker) setTimeout(() => marker.openPopup(), 250);
  }));
}

function updateCountryRanking(records) {
  const countries = aggregateCountries(records).sort((a, b) => selectedMetric(b) - selectedMetric(a));
  const top = countries.slice(0, 10);
  const max = top.length ? selectedMetric(top[0]) : 1;
  $("#ranking-title").textContent = `Countries by ${metricLabel()}`;
  $("#place-count").textContent = `${formatNumber.format(countries.length)} countries`;
  $("#place-ranking").innerHTML = top.map((country, index) => `
    <li class="place-row" style="--bar:${(selectedMetric(country) / max) * 100}%"><button class="place-jump country-jump" data-country-code="${escapeHtml(country.code)}" aria-label="Zoom to ${escapeHtml(country.country)}">
      <span class="place-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="place-name"><strong>${escapeHtml(country.country)}</strong><small>${escapeHtml(country.continent)}</small></span>
      <span class="place-value">${formatNumber.format(selectedMetric(country))}</span>
    </button></li>`).join("") || `<li>${emptyState("No countries match this selection.")}</li>`;
  $$(".country-jump").forEach((button) => button.addEventListener("click", () => {
    const layer = state.countryLayers.get(button.dataset.countryCode);
    if (layer) state.map.fitBounds(layer.getBounds(), { padding: [35, 35], maxZoom: 5 });
  }));
}

function updatePopulationRanking(records) {
  const cells = aggregatePopulationCells(records);
  const reliable = cells.filter((cell) => cell.stable).sort((a, b) => b.rate - a.rate);
  const top = reliable.slice(0, 10);
  const max = top[0]?.rate || 1;
  $("#ranking-title").textContent = "Players per 1M people";
  $("#place-count").textContent = `${formatNumber.format(cells.length)} local areas`;
  $("#place-ranking").innerHTML = top.map((cell, index) => `
    <li class="place-row" style="--bar:${cell.rate / max * 100}%"><button class="place-jump population-jump" data-hex-id="${escapeHtml(cell.hexId)}" aria-label="Zoom to ${escapeHtml(cell.label)} area">
      <span class="place-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="place-name"><strong>${escapeHtml(cell.label)} area</strong><small>${escapeHtml(cell.country)} · ${cell.players} players / ${formatCompact.format(cell.population)} people</small></span>
      <span class="place-value">${cell.rate.toFixed(1)}</span>
    </button></li>`).join("") || `<li>${emptyState("No reliable local areas match this selection.")}</li>`;
  $$(".population-jump").forEach((button) => button.addEventListener("click", () => {
    const layer = state.populationLayers.get(button.dataset.hexId);
    if (layer) state.map.fitBounds(layer.getBounds(), { padding: [35, 35], maxZoom: 7 });
  }));
}

function updateMapAndRanking(records, places) {
  if (state.mapMode === "population") {
    if (!state.populationGeojson) {
      showPopulationLoading();
      return;
    }
    updatePopulationMap(records);
    updatePopulationRanking(records);
  } else if (state.mapMode === "country") {
    if (!state.countryGeojson) {
      state.mapMode = "city";
      syncMapModeControls();
      updateCityMap(places);
      updateRanking(places);
      return;
    }
    updateCountryMap(records);
    updateCountryRanking(records);
  } else {
    updateCityMap(places);
    updateRanking(places);
  }
}

function updateLeagueComparison() {
  if (!state.countryMetadataAvailable) {
    $("#league-comparison").innerHTML = `<div class="empty-state comparison-unavailable" role="status"><h3>Birth-country comparison unavailable</h3><p>Country reference data could not be loaded. Club and age comparisons are still available below.</p></div>`;
    return;
  }
  const leagues = aggregateLeagues(filteredRecords());
  $("#league-comparison").innerHTML = leagues.map((league, index) => {
    const continents = league.continentCounts.map(([name, count]) => `<span>${escapeHtml(name)} <b>${count}</b></span>`).join("");
    const countries = league.topCountries.map(([name, count]) => `<li><span>${escapeHtml(name)}</span><b>${count}</b></li>`).join("");
    return `<article class="league-card" style="--order:${index}">
      <header><div><span>0${index + 1}</span><h3>${escapeHtml(league.league)}</h3></div><strong>${league.diversity.toFixed(0)}<small>/100 diversity</small></strong></header>
      <div class="league-primary"><div><b>${league.domesticPct.toFixed(1)}%</b><span>domestic-born</span></div><div><b>${league.countries}</b><span>birth countries</span></div><div><b>${league.continents}</b><span>continents</span></div></div>
      <div class="domestic-track"><i style="width:${league.domesticPct}%"></i></div>
      <div class="league-age"><span><b>${league.medianAge?.toFixed(1) ?? "—"}</b> median age</span><span><b>${league.under21Pct.toFixed(1)}%</b> U21</span><span><b>${league.over30Pct.toFixed(1)}%</b> 30+</span></div>
      <div class="league-detail"><div><span class="card-label">Leading birth countries</span><ol>${countries}</ol></div><div><span class="card-label">Continents</span><div class="continent-chips">${continents}</div></div></div>
      <div class="league-footer">${formatNumber.format(league.mapped)} of ${formatNumber.format(league.players)} players mapped</div>
    </article>`;
  }).join("") || emptyState("No league comparison matches this selection.");
}

function renderAgeBandChart(groups) {
  const rows = groups.map((group) => {
    const counts = AGE_BANDS.map((band) => group.players.filter((player) => matchesAgeBand(player.age, band.id)).length);
    const summary = AGE_BANDS.map((band, index) => {
      const percentage = group.players.length ? counts[index] / group.players.length * 100 : 0;
      return `${band.label}: ${counts[index]} players, ${percentage.toFixed(1)}%`;
    }).join("; ");
    const segments = AGE_BANDS.map((band, index) => {
      const percentage = group.players.length ? counts[index] / group.players.length * 100 : 0;
      const muted = state.ageBand !== "all" && state.ageBand !== band.id ? " muted" : "";
      return `<i class="age-${index}${muted}" style="width:${percentage}%" aria-hidden="true" title="${escapeHtml(band.label)}: ${counts[index]} players (${percentage.toFixed(1)}%)"></i>`;
    }).join("");
    return `<div class="age-league-row"><div><strong>${escapeHtml(group.name)}</strong><small>${escapeHtml(group.detail)} · ${group.players.length} players · median ${median(group.ages)?.toFixed(1) ?? "—"}</small></div><div class="age-stack" role="img" aria-label="${escapeHtml(`${group.name} age bands. ${summary}`)}">${segments}</div></div>`;
  }).join("");
  return `<div class="age-legend">${AGE_BANDS.map((band, index) => `<span><i class="age-${index}"></i>${escapeHtml(band.label)}</span>`).join("")}</div>${rows}`;
}

function renderAgeDensityChart(groups) {
  const allAges = groups.flatMap((group) => group.ages);
  if (!allAges.length) return { html: `<p class="age-chart-empty">No age data matches this selection.</p>`, bandwidths: [] };
  const minimum = Math.floor(Math.min(...allAges) - 1);
  const maximum = Math.ceil(Math.max(...allAges) + 1);
  const width = 800;
  const height = 66;
  const baseline = 59;
  const series = groups.map((group) => ({ ...group, density: densitySeries(group.ages, minimum, maximum) }));
  const peak = Math.max(...series.flatMap((group) => group.density.points.map((point) => point.density)), .001);
  const x = (age) => (age - minimum) / (maximum - minimum) * width;
  const y = (density) => baseline - density / peak * 50;
  const selectedBand = AGE_BANDS.find((band) => band.id === state.ageBand);
  const highlight = selectedBand
    ? `<rect class="density-highlight" x="${Math.max(0, x(selectedBand.min)).toFixed(1)}" y="4" width="${Math.max(0, Math.min(width, x(selectedBand.max + 1)) - Math.max(0, x(selectedBand.min))).toFixed(1)}" height="${baseline - 4}" />`
    : "";
  const ticks = [];
  for (let age = Math.ceil(minimum / 5) * 5; age <= maximum; age += 5) ticks.push(age);
  const axis = `<div class="density-axis"><span></span><div>${ticks.map((age) => `<i style="left:${x(age).toFixed(1) / width * 100}%"><b>${age}</b></i>`).join("")}</div></div>`;
  const rows = series.map((group) => {
    const line = group.density.points.map((point, index) => `${index ? "L" : "M"}${x(point.age).toFixed(1)},${y(point.density).toFixed(1)}`).join(" ");
    const area = `M0,${baseline} ${line.replace(/^M/, "L")} L${width},${baseline} Z`;
    const medianX = x(median(group.ages));
    return `<div class="age-density-row"><div><strong>${escapeHtml(group.name)}</strong><small>${escapeHtml(group.detail)} · ${group.players.length} players · median ${median(group.ages)?.toFixed(1) ?? "—"}</small></div><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Age distribution for ${escapeHtml(group.name)}">${highlight}<line class="density-baseline" x1="0" y1="${baseline}" x2="${width}" y2="${baseline}"/><path class="density-area" d="${area}"/><path class="density-line" d="${line}"/><line class="density-median" x1="${medianX.toFixed(1)}" y1="8" x2="${medianX.toFixed(1)}" y2="${baseline}"/></svg></div>`;
  }).join("");
  return { html: `${axis}${rows}`, bandwidths: series.map((group) => group.density.bandwidth) };
}

function updateAgeView() {
  // Keep the complete age context visible and use the selected age band as a
  // highlight. The age filter still applies to every other comparison/view.
  const records = filteredRecords({ ignoreAge: true });
  const players = aggregatePlayers(records).filter((player) => player.age !== null);
  const ages = players.map((player) => player.age);
  const exact = players.filter((player) => player.ageExact).length;
  $("#age-overview").innerHTML = `
    <article><span>Median age</span><strong>${median(ages)?.toFixed(1) ?? "—"}</strong><small>at 30 June 2026</small></article>
    <article><span>Under 21</span><strong>${formatNumber.format(ages.filter((age) => age < 21).length)}</strong><small>${ages.length ? (ages.filter((age) => age < 21).length / ages.length * 100).toFixed(1) : 0}% of players</small></article>
    <article><span>Age 30+</span><strong>${formatNumber.format(ages.filter((age) => age >= 30).length)}</strong><small>${ages.length ? (ages.filter((age) => age >= 30).length / ages.length * 100).toFixed(1) : 0}% of players</small></article>
    <article><span>Exact ages</span><strong>${players.length ? (exact / players.length * 100).toFixed(1) : 0}%</strong><small>remaining values approximate</small></article>`;

  const groups = ageComparisonGroups(records);
  const level = state.ageGroupMode === "league" ? "league" : "club";
  $("#age-chart-kicker").textContent = `${level === "league" ? "League" : "Club"} distribution`;
  $("#age-chart-title").textContent = `${state.ageChartMode === "distribution" ? "Age distribution" : "Age bands"} by ${level}`;
  if (state.ageChartMode === "distribution") {
    const density = renderAgeDensityChart(groups);
    $("#age-chart").innerHTML = density.html;
    $("#age-chart-meta").textContent = `Smoothed age distribution · curves share one scale${level === "club" ? " · youngest median first" : ""}`;
  } else {
    $("#age-chart").innerHTML = groups.length ? renderAgeBandChart(groups) : `<p class="age-chart-empty">No age data matches this selection.</p>`;
    $("#age-chart-meta").textContent = `Each row totals 100% of players with an available age${level === "club" ? " · youngest median first" : ""}`;
  }
  $("#age-chart").classList.toggle("club-comparison", state.ageGroupMode === "club");

  const ageLabel = (player) => `${player.ageExact ? "" : "≈"}${player.age}`;
  const playerRow = (player) => `<li><span><strong>${escapeHtml(player.name)}</strong><small>${escapeHtml([...player.teams].sort().join(", "))}</small></span><b>${ageLabel(player)}</b></li>`;
  const youngest = [...players].sort((a, b) => a.age - b.age || a.name.localeCompare(b.name)).slice(0, 10);
  const oldest = [...players].sort((a, b) => b.age - a.age || a.name.localeCompare(b.name)).slice(0, 10);
  $("#youngest-players").innerHTML = youngest.map(playerRow).join("");
  $("#oldest-players").innerHTML = oldest.map(playerRow).join("");
  const selectedBand = AGE_BANDS.find((band) => band.id === state.ageBand);
  $("#age-scope").textContent = selectedBand
    ? `${formatNumber.format(players.length)} players · ${selectedBand.label} highlighted`
    : `${formatNumber.format(players.length)} players in the current selection`;
}

function updateTeamChart() {
  const teams = aggregateTeams(filteredRecords()).sort((a, b) => b.starts - a.starts);
  const max = Math.max(...teams.map((team) => team.starts), 1);
  $("#team-chart").innerHTML = teams.map((team) => `
    <div class="team-row">
      <div class="team-name"><strong>${escapeHtml(team.team)}</strong><small>${escapeHtml(team.leagues.join(", "))}</small></div>
      <div class="team-track"><i style="width:${(team.starts / max) * 100}%"></i></div>
      <div class="team-value">${formatNumber.format(team.starts)}<small>${team.coverage.toFixed(1)}% birthplace coverage</small></div>
    </div>`).join("") || emptyState("No clubs match this selection.");
}

function updatePlayerTable() {
  const query = state.search.trim().toLowerCase();
  const players = aggregatePlayers(filteredRecords())
    .filter((player) => !query || [player.name, player.place, player.country, ...player.teams].some((value) => String(value ?? "").toLowerCase().includes(query)))
    .sort((a, b) => b.starts - a.starts || a.name.localeCompare(b.name));
  const visible = players.slice(0, state.playerLimit);
  $("#player-table").innerHTML = visible.map((player) => `
    <tr class="player-row"><td data-label="Player"><button type="button" class="player-open-button" data-player-id="${escapeHtml(player.id)}" aria-label="Open profile for ${escapeHtml(player.name)}"><strong>${escapeHtml(player.name)}</strong><small>${escapeHtml(player.dob || player.birthYear || "DOB unavailable")}</small></button></td>
    <td data-label="Club">${escapeHtml([...player.teams].sort().join(", "))}</td>
    <td data-label="League">${escapeHtml([...player.leagues].sort().join(", "))}</td>
    <td data-label="Birthplace">${player.mapped ? `${escapeHtml(player.place)}<br><small>${escapeHtml(player.country || "")}</small>` : `<span style="color:var(--danger)">Unavailable</span>`}</td>
    <td class="numeric" data-label="Apps">${formatNumber.format(player.apps)}</td><td class="numeric" data-label="Starts">${formatNumber.format(player.starts)}</td></tr>`).join("");
  const empty = $("#player-empty-state");
  if (empty) {
    empty.hidden = players.length > 0;
    empty.innerHTML = players.length ? "" : `<h3>No players found</h3><p>${escapeHtml(query ? "Try another search or clear your filters." : "This selection has no players.")}</p><button type="button" class="empty-state-action" data-clear-filters>Clear filters</button>`;
  }
  const table = $("#player-table")?.closest("table");
  if (table) table.hidden = players.length === 0;
  $("#player-table-note").textContent = players.length
    ? `Showing ${formatNumber.format(visible.length)} of ${formatNumber.format(players.length)} players in this selection`
    : "No players to show";
  const loadMore = $("#load-more-players");
  if (loadMore) {
    const remaining = Math.max(0, players.length - visible.length);
    loadMore.hidden = remaining === 0;
    loadMore.textContent = remaining ? `Show ${formatNumber.format(Math.min(150, remaining))} more` : "Show more players";
    loadMore.setAttribute("aria-label", remaining ? `Show ${Math.min(150, remaining)} more players` : "All players shown");
  }
  $$(".player-open-button").forEach((button) => {
    button.addEventListener("click", () => openPlayerProfile(button.dataset.playerId, button));
  });
}

function setBackgroundInert(inert) {
  [$(".site-header"), $("main"), $("footer")].filter(Boolean).forEach((element) => {
    element.inert = inert;
  });
}

function openPlayerProfile(playerId, opener = document.activeElement) {
  const player = aggregatePlayers(state.payload.records.filter((row) => row.id === playerId))[0];
  if (!player) return;
  $("#profile-name").textContent = player.name;
  $("#profile-meta").textContent = `${[...player.positions].sort().join(" / ") || "Position unavailable"} · ${player.nation || "Nationality unavailable"}`;
  $("#profile-clubs").textContent = [...player.teams].sort().join(" · ");
  $("#profile-leagues").textContent = [...player.leagues].sort().join(" · ");
  $("#profile-apps").textContent = formatNumber.format(player.apps);
  $("#profile-starts").textContent = formatNumber.format(player.starts);
  $("#profile-minutes").textContent = formatNumber.format(player.minutes);
  $("#profile-goals").textContent = formatNumber.format(player.goals);
  $("#profile-assists").textContent = formatNumber.format(player.assists);
  $("#profile-birthplace").textContent = player.mapped ? `${player.place}, ${player.country}` : "Birthplace awaiting QA";
  $("#profile-dob").textContent = player.dob || player.birthYear || "Unavailable";
  $("#profile-age").textContent = player.age === null ? "Age unavailable" : `${player.ageExact ? "" : "≈ "}${player.age} years at season end`;
  state.profileOpener = opener instanceof HTMLElement && !$("#player-modal").contains(opener) ? opener : document.activeElement;
  state.profilePlayerId = String(playerId);
  setBackgroundInert(true);
  $("#player-modal").classList.add("open");
  $("#player-modal").setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
  $("#profile-map-empty").hidden = player.mapped;
  $("#player-mini-map").hidden = !player.mapped;
  if (player.mapped) {
    setTimeout(() => {
      if (!$("#player-modal").classList.contains("open") || state.profilePlayerId !== String(playerId)) return;
      state.profileMap = L.map("player-mini-map", { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false }).setView([player.lat, player.lon], 6);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd" }).addTo(state.profileMap);
      L.circleMarker([player.lat, player.lon], { radius: 8, color: "#d9ff57", fillColor: "#d9ff57", fillOpacity: .7 }).addTo(state.profileMap);
    }, 80);
  }
  $("#close-player-modal").focus();
}

function closePlayerProfile() {
  const opener = state.profileOpener;
  const fallback = $(`.view-tabs button[data-view="${state.view}"]`);
  setBackgroundInert(false);
  const focusTarget = opener?.isConnected ? opener : fallback;
  focusTarget?.focus({ preventScroll: true });
  $("#player-modal").classList.remove("open");
  $("#player-modal").setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
  state.profilePlayerId = null;
  state.profileOpener = null;
}

function handleModalKeydown(event) {
  const modal = $("#player-modal");
  if (!modal?.classList.contains("open")) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closePlayerProfile();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...modal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
    .filter((element) => !element.hidden && element.getClientRects().length);
  if (!focusable.length) {
    event.preventDefault();
    modal.focus();
    return;
  }
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
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
  const age = state.ageBand === "all" ? "All ages" : AGE_BANDS.find((band) => band.id === state.ageBand)?.label;
  $("#filter-summary").textContent = `${league} · ${team} · ${country} · ${age}`;
}

function updateActiveFilters() {
  const container = $("#active-filters");
  if (!container) return;
  const filters = [
    state.league !== "all" && { key: "league", label: `League: ${state.league}` },
    state.team !== "all" && { key: "team", label: `Club: ${state.team}` },
    state.country !== "all" && { key: "country", label: `Born in: ${state.country}` },
    state.ageBand !== "all" && { key: "age", label: `Age: ${AGE_BANDS.find((band) => band.id === state.ageBand)?.label || state.ageBand}` },
  ].filter(Boolean);
  container.innerHTML = filters.map((filter) => `<button type="button" class="filter-chip" data-clear-filter="${filter.key}" aria-label="Remove ${escapeHtml(filter.label)} filter"><span>${escapeHtml(filter.label)}</span><span aria-hidden="true">×</span></button>`).join("");
  container.hidden = filters.length === 0;
  const moreCount = $("#more-filter-count");
  if (moreCount) {
    const count = Number(state.country !== "all") + Number(state.ageBand !== "all");
    moreCount.textContent = count ? String(count) : "";
    moreCount.setAttribute("aria-label", count ? `${count} active ${count === 1 ? "filter" : "filters"}` : "No active filters");
  }
  const resetButton = $("#reset-filters");
  if (resetButton) {
    const hasNonDefaultState = filters.length > 0
      || Boolean(state.search.trim())
      || Boolean(state.placeQuery.trim())
      || state.metric !== "starts"
      || state.mapMode !== "city"
      || state.ageChartMode !== "distribution"
      || state.ageGroupMode !== "league";
    resetButton.disabled = !hasNonDefaultState;
  }
}

function updateSnapshotCopy() {
  const { meta, summary } = state.payload;
  const generated = new Date(meta.generated_at);
  const updated = Number.isNaN(generated.getTime())
    ? ""
    : generated.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric", timeZone: "Australia/Melbourne" });
  const status = $(".status-pill");
  if (status && updated) {
    status.innerHTML = `<i aria-hidden="true"></i> 2025–26 · Updated ${escapeHtml(updated)}`;
    status.title = `Dataset generated ${updated}`;
  }
  const statline = $(".hero-statline");
  if (statline) {
    statline.innerHTML = `<strong>${formatNumber.format(summary.players)} players</strong><span>${formatNumber.format(summary.teams)} clubs</span><span>${formatNumber.format(meta.leagues.length)} leagues</span>`;
  }
}

function filteredPlaces() {
  const query = state.placeQuery.trim().toLowerCase();
  return aggregatePlaces(filteredRecords()).filter((place) =>
    !query || `${place.place} ${place.country}`.toLowerCase().includes(query)
  );
}

function renderMapExplorer() {
  const records = filteredRecords();
  const places = filteredPlaces();
  const clearPlaceButton = $("#clear-place-search");
  const hasPlaceQuery = Boolean(state.placeQuery.trim());
  if (clearPlaceButton) clearPlaceButton.hidden = !hasPlaceQuery;
  $("#map-explorer")?.classList.toggle("has-place-query", hasPlaceQuery);
  updateActiveFilters();
  updateMapAndRanking(records, places);
}

function render() {
  const records = filteredRecords();
  const allPlaces = aggregatePlaces(records);
  const query = state.placeQuery.trim().toLowerCase();
  const places = allPlaces.filter((place) => !query || `${place.place} ${place.country}`.toLowerCase().includes(query));
  updateKpis(records, allPlaces);
  updateFilterSummary();
  updateActiveFilters();
  updateMapAndRanking(records, places);
  updateLeagueComparison();
  updateAgeView();
  updateTeamChart();
  updatePlayerTable();
  updateQuality();
}

function setView(view, { scroll = true, updateHash = true, focusTab = false } = {}) {
  const hashView = view === "methodology" ? "quality" : view;
  const requested = hashView === "age" && !$("#view-age") ? "teams" : hashView;
  const button = $(`.view-tabs button[data-view="${requested}"]`);
  const panel = $(`#view-${requested}`);
  if (!button || !panel) return;
  state.view = requested;
  $$(".view-tabs button").forEach((item) => {
    const active = item === button;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
  });
  $$(".view-panel").forEach((item) => {
    const active = item === panel;
    item.classList.toggle("active", active);
    item.hidden = !active;
  });
  if (requested === "map" && state.map) setTimeout(() => state.map.invalidateSize(), 100);
  if (updateHash && window.location.hash !== `#${requested}`) history.replaceState(null, "", `#${requested}`);
  if (focusTab) button.focus();
  if (scroll) $(".view-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function syncPressedButtons(selector, dataKey, value) {
  $$(selector).forEach((button) => {
    const active = button.dataset[dataKey] === value;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function resetAllFilters() {
  state.league = "all";
  state.team = "all";
  state.country = "all";
  state.ageBand = "all";
  state.placeQuery = "";
  state.search = "";
  state.years = new Set(state.payload.meta.years);
  state.metric = "starts";
  state.mapMode = "city";
  state.ageChartMode = "distribution";
  state.ageGroupMode = "league";
  state.playerLimit = 150;
  if ($("#league-filter")) $("#league-filter").value = "all";
  populateTeamOptions();
  if ($("#team-filter")) $("#team-filter").value = "all";
  if ($("#country-filter")) $("#country-filter").value = "all";
  if ($("#age-filter")) $("#age-filter").value = "all";
  if ($("#place-search")) $("#place-search").value = "";
  if ($("#player-search")) $("#player-search").value = "";
  if ($("#more-filters")) $("#more-filters").open = false;
  syncPressedButtons("#metric-control button", "metric", state.metric);
  syncPressedButtons("#age-chart-mode button", "ageChart", state.ageChartMode);
  syncPressedButtons("#age-group-mode button", "ageGroup", state.ageGroupMode);
  syncMapModeControls();
  render();
}

function clearFilter(key) {
  if (key === "league") {
    state.league = "all";
    $("#league-filter").value = "all";
    populateTeamOptions();
    $("#team-filter").value = state.team;
  } else if (key === "team") {
    state.team = "all";
    $("#team-filter").value = "all";
  } else if (key === "country") {
    state.country = "all";
    $("#country-filter").value = "all";
  } else if (key === "age") {
    state.ageBand = "all";
    $("#age-filter").value = "all";
  } else if (key === "place") {
    state.placeQuery = "";
    $("#place-search").value = "";
  } else return;
  state.playerLimit = 150;
  render();
}

async function activateMapMode(mode) {
  if (mode === "country" && !state.countryGeojson) return;
  if (mode === "population" && state.populationUnavailable) return;
  if (mode !== "city" && state.placeQuery) {
    state.placeQuery = "";
    if ($("#place-search")) $("#place-search").value = "";
  }
  state.mapMode = mode;
  syncMapModeControls();
  renderMapExplorer();
  if (mode !== "population" || state.populationGeojson) return;
  try {
    await loadPopulationGeometry();
    if (state.mapMode === "population") renderMapExplorer();
  } catch (error) {
    console.error(error);
    if (state.mapMode === "population") {
      state.mapMode = "city";
      syncMapModeControls();
      renderMapExplorer();
    }
    showToast("The population view is unavailable right now. Birthplace and country views still work.");
  }
}

function bindControls() {
  $("#map-mode")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-map-mode]");
    if (!button || button.disabled) return;
    activateMapMode(button.dataset.mapMode);
  });
  $("#league-filter")?.addEventListener("change", (event) => {
    state.league = event.target.value;
    state.team = "all";
    state.playerLimit = 150;
    populateTeamOptions();
    render();
  });
  $("#team-filter")?.addEventListener("change", (event) => { state.team = event.target.value; state.playerLimit = 150; render(); });
  $("#age-filter")?.addEventListener("change", (event) => { state.ageBand = event.target.value; state.playerLimit = 150; render(); });
  $("#age-chart-mode")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-age-chart]");
    if (!button) return;
    state.ageChartMode = button.dataset.ageChart;
    $$("#age-chart-mode button").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    });
    updateAgeView();
    updateActiveFilters();
  });
  $("#age-group-mode")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-age-group]");
    if (!button) return;
    state.ageGroupMode = button.dataset.ageGroup;
    $$("#age-group-mode button").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    });
    updateAgeView();
    updateActiveFilters();
  });
  $("#country-filter")?.addEventListener("change", (event) => { state.country = event.target.value; state.playerLimit = 150; render(); });
  $("#place-search")?.addEventListener("input", (event) => { state.placeQuery = event.target.value; renderMapExplorer(); });
  $("#clear-place-search")?.addEventListener("click", () => {
    state.placeQuery = "";
    $("#place-search").value = "";
    renderMapExplorer();
  });
  $("#metric-control")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-metric]");
    if (!button) return;
    state.metric = button.dataset.metric;
    syncPressedButtons("#metric-control button", "metric", state.metric);
    renderMapExplorer();
  });
  $("#reset-filters")?.addEventListener("click", resetAllFilters);
  const tabs = $$(".view-tabs button[data-view]");
  tabs.forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const current = tabs.indexOf(button);
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      setView(tabs[next].dataset.view, { scroll: false, focusTab: true });
    });
  });
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink, { focusTab: true }); }));
  $("#player-search")?.addEventListener("input", (event) => { state.search = event.target.value; state.playerLimit = 150; updatePlayerTable(); updateActiveFilters(); });
  $("#load-more-players")?.addEventListener("click", () => { state.playerLimit += 150; updatePlayerTable(); });
  $("#close-player-modal")?.addEventListener("click", closePlayerProfile);
  $("#player-modal")?.addEventListener("click", (event) => { if (event.target === event.currentTarget) closePlayerProfile(); });
  document.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-clear-filter]");
    if (chip) clearFilter(chip.dataset.clearFilter);
    const clear = event.target.closest("[data-clear-filters]");
    if (clear) resetAllFilters();
    const popupPlayer = event.target.closest(".popup-player[data-player-id]");
    if (popupPlayer) {
      event.preventDefault();
      event.stopPropagation();
      openPlayerProfile(popupPlayer.dataset.playerId, popupPlayer);
    }
  });
  document.addEventListener("keydown", handleModalKeydown);
  window.addEventListener("hashchange", () => {
    const view = window.location.hash.slice(1);
    if (view) setView(view, { scroll: false, updateHash: false });
  });
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

function showToast(message) {
  const toast = $("#error-toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 6000);
}

function showError(message) {
  showToast(message);
  $("#loading-screen")?.classList.add("hidden");
}

async function boot() {
  try {
    const countryRequest = fetch(COUNTRY_GEO_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`Country geometry request failed (${response.status})`);
        return response.json();
      })
      .then((geojson) => ({ geojson, error: null }))
      .catch((error) => ({ geojson: null, error }));
    const [response, countryResult] = await Promise.all([fetch(DATA_URL), countryRequest]);
    if (!response.ok) throw new Error(`Dataset request failed (${response.status})`);
    state.payload = await response.json();
    state.countryGeojson = countryResult.geojson;
    if (countryResult.error) console.error(countryResult.error);
    prepareCountryMetadata();
    populateControls();
    updateSnapshotCopy();
    bindControls();
    syncMapModeControls();
    render();
    const initialView = window.location.hash.slice(1) || "map";
    setView(initialView, { scroll: false, updateHash: false });
    $("#loading-screen")?.classList.add("hidden");
    if (countryResult.error) showToast("Country boundaries could not be loaded. The rest of the dashboard is available.");
  } catch (error) {
    console.error(error);
    showError("The dashboard data could not be loaded. Please refresh or try again shortly.");
  }
}

boot();
