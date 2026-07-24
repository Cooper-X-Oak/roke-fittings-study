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

function sanitize(source, relative) {
  let result = source
    .replace(
      /<script>var _ba = _ba \|\| \[\];[\s\S]*?bitrix\.info\/ba\.js[\s\S]*?<\/script>\s*/g,
      "",
    )
    .replace(
      /<script async src="http:\/\/widgets\.mango-office\.ru\/site\/36420"><\/script>\s*/g,
      "",
    )
    .replace(
      /\s*<!-- Yandex\.Metrika counter -->[\s\S]*?<!-- \/Yandex\.Metrika counter -->/g,
      "",
    )
    .replace(
      /\s*<script>\s*var abc = new XMLHttpRequest\(\);[\s\S]*?abc\.send\(abcbody\);\s*<\/script>/g,
      "",
    )
    .replace(/\s*<!-- Mirrored from [\s\S]*?by HTTrack Website Copier\/[\s\S]*?-->/g, "")
    .replace(
      /<a href="#Offcanvas" class="btn p-0" role="button" data-bs-toggle="offcanvas">/g,
      '<a href="#Offcanvas" class="btn p-0" role="button" data-bs-toggle="offcanvas" aria-label="打开菜单">',
    )
    .replace(/<canvas([^>]+)\/>/g, "<canvas$1></canvas>")
    .replace(/<\/dvi>/g, "</div>");

  if (relative === "index.html") {
    result = result.replace(
      /class="section-hero-mobile-image lazyload"\s+data-src="([^"]+)"\s*\/>/,
      'class="section-hero-mobile-image lazyload"\n        src="$1"\n        data-src="$1"\n        alt="ROKE 双卡套管接头"\n      />',
    );
  }

  if (relative === "about/index.html") {
    result = result
      .replace(
        /(<div class="about-hero-text about-hero-text-1 px-3 px-lg-4">)[\s\S]*?(<\/div>)/,
        "$1\n                          <span>ROKE Fluid Equipment</span> 成立于 2008 年，专注于为关键生产过程供应不锈钢、钛等材料的管路配件、阀门和管接头。BHS RUS 是 ROKE Fluid Equipment 工厂及其全系列产品在俄罗斯的官方独家经销商。\n                        $2",
      )
      .replace(
        /(<div class="about-hero-text about-hero-text-2 px-3 px-lg-4">)[\s\S]*?(<\/div>)/,
        "$1\n                          <span>产品</span> 我们生产并供应碳钢、316/316L 不锈钢、双相钢、超级双相钢、哈氏合金、蒙乃尔合金、因科镍合金、因科洛伊合金和钛材产品。\n                        $2",
      );
  }

  return result;
}

const report = [];
let failed = false;

for (const relative of pageFiles) {
  const target = path.join(artifactRoot, relative);
  const original = fs.readFileSync(target, "utf8");
  const sanitized = sanitize(original, relative);
  const changed = sanitized !== original;
  const forbidden = [
    "bitrix.info/ba.js",
    "widgets.mango-office.ru",
    "Yandex.Metrika counter",
    "var abc = new XMLHttpRequest()",
    "HTTrack Website Copier",
  ].filter((needle) => sanitized.includes(needle));

  if (!checkOnly && changed) {
    fs.writeFileSync(target, sanitized, "utf8");
  }
  if (checkOnly && changed) {
    failed = true;
  }
  if (forbidden.length > 0) {
    failed = true;
  }

  report.push({ page: relative, changed, forbidden });
}

console.log(JSON.stringify({ artifactRoot, checkOnly, report }, null, 2));

if (failed) {
  process.exitCode = 1;
}
