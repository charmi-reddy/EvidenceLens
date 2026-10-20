import { test, expect } from '@playwright/test';
import path from 'node:path';

const imagePath = path.join(import.meta.dirname, 'assets', 'red-circle.png');

test('rejects malformed success JSON safely and offers a retry', async ({ page }) => {
  await page.route('**/api/analyze', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      overall_status: 'supported',
      claims: [{ text: 'A red circle is visible.', status: 'unknown', evidence: 'Some evidence', explanation: 'Some reason', confidence: 'high' }],
      limitations: [],
    }),
  }));
  await page.goto('/');
  await page.locator('#image-file').setInputFiles(imagePath);
  await page.getByLabel('Caption or claims').fill('A red circle is visible in the image.');
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByRole('alert')).toContainText('incomplete claim result');
  await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
  await expect(page.locator('.claim-card')).toHaveCount(0);
});

test('renders a retryable API quota error without losing the upload or caption', async ({ page }) => {
  await page.route('**/api/analyze', route => route.fulfill({
    status: 429,
    contentType: 'application/json',
    body: JSON.stringify({ error: { message: 'Gemini rate limit or quota exceeded. Check API quota/billing and retry later.' } }),
  }));
  await page.goto('/');
  await page.locator('#image-file').setInputFiles(imagePath);
  await page.getByLabel('Caption or claims').fill('A red circle is visible in the image.');
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await expect(page.getByRole('alert')).toContainText('Gemini rate limit or quota exceeded');
  await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
  await expect(page.getByAltText('Preview of the image you selected')).toBeVisible();
  await expect(page.getByLabel('Caption or claims')).toHaveValue('A red circle is visible in the image.');
});
