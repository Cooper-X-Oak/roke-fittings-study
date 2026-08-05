import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(process.argv[2] ?? 'dist');
const prefix = process.argv[3] ?? '/ztovalue/';
const files = [];
const references = new Set();

function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath);
    } else if (/\.(html|css|js)$/i.test(entry.name)) {
      files.push(fullPath);
    }
  }
}

walk(root);

const escapedPrefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const referencePattern = new RegExp(`${escapedPrefix}[^"'\\)\\s<>]+`, 'g');

for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/\/\*[\s\S]*?\*\//g, '');
  content = content.replace(/^\s*\/\/.*$/gm, '');
  for (const match of content.matchAll(referencePattern)) {
    let url = match[0].split('#')[0].split('?')[0];
    if (url.includes('${')) continue;
    if (url.startsWith(`${prefix}ajax/`)) continue;
    if (url === prefix || (url.endsWith('/') && !url.startsWith(`${prefix}assets/`))) {
      url += 'index.html';
    }
    if (url.endsWith('/')) continue;
    references.add(url);
  }
}

const missing = [];
for (const url of references) {
  const relative = decodeURIComponent(url.replace(prefix, ''));
  const target = path.join(root, relative);
  if (!fs.existsSync(target)) missing.push(url);
}

if (missing.length > 0) {
  console.error(JSON.stringify({ scannedFiles: files.length, references: references.size, missing }, null, 2));
  process.exit(1);
}

console.log(
  JSON.stringify({ scannedFiles: files.length, references: references.size, missing }, null, 2)
);
