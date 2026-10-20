import { test, expect } from '@playwright/test';
import path from 'node:path';

const imagePath = path.join(import.meta.dirname, 'assets', 'red-circle.png');

test('uploads image, shows loading state and renders a real API result', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /does the image support the story/i })).toBeVisible();
  await page.locator('#image-file').setInputFiles(imagePath);
  await expect(page.getByAltText('Preview of the image you selected')).toBeVisible();
  await page.getByLabel('Caption or claims').fill('A red circle is visible in the image.');

  const analysisResponse = page.waitForResponse(r => r.url().includes('/api/analyze') && r.request().method() === 'POST');
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByText('Looking closely…')).toBeVisible();
  const response = await analysisResponse;
  expect(response.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Claim-by-claim results' })).toBeVisible();
  await expect(page.getByText('Supported', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('WHAT’S VISIBLE')).toBeVisible();
  await expect(page.getByText(/red circular shape|red circle/i).first()).toBeVisible();
  await expect(page.getByText(/cannot prove a photo is authentic/i)).toBeVisible();
});

test('shows a useful retryable error when the API is unreachable', async ({ page }) => {
  await page.route('**/api/analyze', route => route.abort('failed'));
  await page.goto('/');
  await page.locator('#image-file').setInputFiles(imagePath);
  await page.getByLabel('Caption or claims').fill('A red circle is visible in the image.');
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByRole('alert')).toContainText('Could not reach the EvidenceLens API');
  await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
});

test('keeps the upload and input usable on a narrow mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /does the image support the story/i })).toBeVisible();
  await expect(page.locator('.upload-zone')).toBeVisible();
  await page.locator('#image-file').setInputFiles(imagePath);
  await expect(page.getByAltText('Preview of the image you selected')).toBeVisible();
  await page.getByRole('button', { name: 'Remove selected image' }).click();
  await expect(page.locator('.upload-zone')).toBeVisible();
  const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(pageWidth).toBeLessThanOrEqual(390);
});
