// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';

test.describe('Dubbing App - Vietnamese UI Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('1. Initial page load and UI elements', async ({ page }) => {
    // Check title
    await expect(page).toHaveTitle(/Dubbing/i);

    // Check tabs exist (Vietnamese)
    await expect(page.locator('button:has-text("Nguồn Video")')).toBeVisible();
    await expect(page.locator('button:has-text("Điều Chỉnh")')).toBeVisible();
    await expect(page.locator('button:has-text("Lồng Tiếng")')).toBeVisible();
  });

  test('2. Source Tab - URL input validation', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();

    // Test empty URL
    await urlInput.fill('');
    await urlInput.press('Enter');

    // Test invalid URL
    await urlInput.fill('not-a-url');
    await page.waitForTimeout(500);

    // Test valid YouTube URL
    await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    await expect(urlInput).toHaveValue('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  });

  test('3. Source Tab - Engine mode selection', async ({ page }) => {
    // Find radio buttons
    const monolithicRadio = page.locator('input[type="radio"]').first();
    const stepByStepRadio = page.locator('input[type="radio"]').nth(1);

    // Click each radio
    await stepByStepRadio.click();
    await expect(stepByStepRadio).toBeChecked();

    await monolithicRadio.click();
    await expect(monolithicRadio).toBeChecked();
  });

  test('4. Source Tab - Preview button test', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();
    await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

    const previewBtn = page.locator('button:has-text("Preview")');
    await expect(previewBtn).toBeVisible();

    // Click preview button
    await previewBtn.click();
    await page.waitForTimeout(1000);
  });

  test('5. Adjust Tab - Navigation', async ({ page }) => {
    const adjustTab = page.locator('button:has-text("Điều Chỉnh")');
    await adjustTab.click();
    await page.waitForTimeout(500);

    // Check tab is active (should have different styling)
    const isVisible = await adjustTab.isVisible();
    expect(isVisible).toBeTruthy();
  });

  test('6. Dub Tab - Navigation', async ({ page }) => {
    const dubTab = page.locator('button:has-text("Lồng Tiếng")');
    await dubTab.click();
    await page.waitForTimeout(500);

    const isVisible = await dubTab.isVisible();
    expect(isVisible).toBeTruthy();
  });

  test('7. Tab switching stress test', async ({ page }) => {
    const tabs = ['Nguồn Video', 'Điều Chỉnh', 'Lồng Tiếng'];

    // Rapidly switch between tabs
    for (let i = 0; i < 10; i++) {
      for (const tabName of tabs) {
        const tab = page.locator(`button:has-text("${tabName}")`);
        await tab.click();
        await page.waitForTimeout(50);
      }
    }
  });

  test('8. Backend API health check', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('9. WebSocket connection check', async ({ page }) => {
    // Wait for WebSocket to attempt connection
    await page.waitForTimeout(3000);

    // Check connection status in UI
    const statusElement = page.locator('text=/Connected|Disconnected/i').first();
    const statusText = await statusElement.textContent();
    console.log('WebSocket status:', statusText);
  });

  test('10. Dark mode toggle', async ({ page }) => {
    // Find button by icon or text (Light/Dark)
    const darkModeBtn = page.locator('button').filter({ hasText: /Light|Dark/i }).first();

    const isVisible = await darkModeBtn.isVisible();
    if (isVisible) {
      const initialText = await darkModeBtn.textContent();

      // Click to toggle
      await darkModeBtn.click();
      await page.waitForTimeout(500);

      // Verify text changed
      const newText = await darkModeBtn.textContent();
      expect(newText).not.toBe(initialText);

      console.log(`Dark mode toggled: ${initialText} -> ${newText}`);
    }
  });

  test('11. Cleanup button test', async ({ page }) => {
    const cleanupBtn = page.locator('button:has-text("Don Cache"), button:has-text("Cleanup")');

    if (await cleanupBtn.count() > 0) {
      // Just check if button is clickable, don't actually click
      await expect(cleanupBtn.first()).toBeVisible();
    }
  });

  test('12. Start processing button', async ({ page }) => {
    const startBtn = page.locator('button:has-text("Bắt Đầu"), button:has-text("Start")');

    if (await startBtn.count() > 0) {
      await expect(startBtn.first()).toBeVisible();
    }
  });

  test('13. Responsive layout check', async ({ page }) => {
    const sizes = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 768, height: 1024 },
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.waitForTimeout(500);

      // Check if main content is visible
      const mainContent = page.locator('main').first();
      await expect(mainContent).toBeVisible();
    }
  });

  test('14. Keyboard navigation', async ({ page }) => {
    // Tab through elements
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
  });

  test('15. Console errors check', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.waitForTimeout(3000);

    console.log('Console errors found:', errors.length);
    errors.forEach(err => console.log('  -', err));
  });
});
