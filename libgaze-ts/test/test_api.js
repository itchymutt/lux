/**
 * Unit tests for libgaze-ts API surface.
 *
 * Run: node --test test/test_api.js
 * Requires: npm run build first (tests import from dist/)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { analyzeSource, analyzeFilePath, Effect } from "../dist/src/index.js";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

// ---------------------------------------------------------------------------
// analyzeSource
// ---------------------------------------------------------------------------

describe("analyzeSource", () => {
  it("returns a ModuleEffects object", () => {
    const result = analyzeSource("const x = 1;");
    assert.ok(result);
    assert.ok("path" in result);
    assert.ok("functions" in result);
    assert.ok("allEffects" in result);
    assert.ok("moduleEffects" in result);
  });

  it("defaults path to <string>", () => {
    const result = analyzeSource("const x = 1;");
    assert.equal(result.path, "<string>");
  });

  it("accepts a custom path", () => {
    const result = analyzeSource("const x = 1;", "custom.ts");
    assert.equal(result.path, "custom.ts");
  });

  it("detects no effects in pure code", () => {
    const result = analyzeSource(`
      function add(a: number, b: number): number {
        return a + b;
      }
    `);
    assert.equal(result.allEffects.size, 0);
    assert.equal(result.functions.length, 1);
    assert.ok(result.functions[0].pure);
  });

  it("detects Console from console.log", () => {
    const result = analyzeSource(`
      function greet() {
        console.log("hello");
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Console"));
    assert.ok(!fn.pure);
  });

  it("detects Net from fetch", () => {
    const result = analyzeSource(`
      function getData(url: string) {
        return fetch(url);
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Net"));
  });

  it("detects Env from process.env", () => {
    const result = analyzeSource(`
      function getKey() {
        return process.env.API_KEY;
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Env"));
  });

  it("detects Fs from node:fs import", () => {
    const result = analyzeSource(`
      import { readFileSync } from "node:fs";
      function readConfig() {
        return readFileSync("config.json", "utf-8");
      }
    `);
    assert.ok(result.allEffects.has("Fs"));
  });

  it("detects Unsafe from eval", () => {
    const result = analyzeSource(`
      function dangerous(code: string) {
        return eval(code);
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Unsafe"));
  });

  it("detects Time from setTimeout", () => {
    const result = analyzeSource(`
      function delay(ms: number) {
        setTimeout(() => {}, ms);
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Time"));
  });

  it("detects Rand from Math.random", () => {
    const result = analyzeSource(`
      function roll() {
        return Math.random();
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Rand"));
  });

  it("detects Fail from process.exit", () => {
    const result = analyzeSource(`
      function bail() {
        process.exit(1);
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.effects.has("Fail"));
  });

  it("detects Db from pg import", () => {
    const result = analyzeSource(`
      import { Pool } from "pg";
      function query() {
        const pool = new Pool();
      }
    `);
    assert.ok(result.allEffects.has("Db"));
  });

  it("handles empty source", () => {
    const result = analyzeSource("");
    assert.equal(result.functions.length, 0);
    assert.equal(result.allEffects.size, 0);
  });

  it("records evidence for effects", () => {
    const result = analyzeSource(`
      function greet() {
        console.log("hello");
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.evidence.length > 0);
    assert.ok(fn.evidence.some(e => e.includes("console.log")));
  });

  it("records calls for functions", () => {
    const result = analyzeSource(`
      function helper() { console.log("x"); }
      function main() { helper(); }
    `);
    const mainFn = result.functions.find(f => f.name === "main");
    assert.ok(mainFn);
    assert.ok(mainFn.calls.includes("helper"));
  });
});

// ---------------------------------------------------------------------------
// analyzeFilePath
// ---------------------------------------------------------------------------

describe("analyzeFilePath", () => {
  let tmpDir;

  it("analyzes a real file", () => {
    tmpDir = mkdtempSync(join(tmpdir(), "libgaze-test-"));
    const filePath = join(tmpDir, "test.ts");
    writeFileSync(filePath, `
      function add(a: number, b: number) { return a + b; }
      function greet() { console.log("hi"); }
    `);
    const result = analyzeFilePath(filePath);
    assert.equal(result.functions.length, 2);
    assert.ok(result.allEffects.has("Console"));
    rmSync(tmpDir, { recursive: true });
  });

  it("throws on nonexistent file", () => {
    assert.throws(() => {
      analyzeFilePath("/nonexistent/file.ts");
    });
  });
});

// ---------------------------------------------------------------------------
// Call graph propagation
// ---------------------------------------------------------------------------

describe("call graph propagation", () => {
  it("propagates through this.method()", () => {
    const result = analyzeSource(`
      class Service {
        connect() { return fetch("http://example.com"); }
        run() { this.connect(); }
      }
    `);
    const run = result.functions.find(f => f.name === "run");
    assert.ok(run);
    assert.ok(run.effects.has("Net"));
  });

  it("propagates through ClassName.method()", () => {
    const result = analyzeSource(`
      class Logger {
        static log(msg: string) { console.log(msg); }
      }
      function process() { Logger.log("done"); }
    `);
    const process = result.functions.find(f => f.name === "process");
    assert.ok(process);
    assert.ok(process.effects.has("Console"));
  });

  it("propagates through bare function calls", () => {
    const result = analyzeSource(`
      function writeLog() { console.log("entry"); }
      function process() { writeLog(); }
    `);
    const process = result.functions.find(f => f.name === "process");
    assert.ok(process);
    assert.ok(process.effects.has("Console"));
  });

  it("handles transitive propagation", () => {
    const result = analyzeSource(`
      function a() { console.log("x"); }
      function b() { a(); }
      function c() { b(); }
    `);
    const c = result.functions.find(f => f.name === "c");
    assert.ok(c);
    assert.ok(c.effects.has("Console"));
  });

  it("does not self-recurse infinitely", () => {
    const result = analyzeSource(`
      function recurse(n: number): number {
        if (n > 0) return recurse(n - 1);
        return 0;
      }
    `);
    const fn = result.functions[0];
    assert.ok(fn.pure);
  });
});

// ---------------------------------------------------------------------------
// Arrow functions and variable declarations
// ---------------------------------------------------------------------------

describe("arrow functions", () => {
  it("detects effects in arrow functions", () => {
    const result = analyzeSource(`
      const greet = () => { console.log("hi"); };
    `);
    assert.equal(result.functions.length, 1);
    assert.ok(result.functions[0].effects.has("Console"));
  });

  it("detects effects in function expressions", () => {
    const result = analyzeSource(`
      const greet = function() { console.log("hi"); };
    `);
    assert.equal(result.functions.length, 1);
    assert.ok(result.functions[0].effects.has("Console"));
  });
});

// ---------------------------------------------------------------------------
// Effect enum
// ---------------------------------------------------------------------------

describe("Effect enum", () => {
  it("has all ten effects", () => {
    const effects = [
      Effect.Net, Effect.Fs, Effect.Db, Effect.Console, Effect.Env,
      Effect.Time, Effect.Rand, Effect.Async, Effect.Unsafe, Effect.Fail,
    ];
    assert.equal(effects.length, 10);
  });

  it("values are capitalized strings", () => {
    assert.equal(Effect.Net, "Net");
    assert.equal(Effect.Fs, "Fs");
    assert.equal(Effect.Unsafe, "Unsafe");
  });
});

// ---------------------------------------------------------------------------
// Module-level effects
// ---------------------------------------------------------------------------

describe("module-level effects", () => {
  it("detects effects from imports", () => {
    const result = analyzeSource(`
      import axios from "axios";
    `);
    assert.ok(result.moduleEffects.has("Net"));
  });

  it("detects effects from require()", () => {
    const result = analyzeSource(`
      const fs = require("node:fs");
    `);
    assert.ok(result.moduleEffects.has("Fs"));
  });
});
