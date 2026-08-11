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
  map: null,
  markerLayer: null,
  placeMarkers: new Map(),
  countryGeojson: null,
  countryLayer: null,
  countryLayers: new Map(),
  populationGeojson: null,
  populationLayer: null,
  populationLayers: new Map(),
  profileMap: null,
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
  state.countryGeojson.features.forEach((feature) => {
    const properties = feature.properties;
    const meta = { code: properties.ADM0_A3, continent: properties.CONTINENT, name: properties.ADMIN };
    fields.forEach((field) => { if (properties[field]) lookup.set(normalCountry(properties[field]), meta); });
  });
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
  return { starts: "starts", starters: "unique starters", players: "players" }[metric];
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
  return state.populationGeojson.features.map((feature) => {
    const selected = feature.properties.player_ids.filter((playerId) => players.has(playerId));
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
  const reliableRates = cells.filter((cell) => cell.stable).map((cell) => cell.rate).sort((a, b) => a - b);
  const availableRates = cells.map((cell) => cell.rate).filter((rate) => rate !== null);
  const cap = reliableRates[Math.floor((reliableRates.length - 1) * .95)] || Math.max(...availableRates, 1);
  const palette = ["#173128", "#22563f", "#347d54", "#5fbf71", "#d9ff57"];
  state.populationLayers = new Map();
  state.populationLayer = L.geoJSON({ type: "FeatureCollection", features: cells.map((cell) => cell.feature) }, {
    style: (feature) => {
      const cell = byId.get(feature.properties.hex_id);
      const scale = cell.rate === null ? 0 : Math.min(cell.rate / cap, 1);
      const colour = palette[Math.min(palette.length - 1, Math.floor(scale * palette.length))];
      return { color: cell.stable ? "#75958a" : "#51645d", weight: cell.stable ? .8 : .55, dashArray: cell.stable ? null : "3 3", fillColor: colour, fillOpacity: cell.stable ? .2 + scale * .62 : .2 };
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
    </button></li>`).join("");
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
  $("#place-count").textContent = `${formatNumber.format(cells.length)} occupied hexes`;
  $("#place-ranking").innerHTML = top.map((cell, index) => `
    <li class="place-row" style="--bar:${cell.rate / max * 100}%"><button class="place-jump population-jump" data-hex-id="${escapeHtml(cell.hexId)}" aria-label="Zoom to ${escapeHtml(cell.label)} area">
      <span class="place-rank">${String(index + 1).padStart(2, "0")}</span>
      <span class="place-name"><strong>${escapeHtml(cell.label)} area</strong><small>${escapeHtml(cell.country)} · ${cell.players} players / ${formatCompact.format(cell.population)} people</small></span>
      <span class="place-value">${cell.rate.toFixed(1)}</span>
    </button></li>`).join("") || `<li class="place-row"><span class="place-name"><strong>No stable cells match this selection</strong><small>Rankings require at least two players and 100,000 residents.</small></span></li>`;
  $$(".population-jump").forEach((button) => button.addEventListener("click", () => {
    const layer = state.populationLayers.get(button.dataset.hexId);
    if (layer) state.map.fitBounds(layer.getBounds(), { padding: [35, 35], maxZoom: 7 });
  }));
}

function updateMapAndRanking(records, places) {
  if (state.mapMode === "population") {
    updatePopulationMap(records);
    updatePopulationRanking(records);
  } else if (state.mapMode === "country") {
    updateCountryMap(records);
    updateCountryRanking(records);
  } else {
    updateCityMap(places);
    updateRanking(places);
  }
}

function updateLeagueComparison() {
  const leagues = aggregateLeagues(state.payload.records);
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
  }).join("");
}

function renderAgeBandChart(groups) {
  const rows = groups.map((group) => {
    const counts = AGE_BANDS.map((band) => group.players.filter((player) => matchesAgeBand(player.age, band.id)).length);
    const segments = AGE_BANDS.map((band, index) => {
      const percentage = group.players.length ? counts[index] / group.players.length * 100 : 0;
      const muted = state.ageBand !== "all" && state.ageBand !== band.id ? " muted" : "";
      return `<i class="age-${index}${muted}" style="width:${percentage}%" title="${escapeHtml(band.label)}: ${counts[index]} players (${percentage.toFixed(1)}%)"></i>`;
    }).join("");
    return `<div class="age-league-row"><div><strong>${escapeHtml(group.name)}</strong><small>${escapeHtml(group.detail)} · ${group.players.length} players · median ${median(group.ages)?.toFixed(1) ?? "—"}</small></div><div class="age-stack">${segments}</div></div>`;
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
    return `<div class="age-density-row"><div><strong>${escapeHtml(group.name)}</strong><small>${escapeHtml(group.detail)} · ${group.players.length} players · median ${median(group.ages)?.toFixed(1) ?? "—"} · h ${group.density.bandwidth.toFixed(1)}</small></div><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Age distribution for ${escapeHtml(group.name)}">${highlight}<line class="density-baseline" x1="0" y1="${baseline}" x2="${width}" y2="${baseline}"/><path class="density-area" d="${area}"/><path class="density-line" d="${line}"/><line class="density-median" x1="${medianX.toFixed(1)}" y1="8" x2="${medianX.toFixed(1)}" y2="${baseline}"/></svg></div>`;
  }).join("");
  return { html: `${axis}${rows}`, bandwidths: series.map((group) => group.density.bandwidth) };
}

function updateAgeView() {
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
    const low = density.bandwidths.length ? Math.min(...density.bandwidths).toFixed(1) : "—";
    const high = density.bandwidths.length ? Math.max(...density.bandwidths).toFixed(1) : "—";
    $("#age-chart-meta").textContent = `Kernel density estimate · automatic Silverman bandwidth ${low}${low === high ? "" : `–${high}`} years · curves share one scale${level === "club" ? " · youngest median first" : ""}`;
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
  $("#age-scope").textContent = `${formatNumber.format(players.length)} players in the current league, club and birthplace scope`;
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
    <tr class="player-row" data-player-id="${escapeHtml(player.id)}" tabindex="0"><td><strong>${escapeHtml(player.name)}</strong><br><small>${escapeHtml(player.dob || player.birthYear || "DOB unavailable")}</small></td>
    <td>${escapeHtml([...player.teams].sort().join(", "))}</td>
    <td>${escapeHtml([...player.leagues].sort().join(", "))}</td>
    <td>${player.mapped ? `${escapeHtml(player.place)}<br><small>${escapeHtml(player.country || "")}</small>` : `<span style="color:var(--danger)">QA pending</span>`}</td>
    <td class="numeric">${formatNumber.format(player.apps)}</td><td class="numeric">${formatNumber.format(player.starts)}</td></tr>`).join("");
  $("#player-table-note").textContent = `Showing ${formatNumber.format(visible.length)} of ${formatNumber.format(players.length)} players in this selection`;
  $$(".player-row").forEach((row) => {
    row.addEventListener("click", () => openPlayerProfile(row.dataset.playerId));
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openPlayerProfile(row.dataset.playerId); } });
  });
}

function openPlayerProfile(playerId) {
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
  $("#player-modal").classList.add("open");
  $("#player-modal").setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
  $("#profile-map-empty").hidden = player.mapped;
  $("#player-mini-map").hidden = !player.mapped;
  if (player.mapped) {
    setTimeout(() => {
      state.profileMap = L.map("player-mini-map", { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false }).setView([player.lat, player.lon], 6);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, subdomains: "abcd" }).addTo(state.profileMap);
      L.circleMarker([player.lat, player.lon], { radius: 8, color: "#d9ff57", fillColor: "#d9ff57", fillOpacity: .7 }).addTo(state.profileMap);
    }, 80);
  }
  $("#close-player-modal").focus();
}

function closePlayerProfile() {
  $("#player-modal").classList.remove("open");
  $("#player-modal").setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  if (state.profileMap) state.profileMap.remove();
  state.profileMap = null;
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

function filteredPlaces() {
  const query = state.placeQuery.trim().toLowerCase();
  return aggregatePlaces(filteredRecords()).filter((place) =>
    !query || `${place.place} ${place.country}`.toLowerCase().includes(query)
  );
}

function renderMapExplorer() {
  const records = filteredRecords();
  const places = filteredPlaces();
  updateMapAndRanking(records, places);
}

function render() {
  const records = filteredRecords();
  const allPlaces = aggregatePlaces(records);
  const query = state.placeQuery.trim().toLowerCase();
  const places = allPlaces.filter((place) => !query || `${place.place} ${place.country}`.toLowerCase().includes(query));
  updateKpis(records, allPlaces);
  updateFilterSummary();
  updateMapAndRanking(records, places);
  updateLeagueComparison();
  updateAgeView();
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
  $("#map-mode").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-map-mode]");
    if (!button) return;
    state.mapMode = button.dataset.mapMode;
    $$("#map-mode button").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    });
    $("#map-explorer").classList.toggle("country-mode", state.mapMode !== "city");
    renderMapExplorer();
  });
  $("#league-filter").addEventListener("change", (event) => {
    state.league = event.target.value;
    state.team = "all";
    populateTeamOptions();
    render();
  });
  $("#team-filter").addEventListener("change", (event) => { state.team = event.target.value; render(); });
  $("#age-filter").addEventListener("change", (event) => { state.ageBand = event.target.value; render(); });
  $("#age-chart-mode").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-age-chart]");
    if (!button) return;
    state.ageChartMode = button.dataset.ageChart;
    $$("#age-chart-mode button").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    });
    updateAgeView();
  });
  $("#age-group-mode").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-age-group]");
    if (!button) return;
    state.ageGroupMode = button.dataset.ageGroup;
    $$("#age-group-mode button").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-pressed", String(item === button));
    });
    updateAgeView();
  });
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
    state.ageBand = "all";
    state.placeQuery = "";
    state.years = new Set(state.payload.meta.years);
    state.metric = "starts";
    $("#league-filter").value = "all";
    populateTeamOptions();
    $("#team-filter").value = "all";
    $("#country-filter").value = "all";
    $("#age-filter").value = "all";
    $("#place-search").value = "";
    $$("#metric-control button").forEach((button) => button.classList.toggle("active", button.dataset.metric === "starts"));
    render();
  });
  $$(".view-tabs button").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$('[data-view-link]').forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.viewLink); }));
  $("#player-search").addEventListener("input", (event) => { state.search = event.target.value; updatePlayerTable(); });
  $("#close-player-modal").addEventListener("click", closePlayerProfile);
  $("#player-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closePlayerProfile(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && $("#player-modal").classList.contains("open")) closePlayerProfile(); });
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
    const [response, countryResponse, populationResponse] = await Promise.all([fetch(DATA_URL), fetch(COUNTRY_GEO_URL), fetch(POPULATION_GEO_URL)]);
    if (!response.ok) throw new Error(`Dataset request failed (${response.status})`);
    if (!countryResponse.ok) throw new Error(`Country geometry request failed (${countryResponse.status})`);
    if (!populationResponse.ok) throw new Error(`Population geometry request failed (${populationResponse.status})`);
    state.payload = await response.json();
    state.countryGeojson = await countryResponse.json();
    state.populationGeojson = await populationResponse.json();
    prepareCountryMetadata();
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
