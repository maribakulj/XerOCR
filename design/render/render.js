/* Offline reference-screenshot renderer for the XerOCR design report views.
 *
 * Single source of truth: the *real* design files one level up
 * (../tokens.css owns the typography, ../picarones.css the components,
 * ../*.jsx the views). No font/branding overrides live here — if a render
 * looks wrong, the design source is wrong, not this harness.
 *
 * Why a browser at all: the views are React/JSX. We mount them with React +
 * @babel/standalone (installed via npm) and screenshot with Playwright. Fonts
 * (Fluxisch Else + OCR-A) and the Xerox halftone are self-hosted data/woff2 in
 * ../fonts + ../tokens.css, so rendering needs ZERO network.
 *
 * Usage:  node render.js <overview|by-engine|by-document|crosses>
 * Env:    CHROMIUM_PATH  path to a Chromium/Chrome binary (Playwright's or system)
 *         DSF            deviceScaleFactor (default 1.5)
 */
'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DESIGN = path.resolve(__dirname, '..'); // design/
const HERE = __dirname;                        // design/render/
const CHROME = process.env.CHROMIUM_PATH
  || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const DSF = Number(process.env.DSF || 1.5);

// view name (file) -> ReportApp tab id (chrome.jsx)
const VIEWS = {
  overview: 'overview',
  'by-engine': 'engines',
  'by-document': 'documents',
  crosses: 'crosses',
};

function harness(tab) {
  const f = (p) => 'file://' + path.join(DESIGN, p);
  const nm = (p) => 'file://' + path.join(HERE, 'node_modules', p);
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<link rel="stylesheet" href="${f('tokens.css')}">
<link rel="stylesheet" href="${f('picarones.css')}">
<style>/* capture-only: let the board grow for a full-page shot */
.report-board{height:auto!important;min-height:auto!important;overflow:visible!important;max-width:1200px;margin:0 auto;}</style>
<script src="${nm('react/umd/react.development.js')}"></script>
<script src="${nm('react-dom/umd/react-dom.development.js')}"></script>
<script src="${nm('@babel/standalone/babel.min.js')}"></script>
</head><body><div id="root"></div>
<script type="text/babel" data-presets="react" src="${f('data.jsx')}"></script>
<script type="text/babel" data-presets="react" src="${f('chrome.jsx')}"></script>
<script type="text/babel" data-presets="react" src="${f('view-synthesis.jsx')}"></script>
<script type="text/babel" data-presets="react" src="${f('view-by-engine.jsx')}"></script>
<script type="text/babel" data-presets="react" src="${f('view-by-document.jsx')}"></script>
<script type="text/babel" data-presets="react" src="${f('view-crosses.jsx')}"></script>
<script type="text/babel" data-presets="react">
ReactDOM.createRoot(document.getElementById('root')).render(<ReportApp initialTab="${tab}" />);
</script></body></html>`;
}

(async () => {
  const name = process.argv[2];
  const tab = VIEWS[name];
  if (!tab) {
    console.error('usage: node render.js <' + Object.keys(VIEWS).join('|') + '>');
    process.exit(2);
  }
  const htmlPath = path.join(HERE, `.harness-${name}.html`);
  fs.writeFileSync(htmlPath, harness(tab));
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--allow-file-access-from-files', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: DSF });
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle' });
  try { await page.evaluate(() => document.fonts.ready); } catch (_) { /* ok */ }
  await page.waitForTimeout(600);
  const out = path.join(DESIGN, 'screenshots', `report-${name}.png`);
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  fs.unlinkSync(htmlPath);
  if (errs.length) { console.error('page errors:', errs.join(' | ')); process.exit(1); }
  console.log('wrote', path.relative(DESIGN, out));
})().catch((e) => { console.error(e.message || e); process.exit(1); });
