const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function explorer(edition, records) {
  const context = {
    window: { TALENT_GEO_EDITION: edition },
    document: { addEventListener() {} },
  };
  const source = readFileSync(resolve(__dirname, "../../docs/assets/league-app.js"), "utf8");
  vm.runInNewContext(source.replace(/\nboot\(\);\s*$/, "\nwindow.explorer = { state, filteredRecords, filteredTeamRecords, aggregatePopulationCells, aggregatePlaces, aggregateCountries, aggregateTeamPlaces, metricLabel, metricValue };"), context);
  const app = context.window.explorer;
  app.state.payload = { records };
  return app;
}

test("athletics event selection scopes entries, rounds and medals in maps and team charts", () => {
  const payload = JSON.parse(readFileSync(resolve(__dirname, "../../docs/athletics/data/dashboard.json"), "utf8"));
  const original = JSON.stringify(payload.records);
  const app = explorer({ profileLogType: "athletics", positionValuesField: "eventNames", workloadField: "entries", teamSplitStats: ["entries", "rounds", "medals", "gold", "silver", "bronze"] }, payload.records);
  app.state.position = "Men's 100 Metres";
  const rows = app.filteredRecords();
  assert.equal(rows.length, 73);
  assert.equal(rows.reduce((sum, row) => sum + row.minutes, 0), 73);
  assert.equal(rows.reduce((sum, row) => sum + row.medals, 0), 3);
  assert.equal(app.filteredTeamRecords().reduce((sum, row) => sum + row.entries, 0), 73);
  assert.ok(rows.every((row) => row.eventLog.length === 1 && row.rounds === row.eventLog[0].rounds));
  app.state.populationGeojson.set(3, { features: [{ properties: { player_ids: rows.map((row) => row.id), population: 1000000 } }] });
  app.state.mapMode = "population-workload";
  const cell = app.aggregatePopulationCells(rows)[0];
  const mapped = rows.filter((row) => row.mapped).length;
  assert.equal(cell.players, mapped);
  assert.equal(cell.workload, mapped);
  assert.equal(cell.rate, mapped);
  assert.equal(JSON.stringify(payload.records), original);
  app.state.position = "all";
  assert.equal(app.filteredRecords().reduce((sum, row) => sum + row.entries, 0), payload.summary.entries);
});

test("age and ranking selections exclude unknown values and apply ranks to the selected event", () => {
  const records = [
    { id: "a", age: 20, rank: 1, points: 150, teamSplits: [{ team: "Singles", conference: "Men", rank: 1, points: 100, minutes: 100, games: 1 }, { team: "Doubles", conference: "Men", rank: 50, points: 50, minutes: 50, games: 1 }] },
    { id: "b", age: null, rank: 2, team: "Doubles", conference: "Men" },
  ];
  const app = explorer({ teamSplitStats: ["points"], teamSplitMinStats: ["rank"] }, records);
  app.state.age = "u21";
  app.state.rank = "25";
  app.state.team = "Doubles";
  assert.equal(app.filteredRecords().length, 0);
  assert.equal(app.filteredTeamRecords().length, 0);
  app.state.team = "Singles";
  assert.deepEqual(Array.from(app.filteredRecords(), (row) => [row.id, row.rank, row.minutes]), [["a", 1, 100]]);
});

test("performance measures reconcile across city, country and team maps after team projection", () => {
  const app = explorer({ additionalMetrics: [{ field: "goals", label: "Goals" }], teamSplitStats: ["goals"] }, [
    { id: "a", name: "Transferred", country: "Canada", countryCode: "CAN", place: "Toronto", lat: 43, lon: -79, mapped: true, teamSplits: [{ team: "A", conference: "East", minutes: 20, games: 2, goals: 1 }, { team: "B", conference: "West", minutes: 30, games: 3, goals: 4 }] },
  ]);
  app.state.team = "B";
  app.state.metric = "goals";
  const rows = app.filteredRecords();
  assert.equal(app.metricLabel(), "Goals");
  assert.equal(app.metricValue(app.aggregatePlaces(rows)[0]), 4);
  assert.equal(app.aggregateCountries(rows)[0].goals, 4);
  assert.equal(app.aggregateTeamPlaces(app.filteredTeamRecords())[0].teamBubbles[0].goals, 4);
  assert.equal(rows[0].minutes, 30);
});

test("position filters select the same participants in maps and team charts while preserving transfers", () => {
  const records = [
    { id: "a", position: "Forward", country: "Canada", teamSplits: [{ team: "A", conference: "East", minutes: 10, games: 1 }, { team: "B", conference: "West", minutes: 20, games: 2 }] },
    { id: "b", position: "Goalie", country: "Canada", teamSplits: [{ team: "A", conference: "East", minutes: 99, games: 3 }] },
  ];
  const app = explorer({ teamSplitStats: [] }, records);
  app.state.position = "Forward";
  app.state.conference = "West";
  assert.deepEqual(Array.from(app.filteredRecords(), (row) => [row.id, row.minutes]), [["a", 20]]);
  assert.deepEqual(Array.from(app.filteredTeamRecords(), (row) => [row.id, row.team, row.minutes]), [["a", "B", 20]]);
  app.state.country = "Australia";
  assert.equal(app.filteredTeamRecords().length, 0);
});
