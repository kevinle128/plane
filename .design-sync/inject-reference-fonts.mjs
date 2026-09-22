// The propel Storybook loads no web fonts (no preview-head.html), so the
// reference render falls back to system fonts while the synced bundle ships
// Inter Variable / IBM Plex Mono / Material Symbols Rounded via cfg.extraFonts.
// Grading compares screenshots, so both sides must use the same fonts: this
// copies the same @fontsource CSS + files into sb-reference/_fonts/ and links
// them from iframe.html. Reads cfg.extraFonts so the two sides cannot drift.
// Idempotent; re-run after every reference rebuild.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const sbRef = join(repoRoot, ".design-sync", "sb-reference");
const iframe = join(sbRef, "iframe.html");
if (!existsSync(iframe)) throw new Error(`no reference build at ${sbRef} - build it first`);

const cfg = JSON.parse(readFileSync(join(repoRoot, ".design-sync", "config.json"), "utf8"));
const pkgDir = join(repoRoot, "packages", "propel"); // extraFonts entries are package-relative
const cssEntries = (cfg.extraFonts ?? []).filter((p) => p.endsWith(".css"));
if (cssEntries.length === 0) throw new Error("cfg.extraFonts lists no .css entries - nothing to inject");

const links = [];
for (const rel of cssEntries) {
  const cssPath = resolve(pkgDir, rel);
  // "<package>/<file>.css" -> a stable folder name such as "inter" or "ibm-plex-mono-400"
  const pkgName = basename(dirname(cssPath));
  const name = `${pkgName}-${basename(cssPath, ".css")}`;
  const css = readFileSync(cssPath, "utf8");
  const outDir = join(sbRef, "_fonts", name);
  mkdirSync(join(outDir, "files"), { recursive: true });
  let copied = 0;
  for (const m of css.matchAll(/url\(\s*['"]?\.\/files\/([^'")]+)['"]?\s*\)/g)) {
    // Always overwrite: a fontsource bump keeps file names but changes glyphs.
    copyFileSync(join(dirname(cssPath), "files", m[1]), join(outDir, "files", m[1]));
    copied++;
  }
  writeFileSync(join(outDir, "index.css"), css);
  links.push(`<link rel="stylesheet" href="./_fonts/${name}/index.css">`);
  console.error(`inject-reference-fonts: ${name} (${copied} file(s))`);
}

const MARK = "<!-- design-sync:fonts -->";
let html = readFileSync(iframe, "utf8");
if (html.includes(MARK)) {
  html = html.replace(new RegExp(`${MARK}[\\s\\S]*?${MARK}`), `${MARK}${links.join("")}${MARK}`);
} else {
  html = html.replace(/<head>/i, `<head>${MARK}${links.join("")}${MARK}`);
}
writeFileSync(iframe, html);
console.error("inject-reference-fonts: iframe.html linked");
