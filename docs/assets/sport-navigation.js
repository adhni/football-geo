(function () {
  "use strict";

  const scriptUrl = new URL(document.currentScript.src, window.location.href);
  const rootUrl = new URL("../", scriptUrl);
  const sports = window.TALENT_GEO_CATALOG;

  const cleanPath = (value) => decodeURIComponent(value).replace(/\/index\.html$/, "/").replace(/^\/+|\/+$/g, "");
  const rootPath = cleanPath(rootUrl.pathname);
  const pagePath = cleanPath(window.location.pathname);
  const relativePath = pagePath.startsWith(rootPath) ? cleanPath(pagePath.slice(rootPath.length)) : pagePath;
  const currentSport = sports.find((sport) => cleanPath(sport.path) === relativePath) || null;
  const isDirectory = relativePath === "sports";
  const isCompare = relativePath === "compare";
  let mapStateReader = null;
  const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const sportUrl = (sport) => {
    const url = new URL(sport.path, rootUrl);
    const language = window.TalentGeoLanguage?.language;
    if (language && language !== "en") url.searchParams.set("lang", language);
    return url;
  };

  function renderHeaderNavigation() {
    document.querySelectorAll(".sport-switcher").forEach((navigation) => {
      navigation.setAttribute("aria-label", "Primary navigation");
      const sportLinks = (items) => items.map((sport) => {
        const active = currentSport?.id === sport.id;
        return `<a${active ? ' class="active" aria-current="page"' : ""} data-sport-id="${escapeHtml(sport.id)}" href="${escapeHtml(sportUrl(sport).href)}"><i style="--sport-accent:${escapeHtml(sport.accent)}" aria-hidden="true"></i>${escapeHtml(sport.name)}</a>`;
      }).join("");
      const teamSports = sports.filter((sport) => sport.kind === "team");
      const individualSports = sports.filter((sport) => sport.kind !== "team");
      const directoryUrl = escapeHtml(new URL("sports/", rootUrl).href);
      const compareUrl = escapeHtml(new URL("compare/", rootUrl).href);
      navigation.innerHTML = `
        <details class="sport-menu">
          <summary${currentSport || isDirectory ? ' class="active"' : ""}>Sports<span aria-hidden="true" class="sport-menu-chevron">⌄</span></summary>
          <div class="sport-menu-panel">
            <div class="sport-menu-heading"><strong>Explore ${sports.length} sports</strong><span>Choose an edition</span></div>
            <div class="sport-menu-columns">
              <div><span class="sport-menu-label">Team sports</span>${sportLinks(teamSports)}</div>
              <div><span class="sport-menu-label">Individual &amp; racing</span>${sportLinks(individualSports)}</div>
            </div>
            <div class="sport-menu-footer">
              <a class="sport-menu-directory" href="${directoryUrl}">Browse editions <span aria-hidden="true">→</span></a>
              <a class="sport-menu-source" href="https://github.com/adhni/football-geo" target="_blank" rel="noreferrer">Source ↗</a>
            </div>
          </div>
        </details>
        <a class="nav-all-sports${isDirectory ? " active" : ""}"${isDirectory ? ' aria-current="page"' : ""} href="${directoryUrl}">All sports</a>
        <a class="nav-compare${isCompare ? " active" : ""}" aria-label="Compare sports"${isCompare ? ' aria-current="page"' : ""} href="${compareUrl}"><span>Compare<span class="nav-compare-extra"> sports</span></span><span aria-hidden="true">↗</span></a>`;
      const menu = navigation.querySelector(".sport-menu");
      document.addEventListener("click", (event) => { if (!navigation.contains(event.target)) menu.open = false; });
      navigation.addEventListener("keydown", (event) => { if (event.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); } });
      navigation.addEventListener("click", (event) => {
        const link = event.target.closest("a[data-sport-id]");
        const mapPanel = document.querySelector("#view-map");
        if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || !mapStateReader || !mapPanel?.classList.contains("active") || mapPanel.hidden) return;
        const target = sports.find((sport) => sport.id === link.dataset.sportId);
        if (!target || target.id === currentSport?.id) return;
        event.preventDefault();
        window.location.assign(comparisonUrl(target, mapStateReader()).href);
      });
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

  function sideBySideUrl(left = currentSport?.id || "nfl", right = left === "nba" ? "nfl" : "nba", mapState = null) {
    const url = new URL("compare/", rootUrl);
    if (window.TalentGeoLanguage?.language) url.searchParams.set("lang", window.TalentGeoLanguage.language);
    url.searchParams.set("left", sports.some((sport) => sport.id === left) ? left : "nfl");
    url.searchParams.set("right", sports.some((sport) => sport.id === right) ? right : "nba");
    if (mapState?.mode?.startsWith("population")) url.searchParams.set("view", "population");
    if (mapState?.resolution) url.searchParams.set("resolution", String(mapState.resolution));
    if (mapState?.viewport) {
      url.searchParams.set("lat", Number(mapState.viewport.lat).toFixed(5));
      url.searchParams.set("lon", Number(mapState.viewport.lon).toFixed(5));
      url.searchParams.set("zoom", String(Math.round(mapState.viewport.zoom)));
    }
    return url;
  }

  function mountMapSwitcher(getMapState) {
    const explorer = document.querySelector("#map-explorer");
    if (!explorer || !currentSport) return;
    mapStateReader = getMapState;
    const mount = explorer.closest(".view-panel")?.querySelector("[data-map-sport-switcher]") || explorer;
    if (mount.querySelector(".map-sport-handoff")) return;
    const compact = mount !== explorer;
    mount.insertAdjacentHTML("afterbegin", `<div class="map-sport-handoff"><label class="map-sport-control" for="map-sport-select"><span>${compact ? "Sport" : "Compare sport"}</span><span class="select-wrap"><select id="map-sport-select" aria-describedby="map-sport-note">${sports.map((sport) => `<option value="${escapeHtml(sport.id)}"${sport.id === currentSport.id ? " selected" : ""}>${escapeHtml(sport.name)}</option>`).join("")}</select></span></label><p id="map-sport-note"><b>Same place, another sport.</b> Viewpoint and map mode carry over; each sport keeps its own workload unit.</p><a href="${escapeHtml(sideBySideUrl(currentSport.id, currentSport.id === "nba" ? "nfl" : "nba", getMapState()).href)}">Compare side by side →</a></div>`);
    mount.querySelector("#map-sport-select").addEventListener("change", (event) => {
      const target = sports.find((sport) => sport.id === event.target.value);
      if (!target || target.id === currentSport.id) return;
      window.location.assign(comparisonUrl(target, getMapState()).href);
    });
  }

  function restoreMapScroll() {
    if (!readMapState() || window.location.hash !== "#map") return;
    const target = document.querySelector(".view-tabs") || document.querySelector("#view-map");
    if (!target) return;
    const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - 12);
    window.scrollTo(0, top);
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
    const number = new Intl.NumberFormat(window.TalentGeoLanguage?.locale || "en-US");
    container.innerHTML = sports.map((sport) => `<article class="sport-card" style="--card-accent:${escapeHtml(sport.accent)}"><div><span>${escapeHtml(sport.season)}</span><strong>${escapeHtml(sport.name)}</strong><p>${escapeHtml(sport.scope)}</p></div><dl><div><dt>Cohort</dt><dd>${number.format(sport.participants)} ${escapeHtml(sport.participantLabel)}</dd></div><div><dt>Birthplace coverage</dt><dd>${sport.coverage.toFixed(1)}%${sport.mappedCoverage !== sport.coverage ? `<small>${sport.mappedCoverage.toFixed(1)}% including origins</small>` : ""}</dd></div><div><dt>Map measures</dt><dd>${escapeHtml(sport.measures)}</dd></div></dl><a href="${escapeHtml(new URL(`${sport.path}#map`, rootUrl).href)}">Open map <span>→</span></a></article>`).join("");
  }

  window.TalentGeoNavigation = { sports, currentSport, rootUrl, readMapState, comparisonUrl, sideBySideUrl, mountMapSwitcher, restoreMapScroll, renderDirectory };
  renderHeaderNavigation();
  enhanceMapWorkspace();
  restoreMapScroll();
  document.addEventListener("talentgeolanguagechange", () => renderDirectory(document.querySelector("#sport-directory")));
}());
