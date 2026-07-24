import fs from "node:fs";
import path from "node:path";

const repositoryRoot = path.resolve(
  path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")),
  "..",
);
const deployedRoot = path.join(repositoryRoot, "docs");
const offlineRoot = path.resolve(
  process.argv[2] ??
    path.join(repositoryRoot, "..", "..", "site", "www.roke-fittings.ru"),
);

const textFiles = [
  "local/templates/roke/assets/js/animations.homefbd5.js",
  "local/templates/roke/assets/js/animations.aboutc1bc.js",
  "local/templates/roke/assets/js/script81c6.js",
  "bitrix/cache/css/s1/roke/template_9337a44189a6dd4cc5bd5a2b8e1b0888/template_9337a44189a6dd4cc5bd5a2b8e1b0888_v15e7d.css",
];
const binaryFiles = [
  "upload/videos/1.mp4",
  "upload/videos/2.mp4",
  "upload/videos/pd.mp4",
  "upload/iblock/e06/bh7rr01l12oz5oq58ryfjukgeuxaejsi.mp4",
  "upload/iblock/f8f/o76jwnhvqfie30jibw0h5bvnpisyjxpo.mp4",
];

if (!fs.existsSync(path.join(offlineRoot, "index.html"))) {
  throw new Error(`Offline mirror was not found: ${offlineRoot}`);
}

for (const relative of textFiles) {
  const deployed = fs.readFileSync(path.join(deployedRoot, relative), "utf8");
  const local = deployed.replaceAll("/roke-fittings-study/", "/");
  fs.writeFileSync(path.join(offlineRoot, relative), local, "utf8");
}

for (const relative of binaryFiles) {
  fs.copyFileSync(
    path.join(deployedRoot, relative),
    path.join(offlineRoot, relative),
  );
}

console.log(
  JSON.stringify(
    {
      deployedRoot,
      offlineRoot,
      textFiles,
      binaryFiles,
    },
    null,
    2,
  ),
);
