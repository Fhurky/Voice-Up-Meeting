import {chromium, expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';

export const baseUrl = (process.env.APP_E2E_BASE || 'http://127.0.0.1:8081').replace(/\/$/, '');
export const username = process.env.APP_E2E_SUPER_ADMIN_USER || process.env.VOICEUP_SUPER_ADMIN_USER;
export const password = process.env.APP_E2E_SUPER_ADMIN_PASS || process.env.VOICEUP_SUPER_ADMIN_PASS;

export async function withBrowser(name, scenario) {
  assert.ok(username, 'APP_E2E_SUPER_ADMIN_USER is required');
  assert.ok(password, 'APP_E2E_SUPER_ADMIN_PASS is required');
  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext();
  const allowedOrigin = new URL(baseUrl).origin;
  const externalRequests = [];
  await context.route('**/*', async (route) => {
    const requestUrl = route.request().url();
    const protocol = new URL(requestUrl).protocol;
    if (new URL(requestUrl).origin === allowedOrigin || protocol === 'data:' || protocol === 'blob:') {
      await route.continue();
      return;
    }
    externalRequests.push(requestUrl);
    await route.abort('blockedbyclient');
  });
  const page = await context.newPage();
  try {
    await scenario({page, assert});
    assert.deepEqual(externalRequests, [], 'browser attempted an external network request');
    console.log('PASS ' + name);
  } catch (error) {
    await mkdir('test-results', {recursive: true});
    const artifact = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    await page.screenshot({path: `test-results/${artifact || 'scenario'}-failure.png`, fullPage: true});
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

export async function runScenario(name, scenario) {
  return withBrowser(name, ({page}) => scenario({page, expect}));
}
