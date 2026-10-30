import { readFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));

await withBrowser("workspace navigation keeps the workspace visible between pages", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ENROLL_USER;
  const password = process.env.APP_E2E_ENROLL_PASS;
  assert.ok(username && password, "An ordinary speaker account is required");
  const text = catalogues.tr;
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(baseUrl + "/login");
  await page.getByLabel(text["login.username"], { exact: true }).fill(username);
  await page.getByLabel(text["login.password"], { exact: true }).fill(password);
  await page.getByRole("button", { name: text["login.submit"], exact: true }).click();
  await page.waitForURL(baseUrl + "/");
  const navigation = page.getByRole("navigation", { name: text["nav.main"], exact: true });
  await navigation.waitFor();
  // Record every frame in which the main navigation is missing from the document.
  await page.evaluate(() => {
    window.__workspaceGaps = 0;
    new MutationObserver(() => {
      if (!document.querySelector("nav.workspace-nav")) window.__workspaceGaps += 1;
    }).observe(document.body, { childList: true, subtree: true });
  });
  const stops = [["nav.profiles", "speaker.profiles.saved"], ["nav.analysis", "nav.analysis"], ["nav.home", "home.title"], ["nav.profiles", "speaker.profiles.saved"]];
  for (const [link, heading] of stops) {
    await navigation.getByRole("link", { name: text[link], exact: true }).click();
    await page.getByRole("heading", { name: text[heading], exact: true }).first().waitFor();
  }
  const gaps = await page.evaluate(() => window.__workspaceGaps);
  assert.equal(gaps, 0, `the workspace disappeared ${gaps} time(s) during navigation`);
  assert.deepEqual(errors, []);
}, { requireCredentials: false });
