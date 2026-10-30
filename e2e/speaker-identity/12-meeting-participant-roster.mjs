import { mkdir, readFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));

await withBrowser("meeting participant roster selection", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ROSTER_USER;
  const password = process.env.APP_E2E_ROSTER_PASS;
  assert.ok(username && password, "An ordinary meeting account with saved profiles is required");
  const failures = [];
  const writes = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") failures.push(message.text()); });
  page.on("response", (response) => {
    if (response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/") && request.method() !== "GET" && !request.url().endsWith("/auth/login")) {
      writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });

  await page.goto(baseUrl + "/login");
  await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
  const loginResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
  await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
  const identity = (await (await loginResponse).json()).user;
  assert.equal(identity.is_super_admin, false, "The roster must be accepted with an ordinary role");
  for (const permission of ["meeting_analysis:run", "speaker_profiles:read"]) {
    assert.ok(identity.permissions.includes(permission), `${permission} is required`);
  }
  await page.waitForURL(baseUrl + "/");

  for (const [locale, width] of [["tr", 1440], ["en", 390]]) {
    const text = catalogues[locale];
    await page.setViewportSize({ width, height: 900 });
    await page.goto(baseUrl + "/meetings?new=file");
    if (locale === "en") await page.getByRole("button", { name: catalogues.tr["common.otherLanguage"], exact: true }).click();
    await page.getByText(text["meeting.advancedOptions"], { exact: true }).click();
    const roster = page.getByRole("group", { name: text["meeting.roster.title"], exact: true });
    await roster.waitFor();
    await roster.getByText(text["meeting.roster.loading"], { exact: true }).waitFor({ state: "detached" });
    const options = roster.getByRole("checkbox");
    assert.ok(await options.count() > 0, "The account needs at least one saved profile");
    const name = await options.first().evaluate((element) => element.closest("label").textContent.trim());
    await roster.getByLabel(text["meeting.roster.search"], { exact: true }).fill(name.slice(0, 2).toLocaleLowerCase(locale));
    const choice = roster.getByRole("checkbox", { name, exact: true });
    await choice.check();
    assert.equal(await choice.isChecked(), true);
    await roster.getByText(text["meeting.roster.selected"].replace("{count}", "1"), { exact: true }).waitFor();
    await roster.getByLabel(text["meeting.roster.search"], { exact: true }).fill("§");
    await roster.getByText(text["meeting.roster.noMatch"], { exact: true }).waitFor();
    const widths = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth }));
    assert.ok(widths.content <= widths.viewport + 1, `roster overflows at ${width}px`);
    await mkdir("test-results", { recursive: true });
    await page.screenshot({ path: `test-results/roster-${locale}-${width}.png`, fullPage: true });
  }
  assert.deepEqual(writes, [], "Selecting participants must not create or change business records");
  assert.deepEqual(failures, []);
}, { requireCredentials: false });
