import fs from "node:fs";
import path from "node:path";

const repositoryRoot = path.resolve(
  path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")),
  "..",
);
const artifactRoot = path.resolve(process.argv[2] ?? path.join(repositoryRoot, "docs"));
const checkOnly = process.argv.includes("--check");
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
const baseTranslations = JSON.parse(
  fs.readFileSync(
    path.join(repositoryRoot, "scripts/localization.ru-zh.json"),
    "utf8",
  ),
);
const overrides = JSON.parse(
  fs.readFileSync(
    path.join(repositoryRoot, "scripts/localization.overrides.zh-CN.json"),
    "utf8",
  ),
);
const translations = { ...baseTranslations, ...overrides };
const cyrillicPattern = /[А-Яа-яЁё]/;
const tokenPattern =
  /<!--[\s\S]*?-->|<script\b[\s\S]*?<\/script>|<style\b[\s\S]*?<\/style>|<[^>]+>|[^<]+/gi;
const translatedAttributes = new Set([
  "alt",
  "content",
  "placeholder",
  "title",
  "value",
]);

function decodeEntities(value) {
  return value
    .replace(/&nbsp;/gi, "\u00a0")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&copy;/gi, "©")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#(\d+);/g, (_match, code) =>
      String.fromCodePoint(Number(code)),
    )
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) =>
      String.fromCodePoint(Number.parseInt(code, 16)),
    );
}

function normalize(value) {
  return decodeEntities(value).replace(/\s+/g, " ").trim();
}

function escapeText(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;");
}

function escapeAttribute(value, quote) {
  let escaped = escapeText(value);
  if (quote === '"') {
    escaped = escaped.replaceAll('"', "&quot;");
  } else {
    escaped = escaped.replaceAll("'", "&#39;");
  }
  return escaped;
}

function translatedValue(value) {
  const key = normalize(value);
  return translations[key];
}

function translateTextToken(token) {
  const translation = translatedValue(token);
  if (translation === undefined) {
    return token;
  }

  const leading = token.match(/^\s*/)?.[0] ?? "";
  const trailing = token.match(/\s*$/)?.[0] ?? "";
  return `${leading}${escapeText(translation)}${trailing}`;
}

function translateTagToken(token) {
  if (/^<html\b/i.test(token)) {
    token = token.replace(/\blang=(["'])ru\1/i, 'lang="zh-CN"');
  }

  return token.replace(
    /\b([A-Za-z:-]+)=(["'])([\s\S]*?)\2/g,
    (match, name, quote, value) => {
      if (!translatedAttributes.has(name.toLowerCase())) {
        return match;
      }
      const translation = translatedValue(value);
      if (translation === undefined) {
        return match;
      }
      return `${name}=${quote}${escapeAttribute(translation, quote)}${quote}`;
    },
  );
}

function translateDocument(source) {
  return source.replace(tokenPattern, (token) => {
    if (
      token.startsWith("<!--") ||
      /^<script\b/i.test(token) ||
      /^<style\b/i.test(token)
    ) {
      return token;
    }
    if (token.startsWith("<")) {
      return translateTagToken(token);
    }
    return translateTextToken(token);
  });
}

function visibleCyrillic(source) {
  const leftovers = [];
  for (const token of source.match(tokenPattern) ?? []) {
    if (
      token.startsWith("<!--") ||
      /^<script\b/i.test(token) ||
      /^<style\b/i.test(token)
    ) {
      continue;
    }

    if (token.startsWith("<")) {
      token.replace(
        /\b([A-Za-z:-]+)=(["'])([\s\S]*?)\2/g,
        (_match, name, _quote, value) => {
          if (
            translatedAttributes.has(name.toLowerCase()) &&
            cyrillicPattern.test(decodeEntities(value))
          ) {
            leftovers.push(`${name}: ${normalize(value)}`);
          }
          return _match;
        },
      );
      continue;
    }

    if (cyrillicPattern.test(decodeEntities(token))) {
      leftovers.push(normalize(token));
    }
  }
  return [...new Set(leftovers.filter(Boolean))];
}

const report = [];
let failed = false;

for (const relative of pageFiles) {
  const target = path.join(artifactRoot, relative);
  const original = fs.readFileSync(target, "utf8");
  const localized = translateDocument(original);
  const leftovers = visibleCyrillic(localized);
  const changed = localized !== original;

  if (!checkOnly && changed) {
    fs.writeFileSync(target, localized, "utf8");
  }

  if (leftovers.length > 0) {
    failed = true;
  }

  report.push({
    page: relative,
    changed,
    untranslatedVisibleStrings: leftovers,
  });
}

console.log(
  JSON.stringify(
    {
      artifactRoot,
      checkOnly,
      pageCount: pageFiles.length,
      report,
    },
    null,
    2,
  ),
);

if (failed) {
  process.exitCode = 1;
}
