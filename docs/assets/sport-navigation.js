(function () {
  "use strict";

  const scriptUrl = new URL(document.currentScript.src, window.location.href);
  const rootUrl = new URL("../", scriptUrl);
  const sports = [
    { id: "football", name: "Football", path: "", season: "2025–26", scope: "Big Five European domestic leagues", participants: 2690, participantLabel: "players", coverage: 90.1, measures: "Starts · Starters · Players", accent: "#d9ff57" },
    { id: "cricket", name: "Cricket", path: "cricket/", season: "2025", scope: "Men’s and women’s Full Member T20 internationals", participants: 446, participantLabel: "players", coverage: 87.0, measures: "Appearances · Players", accent: "#f4c95d" },
    { id: "ufc", name: "UFC", path: "ufc/", season: "2025", scope: "All 42 UFC events", participants: 620, participantLabel: "fighters", coverage: 84.2, measures: "Bouts · Fighters", accent: "#ef4444" },
    { id: "formula", name: "Formula", path: "formula/", season: "2025", scope: "F1, F2, F3 and F1 Academy", participants: 106, participantLabel: "drivers", coverage: 81.1, measures: "Laps · Starts · Drivers", accent: "#ff5a36" },
    { id: "motogp", name: "MotoGP", path: "motogp/", season: "2025", scope: "MotoGP, Moto2, Moto3, MotoE and WorldWCR", participants: 163, participantLabel: "riders", coverage: 90.2, measures: "Laps · Starts · Riders", accent: "#ff3b30" },
    { id: "volleyball", name: "Volleyball", path: "volleyball/", season: "2025", scope: "Women’s and men’s Volleyball Nations League", participants: 580, participantLabel: "players", coverage: 60.2, measures: "Sets · Matches · Players", accent: "#ffcf33" },
    { id: "tennis", name: "Tennis", path: "tennis/", season: "2025", scope: "Year-end ATP and WTA singles top 100", participants: 200, participantLabel: "players", coverage: 99.5, measures: "Ranking points · Players", accent: "#b9ef72" },
    { id: "padel", name: "Padel", path: "padel/", season: "2025", scope: "Year-end FIP men’s and women’s top 100", participants: 200, participantLabel: "players", coverage: 99.0, measures: "Ranking points · Players", accent: "#5dd6db" },
    { id: "badminton", name: "Badminton", path: "badminton/", season: "2025", scope: "Top singles players and doubles pairs", participants: 468, participantLabel: "athletes", coverage: 73.7, measures: "Allocated points · Athletes", accent: "#b592ff" },
    { id: "golf", name: "Golf", path: "golf/", season: "2025", scope: "Final men’s and women’s world top 100", participants: 200, participantLabel: "golfers", coverage: 84.0, measures: "Ranking points · Golfers", accent: "#e9c75f" },
    { id: "afl", name: "AFL", path: "afl/", season: "2025", scope: "Men’s home-and-away season", participants: 663, participantLabel: "players", coverage: 47.4, measures: "Games · Players", accent: "#e5652f" },
    { id: "nrl", name: "NRL", path: "nrl/", season: "2025", scope: "Men’s regular season", participants: 506, participantLabel: "players", coverage: 56.1, measures: "Games · Players", accent: "#78d69a" },
    { id: "nba", name: "NBA", path: "nba/", season: "2025–26", scope: "Men’s regular season", participants: 582, participantLabel: "players", coverage: 99.1, measures: "Minutes · Games · Players", accent: "#ff9b54" },
    { id: "nfl", name: "NFL", path: "nfl/", season: "2025", scope: "Men’s regular season", participants: 2186, participantLabel: "players", coverage: 97.0, measures: "Snaps · Games · Players", accent: "#71b8ff" },
    { id: "nhl", name: "NHL", path: "nhl/", season: "2025–26", scope: "Men’s regular season", participants: 1038, participantLabel: "players", coverage: 95.8, measures: "Minutes · Games · Players", accent: "#65d4ec" },
    { id: "mlb", name: "MLB", path: "mlb/", season: "2025", scope: "Men’s regular season", participants: 1470, participantLabel: "players", coverage: 96.1, measures: "Workload · Games · Players", accent: "#f28c5c" },
  ];

  const cleanPath = (value) => decodeURIComponent(value).replace(/\/index\.html$/, "/").replace(/^\/+|\/+$/g, "");
  const rootPath = cleanPath(rootUrl.pathname);
  const pagePath = cleanPath(window.location.pathname);
  const relativePath = pagePath.startsWith(rootPath) ? cleanPath(pagePath.slice(rootPath.length)) : pagePath;
  const currentSport = sports.find((sport) => cleanPath(sport.path) === relativePath) || null;
  const isDirectory = relativePath === "sports";
  const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const sportUrl = (sport) => new URL(sport.path, rootUrl);

  function renderHeaderNavigation() {
    document.querySelectorAll(".sport-switcher").forEach((navigation) => {
      navigation.innerHTML = sports.map((sport) => {
        const active = currentSport?.id === sport.id;
        return `<a${active ? ' class="active" aria-current="page"' : ""} href="${escapeHtml(sportUrl(sport).href)}">${escapeHtml(sport.name)}</a>`;
      }).join("") + `<a${isDirectory ? ' class="active" aria-current="page"' : ""} href="${escapeHtml(new URL("sports/", rootUrl).href)}">All sports</a>`;
      navigation.querySelector("a.active")?.scrollIntoView({ block: "nearest", inline: "center" });
    });
  }

  function readMapState() {
    const parameters = new URLSearchParams(window.location.search);
    if (parameters.get("compare") !== "1") return null;
    const mode = ["city", "country", "population", "population-workload"].includes(parameters.get("mode")) ? parameters.get("mode") : "city";
    const measure = parameters.get("measure") === "people" ? "people" : "workload";
    const resolution = [1, 2, 3].includes(Number(parameters.get("resolution"))) ? Number(parameters.get("resolution")) : 3;
    const lat = Number(parameters.get("lat"));
    const lon = Number(parameters.get("lon"));
    const zoom = Number(parameters.get("zoom"));
    const viewport = Number.isFinite(lat) && Math.abs(lat) <= 90 && Number.isFinite(lon) && Math.abs(lon) <= 180 && Number.isFinite(zoom) && zoom >= 1 && zoom <= 19
      ? { lat, lon, zoom }
      : null;
    return { mode, measure, resolution, country: parameters.get("country") || "all", viewport };
  }

  function comparisonUrl(target, mapState) {
    const url = sportUrl(target);
    const mode = ["city", "country", "population", "population-workload"].includes(mapState?.mode) ? mapState.mode : "city";
    url.searchParams.set("compare", "1");
    url.searchParams.set("mode", mode);
    url.searchParams.set("measure", mapState?.measure === "people" ? "people" : "workload");
    if (mode.startsWith("population")) url.searchParams.set("resolution", String(mapState?.resolution || 3));
    if (mapState?.country && mapState.country !== "all") url.searchParams.set("country", mapState.country);
    if (mapState?.viewport) {
      url.searchParams.set("lat", Number(mapState.viewport.lat).toFixed(5));
      url.searchParams.set("lon", Number(mapState.viewport.lon).toFixed(5));
      url.searchParams.set("zoom", String(Math.round(mapState.viewport.zoom)));
    }
    url.hash = "map";
    return url;
  }

  function mountMapSwitcher(getMapState) {
    const explorer = document.querySelector("#map-explorer");
    if (!explorer || !currentSport) return;
    const mount = explorer.closest(".view-panel")?.querySelector("[data-map-sport-switcher]") || explorer;
    if (mount.querySelector(".map-sport-handoff")) return;
    const compact = mount !== explorer;
    mount.insertAdjacentHTML("afterbegin", `<div class="map-sport-handoff"><label class="map-sport-control" for="map-sport-select"><span>${compact ? "Sport" : "Compare sport"}</span><span class="select-wrap"><select id="map-sport-select" aria-describedby="map-sport-note">${sports.map((sport) => `<option value="${escapeHtml(sport.id)}"${sport.id === currentSport.id ? " selected" : ""}>${escapeHtml(sport.name)}</option>`).join("")}</select></span></label><p id="map-sport-note"><b>Same place, another sport.</b> Viewpoint and map mode carry over; each sport keeps its own workload unit.</p><a href="${escapeHtml(new URL("sports/", rootUrl).href)}">Compare all editions →</a></div>`);
    mount.querySelector("#map-sport-select").addEventListener("change", (event) => {
      const target = sports.find((sport) => sport.id === event.target.value);
      if (!target || target.id === currentSport.id) return;
      window.location.assign(comparisonUrl(target, getMapState()).href);
    });
  }

  function enhanceMapWorkspace() {
    const view = document.querySelector("#view-map");
    const explorer = view?.querySelector("#map-explorer");
    const layout = view?.querySelector(".map-layout");
    const ranking = layout?.querySelector(".ranking-card");
    if (!view || !explorer || !layout || !ranking) return;
    document.body.classList.add("map-first-layout");
    if (view.querySelector(".map-workspace-toolbar")) return;

    const heading = view.querySelector(":scope > .section-heading");
    const headingCopy = heading?.querySelector(":scope > div:first-child");
    const summary = heading?.querySelector(":scope > p");
    heading?.classList.add("map-first-heading");
    summary?.classList.add("map-scope-summary");
    if (summary && headingCopy) headingCopy.append(summary);

    const headingActions = document.createElement("div");
    headingActions.className = "map-heading-actions";
    headingActions.innerHTML = '<div class="map-switcher-slot" data-map-sport-switcher></div><button class="ranking-toggle" id="ranking-toggle" type="button" aria-controls="ranking-panel" aria-expanded="false"><span>Top locations</span><b id="ranking-toggle-count">—</b></button>';
    heading?.append(headingActions);

    const toolbar = document.createElement("div");
    toolbar.className = "map-workspace-toolbar";
    explorer.before(toolbar);
    const controls = document.querySelector("main > .controls");
    const activeFilters = document.querySelector("main > .active-filters");
    if (controls) { controls.classList.add("map-scope-controls"); toolbar.append(controls); }
    if (activeFilters) toolbar.append(activeFilters);
    toolbar.append(explorer);

    layout.classList.add("map-first-map-layout");
    ranking.id = "ranking-panel";
    ranking.setAttribute("aria-hidden", "true");
    const scrim = document.createElement("button");
    scrim.className = "ranking-scrim";
    scrim.type = "button";
    scrim.setAttribute("aria-label", "Close top locations");
    layout.insertBefore(scrim, ranking);
    const close = document.createElement("button");
    close.className = "ranking-close";
    close.type = "button";
    close.setAttribute("aria-label", "Close top locations");
    close.textContent = "×";
    ranking.querySelector(".card-heading")?.append(close);

    const toggle = headingActions.querySelector(".ranking-toggle");
    const toggleCount = headingActions.querySelector("#ranking-toggle-count");
    const count = ranking.querySelector("#place-count");
    const syncCount = () => { toggleCount.textContent = count?.textContent || "—"; };
    const setOpen = (open, restoreFocus = true) => {
      layout.classList.toggle("ranking-open", open);
      ranking.setAttribute("aria-hidden", String(!open));
      toggle.setAttribute("aria-expanded", String(open));
      if (open) close.focus({ preventScroll: true });
      else if (restoreFocus) toggle.focus({ preventScroll: true });
    };
    syncCount();
    if (count) new MutationObserver(syncCount).observe(count, { childList: true, characterData: true, subtree: true });
    toggle.addEventListener("click", () => setOpen(!layout.classList.contains("ranking-open")));
    close.addEventListener("click", () => setOpen(false));
    scrim.addEventListener("click", () => setOpen(false));
    ranking.addEventListener("click", (event) => { if (event.target.closest("[data-place-key], [data-country-code], [data-hex-id]")) setOpen(false, false); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && layout.classList.contains("ranking-open")) { event.preventDefault(); setOpen(false); } });
    document.querySelector(".view-tabs")?.addEventListener("click", (event) => { if (event.target.closest('[data-view]:not([data-view="map"])')) setOpen(false, false); });
  }

  function renderDirectory(container) {
    if (!container) return;
    const number = new Intl.NumberFormat("en-US");
    container.innerHTML = sports.map((sport) => `<article class="sport-card" style="--card-accent:${escapeHtml(sport.accent)}"><div><span>${escapeHtml(sport.season)}</span><strong>${escapeHtml(sport.name)}</strong><p>${escapeHtml(sport.scope)}</p></div><dl><div><dt>Cohort</dt><dd>${number.format(sport.participants)} ${escapeHtml(sport.participantLabel)}</dd></div><div><dt>Birthplace coverage</dt><dd>${sport.coverage.toFixed(1)}%</dd></div><div><dt>Map measures</dt><dd>${escapeHtml(sport.measures)}</dd></div></dl><a href="${escapeHtml(new URL(`${sport.path}#map`, rootUrl).href)}">Open map <span>→</span></a></article>`).join("");
  }

  window.TalentGeoNavigation = { sports, currentSport, rootUrl, readMapState, comparisonUrl, mountMapSwitcher, renderDirectory };
  renderHeaderNavigation();
  enhanceMapWorkspace();
}());
