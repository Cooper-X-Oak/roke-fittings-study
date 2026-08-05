import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const maxFileSize = 100 * 1024 * 1024;

function fail(message) {
  throw new Error(message);
}

function requireFile(relativePath) {
  const file = path.join(root, relativePath);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
    fail(`Missing required file: ${relativePath}`);
  }
  const size = fs.statSync(file).size;
  if (size === 0) fail(`Empty required file: ${relativePath}`);
  if (size >= maxFileSize) fail(`File exceeds GitHub 100 MB limit: ${relativePath}`);
  return file;
}

function walkFiles(directory) {
  const files = [];
  if (!fs.existsSync(directory)) return files;

  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === 'dist') {
      continue;
    }
    if (entry.isDirectory()) {
      files.push(...walkFiles(fullPath));
    } else {
      files.push(fullPath);
    }
  }
  return files;
}

const heroDir = path.join(root, 'public', 'assets', 'upload', 'images', 'zt-hero-fixed-ball-valve');
const heroFrames = fs.readdirSync(heroDir).filter((name) => name.endsWith('.avif')).sort();
if (heroFrames.length !== 240) {
  fail(`Expected 240 hero frames, found ${heroFrames.length}`);
}

for (let frame = 1; frame <= 240; frame += 1) {
  const expected = `${String(frame).padStart(4, '0')}.avif`;
  if (heroFrames[frame - 1] !== expected) fail(`Missing hero frame ${expected}`);
  requireFile(path.join('public', 'assets', 'upload', 'images', 'zt-hero-fixed-ball-valve', expected));
}

requireFile('public/assets/hero/fixed-ball-valve-mobile-fallback.png');
requireFile('public/assets/template/images/ztovalve-benefits-product.png');
requireFile('public/assets/upload/iblock/7b2/1lomd3e7eftm83ocnj3iyqy2978cz7to.glb');
requireFile('public/assets/upload/iblock/4da/0q73zvtq6ngmvx87pgsco61m30gd9q2r.glb');
requireFile('src/styles/legacy/template.css');
requireFile('src/scripts/legacy/animations.homefbd5.js');
requireFile('src/scripts/legacy/script81c6.js');
requireFile('src/assets-manifest/delivery-assets.json');
requireFile('src/pages/index.html');
requireFile('src/pages/catalog/index.html');

const forbiddenParts = [
  `${path.sep}.scratch${path.sep}`,
  `${path.sep}docs${path.sep}engineering${path.sep}`,
  `${path.sep}v3-blender-preview-entry${path.sep}`,
  `${path.sep}v3-closeup-asset-inspection${path.sep}`,
  `${path.sep}v3-low-cost-preview-bundle${path.sep}`
];

for (const file of walkFiles(root)) {
  const stat = fs.statSync(file);
  if (stat.size === 0 && !file.endsWith(`${path.sep}.nojekyll`)) {
    fail(`Zero-byte file found: ${path.relative(root, file)}`);
  }
  if (stat.size >= maxFileSize) {
    fail(`File exceeds GitHub 100 MB limit: ${path.relative(root, file)}`);
  }
  if (forbiddenParts.some((part) => file.includes(part))) {
    fail(`Forbidden legacy/experiment file found: ${path.relative(root, file)}`);
  }
}

console.log('Asset check OK: pages, legacy modules, hero frames, GLB files, and size limits pass.');
