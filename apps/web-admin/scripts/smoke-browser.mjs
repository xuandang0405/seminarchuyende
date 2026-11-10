import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import puppeteer from 'puppeteer-core';

const base = process.env.TOURVOICE_TEST_URL || 'http://127.0.0.1:18081';
const executablePath = process.env.BROWSER_EXECUTABLE ||
  (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : '/usr/bin/google-chrome');
const browser = await puppeteer.launch({ executablePath, headless: true, args: [
  '--enable-unsafe-swiftshader', ...(process.env.CI ? ['--no-sandbox'] : []),
] });
try {
  const page = await browser.newPage();
  const errors = [], tiles = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.url().includes('tile.openstreetmap.org')) tiles.push(response.status()); });
  page.on('requestfailed', request => { if (request.url().includes('tile.openstreetmap.org')) tiles.push(request.failure()?.errorText); });
  page.on('dialog', dialog => dialog.dismiss());
  await page.evaluateOnNewDocument(() => {
    window.__audioStarted = [];
    document.addEventListener('playing', event => {
      if (event.target instanceof HTMLAudioElement) window.__audioStarted.push(event.target.currentSrc);
    }, true);
  });
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await page.goto(base + '/account', { waitUntil: 'networkidle2' });
  await page.waitForFunction(() => location.pathname.replace(/\/$/, '') === '/client/login');
  await page.waitForSelector('input[type=email]');
  await page.goto(base + '/client/', { waitUntil: 'networkidle2' });
  await page.waitForSelector('#root header');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Mobile view overflows');
  for (const path of ['/sw.js', '/registerSW.js', '/manifest.webmanifest', '/assets/tourvoice-mark.svg', '/assets/tourvoice-mark.png', '/moderation', '/audit-logs']) {
    const response = await fetch(base + path);
    assert.equal(response.status, 200, path);
  }
  const api = async (path, body, method = 'POST') => page.evaluate(async ({ path, body, method }) => {
    const response = await fetch('/api/v1' + path, { method, credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) });
    return { status: response.status, data: await response.json() };
  }, { path, body, method });
  const click = async text => {
    await page.waitForFunction(text => Array.from(document.querySelectorAll('button')).some(button =>
      !button.disabled && button.getBoundingClientRect().width > 0 && (button.getAttribute('aria-label') || button.innerText).includes(text)), { timeout: 12000 }, text);
    const handle = await page.evaluateHandle(text => Array.from(document.querySelectorAll('button'))
      .find(button => !button.disabled && button.getBoundingClientRect().width > 0 &&
        (button.getAttribute('aria-label') || button.innerText).replace(/\s+/g, ' ').includes(text)), text);
    assert.ok(handle.asElement(), 'Missing visible button: ' + text);
    await handle.evaluate(button => button.scrollIntoView({ block: 'center', inline: 'nearest' }));
    await page.waitForFunction(button => {
      const bounds = button.getBoundingClientRect();
      return button.contains(document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2));
    }, { timeout: 6000 }, handle);
    await handle.asElement().click();
    await handle.dispose();
  };
  const waitText = text => page.waitForFunction(text => document.body.innerText.includes(text), { timeout: 20000 }, text);
  const waitAudio = async prefix => {
    await page.waitForSelector('audio');
    const tap = await page.waitForFunction(() => document.body.innerText.includes('Chạm Phát để bắt đầu'), { timeout: 900 }).catch(() => null);
    if (tap) await click('Phát');
    await page.waitForFunction(prefix => {
      const audio = document.querySelector('audio');
      return audio?.currentSrc.includes(prefix) && !audio.paused && window.__audioStarted.includes(audio.currentSrc);
    }, { timeout: 15000 }, prefix);
  };
  await waitText('Điểm kiểm tra TourVoice');
  const localMap = '.tv-map-card[data-basemap="ready"] .leaflet-district-geometry-pane canvas';
  await page.waitForSelector(localMap, { visible: true });
  assert.equal(await page.evaluate(() => Boolean(document.querySelector('.tv-map-viewport .tv-leaflet'))), true);
  assert.ok(await page.$eval('.tv-leaflet', map => map.getBoundingClientRect().height > innerHeight * .7));
  assert.equal(await page.evaluate(() => Array.from(document.querySelectorAll('.tv-map-label-area')).some(label => label.textContent === 'Quận 4')), true);
  assert.deepEqual(tiles, [], 'District map needs to work with zero external tile requests');
  assert.ok(await page.$eval(localMap, canvas => canvas.clientWidth) > 0);
  const markerSelector = '.tv-pin[title^="Điểm kiểm tra"]';
  const positionOfMarker = () => page.$eval(markerSelector, marker => {
    const point = marker.getBoundingClientRect();
    const map = marker.closest('.tv-leaflet').getBoundingClientRect();
    return [point.x - map.x, point.y - map.y];
  });
  const initial = await positionOfMarker();
  await click('Phóng to bản đồ');
  assert.notDeepEqual(await positionOfMarker(), initial, 'Zoom should reproject the point');
  await click('Về trung tâm Quận 4');
  assert.ok((await positionOfMarker()).every((value, axis) => Math.abs(value - initial[axis]) <= 2), 'Return to district should reset the viewport');
  await page.select('.tv-lang-select-hidden', 'en');
  await page.waitForFunction(() => document.documentElement.lang === 'en');
  await page.select('.tv-lang-select-hidden', 'vi');
  await waitText('Điểm kiểm tra TourVoice');
  await click('Đã lưu');
  await click('Tải bản đồ');
  await waitText('Đã lưu bản đồ Quận 4.');
  assert.equal(await page.evaluate(() => localStorage.getItem('tourvoice_map_mode')), 'offline');
  const webgl = await page.evaluate(() => Boolean(document.createElement('canvas').getContext('webgl2')));
  if (webgl) await page.waitForSelector('[data-renderer="pmtiles"] .maplibregl-canvas');
  await click('Bật thống kê');
  await click('Quán ngon');
  const sheetHandle = 'Chuyển kích thước bảng điều khiển';
  const peek = async () => {
    for (let i = 0; i < 2 && await page.$eval('.tv-sheet-dock', dock => dock.dataset.snap) !== 'peek'; i++) {
      await click(sheetHandle);
    }
    await page.waitForFunction(() => document.querySelector('.tv-sheet-dock').getBoundingClientRect().height < 210);
  };
  await peek();
  await page.hover('.tv-pin[title^="<img"]');
  await page.waitForFunction(() => document.querySelector('.leaflet-tooltip')?.textContent.startsWith('<img'));
  assert.equal(await page.evaluate(() => window.__reviewPopupExecuted), undefined, 'Markup executed in the map label');
  await page.click('.tv-pin[title^="Điểm kiểm tra"]');
  await page.browserContext().setPermission(base, { permission: { name: 'geolocation' }, state: 'granted' });
  await page.setGeolocation({ latitude: 10.7635, longitude: 106.7042, accuracy: 10 });
  await click('Chỉ đường');
  await page.waitForSelector('.tv-map-route');
  await click(sheetHandle);
  await waitText('Bạn đang ở ngay điểm đến');
  await click('Ẩn lộ trình');
  const consentResponse = page.waitForResponse(response => response.url().endsWith('/playback-grants') && response.status() === 403);
  await click('Nghe thuyết minh');
  assert.equal((await (await consentResponse).json()).detail.error_code, 'TRIAL_CONSENT_REQUIRED');
  await waitText('Dùng một lượt nghe thử?');
  await page.waitForSelector('dialog:modal');
  assert.equal(await page.$('audio'), null, 'Audio started without consent');
  const analytics = page.waitForResponse(response => response.url().endsWith('/analytics/events/batch') &&
    response.request().postData()?.includes('narration_started'));
  await click('Đồng ý nghe thử');
  await waitAudio('/stream?grant_token=');
  assert.equal((await (await analytics).json()).accepted_count, 1);
  await page.evaluate(() => { window.__testAudioNode = document.querySelector('audio'); });
  await peek();
  assert.ok(await page.evaluate(() => window.__testAudioNode === document.querySelector('audio') && !window.__testAudioNode.paused));
  await click(sheetHandle);
  await click('Dừng');
  await click('Nghe thuyết minh');
  await waitText('Đã dùng hết lượt nghe thử');
  await page.waitForSelector('dialog:modal');
  await click('Xem vé tuyến tour');
  await waitText('Đăng nhập để mua vé');
  const guest = await api('/guest-sessions');
  const resumed = await api('/guest-sessions');
  assert.equal(guest.data.guest_session_id, resumed.data.guest_session_id);
  const registered = await api('/auth/register', { email: 'browser-' + Date.now() + '@example.org',
    full_name: 'Browser review', password: 'ReviewPass@2026', confirm_password: 'ReviewPass@2026' });
  assert.equal(registered.status, 201, JSON.stringify(registered.data));
  await page.reload({ waitUntil: 'networkidle2' });
  await click('Tuyến tour');
  await click('Tour kiểm tra');
  const created = page.waitForResponse(response => response.url().endsWith('/payments/simulate-checkout') && response.request().method() === 'POST');
  await click('Mô phỏng thanh toán thành công');
  const response = await created;
  assert.equal(response.status(), 200);
  const order = await response.json();
  assert.equal(order.data?.amount_vnd, 99000, JSON.stringify(order));
  assert.equal(order.data?.status, 'paid');
  assert.match(order.data?.ticket_code, /^TICKET-Q4-/);
  await waitText('Thanh toán mô phỏng thành công');
  await page.waitForFunction(() => document.querySelector('.tv-detail-view .tv-card-kicker')?.textContent.trim() === 'Đã sở hữu vé');
  await click('Điểm kiểm tra TourVoice');
  const playback = page.waitForResponse(response => response.url().endsWith('/playback-grants') && response.status() === 200);
  await click('Nghe thuyết minh');
  assert.equal((await (await playback).json()).scope, 'entitled');
  await waitAudio('/stream?grant_token=');
  await click('Dừng');
  await click('Về tuyến tour');
  await click('Tải gói');
  await page.waitForFunction(() => document.body.innerText.includes('Đã lưu thuyết minh ngoại tuyến'), { timeout: 30000 });
  await click('Tất cả tuyến tour');
  await click('Tour miễn phí mẫu');
  await click('Tải gói');
  await waitText('Đã lưu thuyết minh ngoại tuyến');
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), { timeout: 12000 });
  await page.setOfflineMode(true);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await click('Đã lưu');
  await page.waitForSelector(localMap, { visible: true });
  await waitText('Đang dùng bản đồ Quận 4 ngoại tuyến.');
  if (webgl) await page.waitForSelector('[data-renderer="pmtiles"] .maplibregl-canvas');
  await click('Tour kiểm tra');
  await click('Điểm kiểm tra TourVoice');
  await click('Nghe thuyết minh');
  await waitAudio('blob:');
  const screenshots = process.env.BROWSER_SCREENSHOT_DIR;
  if (screenshots) {
    await mkdir(screenshots, { recursive: true });
    await page.screenshot({ path: join(screenshots, 'tourvoice-mobile-offline.png'), fullPage: true });
  }
  await page.setOfflineMode(false);
  await api('/auth/logout');
  await page.goto(base + '/admin/login', { waitUntil: 'networkidle2' });
  if (screenshots) await page.screenshot({ path: join(screenshots, 'tourvoice-sign-in.png'), fullPage: true });
  await page.type('input[type=email]', 'review-admin@example.org');
  await page.type('input[type=password]', 'ReviewPass@2026');
  await page.click('button[type=submit]');
  await page.waitForFunction(() => location.pathname === '/admin', { timeout: 15000 });
  await page.waitForSelector('[aria-label="Mở menu điều hướng"]');
  await page.click('[aria-label="Mở menu điều hướng"]');
  await page.waitForSelector('.console-sidebar.is-open');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('.console-sidebar.is-open'));
  await page.setViewport({ width: 1440, height: 900 });
  await waitText('Không gian quản trị');
  if (screenshots) await page.screenshot({ path: join(screenshots, 'tourvoice-console.png'), fullPage: true });
  await page.goto(base + '/pois', { waitUntil: 'networkidle2' });
  await page.waitForFunction(() => document.body.innerText.includes('Điểm kiểm tra TourVoice'));
  if (screenshots) {
    await page.screenshot({ path: join(screenshots, 'tourvoice-admin.png'), fullPage: true });
    await page.goto(base + '/client', { waitUntil: 'networkidle2' });
    await waitText('Điểm kiểm tra TourVoice');
    await page.type('.tv-search-desktop input[type=search]', 'Diem kiem tra');
    await page.waitForFunction(() => document.querySelectorAll('.tv-list .tv-card-item').length === 1);
    await page.$eval('.tv-search-desktop input[type=search]', input => input.blur());
    await page.screenshot({ path: join(screenshots, 'tourvoice-desktop.png'), fullPage: true });
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ result: 'PASS', checks: ['map-first mobile layout', 'verified PMTiles pack online and offline', 'UI language switching', 'zoom and return to district', 'safe map label', 'one-click GPS routing', 'PWA assets', 'guest resume', 'trial consent and grant playback', 'verified playback analytics',
    'playback survives bottom-sheet resize', 'trial exhaustion opens tour ticket', 'one-click simulated payment at server price',
    'paid narration grant', 'two verified offline downloads', 'offline reload and real MP3 playback',
    'admin login redirect', 'admin POI list'], tileResponses: [...new Set(tiles)] }));
} finally { await browser.close(); }
