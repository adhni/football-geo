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
