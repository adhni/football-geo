(function () {
  "use strict";

  const navigation = window.TalentGeoNavigation;
  const sports = navigation?.sports || [];
  const rootUrl = navigation?.rootUrl || new URL("../", window.location.href);
  const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
  const parameters = new URLSearchParams(window.location.search);
  const sportById = (id) => sports.find((sport) => sport.id === id) || null;
  const validSportId = (id, fallback) => sportById(id)?.id || fallback;
  const validMeasure = (value) => value === "people" ? "people" : "workload";
  const initialLat = Number(parameters.get("lat"));
  const initialLon = Number(parameters.get("lon"));
  const initialZoom = Number(parameters.get("zoom"));
  const initialViewport = Number.isFinite(initialLat) && Math.abs(initialLat) <= 90 && Number.isFinite(initialLon) && Math.abs(initialLon) <= 180 && Number.isFinite(initialZoom) && initialZoom >= 1 && initialZoom <= 18
    ? { lat: initialLat, lon: initialLon, zoom: initialZoom }
    : { lat: 12, lon: 5, zoom: 1 };

  const state = {
    view: parameters.get("view") === "population" ? "population" : "places",
    resolution: [1, 2, 3].includes(Number(parameters.get("resolution"))) ? Number(parameters.get("resolution")) : 3,
    mobilePanel: "left",
    datasets: new Map(),
    population: new Map(),
    urlTimer: null,
    syncingViewport: false,
    sides: {
      left: { id: validSportId(parameters.get("left"), "nfl"), measure: validMeasure(parameters.get("leftMeasure")), token: 0 },
      right: { id: validSportId(parameters.get("right"), "nba"), measure: validMeasure(parameters.get("rightMeasure")), token: 0 },
    },
  };

  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const titleCase = (value) => String(value || "").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const workloadValue = (record, sport) => Number(record[sport.workloadField]) || 0;
  const datasetUrl = (sport) => new URL(`${sport.path}data/dashboard.json`, rootUrl);
  const populationUrl = (sport, resolution) => new URL(`${sport.path}data/population_hexes_r${resolution}.geojson`, rootUrl);
  const otherSide = (side) => side === "left" ? "right" : "left";

  function showError(message) {
    const toast = $("#error-toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showError.timer);
    showError.timer = window.setTimeout(() => toast.classList.remove("show"), 5200);
  }

  async function fetchJson(url, cache, key) {
    if (cache.has(key)) return cache.get(key);
    const promise = fetch(url).then((response) => {
      if (!response.ok) throw new Error(`Data request failed (${response.status})`);
      return response.json();
    }).catch((error) => {
      cache.delete(key);
      throw error;
    });
    cache.set(key, promise);
    return promise;
  }

  function datasetFor(sport) {
    return fetchJson(datasetUrl(sport), state.datasets, sport.id);
  }

  function populationFor(sport) {
    const key = `${sport.id}:${state.resolution}`;
    return fetchJson(populationUrl(sport, state.resolution), state.population, key);
  }

  function initMap(side) {
    const panel = state.sides[side];
    panel.map = L.map(`${side}-map`, { preferCanvas: true, zoomControl: false, worldCopyJump: true, minZoom: 1 }).setView([initialViewport.lat, initialViewport.lon], initialViewport.zoom);
    L.control.zoom({ position: side === "left" ? "bottomleft" : "bottomright" }).addTo(panel.map);
    panel.baseLayer = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    }).addTo(panel.map);
    panel.layer = L.layerGroup().addTo(panel.map);
    panel.map.on("moveend", () => syncViewport(side));
  }

  function sameViewport(first, second) {
    const firstCenter = first.getCenter();
    const secondCenter = second.getCenter();
    const longitudeGap = Math.abs(((firstCenter.lng - secondCenter.lng + 540) % 360) - 180);
    return first.getZoom() === second.getZoom() && Math.abs(firstCenter.lat - secondCenter.lat) < .00001 && longitudeGap < .00001;
  }

  function syncViewport(sourceSide) {
    if (state.syncingViewport) return;
    const source = state.sides[sourceSide].map;
    const target = state.sides[otherSide(sourceSide)].map;
    if (!sameViewport(source, target)) {
      state.syncingViewport = true;
      target.setView(source.getCenter(), source.getZoom(), { animate: false });
      window.requestAnimationFrame(() => { state.syncingViewport = false; });
    }
    scheduleUrlUpdate();
  }

  function scheduleUrlUpdate() {
    window.clearTimeout(state.urlTimer);
    state.urlTimer = window.setTimeout(updateUrl, 120);
  }

  function updateUrl() {
    const url = new URL(window.location.href);
    const center = state.sides.left.map?.getCenter();
    url.searchParams.set("left", state.sides.left.id);
    url.searchParams.set("right", state.sides.right.id);
    url.searchParams.set("view", state.view);
    url.searchParams.set("leftMeasure", state.sides.left.measure);
    url.searchParams.set("rightMeasure", state.sides.right.measure);
    if (state.view === "population") url.searchParams.set("resolution", String(state.resolution));
    else url.searchParams.delete("resolution");
    if (center) {
      url.searchParams.set("lat", center.lat.toFixed(5));
      url.searchParams.set("lon", center.lng.toFixed(5));
      url.searchParams.set("zoom", String(state.sides.left.map.getZoom()));
    }
    window.history.replaceState(null, "", url);
  }

  function aggregatePlaces(records, sport) {
    const places = new Map();
    records.forEach((record) => {
      const lat = Number(record.lat);
      const lon = Number(record.lon);
      if (!record.mapped || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
      const key = `${lat.toFixed(4)}:${lon.toFixed(4)}`;
      if (!places.has(key)) places.set(key, { lat, lon, place: record.place || "Mapped place", country: record.country || "Country unavailable", people: 0, workload: 0, origins: 0 });
      const place = places.get(key);
      place.people += 1;
      place.workload += workloadValue(record, sport);
      if (record.locationType && record.locationType !== "birthplace") place.origins += 1;
    });
    return [...places.values()];
  }

  function clearSideLayer(side) {
    const panel = state.sides[side];
    if (panel.layer && panel.map.hasLayer(panel.layer)) panel.map.removeLayer(panel.layer);
    panel.layer = L.layerGroup().addTo(panel.map);
  }

  function markerRadius(value, maximum) {
    return 5 + Math.sqrt(Math.max(value, 0) / Math.max(maximum, 1)) * 17;
  }

  function renderPlaces(side, payload, sport) {
    const panel = state.sides[side];
    clearSideLayer(side);
    const places = aggregatePlaces(payload.records || [], sport);
    const metric = (place) => panel.measure === "people" ? place.people : place.workload;
    const maximum = Math.max(...places.map(metric), 1);
    places.sort((a, b) => metric(a) - metric(b)).forEach((place) => {
      const value = metric(place);
      const kind = place.origins === place.people ? "Origin fallback" : place.origins ? `${place.origins} origin fallback` : "Birthplace";
      L.circleMarker([place.lat, place.lon], {
        radius: markerRadius(value, maximum),
        color: "rgba(255,255,255,.82)",
        weight: 1.2,
        fillColor: sport.accent,
        fillOpacity: .76,
      }).bindTooltip(`<strong>${escapeHtml(place.place)}</strong><small>${escapeHtml(place.country)} · ${escapeHtml(kind)}</small>${number.format(value)} ${escapeHtml(panel.measure === "people" ? sport.participantLabel : sport.workloadLabel)}<small>${number.format(place.people)} ${escapeHtml(sport.participantLabel)} · ${number.format(place.workload)} ${escapeHtml(sport.workloadLabel)}</small>`, { className: "compare-tooltip", sticky: true }).addTo(panel.layer);
    });
    const mapped = (payload.records || []).filter((record) => record.mapped);
    const mappedWorkload = mapped.reduce((sum, record) => sum + workloadValue(record, sport), 0);
    $(`#${side}-summary`).innerHTML = `<b>${number.format(mapped.length)}</b> mapped ${escapeHtml(sport.participantLabel)} · <b>${number.format(places.length)}</b> places · <b>${compact.format(mappedWorkload)}</b> ${escapeHtml(sport.workloadLabel)}`;
    $(`#${side}-legend`).innerHTML = `<i></i> Size = ${escapeHtml(panel.measure === "people" ? sport.participantLabel : sport.workloadLabel)} · scaled within Map ${side === "left" ? "A" : "B"}`;
  }

  function hexToRgb(hex) {
    const value = hex.replace("#", "");
    return [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16));
  }

  function mixColour(startHex, endHex, ratio) {
    const start = hexToRgb(startHex);
    const end = hexToRgb(endHex);
    const amount = Math.max(0, Math.min(ratio, 1));
    return `rgb(${start.map((channel, index) => Math.round(channel + (end[index] - channel) * amount)).join(",")})`;
  }

  function quantile(values, fraction) {
    if (!values.length) return 1;
    return values[Math.min(values.length - 1, Math.floor((values.length - 1) * fraction))] || 1;
  }

  function populationCells(records, geojson, sport, measure) {
    const players = new Map(records.filter((record) => record.mapped && (!record.locationType || record.locationType === "birthplace")).map((record) => [record.id, record]));
    return (geojson.features || []).map((feature) => {
      const selected = [...new Set(feature.properties.player_ids || [])].map((id) => players.get(id)).filter(Boolean);
      if (!selected.length) return null;
      const population = Number(feature.properties.population) || 0;
      const workload = selected.reduce((sum, record) => sum + workloadValue(record, sport), 0);
      const raw = measure === "people" ? selected.length : workload;
      return {
        feature,
        people: selected.length,
        workload,
        population,
        rate: population ? raw / population * 1_000_000 : null,
        stable: selected.length >= 2 && population >= 100000,
        label: feature.properties.label || "Mapped area",
        country: feature.properties.country || "Country unavailable",
      };
    }).filter(Boolean);
  }

  function renderPopulation(side, payload, geojson, sport) {
    const panel = state.sides[side];
    clearSideLayer(side);
    const cells = populationCells(payload.records || [], geojson, sport, panel.measure);
    const rates = cells.map((cell) => cell.rate).filter((rate) => rate !== null).sort((a, b) => a - b);
    const colourMaximum = quantile(rates, .9);
    const byId = new Map(cells.map((cell) => [cell.feature.properties.hex_id, cell]));
    panel.map.removeLayer(panel.layer);
    panel.layer = L.geoJSON({ type: "FeatureCollection", features: cells.map((cell) => cell.feature) }, {
      style(feature) {
        const cell = byId.get(feature.properties.hex_id);
        const strength = Math.sqrt(Math.min((cell.rate || 0) / Math.max(colourMaximum, 1), 1));
        return { color: cell.stable ? sport.accent : "#82918c", weight: cell.stable ? .9 : .7, dashArray: cell.stable ? null : "3 3", fillColor: mixColour("#122d2e", sport.accent, strength), fillOpacity: cell.stable ? .8 : .42 };
      },
      onEachFeature(feature, layer) {
        const cell = byId.get(feature.properties.hex_id);
        const label = panel.measure === "people" ? `${sport.participantLabel} per 1M` : `${sport.workloadLabel} per 1M`;
        layer.bindTooltip(`<strong>${escapeHtml(cell.label)} area</strong><small>${escapeHtml(cell.country)}${cell.stable ? "" : " · small sample"}</small>${cell.rate === null ? "Population unavailable" : `${compact.format(cell.rate)} ${escapeHtml(label)}`}<small>${cell.people} ${escapeHtml(sport.participantLabel)} · ${number.format(cell.workload)} ${escapeHtml(sport.workloadLabel)} · ${compact.format(cell.population)} residents</small>`, { className: "compare-tooltip", sticky: true });
      },
    }).addTo(panel.map);
    const birthplacePlayers = new Set(cells.flatMap((cell) => cell.feature.properties.player_ids || []));
    $(`#${side}-summary`).innerHTML = `<b>${number.format(cells.length)}</b> occupied areas · <b>${number.format(birthplacePlayers.size)}</b> birthplace-mapped ${escapeHtml(sport.participantLabel)} · H3 resolution ${state.resolution}`;
    const rateLabel = panel.measure === "people" ? `${sport.participantLabel} per 1M` : `${sport.workloadLabel} per 1M`;
    $(`#${side}-legend`).innerHTML = `<span class="colour-ramp"></span> ${escapeHtml(rateLabel)} · dashed = small sample`;
  }

  function updatePanelCopy(side, sport) {
    const panel = $(`#${side}-panel`);
    panel.style.setProperty("--panel-accent", sport.accent);
    document.body.style.setProperty(`--${side}-accent`, sport.accent);
    $(`#${side}-title`).textContent = sport.name;
    $(`#${side}-season`).textContent = sport.season;
    $(`#${side}-scope`).textContent = sport.scope;
    const buttons = [...document.querySelectorAll(`#${side}-measures button`)];
    buttons.find((button) => button.dataset.measure === "workload").textContent = titleCase(sport.workloadLabel);
    buttons.find((button) => button.dataset.measure === "people").textContent = titleCase(sport.participantLabel);
    buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.measure === state.sides[side].measure)));
    $(`#mobile-${side}-tab`).textContent = `${side === "left" ? "A" : "B"} · ${sport.name}`;
  }

  async function renderSide(side) {
    const panel = state.sides[side];
    const sport = sportById(panel.id);
    const token = ++panel.token;
    updatePanelCopy(side, sport);
    $(`#${side}-loading`).hidden = false;
    $(`#${side}-loading`).textContent = `Loading ${sport.name}…`;
    try {
      const payload = await datasetFor(sport);
      if (token !== panel.token) return;
      if (state.view === "population") {
        const geojson = await populationFor(sport);
        if (token !== panel.token) return;
        renderPopulation(side, payload, geojson, sport);
      } else {
        renderPlaces(side, payload, sport);
      }
      $(`#${side}-loading`).hidden = true;
    } catch (error) {
      if (token !== panel.token) return;
      $(`#${side}-loading`).textContent = "Map data unavailable";
      showError(`${sport.name}: ${error.message}`);
    }
  }

  function renderBoth() {
    renderSide("left");
    renderSide("right");
    scheduleUrlUpdate();
  }

  function setView(view) {
    state.view = view === "population" ? "population" : "places";
    document.querySelectorAll("#view-mode [data-view]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.view === state.view)));
    $("#resolution-control").hidden = state.view !== "population";
    renderBoth();
  }

  function setResolution(resolution) {
    state.resolution = [1, 2, 3].includes(Number(resolution)) ? Number(resolution) : 3;
    document.querySelectorAll("[data-resolution]").forEach((button) => button.setAttribute("aria-pressed", String(Number(button.dataset.resolution) === state.resolution)));
    if (state.view === "population") renderBoth();
  }

  function setMobilePanel(side) {
    state.mobilePanel = side;
    document.querySelectorAll("[data-mobile-panel]").forEach((button) => button.setAttribute("aria-selected", String(button.dataset.mobilePanel === side)));
    document.querySelectorAll(".compare-panel").forEach((panel) => panel.classList.toggle("active-mobile-panel", panel.dataset.side === side));
    window.setTimeout(() => state.sides[side].map.invalidateSize(), 0);
  }

  function populateSportSelects() {
    const options = sports.map((sport) => `<option value="${escapeHtml(sport.id)}">${escapeHtml(sport.name)}</option>`).join("");
    document.querySelectorAll("[data-sport-select]").forEach((select) => {
      select.innerHTML = options;
      select.value = state.sides[select.dataset.sportSelect].id;
    });
  }

  function bindEvents() {
    document.querySelectorAll("[data-sport-select]").forEach((select) => select.addEventListener("change", () => {
      const side = select.dataset.sportSelect;
      state.sides[side].id = select.value;
      renderSide(side);
      scheduleUrlUpdate();
    }));
    document.querySelectorAll(".panel-measures button").forEach((button) => button.addEventListener("click", () => {
      const side = button.dataset.side;
      state.sides[side].measure = validMeasure(button.dataset.measure);
      updatePanelCopy(side, sportById(state.sides[side].id));
      renderSide(side);
      scheduleUrlUpdate();
    }));
    document.querySelectorAll("#view-mode [data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
    document.querySelectorAll("[data-resolution]").forEach((button) => button.addEventListener("click", () => setResolution(button.dataset.resolution)));
    document.querySelectorAll("[data-mobile-panel]").forEach((button) => button.addEventListener("click", () => setMobilePanel(button.dataset.mobilePanel)));
    document.querySelectorAll("[data-preset]").forEach((button) => button.addEventListener("click", () => {
      const [left, right] = button.dataset.preset.split(",");
      state.sides.left.id = left;
      state.sides.right.id = right;
      $("#left-sport").value = left;
      $("#right-sport").value = right;
      renderBoth();
    }));
    $("#swap-sports").addEventListener("click", () => {
      const left = { id: state.sides.left.id, measure: state.sides.left.measure };
      state.sides.left.id = state.sides.right.id;
      state.sides.left.measure = state.sides.right.measure;
      state.sides.right.id = left.id;
      state.sides.right.measure = left.measure;
      $("#left-sport").value = state.sides.left.id;
      $("#right-sport").value = state.sides.right.id;
      renderBoth();
    });
    $("#copy-link").addEventListener("click", async (event) => {
      updateUrl();
      try {
        await navigator.clipboard.writeText(window.location.href);
        event.currentTarget.textContent = "Copied";
        window.setTimeout(() => { event.currentTarget.textContent = "Copy link"; }, 1500);
      } catch (_) {
        showError("Copy failed. Use the address bar to copy this comparison.");
      }
    });
    window.addEventListener("resize", () => {
      state.sides.left.map.invalidateSize();
      state.sides.right.map.invalidateSize();
    });
  }

  function init() {
    if (!sports.length || !window.L) {
      showError("The comparison map could not start.");
      return;
    }
    populateSportSelects();
    initMap("left");
    initMap("right");
    bindEvents();
    setResolution(state.resolution);
    setMobilePanel("left");
    setView(state.view);
  }

  init();
}());
