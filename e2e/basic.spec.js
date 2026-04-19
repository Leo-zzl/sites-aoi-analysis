const { test, expect, chromium } = require('@playwright/test');
const path = require('path');

const RENDERER_PATH = `file://${path.resolve(__dirname, '../electron/renderer/index.html')}`;

test.describe('Renderer UI', () => {
  test('page loads with correct title and buttons', async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(RENDERER_PATH);

    // Verify page title
    await expect(page).toHaveTitle(/小区-AOI/);

    // Verify key buttons exist
    await expect(page.locator('text=选择文件').first()).toBeVisible();
    await expect(page.locator('text=校验数据')).toBeVisible();
    await expect(page.locator('text=开始分析')).toBeVisible();

    // Verify sections exist
    await expect(page.locator('text=AOI 数据')).toBeVisible();
    await expect(page.locator('text=站点数据')).toBeVisible();
    await expect(page.locator('text=输出文件')).toBeVisible();

    await browser.close();
  });

  test('analyze button is disabled before validation', async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(RENDERER_PATH);

    const analyzeBtn = page.locator('#analyze-btn');
    await expect(analyzeBtn).toBeDisabled();

    await browser.close();
  });
});
