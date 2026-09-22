// @plane/constants reads `process.env.VITE_*` at module scope (endpoints.ts).
// Vite and the Storybook builder define `process.env` at build time; the
// design-sync IIFE bundle only defines NODE_ENV, so `process` is undefined in
// the browser and the whole bundle throws before anything lands on the global.
// Listed FIRST in cfg.extraEntries so it evaluates before every other module:
// the same empty env Storybook gives those reads (they fall back to "").
export function installDesignSyncProcessEnv() {
  if (typeof globalThis.process === "undefined") globalThis.process = { env: {} };
  else if (globalThis.process.env == null) globalThis.process.env = {};
}

installDesignSyncProcessEnv();
