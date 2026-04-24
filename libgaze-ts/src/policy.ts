/**
 * Effect policy checking.
 *
 * A .gazepolicy file declares which effects are allowed (or denied) for a module.
 * libgaze-ts checks the analyzed effects against the policy and reports violations.
 *
 * Policy format (JSON):
 * {
 *     "allow": ["Net", "Fail"],           // only these effects are permitted
 *     "deny": ["Unsafe", "Db"],           // these effects are forbidden
 *     "functions": {
 *         "process_data": { "allow": [] } // this function must be pure
 *     }
 * }
 *
 * Rules:
 * - If "allow" is present, any effect NOT in the list is a violation.
 * - If "deny" is present, any effect IN the list is a violation.
 * - "allow" and "deny" are mutually exclusive at each level.
 * - Function-level policies override module-level policies.
 */

import { readFileSync } from "node:fs";
import type { Effect } from "./effects.js";
import type { ModuleEffects } from "./analyzer.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Policy {
  allow: Set<string> | null;
  deny: Set<string> | null;
  functions: Map<string, Policy> | null;
}

export interface PolicyViolation {
  function: string;
  line: number;
  effect: string;
  reason: string;
}

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

export function loadPolicy(path: string): Policy {
  const data = JSON.parse(readFileSync(path, "utf-8"));
  return parsePolicy(data);
}

function parsePolicy(data: Record<string, unknown>): Policy {
  let allow: Set<string> | null = null;
  let deny: Set<string> | null = null;
  let functions: Map<string, Policy> | null = null;

  if ("allow" in data) {
    allow = new Set(data.allow as string[]);
  }
  if ("deny" in data) {
    deny = new Set(data.deny as string[]);
  }
  if ("functions" in data) {
    functions = new Map();
    const fnData = data.functions as Record<string, Record<string, unknown>>;
    for (const [name, fnPolicy] of Object.entries(fnData)) {
      functions.set(name, parsePolicy(fnPolicy));
    }
  }

  if (allow !== null && deny !== null) {
    throw new Error("Policy cannot have both 'allow' and 'deny' at the same level");
  }

  return { allow, deny, functions };
}

// ---------------------------------------------------------------------------
// Checking
// ---------------------------------------------------------------------------

export function checkPolicy(result: ModuleEffects, policy: Policy): PolicyViolation[] {
  const violations: PolicyViolation[] = [];

  for (const fn of result.functions) {
    let activePolicy = policy;
    if (policy.functions?.has(fn.name)) {
      activePolicy = policy.functions.get(fn.name)!;
    }

    for (const effect of fn.effects) {
      const violation = checkEffect(activePolicy, effect, fn.name, fn.line);
      if (violation) {
        violations.push(violation);
      }
    }
  }

  // Check module-level effects
  for (const effect of result.moduleEffects) {
    const violation = checkEffect(policy, effect, "(module level)", 0);
    if (violation) {
      violations.push(violation);
    }
  }

  return violations;
}

function checkEffect(
  policy: Policy,
  effect: string,
  fnName: string,
  line: number,
): PolicyViolation | null {
  if (policy.allow !== null && !policy.allow.has(effect)) {
    const allowed = [...policy.allow].sort().join(", ");
    return {
      function: fnName,
      line,
      effect,
      reason: `not in allowed effects: {${allowed}}`,
    };
  }
  if (policy.deny !== null && policy.deny.has(effect)) {
    return {
      function: fnName,
      line,
      effect,
      reason: "explicitly denied by policy",
    };
  }
  return null;
}
