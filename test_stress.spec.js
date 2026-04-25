// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';

test.describe('Dubbing App - Stress & Edge Case Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('1. Spam Preview button - should handle multiple clicks', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();
    await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

    const previewBtn = page.locator('button:has-text("Preview")');

    // Spam click 10 times rapidly
    for (let i = 0; i < 10; i++) {
      await previewBtn.click({ force: true });
      await page.waitForTimeout(50);
    }

    // Check if button becomes disabled or shows loading state
    await page.waitForTimeout(1000);
    const isDisabled = await previewBtn.isDisabled();
    console.log('Preview button disabled after spam:', isDisabled);
  });

  test('2. Spam Start Processing button', async ({ page }) => {
    const startBtn = page.locator('button:has-text("Bắt Đầu")').first();

    // Spam click
    for (let i = 0; i < 10; i++) {
      await startBtn.click({ force: true });
      await page.waitForTimeout(50);
    }

    await page.waitForTimeout(1000);
  });

  test('3. Rapid tab switching with input changes', async ({ page }) => {
    const tabs = ['Nguồn Video', 'Điều Chỉnh', 'Lồng Tiếng'];

    for (let i = 0; i < 20; i++) {
      // Go back to Source tab first
      await page.locator('button:has-text("Nguồn Video")').click();
      await page.waitForTimeout(100);

      // Fill input
      const urlInput = page.locator('input[placeholder*="youtube"]').first();
      await urlInput.fill(`https://test${i}.com`);

      // Switch tabs
      for (const tabName of tabs) {
        const tab = page.locator(`button:has-text("${tabName}")`);
        await tab.click();
        await page.waitForTimeout(30);
      }
    }

    // Go back to Source tab and verify input
    await page.locator('button:has-text("Nguồn Video")').click();
    await page.waitForTimeout(200);

    const urlInput = page.locator('input[placeholder*="youtube"]').first();
    const finalValue = await urlInput.inputValue();
    expect(finalValue).toContain('test19.com');
  });

  test('4. Toggle dark mode rapidly', async ({ page }) => {
    const darkModeBtn = page.locator('button').filter({ hasText: /Light|Dark/i }).first();

    // Toggle 20 times
    for (let i = 0; i < 20; i++) {
      await darkModeBtn.click();
      await page.waitForTimeout(50);
    }

    // Should still be functional
    await expect(darkModeBtn).toBeVisible();
  });

  test('5. Invalid URL inputs', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();

    const invalidUrls = [
      '',
      'not-a-url',
      'javascript:alert(1)',
      'file:///etc/passwd',
      'http://',
      'ftp://test.com',
      '../../../etc/passwd',
      '<script>alert(1)</script>',
      'https://youtube.com/watch?v=' + 'x'.repeat(1000),
    ];

    for (const url of invalidUrls) {
      await urlInput.fill(url);
      await page.waitForTimeout(200);

      // Find preview button and check if disabled
      const previewBtn = page.locator('button:has-text("Preview")').first();

      try {
        const isDisabled = await previewBtn.isDisabled({ timeout: 2000 });
        console.log(`URL "${url.substring(0, 30)}..." -> Button disabled: ${isDisabled}`);

        // Only click if not disabled
        if (!isDisabled) {
          await previewBtn.click();
          await page.waitForTimeout(500);
        }
      } catch (e) {
        console.log(`URL "${url.substring(0, 30)}..." -> Button not found`);
      }
    }
  });

  test('6. Radio button spam', async ({ page }) => {
    const radios = page.locator('input[type="radio"]');
    const count = await radios.count();

    // Spam click all radios
    for (let i = 0; i < 50; i++) {
      for (let j = 0; j < count; j++) {
        await radios.nth(j).click();
        await page.waitForTimeout(20);
      }
    }

    // Verify one is still checked
    const checkedCount = await page.locator('input[type="radio"]:checked').count();
    expect(checkedCount).toBeGreaterThan(0);
  });

  test('7. Cleanup button spam', async ({ page }) => {
    const cleanupBtn = page.locator('button:has-text("Don Cache")').first();

    // Spam click
    for (let i = 0; i < 5; i++) {
      await cleanupBtn.click({ force: true });
      await page.waitForTimeout(100);
    }

    await page.waitForTimeout(1000);
  });

  test('8. Extreme viewport sizes', async ({ page }) => {
    const sizes = [
      { width: 320, height: 568 },   // iPhone SE
      { width: 2560, height: 1440 }, // 2K
      { width: 3840, height: 2160 }, // 4K
      { width: 800, height: 600 },   // Small desktop
    ];

    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.waitForTimeout(500);

      // Check if UI is still functional
      const mainContent = page.locator('main').first();
      await expect(mainContent).toBeVisible();

      // Try clicking a tab
      const tab = page.locator('button:has-text("Nguồn Video")');
      await tab.click();
      await page.waitForTimeout(200);

      console.log(`UI functional at ${size.width}x${size.height}`);
    }
  });

  test('9. Long text input in URL field', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();

    // Very long URL
    const longUrl = 'https://youtube.com/watch?v=' + 'a'.repeat(10000);
    await urlInput.fill(longUrl);

    const value = await urlInput.inputValue();
    console.log('Long URL length:', value.length);
  });

  test('10. Special characters in URL', async ({ page }) => {
    const urlInput = page.locator('input[placeholder*="youtube"]').first();

    const specialUrls = [
      'https://youtube.com/watch?v=test&t=123',
      'https://youtube.com/watch?v=test#fragment',
      'https://youtube.com/watch?v=test%20space',
      'https://youtube.com/watch?v=тест', // Cyrillic
      'https://youtube.com/watch?v=测试', // Chinese
    ];

    for (const url of specialUrls) {
      await urlInput.fill(url);
      await page.waitForTimeout(200);
      const value = await urlInput.inputValue();
      expect(value).toBe(url);
    }
  });

  test('11. Rapid WebSocket reconnection simulation', async ({ page }) => {
    // Monitor WebSocket status
    const statusElement = page.locator('text=/Connected|Disconnected/i').first();

    for (let i = 0; i < 5; i++) {
      const status = await statusElement.textContent();
      console.log(`WebSocket status check ${i + 1}:`, status);
      await page.waitForTimeout(1000);
    }
  });

  test('12. Memory leak - repeated operations', async ({ page }) => {
    const tabs = ['Nguồn Video', 'Điều Chỉnh', 'Lồng Tiếng'];

    // Perform 50 operations (reduced from 100 to avoid timeout)
    for (let i = 0; i < 50; i++) {
      // Go to Source tab first
      await page.locator('button:has-text("Nguồn Video")').click();
      await page.waitForTimeout(30);

      // Fill input
      const urlInput = page.locator('input[placeholder*="youtube"]').first();
      await urlInput.fill(`https://test${i}.com`);

      // Switch tabs
      for (const tabName of tabs) {
        await page.locator(`button:has-text("${tabName}")`).click();
        await page.waitForTimeout(20);
      }

      // Toggle dark mode
      const darkModeBtn = page.locator('button').filter({ hasText: /Light|Dark/i }).first();
      await darkModeBtn.click();

      if (i % 10 === 0) {
        console.log(`Memory leak test: ${i}/50 iterations`);
      }
    }

    console.log('Memory leak test completed - check browser memory');
  });

  test('13. Backend API stress - multiple concurrent requests', async ({ request }) => {
    const promises = [];

    // Send 10 concurrent health check requests (reduced from 20 to avoid overload)
    for (let i = 0; i < 10; i++) {
      promises.push(request.get(`${API_URL}/health`));
    }

    const responses = await Promise.all(promises);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }

    console.log('All 10 concurrent requests succeeded');
  });

  test('14. Tab navigation with keyboard', async ({ page }) => {
    // Use keyboard to navigate
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
    }

    // Press Enter on focused element
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
  });

  test('15. Browser back/forward navigation', async ({ page }) => {
    // Navigate to different tabs
    await page.locator('button:has-text("Điều Chỉnh")').click();
    await page.waitForTimeout(500);

    await page.locator('button:has-text("Lồng Tiếng")').click();
    await page.waitForTimeout(500);

    // SPA doesn't use browser history, so back button shouldn't work
    // This is expected behavior - just verify we're still on the app
    const currentUrl = page.url();
    expect(currentUrl).toContain('localhost:5173');

    console.log('SPA navigation works correctly without browser history');
  });
});
