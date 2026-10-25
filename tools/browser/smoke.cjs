/* Real-browser delivery checks; no training, inference or organizer requests. */
const { chromium: playwright } = require('playwright-core');
const runtime = require('@sparticuz/chromium');
const chromium = runtime.default;
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '../..');
const output = path.join(root, 'work/browser-proof');
const baseURL = process.env.PORTAL_BASE_URL || 'http://127.0.0.1:8000/';

async function main() {
  fs.mkdirSync(output, { recursive: true });
  // The npm package bundles its browser and NSS libraries; no download from
  // unapproved browser-CDN hosts is required in the constrained sandbox.
  await runtime.inflate(path.join(__dirname, 'node_modules/@sparticuz/chromium/bin/al2023.tar.br'));
  runtime.setupLambdaEnvironment('/tmp/al2023/lib');
  const browser = await playwright.launch({
    headless: true,
    executablePath: await chromium.executablePath(),
    args: chromium.args,
  });
  const errors = [];
  const accessibility = [];
  let report;
  try {
    const context = await browser.newContext({
      acceptDownloads: true,
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    page.on('response', response => {
      if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    });
    if (process.env.PORTAL_ENTRY_URL) {
      await page.goto(process.env.PORTAL_ENTRY_URL, { waitUntil: 'networkidle' });
      await page.waitForURL(new URL('index.html', baseURL).href);
    }
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    const submissionStates = page.locator('[data-submission-ready]');
    const stateCount = await submissionStates.count();
    const allStatesFailClosed = await submissionStates.evaluateAll(nodes =>
      nodes.length > 0 && nodes.every(node => node.getAttribute('data-submission-ready') === 'false')
    );
    if (!allStatesFailClosed || stateCount === 0) {
      throw new Error('Missing fail-closed negative submission state');
    }
    if (!(await page.getByText('NOT OK TO SUBMIT', { exact: true }).count())) {
      throw new Error('Submission warning is not visible');
    }
    // The current candidate has one obvious download and an automated negative verdict.
    const s16DownloadEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: '↓ Download S16 research TIFF', exact: true }).click();
    const s16Download = await s16DownloadEvent;
    const s16Bytes = fs.readFileSync(await s16Download.path());
    const s16Digest = crypto.createHash('sha256').update(s16Bytes).digest('hex');
    const s16Card = JSON.parse(fs.readFileSync(path.join(root, 'docs/run-card-S16.json')));
    if (s16Digest !== s16Card.raster_sha256 || s16Card.ok_to_submit !== false) {
      throw new Error('Current S16 download identity/readiness mismatch');
    }
    const s16ZipEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Single-TIFF ZIP', exact: true }).click();
    const s16Zip = await s16ZipEvent;
    const s16ZipDigest = crypto.createHash('sha256').update(fs.readFileSync(await s16Zip.path())).digest('hex');
    if (s16ZipDigest !== s16Card.artifact.zip_sha256) throw new Error('Current ZIP download bytes mismatch');
    await page.getByRole('button', { name: 'Copy submission note', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('copy-status').textContent.length > 0);
    await page.locator('h1').click();
    await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    // Historical downloads remain testable, but no longer masquerade as the current page.
    await page.goto(new URL('archive-results.html', baseURL).href, { waitUntil: 'networkidle' });
    const s14DownloadEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: '↓ Download S14-HVDC GeoTIFF', exact: true }).first().click();
    const s14Download = await s14DownloadEvent;
    const s14Bytes = fs.readFileSync(await s14Download.path());
    const s14Digest = crypto.createHash('sha256').update(s14Bytes).digest('hex');
    const s14Card = JSON.parse(fs.readFileSync(path.join(root, 'docs/run-card-S14-HVDC.json')));
    if (s14Digest !== s14Card.raster_sha256) throw new Error('Downloaded S14-HVDC bytes do not match advertised SHA256');

    const s13DownloadEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: '↓ Download S13-PTHA E3 GeoTIFF', exact: true }).click();
    const s13Download = await s13DownloadEvent;
    const s13Bytes = fs.readFileSync(await s13Download.path());
    const s13Digest = crypto.createHash('sha256').update(s13Bytes).digest('hex');
    const s13Card = JSON.parse(fs.readFileSync(path.join(root, 'docs/run-card-S13.json')));
    if (s13Digest !== s13Card.raster_sha256) throw new Error('Downloaded S13-PTHA bytes do not match advertised SHA256');

    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: '↓ Download new CCR91 GeoTIFF', exact: true }).click();
    const download = await downloadEvent;
    const bytes = fs.readFileSync(await download.path());
    const digest = crypto.createHash('sha256').update(bytes).digest('hex');
    const card = JSON.parse(fs.readFileSync(path.join(root, 'docs/run-card-CCR91.json')));
    if (digest !== card.raster_sha256) throw new Error('Downloaded CCR91 bytes do not match advertised SHA256');
    await page.getByRole('button', { name: 'Copy submission note', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('copy-status').textContent.length > 0);
    const copyStatus = await page.locator('#copy-status').textContent();
    await page.screenshot({ path: path.join(output, 'archive-desktop.png'), fullPage: true });

    for (const target of ['index.html', 'executive-summary.html', 'research.html', 'archive-results.html', 's14-hvdc.html', 's14-hvdc-executive-summary.html', 's13-ptha.html', 's13-ptha-executive-summary.html', 's11-mhtr.html', 's11-executive-summary.html', 's12-spac.html', 's12-executive-summary.html', 's12-spid.html', 'spid91-executive-summary.html']) {
      await page.goto(new URL(target, baseURL).href, { waitUntil: 'networkidle' });
      await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
      const result = await page.evaluate(async () => {
        const audit = await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa'] });
        return audit.violations.map(item => ({ id: item.id, impact: item.impact, description: item.description }));
      });
      accessibility.push({ page: target, violations: result });
    }
    // Verify SPID91 download SHA-256 and fail-closed status banner in real Chromium
    await page.goto(new URL('s12-spid.html', baseURL).href, { waitUntil: 'networkidle' });
    if (await page.locator('[data-submission-ready="false"]').count() !== 1) {
      throw new Error('Missing SPID91 fail-closed negative submission state');
    }
    const s12DlEvent = page.waitForEvent('download');
    await page.locator('a[download][href$="-zeros.tif"]').first().click();
    const s12Download = await s12DlEvent;
    const s12Bytes = fs.readFileSync(await s12Download.path());
    const s12Digest = crypto.createHash('sha256').update(s12Bytes).digest('hex');
    const s12Card = JSON.parse(fs.readFileSync(path.join(root, 'docs/run-card-SPID91.json')));
    if (s12Digest !== s12Card.raster_sha256) throw new Error('SPID91 downloaded bytes do not match advertised SHA256');

    let overflow = false;
    await page.setViewportSize({ width: 390, height: 844 });
    for (const mTarget of ['index.html', 's14-hvdc.html', 's14-hvdc-executive-summary.html', 's13-ptha.html', 's13-ptha-executive-summary.html', 's12-spac.html', 's12-executive-summary.html', 's12-spid.html', 'spid91-executive-summary.html']) {
      await page.goto(new URL(mTarget, baseURL).href, { waitUntil: 'networkidle' });
      overflow = overflow || await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      if (overflow) throw new Error(`Mobile horizontal document overflow on ${mTarget}`);
    }
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
    report = {
      status: errors.length || accessibility.some(a => a.violations.length) ? 'FAIL' : 'PASS',
      scope: 'Delivery/UI engineering checks, not a competition score or scientific experiment',
      checked_utc: new Date().toISOString(),
      browser: browser.version(),
      pages_root_redirect_tested: Boolean(process.env.PORTAL_ENTRY_URL),
      desktop: { width: 1440, height: 1000 },
      mobile: { width: 390, height: 844 },
      s16_download_sha256: s16Digest,
      s16_submission_ready: s16Card.ok_to_submit,
      s16_zip_download_sha256: s16ZipDigest,
      s14_download_sha256: s14Digest,
      s13_download_sha256: s13Digest,
      download_sha256: digest,
      copy_status: copyStatus,
      console_or_http_errors: errors,
      mobile_overflow: overflow,
      accessibility,
    };
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(output, 'browser-verification.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== 'PASS') process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
