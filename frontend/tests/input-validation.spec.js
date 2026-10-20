import { test, expect } from '@playwright/test';
import path from 'node:path';

const imagePath = path.join(import.meta.dirname, 'assets', 'red-circle.png');

test('prevents requests when the image or caption is missing', async ({ page }) => {
  let requestCount = 0;
  page.on('request', request => {
    if (request.url().includes('/api/analyze')) requestCount += 1;
  });
  await page.goto('/');
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByRole('alert')).toContainText('Add an image before analyzing');
  expect(requestCount).toBe(0);

  await page.locator('#image-file').setInputFiles(imagePath);
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByRole('alert')).toContainText('Add a caption or a few claims');
  expect(requestCount).toBe(0);
});

test('rejects unsupported file types before making an API request', async ({ page }) => {
  let requestCount = 0;
  page.on('request', request => {
    if (request.url().includes('/api/analyze')) requestCount += 1;
  });
  await page.goto('/');
  await page.locator('#image-file').setInputFiles({
    name: 'not-an-image.txt', mimeType: 'text/plain', buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText('Choose a JPEG, PNG, or WEBP image');
  expect(requestCount).toBe(0);
});
