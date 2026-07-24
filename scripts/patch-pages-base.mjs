import fs from "node:fs";
import path from "node:path";

const artifactRoot = path.resolve(process.argv[2] ?? "docs");
const pagesPrefix = process.argv[3] ?? "/roke-fittings-study";
const textExtensions = new Set([".html", ".css", ".js", ".mjs"]);
const sameSiteRoots = [
  "upload",
  "local",
  "bitrix",
  "ajax",
  "roked",
  "catalog",
  "about",
  "why",
  "service",
  "vacancies",
  "download",
  "privacy",
];

if (!fs.existsSync(path.join(artifactRoot, "index.html"))) {
  throw new Error(`Pages artifact is missing index.html: ${artifactRoot}`);
}

const rootPattern = new RegExp(
  `(^|[^A-Za-z0-9_:/.-])/(${sameSiteRoots.join("|")})(?=/)`,
  "gm",
);

let scannedFiles = 0;
let changedFiles = 0;
let replacements = 0;

function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      walk(target);
      continue;
    }

    if (!textExtensions.has(path.extname(entry.name).toLowerCase())) {
      continue;
    }

    scannedFiles += 1;
    const original = fs.readFileSync(target, "utf8");
    const updated = original.replace(rootPattern, (...args) => {
      replacements += 1;
      return `${args[1]}${pagesPrefix}/${args[2]}`;
    });

    if (updated !== original) {
      fs.writeFileSync(target, updated, "utf8");
      changedFiles += 1;
    }
  }
}

walk(artifactRoot);

console.log(
  JSON.stringify(
    {
      artifactRoot,
      pagesPrefix,
      scannedFiles,
      changedFiles,
      replacements,
    },
    null,
    2,
  ),
);
