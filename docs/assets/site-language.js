(function () {
  "use strict";
  const catalogs = window.TALENT_GEO_LANGUAGE_CATALOG;
  const codes = Object.keys(catalogs);
  const locales = Object.fromEntries(codes.map((code) => [code, catalogs[code].locale]));
  const dictionary = new Map(Object.entries(catalogs.en.messages).filter(([key]) => key.startsWith("phrase.")).map(([key, value]) => [value, key]));
  const countryCodes = new Map([
    ["Ivory Coast", "CI"], ["Czech Republic", "CZ"],
    ["Turkey", "TR"], ["The Gambia", "GM"], ["Democratic Republic of the Congo", "CD"],
    ["Bosnia and Herzegovina", "BA"], ["Republic of the Congo", "CG"],
  ]);
  const displayNames = new Map();
  if (Intl.DisplayNames) {
    const englishNames = new Intl.DisplayNames(["en"], { type: "region" });
    for (let first = 65; first <= 90; first += 1) {
      for (let second = 65; second <= 90; second += 1) {
        const code = String.fromCharCode(first, second);
        const name = englishNames.of(code);
        if (name !== code) countryCodes.set(name, code);
      }
    }
  }
  const textRecords = new WeakMap();
  const attributeRecords = new WeakMap();
  const attributes = ["aria-label", "title", "placeholder", "data-label"];
  const sourceTitle = document.title;
  let language = "en";
  try {
    const saved = localStorage.getItem("talent-geo-language") || localStorage.getItem("football-geo-language");
    if (codes.includes(saved)) language = saved;
  } catch (_) { /* Storage can be disabled. */ }
  const requestedLanguage = new URLSearchParams(window.location?.search || "").get("lang");
  if (codes.includes(requestedLanguage)) language = requestedLanguage;

  function message(key, values = {}) {
    const template = catalogs[language].messages[key] ?? catalogs.en.messages[key] ?? key;
    return template.replace(/\{(\w+)\}/g, (token, name) => values[name] ?? token);
  }

  function word(source) {
    const key = dictionary.get(source);
    return key ? message(key) : source;
  }

  function countWord(count, noun) {
    const numeric = Number(String(count).replace(/[\s,]/g, ""));
    const category = new Intl.PluralRules(locales[language]).select(numeric);
    const key = `count.${noun}.${category}`;
    const fallback = `count.${noun}.other`;
    return message(catalogs[language].messages[key] ? key : fallback, { count });
  }

  function translateCore(source) {
    let match;
    if ((match = source.match(/^(\d+) (players|teams|athletes)$/))) return countWord(match[1], match[2]);
    if (language === "en") return source;
    if (dictionary.has(source)) return word(source);
    if (countryCodes.has(source) && Intl.DisplayNames) {
      if (!displayNames.has(language)) displayNames.set(language, new Intl.DisplayNames([locales[language]], { type: "region" }));
      return displayNames.get(language).of(countryCodes.get(source));
    }
    if ((match = source.match(/^([\d.,]+)% (including origins|verified birthplaces)$/))) return `${match[1]}% ${word(match[2])}`;
    if ((match = source.match(/^([^:]+): (.+)$/)) && dictionary.has(match[1])) return `${word(match[1])}: ${translateCore(match[2])}`;
    if ((match = source.match(/^Interactive (.+) map$/))) return `${message("template.interactive_map")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Search (.+)$/))) return `${message("template.search")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Try (.+)$/))) return `${message("template.try")} ${match[1]}`;
    if ((match = source.match(/^Open (.+) source ↗$/))) return `${message("template.open_source")} ${match[1]} ↗`;
    if ((match = source.match(/^Open (.+) ↗$/))) return `${message("template.open")} ${translateCore(match[1])} ↗`;
    if ((match = source.match(/^Loading (.+)…$/))) return `${message("template.loading")} ${translateCore(match[1])}…`;
    if ((match = source.match(/^All (\d+) teams$/))) return message("template.all_teams", { p1: match[1] });
    if ((match = source.match(/^([\d.,]+) ([a-z][a-z -]+)$/)) && dictionary.has(match[2])) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^Compare (.+)$/))) return `${word("Compare")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Current (.+) selection summary$/))) return `${word("Current selection summary")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+) players matching (?:the current )?filters$/))) return `${word("Players")} ${translateCore(match[1])} ${message("template.matching_player_filters")}`;
    if ((match = source.match(/^(.+) matching (?:the current )?filters$/))) return `${translateCore(match[1])} · ${message("template.matching_filters")}`;
    if ((match = source.match(/^(.+) birthplace map$/))) return `${word("Birthplace")} · ${translateCore(match[1])} ${word("Map view")}`;
    if ((match = source.match(/^([\d.,]+) ([A-Za-z][A-Za-z -]+)$/)) && dictionary.has(match[2])) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^(.+) in selection$/))) return `${translateCore(match[1])} ${word("in the current selection")}`;
    if ((match = source.match(/^— mapped (.+)$/))) return `— ${word("mapped")} ${translateCore(match[1])}`;
    if ((match = source.match(/^— (.+)$/))) return `— ${translateCore(match[1])}`;
    if ((match = source.match(/^Birthplace mix, player age and team (.+)$/))) return `${message("template.birthplace_mix")} ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+) Talent Geography home$/))) return `${translateCore(match[1])} · ${message("template.home")}`;
    if ((match = source.match(/^(.+) Talent Geography$/))) return `${translateCore(match[1])} · ${word("Talent Geography")}`;
    if ((match = source.match(/^(.+) dashboard (filters|views)$/))) return `${word(match[2] === "filters" ? "Dashboard filters" : "Dashboard views")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Close (player|driver|rider|fighter|athlete|golfer) profile$/))) return `${message("template.close_profile")} ${word(match[1][0].toUpperCase() + match[1].slice(1))}`;
    if ((match = source.match(/^([\w\s-]+) profile$/))) return `${word("Player profile")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Building the (.+) map$/))) return `${message("template.building_map")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^([\w\s-]+) per 1M$/))) return `${translateCore(match[1])} ${word("per 1M")}`;
    if ((match = source.match(/^([\w\s-]+) coverage$/))) return `${word("Coverage")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^([\w\s-]+)-level detail$/))) return `${message("template.detail")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Unresolved ([\w\s-]+)$/))) return `${word("unresolved")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Show more ([\w\s-]+)$/))) return `${message("template.show_more")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Find (?:a |an )?(.+)$/))) return `${message("template.find")} ${translateCore(match[1])}`;
    if ((match = source.match(/^([\d.,\s—]+) (players|clubs|leagues|places|countries|areas|starts|mapped starts|mapped|unresolved|total|residents|starters|birthplaces|locations|teams|divisions|drivers|riders|fighters|athletes|golfers|cricketers|games|matches|appearances|laps|sets|bouts|snaps|points|wins|podiums|fights|ranking points|minutes)$/))) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^Explore (\d+) sports$/))) return `${word("Explore")} ${match[1]} ${word("sports")}`;
    if ((match = source.match(/^([\d.,\s]+) active (filter|filters)$/))) return `${match[1]} ${word("filters")} ${word("active")}`;
    if ((match = source.match(/^All (\d+) clubs$/))) return message("template.all_clubs", { p1: match[1] });
    if ((match = source.match(/^([\d.,\s—]+) (players|clubs|leagues|places|countries|areas|starts|mapped starts|mapped|unresolved|total|residents|starters)$/))) {
      return `${match[1]} ${word(match[2])}`;
    }
    if ((match = source.match(/^\+([\d.,\s]+) more players$/))) return `+${match[1]} ${word("players")}`;
    if ((match = source.match(/^([\d.,\s]+) players in (this|the current) selection$/))) return `${match[1]} ${word("players")} ${word("in the current selection")}`;
    if ((match = source.match(/^([\d.,\s]+) (mapped players|reference areas)$/))) return `${match[1]} ${match[2] === "mapped players" ? `${word("players")} ${word("mapped")}` : `${word("areas")} ${word("reference")}`}`;
    if ((match = source.match(/^([\d.,\s]+) players with 1\+ start$/))) return `${match[1]} ${word("players with 1+ start")}`;
    if ((match = source.match(/^([\d.,\s]+) players · (.+) highlighted$/))) return `${match[1]} ${word("players")} · ${translateCore(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) of ([\d.,\s]+) players mapped$/))) return `${match[1]} / ${match[2]} ${word("players")} ${word("mapped")}`;
    if ((match = source.match(/^([\d.,\s]+)% (of players|birthplace coverage)$/))) return `${match[1]}% ${word(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) players, ([\d.,\s]+(?:\.\d+)?)%$/))) return `${match[1]} ${word("players")}, ${match[2]}%`;
    if ((match = source.match(/^(.+) population areas are unavailable\. Try another size\.$/))) return `${translateCore(match[1])} ${message("template.population_unavailable")}`;
    if ((match = source.match(/^By (.+)$/))) return `${message("template.by")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Countries by (.+)$/))) return `${word("Countries")} · ${translateCore(`By ${match[1]}`)}`;
    if ((match = source.match(/^(League|Club) distribution$/))) return `${word("Distribution")} · ${word(match[1])}`;
    if ((match = source.match(/^(Age distribution|Age bands) by (league|club)$/))) return `${word(match[1])} · ${word(match[2] === "league" ? "League" : "Club")}`;
    if ((match = source.match(/^Age distribution for (.+)$/))) return `${word("Age distribution")} · ${match[1]}`;
    if ((match = source.match(/^(.+) age bands\. (.+)$/))) return `${match[1]} · ${word("Age bands")}. ${translateCore(match[2])}`;
    if ((match = source.match(/^(.+) · ([\d.,\s]+) players · median (.+)$/))) return `${match[1]} · ${match[2]} ${word("players")} · ${word("median")} ${match[3]}`;
    if ((match = source.match(/^Born in:? (.+)$/))) return `${message("template.born_in")}: ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+), (.+)$/)) && (countryCodes.has(match[2]) || dictionary.has(match[2]))) return `${match[1]}, ${translateCore(match[2])}`;
    if ((match = source.match(/^(League|Club|Age): (.+)$/))) return `${word(match[1])}: ${translateCore(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) active · ([\d.,\s]+) reference$/))) return `${match[1]} ${message("template.active")} · ${match[2]} ${message("template.reference")}`;
    if ((match = source.match(/^([\d.,\s]+) (very broad|large|regional) areas$/i))) return `${match[1]} ${word(match[2][0].toUpperCase() + match[2].slice(1))} ${word("areas")}`;
    if ((match = source.match(/^Showing (.+) of (.+) players in this selection$/))) return `${message("template.showing")} ${match[1]} / ${match[2]} ${word("players")}`;
    if ((match = source.match(/^Show (\d+) more(?: players)?$/))) return `${message("template.show")} ${match[1]} ${word("players")}`;
    if ((match = source.match(/^([\d.,\s]+) years at season end$/))) return `${match[1]} ${message("template.season_end_age")}`;
    if ((match = source.match(/^([\d.,\s]+) (active|reference)$/))) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^2025–26 · Updated (.+)$/))) return `2025–26 · ${word("Updated")} ${match[1]}`;
    if ((match = source.match(/^Dataset generated (.+)$/))) return `${word("Dataset generated")} ${match[1]}`;
    if ((match = source.match(/^(.+) per 1M(?: people)?$/))) return `${translateCore(match[1])} ${message("template.per_million")}`;
    if ((match = source.match(/^population (.+)$/))) return `${word("population")} ${translateCore(match[1])}`;
    if ((match = source.match(/^([\d.,\s]+) players · ([\d.,\s]+) starts$/))) return `${match[1]} ${word("players")} · ${match[2]} ${word("starts")}`;
    if ((match = source.match(/^(Zoom to|Open profile for|Remove) (.+)$/))) return `${message("action." + match[1])} ${translateCore(match[2])}`;
    if ((match = source.match(/^(.+?) (reference area|area)$/))) {
      const name = translateCore(match[1]);
      if (match[2] === "reference area") return message("template.reference_area", { name });
      return message("template.area", { name });
    }
    if ((match = source.match(/^(.+) (player|players)$/))) return `${word(match[2] === "player" ? "Player" : "players")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+) · (.+)$/))) return `${translateCore(match[1])} · ${translateCore(match[2])}`;
    return source;
  }

  function translate(source) {
    const match = String(source).match(/^(\s*)([\s\S]*?)(\s*)$/);
    return match[1] + translateCore(match[2]) + match[3];
  }

  function renderText(node) {
    if (node.parentElement?.closest("script, style, noscript, #site-language")) return;
    const previous = textRecords.get(node);
    const source = previous && node.nodeValue === previous.rendered ? previous.source : node.nodeValue;
    const rendered = translate(source);
    textRecords.set(node, { source, rendered });
    if (node.nodeValue !== rendered) node.nodeValue = rendered;
  }

  function renderAttributes(element) {
    const remembered = attributeRecords.get(element) || {};
    for (const name of attributes) {
      if (!element.hasAttribute(name)) continue;
      const current = element.getAttribute(name);
      const previous = remembered[name];
      const source = previous && current === previous.rendered ? previous.source : current;
      const rendered = translate(source);
      remembered[name] = { source, rendered };
      if (current !== rendered) element.setAttribute(name, rendered);
    }
    attributeRecords.set(element, remembered);
  }

  function renderSubtree(root) {
    if (root.nodeType === Node.TEXT_NODE) { renderText(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    renderAttributes(root);
    for (const element of root.querySelectorAll("*")) renderAttributes(element);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) renderText(walker.currentNode);
  }

  function applyLanguage() {
    document.documentElement.lang = language;
    document.documentElement.dir = catalogs[language].dir;
    document.title = translate(sourceTitle);
    const select = document.querySelector("#site-language");
    if (select) select.value = language;
    renderSubtree(document.body);
  }

  function setLanguage(next) {
    if (!codes.includes(next)) return;
    language = next;
    try { localStorage.setItem("talent-geo-language", language); } catch (_) { /* Storage can be disabled. */ }
    if (window.location?.href && window.history?.replaceState) {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", language);
      window.history.replaceState(null, "", url);
    }
    applyLanguage();
    document.dispatchEvent(new CustomEvent("footballlanguagechange", { detail: { language } }));
    document.dispatchEvent(new CustomEvent("talentgeolanguagechange", { detail: { language } }));
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "characterData") renderText(mutation.target);
      else if (mutation.type === "attributes") renderAttributes(mutation.target);
      else for (const node of mutation.addedNodes) renderSubtree(node);
    }
  });

  if (!document.querySelector("#site-language")) {
    document.querySelector(".site-header .sport-switcher")?.insertAdjacentHTML("afterend", '<label class="language-control" for="site-language"><span>Language</span><select id="site-language" aria-label="Language"></select></label>');
  }
  const selector = document.querySelector("#site-language");
  if (selector) selector.innerHTML = codes.map((code) => `<option value="${code}">${catalogs[code].name}${catalogs[code].status === "preview" ? " · " + catalogs[code].previewLabel : ""}</option>`).join("");
  window.TalentGeoLanguage = window.FootballLanguage = { get language() { return language; }, get locale() { return locales[language]; }, setLanguage, translate, message, languages: codes };
  applyLanguage();
  document.querySelector("#site-language")?.addEventListener("change", (event) => setLanguage(event.target.value));
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: attributes });
})();
