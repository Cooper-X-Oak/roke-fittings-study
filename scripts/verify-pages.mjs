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
const rootPattern = new RegExp(
  `(^|[^A-Za-z0-9_:/.-])/(${sameSiteRoots.join("|")})(?=/)`,
  "gm",
);
const expectedMissing = new Set([
  "local/templates/roke/assets/images/roke-item.png",
  "upload/images/frames/001.png",
]);
const pageFiles = [
  "index.html",
  "why/index.html",
  "catalog/index.html",
  "service/index.html",
  "about/index.html",
  "vacancies/index.html",
  "download/index.html",
  "privacy/index.html",
];

function walk(directory, output = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(target, output);
    } else {
      output.push(target);
    }
  }
  return output;
}

function localTarget(rawReference, baseDirectory) {
  let reference = rawReference.trim().replace(/^['"]|['"]$/g, "");
  if (
    !reference ||
    /^(#|data:|mailto:|tel:|javascript:)/i.test(reference)
  ) {
    return null;
  }

  if (reference.startsWith("//")) {
    reference = `https:${reference}`;
  }

  if (/^https?:/i.test(reference)) {
    const url = new URL(reference);
    if (!["www.roke-fittings.ru", "roke-fittings.ru"].includes(url.hostname)) {
      return null;
    }
    reference = url.pathname;
  }

  reference = reference.split("#")[0].split("?")[0];
  if (!reference || reference.includes("mc.yandex.ru")) {
    return null;
  }

  let decoded;
  try {
    decoded = decodeURIComponent(reference);
  } catch {
    decoded = reference;
  }

  if (decoded.startsWith(`${pagesPrefix}/`)) {
    return path.join(artifactRoot, decoded.slice(pagesPrefix.length + 1));
  }

  if (decoded.startsWith("/")) {
    return path.join(artifactRoot, decoded.slice(1));
  }

  return path.resolve(baseDirectory, decoded);
}

function existsAsPublished(target) {
  return (
    fs.existsSync(target) ||
    fs.existsSync(`${target}.html`) ||
    fs.existsSync(path.join(target, "index.html"))
  );
}

if (!fs.existsSync(path.join(artifactRoot, "index.html"))) {
  throw new Error(`Pages artifact is missing index.html: ${artifactRoot}`);
}

const files = walk(artifactRoot);
const zeroByteFiles = [];
const temporaryFiles = [];
const oversizedFiles = [];
const unprefixedReferences = [];

for (const file of files) {
  const stat = fs.statSync(file);
  const relative = path.relative(artifactRoot, file).replaceAll("\\", "/");

  if (stat.size === 0 && relative !== ".nojekyll") {
    zeroByteFiles.push(relative);
  }
  if (path.extname(file).toLowerCase() === ".tmp") {
    temporaryFiles.push(relative);
  }
  if (stat.size >= 100 * 1024 * 1024) {
    oversizedFiles.push({ file: relative, bytes: stat.size });
  }

  if (textExtensions.has(path.extname(file).toLowerCase())) {
    const source = fs.readFileSync(file, "utf8");
    let match;
    rootPattern.lastIndex = 0;
    while ((match = rootPattern.exec(source))) {
      unprefixedReferences.push({
        file: relative,
        root: match[2],
        offset: match.index,
      });
    }
  }
}

const missingReferences = [];
const attributePattern =
  /(?:src|href|poster|data-src)\s*=\s*["']([^"']+)["']/gi;
const cssUrlPattern = /url\(([^)]+)\)/gi;
const validationSources = [...pageFiles];

const cssDirectory = path.join(
  artifactRoot,
  "bitrix/cache/css/s1/roke/template_9337a44189a6dd4cc5bd5a2b8e1b0888",
);
if (fs.existsSync(cssDirectory)) {
  for (const name of fs.readdirSync(cssDirectory)) {
    if (name.endsWith(".css")) {
      validationSources.push(
        path
          .relative(artifactRoot, path.join(cssDirectory, name))
          .replaceAll("\\", "/"),
      );
    }
  }
}

for (const relative of validationSources) {
  const sourceFile = path.join(artifactRoot, relative);
  const source = fs.readFileSync(sourceFile, "utf8");
  const baseDirectory = path.dirname(sourceFile);
  const patterns = [attributePattern];
  if (relative.endsWith(".css")) {
    patterns.push(cssUrlPattern);
  }

  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(source))) {
      const target = localTarget(match[1], baseDirectory);
      if (!target || existsAsPublished(target)) {
        continue;
      }

      const publishedPath = path
        .relative(artifactRoot, target)
        .replaceAll("\\", "/");
      if (!expectedMissing.has(publishedPath)) {
        missingReferences.push({
          source: relative,
          reference: match[1],
          target: publishedPath,
        });
      }
    }
  }
}

const frameSets = [
  ["frames1_avif_new", 240],
  ["frames2_avif_new", 240],
  ["frames3_avif", 170],
  ["zt-hero-fixed-ball-valve", 240],
].map(([name, expected]) => {
  const directory = path.join(artifactRoot, "upload/images", name);
  const actual = fs.existsSync(directory)
    ? fs
        .readdirSync(directory)
        .filter(
          (file) =>
            file.endsWith(".avif") &&
            fs.statSync(path.join(directory, file)).size > 100,
        ).length
    : 0;
  return { name, expected, actual };
});

const report = {
  artifactRoot,
  pagesPrefix,
  fileCount: files.length,
  totalBytes: files.reduce((sum, file) => sum + fs.statSync(file).size, 0),
  zeroByteFiles,
  temporaryFiles,
  oversizedFiles,
  unprefixedReferences,
  missingReferences,
  frameSets,
};

console.log(JSON.stringify(report, null, 2));

const failed =
  zeroByteFiles.length > 0 ||
  temporaryFiles.length > 0 ||
  oversizedFiles.length > 0 ||
  unprefixedReferences.length > 0 ||
  missingReferences.length > 0 ||
  frameSets.some(({ expected, actual }) => expected !== actual);

if (failed) {
  process.exitCode = 1;
}
