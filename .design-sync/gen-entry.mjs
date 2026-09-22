// @plane/propel ships subpath entries only (`@plane/propel/button`, ...) - there
// is no root `.` export and no root `types`. The design-sync converter needs
// one JS entry and one .d.ts entry, so this writes a barrel pair into the
// (gitignored) dist/ after the package build:
//   packages/propel/dist/index.js    - `--entry` / cfg.entry
//   packages/propel/dist/index.d.ts  - resolved by .design-sync/overrides/dts.mjs
// Both are derived from package.json `exports`, so a new subpath is picked up
// on the next build with no edit here. Run via cfg.buildCmd.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const pkgDir = join(repoRoot, "packages", "propel");
const pkg = JSON.parse(readFileSync(join(pkgDir, "package.json"), "utf8"));

const subpaths = Object.values(pkg.exports)
  .filter((v) => typeof v === "string" && v.startsWith("./dist/") && v.endsWith("/index.js"))
  .map((v) => v.replace(/^\.\/dist\//, "./"));

// Fail here, not three stages later as "[BUNDLE_EXPORT] 36/36 not a component".
if (subpaths.length === 0)
  throw new Error(
    'gen-entry: no "./dist/<sub>/index.js" string exports found in package.json - did the exports map change shape (conditional objects)?'
  );

const barrel = subpaths.map((p) => `export * from ${JSON.stringify(p)};`).join("\n") + "\n";
writeFileSync(join(pkgDir, "dist", "index.js"), barrel);
writeFileSync(join(pkgDir, "dist", "index.d.ts"), barrel);
console.error(`gen-entry: wrote dist/index.js + dist/index.d.ts re-exporting ${subpaths.length} subpaths`);
