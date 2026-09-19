const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function clipboardHarness(writeText) {
  const copy = new EventTarget();
  copy.textContent = "Copy link";
  const swap = new EventTarget();
  const toast = { textContent: "", classList: { add() {}, remove() {} } };
  const timers = [];
  const context = {
    URL, URLSearchParams,
    window: {
      location: { href: "https://example.test/compare/", search: "" },
      history: { replaceState() {} },
      addEventListener() {}, clearTimeout() {},
      setTimeout(callback) { timers.push(callback); },
    },
    navigator: { clipboard: { writeText } },
    document: {
      querySelectorAll: () => [],
      querySelector: (selector) => ({ "#copy-link": copy, "#swap-sports": swap, "#error-toast": toast })[selector],
    },
  };
  const source = readFileSync(resolve(__dirname, "../../docs/compare/compare.js"), "utf8");
  // Bind the production handlers without booting Leaflet or fetching datasets.
  // EventTarget supplies real dispatch semantics, including currentTarget cleanup.
  assert.match(source, /\n  init\(\);\n/);
  vm.runInNewContext(source.replace(/\n  init\(\);\n/, "\n  bindEvents();\n"), context);
  return { copy, toast, timers };
}

function comparisonDataHarness() {
  const context = {
    URL, URLSearchParams,
    window: {
      location: { href: "https://example.test/compare/", search: "" },
      TalentGeoNavigation: { sports: [], rootUrl: new URL("https://example.test/") },
    },
    document: {},
  };
  const source = readFileSync(resolve(__dirname, "../../docs/compare/compare.js"), "utf8");
  vm.runInNewContext(source.replace(/\n  init\(\);\n/, "\n  window.comparisonData = { mappedPeople, aggregatePlaces, populationCells };\n"), context);
  return context.window.comparisonData;
}

test("football people are counted once while club workloads are summed", () => {
  const { mappedPeople, aggregatePlaces, populationCells } = comparisonDataHarness();
  const sport = { workloadField: "starts" };
  const records = [
    { id: "a", mapped: true, lat: 51.5, lon: -.1, place: "London", country: "United Kingdom", starts: 20 },
    { id: "a", mapped: true, lat: 51.5, lon: -.1, place: "London", country: "United Kingdom", starts: 17 },
    { id: "b", mapped: true, lat: 51.5, lon: -.1, place: "London", country: "United Kingdom", starts: 10 },
  ];
  const features = [{ properties: { player_ids: ["a", "b"], population: 100000, label: "London", country: "United Kingdom" } }];

  assert.equal(mappedPeople(records, sport).size, 2);
  assert.deepEqual(Array.from(aggregatePlaces(records, sport), (place) => [place.people, place.workload]), [[2, 47]]);
  assert.deepEqual(Array.from(populationCells(records, { features }, sport, "workload"), (cell) => [cell.people, cell.workload, cell.rate]), [[2, 47, 470]]);
});

test("population comparison retains empty reference cells and excludes origin fallbacks", () => {
  const { populationCells } = comparisonDataHarness();
  const sport = { workloadField: "starts" };
  const records = [
    { id: "a", mapped: true, locationType: "birthplace", starts: 3 },
    { id: "b", mapped: true, locationType: "football_origin", starts: 4 },
  ];
  const features = [
    { properties: { player_ids: ["a"], population: 100000, label: "Active", country: "Testland" } },
    { properties: { player_ids: ["b"], population: 200000, label: "Origin", country: "Testland" } },
    { properties: { player_ids: [], population: 300000, label: "Reference", country: "Testland" } },
  ];

  assert.deepEqual(Array.from(populationCells(records, { features }, sport, "people"), (cell) => [cell.people, cell.reference, cell.rate]), [
    [1, false, 10], [0, true, 0], [0, true, 0],
  ]);
});

test("copy link survives asynchronous clipboard completion and resets its label", async () => {
  let copied;
  let complete;
  const harness = clipboardHarness((text) => {
    copied = text;
    return new Promise((resolve) => { complete = resolve; });
  });
  const event = new Event("click");
  harness.copy.dispatchEvent(event);
  assert.equal(event.currentTarget, null);
  assert.equal(harness.copy.textContent, "Copy link");
  complete();
  await new Promise(setImmediate);
  assert.equal(copied, "https://example.test/compare/");
  assert.equal(harness.copy.textContent, "Copied");
  assert.equal(harness.toast.textContent, "");
  harness.timers[0]();
  assert.equal(harness.copy.textContent, "Copy link");
});

test("a rejected clipboard request displays the failure without a success label", async () => {
  const harness = clipboardHarness(async () => { throw new Error("Permission denied"); });
  harness.copy.dispatchEvent(new Event("click"));
  await new Promise(setImmediate);
  assert.equal(harness.copy.textContent, "Copy link");
  assert.match(harness.toast.textContent, /Copy failed/);
});
