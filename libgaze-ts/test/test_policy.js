/**
 * Tests for the policy system.
 *
 * Run: node --test test/test_policy.js
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

import { analyzeSource } from "../dist/src/index.js";
import { loadPolicy, checkPolicy } from "../dist/src/policy.js";

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
// Policy loading
// ---------------------------------------------------------------------------

describe("loadPolicy", () => {
  const tmpDir = mkdtempSync(join(tmpdir(), "libgaze-policy-"));
  after(() => rmSync(tmpDir, { recursive: true }));

  it("loads a deny policy", () => {
    const policyFile = join(tmpDir, "deny.gazepolicy");
    writeFileSync(policyFile, JSON.stringify({ deny: ["Unsafe", "Db"] }));
    const policy = loadPolicy(policyFile);
    assert.ok(policy.deny);
    assert.ok(policy.deny.has("Unsafe"));
    assert.ok(policy.deny.has("Db"));
    assert.equal(policy.allow, null);
  });

  it("loads an allow policy", () => {
    const policyFile = join(tmpDir, "allow.gazepolicy");
    writeFileSync(policyFile, JSON.stringify({ allow: ["Net", "Fs"] }));
    const policy = loadPolicy(policyFile);
    assert.ok(policy.allow);
    assert.ok(policy.allow.has("Net"));
    assert.ok(policy.allow.has("Fs"));
    assert.equal(policy.deny, null);
  });

  it("loads function-level policies", () => {
    const policyFile = join(tmpDir, "fn.gazepolicy");
    writeFileSync(policyFile, JSON.stringify({
      deny: ["Unsafe"],
      functions: { transform: { allow: [] } },
    }));
    const policy = loadPolicy(policyFile);
    assert.ok(policy.functions);
    assert.ok(policy.functions.has("transform"));
    const fnPolicy = policy.functions.get("transform");
    assert.ok(fnPolicy.allow);
    assert.equal(fnPolicy.allow.size, 0);
  });

  it("throws on allow + deny at same level", () => {
    const policyFile = join(tmpDir, "bad.gazepolicy");
    writeFileSync(policyFile, JSON.stringify({ allow: ["Net"], deny: ["Unsafe"] }));
    assert.throws(() => loadPolicy(policyFile), /both 'allow' and 'deny'/);
  });
});

// ---------------------------------------------------------------------------
// Policy checking (API)
// ---------------------------------------------------------------------------

describe("checkPolicy", () => {
  it("deny policy catches denied effects", () => {
    const result = analyzeSource(`
      function dangerous(code: string) { eval(code); }
    `);
    const policy = { allow: null, deny: new Set(["Unsafe"]), functions: null };
    const violations = checkPolicy(result, policy);
    assert.ok(violations.length > 0);
    assert.ok(violations.some(v => v.effect === "Unsafe"));
  });

  it("deny policy passes clean code", () => {
    const result = analyzeSource(`
      function add(a: number, b: number) { return a + b; }
    `);
    const policy = { allow: null, deny: new Set(["Unsafe"]), functions: null };
    const violations = checkPolicy(result, policy);
    assert.equal(violations.length, 0);
  });

  it("allow policy permits listed effects", () => {
    const result = analyzeSource(`
      function greet() { console.log("hi"); }
    `);
    const policy = { allow: new Set(["Console"]), deny: null, functions: null };
    const violations = checkPolicy(result, policy);
    assert.equal(violations.length, 0);
  });

  it("allow policy denies unlisted effects", () => {
    const result = analyzeSource(`
      function greet() { console.log("hi"); }
    `);
    const policy = { allow: new Set(["Net"]), deny: null, functions: null };
    const violations = checkPolicy(result, policy);
    assert.ok(violations.length > 0);
    assert.ok(violations.some(v => v.effect === "Console"));
  });

  it("empty allow requires pure", () => {
    const result = analyzeSource(`
      function greet() { console.log("hi"); }
      function add(a: number, b: number) { return a + b; }
    `);
    const policy = { allow: new Set(), deny: null, functions: null };
    const violations = checkPolicy(result, policy);
    assert.ok(violations.length > 0);
    assert.ok(violations.every(v => v.function === "greet"));
  });

  it("function-level policy overrides module-level", () => {
    const result = analyzeSource(`
      function greet() { console.log("hi"); }
      function dangerous(code: string) { eval(code); }
    `);
    // Module: deny Unsafe. Function "greet": must be pure (allow nothing).
    const policy = {
      allow: null,
      deny: new Set(["Unsafe"]),
      functions: new Map([["greet", { allow: new Set(), deny: null, functions: null }]]),
    };
    const violations = checkPolicy(result, policy);
    // greet violates its function-level allow (Console not in empty set)
    // dangerous violates module-level deny (Unsafe)
    const greetV = violations.filter(v => v.function === "greet");
    const dangerousV = violations.filter(v => v.function === "dangerous");
    assert.ok(greetV.length > 0);
    assert.ok(dangerousV.length > 0);
  });

  it("checks module-level effects", () => {
    const result = analyzeSource(`
      import axios from "axios";
    `);
    const policy = { allow: null, deny: new Set(["Net"]), functions: null };
    const violations = checkPolicy(result, policy);
    const moduleV = violations.filter(v => v.function === "(module level)");
    assert.ok(moduleV.length > 0);
  });
});

// ---------------------------------------------------------------------------
// Policy CLI command
// ---------------------------------------------------------------------------

describe("CLI policy", () => {
  const tmpDir = mkdtempSync(join(tmpdir(), "libgaze-policy-cli-"));

  const pureFile = join(tmpDir, "pure.ts");
  writeFileSync(pureFile, `
    function add(a: number, b: number) { return a + b; }
  `);

  const effectfulFile = join(tmpDir, "effectful.ts");
  writeFileSync(effectfulFile, `
    function greet() { console.log("hello"); }
    function dangerous(code: string) { eval(code); }
  `);

  const denyPolicy = join(tmpDir, "deny.gazepolicy");
  writeFileSync(denyPolicy, JSON.stringify({ deny: ["Unsafe", "Db"] }));

  const purePolicy = join(tmpDir, "pure.gazepolicy");
  writeFileSync(purePolicy, JSON.stringify({ allow: [] }));

  after(() => rmSync(tmpDir, { recursive: true }));

  it("passes clean code", () => {
    const { stdout, exitCode } = run("policy", pureFile, "-p", denyPolicy);
    assert.equal(exitCode, 0);
    assert.ok(stdout.includes("PASS"));
  });

  it("fails on violations", () => {
    const { stdout, exitCode } = run("policy", effectfulFile, "-p", denyPolicy);
    assert.equal(exitCode, 1);
    assert.ok(stdout.includes("FAIL"));
    assert.ok(stdout.includes("Unsafe"));
    assert.ok(stdout.includes("violation"));
  });

  it("outputs JSON with --json", () => {
    const { stdout, exitCode } = run("policy", effectfulFile, "-p", denyPolicy, "--json");
    assert.equal(exitCode, 1);
    const data = JSON.parse(stdout);
    assert.equal(data.pass, false);
    assert.ok(data.violations.length > 0);
    assert.ok(data.violations.some(v => v.effect === "Unsafe"));
  });

  it("JSON passes for clean code", () => {
    const { stdout, exitCode } = run("policy", pureFile, "-p", denyPolicy, "--json");
    assert.equal(exitCode, 0);
    const data = JSON.parse(stdout);
    assert.equal(data.pass, true);
    assert.equal(data.violations.length, 0);
  });

  it("enforces purity with empty allow", () => {
    const { stdout, exitCode } = run("policy", effectfulFile, "-p", purePolicy);
    assert.equal(exitCode, 1);
    assert.ok(stdout.includes("FAIL"));
  });

  it("fails on missing file", () => {
    const { exitCode, stderr } = run("policy", "/nonexistent.ts", "-p", denyPolicy);
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("not found"));
  });

  it("fails on missing policy file", () => {
    const { exitCode, stderr } = run("policy", pureFile, "-p", "/nonexistent.gazepolicy");
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("not found"));
  });

  it("fails without -p flag", () => {
    const { exitCode, stderr } = run("policy", pureFile);
    assert.equal(exitCode, 1);
    assert.ok(stderr.includes("--policy/-p"));
  });
});
