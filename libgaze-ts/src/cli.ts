#!/usr/bin/env node

/**
 * libgaze-ts CLI for TypeScript.
 *
 * Usage:
 *   libgaze-ts check <file.ts>
 *   libgaze-ts check <file.ts> --json
 *   libgaze-ts check <file.ts> --deny Unsafe,Db
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { analyzeFilePath } from "./analyzer.js";
import type { ModuleEffects } from "./analyzer.js";
import { loadPolicy, checkPolicy } from "./policy.js";
import type { PolicyViolation } from "./policy.js";

export function main(argv: string[] = process.argv.slice(2)): void {
  const args = argv;
  const command = args[0];

  if (!command || command === "--help" || command === "-h") {
    console.log(`libgaze-ts — See what your code does to the world before it runs.

Usage:
  libgaze-ts check <file.ts>              Report effects
  libgaze-ts check <file.ts> --json       Output as JSON
  libgaze-ts check <file.ts> --deny X,Y   Fail if effects found
  libgaze-ts scan <dir>                   Scan all TS files
  libgaze-ts scan <dir> --json            JSON output
  libgaze-ts scan <dir> --deny X          Fail if effects found
  libgaze-ts scan <dir> --quiet           Only show effectful files
  libgaze-ts policy <file.ts> -p .gazepolicy  Check against policy`);
    process.exit(0);
  }

  if (command === "check") {
    const filePath = args[1];
    if (!filePath) {
      console.error("error: missing file path");
      process.exit(1);
    }

    const jsonOutput = args.includes("--json");
    const denyIdx = args.indexOf("--deny");
    const denyEffects = denyIdx >= 0 ? args[denyIdx + 1]?.split(",") : null;

    let result: ModuleEffects;
    try {
      result = analyzeFilePath(resolve(filePath));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`error: ${msg}`);
      process.exit(1);
    }

    if (jsonOutput) {
      console.log(JSON.stringify(toJson(result), null, 2));
    } else {
      printReport(result);
    }

    if (denyEffects) {
      const denied = new Set(denyEffects);
      const found = [...result.allEffects].filter(e => denied.has(e));
      if (found.length > 0) {
        console.log(`\nFAIL  denied effects found: ${found.sort().join(", ")}`);
        process.exit(1);
      }
    }
  } else if (command === "scan") {
    const dirPath = args[1];
    if (!dirPath) {
      console.error("error: missing directory path");
      process.exit(1);
    }

    const denyIdx = args.indexOf("--deny");
    const denyEffects = denyIdx >= 0 ? args[denyIdx + 1]?.split(",") : null;
    const quiet = args.includes("--quiet") || args.includes("-q");
    const jsonOutput = args.includes("--json");

    let files: string[];
    try {
      files = collectTsFiles(resolve(dirPath));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`error: ${msg}`);
      process.exit(1);
    }

    const results: ModuleEffects[] = [];

    for (const f of files) {
      try {
        results.push(analyzeFilePath(f));
      } catch {
        // skip files that don't parse
      }
    }

    if (jsonOutput) {
      console.log(JSON.stringify(results.map(r => toJson(r)), null, 2));
    } else {
      const effectful = results.filter(r => r.allEffects.size > 0);
      const pure = results.filter(r => r.allEffects.size === 0);

      for (const r of effectful) {
        const effects = [...r.allEffects].sort().join(", ");
        const pureCount = r.functions.filter(f => f.pure).length;
        console.log(`  ${r.path}  can ${effects}  (${pureCount}/${r.functions.length} pure)`);
      }

      if (!quiet && pure.length > 0) {
        console.log();
        for (const r of pure) {
          console.log(`  ${r.path}  (pure)`);
        }
      }

      console.log();
      console.log(`${results.length} files scanned. ${effectful.length} effectful, ${pure.length} pure.`);
    }

    if (denyEffects) {
      const denied = new Set(denyEffects);
      const violations: string[] = [];
      for (const r of results) {
        const found = [...r.allEffects].filter(e => denied.has(e));
        if (found.length > 0) {
          violations.push(`  ${r.path}: ${found.sort().join(", ")}`);
        }
      }
      if (violations.length > 0) {
        if (!jsonOutput) console.log("\nFAIL  denied effects found:");
        for (const v of violations) console.log(v);
        process.exit(1);
      }
    }
  } else if (command === "policy") {
    const filePath = args[1];
    if (!filePath) {
      console.error("error: missing file path");
      process.exit(1);
    }

    const policyIdx = args.indexOf("--policy") >= 0 ? args.indexOf("--policy") : args.indexOf("-p");
    if (policyIdx < 0 || !args[policyIdx + 1]) {
      console.error("error: missing --policy/-p <path>");
      process.exit(1);
    }
    const policyPath = args[policyIdx + 1];
    const jsonOutput = args.includes("--json");

    if (!existsSync(resolve(filePath))) {
      console.error(`error: ${filePath} not found`);
      process.exit(1);
    }
    if (!existsSync(resolve(policyPath))) {
      console.error(`error: ${policyPath} not found`);
      process.exit(1);
    }

    let result: ModuleEffects;
    try {
      result = analyzeFilePath(resolve(filePath));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`error: ${msg}`);
      process.exit(1);
    }

    let policy;
    try {
      policy = loadPolicy(resolve(policyPath));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`error: ${policyPath}: ${msg}`);
      process.exit(1);
    }
    const violations = checkPolicy(result, policy);

    if (jsonOutput) {
      console.log(JSON.stringify({
        file: filePath,
        policy: policyPath,
        pass: violations.length === 0,
        violations: violations.map(v => ({
          function: v.function,
          line: v.line,
          effect: v.effect,
          reason: v.reason,
        })),
      }, null, 2));
      if (violations.length > 0) process.exit(1);
    } else {
      if (violations.length > 0) {
        console.log(`FAIL  ${filePath}`);
        console.log();

        let source: string[] = [];
        try { source = readFileSync(resolve(filePath), "utf-8").split("\n"); } catch {}

        for (const v of violations) {
          if (v.line > 0 && v.line <= source.length) {
            console.log(`  ${v.function}:${v.line}  ${v.effect} -- ${v.reason}`);
            console.log(`    ${v.line} | ${source[v.line - 1].trim()}`);
          } else {
            console.log(`  ${v.function}  ${v.effect} -- ${v.reason}`);
          }
        }
        console.log();
        console.log(`${violations.length} violation(s) found.`);
        process.exit(1);
      } else {
        console.log(`PASS  ${filePath}`);
      }
    }
  } else {
    console.error(`Unknown command: ${command}`);
    process.exit(1);
  }
}

// ---------------------------------------------------------------------------

function printReport(result: ModuleEffects): void {
  if (result.allEffects.size === 0) {
    const total = result.functions.length;
    if (total > 0) {
      console.log(`${result.path}  (pure, ${total} functions)`);
    } else {
      console.log(`${result.path}  (pure)`);
    }
    return;
  }

  const effects = [...result.allEffects].sort().join(", ");
  console.log(`${result.path}  can ${effects}`);
  console.log();

  const source = readFileSync(result.path, "utf-8");
  const lines = source.split("\n");

  for (const fn of result.functions) {
    if (fn.pure) {
      console.log(`  ${fn.name}:${fn.line}  (pure)`);
    } else {
      const fnEffects = [...fn.effects].sort().join(", ");
      console.log(`  ${fn.name}:${fn.line}  can ${fnEffects}`);
      for (const ev of fn.evidence) {
        const lineMatch = ev.match(/\(line (\d+)\)/);
        if (lineMatch) {
          const lineNo = parseInt(lineMatch[1]);
          if (lineNo > 0 && lineNo <= lines.length) {
            console.log(`    ${lineNo} | ${lines[lineNo - 1].trim()}`);
          }
        }
      }
    }
  }

  if (result.moduleEffects.size > 0) {
    console.log();
    const modEffects = [...result.moduleEffects].sort().join(", ");
    console.log(`  (module level)  can ${modEffects}`);
  }

  const pureCount = result.functions.filter(f => f.pure).length;
  const total = result.functions.length;
  if (total > 0) {
    console.log();
    console.log(`${pureCount}/${total} functions are pure.`);
  }
}

export function toJson(result: ModuleEffects) {
  return {
    file: result.path,
    effects: [...result.allEffects].sort(),
    functions: result.functions.map(fn => ({
      name: fn.name,
      line: fn.line,
      effects: [...fn.effects].sort(),
      pure: fn.pure,
      evidence: fn.evidence,
      calls: fn.calls,
    })),
    moduleEffects: [...result.moduleEffects].sort(),
  };
}

function collectTsFiles(dir: string): string[] {
  const results: string[] = [];
  const skip = new Set(["node_modules", ".git", "dist", "build", ".next", "__tests__"]);

  function walk(d: string) {
    for (const entry of readdirSync(d, { withFileTypes: true })) {
      if (entry.name.startsWith(".") || skip.has(entry.name)) continue;
      const full = join(d, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.name.endsWith(".ts") && !entry.name.endsWith(".d.ts") && !entry.name.endsWith(".test.ts") && !entry.name.endsWith(".spec.ts")) {
        results.push(full);
      }
    }
  }

  walk(dir);
  return results.sort();
}

// Run when invoked directly
main();
