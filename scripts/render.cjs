// Screenshot every slide of a day to <day>/png/<post>_<n>.png at 1080x1350, and a JPEG copy
// to <day>/jpg/ (the Instagram API takes JPEG only for images).
//   node render.cjs <day_dir>
// Fails (exit 1) on a missing image, a brand font that did not load, or anything past the
// canvas: a fallback font or a clipped line must never reach a post.
const fs = require('fs'), path = require('path');
const SKILL = path.resolve(__dirname, '..');

function playwright() {
  // 1) the skill's own node_modules (`npm install` in the skill folder), 2) the npx cache
  //    (`npx playwright@<v> install chromium` leaves a copy there). Take the newest.
  try { return require(require.resolve('playwright', { paths: [SKILL] })); } catch (e) { /* fall through */ }
  const base = path.join(process.env.HOME || '', '.npm/_npx');
  const found = fs.existsSync(base) ? fs.readdirSync(base).map(d => path.join(base, d, 'node_modules/playwright'))
    .filter(p => fs.existsSync(path.join(p, 'package.json')))
    .sort((a, b) => require(path.join(b, 'package.json')).version.localeCompare(require(path.join(a, 'package.json')).version, undefined, { numeric: true })) : [];
  if (!found.length) throw new Error('playwright not found: run `npm install` in the skill folder (see INSTALL.md)');
  return require(found[0]);
}

const brand = JSON.parse(fs.readFileSync(process.env.IG_BRAND || path.join(SKILL, 'brand.json'), 'utf8'));
const FONTS = [brand.fonts.headline, brand.fonts.body];
const { chromium } = playwright();
const day = path.resolve(process.argv[2]);
const manifest = JSON.parse(fs.readFileSync(path.join(day, 'manifest.json'), 'utf8'));
for (const d of ['png', 'jpg']) fs.mkdirSync(path.join(day, d), { recursive: true });
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  for (const names of Object.values(manifest)) for (const n of names) {
    await page.goto('file://' + path.join(day, 'slides', n), { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    const bad = await page.evaluate((fonts) => ({
      imgs: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src),
      fonts: fonts.filter(fam => ![...document.fonts].some(f => f.family.replace(/"/g, '') === fam && f.status === 'loaded')),
      overflow: [...document.querySelectorAll('.hl,.body,.credit,.divider,.rank')]
        .filter(e => { const r = e.getBoundingClientRect(); return r.top < 0 || r.right > 1080 || r.left < 0 ||
          r.bottom > (e.matches('.hl,.body') && document.querySelector('.foot') ? 1350 - 56 : 1350); })   // text must clear the footer line
        .map(e => e.className),
    }), FONTS);
    if (bad.imgs.length || bad.fonts.length || bad.overflow.length) { console.error('FAIL', n, JSON.stringify(bad)); process.exitCode = 1; }
    // PNG for the review sheet, JPEG for Instagram. No ffmpeg: a cloud sandbox may lack it.
    await page.screenshot({ path: path.join(day, 'png', n.replace('.html', '.png')) });
    await page.screenshot({ path: path.join(day, 'jpg', n.replace('.html', '.jpg')), type: 'jpeg', quality: 92 });
    console.log('ok', n);
  }
  await b.close();
})();
