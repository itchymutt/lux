/**
 * The ten Gaze effects and their mapping to Node.js/TypeScript modules.
 *
 * This is the same vocabulary as libgaze (Python). Every entry is a claim:
 * "importing or calling this module/function performs this effect."
 */

export enum Effect {
  Net = "Net",
  Fs = "Fs",
  Db = "Db",
  Console = "Console",
  Env = "Env",
  Time = "Time",
  Rand = "Rand",
  Async = "Async",
  Unsafe = "Unsafe",
  Fail = "Fail",
}

// ---------------------------------------------------------------------------
// Module-level effects
//
// Importing anything from these modules implies the effect.
// Matched by prefix: "node:http" matches "node:http" and "node:http2".
// ---------------------------------------------------------------------------

const NET_MODULES = [
  // Node.js stdlib
  "node:http", "node:https", "node:http2", "node:net", "node:tls",
  "node:dgram", "node:dns",
  "http", "https", "http2", "net", "tls", "dgram", "dns",
  // Third-party HTTP
  "axios", "node-fetch", "got", "undici", "ky", "superagent",
  // WebSocket
  "ws", "socket.io", "socket.io-client",
  // Cloud
  "@aws-sdk", "aws-sdk", "@azure", "@google-cloud",
  // LLM clients
  "openai", "@anthropic-ai/sdk", "cohere-ai", "@ai-sdk",
  // Browser automation
  "puppeteer", "playwright",
  // MCP
  "@modelcontextprotocol/sdk",
];

const FS_MODULES = [
  // Node.js stdlib
  // NOTE: node:path is NOT here. path.join/dirname/basename/extname are pure string ops.
  "node:fs",
  "fs", "fs/promises",
  // Third-party
  "fs-extra", "glob", "globby", "chokidar", "tmp", "archiver",
];

const DB_MODULES = [
  // SQL
  "pg", "mysql2", "better-sqlite3", "sqlite3", "knex", "sequelize",
  "typeorm", "prisma", "@prisma/client", "drizzle-orm",
  // NoSQL
  "mongodb", "mongoose", "redis", "ioredis",
  // Generic
  "keyv", "level",
];

const CONSOLE_MODULES = [
  "node:readline", "readline",
  "inquirer", "@inquirer/prompts", "prompts",
  "chalk", "ora", "cli-progress", "boxen",
  "commander", "yargs", "meow",
];

const ENV_MODULES = [
  "dotenv",
];

const TIME_MODULES: string[] = [
  // No module-level: setTimeout/Date are globals handled in FUNCTION_EFFECTS
];

const RAND_MODULES = [
  "node:crypto",
  "crypto",
  "uuid",
];

const ASYNC_MODULES = [
  "node:worker_threads", "node:cluster",
  "worker_threads", "cluster",
  "p-queue", "p-limit", "bull", "bullmq",
];

const UNSAFE_MODULES = [
  "node:vm", "vm",
  "node:ffi", "ffi-napi", "ref-napi",
  "node:child_process", "child_process",
];

export const MODULE_EFFECTS: Map<string, Effect> = new Map();

const moduleGroups: [string[], Effect][] = [
  [NET_MODULES, Effect.Net],
  [FS_MODULES, Effect.Fs],
  [DB_MODULES, Effect.Db],
  [CONSOLE_MODULES, Effect.Console],
  [ENV_MODULES, Effect.Env],
  [TIME_MODULES, Effect.Time],
  [RAND_MODULES, Effect.Rand],
  [ASYNC_MODULES, Effect.Async],
  [UNSAFE_MODULES, Effect.Unsafe],
];

for (const [modules, effect] of moduleGroups) {
  for (const mod of modules) {
    MODULE_EFFECTS.set(mod, effect);
  }
}

// ---------------------------------------------------------------------------
// Function-level effects
//
// Specific global functions or property accesses that imply effects.
// ---------------------------------------------------------------------------

export const FUNCTION_EFFECTS: Map<string, Effect> = new Map([
  // Console
  ["console.log", Effect.Console],
  ["console.error", Effect.Console],
  ["console.warn", Effect.Console],
  ["console.info", Effect.Console],
  ["console.debug", Effect.Console],
  ["console.table", Effect.Console],
  ["console.dir", Effect.Console],

  // Env
  ["process.env", Effect.Env],
  ["process.cwd", Effect.Env],
  ["process.argv", Effect.Env],

  // Time
  ["setTimeout", Effect.Time],
  ["setInterval", Effect.Time],
  ["setImmediate", Effect.Time],
  ["Date.now", Effect.Time],
  ["performance.now", Effect.Time],

  // Rand
  ["Math.random", Effect.Rand],
  ["crypto.randomUUID", Effect.Rand],
  ["crypto.randomBytes", Effect.Rand],
  ["crypto.getRandomValues", Effect.Rand],

  // Unsafe
  ["eval", Effect.Unsafe],
  ["Function", Effect.Unsafe],
  ["new Function", Effect.Unsafe],

  // Fail
  ["process.exit", Effect.Fail],

  // Net (global fetch)
  ["fetch", Effect.Net],

  // Async
  ["queueMicrotask", Effect.Async],

  // Fs (path module functions that touch the filesystem)
  // NOTE: path.join, path.resolve, path.dirname are pure string ops
  // and are NOT listed here. Only fs.* functions are Fs.
]);
