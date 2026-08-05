# ZTOVALUE Structured Website Delivery

Structured static source for the ZTOVALUE enterprise valve website. The public
site is built from source pages, legacy styling and interaction modules, and a
curated asset bundle.

## Structure

```text
src/
  pages/              Source HTML pages
  styles/legacy/      Reused production CSS, flattened from the old cache path
  scripts/legacy/     Reused production JavaScript modules
  assets-manifest/    Delivery asset mapping and source notes
public/
  assets/             Runtime images, fonts, videos, GLB files, and hero frames
scripts/
  build-site.mjs      Builds dist/
  check-assets.mjs    Validates required delivery assets
  serve-preview.mjs   Local preview server with /ztovalue prefix
```

The delivery asset manifest is stored at
`src/assets-manifest/delivery-assets.json`.

## Local Verification

```bash
npm install
npm run check:assets
npm run build
npm run preview
```

Open:

```text
http://127.0.0.1:4179/ztovalue/
```

## Deployment

The `main` branch keeps the structured source. The built site is published from
the `gh-pages` branch to:

```text
https://cooper-x-oak.github.io/ztovalue/
```
