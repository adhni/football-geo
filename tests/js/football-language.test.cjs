const assert = require("node:assert/strict");
const { readFileSync, readdirSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function languageHarness(saved = null, title = "Football Talent Geography", search = "") {
  const values = new Map(saved ? [["football-geo-language", saved]] : []);
  const button = {
    label: "Close player profile",
    closest() { return null; },
    hasAttribute(name) { return name === "aria-label"; },
    getAttribute() { return this.label; },
    setAttribute(_name, value) { this.label = value; },
  };
  const body = {
    nodeType: 1,
    closest() { return null; },
    hasAttribute() { return false; },
    querySelectorAll() { return [button]; },
  };
  const parent = { closest() { return null; } };
  const headline = { nodeType: 3, nodeValue: "Players", parentElement: parent };
  const select = { value: "en", addEventListener(type, callback) { this.onChange = callback; } };
  const document = {
    body,
    title,
    documentElement: { lang: "en", dir: "ltr" },
    querySelector(selector) { return selector === "#site-language" ? select : null; },
    createTreeWalker(root) {
      const nodes = root === body ? [headline] : [];
      let index = -1;
      return { currentNode: null, nextNode() { this.currentNode = nodes[++index]; return !!this.currentNode; } };
    },
    dispatchEvent() {},
  };
  let observer;
  class MutationObserver {
    constructor(callback) { this.callback = callback; observer = this; }
    observe() {}
  }
  const context = {
    URL, URLSearchParams,
    window: { location: { search } }, document, localStorage: { getItem(key) { return values.get(key); }, setItem(key, value) { values.set(key, value); } },
    MutationObserver, CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 }, NodeFilter: { SHOW_TEXT: 4 },
  };
  vm.runInNewContext(readFileSync(resolve(__dirname, "../../docs/assets/language-catalog.js"), "utf8"), context);
  vm.runInNewContext(readFileSync(resolve(__dirname, "../../docs/assets/site-language.js"), "utf8"), context);
  return { language: context.window.FootballLanguage, document, headline, select, values, observer, parent, button };
}

test("football languages translate the page and restore the English source", () => {
  const { language, document, headline, select, values, button } = languageHarness();
  assert.equal(headline.nodeValue, "Players");
  language.setLanguage("es");
  assert.equal(headline.nodeValue, "Jugadores");
  assert.equal(button.label, "Cerrar perfil del jugador");
  assert.equal(language.translate("Birthplace coverage"), "Cobertura de lugares de nacimiento");
  assert.equal(language.translate("France"), "Francia");
  assert.equal(language.translate("France reference area"), "Zona de referencia: Francia");
  assert.equal(language.translate("All five leagues · All clubs · 2025–26"), "Las cinco ligas · Todos los clubes · 2025–26");
  assert.equal(values.get("talent-geo-language"), "es");
  assert.equal(select.value, "es");
  language.setLanguage("fr");
  assert.equal(headline.nodeValue, "Joueurs");
  assert.equal(language.translate("London, Germany"), "London, Allemagne");
  language.setLanguage("ar");
  assert.equal(headline.nodeValue, "اللاعبون");
  assert.equal(document.documentElement.dir, "rtl");
  language.setLanguage("id");
  assert.equal(headline.nodeValue, "Pemain");
  assert.equal(document.documentElement.dir, "ltr");
  language.setLanguage("en");
  assert.equal(headline.nodeValue, "Players");
  assert.equal(button.label, "Close player profile");
  assert.equal(document.title, "Football Talent Geography");
});

test("language catalogs fix mixed-language compounds and choose singular counts", () => {
  const { language } = languageHarness("es");
  assert.equal(language.translate("Find an NBA player"), "Buscar Jugador · NBA");
  assert.equal(language.translate("Search NBA players"), "Buscar jugadores · NBA");
  assert.equal(language.translate("Minutes and mapped birthplace coverage"), "Minutos y cobertura de lugares de nacimiento");
  assert.equal(language.translate("Compare Full Member sides"), "Comparar selecciones de miembros plenos");
  assert.equal(language.translate("1 players"), "1 jugador");
  assert.equal(language.translate("2 players"), "2 jugadores");
  language.setLanguage("en");
  assert.equal(language.translate("1 players"), "1 player");
  assert.equal(language.translate("2 players"), "2 players");
});

