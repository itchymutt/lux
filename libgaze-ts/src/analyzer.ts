/**
 * Static effect analyzer for TypeScript source code.
 *
 * Two-pass analysis:
 * 1. Walk the AST. Detect direct effects from known functions and modules.
 *    Record every call site for the call graph.
 * 2. Propagate effects through intra-module calls. If function A calls
 *    function B (via this.method(), ClassName.method(), or bare name()),
 *    A inherits B's effects. Iterate until stable.
 *
 * Same vocabulary as libgaze (Python). Same architecture. Different AST.
 *
 * Uses oxc-parser for TypeScript parsing (~2.4MB vs ~50MB for ts-morph).
 */

import { parseSync } from "oxc-parser";
import { readFileSync } from "node:fs";
import type { Effect } from "./effects.js";
import { MODULE_EFFECTS, FUNCTION_EFFECTS } from "./effects.js";

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

export interface FunctionEffects {
  name: string;
  line: number;
  effects: Set<Effect>;
  calls: string[];
  evidence: string[];
  pure: boolean;
}

export interface ModuleEffects {
  path: string;
  functions: FunctionEffects[];
  moduleEffects: Set<Effect>;
  allEffects: Set<Effect>;
}

interface ModuleStructure {
  classMethods: Map<string, Set<string>>;  // className -> methodNames
  functionOwner: Map<string, string>;       // fnName -> className
}

// ---------------------------------------------------------------------------
// Line number resolution (oxc gives byte offsets, not line numbers)
// ---------------------------------------------------------------------------

function buildLineTable(source: string): number[] {
  const offsets = [0];
  for (let i = 0; i < source.length; i++) {
    if (source[i] === "\n") offsets.push(i + 1);
  }
  return offsets;
}

function offsetToLine(offsets: number[], pos: number): number {
  let lo = 0, hi = offsets.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (offsets[mid] <= pos) lo = mid;
    else hi = mid - 1;
  }
  return lo + 1; // 1-indexed
}

// ---------------------------------------------------------------------------
// AST walking helpers
// ---------------------------------------------------------------------------

// Intentional 'any': oxc-parser's strict union types fight generic tree walking.
// We pattern-match on node.type at runtime, which requires a flexible type.
type AstNode = any;

function walk(node: AstNode, visitor: (n: AstNode) => void): void {
  if (!node || typeof node !== "object") return;
  if (node.type) visitor(node);
  for (const key of Object.keys(node)) {
    if (key === "type" || key === "start" || key === "end") continue;
    const val = node[key];
    if (Array.isArray(val)) {
      for (const item of val) {
        if (item && typeof item === "object") walk(item, visitor);
      }
    } else if (val && typeof val === "object" && val.type) {
      walk(val, visitor);
    }
  }
}

/** Check if a node is a string literal (ESTree "Literal" or "StringLiteral"). */
function isStringNode(node: AstNode): boolean {
  return (node.type === "Literal" || node.type === "StringLiteral") && typeof node.value === "string";
}

/** Resolve a callee expression to a dotted name string. */
function resolveCallee(node: AstNode): string | null {
  if (node.type === "Identifier") return node.name;
  if (node.type === "ThisExpression") return "this";
  if (node.type === "MemberExpression" && !node.computed) {
    const obj = resolveCallee(node.object);
    const prop = node.property?.name || node.property?.value;
    if (obj && prop) return `${obj}.${prop}`;
  }
  return null;
}

