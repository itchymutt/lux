/**
 * Tests for the libgaze-ts CLI.
 *
 * Run: node --test test/test_cli.js
 * Requires: npm run build first
 */

import { describe, it, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, "..", "dist", "src", "cli.js");

function run(...args) {
  try {
    const stdout = execFileSync("node", [CLI, ...args], {
      encoding: "utf-8",
      timeout: 30000,
    });
    return { stdout, stderr: "", exitCode: 0 };
  } catch (err) {
    return { stdout: err.stdout || "", stderr: err.stderr || "", exitCode: err.status };
  }
}

// ---------------------------------------------------------------------------
// check command
// ---------------------------------------------------------------------------

describe("CLI check", () => {
  const tmpDir = mkdtempSync(join(tmpdir(), "libgaze-cli-"));
  const pureFile = join(tmpDir, "pure.ts");
  writeFileSync(pureFile, `
    function add(a: number, b: number): number { return a + b; }
    function multiply(a: number, b: number): number { return a * b; }
  `);
  const effectfulFile = join(tmpDir, "effectful.ts");
  writeFileSync(effectfulFile, `
    function greet() { console.log("hello"); }
    function dangerous(code: string) { eval(code); }
    function add(a: number, b: number) { return a + b; }
  `);

  after(() => rmSync(tmpDir, { recursive: true }));

  it("reports pure file with function count", () => {
    const { stdout, exitCode } = run("check", pureFile);
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("(pure"));
    assert.ok(stdout.includes("functions"));
  });

  it("reports effectful file", () => {
    const { stdout, exitCode } = run("check", effectfulFile);
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("Console"));
    assert.ok(stdout.includes("Unsafe"));
  });

  it("outputs valid JSON with --json", () => {
    const { stdout, exitCode } = run("check", effectfulFile, "--json");
    assert.equal(exitCode, 0);
    const data = JSON.parse(stdout);
    assert.ok("file" in data);
    assert.ok("effects" in data);
    assert.ok("functions" in data);
    assert.ok(Array.isArray(data.effects));
    assert.ok(data.effects.includes("Console"));
    assert.ok(data.effects.includes("Unsafe"));
  });

  it("JSON marks pure functions correctly", () => {
    const { stdout } = run("check", pureFile, "--json");
    const data = JSON.parse(stdout);
    assert.ok(data.functions.every(fn => fn.pure === true));
    assert.deepEqual(data.effects, []);
  });

  it("--deny passes when effects not present", () => {
    const { exitCode } = run("check", pureFile, "--deny", "Unsafe,Net");
    assert.equal(exitCode, 0);
  });

  it("--deny fails when effects present", () => {
    const { stdout, exitCode } = run("check", effectfulFile, "--deny", "Unsafe");
    assert.equal(exitCode, 1);
    assert.ok(stdout.includes("FAIL"));
    assert.ok(stdout.includes("Unsafe"));
  });

  it("fails on missing file", () => {
    const { exitCode, stderr } = run("check", "/nonexistent/file.ts");
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("error"));
  });

  it("fails with no arguments", () => {
    const { exitCode } = run("check");
    assert.equal(exitCode, 1);
  });
});

// ---------------------------------------------------------------------------
// scan command
// ---------------------------------------------------------------------------

describe("CLI scan", () => {
  const tmpDir = mkdtempSync(join(tmpdir(), "libgaze-scan-"));
  writeFileSync(join(tmpDir, "pure.ts"), `
    function add(a: number, b: number) { return a + b; }
  `);
  writeFileSync(join(tmpDir, "effectful.ts"), `
    function greet() { console.log("hello"); }
  `);

  after(() => rmSync(tmpDir, { recursive: true }));

  it("scans a directory", () => {
    const { stdout, exitCode } = run("scan", tmpDir);
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("files scanned"));
  });

  it("--quiet hides pure files", () => {
    const { stdout } = run("scan", tmpDir, "--quiet");
    assert.ok(!stdout.includes("(pure)"));
  });

  it("--deny fails when effects present", () => {
    const { stdout, exitCode } = run("scan", tmpDir, "--deny", "Console");
    assert.equal(exitCode, 1);
    assert.ok(stdout.includes("FAIL"));
  });

  it("--deny passes when clean", () => {
    const cleanDir = mkdtempSync(join(tmpdir(), "libgaze-clean-"));
    writeFileSync(join(cleanDir, "pure.ts"), `
      function add(a: number, b: number) { return a + b; }
    `);
    const { exitCode } = run("scan", cleanDir, "--deny", "Unsafe,Net");
    assert.equal(exitCode, 0);
    rmSync(cleanDir, { recursive: true });
  });

  it("fails on missing directory", () => {
    const { exitCode, stderr } = run("scan", "/nonexistent/dir");
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("error"));
  });
});

// ---------------------------------------------------------------------------
// help
// ---------------------------------------------------------------------------

describe("CLI help", () => {
  it("shows help with --help", () => {
    const { stdout, exitCode } = run("--help");
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("libgaze-ts"));
    assert.ok(stdout.includes("check"));
    assert.ok(stdout.includes("scan"));
  });

  it("shows help with -h", () => {
    const { stdout, exitCode } = run("-h");
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("libgaze-ts"));
  });

  it("fails on unknown command", () => {
    const { exitCode, stderr } = run("unknown");
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("Unknown command"));
  });
});
