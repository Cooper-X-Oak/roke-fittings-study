import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const distRoot = path.join(root, 'dist');
const publicRoot = path.join(root, 'public');
const pagesRoot = path.join(root, 'src', 'pages');
const stylesRoot = path.join(root, 'src', 'styles', 'legacy');
const scriptsRoot = path.join(root, 'src', 'scripts', 'legacy');

function assertInside(parent, child) {
  const relative = path.relative(parent, child);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Refusing to write outside ${parent}: ${child}`);
  }
}

function copyDirectory(source, destination) {
  if (!fs.existsSync(source)) return;
  fs.mkdirSync(destination, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(destination, entry.name);

    if (entry.isDirectory()) {
      copyDirectory(from, to);
      continue;
    }

    fs.copyFileSync(from, to);
  }
}

function copyPages(source, destination) {
  fs.mkdirSync(destination, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(destination, entry.name);

    if (entry.isDirectory()) {
      copyPages(from, to);
      continue;
    }

    if (!entry.name.endsWith('.html')) continue;
    fs.copyFileSync(from, to);
  }
}

assertInside(root, distRoot);
fs.rmSync(distRoot, { recursive: true, force: true });
fs.mkdirSync(distRoot, { recursive: true });

copyDirectory(publicRoot, distRoot);
copyPages(pagesRoot, distRoot);
copyDirectory(stylesRoot, path.join(distRoot, 'assets', 'styles'));
copyDirectory(scriptsRoot, path.join(distRoot, 'assets', 'scripts'));

fs.writeFileSync(path.join(distRoot, '.nojekyll'), '\n', 'utf8');

console.log('Built static site to dist/.');