test("new language previews translate controls and dynamic templates with a safe source fallback", () => {
  const { language, document, select } = languageHarness();
  for (const [code, players, country] of [["pt", "Jogadores", "Alemanha"], ["de", "Spieler", "Deutschland"], ["it", "Giocatori", "Germania"]]) {
    language.setLanguage(code);
    assert.equal(language.translate("Players"), players);
    assert.equal(language.translate("Germany"), country);
    assert.equal(document.documentElement.lang, code);
    assert.equal(document.documentElement.dir, "ltr");
    assert.doesNotMatch(language.translate("All 32 teams"), /undefined|\{p1\}/);
    assert.doesNotMatch(language.translate("Germany reference area"), /undefined|\{name\}/);
    assert.equal(language.translate("Unknown source description"), "Unknown source description");
  }
  assert.match(select.innerHTML, /Português/);
  assert.match(select.innerHTML, /Anteprima/);
});

test("shareable language selection takes precedence over the saved preference", () => {
  const { language, document } = languageHarness("ar", "Tennis Talent Geography", "?lang=it");
  assert.equal(language.language, "it");
  assert.equal(document.documentElement.dir, "ltr");
  assert.equal(languageHarness("fr", "Tennis Talent Geography", "?lang=invalid").language.language, "fr");
});

test("saved language applies to new dashboard text", () => {
  const { language, document, headline, observer, parent } = languageHarness("ar");
  assert.equal(document.documentElement.lang, "ar");
  assert.equal(headline.nodeValue, "اللاعبون");
  const popupText = { nodeType: 3, nodeValue: "No mapped players in this selection", parentElement: parent };
  observer.callback([{ type: "childList", addedNodes: [popupText] }]);
  assert.equal(popupText.nodeValue, "لا يوجد لاعبون محددو الموقع في هذا الاختيار");
  popupText.nodeValue = "Population unavailable";
  observer.callback([{ type: "characterData", target: popupText }]);
  assert.equal(popupText.nodeValue, "بيانات السكان غير متاحة");
  language.setLanguage("en");
  observer.callback([{ type: "characterData", target: popupText }]);
  assert.equal(popupText.nodeValue, "Population unavailable");
});

test("every sport, directory, and comparison page loads the shared language selector", () => {
  const docs = resolve(__dirname, "../../docs");
  const pages = [resolve(docs, "index.html"), ...readdirSync(docs, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && readdirSync(resolve(docs, entry.name)).includes("index.html"))
    .map((entry) => resolve(docs, entry.name, "index.html"))];
  const catalog = JSON.parse(readFileSync(resolve(__dirname, "../../config/editions.json"), "utf8"));
  assert.equal(pages.length, catalog.editions.length + 2);
  for (const page of pages) {
    const html = readFileSync(page, "utf8");
    assert.match(html, /assets\/site-language\.js/ , page);
    assert.ok(html.indexOf("site-language.js") < html.indexOf("sport-navigation.js"), page);
  }
});

test("saved language translates another sport title and sport-specific copy", () => {
  const { language, document } = languageHarness("fr", "NBA Talent Geography");
  assert.equal(document.title, "NBA · Géographie du talent");
  assert.equal(language.translate("NBA players matching the current filters"), "Joueurs NBA correspondant aux filtres");
  assert.equal(language.translate("Team comparison"), "Comparaison des équipes");
  language.setLanguage("ar");
  assert.equal(document.documentElement.dir, "rtl");
  assert.equal(language.translate("Compare MLB"), "قارن دوري البيسبول الأمريكي");
});