/** Resolve a member expression chain to a dotted name string. */
function resolveMemberChain(node: AstNode): string | null {
  if (node.type === "Identifier") return node.name;
  if (node.type === "ThisExpression") return "this";
  if (node.type === "MemberExpression" && !node.computed) {
    const obj = resolveMemberChain(node.object);
    const prop = node.property?.name || node.property?.value;
    if (obj && prop) return `${obj}.${prop}`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export function analyzeSource(source: string, path = "<string>"): ModuleEffects {
  return analyze(source, path);
}

export function analyzeFilePath(filePath: string): ModuleEffects {
  const source = readFileSync(filePath, "utf-8");
  return analyze(source, filePath);
}

function analyze(source: string, path: string): ModuleEffects {
  // oxc-parser infers language from filename extension. When the path has no
  // .ts extension (e.g. "<string>"), explicitly set lang to TypeScript.
  const parsePath = path.endsWith(".ts") || path.endsWith(".tsx") ? path : "input.ts";
  const result = parseSync(parsePath, source, { sourceType: "module", lang: "ts" });
  if (result.errors.length > 0) {
    throw new Error(`Parse error in ${path}: ${result.errors[0].message}`);
  }

  // Use 'any' for the AST: we do structural pattern matching on node.type,
  // and oxc-parser's strict union types fight generic tree walking.
  const ast: AstNode = result.program;
  const lineTable = buildLineTable(source);
  const line = (offset: number) => offsetToLine(lineTable, offset);

  const imports = new Map<string, string>();  // localName -> moduleName
  const moduleEffects = new Set<Effect>();
  const functions: FunctionEffects[] = [];
  const structure: ModuleStructure = {
    classMethods: new Map(),
    functionOwner: new Map(),
  };

  // --- Pass 1a: collect imports ---
  for (const node of ast.body) {
    if (node.type === "ImportDeclaration") {
      const moduleSpec: string = node.source.value;
      const effect = resolveModuleEffect(moduleSpec);
      if (effect) moduleEffects.add(effect);

      for (const spec of (node.specifiers || [])) {
        if (spec.type === "ImportSpecifier") {
          const localName = spec.local.name;
          imports.set(localName, moduleSpec);
        } else if (spec.type === "ImportDefaultSpecifier") {
          imports.set(spec.local.name, moduleSpec);
        } else if (spec.type === "ImportNamespaceSpecifier") {
          imports.set(spec.local.name, moduleSpec);
        }
      }
    }
  }

  // Also track require() calls at module level
  for (const node of ast.body) {
    if (node.type === "VariableDeclaration") {
      for (const decl of node.declarations) {
        if (
          decl.init?.type === "CallExpression" &&
          decl.init.callee?.type === "Identifier" &&
          decl.init.callee.name === "require" &&
          decl.init.arguments?.length === 1 &&
          isStringNode(decl.init.arguments[0])
        ) {
          const moduleSpec: string = decl.init.arguments[0].value;
          const effect = resolveModuleEffect(moduleSpec);
          if (effect) moduleEffects.add(effect);
          if (decl.id?.name) imports.set(decl.id.name, moduleSpec);
        }
      }
    }
  }

  // --- Pass 1b: collect class structure ---
  for (const node of ast.body) {
    const cls = node.type === "ClassDeclaration" ? node
      : (node.type === "ExportNamedDeclaration" || node.type === "ExportDefaultDeclaration")
        && node.declaration?.type === "ClassDeclaration" ? node.declaration
      : null;
    if (!cls || !cls.id?.name) continue;

    const className: string = cls.id.name;
    const methods = new Set<string>();
    for (const member of (cls.body?.body || [])) {
      if (member.type === "MethodDefinition" && member.key?.name) {
        methods.add(member.key.name);
        structure.functionOwner.set(member.key.name, className);
      }
    }
    structure.classMethods.set(className, methods);
  }

  // --- Pass 1c: analyze functions ---
  const analyzeFn = (name: string, body: AstNode, fnLine: number) => {
    const fn: FunctionEffects = {
      name,
      line: fnLine,
      effects: new Set(),
      calls: [],
      evidence: [],
      pure: true,
    };

    walk(body, (node: AstNode) => {
      // Call expressions
      if (node.type === "CallExpression") {
        const callName = resolveCallee(node.callee);
        if (callName) {
          // Check for require() inside function bodies
          if (callName === "require" && node.arguments?.length === 1 && isStringNode(node.arguments[0])) {
            const moduleSpec: string = node.arguments[0].value;
            const effect = resolveModuleEffect(moduleSpec);
            if (effect) {
              record(fn, effect, `require("${moduleSpec}")`, line(node.start));
            }
          } else {
            // Resolve through imports
            const resolved = resolveCallThroughImports(callName, imports);
            fn.calls.push(resolved);
            checkCallEffects(resolved, line(node.start), fn, imports);
          }
        }
      }

      // New expressions: new Function(...), new Worker(...)
      if (node.type === "NewExpression") {
        const ctorName = node.callee?.type === "Identifier" ? node.callee.name : null;
        if (ctorName) {
          const key = `new ${ctorName}`;
          if (FUNCTION_EFFECTS.has(key)) {
            record(fn, FUNCTION_EFFECTS.get(key)!, `${key}()`, line(node.start));
          } else if (FUNCTION_EFFECTS.has(ctorName)) {
            record(fn, FUNCTION_EFFECTS.get(ctorName)!, `new ${ctorName}()`, line(node.start));
          }
        }
      }

      // Property access: process.env, etc. (not part of a call)
      if (node.type === "MemberExpression") {
        const chain = resolveMemberChain(node);
        if (chain) {
          const effect = FUNCTION_EFFECTS.get(chain);
          if (effect) {
            record(fn, effect, chain, line(node.start));
          }
        }
      }
    });

    fn.pure = fn.effects.size === 0;
    functions.push(fn);
  };

  // Collect all functions from the module body
  for (const node of ast.body) {
    // Top-level function declarations
    if (node.type === "FunctionDeclaration") {
      const name = node.id?.name ?? "<anonymous>";
      analyzeFn(name, node.body, line(node.start));
    }

    // Class methods
    const cls = node.type === "ClassDeclaration" ? node
      : (node.type === "ExportNamedDeclaration" || node.type === "ExportDefaultDeclaration")
        && node.declaration?.type === "ClassDeclaration" ? node.declaration
      : null;
    if (cls) {
      for (const member of (cls.body?.body || [])) {
        if (member.type === "MethodDefinition" && member.key?.name && member.value) {
          analyzeFn(member.key.name, member.value.body, line(member.start));
        }
      }
    }

    // Variable declarations with arrow functions or function expressions
    if (node.type === "VariableDeclaration") {
      for (const decl of node.declarations) {
        if (decl.init?.type === "ArrowFunctionExpression" || decl.init?.type === "FunctionExpression") {
          const name = decl.id?.name ?? "<anonymous>";
          const body = decl.init.body;
          analyzeFn(name, body, line(node.start));
        }
      }
    }

    // Exported function declarations
    if ((node.type === "ExportNamedDeclaration" || node.type === "ExportDefaultDeclaration") && node.declaration) {
      const decl = node.declaration;
      if (decl.type === "FunctionDeclaration") {
        const name = decl.id?.name ?? "<anonymous>";
        analyzeFn(name, decl.body, line(decl.start));
      }
      if (decl.type === "VariableDeclaration") {
        for (const vd of decl.declarations) {
          if (vd.init?.type === "ArrowFunctionExpression" || vd.init?.type === "FunctionExpression") {
            const name = vd.id?.name ?? "<anonymous>";
            analyzeFn(name, vd.init.body, line(decl.start));
          }
        }
      }
    }
  }

  // --- Pass 2: propagate effects ---
  propagateEffects(functions, structure);

  // Compute allEffects
  const allEffects = new Set(moduleEffects);
  for (const fn of functions) {
    for (const e of fn.effects) {
      allEffects.add(e);
    }
  }

  return { path, functions, moduleEffects, allEffects };
}

// ---------------------------------------------------------------------------
// Call resolution
// ---------------------------------------------------------------------------

function resolveCallThroughImports(callName: string, imports: Map<string, string>): string {
  const parts = callName.split(".");
  if (parts.length >= 1 && imports.has(parts[0])) {
    return `${imports.get(parts[0])}.${parts.slice(1).join(".")}`;
  }
  return callName;
}

// ---------------------------------------------------------------------------
// Effect detection
// ---------------------------------------------------------------------------

function resolveModuleEffect(moduleSpec: string): Effect | undefined {
  if (MODULE_EFFECTS.has(moduleSpec)) {
    return MODULE_EFFECTS.get(moduleSpec);
  }
  for (const [pattern, effect] of MODULE_EFFECTS) {
    if (moduleSpec === pattern || moduleSpec.startsWith(pattern + "/")) {
      return effect;
    }
  }
  return undefined;
}

function checkCallEffects(
  callName: string,
  callLine: number,
  fn: FunctionEffects,
  imports: Map<string, string>,
): void {
  // Direct function match (globals like fetch, eval, console.log)
  if (FUNCTION_EFFECTS.has(callName)) {
    record(fn, FUNCTION_EFFECTS.get(callName)!, `${callName}()`, callLine);
    return;
  }

  // If the call name was resolved through imports (e.g. "node:fs.readFileSync"),
  // extract the module part and check it against MODULE_EFFECTS.
  const dotIdx = callName.indexOf(".");
  if (dotIdx > 0) {
    const modulePart = callName.slice(0, dotIdx);
    const effect = resolveModuleEffect(modulePart);
    if (effect) {
      record(fn, effect, `${callName}()`, callLine);
      return;
    }
  }

  // Check if the first part is a local name imported from a known module
  const parts = callName.split(".");
  if (parts.length >= 2) {
    const firstPart = parts[0];
    if (imports.has(firstPart)) {
      const moduleSpec = imports.get(firstPart)!;
      const effect = resolveModuleEffect(moduleSpec);
      if (effect) {
        record(fn, effect, `${callName}()`, callLine);
        return;
      }
    }

    // Check the dotted prefix against known functions
    for (let i = parts.length; i >= 2; i--) {
      const prefix = parts.slice(0, i).join(".");
      if (FUNCTION_EFFECTS.has(prefix)) {
        record(fn, FUNCTION_EFFECTS.get(prefix)!, `${callName}()`, callLine);
        return;
      }
    }
  }
}

function record(fn: FunctionEffects, effect: Effect, evidence: string, callLine: number): void {
  fn.effects.add(effect);
  fn.evidence.push(`${evidence} (line ${callLine})`);
}

// ---------------------------------------------------------------------------
// Effect propagation (pass 2)
// ---------------------------------------------------------------------------

function propagateEffects(functions: FunctionEffects[], structure: ModuleStructure): void {
  const fnByName = new Map<string, FunctionEffects>();
  for (const fn of functions) {
    fnByName.set(fn.name, fn);
  }

  let changed = true;
  while (changed) {
    changed = false;
    for (const fn of functions) {
      for (const call of fn.calls) {
        const calleeName = resolveIntraModuleCall(fn.name, call, structure);
        const callee = calleeName ? fnByName.get(calleeName) : undefined;
        if (callee && callee !== fn) {
          for (const effect of callee.effects) {
            if (!fn.effects.has(effect)) {
              fn.effects.add(effect);
              fn.evidence.push(`calls ${callee.name} (line ${callee.line})`);
              changed = true;
            }
          }
        }
      }
    }
  }

  // Update pure flag after propagation
  for (const fn of functions) {
    fn.pure = fn.effects.size === 0;
  }
}

function resolveIntraModuleCall(
  callerName: string,
  callName: string,
  structure: ModuleStructure,
): string | null {
  const parts = callName.split(".");

  // this.method()
  if (parts.length === 2 && parts[0] === "this") {
    const method = parts[1];
    const owner = structure.functionOwner.get(callerName);
    if (owner && structure.classMethods.get(owner)?.has(method)) {
      return method;
    }
  }

  // ClassName.method()
  if (parts.length === 2 && structure.classMethods.has(parts[0])) {
    if (structure.classMethods.get(parts[0])!.has(parts[1])) {
      return parts[1];
    }
  }

  // bare function()
  if (parts.length === 1 && !structure.functionOwner.has(parts[0])) {
    return parts[0];
  }

  return null;
}
