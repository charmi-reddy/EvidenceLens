// These are deterministic local UI fixtures. They are test-only intercepts;
// the shipped user workflow still sends each request to the live Flask API.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixtures = path.resolve(here, '../../fixtures');
const imagePath = path.join(here, 'assets', 'red-circle.png');

async function openWithFixture(page, fixtureName, caption) {
  const body = JSON.parse(fs.readFileSync(path.join(fixtures, fixtureName), 'utf8'));
  let releaseResponse;
  let notifyRequest;
  const responseGate = new Promise(resolve => { releaseResponse = resolve; });
  const requestSeen = new Promise(resolve => { notifyRequest = resolve; });
  await page.route('**/api/analyze', async route => {
    const request = route.request();
    expect(request.headers()['content-type']).toContain('multipart/form-data');
    expect(request.postData()).toContain(caption);
    notifyRequest();
    await responseGate;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('/');
  await page.locator('#image-file').setInputFiles(imagePath);
  await expect(page.getByAltText('Preview of the image you selected')).toBeVisible();
  await page.getByLabel('Caption or claims').fill(caption);
  await page.getByRole('button', { name: /analyze consistency/i }).click();
  await requestSeen;
  await expect(page.getByText('Looking closely…')).toBeVisible();
  releaseResponse();
  await expect(page.locator('.claim-card').first()).toBeVisible();
  return body;
}

const oneClaimCases = [
  ['evidencelens-supported.json', 'A red circle is visible in the image.', 'Supported', 'WHAT’S VISIBLE'],
  ['evidencelens-contradicted.json', 'A blue square is visible in the image.', 'Contradicted', 'WHAT’S VISIBLE'],
  ['evidencelens-insufficient.json', 'This image was taken in Hyderabad.', 'Insufficient evidence', 'WHY THIS VERDICT'],
];

for (const [fixture, caption, label, evidenceHeading] of oneClaimCases) {
  test(`fixture rendering: ${label}`, async ({ page }) => {
    const body = await openWithFixture(page, fixture, caption);
    await expect(page.locator('.overall-card')).toContainText(label);
    await expect(page.locator('.claim-card .status-pill')).toContainText(label);
    await expect(page.locator('.claim-card')).toContainText(evidenceHeading);
    await expect(page.locator('.claim-card')).toContainText(body.claims[0].evidence);
    await expect(page.locator('.claim-card')).toContainText(body.claims[0].explanation);
    await expect(page.locator('.limitations-card')).toBeVisible();
  });
}

test('mixed fixture renders all claim verdicts and the backend overall aggregation', async ({ page }) => {
  const body = await openWithFixture(
    page,
    'evidencelens-mixed-claims.json',
    'A red circle is visible. A blue square is visible. This image was taken in Hyderabad.',
  );
  const cards = page.locator('.claim-card');
  await expect(cards).toHaveCount(3);
  const renderedStatuses = await cards.locator('.status-pill').allTextContents();
  expect(renderedStatuses.map(value => value.trim())).toEqual([
    'Supported', 'Contradicted', 'Insufficient evidence',
  ]);
  await expect(page.locator('.overall-card')).toContainText('Contradicted');
  await expect(page.locator('.count-supported')).toContainText('1 supported');
  await expect(page.locator('.count-contradicted')).toContainText('1 contradicted');
  await expect(page.locator('.count-insufficient')).toContainText('1 unclear');
  for (let i = 0; i < body.claims.length; i += 1) {
    await expect(cards.nth(i)).toContainText(body.claims[i].evidence);
    await expect(cards.nth(i)).toContainText(body.claims[i].explanation);
  }
  await expect(page.locator('.limitations-card')).toContainText('capture location or time');
});
